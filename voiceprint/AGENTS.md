# AGENTS.md

Guidance for AI coding agents working on the **Voiceprint** add-on.
Symlinked as `CLAUDE.md` — edit `AGENTS.md`, the symlink follows.

## What this is

A Wyoming **STT proxy** with speaker verification, entirely our own code
(`wyoming_voiceprint/`). It sits between HA and a real STT service:

```
HA ──► voiceprint :10350 ──► upstream STT (upstream_uri)
```

Design verdict (2026-06-12, after reviewing jxlarrea/wyoming-voice-match):
verification belongs at the **ASR stage**, not the wake-word stage — the
wake phrase (<1 s) is too short for text-independent speaker embeddings,
while the command utterance (2–5 s) is exactly right. Unlike
wyoming-voice-match (buffer → verify → forward, which defeats streaming
decoders), this proxy is a **pass-through gate**: chunks are forwarded
unchanged as they arrive; verification runs in an executor between
`AudioStop` and the upstream `Transcript`, and a mismatch swallows the
transcript (empty `Transcript`). Added latency ≈ max(0, embed − decode tail)
≈ 0 in practice.

## Layout

```
config.yaml / Dockerfile        packaging; pure pip, model fetched at runtime
pyproject.toml                  bridge package metadata
wyoming_voiceprint/
  __main__.py   fetch model -> enroll -> serve; InfoProvider mirrors upstream
                languages (re-queried per Describe until non-empty); a
                background startup check retries until the upstream is up,
                then streams a silent test utterance and logs whether a
                Transcript came back (never blocks or kills the proxy)
  models.py     ensure_model(): download the .tflite into /data on first run,
                verify const.MODEL_SHA256, atomic rename (cached thereafter)
  handler.py    pass-through proxy + parallel verification gate
  embedder.py   kaldi fbank (kaldi-native-fbank) + CAM++ on LiteRT
  enroll.py     /share/voiceprint/<speaker>/*.wav -> mean embedding
  const.py      model contract constants, paths, MODEL_URL/SHA256
rootfs/.../s6-rc.d/             voiceprint (longrun) + discovery (oneshot)
translations/{en,ko}.yaml       option UI strings
```

The 14 MB model is **not** in the image or the repo — it downloads once into
`/data` (`models.MODEL_URL`, a pinned GitHub release asset) and is verified
against `const.MODEL_SHA256`. A local dev copy under `models/` is gitignored.
**Publishing the asset is a one-time manual step:** create a
`voiceprint-model-v1` release and upload `campplus_zh_en_fp16.tflite`, or the
first run can't fetch it.

## Git / repo tracking

Stage-gated by the root `.gitignore`. **This add-on:** `stage: stable`
→ committed. Its slug is registered in the repo-root release-please config,
`.release-please-manifest.json`, `labels.yml`, `labeler.yml`, and the issue
templates. The model is fetched at runtime (see above), so nothing large is in
the tree.

`icon.png` / `logo.png` are Google's Material Icons **fingerprint** glyph
(Apache-2.0), recoloured to teal `#0EA5A4`; the logo adds a "Voiceprint"
wordmark. Add an Apache-2.0 NOTICE/attribution for it when promoting to stable.

## The model (do not swap casually)

`models/campplus_zh_en_fp16.tflite` is **our conversion** of 3D-Speaker's
CAM++ zh_en advanced (Apache 2.0), sha256 in `const.MODEL_SHA256`. Source:
`3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx` from the
sherpa-onnx `speaker-recongition-models` release (tag spelled exactly so).

Why TFLite/LiteRT instead of onnxruntime: identical embeddings (cos =
1.000000 fp32, 0.999997 fp16 — verified) at roughly half the ML payload
(litert 29 MB + model 14 MB vs ort 65 MB + 28 MB). There is **no ggml
speaker-embedding runtime** to go lighter; this was checked.

Conversion is NOT mechanical — the dynamic-shape graph fails both onnx2tf
backends. Recipe (.agents/runtime-experiment, gitignored): fix input shape to
`(1,500,80)` with onnxsim → constant-fold remaining `Shape` nodes with
onnx-graphsurgeon → onnx2tf `-tb tf_converter` (the flatbuffer_direct fp16
output does NOT load — missing dequant; use the tf_converter one).

Model contract baked into `embedder.py` — all four must move together:
- input `(1, 80, 500)` = **transposed** fbank (onnx2tf flipped the layout);
- exactly 500 frames (5 s): repeat-pad shorter, crop longer;
- 80-dim kaldi fbank, dither 0, snip_edges, **global-mean subtracted**;
- audio float32 [-1, 1] mono 16 kHz.

## Handler subtleties

- Forward the **original** chunk events to upstream; the 16 kHz converted
  copy is only for our buffer. Never re-encode the forwarded stream.
- The final `return False` after writing the transcript closes the client
  connection (Wyoming STT sessions are one-shot).
- **Languages are load-bearing for HA**: a pipeline only offers STT engines
  that advertise the pipeline's language — an empty list makes the proxy
  unselectable (not "all languages"). The advertised list is **always mirrored
  from the downstream ASR** (no override option); `InfoProvider` re-queries it
  on every `Describe` until it gets a non-empty list and caches it. After what
  the downstream advertises changes, the HA Wyoming integration entry must be
  **reloaded** (HA caches Info at setup).
- No enrolled voiceprints → pass-through with a warning, never block.
- Verification runs via `run_in_executor` — keep it off the event loop;
  `Embedder` holds a lock (LiteRT interpreters are not thread-safe).

## Sanity checks before PR

- `python3 -c "import ast,glob;[ast.parse(open(f).read()) for f in glob.glob('wyoming_voiceprint/*.py')]"`
- yamllint `config.yaml translations/*.yaml`; `shellcheck` the s6 scripts.
- `docker build .` (pure wheels; the model downloads at runtime, not build).
- Smoke: `echo '{"type":"describe"}' | nc -w 1 localhost 10350 | grep -qi voiceprint`.
- End-to-end: dummy upstream STT + enrolled `say` voice → transcript passes;
  different `say` voice → empty transcript (see .agents/ for the harness).

## Don'ts

- **Don't buffer-then-forward** (wyoming-voice-match style) — pass-through
  is the point; it keeps streaming STT latency at zero.
- **Don't put verification in the wake-word add-on** — the wake phrase is
  too short; the decision record is at the top of this file.
- **Don't regenerate the model without re-running the fidelity check**
  (embeddings must match ONNX within cos ≥ 0.999).
- `/share` is mapped **`share:rw`** (was `ro`) so the `capture_dir` option can
  write in-domain enrollment clips to /share. Outside capture, nothing is
  written to /share — voiceprints are still computed read-only at startup.
- **In-domain enrollment:** clean/close-mic clips score poorly against live
  audio (HA noise-reduction + auto-gain + far-field shift CAM++ embeddings).
  The `capture` option (bool, default off) dumps every received utterance to the
  fixed `const.CAPTURE_DIR` = `/share/voiceprint/_captures` (run script
  `mkdir -p`s it; `handler._save_capture` writes the exact buffered 16 kHz
  audio). It lives under the enroll dir but is **not** enrolled as a speaker —
  `enroll.load_voiceprints` skips `_`/`.`-prefixed dirs. Turn `capture` on, speak
  a few times, move the good clips into `/share/voiceprint/<speaker>/`, turn it
  back off. Same acoustic domain as live → scores recover.
