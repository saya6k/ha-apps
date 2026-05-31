"""Constants for the Supertonic Wyoming bridge (MNN backend)."""

DEFAULT_PORT = 10209
SAMPLE_RATE = 44100  # Supertonic native output rate

VOICES = [
    "M1", "M2", "M3", "M4", "M5",
    "F1", "F2", "F3", "F4", "F5",
]
DEFAULT_VOICE = "M1"

# Supertonic (MNN v3 default) languages.
#
# The HA dropdown shows each language by its **native** name (한국어, 日本語,
# Deutsch, …) — same convention OS language pickers use. The engine still
# talks ISO 639-1 codes internally; `resolve_language()` converts.
#
# Ordered by ISO code (canonical / stable). Native script alphabetic
# ordering across mixed scripts is not a thing — and HA cannot i18n-sort
# the schema list per user locale — so ISO order is the only consistent
# choice. Users can still scan the dropdown for their language.
#
# Tuples kept as a list so the order is stable; the dicts below are
# derived from it.
LANGUAGE_ENTRIES = [
    ("ar", "العربية"),
    ("bg", "Български"),
    ("cs", "Čeština"),
    ("da", "Dansk"),
    ("de", "Deutsch"),
    ("el", "Ελληνικά"),
    ("en", "English"),
    ("es", "Español"),
    ("et", "Eesti"),
    ("fi", "Suomi"),
    ("fr", "Français"),
    ("hi", "हिन्दी"),
    ("hr", "Hrvatski"),
    ("hu", "Magyar"),
    ("id", "Bahasa Indonesia"),
    ("it", "Italiano"),
    ("ja", "日本語"),
    ("ko", "한국어"),
    ("lt", "Lietuvių"),
    ("lv", "Latviešu"),
    ("nl", "Nederlands"),
    ("pl", "Polski"),
    ("pt", "Português"),
    ("ro", "Română"),
    ("ru", "Русский"),
    ("sk", "Slovenčina"),
    ("sl", "Slovenščina"),
    ("sv", "Svenska"),
    ("tr", "Türkçe"),
    ("uk", "Українська"),
    ("vi", "Tiếng Việt"),
]
LANGUAGES = [iso for iso, _ in LANGUAGE_ENTRIES]
LANGUAGE_NAMES = {native: iso for iso, native in LANGUAGE_ENTRIES}
DEFAULT_LANGUAGE = "en"

# Backwards-compat aliases for the English names the schema used briefly
# during 2.0.0 development (Arabic, Korean, …). Resolves so existing
# configs from that window keep working.
_ENGLISH_NAMES = {
    "Arabic": "ar", "Bulgarian": "bg", "Croatian": "hr", "Czech": "cs",
    "Danish": "da", "Dutch": "nl", "English": "en", "Estonian": "et",
    "Finnish": "fi", "French": "fr", "German": "de", "Greek": "el",
    "Hindi": "hi", "Hungarian": "hu", "Indonesian": "id", "Italian": "it",
    "Japanese": "ja", "Korean": "ko", "Latvian": "lv", "Lithuanian": "lt",
    "Polish": "pl", "Portuguese": "pt", "Romanian": "ro", "Russian": "ru",
    "Slovak": "sk", "Slovenian": "sl", "Spanish": "es", "Swedish": "sv",
    "Turkish": "tr", "Ukrainian": "uk", "Vietnamese": "vi",
}


def resolve_language(value: str) -> str:
    """Accept a native name ('한국어'), an English name ('Korean'), or an
    ISO code ('ko'). Returns the canonical ISO code.

    Unknown values pass through unchanged so an error surfaces at the
    engine layer instead of here.
    """
    if value in LANGUAGES:
        return value
    if value in LANGUAGE_NAMES:
        return LANGUAGE_NAMES[value]
    if value in _ENGLISH_NAMES:
        return _ENGLISH_NAMES[value]
    return value

# MNN model cache location. The supertonic_mnn library defaults to
# ~/.cache/supertonic-mnn; the s6 run script exports HOME=/data so this
# lands under /data/.cache/supertonic-mnn and survives container recreations.
MNN_CACHE_DIR = "/data/.cache/supertonic-mnn"

# A single short warm-up sample. MNN has no dynamic-shape compilation
# cache to prime (unlike OpenVINO), so a multi-shape sweep is unnecessary.
WARMUP_TEXT = ("en", "Hello.")
