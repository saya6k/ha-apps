"""Constants for the Wyoming NeMo-ASR-on-ggml bridge (parakeet.cpp)."""
from __future__ import annotations

from collections import namedtuple

DEFAULT_PORT = 10360

# parakeet.cpp's shared libs (libparakeet + ggml) are installed here by the
# Dockerfile; the bridge dlopens them via ctypes.
LIB_DIR = "/usr/local/lib"

# GGUF models all live in this HF collection. The downloaded file is
# "<basename>-<quant>.gguf"; the basename comes from the selected MODELS entry.
GGUF_REPO = "mudler/parakeet-cpp-gguf"
GGUF_FILE = "{basename}-{quant}.gguf"
MODEL_DIR = "/data/models"

QUANT_CHOICES = ["q4_k", "q5_k", "q6_k", "q8_0", "f16"]

# Selectable models (dropdown label -> GGUF basename + capability flags).
# This add-on's identity is *streaming + hotword-boost* ASR, so every model
# here is a streaming RNN-T transducer that our vendored hotword patch can bias.
# parakeet.cpp auto-detects the architecture from the GGUF and `decoder=0`
# picks the right head, so the engine is model-agnostic; the flags only drive
# UX/metadata:
#   multilingual -- takes the Nemotron language prompt. English-only models
#     ignore it (the pipeline language is passed through but has no effect).
#   hotwords     -- has the RNN-T greedy decoder our vendored patch biases.
ModelSpec = namedtuple("ModelSpec", ["basename", "multilingual", "hotwords"])

MODELS = {
    "Nemotron 3.5 Streaming 0.6b": ModelSpec(
        "nemotron-3.5-asr-streaming-0.6b", multilingual=True, hotwords=True
    ),
}
DEFAULT_MODEL = "Nemotron 3.5 Streaming 0.6b"

# Pipe-joined labels for the config.yaml `model: list(...)` schema (drift test).
SCHEMA_MODELS = "|".join(MODELS)


def resolve_model(label: str | None) -> ModelSpec:
    """Map a dropdown label to its ModelSpec; fall back to the default."""
    return MODELS.get(label or DEFAULT_MODEL, MODELS[DEFAULT_MODEL])

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


def resolve_lang(language: str | None) -> str:
    """Map a native-name label / ISO code to the locale string parakeet expects.

    The Wyoming pipeline sends ISO codes (passed through as-is); a None/empty
    language means model auto-detect.
    """
    if not language:
        return "auto"
    return NAME_TO_LANG.get(language, language)
