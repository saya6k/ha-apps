"""HuggingFace download + .nemo -> .bin conversion.

The add-on downloads a .nemo model file at boot, then converts it to the
C-runtime .bin format via the vendored tools/convert_nemo.py. The .bin is cached
per quantisation in /data/models/<repo_slug>/<quant>/model.bin.

PyTorch is required for conversion (torch.load on the .ckpt inside the .nemo
tar.gz). This is the runtime cost of Option C (any fine-tuned .nemo, any time).
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

from .const import CONVERT_SCRIPT, QUANT_CONVERTER_FLAGS, QUANTS

_LOGGER = logging.getLogger(__name__)


def _repo_slug(repo_id: str) -> str:
    """Turn 'nvidia/nemotron-3.5-asr-streaming-0.6b' into a safe dir name."""
    return repo_id.replace("/", "_")


def cleanup_old_models(models_dir: str, repo_id: str) -> None:
    """Remove model directories that don't match the currently configured repo.

    Each model is ~650 MiB (q8p .bin).  When the user changes the model in
    config.yaml, the old directory stays on disk forever unless we clean it up.
    """
    current_slug = _repo_slug(repo_id)
    models_path = Path(models_dir)
    if not models_path.is_dir():
        return
    for entry in models_path.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if entry.name == current_slug:
            continue
        _LOGGER.info("Removing unused model: %s", entry)
        shutil.rmtree(entry)


def _find_nemo_file(repo_id: str, token: str | None) -> Path:
    """Locate the .nemo file in a HF repo (filename not known ahead of time).

    The converter needs the exact filename. We download to a temp name first,
    then detect the real filename from the download result.
    """
    from huggingface_hub import list_repo_files

    files = list_repo_files(repo_id, token=token)
    nemo_files = [f for f in files if f.endswith(".nemo")]
    if not nemo_files:
        raise FileNotFoundError(f"No .nemo file found in repo {repo_id}")
    if len(nemo_files) > 1:
        _LOGGER.warning(
            "Multiple .nemo files in %s: %s — using %s",
            repo_id, nemo_files, nemo_files[0],
        )
    return hf_hub_download(
        repo_id=repo_id,
        filename=nemo_files[0],
        token=token,
    )


def ensure_nemo(repo_id: str, models_dir: str, token: str | None = None) -> Path:
    """Download the .nemo file from HF, caching in models_dir.

    Returns the path to the cached .nemo file.
    """
    slug = _repo_slug(repo_id)
    cache_dir = Path(models_dir) / slug
    cache_dir.mkdir(parents=True, exist_ok=True)

    nemo_path = cache_dir / f"{slug}.nemo"
    if nemo_path.exists() and nemo_path.stat().st_size > 0:
        _LOGGER.info("Using cached .nemo: %s", nemo_path)
        return nemo_path

    _LOGGER.info("Downloading .nemo from %s ...", repo_id)
    downloaded = _find_nemo_file(repo_id, token)
    # Symlink or copy to our managed cache.
    if not nemo_path.exists():
        os.symlink(downloaded, nemo_path)
    _LOGGER.info("Cached .nemo at %s", nemo_path)
    return nemo_path


def convert_to_bin(nemo_path: Path, quant: str, output_dir: Path) -> Path:
    """Convert a .nemo file to a quantized .bin via tools/convert_nemo.py.

    Returns the path to the resulting .bin file.
    """
    if quant not in QUANTS:
        raise ValueError(f"Unknown quantization: {quant}")
    quant_spec = QUANTS[quant]
    if not quant_spec.implemented:
        raise NotImplementedError(
            f"Quantization {quant} ({quant_spec.label}) is not yet implemented. "
            "C kernels are needed upstream."
        )

    stem = nemo_path.stem  # e.g. "nvidia_nemotron-3.5-asr-streaming-0.6b"
    output_path = output_dir / f"{stem}-{quant}.bin"

    if output_path.exists() and output_path.stat().st_size > 0:
        _LOGGER.info("Using cached .bin: %s", output_path)
        return output_path

    flag = QUANT_CONVERTER_FLAGS.get(quant)
    cmd = [sys.executable, str(CONVERT_SCRIPT), str(nemo_path), "-o", str(output_path)]
    if flag:
        cmd.append(flag)

    _LOGGER.info("Converting .nemo -> .bin [%s]: %s", quant, " ".join(cmd))
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        _LOGGER.error("Converter failed (stdout):\n%s", exc.stdout)
        _LOGGER.error("Converter failed (stderr):\n%s", exc.stderr)
        raise RuntimeError(
            f".nemo -> .bin conversion failed for quant={quant}: {exc}"
        ) from exc

    if not output_path.exists():
        raise RuntimeError(f"Converter did not produce {output_path}")
    size_mb = output_path.stat().st_size / (1024 * 1024)
    _LOGGER.info("Converted %s -> %s (%.1f MiB)", quant, output_path, size_mb)
    return output_path


def ensure_bin(
    repo_id: str, quant: str, models_dir: str, token: str | None = None
) -> Path:
    """Download .nemo and convert to .bin for the given quant.

    This is the main entry point: cached downloads + conversion, so the engine
    can just call nemo_load(bin_path).
    """
    # 1. Download .nemo (cached).
    nemo_path = ensure_nemo(repo_id, models_dir, token)

    # 2. Convert to .bin for the requested quant (cached).
    slug = _repo_slug(repo_id)
    output_dir = Path(models_dir) / slug / quant
    bin_path = convert_to_bin(nemo_path, quant, output_dir)

    return bin_path
