"""Wyoming protocol handler for nemo-asr-c.

Chunk-by-chunk encoder streaming internally; only the final Transcript
is sent (matches wyoming-faster-whisper pattern — HA skips streaming events).
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
        self._stream: NemoCStream | None = None
        self._t0: float = 0.0
        self._n_samples: int = 0
        self._last_emitted: str = ""

    async def handle_event(self, event: Event) -> bool:
        try:
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
                self._t0 = time.monotonic()
                self._n_samples = 0
                self._last_emitted = ""
                return True

            if AudioChunk.is_type(event.type):
                await self._feed(AudioChunk.from_event(event))
                return True

            if AudioStop.is_type(event.type):
                _LOGGER.info("Utterance stop")
                await self._stop()
                return True

            _LOGGER.debug("Unhandled event type: %s", event.type)
            return True
        except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
            _LOGGER.debug("Client disconnected")
            self._release()
            return False
        except Exception:
            _LOGGER.exception("Unexpected error in handle_event")
            self._release()
            await self.write_event(
                Event("error", {"text": "Internal server error", "code": "internal"})
            )
            return False

    async def _feed(self, chunk: AudioChunk) -> None:
        samples = _pcm16_to_float32(chunk.audio)
        self._n_samples += samples.size
        loop = asyncio.get_running_loop()
        async with _ASR_LOCK:
            # Lazy-init stream on first audio chunk (matching
            # wyoming-faster-whisper pattern).
            if self._stream is None:
                self._stream = self._engine.create_stream(self._language)
            await loop.run_in_executor(None, self._stream.accept_audio, samples)
        self._emit_delta()

    async def _stop(self) -> None:
        try:
            if self._stream is not None:
                loop = asyncio.get_running_loop()
                async with _ASR_LOCK:
                    await loop.run_in_executor(None, self._stream.finalize)
                self._emit_delta()
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

    def _emit_delta(self) -> None:
        """Track latest text for the final transcript (no streaming output to HA)."""
        if self._stream is None:
            return
        text = self._stream.text()
        if text != self._last_emitted:
            self._last_emitted = text

    def _release(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None
