"""Wyoming event handler for Supertonic.

Mirrors wyoming-piper's behaviour:
  * Describe -> Info (lists voices, advertises supports_synthesize_streaming).
  * Plain Synthesize: split into sentences, stream Audio* per sentence.
  * Stream Synthesize (SynthesizeStart / SynthesizeChunk / SynthesizeStop):
    feed text into a SentenceBoundaryDetector, synthesize on each completed
    sentence, emit SynthesizeStopped on stop.

`AudioStart` is sent *before* the first synthesis pass so the client can
prepare its audio pipeline while the model is still working — this trims
~5–10 ms off perceived TTFT vs sending `AudioStart` after synthesis
completes.

Synthesis itself is monolithic per sentence (supertonic.TTS returns the
whole PCM at once and flow matching can't be sliced mid-iteration), so we
don't have ppaso-style within-sentence chunk streaming. Sentence-level
streaming is still effective for any multi-sentence response.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import math
import time
from typing import Optional

from sentence_stream import SentenceBoundaryDetector
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.error import Error
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler
from wyoming.tts import (
    Synthesize,
    SynthesizeChunk,
    SynthesizeStart,
    SynthesizeStop,
    SynthesizeStopped,
)

from .const import DEFAULT_LANGUAGE, DEFAULT_VOICE
from .engine import SupertonicEngine, float_to_pcm16

_LOGGER = logging.getLogger(__name__)

_WIDTH = 2  # int16
_CHANNELS = 1
_TTS_LOCK = asyncio.Lock()


class SupertonicEventHandler(AsyncEventHandler):
    def __init__(
        self,
        wyoming_info: Info,
        cli_args: argparse.Namespace,
        engine: SupertonicEngine,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.cli_args = cli_args
        self.wyoming_info_event = wyoming_info.event()
        self.engine = engine
        self.is_streaming: Optional[bool] = None
        self.sbd = SentenceBoundaryDetector()
        self._synthesize: Optional[Synthesize] = None
        # Wall-clock at which the current client request arrived. Consumed
        # (and cleared) by the first sentence's first AudioChunk to log TTFT.
        self._request_t0: Optional[float] = None

    async def handle_event(self, event: Event) -> bool:
        try:
            if Describe.is_type(event.type):
                # No log here: HA's Wyoming integration and our own
                # Docker HEALTHCHECK both poll Describe every ~30 s.
                # Debug spam would drown out genuinely interesting events.
                await self.write_event(self.wyoming_info_event)
                return True

            if Synthesize.is_type(event.type):
                if self.is_streaming:
                    # Streaming variant is already in flight; the plain
                    # Synthesize event is sent only for older clients.
                    return True
                self._request_t0 = time.monotonic()
                synthesize = Synthesize.from_event(event)
                self._synthesize = Synthesize(text="", voice=synthesize.voice)
                self.sbd = SentenceBoundaryDetector()
                start_sent = False
                for i, sentence in enumerate(self.sbd.add_chunk(synthesize.text)):
                    self._synthesize.text = sentence
                    await self._handle_synthesize(
                        self._synthesize,
                        send_start=(i == 0),
                        send_stop=False,
                    )
                    start_sent = True

                tail = self.sbd.finish()
                if tail:
                    self._synthesize.text = tail
                    await self._handle_synthesize(
                        self._synthesize,
                        send_start=(not start_sent),
                        send_stop=True,
                    )
                else:
                    await self.write_event(AudioStop().event())
                return True

            if self.cli_args.no_streaming:
                return True

            if SynthesizeStart.is_type(event.type):
                stream_start = SynthesizeStart.from_event(event)
                self.is_streaming = True
                self.sbd = SentenceBoundaryDetector()
                self._synthesize = Synthesize(text="", voice=stream_start.voice)
                self._request_t0 = time.monotonic()
                _LOGGER.debug("Text stream started: voice=%s", stream_start.voice)
                return True

            if SynthesizeChunk.is_type(event.type):
                assert self._synthesize is not None
                stream_chunk = SynthesizeChunk.from_event(event)
                for sentence in self.sbd.add_chunk(stream_chunk.text):
                    self._synthesize.text = sentence
                    await self._handle_synthesize(self._synthesize)
                return True

            if SynthesizeStop.is_type(event.type):
                assert self._synthesize is not None
                tail = self.sbd.finish()
                if tail:
                    self._synthesize.text = tail
                    await self._handle_synthesize(self._synthesize)
                await self.write_event(SynthesizeStopped().event())
                _LOGGER.debug("Text stream stopped")
                return True

            return True
        except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
            _LOGGER.debug("Client disconnected")
            return False
        except Exception as err:
            _LOGGER.exception("Synthesis error")
            try:
                await self.write_event(
                    Error(text=str(err), code=err.__class__.__name__).event()
                )
            except (ConnectionResetError, BrokenPipeError):
                pass
            return False

    async def _handle_synthesize(
        self,
        synthesize: Synthesize,
        send_start: bool = True,
        send_stop: bool = True,
    ) -> bool:
        raw_text = synthesize.text
        text = " ".join(raw_text.strip().splitlines())
        if not text:
            if send_start:
                await self.write_event(
                    AudioStart(
                        rate=self.engine.sample_rate,
                        width=_WIDTH,
                        channels=_CHANNELS,
                    ).event()
                )
            if send_stop:
                await self.write_event(AudioStop().event())
            return True

        if self.cli_args.auto_punctuation:
            if text[-1] not in self.cli_args.auto_punctuation:
                text = text + self.cli_args.auto_punctuation[0]

        # Pick voice + language from the request, with our defaults as fallback.
        voice_name = DEFAULT_VOICE
        language = self.cli_args.language or DEFAULT_LANGUAGE
        if synthesize.voice is not None:
            if synthesize.voice.name:
                voice_name = synthesize.voice.name
            if getattr(synthesize.voice, "language", None):
                language = synthesize.voice.language

        if voice_name not in self.engine.available_voices:
            _LOGGER.warning(
                "Unknown voice %r; falling back to %s",
                voice_name,
                self.engine.available_voices[0],
            )
            voice_name = self.engine.available_voices[0]

        _LOGGER.info(
            "Synthesizing: %r [voice=%s lang=%s len=%d]",
            text[:40],
            voice_name,
            language,
            len(text),
        )

        # Send AudioStart before synthesis so the client can prep its
        # pipeline while we're still running the model.
        if send_start:
            await self.write_event(
                AudioStart(
                    rate=self.engine.sample_rate,
                    width=_WIDTH,
                    channels=_CHANNELS,
                ).event()
            )

        loop = asyncio.get_running_loop()

        t0 = time.monotonic()
        async with _TTS_LOCK:
            wav = await loop.run_in_executor(
                None, self.engine.synthesize, text, voice_name, language
            )
        synth_dt = time.monotonic() - t0
        audio_dt = float(wav.size) / max(self.engine.sample_rate, 1)
        _LOGGER.info(
            "Synth done: %.2fs CPU for %.2fs audio (RTF=%.2f)",
            synth_dt,
            audio_dt,
            synth_dt / max(audio_dt, 1e-6),
        )

        audio_bytes = float_to_pcm16(wav)

        bytes_per_sample = _WIDTH * _CHANNELS
        bytes_per_chunk = bytes_per_sample * self.cli_args.samples_per_chunk
        if bytes_per_chunk <= 0:
            bytes_per_chunk = bytes_per_sample * 1024
        num_chunks = int(math.ceil(len(audio_bytes) / bytes_per_chunk)) or 1
        for i in range(num_chunks):
            offset = i * bytes_per_chunk
            chunk = audio_bytes[offset : offset + bytes_per_chunk]
            if not chunk:
                continue
            await self.write_event(
                AudioChunk(
                    audio=chunk,
                    rate=self.engine.sample_rate,
                    width=_WIDTH,
                    channels=_CHANNELS,
                ).event()
            )
            # TTFT = time from the client's Synthesize / SynthesizeStart
            # event arriving to the first audio chunk leaving the socket.
            # Includes lock-wait, synth, and PCM conversion — what the
            # listener actually perceives as "time until they hear sound".
            # Only the very first chunk of the first sentence reports it;
            # subsequent chunks and sentences would log near-zero deltas.
            if i == 0 and self._request_t0 is not None:
                _LOGGER.info(
                    "TTFT: %.2fs (request → first audio chunk)",
                    time.monotonic() - self._request_t0,
                )
                self._request_t0 = None

        if send_stop:
            await self.write_event(AudioStop().event())
        return True
