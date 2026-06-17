"""Constants for the nemo-asr-c add-on."""

from collections import namedtuple

# ---- Network ----
PORT = 10370

# ---- Directories ----
LIB_DIR = "/usr/local/lib"
DATA_DIR = "/data"
MODELS_DIR = f"{DATA_DIR}/models"
TOOLS_DIR = "/usr/src/app/tools"
CONVERT_SCRIPT = f"{TOOLS_DIR}/convert_nemo.py"

# ---- Audio ----
SAMPLE_RATE = 16000

# ---- Quantization formats ----
# fmt -> (label, weight_bits, activation, implemented)
# implemented=False means the converter dtype exists but C kernels are not yet
# written (deferred to a follow-up).
QuantSpec = namedtuple("QuantSpec", ["label", "weight_bits", "activation", "implemented"])

QUANTS: dict[str, QuantSpec] = {
    "f32":   QuantSpec("Float32",              32, "f32",  True),
    "bf16":  QuantSpec("BFloat16",             16, "f32",  True),
    "w8a16": QuantSpec("W8A16 (int8 weights)",  8, "f16",  False),
    "q8p":   QuantSpec("Q8P (W8A8 packed)",     8, "int8", True),
    "q4p":   QuantSpec("Q4P (4-bit packed)",    4, "int8", False),
}

# Converter flag per quant key (matches convert_nemo.py --*-linear-weights).
QUANT_CONVERTER_FLAGS: dict[str, str | None] = {
    "f32":   None,                      # default (no flag)
    "bf16":  "--bf16-linear-weights",
    "w8a16": "--w8a16-linear-weights",  # not yet supported by converter
    "q8p":   "--w8a8-linear-weights",
    "q4p":   "--q4p-linear-weights",    # not yet supported by converter
}

# ---- Chunk size presets ----
# label -> att_right (the right-context in encoder frames).
# chunk_ms = (att_right + 1) * 80
CHUNK_CHOICES: dict[str, int] = {
    "80ms":   0,
    "160ms":  1,
    "320ms":  3,
    "560ms":  6,
    "1120ms": 13,
}

DEFAULT_CHUNK_SIZE = "320ms"

# ---- Languages (advertised in Wyoming Info) ----
LANGUAGES = [
    "ar", "bg", "cs", "da", "de", "el", "en", "es", "et", "fi",
    "fr", "he", "hi", "hr", "hu", "id", "it", "ja", "ko", "lt",
    "lv", "ms", "nl", "no", "pl", "pt", "ro", "ru", "sk", "sl",
    "sv", "th", "tr", "uk", "vi", "zh",
    "auto",
]

# Map HA/native language labels to ISO 639-1 codes (two-letter keys the C
# runtime's prompt dictionary expects).
NAME_TO_PROMPT_KEY: dict[str, str] = {
    "Auto":                  "auto",
    "English":               "en",
    "Español":              "es",
    "Français":             "fr",
    "Deutsch":              "de",
    "Italiano":             "it",
    "Português":            "pt",
    "Nederlands":           "nl",
    "Polski":               "pl",
    "Türkçe":               "tr",
    "Українська":           "uk",
    "Română":               "ro",
    "Čeština":              "cs",
    "Magyar":               "hu",
    "Ελληνικά":             "el",
    "Svenska":              "sv",
    "Dansk":                "da",
    "Suomi":                "fi",
    "Norsk":                "no",
    "Slovenčina":           "sk",
    "Hrvatski":             "hr",
    "Български":            "bg",
    "Lietuvių":             "lt",
    "Latviešu":             "lv",
    "Eesti":                "et",
    "Slovenščina":          "sl",
    "ไทย":                  "th",
    "Tiếng Việt":           "vi",
    "Bahasa Indonesia":     "id",
    "Bahasa Melayu":        "ms",
    "עברית":                "he",
    "中文":                  "zh",
    "日本語":                "ja",
    "Русский":              "ru",
    "हिन्दी":                "hi",
    "العربية":              "ar",
    "한국어":                "ko",
}


def resolve_lang(language: str | None) -> str:
    """Map a Wyoming/HA language label to the locale code the C runtime expects.

    Resolution order:
    1. None/empty -> "auto"
    2. Look up in NAME_TO_PROMPT_KEY (HA dropdown labels)
    3. Pass through as-is (already a locale code like "ko", "en-US")
    """
    if not language:
        return "auto"
    return NAME_TO_PROMPT_KEY.get(language, language)
