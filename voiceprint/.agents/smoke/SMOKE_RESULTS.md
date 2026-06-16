# voiceprint smoke run — 2026-06-12 (Mac + Docker)

Harness: `dummy_stt.py` (fixed-transcript upstream on :10300) +
`client_test.py` (streams a WAV, prints the transcript). Enrollment
fixtures: macOS `say` voices (daniel ×5, karen ×3) + held-out clips.

| Check | Result |
|---|---|
| linters (yamllint/shellcheck/hadolint/ast) | OK |
| venv enroll + separation | daniel 0.917 / karen 0.879 self; 0.28 cross |
| gate pass (enrolled → transcript) | OK |
| gate reject (threshold 0.6, samantha) | OK — empty transcript |
| pass-through (no voiceprints) | OK + warning |
| tag_speaker | `[daniel] hello from upstream` |
| docker build | OK (409 MB image) |
| container s6 boot + options.json + e2e | OK |

Gotchas (fixed in code, will not recur):
- `AsrModel`/`AsrProgram` import from `wyoming.info`, not `wyoming.asr`.
- wyoming `AsyncClient` has no async context manager — connect/disconnect.
- `bashio::config` needs a live Supervisor; standalone docker gets empty
  strings. The s6 run script reads `/data/options.json` with jq directly
  (works in both environments).

Known caveat: same-TTS-engine synthetic voices score inflated cross-speaker
similarity (samantha→karen 0.532). Real-human impostor scores run lower;
threshold tuning guidance is in DOCS.md. Validate with real voices on the
actual satellite mic before trusting the 0.5 default.
