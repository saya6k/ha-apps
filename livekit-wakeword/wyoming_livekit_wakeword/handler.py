"""Wyoming wake word event handler."""
from __future__ import annotations

import argparse
import logging
import time

import numpy as np
from wyoming.audio import AudioChunk, AudioChunkConverter, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler
from wyoming.wake import Detection, NotDetected

from .const import REFRACTORY_SECONDS, SAMPLE_RATE
from .engine import Engine, StreamState

_LOGGER = logging.getLogger(__name__)


class WakeWordHandler(AsyncEventHandler):
    def __init__(
        self,
        wyoming_info: Info,
        cli_args: argparse.Namespace,
        engine: Engine,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._info = wyoming_info
        self._args = cli_args
        self._engine = engine
        self._converter = AudioChunkConverter(rate=SAMPLE_RATE, width=2, channels=1)
        self._state: StreamState | None = None
        self._detected = False

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self._info.event())
            return True

        if AudioStart.is_type(event.type):
            self._state = StreamState()
            self._detected = False
            return True

        if AudioChunk.is_type(event.type):
            if self._state is None:
                self._state = StreamState()
            chunk = self._converter.convert(AudioChunk.from_event(event))
            audio = (
                np.frombuffer(chunk.audio, dtype=np.int16).astype(np.float32)
                / 32768.0
            )
            st = self._state
            now = time.monotonic()
            for scores in self._engine.feed(st, audio):
                if _LOGGER.isEnabledFor(logging.DEBUG):
                    _LOGGER.debug(
                        "%s",
                        " ".join(f"{n}={s:.3f}" for n, s in scores.items()),
                    )
                if (now - st.last_detection) < REFRACTORY_SECONDS:
                    continue
                for name, score in scores.items():
                    if score >= self._args.threshold:
                        st.activations[name] = st.activations.get(name, 0) + 1
                    else:
                        st.activations[name] = 0
                        continue
                    if st.activations[name] >= self._args.trigger_level:
                        _LOGGER.info("Detection: %s (%.3f)", name, score)
                        st.last_detection = now
                        st.activations[name] = 0
                        self._detected = True
                        await self.write_event(
                            Detection(name=name, timestamp=chunk.timestamp).event()
                        )
            return True

        if AudioStop.is_type(event.type):
            if not self._detected:
                await self.write_event(NotDetected().event())
            return True

        return True
