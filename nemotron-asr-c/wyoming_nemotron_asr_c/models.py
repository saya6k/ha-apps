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


def _invalidate_bin_caches(slug_dir: Path) -> None:
    """Delete all quantised .bin directories under *slug_dir*."""
    for entry in slug_dir.iterdir():
        if entry.is_dir() and not entry.name.startswith("."):
            _LOGGER.info("Removing stale .bin: %s", entry)
            shutil.rmtree(entry)


def ensure_nemo(repo_id: str, models_dir: str, token: str | None = None) -> Path:
    """Download the .nemo file from HF, caching in models_dir.

    Always resolves the latest version from HF so upstream model updates are
    detected.  hf_hub_download handles ETag-based caching internally — unchanged
    models return instantly from the local HF cache without re-downloading.
    """
    slug = _repo_slug(repo_id)
    cache_dir = Path(models_dir) / slug
    cache_dir.mkdir(parents=True, exist_ok=True)

    nemo_path = cache_dir / f"{slug}.nemo"

    # Always resolve the latest download (ETag-cached by huggingface_hub).
    _LOGGER.info("Resolving .nemo from %s ...", repo_id)
    downloaded = _find_nemo_file(repo_id, token)

    if nemo_path.exists():
        try:
            if nemo_path.resolve() == Path(downloaded).resolve():
                # Validate that the cached file is a real .nemo (not a stale Xet
                # pointer file from an older huggingface_hub).
                if _is_tar_archive(nemo_path):
                    _LOGGER.info("Using cached .nemo: %s", nemo_path)
                    return nemo_path
                _LOGGER.warning(
                    "Cached .nemo is not a valid tar archive (likely a stale "
                    "Xet pointer file). Re-downloading."
                )
                nemo_path.unlink()
                _invalidate_bin_caches(cache_dir)
            else:
                _LOGGER.info("Model updated on HF — invalidating .bin caches")
                nemo_path.unlink()
                _invalidate_bin_caches(cache_dir)
        except OSError:
            _LOGGER.warning("Broken symlink at %s — re-creating", nemo_path)
            if nemo_path.exists():
                nemo_path.unlink()

    # Remove any existing entry (regular file, symlink, or broken symlink)
    # before creating the new symlink.  Broken symlinks are NOT reported by
    # Path.exists(), so the OSError handler above cannot reach them.
    nemo_path.unlink(missing_ok=True)
    os.symlink(downloaded, nemo_path)

    # Validate the downloaded file is a real .nemo archive.
    if not _is_tar_archive(nemo_path):
        nemo_path.unlink()
        raise RuntimeError(
            f"Downloaded file from {repo_id} is not a valid .nemo archive "
            "(expected tar or tar.gz). "
            "This may be a Xet pointer file — install huggingface_hub with the "
            "hf-xet extra: pip install 'huggingface_hub[hf-xet]>=0.32'"
        )
    _LOGGER.info("Cached .nemo at %s", nemo_path)
    return nemo_path


def _is_tar_archive(path: Path) -> bool:
    """Check that a file is a valid tar archive (not a Xet pointer file).

    .nemo files are tar archives, optionally gzip-compressed.  Xet pointer
    files are plain text starting with './...' — they lack tar magic bytes
    and will fail this check.
    """
    try:
        with open(path, "rb") as f:
            header = f.read(2)
        # gzip-compressed tar
        if header == b"\x1f\x8b":
            return True
        # plain tar — check for ustar magic at offset 257
        if path.stat().st_size < 512:
            return False
        with open(path, "rb") as f:
            f.seek(257)
            magic = f.read(6)
        return magic in (b"ustar\x00", b"ustar  ")
    except OSError:
        return False


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


def extract_tokenizer(nemo_path: Path, output_dir: Path) -> Path | None:
    """Extract SentencePiece tokenizer.model from a .nemo archive.

    The .nemo is a tar archive (optionally gzip-compressed) containing
    model_config.yaml, model_weights.ckpt, and tokenizer.model.  We extract
    the tokenizer so the engine can tokenize hotword phrases at runtime.

    Returns the path to tokenizer.model, or None if extraction failed.
    """
    import tarfile

    tok_path = output_dir / "tokenizer.model"
    if tok_path.exists():
        return tok_path
    try:
        with tarfile.open(nemo_path, "r:") as tar:
            for m in tar.getmembers():
                if m.name.endswith("tokenizer.model"):
                    with tar.extractfile(m) as src:
                        if src is None:
                            continue
                        with tok_path.open("wb") as fp:
                            shutil.copyfileobj(src, fp)
                    _LOGGER.info("Extracted tokenizer to %s", tok_path)
                    return tok_path
    except Exception:
        _LOGGER.warning(
            "Could not extract tokenizer.model from %s", nemo_path,
        )
    return None
