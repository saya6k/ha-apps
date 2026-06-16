"""Wyoming event handler: Nemotron streaming ASR.

Home Assistant opens one connection per transcription. As audio arrives we feed
the per-connection NemotronStream, decode every stable chunk, and emit
TranscriptChunk deltas so HA can show partial text and start the LLM earlier —
a real latency win on slow CPUs. On AudioStop we flush the tail and send the
final Transcript. supports_transcript_streaming=True.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import time
from typing import Optional

import numpy as np
from wyoming.asr import (
    Transcribe,
    Transcript,
    TranscriptChunk,
    TranscriptStart,
    TranscriptStop,
)
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.error import Error
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler

from .const import SAMPLE_RATE
from .engine import NemotronASR

_LOGGER = logging.getLogger(__name__)

# One transcription at a time: CPU is the bottleneck and the ONNX/decode work
# for a single utterance already saturates the configured threads. The lock is
# held for a whole utterance (AudioStart..AudioStop) to avoid interleaving.
_ASR_LOCK = asyncio.Lock()


def _pcm16_to_float32(audio: bytes) -> np.ndarray:
    return np.frombuffer(audio, dtype="<i2").astype(np.float32) / 32768.0


class NemotronEventHandler(AsyncEventHandler):
    def __init__(
        self,
        wyoming_info: Info,
        cli_args: argparse.Namespace,
        engine: NemotronASR,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.cli_args = cli_args
        self.wyoming_info_event = wyoming_info.event()
        self.engine = engine
        # When False, send only the final Transcript (no TranscriptStart/Chunk/Stop)
        # for maximum compatibility with older HA voice pipelines.
        self.streaming = not getattr(cli_args, "no_transcript_streaming", False)
        self._language: Optional[str] = cli_args.language or None
        self._stream = None
        self._last_emitted = ""
        self._n_samples = 0
        self._t0 = 0.0
        self._have_lock = False

    async def handle_event(self, event: Event) -> bool:
        try:
            if Describe.is_type(event.type):
                await self.write_event(self.wyoming_info_event)
                return True

            if Transcribe.is_type(event.type):
                lang = Transcribe.from_event(event).language
                if lang:
                    self._language = lang
                return True

            if AudioStart.is_type(event.type):
                await self._start()
                return True

            if AudioChunk.is_type(event.type):
                await self._feed(AudioChunk.from_event(event))
                return True

            if AudioStop.is_type(event.type):
                await self._stop()
                return True

            return True
        except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
            _LOGGER.debug("Client disconnected")
            self._release()
            return False
        except Exception as err:  # noqa: BLE001 - surface any engine error
            _LOGGER.exception("Transcription error")
            self._release()
            try:
                await self.write_event(
                    Error(text=str(err), code=err.__class__.__name__).event()
                )
            except (ConnectionResetError, BrokenPipeError):
                pass
            return False

    async def _start(self) -> None:
        await _ASR_LOCK.acquire()
        self._have_lock = True
        self._t0 = time.monotonic()
        self._n_samples = 0
        self._last_emitted = ""
        self._stream = self.engine.create_stream(self._language)
        if self.streaming:
            await self.write_event(TranscriptStart(language=self._language).event())

    async def _feed(self, chunk: AudioChunk) -> None:
        if self._stream is None:
            return
        samples = _pcm16_to_float32(chunk.audio)
        self._n_samples += samples.size
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._stream.accept_audio, samples)
        if self.streaming:
            await self._emit_delta()

    async def _emit_delta(self) -> None:
        text = self._stream.text()
        if text == self._last_emitted:
            return
        # Greedy RNN-T output normally grows by appending; emit the new suffix.
        # On a rare non-append revision we resync silently — the final Transcript
        # still carries the corrected text.
        if text.startswith(self._last_emitted):
            delta = text[len(self._last_emitted):]
            if delta:
                await self.write_event(TranscriptChunk(text=delta).event())
        self._last_emitted = text

    async def _stop(self) -> None:
        try:
            if self._stream is not None:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._stream.finalize)
                if self.streaming:
                    await self._emit_delta()
                    await self.write_event(TranscriptStop().event())
                text = self._stream.text()
                await self.write_event(
                    Transcript(text=text, language=self._language).event()
                )
                audio_dt = self._n_samples / SAMPLE_RATE
                dt = time.monotonic() - self._t0
                _LOGGER.info(
                    "Transcript (%.2fs for %.2fs audio, RTF=%.2f) [lang=%s]: %r",
                    dt, audio_dt, dt / max(audio_dt, 1e-6), self._language, text[:80],
                )
        finally:
            self._release()

    def _release(self) -> None:
        self._stream = None
        if self._have_lock:
            _ASR_LOCK.release()
            self._have_lock = False
