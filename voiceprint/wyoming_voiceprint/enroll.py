"""Voiceprint enrollment from /share/voiceprint/<speaker>/*.wav."""
from __future__ import annotations

import logging
import wave
from pathlib import Path

import numpy as np

from .const import SAMPLE_RATE
from .embedder import Embedder

_LOGGER = logging.getLogger(__name__)


def _read_wav(path: Path) -> np.ndarray | None:
    """Read a WAV file as float32 [-1, 1] mono 16 kHz."""
    try:
        with wave.open(str(path), "rb") as wav:
            if wav.getsampwidth() != 2:
                _LOGGER.warning("%s: only 16-bit PCM supported, skipping", path)
                return None
            rate = wav.getframerate()
            channels = wav.getnchannels()
            data = wav.readframes(wav.getnframes())
    except (wave.Error, EOFError, OSError) as err:
        _LOGGER.warning("%s: unreadable (%s), skipping", path, err)
        return None

    audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
    if channels > 1:
        audio = audio.reshape(-1, channels).mean(axis=1)
    if rate != SAMPLE_RATE:
        n = int(len(audio) * SAMPLE_RATE / rate)
        audio = np.interp(
            np.linspace(0, len(audio) - 1, n), np.arange(len(audio)), audio
        ).astype(np.float32)
    return audio


def load_voiceprints(enroll_dir: str, embedder: Embedder) -> dict[str, np.ndarray]:
    """Mean L2-normalized embedding per speaker subdirectory."""
    voiceprints: dict[str, np.ndarray] = {}
    root = Path(enroll_dir)
    if not root.is_dir():
        return voiceprints

    # Skip "_"/"." dirs (e.g. _captures) so they aren't enrolled as a speaker.
    for speaker_dir in sorted(
        p for p in root.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))
    ):
        embeddings = []
        for wav_path in sorted(speaker_dir.glob("*.wav")):
            audio = _read_wav(wav_path)
            if audio is None:
                continue
            emb = embedder.embed(audio)
            if emb is None:
                _LOGGER.warning("%s: too short, skipping", wav_path)
                continue
            embeddings.append(emb)
        if not embeddings:
            _LOGGER.warning("No usable WAVs for speaker '%s'", speaker_dir.name)
            continue
        mean = np.mean(embeddings, axis=0)
        voiceprints[speaker_dir.name] = mean / np.linalg.norm(mean)
        _LOGGER.info(
            "Enrolled '%s' from %d clip(s)", speaker_dir.name, len(embeddings)
        )
    return voiceprints
