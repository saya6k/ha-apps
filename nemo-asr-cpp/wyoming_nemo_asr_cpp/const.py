"""Constants for the Wyoming NeMo-ASR-on-ggml bridge (parakeet.cpp)."""
from __future__ import annotations

DEFAULT_PORT = 10360

# parakeet.cpp's shared libs (libparakeet + ggml) are installed here by the
# Dockerfile; the bridge dlopens them via ctypes.
LIB_DIR = "/usr/local/lib"

# GGUF models live in this HF collection. We download one quant of the
# multilingual Nemotron streaming model (the only one with Korean / 40 locales).
GGUF_REPO = "mudler/parakeet-cpp-gguf"
GGUF_FILE = "nemotron-3.5-asr-streaming-0.6b-{quant}.gguf"
MODEL_DIR = "/data/models"

QUANT_CHOICES = ["q4_k", "q5_k", "q6_k", "q8_0", "f16"]

# Home Assistant's voice pipeline sends 16 kHz mono 16-bit PCM.
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2
CHANNELS = 1

# Advertised to HA (model actually does 40+ locales via the language prompt).
LANGUAGES = [
    "ar", "bg", "cs", "da", "de", "el", "en", "es", "et", "fa", "fi", "fr",
    "he", "hi", "hr", "hu", "id", "it", "ja", "ko", "lt", "lv", "ms", "nl",
    "no", "pl", "pt", "ro", "ru", "sk", "sl", "sv", "th", "tr", "uk", "vi",
    "zh",
]

# Native-name dropdown for the `language` option. Label -> the locale string
# passed to parakeet's `--lang` / transcribe_pcm_lang (same Nemotron prompt
# dictionary as the nemotron-asr add-on). "Auto" lets the model detect.
LANGUAGE_CHOICES = [
    ("Auto", "auto"),
    ("English", "en"),
    ("Español", "es"),
    ("中文", "zh-CN"),
    ("हिन्दी", "hi"),
    ("العربية", "ar"),
    ("Français", "fr"),
    ("Deutsch", "de"),
    ("日本語", "ja-JP"),
    ("Русский", "ru"),
    ("Português", "pt"),
    ("한국어", "ko"),
    ("Italiano", "it"),
    ("Nederlands", "nl"),
    ("Polski", "pl"),
    ("Türkçe", "tr"),
    ("Українська", "uk"),
    ("Română", "ro"),
    ("Čeština", "cs"),
    ("Magyar", "hu"),
    ("Ελληνικά", "el"),
    ("Svenska", "sv"),
    ("Dansk", "da"),
    ("Suomi", "fi"),
    ("Norsk", "no"),
    ("Slovenčina", "sk"),
    ("Hrvatski", "hr"),
    ("Български", "bg"),
    ("Lietuvių", "lt"),
    ("Latviešu", "lv"),
    ("Eesti", "et"),
    ("Slovenščina", "sl"),
    ("ไทย", "th-TH"),
    ("Tiếng Việt", "vi-VN"),
    ("Bahasa Indonesia", "id-ID"),
    ("Bahasa Melayu", "ms-MY"),
    ("עברית", "he-IL"),
]

NAME_TO_LANG = {label: lang for label, lang in LANGUAGE_CHOICES}

# Mirror of the config.yaml `language: list(...)` schema (drift test).
SCHEMA_LANGUAGES = "|".join(label for label, _ in LANGUAGE_CHOICES)


def resolve_lang(language: str | None) -> str:
    """Map a dropdown label / ISO code to the locale string parakeet expects."""
    if not language:
        return "auto"
    return NAME_TO_LANG.get(language, language)
