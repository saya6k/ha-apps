"""Constants for the Wyoming Nemotron ASR bridge."""
from __future__ import annotations

DEFAULT_PORT = 10350

# The ONNX model is downloaded from this HuggingFace repo into MODEL_DIR on
# first start. It must contain: encoder.onnx (+ encoder.onnx.data),
# decoder_joint.onnx, tokenizer.model, config.json.
DEFAULT_MODEL_REPO = "tonythethompson/Nemotron-3.5-ASR-Streaming-0.6B-ONNX"

# Models persist on the add-on's /data volume (not baked into the image).
MODEL_BASE_DIR = "/data/models"

# Home Assistant's voice pipeline sends 16 kHz mono 16-bit PCM over Wyoming.
SAMPLE_RATE = 16000
SAMPLE_WIDTH = 2
CHANNELS = 1

# Languages advertised in the Wyoming Info. The model actually supports 40+
# locales (see config.json prompt_dictionary); this is the subset HA commonly
# drives pipelines with. The per-request Transcribe.language picks the prompt.
LANGUAGES = [
    "ar", "bg", "cs", "da", "de", "el", "en", "es", "et", "fa", "fi", "fr",
    "he", "hi", "hr", "hu", "id", "it", "ja", "ko", "lt", "lv", "ms", "nl",
    "no", "pl", "pt", "ro", "ru", "sk", "sl", "sv", "th", "tr", "uk", "vi",
    "zh",
]

# Curated dropdown for the `language` add-on option (native names, like the
# Supertonic add-on). Each label maps to a key that exists in the model's
# config.json `prompt_dictionary`; the engine resolves it to a prompt slot.
# "Auto" lets the model auto-detect. The per-request HA pipeline language (an
# ISO code) still overrides this fallback. Keep this in lockstep with the
# `language` schema list in config.yaml (SCHEMA_LANGUAGES below mirrors it).
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

# Dropdown label -> prompt_dictionary key.
NAME_TO_PROMPT_KEY = {label: key for label, key in LANGUAGE_CHOICES}

# Mirror of the config.yaml `language: list(...)` schema (for the drift test).
SCHEMA_LANGUAGES = "|".join(label for label, _ in LANGUAGE_CHOICES)
