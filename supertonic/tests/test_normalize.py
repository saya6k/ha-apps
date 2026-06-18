"""Unit tests for the language-aware number normalizer.

Requires langid + unicode-rbnf; run in the local uv venv without the MNN
engine:  .venv/bin/python -m pytest tests/test_normalize.py
"""
from wyoming_supertonic.normalize import TextNormalizer, detect_norm_lang


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


def test_detect_norm_lang_korean():
    assert detect_norm_lang("오늘 온도는 23도입니다.") == "ko"


def test_detect_norm_lang_japanese():
    assert detect_norm_lang("今日の気温は23度です。") == "ja"


def test_detect_norm_lang_english():
    assert detect_norm_lang("The temperature is 23 degrees today.") == "en"


def test_detect_norm_lang_german():
    assert detect_norm_lang("Die Temperatur beträgt 23 Grad.") == "de"


def test_detect_norm_lang_arabic():
    assert detect_norm_lang("درجة الحرارة اليوم 23 درجة.") == "ar"


def test_detect_norm_lang_russian():
    assert detect_norm_lang("Сегодня температура 23 градуса.") == "ru"


def test_normalize_korean_with_english_fallback_lang():
    # Simulates the real scenario: HA sends no language (defaults to "en"),
    # but text is Korean. detect_norm_lang picks "ko" and normalization
    # produces Korean number words instead of English.
    n = TextNormalizer()
    detected = detect_norm_lang("오늘 온도는 23도입니다.")
    norm_lang = detected or "en"
    assert norm_lang == "ko"
    assert n.normalize("오늘 온도는 23도입니다.", norm_lang) == "오늘 온도는 이십삼도입니다."


def test_streaming_number_split_across_chunks():
    # "12" + "34" arrive in separate chunks; the SBD buffers, so the
    # normalizer sees the reassembled "1234".
    assert _run_stream(["I have 12", "34 apples. ", "Cost 5", "6.7 now."]) == [
        "I have one thousand two hundred thirty-four apples.",
        "Cost fifty-six point seven now.",
    ]
