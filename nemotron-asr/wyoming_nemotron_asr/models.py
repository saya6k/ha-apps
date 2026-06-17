"""Download the ONNX model from HuggingFace into the persistent /data volume."""
from __future__ import annotations

import logging
import os
from typing import Optional

_LOGGER = logging.getLogger(__name__)

# Required files for inference. Everything else in the repo (README, CoreML
# variants, .gitattributes) is skipped to save bandwidth/disk.
_ALLOW = [
    "encoder.onnx",
    "encoder.onnx.data",
    "decoder_joint.onnx",
    "tokenizer.model",
    "config.json",
]


def basename(repo_id: str) -> str:
    return repo_id.strip().rstrip("/").split("/")[-1]


def ensure_model(repo_id: str, base_dir: str, token: Optional[str] = None) -> str:
    """Download `repo_id` into `base_dir/<basename>` if absent; return the path."""
    repo_id = repo_id.strip()
    dest = os.path.join(base_dir, basename(repo_id))
    if os.path.isfile(os.path.join(dest, "encoder.onnx")):
        _LOGGER.info("Model already present: %s", dest)
        return dest

    os.makedirs(base_dir, exist_ok=True)
    from huggingface_hub import snapshot_download

    _LOGGER.info("Downloading %s -> %s (first use, ~2.6 GB) ...", repo_id, dest)
    snapshot_download(
        repo_id=repo_id,
        local_dir=dest,
        allow_patterns=_ALLOW,
        token=token or None,
    )
    _LOGGER.info("Downloaded %s", repo_id)
    return dest
