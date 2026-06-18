"""Wyoming protocol handler for nemotron-asr-c.

Streaming: each AudioChunk's new PCM samples are fed to the C streaming cascade
(mel -> encoder -> RNN-T, each stateful across calls). Partial transcripts are
emitted as TranscriptChunk delta events; the final Transcript is sent on
AudioStop.
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
        self._last_partial: str = ""
        self._transcript_started: bool = False
        self._t0: float = 0.0
        self._n_samples: int = 0

    def _close_stream(self) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None

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
                self._close_stream()
                self._stream = self._engine.create_stream(self._language)
                self._last_partial = ""
                self._t0 = time.monotonic()
                self._n_samples = 0
                await self.write_event(TranscriptStart(language=self._language).event())
                self._transcript_started = True
                return True

            if AudioChunk.is_type(event.type):
                if self._stream is None:
                    return True
                chunk = AudioChunk.from_event(event)
                self._n_samples += len(chunk.audio) // 2
                samples = _pcm16_to_float32(chunk.audio)
                loop = asyncio.get_running_loop()
                async with _ASR_LOCK:
                    await loop.run_in_executor(None, self._stream.accept_audio, samples)
                    partial = self._stream.text()
                if partial and partial != self._last_partial:
                    # TranscriptChunk.text is a delta — emit only the new tail.
                    delta = (
                        partial[len(self._last_partial):]
                        if partial.startswith(self._last_partial)
                        else partial
                    )
                    if delta:
                        await self.write_event(TranscriptChunk(text=delta).event())
                    self._last_partial = partial
                return True

            if AudioStop.is_type(event.type):
                _LOGGER.info("Utterance stop")
                await self._finalize()
                return True

            _LOGGER.debug("Unhandled event type: %s", event.type)
            return True
        except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
            _LOGGER.debug("Client disconnected")
            self._close_stream()
            return False
        except Exception:
            _LOGGER.exception("Unexpected error in handle_event")
            self._close_stream()
            if self._transcript_started:
                self._transcript_started = False
                await self.write_event(TranscriptStop().event())
            await self.write_event(
                Event("error", {"text": "Internal server error", "code": "internal"})
            )
            return False

    async def _finalize(self) -> None:
        """Finalize the active stream and emit TranscriptStop + Transcript."""
        if self._stream is None:
            _LOGGER.debug("No active stream on AudioStop")
            return  # no TranscriptStart was sent — don't emit orphaned Stop/Transcript
        loop = asyncio.get_running_loop()
        text = ""
        try:
            async with _ASR_LOCK:
                await loop.run_in_executor(None, self._stream.finalize)
                text = self._stream.text()
        except Exception:
            _LOGGER.exception("Error during stream finalization")
        finally:
            self._close_stream()
        self._transcript_started = False
        await self.write_event(TranscriptStop().event())
        await self.write_event(Transcript(text=text, language=self._language).event())
        audio_dt = self._n_samples / 16000.0 if self._n_samples else 0.0
        dt = time.monotonic() - self._t0
        rtf = f"{dt / audio_dt:.2f}" if audio_dt > 0 else "?"
        _LOGGER.info(
            "Utterance: %d samples (%.1fs), wall=%.2fs, RTF=%s",
            self._n_samples, audio_dt, dt, rtf,
        )
