"""Unit tests for NemoCStream's streaming cascade.

These verify that accept_audio() feeds only NEW PCM samples through the stateful
mel -> encoder -> RNN-T cascade (nemo_*_stream_accept), never the old one-shot
full-mel recompute (nemo_mel_spectrogram / nemo_encoder_forward_chunks). The C
library is mocked throughout — no model binary required.
"""

from __future__ import annotations

import ctypes
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from wyoming_nemotron_asr_c.engine import NemoCStream

_FAKE_CTX = ctypes.c_void_p(1)
_FAKE_RNNT = ctypes.c_void_p(2)
_FAKE_ENC = ctypes.c_void_p(3)
_FAKE_MEL = ctypes.c_void_p(4)


def _make_engine() -> tuple[MagicMock, dict[str, list]]:
    """Mock NemoCEngine wired so the mel->encoder->rnnt cascade actually fires.

    Returns (engine, trace) where trace records the frames seen at each stage so
    tests can assert the cascade reached the RNN-T decoder.
    """
    engine = MagicMock()
    engine._ctx = _FAKE_CTX
    L = engine._lib

    L.nemo_rnnt_stream_create.return_value = _FAKE_RNNT
    L.nemo_encoder_stream_create.return_value = _FAKE_ENC
    L.nemo_mel_stream_create.return_value = _FAKE_MEL

    trace: dict[str, list] = {"mel": [], "enc": [], "rnnt": []}

    def _mel_accept(mel_stream, samples_ptr, n_samples, final, cb, user):
        trace["mel"].append((n_samples, final))
        # Emit one mel chunk of 8 frames into the encoder callback.
        cb(None, None, 8, final)
        return 0

    def _enc_accept(ctx, enc_stream, mel_ptr, mel_frames, final, cb, user):
        trace["enc"].append((mel_frames, final))
        # Emit one encoder chunk of 2 frames into the RNN-T callback.
        cb(None, None, 2)
        return 0

    def _rnnt_accept(ctx, rnnt, enc_ptr, enc_frames):
        trace["rnnt"].append(enc_frames)
        return 0

    L.nemo_mel_stream_accept.side_effect = _mel_accept
    L.nemo_encoder_stream_accept.side_effect = _enc_accept
    L.nemo_rnnt_stream_accept.side_effect = _rnnt_accept
    return engine, trace


class TestStreamingCascade(unittest.TestCase):
    """accept_audio() must drive the stateful streaming cascade."""

    def test_accept_audio_feeds_delta_samples(self):
        engine, _ = _make_engine()
        stream = NemoCStream(engine, 101)

        stream.accept_audio(np.zeros(160, dtype=np.float32))

        call = engine._lib.nemo_mel_stream_accept.call_args
        self.assertEqual(call.args[2], 160)   # n_samples = the new chunk only
        self.assertEqual(call.args[3], 0)     # final flag = 0 mid-stream

    def test_cascade_reaches_rnnt(self):
        engine, trace = _make_engine()
        stream = NemoCStream(engine, 101)

        stream.accept_audio(np.zeros(160, dtype=np.float32))

        self.assertEqual(trace["mel"], [(160, 0)])
        self.assertEqual(trace["enc"], [(8, 0)])
        self.assertEqual(trace["rnnt"], [2])

    def test_empty_audio_is_noop(self):
        engine, _ = _make_engine()
        stream = NemoCStream(engine, 101)

        stream.accept_audio(np.zeros(0, dtype=np.float32))

        engine._lib.nemo_mel_stream_accept.assert_not_called()

    def test_no_oneshot_mel_recompute(self):
        """The removed one-shot paths must never be touched."""
        engine, _ = _make_engine()
        stream = NemoCStream(engine, 101)

        stream.accept_audio(np.zeros(160, dtype=np.float32))

        self.assertFalse(engine._lib.nemo_mel_spectrogram.called)
        self.assertFalse(engine._lib.nemo_encoder_forward_chunks.called)


class TestFinalize(unittest.TestCase):
    """finalize() must flush the cascade then finish the RNN-T stream."""

    @patch("wyoming_nemotron_asr_c.engine._libc")
    def test_finalize_flushes_with_final_flag(self, _mock_libc):
        engine, trace = _make_engine()
        engine._lib.nemo_rnnt_stream_finish.return_value = None
        stream = NemoCStream(engine, 101)

        stream.accept_audio(np.zeros(160, dtype=np.float32))
        stream.finalize()

        # Last mel_stream_accept carries final=1 and no new samples.
        self.assertEqual(trace["mel"][-1], (0, 1))
        engine._lib.nemo_rnnt_stream_finish.assert_called_once()
        self.assertIsNone(stream._rnnt)
        self.assertEqual(stream.text(), "")

    @patch("wyoming_nemotron_asr_c.engine._libc")
    def test_finalize_decodes_and_strips_tags(self, _mock_libc):
        engine, _ = _make_engine()
        buf = ctypes.create_string_buffer("안녕 <ko-KR> 하세요".encode("utf-8"))
        engine._lib.nemo_rnnt_stream_finish.return_value = ctypes.cast(
            buf, ctypes.c_void_p
        ).value
        stream = NemoCStream(engine, 101)

        stream.finalize()

        self.assertEqual(stream.text(), "안녕 하세요")


class TestPartialText(unittest.TestCase):
    """text() reads the RNN-T partial and strips language tags."""

    def test_text_strips_tags(self):
        engine, _ = _make_engine()
        engine._lib.nemo_rnnt_stream_text.return_value = "오늘 <ko-KR> 날씨".encode("utf-8")
        stream = NemoCStream(engine, 101)

        self.assertEqual(stream.text(), "오늘 날씨")


class TestInitFailureCleanup(unittest.TestCase):
    """A failed create() midway must free already-created streams, not crash."""

    def test_encoder_create_failure_frees_rnnt(self):
        engine, _ = _make_engine()
        engine._lib.nemo_encoder_stream_create.return_value = None

        with self.assertRaises(RuntimeError):
            NemoCStream(engine, 101)

        engine._lib.nemo_rnnt_stream_free.assert_called_once_with(_FAKE_RNNT)
        engine._lib.nemo_mel_stream_free.assert_not_called()


class TestClose(unittest.TestCase):
    """close() must free all three C streams."""

    def test_close_frees_all_streams(self):
        engine, _ = _make_engine()
        stream = NemoCStream(engine, 101)

        stream.close()

        engine._lib.nemo_mel_stream_free.assert_called_once_with(_FAKE_MEL)
        engine._lib.nemo_encoder_stream_free.assert_called_once_with(_FAKE_ENC)
        engine._lib.nemo_rnnt_stream_free.assert_called_once_with(_FAKE_RNNT)
        self.assertIsNone(stream._mel)
        self.assertIsNone(stream._enc)
        self.assertIsNone(stream._rnnt)


if __name__ == "__main__":
    unittest.main()
