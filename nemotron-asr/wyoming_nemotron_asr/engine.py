"""ONNX inference for the Nemotron cache-aware streaming Conformer-Transducer.

Two graphs (see the model's config.json + the ONNX I/O signatures):

  encoder.onnx
    in:  processed_signal[B,128,T], processed_signal_length[B],
         cache_last_channel[24,1,56,1024], cache_last_time[24,1,1024,8],
         cache_last_channel_len[1], prompt_index[B]
    out: encoded[B,1024,T'], encoded_len[B], <three *_next caches>

  decoder_joint.onnx  (fused RNN-T prediction LSTM + joint network)
    in:  encoder_outputs[B,1024,T], targets[B,U] int32, target_length[B] int32,
         input_states_1[2,B,640], input_states_2[2,B,640]
    out: outputs[...,13088] logits, prednet_lengths, output_states_1/2

We run it utterance-buffered: accumulate audio, then on finalize compute the
full log-mel and replay it through the encoder in 56-mel-frame chunks (the
cache makes chunked == true-streaming), collect all encoded frames, then do a
standard greedy RNN-T decode. supports_transcript_streaming is therefore False.

Streaming constants are read from config.json, cross-checked against the
Microsoft Olive export recipe:
  chunk_mel_frames   = chunk_size_output_frames * subsampling_factor   (56)
  static_mel_frames  = config.test_input.mel_shape[-1]                 (65)
  pre_encode_frames  = static_mel_frames - chunk_mel_frames            (9)
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import List, Optional

import numpy as np

from .featurizer import MelFeaturizer

_LOGGER = logging.getLogger(__name__)


class NemotronASR:
    def __init__(
        self,
        model_dir: str,
        num_threads: int = 4,
        hotwords: Optional[List[str]] = None,
        hotword_boost: float = 2.0,
    ) -> None:
        import onnxruntime as ort
        import sentencepiece as spm

        self.model_dir = model_dir
        with open(os.path.join(model_dir, "config.json"), encoding="utf-8") as f:
            cfg = self.config = json.load(f)

        self.sample_rate = int(cfg["sample_rate"])
        self.n_mels = int(cfg["n_mels"])
        self.subsampling = int(cfg["subsampling_factor"])
        self.blank_id = int(cfg["blank_id"])
        self.prompt_dictionary = cfg["prompt_dictionary"]

        pp = cfg["preprocessor"]
        self.featurizer = MelFeaturizer(
            sample_rate=self.sample_rate,
            n_mels=self.n_mels,
            n_fft=int(pp["n_fft"]),
            win_length=int(round(pp["window_size"] * self.sample_rate)),
            hop_length=int(round(pp["window_stride"] * self.sample_rate)),
            preemph=float(pp["preemph"]),
        )

        self.chunk_mel = int(cfg["chunk_size_output_frames"]) * self.subsampling  # 56
        self.static_mel = int(cfg["test_input"]["mel_shape"][-1])                 # 65
        self.pre_encode = self.static_mel - self.chunk_mel                        # 9

        cs = cfg["cache_shapes"]
        self._cache_ch_shape = tuple(cs["cache_last_channel"])
        self._cache_tm_shape = tuple(cs["cache_last_time"])

        so = ort.SessionOptions()
        so.intra_op_num_threads = max(1, num_threads)
        so.inter_op_num_threads = 1
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        providers = ["CPUExecutionProvider"]
        self.enc = ort.InferenceSession(
            os.path.join(model_dir, "encoder.onnx"), so, providers=providers
        )
        self.dec = ort.InferenceSession(
            os.path.join(model_dir, "decoder_joint.onnx"), so, providers=providers
        )

        self.sp = spm.SentencePieceProcessor()
        self.sp.Load(os.path.join(model_dir, "tokenizer.model"))

        # The vocab includes meta tokens (language tags like <en-US>, <bg-BG>,
        # plus <unk> etc.). The model emits the active language tag, which would
        # otherwise render as literal text — suppress all "<...>" pieces.
        tag = re.compile(r"^<[^>]*>$")
        self._suppress_ids = {
            i for i in range(self.sp.GetPieceSize()) if tag.match(self.sp.IdToPiece(i))
        }

        # Hotword (contextual) biasing: each phrase -> its SentencePiece token
        # ids. During greedy decode, tokens that continue an active hotword get
        # a logit bonus. Greedy biasing is best-effort (it can only flip a
        # near-tie, and relies on the model segmenting the word the same way).
        self.hotword_boost = float(hotword_boost)
        self.hotword_seqs: List[List[int]] = []
        for phrase in hotwords or []:
            ids = list(self.sp.EncodeAsIds(phrase))
            if ids:
                self.hotword_seqs.append(ids)

        self.max_symbols_per_frame = 10
        if self.hotword_seqs:
            _LOGGER.info(
                "Hotword biasing: %d phrase(s), boost=%.1f",
                len(self.hotword_seqs), self.hotword_boost,
            )
        _LOGGER.info(
            "Engine ready: onnxruntime=%s intra_op_threads=%d providers=%s",
            ort.__version__, so.intra_op_num_threads, self.enc.get_providers(),
        )
        _LOGGER.info(
            "Model: chunk_mel=%d static_mel=%d pre_encode=%d blank=%d vocab=%d",
            self.chunk_mel, self.static_mel, self.pre_encode, self.blank_id,
            self.sp.GetPieceSize(),
        )

    # -- language prompt -----------------------------------------------------

    def resolve_prompt(self, language: Optional[str]) -> int:
        """Map a language to a prompt slot.

        Accepts a dropdown label ('한국어', 'Auto'), an HA pipeline ISO code
        ('ko'), or a locale ('ko-KR') — in that resolution order.
        """
        from .const import NAME_TO_PROMPT_KEY

        if not language:
            return self.prompt_dictionary.get("auto", 0)
        key = NAME_TO_PROMPT_KEY.get(language, language)
        for k in (key, key.replace("_", "-"), key.split("-")[0]):
            if k in self.prompt_dictionary:
                return int(self.prompt_dictionary[k])
        # Bare 2-letter ISO with no bare entry (e.g. HA sends 'ja'/'th'): fall
        # back to the first matching locale slot ('ja-JP', 'th-TH').
        base = key.split("-")[0]
        for dk, dv in self.prompt_dictionary.items():
            if dk.split("-")[0] == base:
                return int(dv)
        return self.prompt_dictionary.get("auto", 0)

    # -- streaming -----------------------------------------------------------

    def create_stream(self, language: Optional[str] = None) -> "NemotronStream":
        """Open a per-connection decode session (own caches + RNN-T state)."""
        return NemotronStream(self, self.resolve_prompt(language))

    def transcribe(self, audio: np.ndarray, language: Optional[str] = None) -> str:
        """One-shot offline convenience (used by tests / non-streaming clients)."""
        stream = self.create_stream(language)
        stream.accept_audio(np.asarray(audio, dtype=np.float32))
        stream.finalize()
        return stream.text()

    def warmup(self, language: Optional[str] = None, seconds: float = 1.5) -> None:
        """Run one dummy utterance so the first real request isn't a cold start.

        First inference pays ORT kernel warm-up + faults the (large) weights in
        from disk — on a Pi that's several seconds. Doing it at boot moves that
        cost off the user's first command.
        """
        t0 = time.monotonic()
        self.transcribe(np.zeros(int(self.sample_rate * seconds), dtype=np.float32),
                        language)
        _LOGGER.info("Warm-up done in %.2fs", time.monotonic() - t0)


class NemotronStream:
    """Stateful streaming decode for one connection.

    The ONNX sessions / tokenizer / featurizer are shared (read-only) via the
    parent engine; everything mutable (encoder caches, RNN-T LSTM state, the
    emitted-token list, the audio buffer) lives here.

    Audio is buffered; `accept_audio()` feeds every *stable* 56-mel-frame chunk
    (frames whose STFT window no longer depends on future samples) through the
    encoder + greedy decode, so partial text is available mid-utterance.
    `finalize()` flushes the remaining frames (including a zero-padded partial
    chunk and the legitimate end-padding). Feeding chunked with the persistent
    cache is equivalent to a single offline pass over the whole utterance.
    """

    def __init__(self, engine: NemotronASR, prompt_index: int) -> None:
        self.e = engine
        self.prompt = np.array([prompt_index], dtype=np.int64)

        self.cache_ch = np.zeros(engine._cache_ch_shape, dtype=np.float32)
        self.cache_tm = np.zeros(engine._cache_tm_shape, dtype=np.float32)
        self.cache_len = np.zeros((1,), dtype=np.int64)

        self.h = np.zeros((2, 1, 640), dtype=np.float32)  # LSTM hidden
        self.c = np.zeros((2, 1, 640), dtype=np.float32)  # LSTM cell
        self.last = engine.blank_id  # blank == SOS (zero embedding)

        self.audio = np.zeros(0, dtype=np.float32)
        self.next_chunk = 0  # index of the next 56-frame chunk to feed
        self.tokens: List[int] = []  # emitted, language-tag tokens filtered out
        self._mel = np.zeros((engine.n_mels, 0), dtype=np.float32)  # cached stable frames
        self._mel_done = 0  # number of frames in self._mel
        self._hot_active: List[tuple] = []  # active hotword partial matches

    # -- mel-frame stability bookkeeping ------------------------------------

    def _stable_frames(self, n_samples: int) -> int:
        """How many center-padded mel frames are final (independent of future audio).

        featurizer reflect-pads n_fft//2 at the front, so frame i covers original
        samples [i*hop - pad, i*hop - pad + n_fft) == up to i*hop + pad. Frame i is
        final once n_samples >= i*hop + pad (no reliance on end reflect-padding).
        """
        pad = self.e.featurizer.n_fft // 2
        hop = self.e.featurizer.hop_length
        if n_samples < self.e.featurizer.n_fft:
            return 0
        return (n_samples - pad) // hop + 1

    def _feed(self, mel: np.ndarray, limit: int, allow_partial: bool) -> None:
        cm, pre = self.e.chunk_mel, self.e.pre_encode
        total = mel.shape[1]
        while True:
            start = self.next_chunk * cm
            if start >= limit:
                break
            end = start + cm
            if not allow_partial and end > limit:
                break
            new = mel[:, start : min(end, total)]
            valid = new.shape[1]
            if valid == 0:
                break

            left_avail = min(pre, start)
            window = np.zeros((self.e.n_mels, self.e.static_mel), dtype=np.float32)
            if left_avail:
                window[:, pre - left_avail : pre] = mel[:, start - left_avail : start]
            window[:, pre : pre + valid] = new

            outs = self.e.enc.run(
                None,
                {
                    "processed_signal": window[None, :, :],
                    "processed_signal_length": np.array([pre + valid], dtype=np.int64),
                    "cache_last_channel": self.cache_ch,
                    "cache_last_time": self.cache_tm,
                    "cache_last_channel_len": self.cache_len,
                    "prompt_index": self.prompt,
                },
            )
            encoded, encoded_len, self.cache_ch, self.cache_tm, self.cache_len = outs
            n = int(encoded_len[0])
            if n > 0:
                self._decode(encoded[0, :, :n])
            self.next_chunk += 1

    def _decode(self, encoded: np.ndarray) -> None:
        e, tlen = self.e, np.array([1], dtype=np.int32)
        seqs, boost = e.hotword_seqs, e.hotword_boost
        for t in range(encoded.shape[1]):
            f = encoded[:, t : t + 1][None].astype(np.float32)  # [1, 1024, 1]
            for _ in range(e.max_symbols_per_frame):
                logits, _plen, h_new, c_new = e.dec.run(
                    None,
                    {
                        "encoder_outputs": f,
                        "targets": np.array([[self.last]], dtype=np.int32),
                        "target_length": tlen,
                        "input_states_1": self.h,
                        "input_states_2": self.c,
                    },
                )
                flat = np.reshape(logits, (-1,))
                if seqs:
                    # Boost tokens that start a hotword or continue an active one.
                    flat = flat.copy()
                    expected = {seq[0] for seq in seqs}
                    expected.update(seqs[si][pos] for si, pos in self._hot_active)
                    for tid in expected:
                        flat[tid] += boost
                k = int(np.argmax(flat))
                if k == e.blank_id:
                    break  # blank emits no symbol; active hotword matches persist
                # Advance prediction state for every emitted token (incl. the
                # model's language-tag tokens), but keep tags out of the text.
                if k not in e._suppress_ids:
                    self.tokens.append(k)
                if seqs:
                    self._advance_hotwords(k)
                self.last = k
                self.h, self.c = h_new, c_new

    def _advance_hotwords(self, k: int) -> None:
        seqs = self.e.hotword_seqs
        nxt = [(si, pos + 1) for si, pos in self._hot_active
               if seqs[si][pos] == k and pos + 1 < len(seqs[si])]
        nxt += [(si, 1) for si, seq in enumerate(seqs) if seq[0] == k and len(seq) > 1]
        self._hot_active = nxt

    # -- public --------------------------------------------------------------

    def _extend_mel(self, upto: int) -> None:
        """Grow the cached stable-frame mel to `upto` frames (FFT only new ones)."""
        if upto <= self._mel_done:
            return
        new = self.e.featurizer.logmel_frames(self.audio, self._mel_done, upto)
        self._mel = np.concatenate([self._mel, new], axis=1)
        self._mel_done = upto

    def accept_audio(self, samples: np.ndarray) -> None:
        self.audio = np.concatenate([self.audio, np.asarray(samples, dtype=np.float32)])
        stable = self._stable_frames(self.audio.shape[0])
        if stable < (self.next_chunk + 1) * self.e.chunk_mel:
            return  # not enough new stable frames for another full chunk yet
        self._extend_mel(stable)
        self._feed(self._mel, limit=stable, allow_partial=False)

    def finalize(self) -> None:
        if self.audio.size == 0:
            return
        # The tail frames legitimately use end reflect-padding, so recompute the
        # full mel once; cached stable frames are identical, indexing is absolute.
        mel = self.e.featurizer(self.audio)
        self._feed(mel, limit=mel.shape[1], allow_partial=True)

    def text(self) -> str:
        return " ".join(self.e.sp.DecodeIds(self.tokens).split())
