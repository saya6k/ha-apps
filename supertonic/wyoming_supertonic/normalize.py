"""Language-aware number normalization for Supertonic.

Supertonic feeds text to the model character-by-character with no number
expansion of its own (see `.agents/text-normalization.md`). This pass rewrites
number substrings into spoken words *before* the engine runs, using
`unicode-rbnf` (CLDR RBNF spellout — the same rule data Piper 2 uses via ICU).

Scope is deliberately narrow: cardinal integers and simple decimals. On any
failure — an unsupported language, or a number a locale's ruleset can't format —
the original text is returned untouched, so this is never worse than no
normalization at all.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Optional

from unicode_rbnf import FormatPurpose, RbnfEngine

_LOGGER = logging.getLogger(__name__)

# A signed integer or simple decimal. Bounded by ASCII alphanumerics + dot
# (not `\w`) on both sides: this protects Latin identifiers ("v3", voice "M1")
# and version strings ("3.5.2"), while still normalizing numbers glued to a
# non-Latin word — e.g. a CJK counter like Korean "23개" (`\w` would match the
# Hangul and block it). Locale thousands grouping ("1,234") is intentionally
# not handled — see the module docstring / decision log; such numbers are
# spelled out group-by-group.
_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9.])(-?\d+(?:\.\d+)?)(?![A-Za-z0-9.])")


class TextNormalizer:
    """Expands number tokens to words, one cached RBNF engine per language."""

    def __init__(self) -> None:
        # lang -> engine, or None once we know the language is unsupported
        # (cached so the "unsupported" notice is logged exactly once per lang).
        self._engines: Dict[str, Optional[RbnfEngine]] = {}

    def _engine_for(self, lang: str) -> Optional[RbnfEngine]:
        if lang in self._engines:
            return self._engines[lang]
        try:
            engine: Optional[RbnfEngine] = RbnfEngine.for_language(lang)
        except Exception:  # noqa: BLE001 - any failure means "no ruleset"
            _LOGGER.info(
                "No number normalization ruleset for language %r; "
                "numbers will be spoken as-is.",
                lang,
            )
            engine = None
        self._engines[lang] = engine
        return engine

    def normalize(self, text: str, lang: str) -> str:
        """Return `text` with number tokens spelled out in `lang`.

        A no-op (returns `text` unchanged) when there are no numbers or the
        language has no ruleset.
        """
        if not text or not _NUMBER_RE.search(text):
            return text
        engine = self._engine_for(lang)
        if engine is None:
            return text

        def _replace(match: "re.Match[str]") -> str:
            token = match.group(1)
            try:
                value = float(token) if "." in token else int(token)
                return engine.format_number(value, FormatPurpose.CARDINAL).text
            except Exception:  # noqa: BLE001 - leave unformattable numbers raw
                return token

        return _NUMBER_RE.sub(_replace, text)
