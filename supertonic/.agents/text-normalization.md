# Text normalization — design & library decision

Why supertonic grows a number-spellout pass, why `unicode-rbnf` (not
`num2words`), and the scope boundaries. CHANGELOG carries the headline;
this file carries the decisions, the empirical evidence, and the rejected
options.

## The gap we're filling

Both upstream `supertone-inc/supertonic` (`py/helper.py`) and the MNN port
we actually run (`vra/supertonic-mnn`, `src/supertonic_mnn/text.py`) use the
**same `UnicodeProcessor`**: NFKD-normalize, strip emoji/symbols, fix
punctuation spacing, then feed the text to the model **character-by-character**
(`ord(char)` → unicode indexer). There is **no number/currency/abbreviation
expansion anywhere**. Upstream's own code admits it:

```python
# py/helper.py, _preprocess_text:
# TODO: Need advanced normalizer for better performance
text = normalize("NFKD", text)
```

The "handles real-world text without preprocessing" claim means the acoustic
model learned to read characters — and is demonstrated **in English only**
(finance / phone / units). For the other 30 languages, multi-digit number
pronunciation is unverified. That is exactly the "advanced normalizer" gap.

Because the model is **character-level**, normalization MUST happen in the
frontend, before the model — the same architecture conclusion Piper 2 reaches
(see below). This is not redundant with anything the model does.

## Reference: rhasspy/piper2-prototype (the design we mirror)

Piper 2 (Apache relicense of Piper, char-level ONNX phonemizer instead of
espeak-ng) does number normalization in `libpiper2/src/piper2.cpp` with
**ICU `RuleBasedNumberFormat(URBNF_SPELLOUT)`** — the C++/CLDR origin of the
exact rule data `unicode-rbnf` reimplements in Python. Its loop:

```
sentence split (ICU BreakIterator)
  → word split → only tokens flagged UBRK_WORD_NUMBER
    → NumberFormat.parse → RBNF SPELLOUT (year rule for year-like ints, else default)
    → on parse/format failure: keep the original token
  → grapheme map → char ids
```

What we take from it:
- **Library choice validated** — rhasspy's own next-gen TTS uses RBNF spellout.
  `unicode-rbnf` = same thing without the ICU/C++ build.
- **Fallback on failure → keep raw token** (we do the same with try/except).
Boundary design matches Piper 2 (decided 2026-06-16 after a user asked why
"350m" isn't normalized): the regex normalizes a number only when it is NOT
glued to an ASCII letter/digit/dot. This approximates Piper 2 / ICU UAX#29
word-number detection — rules WB9/WB10 (Numeric×ALetter, ALetter×Numeric have
no break) keep "350m", "v3", "M1", "3.5.2" as single alphanumeric tokens that
Piper 2 also leaves unspelled. CJK-glued numbers ("11번") still normalize
because CJK breaks per character. So "350m" staying literal is correct and
Piper-aligned; full unit expansion ("350m"→"...meters") needs a unit dictionary
and is out of scope (Piper 2 doesn't do it either).

What we deliberately DON'T take:
- Piper2's accent-strip + lowercase transliteration is tuned for its en_US
  char-LSTM. Supertonic is multilingual and its `UnicodeProcessor` already does
  its own cleanup — our pass touches **numbers only**; accent stripping would
  break non-Latin scripts.
- Piper2 detects number tokens via ICU's word-break NUMBER status. We avoid an
  ICU dependency (keep it pure-Python) and use a **regex** instead — the one
  intentional divergence.

Edge-design takeaways (orientation, not action): Piper 2 stays light by
dropping espeak-ng for two small LSTM ONNX models, leaning on one library
(ICU) for all locale-aware text work, exposing a flat C API, downloading
models at runtime, and pulling sentence-by-sentence for low first-audio
latency. Mirrors patterns already in this monorepo (nemo-asr-cpp's flat C
API; supertonic's HF runtime cache + sentence streaming).

## Library decision: unicode-rbnf, drop num2words

Measured locally (`num2words 0.5.14`, `unicode-rbnf 2.4.0`) across the 31
Supertonic v3 languages, integer `1234`:

- **unicode-rbnf: 31/31 covered.**
- **num2words: 26/31** — missing `bg, el, et, hi, hr` (all real Supertonic
  languages → they'd get no number normalization at all).

num2words is marginally more robust on some decimals (e.g. `ru 3.5`:
unicode-rbnf raises `ConversionSyntax`, num2words returns words). Accuracy on
integers is a wash — both have minor per-language quirks (e.g. unicode-rbnf
emits a redundant "one thousand" in cs/sk; num2words drops spaces in some).

Decision: **unicode-rbnf only**, num2words removed. Integer coverage is the
dominant case and decides it; decimal gaps fall back to the raw digits with a
one-time log (never worse than today). One number library, MIT-licensed,
matches the Piper/rhasspy ecosystem and the user's explicit choice.

Rejected: **unicode-rbnf primary + num2words fallback** (retry on exception to
cover rbnf's decimal gaps). Real but narrow benefit; costs a second number
library and more code. Simplicity wins; revisit only if decimal mispronunciation
in a few languages proves to matter in practice.

Note: `num2words` is currently pip-installed in the Dockerfile but used
**nowhere** and isn't in `pyproject.toml` — an orphan from earlier work. Task 1
removes it.

## Scope (MVP)

- **In:** cardinal integers + simple decimals, language-aware, on by default
  with a `text_normalization` toggle. Per-call try/except → leave the token raw
  on any failure.
- **Out / deferred (with evidence):**
  - **Years.** A blanket "4-digit int → YEAR ruleset" heuristic is a trap on a
    multilingual engine. Measured `unicode-rbnf` YEAR vs CARDINAL for `2026`:
    en YEAR "twenty twenty-six" is better, but **ja YEAR "二二六" is broken**,
    **ru YEAR uses the genitive "…двадцать шестого"** (wrong for a plain year),
    and de/fr/ko/es/it YEAR == CARDINAL. Piper 2 gets away with the year rule
    because it's en_US-only. So: CARDINAL for everything in MVP; year handling,
    if ever, must be English-gated.
  - **Currency / dates / units / abbreviations.** English-centric, locale-
    fragile (num2words currency assumes EUR: `$5` → "five euro"); the model
    already handles English acceptably. Low ROI vs. large per-locale effort.

## Insertion point

`handler._handle_synthesize`, after language is resolved to an ISO code and
after the `text = " ".join(text.strip().splitlines())` cleanup, before
auto-punctuation and the `engine.synthesize` call. Engine stays a thin model
adapter; normalization is language-dependent and language only exists in the
handler. Supertonic's own `UnicodeProcessor` still runs inside the engine —
no conflict, our pass only rewrites number substrings.
