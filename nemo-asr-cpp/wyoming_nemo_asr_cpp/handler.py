"""Wyoming event handler: buffer the utterance, transcribe on AudioStop.

The parakeet.cpp context is shared and not re-entrant, so a lock serialises
transcription; CPU is the bottleneck anyway. One transcribe call per utterance
(buffered) gives clean output and is faster than chunked streaming.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import time
from typing import Optional

import numpy as np
from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.error import Error
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler

from .const import SAMPLE_RATE, resolve_lang
from .engine import ParakeetASR

_LOGGER = logging.getLogger(__name__)
_ASR_LOCK = asyncio.Lock()


def _pcm16_to_float32(audio: bytes) -> np.ndarray:
    return np.frombuffer(audio, dtype="<i2").astype(np.float32) / 32768.0


class ParakeetEventHandler(AsyncEventHandler):
    def __init__(
        self,
        wyoming_info: Info,
        cli_args: argparse.Namespace,
        engine: ParakeetASR,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.cli_args = cli_args
        self.wyoming_info_event = wyoming_info.event()
        self.engine = engine
        self._language: Optional[str] = cli_args.language or None
        self._buffer = bytearray()
        self._t0 = 0.0

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
                self._buffer = bytearray()
                self._t0 = time.monotonic()
                return True
            if AudioChunk.is_type(event.type):
                self._buffer += AudioChunk.from_event(event).audio
                return True
            if AudioStop.is_type(event.type):
                await self._finalize()
                return True
            return True
        except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
            _LOGGER.debug("Client disconnected")
            return False
        except Exception as err:  # noqa: BLE001 - surface any engine error
            _LOGGER.exception("Transcription error")
            try:
                await self.write_event(
                    Error(text=str(err), code=err.__class__.__name__).event()
                )
            except (ConnectionResetError, BrokenPipeError):
                pass
            return False

    async def _finalize(self) -> None:
        audio = _pcm16_to_float32(bytes(self._buffer))
        self._buffer = bytearray()
        lang = resolve_lang(self._language)
        loop = asyncio.get_running_loop()
        async with _ASR_LOCK:
            text = await loop.run_in_executor(
                None, self.engine.transcribe, audio, lang
            )
        await self.write_event(Transcript(text=text, language=self._language).event())
        audio_dt = audio.size / SAMPLE_RATE
        dt = time.monotonic() - self._t0
        _LOGGER.info(
            "Transcript (%.2fs for %.2fs audio, RTF=%.2f) [lang=%s]: %r",
            dt, audio_dt, dt / max(audio_dt, 1e-6), lang, text[:80],
        )
