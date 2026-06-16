"""Log-mel feature extraction matching NeMo's AudioToMelSpectrogramPreprocessor.

The Nemotron encoder consumes `processed_signal[B, n_mels, T]` — the exact
features NeMo produces at training time. We reproduce them with numpy only
(no librosa/scipy) so the runtime image stays small.

VALIDATION RISK: getting these features bit-for-bit right is the single most
important correctness factor. The parameters below come from the model's
config.json (`preprocessor` block) and NeMo's documented defaults. If
transcripts come out as garbage, this module is the first suspect — compare a
reference mel (run the real .nemo preprocessor on a known wav) against
`MelFeaturizer(...)(wav)` before touching anything else. See AGENTS.md.

NeMo defaults reproduced here:
  * pre-emphasis 0.97
  * STFT: hann window (periodic=False), center padding (reflect), n_fft=512,
    win=400 (25 ms), hop=160 (10 ms)
  * power spectrum (magnitude ** 2)
  * slaney-normalised mel filterbank (htk=False), fmin=0, fmax=sr/2
  * log(x + 2**-24)
  * normalize="NA"  -> NO per-feature normalization (config.json says so)
  * dither disabled at inference
"""
from __future__ import annotations

import numpy as np


def _hz_to_mel_slaney(freq: np.ndarray) -> np.ndarray:
    f_min, f_sp = 0.0, 200.0 / 3
    mels = (freq - f_min) / f_sp
    min_log_hz = 1000.0
    min_log_mel = (min_log_hz - f_min) / f_sp
    logstep = np.log(6.4) / 27.0
    log_t = freq >= min_log_hz
    mels[log_t] = min_log_mel + np.log(freq[log_t] / min_log_hz) / logstep
    return mels


def _mel_to_hz_slaney(mels: np.ndarray) -> np.ndarray:
    f_min, f_sp = 0.0, 200.0 / 3
    freqs = f_min + f_sp * mels
    min_log_hz = 1000.0
    min_log_mel = (min_log_hz - f_min) / f_sp
    logstep = np.log(6.4) / 27.0
    log_t = mels >= min_log_mel
    freqs[log_t] = min_log_hz * np.exp(logstep * (mels[log_t] - min_log_mel))
    return freqs


def _mel_filterbank(sr: int, n_fft: int, n_mels: int) -> np.ndarray:
    """librosa.filters.mel equivalent: slaney norm, htk=False, fmin=0, fmax=sr/2."""
    fmax = sr / 2.0
    n_freqs = n_fft // 2 + 1
    fftfreqs = np.linspace(0, sr / 2.0, n_freqs)

    min_mel = _hz_to_mel_slaney(np.array([0.0]))[0]
    max_mel = _hz_to_mel_slaney(np.array([fmax]))[0]
    mel_pts = np.linspace(min_mel, max_mel, n_mels + 2)
    freq_pts = _mel_to_hz_slaney(mel_pts)

    fdiff = np.diff(freq_pts)
    ramps = freq_pts[:, None] - fftfreqs[None, :]
    weights = np.zeros((n_mels, n_freqs), dtype=np.float32)
    for i in range(n_mels):
        lower = -ramps[i] / fdiff[i]
        upper = ramps[i + 2] / fdiff[i + 1]
        weights[i] = np.maximum(0.0, np.minimum(lower, upper))
    # Slaney normalization: area-normalize each filter.
    enorm = 2.0 / (freq_pts[2 : n_mels + 2] - freq_pts[:n_mels])
    weights *= enorm[:, None]
    return weights


class MelFeaturizer:
    def __init__(
        self,
        sample_rate: int = 16000,
        n_mels: int = 128,
        n_fft: int = 512,
        win_length: int = 400,
        hop_length: int = 160,
        preemph: float = 0.97,
        log_zero_guard: float = 2.0 ** -24,
    ) -> None:
        self.n_fft = n_fft
        self.win_length = win_length
        self.hop_length = hop_length
        self.preemph = preemph
        self.log_zero_guard = log_zero_guard
        self.pad = n_fft // 2  # center=True reflect padding
        self.n_mels = _mel_filterbank(sample_rate, n_fft, n_mels).shape[0]
        self.mel_fb = _mel_filterbank(sample_rate, n_fft, n_mels)
        # win_length < n_fft -> center the (hann, periodic=False) window in the FFT.
        # torch.hann_window(win_length, periodic=False) == np.hanning(win_length).
        win = np.zeros(n_fft, dtype=np.float32)
        off = (n_fft - win_length) // 2
        win[off : off + win_length] = np.hanning(win_length).astype(np.float32)
        self._fft_window = win

    def _preemph(self, x: np.ndarray) -> np.ndarray:
        if not self.preemph:
            return np.asarray(x, dtype=np.float32)
        return np.concatenate([x[:1], x[1:] - self.preemph * x[:-1]]).astype(np.float32)

    def _logmel(self, frames: np.ndarray) -> np.ndarray:
        """frames: [T, n_fft] raw (un-windowed) -> log-mel [n_mels, T]."""
        spec = np.fft.rfft(frames * self._fft_window, n=self.n_fft, axis=1)
        power = (spec.real ** 2 + spec.imag ** 2).astype(np.float32)  # mag_power=2
        mel = self.mel_fb @ power.T  # [n_mels, T]
        return np.log(mel + self.log_zero_guard).astype(np.float32)

    def __call__(self, audio: np.ndarray) -> np.ndarray:
        """Full center=True log-mel. audio: float32 mono [-1, 1]. Returns [n_mels, T]."""
        x = np.asarray(audio, dtype=np.float32)
        if x.size == 0:
            return np.zeros((self.n_mels, 0), dtype=np.float32)
        xp = np.pad(self._preemph(x), self.pad, mode="reflect")
        n_frames = 1 + (len(xp) - self.n_fft) // self.hop_length
        if n_frames <= 0:
            return np.zeros((self.n_mels, 0), dtype=np.float32)
        frames = np.lib.stride_tricks.as_strided(
            xp,
            shape=(n_frames, self.n_fft),
            strides=(xp.strides[0] * self.hop_length, xp.strides[0]),
        ).copy()
        return self._logmel(frames)

    def logmel_frames(self, audio: np.ndarray, i0: int, i1: int) -> np.ndarray:
        """Frames [i0, i1) of __call__(audio), computed without re-FFT'ing 0..i0.

        Interior frames (i*hop >= pad, i.e. i >= 2 here) are plain slices of the
        pre-emphasized signal — no reflect padding — so they're identical to the
        full path and can be computed incrementally. The first batch (i0 == 0,
        frames 0/1 need front reflect) falls back to the full path once.
        """
        if i1 <= i0:
            return np.zeros((self.n_mels, 0), dtype=np.float32)
        if i0 * self.hop_length < self.pad:
            return self(audio)[:, i0:i1]
        xe = self._preemph(np.asarray(audio, dtype=np.float32))
        base = i0 * self.hop_length - self.pad
        seg = xe[base : (i1 - 1) * self.hop_length + self.n_fft - self.pad]
        nf = i1 - i0
        frames = np.lib.stride_tricks.as_strided(
            seg,
            shape=(nf, self.n_fft),
            strides=(seg.strides[0] * self.hop_length, seg.strides[0]),
        ).copy()
        return self._logmel(frames)
