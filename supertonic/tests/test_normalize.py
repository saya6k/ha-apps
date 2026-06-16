"""Unit tests for the language-aware number normalizer.

Pure-Python (unicode-rbnf only), so these run in the local uv venv without
the MNN engine:  .venv/bin/python -m pytest tests/test_normalize.py
"""
from wyoming_supertonic.normalize import TextNormalizer


def test_english_integer():
    assert TextNormalizer().normalize("I have 23 cats", "en") == (
        "I have twenty-three cats"
    )


def test_decimal_spelled_out():
    out = TextNormalizer().normalize("it is 3.5 meters", "en")
    assert out == "it is three point five meters"


def test_negative_integer():
    out = TextNormalizer().normalize("-7 degrees outside", "en")
    assert out == "minus seven degrees outside"


def test_korean_integer():
    assert TextNormalizer().normalize("사과 23개", "ko") == "사과 이십삼개"


def test_no_number_is_passthrough():
    assert TextNormalizer().normalize("hello world", "en") == "hello world"


def test_unsupported_language_is_passthrough():
    # "zz" has no RBNF ruleset -> numbers left as-is, no crash.
    assert TextNormalizer().normalize("I have 23 cats", "zz") == "I have 23 cats"


def test_wordlike_tokens_untouched():
    # Voice ("M1") and version ("v3") tokens must survive unchanged.
    assert TextNormalizer().normalize("model v3 voice M1", "en") == (
        "model v3 voice M1"
    )


def test_version_string_untouched():
    # Dotted version numbers must not be split into decimals.
    assert TextNormalizer().normalize("version 3.5.2 ready", "en") == (
        "version 3.5.2 ready"
    )


def test_engine_cached_across_calls():
    n = TextNormalizer()
    n.normalize("5", "en")
    n.normalize("6", "en")
    assert set(n._engines) == {"en"}
    assert n._engines["en"] is not None


def _run_stream(chunks, lang="en"):
    """Mimic the handler's streaming path: chunks -> SBD -> per-sentence
    normalize. Numbers must survive being split across chunks, and a decimal
    point must not be mistaken for a sentence boundary."""
    from sentence_stream import SentenceBoundaryDetector

    n = TextNormalizer()
    sbd = SentenceBoundaryDetector()
    out = []
    for c in chunks:
        for sentence in sbd.add_chunk(c):
            out.append(n.normalize(sentence, lang))
    tail = sbd.finish()
    if tail:
        out.append(n.normalize(tail, lang))
    return out


def test_streaming_decimal_not_split_at_period():
    # The SBD must keep "3.5" intact (not split on the dot) before we normalize.
    assert _run_stream(["I have 3.5 apples. Done."]) == [
        "I have three point five apples.",
        "Done.",
    ]


def test_streaming_number_split_across_chunks():
    # "12" + "34" arrive in separate chunks; the SBD buffers, so the
    # normalizer sees the reassembled "1234".
    assert _run_stream(["I have 12", "34 apples. ", "Cost 5", "6.7 now."]) == [
        "I have one thousand two hundred thirty-four apples.",
        "Cost fifty-six point seven now.",
    ]
