"""ctypes bridge to nemotron-asr-streaming.c (libnemotron_asr.so).

The model is loaded ONCE into a resident context (nemo_load), then each
connection creates its own encoder + decoder streams. Audio is fed
incrementally: the mel spectrogram is recomputed on each chunk (cheap, <1% of
inference time), fed through the encoder chunk callback to the RNN-T decoder,
and partial text is available via nemo_rnnt_stream_text().
"""

from __future__ import annotations

import ctypes
import logging
import os
import re
from ctypes import CFUNCTYPE, POINTER, c_char_p, c_float, c_int, c_int32, c_size_t, c_void_p
from typing import Optional

import numpy as np

from .const import SAMPLE_RATE, CHUNK_CHOICES, DEFAULT_CHUNK_SIZE, resolve_lang

_LOGGER = logging.getLogger(__name__)

# Strip the model's inline language-tag tokens (e.g. <ko-KR>, <en-US>).
_TAG_RE = re.compile(r"\s*<[^>]*>\s*")

# ---- C callback signatures ----
# int (*nemo_encoder_chunk_cb)(void *user, const float *enc, int enc_frames);
_ENCODER_CHUNK_CB = CFUNCTYPE(c_int, c_void_p, POINTER(c_float), c_int)

# libc free() for malloc'd float arrays returned by nemo_mel_spectrogram and
# nemo_encoder_forward.
_libc = ctypes.CDLL(None)
_libc.free.argtypes = [c_void_p]


class NemoCStream:
    """Per-connection streaming state.

    Holds the audio buffer, encoder stream, RNN-T stream, and tracks emitted
    text for delta computation. Created by :meth:`NemoCEngine.create_stream`.
    """

    def __init__(self, engine: NemoCEngine, prompt_id: int) -> None:
        self._e = engine
        self._prompt_id = prompt_id
        self._audio = np.zeros(0, dtype=np.float32)
        self._tokens: list[int] = []
        self._last_emitted = ""
        self._final_text: str | None = None  # cached after finalize() frees rnnt

        # Create the RNN-T stream (decoder side — we feed encoder output to it).
        self._rnnt: c_void_p | None = engine._lib.nemo_rnnt_stream_create(engine._ctx)
        if not self._rnnt:
            raise RuntimeError("nemo_rnnt_stream_create failed")

        # Encoder stream is created lazily on first accept_audio() because we
        # need to know mel frame count for the callback wiring.
        self._enc: c_void_p | None = None
        self._mel_done = 0  # total mel frames fed to encoder so far

    def accept_audio(self, samples: np.ndarray) -> None:
        """Feed new float32 audio samples. Updates partial transcript."""
        a = np.ascontiguousarray(samples, dtype=np.float32)
        if a.size == 0:
            return
        self._audio = np.concatenate([self._audio, a])

        # Recompute the full mel spectrogram (cheap; <1% of inference time).
        n_samples = self._audio.shape[0]
        out_frames = c_int(0)
        mel_ptr = self._e._lib.nemo_mel_spectrogram(
            self._e._ctx,
            self._audio.ctypes.data_as(POINTER(c_float)),
            n_samples,
            ctypes.byref(out_frames),
        )
        if not mel_ptr:
            _LOGGER.error("nemo_mel_spectrogram failed")
            return
        try:
            mel_frames = out_frames.value
            if mel_frames == 0:
                return
            # Cast to numpy array (zero-copy view into C allocation — read-only).
            mel_shape = (self._e._n_mels, mel_frames)
            mel_arr = np.ctypeslib.as_array(
                ctypes.cast(mel_ptr, POINTER(c_float)),
                shape=mel_shape,
            ).copy()  # copy so we can free the C buffer

            # Feed only new mel frames (delta since last call).
            # ascontiguousarray is required: column slicing produces a strided
            # view that ctypes passes as a raw pointer, causing the C function
            # to read wrong row data for every row after the first.
            new_mel = np.ascontiguousarray(mel_arr[:, self._mel_done:])
            if new_mel.shape[1] > 0:
                self._feed_encoder(new_mel, new_mel.shape[1])
            self._mel_done = mel_frames
        finally:
            _libc.free(mel_ptr)

    def _feed_encoder(self, mel: np.ndarray, total_frames: int) -> None:
        """Feed mel frames through encoder chunks, into the RNN-T decoder."""
        engine = self._e
        e = engine._lib

        # Build the encoder chunk callback — feeds encoder output to the RNN-T
        # stream and accumulates tokens.
        rnnt_ptr = self._rnnt

        @_ENCODER_CHUNK_CB
        def _on_encoder_chunk(user: c_void_p, enc_ptr, enc_frames: c_int) -> c_int:
            n = enc_frames
            if n <= 0:
                return 0
            # Feed to RNN-T stream.
            ret = e.nemo_rnnt_stream_accept(
                engine._ctx, rnnt_ptr, enc_ptr, n
            )
            if ret != 0:
                return ret
            return 0

        # The encoder takes the full mel and calls _on_encoder_chunk once per
        # chunk with the encoded frames. This uses the persistent encoder stream
        # (created lazily) so caches carry across calls.
        if self._enc is None:
            self._enc = e.nemo_encoder_stream_create(engine._ctx)
            if not self._enc:
                raise RuntimeError("nemo_encoder_stream_create failed")

        # nemo_encoder_forward_chunks processes ALL mel frames and calls the
        # callback for each chunk. The encoder stream handles chunking
        # internally based on ctx->att_right.
        ret = e.nemo_encoder_forward_chunks(
            engine._ctx, mel.ctypes.data_as(POINTER(c_float)), total_frames,
            _on_encoder_chunk, None,
        )
        if ret != 0:
            _LOGGER.error("nemo_encoder_forward_chunks returned %d", ret)

    def text(self) -> str:
        """Return the current partial transcript (language tags stripped)."""
        # After finalize() frees the rnnt stream, return the cached final text.
        if self._rnnt is not None:
            raw = self._e._lib.nemo_rnnt_stream_text(self._rnnt)
            if raw:
                return " ".join(_TAG_RE.sub(" ", raw.decode("utf-8", "replace")).split())
        return self._final_text or ""

    def finalize(self) -> None:
        """Finish the RNN-T stream and return the final text."""
        if self._rnnt is None:
            return
        # nemo_rnnt_stream_finish frees the rnnt stream internally and returns
        # a malloc'd char* with the final text (ownership transferred to caller).
        p = self._e._lib.nemo_rnnt_stream_finish(self._rnnt)
        self._rnnt = None  # already freed by nemo_rnnt_stream_finish
        if p:
            try:
                raw = ctypes.cast(p, ctypes.c_char_p).value
                if raw:
                    decoded = raw.decode("utf-8", "replace")
                    self._final_text = " ".join(_TAG_RE.sub(" ", decoded).split())
                else:
                    self._final_text = ""
            finally:
                _libc.free(p)
        else:
            self._final_text = ""

    def close(self) -> None:
        """Free C stream objects."""
        e = self._e._lib
        if self._enc is not None:
            e.nemo_encoder_stream_free(self._enc)
            self._enc = None
        if self._rnnt is not None:
            e.nemo_rnnt_stream_free(self._rnnt)
            self._rnnt = None

    def __del__(self) -> None:
        self.close()


class NemoCEngine:
    """Shared engine holding the loaded Nemotron model context.

    One instance per process. Creates per-connection NemoCStream objects.
    """

    def __init__(
        self,
        lib_dir: str,
        bin_path: str,
        att_right: int = 3,
        tokenizer_path: str | None = None,
    ) -> None:
        """Load libnemotron_asr.so and the model .bin file.

        Args:
            lib_dir: Directory containing libnemotron_asr.so.
            bin_path: Path to the converted .bin model file.
            att_right: Encoder right-context in frames (0-13). Controls the
                       streaming lookahead / accuracy-speed trade-off.
            tokenizer_path: Path to SentencePiece tokenizer.model for hotword
                            tokenization. Extracted from the .nemo at boot.
        """
        lib_path = os.path.join(lib_dir, "libnemotron_asr.so")
        self._lib = L = ctypes.CDLL(lib_path)

        # ---- Lifecycle ----
        L.nemo_load.restype = c_void_p
        L.nemo_load.argtypes = [c_char_p]
        L.nemo_free.argtypes = [c_void_p]
        L.nemo_set_language.restype = c_int
        L.nemo_set_language.argtypes = [c_void_p, c_char_p]

        # ---- Mel ----
        L.nemo_mel_spectrogram.restype = c_void_p
        L.nemo_mel_spectrogram.argtypes = [
            c_void_p, POINTER(c_float), c_int, POINTER(c_int),
        ]

        # ---- Encoder streaming ----
        L.nemo_encoder_stream_create.restype = c_void_p
        L.nemo_encoder_stream_create.argtypes = [c_void_p]
        L.nemo_encoder_forward_chunks.restype = c_int
        L.nemo_encoder_forward_chunks.argtypes = [
            c_void_p, POINTER(c_float), c_int, _ENCODER_CHUNK_CB, c_void_p,
        ]
        L.nemo_encoder_stream_free.argtypes = [c_void_p]

        # ---- Decoder (RNN-T) streaming ----
        L.nemo_rnnt_stream_create.restype = c_void_p
        L.nemo_rnnt_stream_create.argtypes = [c_void_p]
        L.nemo_rnnt_stream_accept.restype = c_int
        L.nemo_rnnt_stream_accept.argtypes = [
            c_void_p, c_void_p, POINTER(c_float), c_int,
        ]
        L.nemo_rnnt_stream_text.restype = c_char_p
        L.nemo_rnnt_stream_text.argtypes = [c_void_p]
        L.nemo_rnnt_stream_text_len.restype = c_size_t
        L.nemo_rnnt_stream_text_len.argtypes = [c_void_p]
        L.nemo_rnnt_stream_finish.restype = c_void_p
        L.nemo_rnnt_stream_finish.argtypes = [c_void_p]
        L.nemo_rnnt_stream_free.argtypes = [c_void_p]

        # ---- Threads ----
        L.nemo_set_threads.argtypes = [c_int]
        L.nemo_get_threads.restype = c_int

        # ---- Streaming lookahead ----
        L.nemo_set_att_right.argtypes = [c_void_p, c_int]
        L.nemo_set_att_right.restype = None  # void — must be explicit for ctypes
        L.nemo_get_att_right.restype = c_int
        L.nemo_get_att_right.argtypes = [c_void_p]

        # ---- Hotword biasing ----
        L.nemo_set_hotwords.argtypes = [
            c_void_p, POINTER(c_int32), POINTER(c_int), c_int, c_float,
        ]
        L.nemo_set_hotwords.restype = None

        # ---- Load model ----
        self._ctx: c_void_p = L.nemo_load(bin_path.encode("utf-8"))
        if not self._ctx:
            raise RuntimeError(f"nemo_load failed for {bin_path}")

        # Set streaming lookahead.
        self._set_att_right(att_right)

        # Cache encoder output dimension (1024 for Nemotron).
        self._n_mels = 128
        self._n_enc = 1024

        # Load SentencePiece tokenizer for hotword phrase tokenization.
        self._sp: object | None = None
        if tokenizer_path and os.path.exists(tokenizer_path):
            try:
                import sentencepiece as spm
                proc = spm.SentencePieceProcessor()
                if not proc.Load(tokenizer_path):
                    _LOGGER.warning(
                        "Tokenizer Load() returned False from %s — hotwords disabled",
                        tokenizer_path,
                    )
                else:
                    self._sp = proc
                    _LOGGER.info("Tokenizer loaded: %s", tokenizer_path)
            except Exception:
                _LOGGER.warning(
                    "Failed to load tokenizer from %s — hotwords disabled",
                    tokenizer_path,
                )

        _LOGGER.info(
            "Engine ready: %s loaded (att_right=%d, threads=%d)",
            bin_path, att_right, L.nemo_get_threads(),
        )

    def _set_att_right(self, value: int) -> None:
        """Set the encoder right-context (streaming lookahead)."""
        self._lib.nemo_set_att_right(self._ctx, value)
        actual = self._lib.nemo_get_att_right(self._ctx)
        _LOGGER.info("att_right=%d (requested %d)", actual, value)

    def set_hotwords(self, phrases: list[str], boost: float) -> None:
        """Tokenize phrases and pass token IDs to the C runtime.

        Hotwords are applied globally to the shared model context.  Call once
        at boot; subsequent calls replace the previous phrase list.

        Args:
            phrases: List of text phrases (e.g. device names). Must be
                     lowercase for Nemotron (which outputs lowercase).
            boost: Logit bonus for matching tokens during greedy decode.
        """
        if not phrases or not self._sp:
            return
        ids_flat: list[int] = []
        lens: list[int] = []
        for phrase in phrases:
            p = phrase.strip()
            if not p:
                continue
            ids = list(self._sp.EncodeAsIds(p))  # type: ignore[union-attr]
            if ids:
                ids_flat.extend(ids)
                lens.append(len(ids))
        if not lens:
            return
        ids_arr = (ctypes.c_int32 * len(ids_flat))(*ids_flat)
        lens_arr = (ctypes.c_int * len(lens))(*lens)
        self._lib.nemo_set_hotwords(
            self._ctx, ids_arr, lens_arr, len(lens), ctypes.c_float(boost),
        )
        _LOGGER.info(
            "Hotwords set: %d phrase(s) (%d total tokens), boost=%.1f",
            len(lens), len(ids_flat), boost,
        )

    def create_stream(self, language: str | None = None) -> NemoCStream:
        """Create a new streaming session for one utterance.

        Args:
            language: Wyoming language code (e.g. "ko", "en") or None for auto.
        """
        lang_code = resolve_lang(language)
        prompt_id = 101  # default: auto
        # Try to resolve via nemo_set_language (side-effect on ctx, but we only
        # have one ctx shared across streams — the language is per-utterance).
        # For now, we set it on the shared ctx before creating the stream.
        # TODO: make language truly per-stream (needs ctx per stream or API change).
        ret = self._lib.nemo_set_language(self._ctx, lang_code.encode("utf-8"))
        if ret == 0:
            prompt_id = 101  # keep auto as fallback
        return NemoCStream(self, prompt_id)

    def set_threads(self, n: int) -> None:
        """Set the number of worker threads."""
        self._lib.nemo_set_threads(n)

    def warmup(self, language: str | None = None, seconds: float = 1.0) -> None:
        """Run a dummy inference to fault model weights in from disk."""
        stream = self.create_stream(language)
        try:
            silence = np.zeros(int(SAMPLE_RATE * seconds), dtype=np.float32)
            stream.accept_audio(silence)
            stream.finalize()
            _LOGGER.info("Warmup complete: %s", stream.text() or "<empty>")
        finally:
            stream.close()

    def close(self) -> None:
        """Free the model context."""
        if self._ctx is not None:
            self._lib.nemo_free(self._ctx)
            self._ctx = None

    def __del__(self) -> None:
        self.close()
