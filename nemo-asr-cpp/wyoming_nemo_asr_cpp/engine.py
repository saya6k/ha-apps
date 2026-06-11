"""ctypes bridge to parakeet.cpp's flat C API (libparakeet + ggml).

The model is loaded ONCE into a resident context (no per-utterance reload —
the key to staying light on Pi/N100), then each utterance is transcribed from
in-memory PCM via `parakeet_capi_transcribe_pcm_lang`. Buffered (not the live
stream API): one call per utterance gives clean output identical to the CLI and
is faster than chunked feeding.

C API (include/parakeet_capi.h, ABI v5 = v4 + the vendored hotword patch):
  parakeet_capi_load(gguf_path) -> ctx
  parakeet_capi_transcribe_pcm_lang(ctx, float* pcm, n, sr, decoder, lang) -> malloc'd UTF-8
  parakeet_capi_set_hotwords(ctx, int* ids, int* lens, n_phrases, boost)
  parakeet_capi_free_string(p) / parakeet_capi_last_error(ctx)
Returned strings are malloc'd and freed with parakeet_capi_free_string.

Hotword biasing comes from patches/0001-rnnt-hotword-biasing.patch, not
upstream — if the symbol/ABI is missing (patch dropped, upstream divergence),
hotwords are logged and ignored rather than failing the boot.
"""
from __future__ import annotations

import ctypes
import glob
import logging
import os
import re
from ctypes import POINTER, c_char_p, c_float, c_int, c_void_p
from typing import List, Optional

import numpy as np

from .const import SAMPLE_RATE, resolve_lang

_LOGGER = logging.getLogger(__name__)

# Strip the model's inline language-tag tokens (e.g. <ko-KR>, <en-US>) and any
# surrounding whitespace from the transcript.
_TAG_RE = re.compile(r"\s*<[^>]*>\s*")


class ParakeetASR:
    def __init__(
        self,
        lib_dir: str,
        gguf_path: str,
        hotwords: Optional[List[str]] = None,
        hotword_boost: float = 2.0,
    ) -> None:
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
        if hotwords:
            self._set_hotwords(gguf_path, hotwords, hotword_boost)
        _LOGGER.info("Engine ready: parakeet.cpp C ABI v%d, model resident", self.abi)

    def _set_hotwords(self, gguf_path: str, hotwords: List[str], boost: float) -> None:
        """Register hotword phrases (ctx-level; applies to every transcribe)."""
        if self.abi < 5 or not hasattr(self._lib, "parakeet_capi_set_hotwords"):
            _LOGGER.warning(
                "Hotwords configured but libparakeet ABI v%d has no hotword "
                "support (vendored patch missing?) — ignoring.", self.abi,
            )
            return
        self._lib.parakeet_capi_set_hotwords.argtypes = [
            c_void_p, POINTER(c_int), POINTER(c_int), c_int, c_float
        ]
        from .tokenizer import HotwordTokenizer

        tok = HotwordTokenizer(gguf_path)
        seqs: List[List[int]] = []
        n_phrases = 0
        for phrase in hotwords:
            variants = tok.encode_variants(phrase)
            if variants:
                seqs.extend(variants)
                n_phrases += 1
                _LOGGER.debug("Hotword %r -> %s", phrase, variants)
            else:
                _LOGGER.warning("Hotword %r not encodable; skipped", phrase)
        if not seqs:
            return
        flat = [t for s in seqs for t in s]
        ids_arr = (c_int * len(flat))(*flat)
        lens_arr = (c_int * len(seqs))(*[len(s) for s in seqs])
        self._lib.parakeet_capi_set_hotwords(
            self.ctx, ids_arr, lens_arr, len(seqs), c_float(boost)
        )
        _LOGGER.info(
            "Hotword biasing: %d phrase(s) as %d segmentation variant(s), boost=%.1f",
            n_phrases, len(seqs), boost,
        )

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
