"""ctypes bridge to parakeet.cpp's flat C API (libparakeet + ggml).

The model is loaded ONCE into a resident context (no per-utterance reload —
the key to staying light on Pi/N100), then each utterance is transcribed from
in-memory PCM via `parakeet_capi_transcribe_pcm_lang`. Buffered (not the live
stream API): one call per utterance gives clean output identical to the CLI and
is faster than chunked feeding.

C API (include/parakeet_capi.h, ABI v4):
  parakeet_capi_load(gguf_path) -> ctx
  parakeet_capi_transcribe_pcm_lang(ctx, float* pcm, n, sr, decoder, lang) -> malloc'd UTF-8
  parakeet_capi_free_string(p) / parakeet_capi_last_error(ctx)
Returned strings are malloc'd and freed with parakeet_capi_free_string.
"""
from __future__ import annotations

import ctypes
import glob
import logging
import os
import re
from ctypes import POINTER, c_char_p, c_float, c_int, c_void_p
from typing import Optional

import numpy as np

from .const import SAMPLE_RATE, resolve_lang

_LOGGER = logging.getLogger(__name__)

# Strip the model's inline language-tag tokens (e.g. <ko-KR>, <en-US>) and any
# surrounding whitespace from the transcript.
_TAG_RE = re.compile(r"\s*<[^>]*>\s*")


class ParakeetASR:
    def __init__(self, lib_dir: str, gguf_path: str) -> None:
        # ggml shared libs must be resolvable before libparakeet; load them
        # global so libparakeet's undefined symbols bind.
        for g in sorted(glob.glob(os.path.join(lib_dir, "libggml*.so*"))):
            try:
                ctypes.CDLL(g, mode=ctypes.RTLD_GLOBAL)
            except OSError as err:  # noqa: BLE001 - some are symlinks/variants
                _LOGGER.debug("skip %s: %s", g, err)

        lib_path = os.path.join(lib_dir, "libparakeet.so")
        self._lib = L = ctypes.CDLL(lib_path)

        L.parakeet_capi_abi_version.restype = c_int
        L.parakeet_capi_load.restype = c_void_p
        L.parakeet_capi_load.argtypes = [c_char_p]
        L.parakeet_capi_free.argtypes = [c_void_p]
        L.parakeet_capi_transcribe_pcm_lang.restype = c_void_p
        L.parakeet_capi_transcribe_pcm_lang.argtypes = [
            c_void_p, POINTER(c_float), c_int, c_int, c_int, c_char_p
        ]
        L.parakeet_capi_free_string.argtypes = [c_void_p]
        L.parakeet_capi_last_error.restype = c_char_p
        L.parakeet_capi_last_error.argtypes = [c_void_p]

        self.abi = int(L.parakeet_capi_abi_version())
        self.sample_rate = SAMPLE_RATE
        self.ctx = L.parakeet_capi_load(gguf_path.encode("utf-8"))
        if not self.ctx:
            raise RuntimeError(f"parakeet_capi_load failed for {gguf_path}")
        _LOGGER.info("Engine ready: parakeet.cpp C ABI v%d, model resident", self.abi)

    def transcribe(self, audio: np.ndarray, language: Optional[str] = None) -> str:
        """audio: float32 mono [-1, 1] @ 16 kHz. language: locale ('ko', 'auto')."""
        a = np.ascontiguousarray(audio, dtype=np.float32)
        if a.size == 0:
            return ""
        # Resolve a dropdown label ("한국어") / None to the locale parakeet
        # expects ("ko" / "auto"). Idempotent for already-resolved locales.
        lang = resolve_lang(language).encode("utf-8")
        p = self._lib.parakeet_capi_transcribe_pcm_lang(
            self.ctx, a.ctypes.data_as(POINTER(c_float)), a.size,
            SAMPLE_RATE, 0, lang,
        )
        if not p:
            err = self._lib.parakeet_capi_last_error(self.ctx)
            raise RuntimeError(
                "parakeet transcribe failed: "
                + (err.decode("utf-8", "replace") if err else "unknown")
            )
        try:
            text = ctypes.cast(p, c_char_p).value.decode("utf-8", "replace")
        finally:
            self._lib.parakeet_capi_free_string(p)
        return " ".join(_TAG_RE.sub(" ", text).split())

    def warmup(self, language: Optional[str] = None, seconds: float = 1.0) -> None:
        self.transcribe(np.zeros(int(SAMPLE_RATE * seconds), dtype=np.float32), language)
