"""Incremental wake word scoring on livekit-wakeword's frozen frontend.

Upstream's `WakeWordModel.predict()` is stateless: it recomputes mel + all 16
embeddings for a full 2 s window on every call (~10x the CPU of streaming).
This engine instead keeps openWakeWord-style streaming state per audio stream:
every 80 ms of new audio -> mel over the trailing 12640 samples (exactly 76
frames) -> ONE new embedding -> classifiers over the last 16 embeddings.
Numerically equivalent to the stateless API at the same alignment (verified:
positive fixture 0.983 vs 0.981; oWW hey_jarvis 0.995 on a real clip).

The frontends (melspectrogram.onnx + Google speech embedding) are bundled in
the livekit-wakeword wheel and are byte-identical to openWakeWord's, which is
why oWW's pretrained classifiers run here unmodified.
"""
from __future__ import annotations

import logging
from collections import deque

import numpy as np

from .const import EMB_BUFFER_SAMPLES, FRAME_SAMPLES, NUM_EMBEDDINGS
from .models import ResolvedModel

_LOGGER = logging.getLogger(__name__)


class StreamState:
    """Per-connection rolling buffers (engine itself is shared/stateless)."""

    def __init__(self) -> None:
        self.buf = np.zeros(EMB_BUFFER_SAMPLES, dtype=np.float32)
        self.embeddings: deque = deque(maxlen=NUM_EMBEDDINGS)
        self.pending = np.empty(0, dtype=np.float32)
        # model name -> consecutive frames at/above threshold (trigger_level)
        self.activations: dict[str, int] = {}
        self.last_detection = 0.0


class Engine:
    def __init__(self, models: list[ResolvedModel]) -> None:
        import onnxruntime as ort
        from livekit.wakeword.models.feature_extractor import (
            MelSpectrogramFrontend,
            SpeechEmbedding,
        )
        from livekit.wakeword.resources import (
            get_embedding_model_path,
            get_mel_model_path,
        )

        self._mel = MelSpectrogramFrontend(onnx_path=get_mel_model_path())
        self._emb = SpeechEmbedding(onnx_path=get_embedding_model_path())

        self._classifiers: dict[str, tuple] = {}
        for m in models:
            opts = ort.SessionOptions()
            opts.inter_op_num_threads = 1
            opts.intra_op_num_threads = 1
            session = ort.InferenceSession(
                str(m.path), sess_options=opts, providers=["CPUExecutionProvider"]
            )
            self._classifiers[m.name] = (session, session.get_inputs()[0].name)
            _LOGGER.info("Loaded wake word model %r (%s)", m.name, m.path)

    def feed(self, state: StreamState, audio: np.ndarray):
        """Feed float32 [-1, 1] @ 16 kHz samples; yield scores per 80 ms frame."""
        state.pending = np.concatenate([state.pending, audio])
        while len(state.pending) >= FRAME_SAMPLES:
            frame, state.pending = (
                state.pending[:FRAME_SAMPLES],
                state.pending[FRAME_SAMPLES:],
            )
            state.buf = np.concatenate([state.buf[FRAME_SAMPLES:], frame])
            mel = self._mel(state.buf)[0]  # (76, 32)
            state.embeddings.append(self._emb(mel[np.newaxis])[0])  # (96,)
            if len(state.embeddings) < NUM_EMBEDDINGS:
                continue
            x = np.stack(state.embeddings)[np.newaxis].astype(np.float32)
            yield {
                name: float(session.run(None, {inp: x})[0][0, 0])
                for name, (session, inp) in self._classifiers.items()
            }

    def warmup(self) -> None:
        state = StreamState()
        for _ in self.feed(state, np.zeros(FRAME_SAMPLES * (NUM_EMBEDDINGS + 1),
                                           dtype=np.float32)):
            pass
