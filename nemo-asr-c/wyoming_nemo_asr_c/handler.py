"""Wyoming protocol handler for nemo-asr-c.

Streaming ASR: AudioStart -> TranscriptStart, each AudioChunk -> incremental
TranscriptChunk deltas, AudioStop -> TranscriptStop + final Transcript.

Follows the nemotron-asr streaming pattern closely.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

import numpy as np
from wyoming.asr import Transcript, TranscriptChunk, TranscriptStart, TranscriptStop
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler

if TYPE_CHECKING:
    from .engine import NemoCEngine, NemoCStream
    from argparse import Namespace

_LOGGER = logging.getLogger(__name__)

# Serialize utterances — the C context is not re-entrant.
_ASR_LOCK = asyncio.Lock()


def _pcm16_to_float32(audio: bytes) -> np.ndarray:
    """Convert 16-bit PCM bytes to float32 [-1, 1]."""
    return np.frombuffer(audio, dtype="<i2").astype(np.float32) / 32768.0


class NemoCHandler(AsyncEventHandler):
    """Streaming Wyoming ASR handler backed by Nemotron C runtime."""

    def __init__(
        self,
        wyoming_info: Info,
        cli_args: Namespace,
        engine: NemoCEngine,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.wyoming_info_event = wyoming_info.event()
        self._args = cli_args
        self._engine = engine
        self._language: str | None = cli_args.language
        self._stream: NemoCStream | None = None
        self._t0: float = 0.0
        self._n_samples: int = 0
        self._last_emitted: str = ""
        self._have_lock: bool = False
        self._streaming: bool = True  # always streaming for this add-on

    async def handle_event(self, event: Event) -> bool:
        try:
            if Describe.is_type(event.type):
                await self.write_event(self.wyoming_info_event)
                return True

            if event.type == "transcribe":
                # Wyoming Transcribe event carries an optional language override.
                data = event.data if hasattr(event, "data") else {}
                lang = data.get("language") if isinstance(data, dict) else None
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
            return False
        except Exception:
            _LOGGER.exception("Unexpected error in handle_event")
            await self.write_event(
                Event("error", {"text": "Internal server error", "code": "internal"})
            )
            return False

    async def _start(self) -> None:
        await _ASR_LOCK.acquire()
        self._have_lock = True
        self._t0 = time.monotonic()
        self._n_samples = 0
        self._last_emitted = ""
        self._stream = self._engine.create_stream(self._language)
        if self._streaming:
            await self.write_event(
                TranscriptStart(language=self._language).event()
            )

    async def _feed(self, chunk: AudioChunk) -> None:
        if self._stream is None:
            return
        samples = _pcm16_to_float32(chunk.audio)
        self._n_samples += samples.size
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._stream.accept_audio, samples)
        if self._streaming:
            await self._emit_delta()

    async def _stop(self) -> None:
        try:
            if self._stream is not None:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._stream.finalize)
                if self._streaming:
                    await self._emit_delta()
                    await self.write_event(TranscriptStop().event())
                text = self._stream.text()
                await self.write_event(
                    Transcript(text=text, language=self._language).event()
                )
                # Log real-time factor.
                audio_dt = self._n_samples / 16000.0 if self._n_samples else 0.0
                dt = time.monotonic() - self._t0
                rtf = f"{dt / audio_dt:.2f}" if audio_dt > 0 else "?"
                _LOGGER.info(
                    "Utterance: %d samples (%.1fs), wall=%.2fs, RTF=%s",
                    self._n_samples, audio_dt, dt, rtf,
                )
        finally:
            self._release()

    async def _emit_delta(self) -> None:
        if self._stream is None:
            return
        text = self._stream.text()
        if text == self._last_emitted:
            return
        # Greedy RNN-T output normally grows by appending; emit the new suffix.
        if text.startswith(self._last_emitted):
            delta = text[len(self._last_emitted):]
            if delta:
                await self.write_event(TranscriptChunk(text=delta).event())
        self._last_emitted = text

    def _release(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None
        if self._have_lock:
            self._have_lock = False
            _ASR_LOCK.release()
