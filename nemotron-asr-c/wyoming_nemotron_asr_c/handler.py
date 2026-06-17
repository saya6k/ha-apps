"""Wyoming protocol handler for nemotron-asr-c.

Buffered: accumulates audio in a bytearray and transcribes once on AudioStop
(same pattern as nemo-asr-cpp).  The RNN-T greedy decoder produces token-boundary
artifacts when fed chunk-by-chunk — one-shot transcription avoids that.
Only the final Transcript is sent.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

import numpy as np
from wyoming.asr import Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler

if TYPE_CHECKING:
    from .engine import NemoCEngine, NemoCStream
    from argparse import Namespace

_LOGGER = logging.getLogger(__name__)

# Serialize access to the shared C context (not re-entrant).
_ASR_LOCK = asyncio.Lock()


def _pcm16_to_float32(audio: bytes) -> np.ndarray:
    """Convert 16-bit PCM bytes to float32 [-1, 1]."""
    return np.frombuffer(audio, dtype="<i2").astype(np.float32) / 32768.0


class NemoCHandler(AsyncEventHandler):
    """Wyoming ASR handler backed by Nemotron C runtime."""

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
        self._buffer: bytearray = bytearray()
        self._t0: float = 0.0
        self._n_samples: int = 0

    async def handle_event(self, event: Event) -> bool:
        try:
            _LOGGER.debug("Event: %s (data=%s, payload_len=%d)",
                          event.type, bool(event.data),
                          len(event.payload) if event.payload else 0)
            if Describe.is_type(event.type):
                await self.write_event(self.wyoming_info_event)
                return True

            if event.type == "transcribe":
                data = event.data if hasattr(event, "data") else {}
                lang = data.get("language") if isinstance(data, dict) else None
                if lang:
                    self._language = lang
                _LOGGER.info("Transcribe request (language=%s)", self._language)
                return True

            if AudioStart.is_type(event.type):
                _LOGGER.info("Utterance start")
                self._buffer = bytearray()
                self._t0 = time.monotonic()
                self._n_samples = 0
                return True

            if AudioChunk.is_type(event.type):
                # Buffer raw PCM — no C call, no lock.
                chunk = AudioChunk.from_event(event)
                self._buffer.extend(chunk.audio)
                self._n_samples += len(chunk.audio) // 2
                return True

            if AudioStop.is_type(event.type):
                _LOGGER.info("Utterance stop")
                await self._transcribe()
                return True

            _LOGGER.debug("Unhandled event type: %s", event.type)
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

    async def _transcribe(self) -> None:
        """Convert buffered audio and transcribe in one C call (buffered)."""
        if not self._buffer:
            _LOGGER.debug("No audio buffered")
            return
        samples = _pcm16_to_float32(bytes(self._buffer))
        loop = asyncio.get_running_loop()
        async with _ASR_LOCK:
            stream = self._engine.create_stream(self._language)
            try:
                await loop.run_in_executor(None, stream.accept_audio, samples)
                await loop.run_in_executor(None, stream.finalize)
                text = stream.text()
            finally:
                stream.close()
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
