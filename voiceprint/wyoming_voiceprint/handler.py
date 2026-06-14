"""Wyoming STT proxy handler — pass-through with parallel speaker verification.

Audio chunks are forwarded to the upstream STT unchanged as they arrive, so
streaming decoders lose nothing. Verification runs in an executor between
AudioStop and the upstream Transcript; a mismatch swallows the transcript.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import time
import wave

import numpy as np
from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioChunkConverter, AudioStart, AudioStop
from wyoming.client import AsyncClient
from wyoming.event import Event
from wyoming.info import Describe
from wyoming.server import AsyncEventHandler

from .const import CAPTURE_DIR, SAMPLE_RATE
from .embedder import Embedder

_LOGGER = logging.getLogger(__name__)


class VoiceprintHandler(AsyncEventHandler):
    def __init__(
        self,
        info_provider,
        cli_args: argparse.Namespace,
        embedder: Embedder,
        voiceprints: dict[str, np.ndarray],
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._info_provider = info_provider
        self._args = cli_args
        self._embedder = embedder
        self._voiceprints = voiceprints
        self._converter = AudioChunkConverter(rate=SAMPLE_RATE, width=2, channels=1)
        self._upstream: AsyncClient | None = None
        self._transcribe: Event | None = None
        self._buffer: list[np.ndarray] = []

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            info = await self._info_provider.info()
            await self.write_event(info.event())
            return True

        if Transcribe.is_type(event.type):
            self._transcribe = event
            return True

        if AudioStart.is_type(event.type):
            self._buffer = []
            try:
                self._upstream = AsyncClient.from_uri(self._args.upstream_uri)
                await self._upstream.connect()
            except OSError:
                _LOGGER.exception("Cannot connect to upstream %s", self._args.upstream_uri)
                self._upstream = None
                return True
            if self._transcribe is not None:
                await self._upstream.write_event(self._transcribe)
            await self._upstream.write_event(event)
            return True

        if AudioChunk.is_type(event.type):
            if self._upstream is not None:
                await self._upstream.write_event(event)
            chunk = self._converter.convert(AudioChunk.from_event(event))
            self._buffer.append(
                np.frombuffer(chunk.audio, dtype=np.int16).astype(np.float32) / 32768.0
            )
            return True

        if AudioStop.is_type(event.type):
            if self._args.capture:
                self._save_capture()
            if self._upstream is None:
                await self.write_event(Transcript(text="").event())
                return False
            await self._upstream.write_event(event)

            verify_task = None
            if self._voiceprints:
                audio = np.concatenate(self._buffer) if self._buffer else np.zeros(0, np.float32)
                verify_task = asyncio.get_running_loop().run_in_executor(
                    None, self._verify, audio
                )

            transcript_event = await self._read_transcript()
            await self._upstream.disconnect()
            self._upstream = None

            if verify_task is None:
                await self.write_event(transcript_event)
                return False

            speaker, score = await verify_task
            matched = speaker is not None
            _LOGGER.info(
                "Speaker %s (best=%s score=%.3f threshold=%.2f)",
                "matched" if matched else "rejected",
                speaker or "-", score, self._args.threshold,
            )
            if not matched and self._args.require_match:
                await self.write_event(Transcript(text="").event())
                return False
            if matched and self._args.tag_speaker:
                text = Transcript.from_event(transcript_event).text
                transcript_event = Transcript(text=f"[{speaker}] {text}").event()
            await self.write_event(transcript_event)
            return False

        return True

    async def _read_transcript(self) -> Event:
        while True:
            event = await self._upstream.read_event()
            if event is None:
                _LOGGER.error("Upstream closed before sending a transcript")
                return Transcript(text="").event()
            if Transcript.is_type(event.type):
                return event

    def _save_capture(self) -> None:
        """Dump the buffered utterance as a 16 kHz mono WAV to the fixed
        CAPTURE_DIR — same audio path as live, so these clips enroll in-domain.
        Drop the good ones into <enroll_dir>/<speaker>/ and turn capture off."""
        if not self._buffer:
            return
        audio = np.concatenate(self._buffer)
        pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
        os.makedirs(CAPTURE_DIR, exist_ok=True)
        path = os.path.join(CAPTURE_DIR, f"capture-{int(time.time() * 1000)}.wav")
        with wave.open(path, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(pcm)
        _LOGGER.info("Captured %.1fs -> %s", len(audio) / SAMPLE_RATE, path)

    def _verify(self, audio: np.ndarray) -> tuple[str | None, float]:
        emb = self._embedder.embed(audio)
        if emb is None:
            return None, 0.0
        best_name, best_score = None, -1.0
        for name, print_emb in self._voiceprints.items():
            score = float(np.dot(emb, print_emb))
            if score > best_score:
                best_name, best_score = name, score
        if _LOGGER.isEnabledFor(logging.DEBUG):
            _LOGGER.debug(
                "scores: %s",
                " ".join(
                    f"{n}={float(np.dot(emb, p)):.3f}"
                    for n, p in self._voiceprints.items()
                ),
            )
        if best_score >= self._args.threshold:
            return best_name, best_score
        return None, best_score
