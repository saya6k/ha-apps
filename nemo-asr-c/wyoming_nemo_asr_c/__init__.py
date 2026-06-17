"""Wyoming bridge for nemotron-asr-streaming.c (pure-C Nemotron ASR)."""

from pathlib import Path

_pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
if _pyproject.is_file():
    import re as _re
    _match = _re.search(
        r'^version\s*=\s*"(.+)"', _pyproject.read_text(), _re.MULTILINE
    )
    __version__ = _match.group(1) if _match else "0.0.0"
else:
    __version__ = "0.0.0"
