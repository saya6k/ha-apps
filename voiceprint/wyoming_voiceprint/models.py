"""Fetch the CAM++ speaker-embedding model into /data on first run."""

from __future__ import annotations

import hashlib
import logging
import os
import tempfile
import urllib.request

from .const import MODEL_FILENAME, MODEL_SHA256, MODEL_URL

_LOGGER = logging.getLogger(__name__)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_model(base_dir: str = "/data", url: str = MODEL_URL) -> str:
    """Return the model path, downloading it into base_dir if absent/corrupt.

    Verified against MODEL_SHA256 both on the cached copy and on a fresh
    download (atomic rename only after the hash matches), so a truncated or
    tampered file is never used.
    """
    dest = os.path.join(base_dir, MODEL_FILENAME)
    if os.path.isfile(dest) and _sha256(dest) == MODEL_SHA256:
        _LOGGER.info("Model already present: %s", dest)
        return dest

    os.makedirs(base_dir, exist_ok=True)
    _LOGGER.info("Downloading speaker model (first use) from %s", url)
    fd, tmp = tempfile.mkstemp(dir=base_dir, suffix=".part")
    os.close(fd)
    try:
        urllib.request.urlretrieve(url, tmp)
        actual = _sha256(tmp)
        if actual != MODEL_SHA256:
            raise RuntimeError(
                f"Downloaded model SHA256 {actual} != expected {MODEL_SHA256}"
            )
        os.replace(tmp, dest)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)

    _LOGGER.info("Model ready: %s", dest)
    return dest
