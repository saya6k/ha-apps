"""Unit tests for NemoCStream mel-delta feeding (_mel_done fix).

These tests verify that accept_audio() feeds only NEW mel frames to the
encoder on each call, not all frames from the beginning. This prevents the
RNN-T looping artifact where duplicate encoder frames caused the decoder to
re-emit the full sequence on every chunk.

The C library is mocked throughout — no model binary required.
"""

from __future__ import annotations

import ctypes
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from wyoming_nemotron_asr_c.engine import NemoCStream

_N_MELS = 128
_FAKE_CTX = ctypes.c_void_p(1)
_FAKE_RNNT = ctypes.c_void_p(2)
_FAKE_ENC = ctypes.c_void_p(3)


def _make_engine(frame_sizes: list[int]) -> tuple[MagicMock, list[np.ndarray]]:
    """Return a mocked NemoCEngine whose mel spectrogram returns successive sizes.

    frame_sizes: cumulative mel frame counts returned on successive accept_audio calls.
    Returns (engine_mock, list_of_mel_arrays) — keep mel arrays alive to prevent GC.
    """
    engine = MagicMock()
    engine._n_mels = _N_MELS
    engine._ctx = _FAKE_CTX

    mel_arrays: list[np.ndarray] = [
        np.zeros((_N_MELS, n), dtype=np.float32) for n in frame_sizes
    ]
    call_idx: list[int] = [0]

    def _fake_mel(ctx, samples, n_samples, out_frames_byref):
        i = call_idx[0]
        call_idx[0] += 1
        if i >= len(frame_sizes):
            return ctypes.c_void_p(0).value
        # Write frame count to the byref c_int (CPython CArgObject._obj).
        out_frames_byref._obj.value = frame_sizes[i]
        arr = mel_arrays[i]
        return ctypes.cast(
            arr.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), ctypes.c_void_p
        ).value

    engine._lib.nemo_mel_spectrogram.side_effect = _fake_mel
    engine._lib.nemo_rnnt_stream_create.return_value = _FAKE_RNNT
    engine._lib.nemo_encoder_stream_create.return_value = _FAKE_ENC

    return engine, mel_arrays


def _make_stream(engine: MagicMock) -> NemoCStream:
    """Instantiate NemoCStream bypassing __init__ (which calls nemo_rnnt_stream_create)."""
    stream = NemoCStream.__new__(NemoCStream)
    stream._e = engine
    stream._prompt_id = 101
    stream._audio = np.zeros(0, dtype=np.float32)
    stream._last_emitted = ""
    stream._final_text = None
    stream._rnnt = _FAKE_RNNT
    stream._enc = None
    stream._mel_done = 0
    return stream


class TestMelDoneInit(unittest.TestCase):
    """_mel_done should start at zero."""

    def test_mel_done_starts_at_zero(self):
        engine, _ = _make_engine([])
        stream = _make_stream(engine)
        self.assertEqual(stream._mel_done, 0)


class TestMelDoneDeltaFeeding(unittest.TestCase):
    """accept_audio() must feed only new (delta) mel frames to the encoder."""

    @patch("wyoming_nemotron_asr_c.engine._libc")
    def test_first_call_feeds_all_frames(self, _mock_libc):
        engine, _ = _make_engine([60])
        stream = _make_stream(engine)

        fed: list[int] = []
        stream._feed_encoder = lambda mel, n: fed.append(n)

        stream.accept_audio(np.zeros(8000, dtype=np.float32))

        self.assertEqual(stream._mel_done, 60)
        self.assertEqual(fed, [60])

    @patch("wyoming_nemotron_asr_c.engine._libc")
    def test_second_call_feeds_only_delta(self, _mock_libc):
        engine, _ = _make_engine([60, 90])
        stream = _make_stream(engine)

        fed: list[int] = []
        stream._feed_encoder = lambda mel, n: fed.append(n)

        stream.accept_audio(np.zeros(8000, dtype=np.float32))
        stream.accept_audio(np.zeros(4000, dtype=np.float32))

        self.assertEqual(stream._mel_done, 90)
        # Second call must feed only 30 frames (delta: 90 - 60), not 90.
        self.assertEqual(fed, [60, 30])

    @patch("wyoming_nemotron_asr_c.engine._libc")
    def test_no_feed_when_mel_count_unchanged(self, _mock_libc):
        """If the mel frame count doesn't grow, the encoder must not be called."""
        engine, _ = _make_engine([60, 60])
        stream = _make_stream(engine)

        fed: list[int] = []
        stream._feed_encoder = lambda mel, n: fed.append(n)

        stream.accept_audio(np.zeros(8000, dtype=np.float32))
        stream.accept_audio(np.zeros(1, dtype=np.float32))

        self.assertEqual(stream._mel_done, 60)
        self.assertEqual(len(fed), 1)  # no duplicate feed

    @patch("wyoming_nemotron_asr_c.engine._libc")
    def test_mel_done_monotonically_increases(self, _mock_libc):
        """_mel_done must never decrease between calls."""
        sizes = [40, 80, 120, 160]
        engine, _ = _make_engine(sizes)
        stream = _make_stream(engine)
        stream._feed_encoder = lambda mel, n: None

        prev = 0
        for _ in sizes:
            stream.accept_audio(np.zeros(4000, dtype=np.float32))
            self.assertGreaterEqual(stream._mel_done, prev)
            prev = stream._mel_done

        self.assertEqual(stream._mel_done, 160)


if __name__ == "__main__":
    unittest.main()
