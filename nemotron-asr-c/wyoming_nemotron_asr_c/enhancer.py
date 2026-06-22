"""ctypes bridge to libfastenhancer.so — optional speech-enhancement pre-filter.

FastEnhancer denoises 16 kHz mono audio in fixed 256-sample frames
(``fe_run`` = 256 samples in -> 256 out). The C runtime keeps its state in
process globals, so this wraps a single instance; ASR is already serialized by
the handler's ``_ASR_LOCK``, so one shared instance is safe.

Wyoming ``AudioChunk``s are not 256-aligned, so :meth:`process` accumulates
samples in a ring buffer and only emits enhanced output for whole frames; the
trailing partial frame is zero-padded and returned by :meth:`flush` at
end-of-utterance. There is no ``fe_reset`` in the C API, so :meth:`reset` clears
the STFT/GRU history with ``fe_free`` + ``fe_init`` (cheap — 95 KB weights).
"""

from __future__ import annotations

import ctypes
import logging
import os
from ctypes import POINTER, c_char, c_float, c_int, c_void_p

import numpy as np

_LOGGER = logging.getLogger(__name__)

# Samples per fe_run() call (16 ms @ 16 kHz) — fixed by the C runtime.
FRAME = 256


class FastEnhancer:
    """Single-instance denoise pre-filter over libfastenhancer.so."""

    def __init__(self, lib_dir: str, weights_path: str) -> None:
        lib_path = os.path.join(lib_dir, "libfastenhancer.so")
        self._lib = L = ctypes.CDLL(lib_path)

        # int  fe_init(const void *denoise, int dsize, const void *derev, int rsize)
        L.fe_init.restype = c_int
        L.fe_init.argtypes = [c_void_p, c_int, c_void_p, c_int]
        # void fe_run(const float *in, float *out)  — 256 in -> 256 out
        L.fe_run.restype = None
        L.fe_run.argtypes = [POINTER(c_float), POINTER(c_float)]
        # void fe_free(void)
        L.fe_free.restype = None
        L.fe_free.argtypes = []
        # void fe_set_hpf(int) — toggling on also re-zeros the HPF filter state,
        # which fe_init does NOT touch (HPF lives in main.c process globals).
        L.fe_set_hpf.restype = None
        L.fe_set_hpf.argtypes = [c_int]

        with open(weights_path, "rb") as f:
            wbytes = f.read()
        # Keep the weight blob alive for the C state's lifetime: fe_process reads
        # the FeWeights struct (which points into this buffer) on every frame.
        self._weights = (c_char * len(wbytes)).from_buffer_copy(wbytes)
        self._weights_ptr = ctypes.cast(self._weights, c_void_p)
        self._weights_len = len(wbytes)

        # Ring buffer of leftover samples that didn't fill a frame.
        self._buf = np.zeros(0, dtype=np.float32)

        self._init_c()
        _LOGGER.info(
            "FastEnhancer ready: %s (%d-byte weights, denoise-only)",
            lib_path, self._weights_len,
        )

    def _init_c(self) -> None:
        # dereverb disabled (NULL, 0); HPF stays on per upstream default, AGC off.
        rc = self._lib.fe_init(self._weights_ptr, self._weights_len, None, 0)
        if rc != 0:
            raise RuntimeError(f"fe_init failed (rc={rc})")
        self._lib.fe_set_hpf(1)  # enable + zero the 80 Hz HPF history

    def reset(self) -> None:
        """Clear per-utterance state (ring buffer + STFT/GRU history)."""
        self._buf = np.zeros(0, dtype=np.float32)
        self._lib.fe_free()  # no fe_reset; free + re-init clears all C state
        self._init_c()

    def _run_frames(self, samples: np.ndarray) -> np.ndarray:
        """Run fe_run over a multiple-of-FRAME array; return enhanced output."""
        n = samples.size
        if n == 0:
            return np.zeros(0, dtype=np.float32)
        out = np.empty(n, dtype=np.float32)
        out_frame = np.empty(FRAME, dtype=np.float32)
        out_ptr = out_frame.ctypes.data_as(POINTER(c_float))
        for off in range(0, n, FRAME):
            frame = np.ascontiguousarray(samples[off:off + FRAME])
            self._lib.fe_run(frame.ctypes.data_as(POINTER(c_float)), out_ptr)
            out[off:off + FRAME] = out_frame
        return out

    def process(self, samples: np.ndarray) -> np.ndarray:
        """Enhance new audio; return enhanced samples for whole frames only.

        Samples that don't fill a 256-frame are buffered for the next call.
        """
        a = np.ascontiguousarray(samples, dtype=np.float32)
        if a.size:
            self._buf = np.concatenate((self._buf, a))
        nframes = self._buf.size // FRAME
        if nframes == 0:
            return np.zeros(0, dtype=np.float32)
        take = nframes * FRAME
        whole, self._buf = self._buf[:take], self._buf[take:]
        return self._run_frames(whole)

    def flush(self) -> np.ndarray:
        """Process the buffered remainder (zero-padded to one frame)."""
        valid = self._buf.size
        if valid == 0:
            return np.zeros(0, dtype=np.float32)
        pad = np.zeros(FRAME, dtype=np.float32)
        pad[:valid] = self._buf
        self._buf = np.zeros(0, dtype=np.float32)
        return self._run_frames(pad)[:valid]

    def close(self) -> None:
        if getattr(self, "_lib", None) is not None:
            self._lib.fe_free()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:  # noqa: BLE001 — best-effort cleanup
            pass
