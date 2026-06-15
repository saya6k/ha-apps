"""Download one GGUF quant of the selected model from HuggingFace."""
from __future__ import annotations

import logging
import os
import struct
from typing import Optional

from .const import ATT_CONTEXT_RIGHT_KEY, GGUF_FILE, GGUF_REPO

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


# GGUF v2/v3 metadata value types (the only widths we must skip past to reach
# the target key). v1 used 32-bit counts/lengths; published parakeet GGUFs are
# v3, so we require version >= 2 and bail safely otherwise.
_GGUF_SCALAR_SIZE = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 7: 1, 10: 8, 11: 8, 12: 8}
_GGUF_TYPE_INT32 = 5
_GGUF_TYPE_STRING = 8
_GGUF_TYPE_ARRAY = 9


def _skip_value(f, vtype: int) -> None:
    """Advance the file cursor past one GGUF metadata value of type `vtype`."""
    if vtype in _GGUF_SCALAR_SIZE:
        f.seek(_GGUF_SCALAR_SIZE[vtype], os.SEEK_CUR)
    elif vtype == _GGUF_TYPE_STRING:
        (n,) = struct.unpack("<Q", f.read(8))
        f.seek(n, os.SEEK_CUR)
    elif vtype == _GGUF_TYPE_ARRAY:
        (elem_type,) = struct.unpack("<I", f.read(4))
        (count,) = struct.unpack("<Q", f.read(8))
        for _ in range(count):
            _skip_value(f, elem_type)
    else:
        raise ValueError(f"unknown GGUF value type {vtype}")


def set_att_context_right(gguf_path: str, value: int) -> bool:
    """Patch the scalar INT32 KV `parakeet.encoder.att_context_right` in place.

    This is the cache-aware streaming operating point (lookahead). The C++ loader
    reads this scalar and the offline encoder applies the resulting chunked-limited
    attention mask, so editing it switches the accuracy/speed point with no
    re-download or re-quant. Only 4 bytes are rewritten (same width); the file is
    otherwise untouched. Returns True if modified, False if already at `value`,
    absent, or not a cache-aware GGUF.
    """
    with open(gguf_path, "r+b") as f:
        if f.read(4) != b"GGUF":
            _LOGGER.warning("%s: not a GGUF file; skipping chunk-size patch", gguf_path)
            return False
        (version,) = struct.unpack("<I", f.read(4))
        if version < 2:
            _LOGGER.warning(
                "%s: GGUF v%d unsupported for in-place patch; chunk-size not applied",
                gguf_path, version,
            )
            return False
        f.seek(8, os.SEEK_CUR)  # tensor_count (u64), unused
        (n_kv,) = struct.unpack("<Q", f.read(8))
        key = ATT_CONTEXT_RIGHT_KEY.encode("utf-8")
        for _ in range(n_kv):
            (klen,) = struct.unpack("<Q", f.read(8))
            k = f.read(klen)
            (vtype,) = struct.unpack("<I", f.read(4))
            if k == key:
                if vtype != _GGUF_TYPE_INT32:
                    _LOGGER.warning(
                        "%s: %s is type %d, expected INT32; chunk-size not applied",
                        gguf_path, ATT_CONTEXT_RIGHT_KEY, vtype,
                    )
                    return False
                pos = f.tell()
                (cur,) = struct.unpack("<i", f.read(4))
                if cur == value:
                    _LOGGER.info(
                        "Chunk-size already set (%s=%d) in %s",
                        ATT_CONTEXT_RIGHT_KEY, value, os.path.basename(gguf_path),
                    )
                    return False
                f.seek(pos)
                f.write(struct.pack("<i", value))
                _LOGGER.info(
                    "Chunk-size: %s %d -> %d in %s",
                    ATT_CONTEXT_RIGHT_KEY, cur, value, os.path.basename(gguf_path),
                )
                return True
            _skip_value(f, vtype)
    _LOGGER.warning(
        "%s: %s not found; chunk-size not applied (model is not cache-aware "
        "streaming?)", gguf_path, ATT_CONTEXT_RIGHT_KEY,
    )
    return False
