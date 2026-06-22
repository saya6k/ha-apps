"""Language-aware text normalization for Supertonic.

Primary: NeMo WFST TN (nemo_text_processing) for supported languages.
Handles numbers, ordinals, currency, dates, times, units, and more.
Grammars are pre-compiled at Docker build time to /opt/nemo-cache.

Fallback: unicode-rbnf (CLDR RBNF spellout) for unsupported languages.
Scope is deliberately narrow: cardinal integers and simple decimals only.

On any failure the original text is returned untouched.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Optional

_LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# NeMo TN setup
# ---------------------------------------------------------------------------

# Languages with pre-compiled grammars in /opt/nemo-cache.
# Must match the langs compiled in the Dockerfile precompile step.
_NEMO_CACHE_DIR = "/opt/nemo-cache"
_NEMO_LANGS = frozenset({"ko", "en"})

_nemo_available: Optional[bool] = None
_nemo_normalizers: Dict[str, object] = {}


def _check_nemo() -> bool:
    global _nemo_available
    if _nemo_available is not None:
        return _nemo_available
    try:
        import pynini  # noqa: F401
        from nemo_text_processing.text_normalization.normalize import Normalizer  # noqa: F401
        _nemo_available = True
        _LOGGER.info("NeMo TN available — using WFST normalizer for %s", sorted(_NEMO_LANGS))
    except ImportError as exc:
        _nemo_available = False
        _LOGGER.warning("NeMo TN not available (%s); falling back to unicode-rbnf", exc)
    return _nemo_available


def _nemo_normalizer_for(lang: str) -> Optional[object]:
    if lang not in _nemo_normalizers:
        try:
            from nemo_text_processing.text_normalization.normalize import Normalizer
            _LOGGER.debug("Loading NeMo TN grammar for %r from cache …", lang)
            norm = Normalizer(
                input_case="cased",
                lang=lang,
                cache_dir=_NEMO_CACHE_DIR,
                overwrite_cache=False,
                deterministic=True,
            )
            _nemo_normalizers[lang] = norm
            _LOGGER.info("NeMo TN grammar loaded for %r", lang)
        except Exception as exc:
            _LOGGER.warning("NeMo TN grammar load failed for %r: %s", lang, exc)
            _nemo_normalizers[lang] = None
    return _nemo_normalizers[lang]


def _nemo_normalize(text: str, lang: str) -> Optional[str]:
    if not _check_nemo():
        return None
    if lang not in _NEMO_LANGS:
        return None
    norm = _nemo_normalizer_for(lang)
    if norm is None:
        return None
    try:
        return norm.normalize(text, verbose=False)
    except Exception as exc:
        _LOGGER.debug("NeMo TN failed for %r: %s", text[:60], exc)
        return None


# ---------------------------------------------------------------------------
# unicode-rbnf fallback (cardinal integers and simple decimals)
# ---------------------------------------------------------------------------

import langid  # noqa: E402
from unicode_rbnf import FormatPurpose, RbnfEngine  # noqa: E402

try:
    langid.classify("")
except Exception:  # noqa: BLE001
    _LOGGER.warning("langid pre-load failed; language detection will be slower on first request")

_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9.])(-?\d+(?:\.\d+)?)(?![A-Za-z0-9.])")

_rbnf_engines: Dict[str, Optional[RbnfEngine]] = {}


def _rbnf_engine_for(lang: str) -> Optional[RbnfEngine]:
    if lang in _rbnf_engines:
        return _rbnf_engines[lang]
    try:
        engine: Optional[RbnfEngine] = RbnfEngine.for_language(lang)
    except Exception:  # noqa: BLE001
        _LOGGER.info("No RBNF ruleset for %r; numbers spoken as-is.", lang)
        engine = None
    _rbnf_engines[lang] = engine
    return engine


def _rbnf_normalize(text: str, lang: str) -> str:
    if not text or not _NUMBER_RE.search(text):
        return text
    engine = _rbnf_engine_for(lang)
    if engine is None:
        return text

    def _replace(match: "re.Match[str]") -> str:
        token = match.group(1)
        try:
            value = float(token) if "." in token else int(token)
            return engine.format_number(value, FormatPurpose.CARDINAL).text
        except Exception:  # noqa: BLE001
            return token

    return _NUMBER_RE.sub(_replace, text)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_norm_lang(text: str) -> Optional[str]:
    """Detect language of *text*, return ISO 639-1 code or None."""
    try:
        lang, _ = langid.classify(text)
        return lang or None
    except Exception:  # noqa: BLE001
        return None


class TextNormalizer:
    """Normalize text for TTS.

    Uses NeMo WFST TN for supported languages (full sentence normalization),
    falls back to unicode-rbnf number expansion for the rest.
    """

    def normalize(self, text: str, lang: str) -> str:
        result = _nemo_normalize(text, lang)
        if result is not None:
            return result
        return _rbnf_normalize(text, lang)
