"""Download one GGUF quant of the selected model from HuggingFace."""
from __future__ import annotations

import logging
import os
from typing import Optional

from .const import GGUF_FILE, GGUF_REPO

_LOGGER = logging.getLogger(__name__)


def ensure_gguf(
    basename: str,
    quant: str,
    base_dir: str,
    repo: str = GGUF_REPO,
    token: Optional[str] = None,
) -> str:
    """Download `<basename>-<quant>.gguf` into base_dir if absent; return path."""
    fname = GGUF_FILE.format(basename=basename, quant=quant)
    dest = os.path.join(base_dir, fname)
    if os.path.isfile(dest) and os.path.getsize(dest) > 0:
        _LOGGER.info("Model already present: %s", dest)
        return dest

    os.makedirs(base_dir, exist_ok=True)
    from huggingface_hub import hf_hub_download

    _LOGGER.info("Downloading %s/%s (first use) ...", repo, fname)
    path = hf_hub_download(
        repo_id=repo, filename=fname, local_dir=base_dir, token=token or None
    )
    _LOGGER.info("Downloaded %s", fname)
    return path
