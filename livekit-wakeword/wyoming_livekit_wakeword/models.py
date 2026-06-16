"""Resolve wake word model names to verified local ONNX files."""
from __future__ import annotations

import hashlib
import logging
import urllib.request
from pathlib import Path

from .const import KNOWN_MODELS

_LOGGER = logging.getLogger(__name__)


class ResolvedModel:
    def __init__(self, name: str, path: Path, phrase: str,
                 attribution_name: str, attribution_url: str) -> None:
        self.name = name
        self.path = path
        self.phrase = phrase
        self.attribution_name = attribution_name
        self.attribution_url = attribution_url


def _download(url: str, dest: Path, sha256: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    _LOGGER.info("Downloading %s", url)
    urllib.request.urlretrieve(url, tmp)  # noqa: S310 - pinned https URLs only
    digest = hashlib.sha256(tmp.read_bytes()).hexdigest()
    if digest != sha256:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Checksum mismatch for {url}: got {digest}")
    tmp.replace(dest)


def resolve_models(
    names: list[str], model_dir: str, custom_dir: str | None
) -> list[ResolvedModel]:
    """Known names download (once) into model_dir; every *.onnx in custom_dir
    is loaded as a custom model named after its file stem."""
    resolved: list[ResolvedModel] = []

    for name in names:
        spec = KNOWN_MODELS.get(name)
        if spec is None:
            _LOGGER.warning(
                "Unknown model %r (known: %s) — skipped. Custom models go in %s.",
                name, ", ".join(KNOWN_MODELS), custom_dir,
            )
            continue
        dest = Path(model_dir) / f"{name}.onnx"
        if not dest.exists():
            _download(spec.url, dest, spec.sha256)
        resolved.append(ResolvedModel(
            name, dest, spec.phrase, spec.attribution_name, spec.attribution_url,
        ))

    if custom_dir:
        for p in sorted(Path(custom_dir).glob("*.onnx")):
            if any(r.name == p.stem for r in resolved):
                _LOGGER.warning("Custom model %s shadows a selected built-in; skipped", p)
                continue
            resolved.append(ResolvedModel(
                p.stem, p, p.stem.replace("_", " "),
                "custom", "https://github.com/livekit/livekit-wakeword",
            ))
            _LOGGER.info("Custom model: %s", p)

    return resolved
