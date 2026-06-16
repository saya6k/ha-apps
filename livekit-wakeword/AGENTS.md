# AGENTS.md

Guidance for AI coding agents working on the **LiveKit WakeWord** add-on.
Symlinked as `CLAUDE.md` — edit `AGENTS.md`, the symlink follows.

## What this is

A Home Assistant add-on running the
[`livekit/livekit-wakeword`](https://github.com/livekit/livekit-wakeword)
runtime (Apache 2.0) as a Wyoming **wake word** service. Unlike the retired
wakewordlab attempt, upstream here is only the *inference library* — the
Wyoming server (`wyoming_livekit_wakeword/`) is **our own bridge**.

The load-bearing fact (verified empirically, sha256-level): livekit-wakeword
bundles the **byte-identical frozen frontend** as openWakeWord
(melspectrogram.onnx + Google speech embedding → `(16, 96)` features), so
**openWakeWord's pretrained classifiers run unmodified** on this runtime
(hey_jarvis scored 0.995 here vs 0.998 in the oWW lib). That turns the
"single pretrained model" weakness into the oWW zoo + livekit + custom.

## Git / repo tracking

Tracked in git (`stage: experimental` in `config.yaml` controls HA store display only — it does not affect git tracking). Release-please is configured for this slug; commits on `main` scoped `livekit-wakeword` will generate CHANGELOG entries and version bumps.

## Layout

```
config.yaml / Dockerfile        packaging; pure pip install (universal wheel,
                                no git, no compilation anywhere)
pyproject.toml                  bridge package metadata
wyoming_livekit_wakeword/
  __main__.py   resolve models -> Engine -> warmup -> serve
  engine.py     incremental scoring on livekit's frontend (see below)
  handler.py    Wyoming wake events; threshold + trigger_level + refractory
  models.py     name -> pinned URL + sha256 download into /data/models;
                /share/livekit-wakeword/*.onnx auto-loaded as custom
  const.py      audio constants, KNOWN_MODELS registry
rootfs/.../s6-rc.d/             livekit-wakeword (longrun) + discovery (oneshot)
translations/{en,ko}.yaml       option UI strings
```

## Engine: incremental, NOT upstream's stateless predict

Upstream's `WakeWordModel.predict()` recomputes mel + 16 embeddings over a
full 2 s window per call (~23 ms on M-series ⇒ ~200 ms on Pi 4 — a saturated
core when polled). `engine.py` instead keeps openWakeWord-style streaming
state: per 1280 new samples (80 ms), mel over the trailing **12640 samples
(= exactly 76 frames; hop 160, effective window 640)** → one embedding →
classifiers over the last-16 deque. ~4 ms/frame on M-series, est. ~36 ms on
Pi 4 — comfortably real-time. Numerical equivalence to the stateless API at
the same alignment is verified (positive fixture 0.983 vs 0.981).

Bridge subtleties:

- **Audio scale is [-1, 1] float32** (int16 / 32768) — livekit's convention.
  oWW classifiers tolerate it fine (verified); do NOT feed int16-range floats.
- **Classifiers are window-position-sensitive** (fire as the phrase completes
  near the buffer end). The 80 ms cadence handles this; never score coarser.
- The upstream `hey_livekit` model can transiently spike on hard negatives at
  some alignments (its own negative fixture hits 0.90 for ~3 frames at one
  position — reproduced with upstream's stateless API too, not a bridge bug).
  `trigger_level` (consecutive frames ≥ threshold) is the exposed mitigation.
- Per-connection state lives in `StreamState`; ONNX sessions are shared
  (`InferenceSession.run` is thread-safe). Scoring runs inline in the async
  handler — fine at 4 ms/frame; revisit with an executor if many satellites.

## Models / pins

- `const.KNOWN_MODELS`: name → pinned URL + sha256 + phrase.
  - `hey_livekit` — raw file at a pinned livekit-wakeword commit
    (`_LK_REF`); upstream has **no model registry or release asset**, the
    repo file is the distribution channel. Bump `_LK_REF` + sha256 together.
  - oWW zoo — `dscripka/openWakeWord` GitHub release v0.5.1 assets
    (alexa, hey_jarvis, hey_mycroft, hey_rhasspy; Apache 2.0). timer/weather
    exist upstream but aren't wake words; deliberately excluded.
- Downloads land in `/data/models` (persisted, `backup_exclude`), verified
  by sha256, first boot needs network.
- Custom models: `/share/livekit-wakeword/*.onnx` (map `share:ro`), loaded
  automatically, model name = file stem. Expected input `(1, 16, 96)` —
  livekit-trained (any head incl. conv_attention) and oWW classifiers both
  qualify. This is where self-trained (e.g. Korean) models go.

## Sanity checks before PR

- `python3 -c "import ast,glob;[ast.parse(open(f).read()) for f in glob.glob('wyoming_livekit_wakeword/*.py')]"`
- yamllint `config.yaml translations/*.yaml`; `shellcheck` the s6 scripts.
- `docker build .` (fast — pure wheels).
- Smoke: `echo '{"type":"describe"}' | nc -w 1 localhost 10400 | grep -qi livekit`.
- End-to-end: stream a wake word clip over Wyoming, expect a `Detection`
  event (a `say -v Daniel "hey jarvis"` clip reliably trips hey_jarvis).

## Branding

`icon.png` and `logo.png` use the LiveKit logo, used per the
[LiveKit brand guidelines](https://livekit.io/brand) which permit free use
when talking about or representing LiveKit. If you replace them, update
`NOTICE` accordingly.

## Don'ts

- **Don't switch to upstream's stateless `predict()` polling** — 10x CPU for
  identical scores; the incremental engine is the point of this bridge.
- **Don't change the [-1, 1] audio scale** or the 80 ms cadence.
- **Don't add models to the dropdown without pinning a sha256** in
  `KNOWN_MODELS`.
- Upstream code + all built-in models are Apache 2.0 — keep attribution per
  model in the Wyoming Info (already wired via `ModelSpec`).
