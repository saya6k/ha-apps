"""Speaker embedding extraction — kaldi fbank + CAM++ on LiteRT."""
from __future__ import annotations

import threading

import kaldi_native_fbank as knf
import numpy as np
from ai_edge_litert.interpreter import Interpreter

from .const import NUM_FRAMES, NUM_MELS, SAMPLE_RATE, TRIM_RMS_FACTOR


def _fbank(audio: np.ndarray) -> np.ndarray:
    """80-dim kaldi fbank of float32 [-1, 1] audio, global-mean normalized."""
    opts = knf.FbankOptions()
    opts.frame_opts.samp_freq = SAMPLE_RATE
    opts.frame_opts.dither = 0
    opts.frame_opts.snip_edges = True
    opts.mel_opts.num_bins = NUM_MELS
    fb = knf.OnlineFbank(opts)
    fb.accept_waveform(SAMPLE_RATE, audio.tolist())
    fb.input_finished()
    feats = np.stack([fb.get_frame(i) for i in range(fb.num_frames_ready)])
    return (feats - feats.mean(axis=0, keepdims=True)).astype(np.float32)


def _trim_silence(audio: np.ndarray) -> np.ndarray:
    """Cut leading/trailing silence by 25 ms-frame RMS."""
    hop = 400
    n = len(audio) // hop
    if n < 2:
        return audio
    rms = np.sqrt((audio[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
    voiced = np.flatnonzero(rms > rms.max() * TRIM_RMS_FACTOR)
    if len(voiced) == 0:
        return audio
    return audio[voiced[0] * hop : (voiced[-1] + 1) * hop]


class Embedder:
    """Thread-safe single-session embedding extractor."""

    def __init__(self, model_path: str) -> None:
        self._interp = Interpreter(model_path=model_path, num_threads=1)
        self._interp.allocate_tensors()
        self._input = self._interp.get_input_details()[0]["index"]
        self._output = self._interp.get_output_details()[0]["index"]
        self._lock = threading.Lock()

    def embed(self, audio: np.ndarray) -> np.ndarray | None:
        """L2-normalized 192-dim embedding of float32 [-1, 1] mono 16 kHz audio.

        Returns None when the audio is too short to produce fbank frames.
        """
        audio = _trim_silence(audio)
        if len(audio) < SAMPLE_RATE // 4:
            return None
        feats = _fbank(audio)
        if len(feats) < NUM_FRAMES:
            feats = np.tile(feats, (NUM_FRAMES // len(feats) + 1, 1))
        feats = feats[:NUM_FRAMES]
        x = np.ascontiguousarray(feats.T)[np.newaxis]  # (1, 80, 500)
        with self._lock:
            self._interp.set_tensor(self._input, x)
            self._interp.invoke()
            emb = self._interp.get_tensor(self._output)[0]
        return emb / np.linalg.norm(emb)
