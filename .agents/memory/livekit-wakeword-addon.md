---
name: livekit-wakeword-addon
description: livekit-wakeword Wyoming wake-word add-on scaffolded+validated 2026-06-12; experimental/gitignored; OUR bridge with incremental engine (10x less CPU than upstream stateless API); serves oWW zoo + hey_livekit + custom /share models
metadata: 
  node_type: memory
  type: project
  originSessionId: 88d78d9d-5fd8-4d2d-bd99-664dec394d7e
---

As of 2026-06-12, `livekit-wakeword/` in ha-apps is a scaffolded, fully
validated (venv + docker + s6) Wyoming **wake word** add-on on the
[livekit/livekit-wakeword](https://github.com/livekit/livekit-wakeword)
runtime (Apache 2.0). `stage: experimental` → gitignored (`/livekit-wakeword/`
in root .gitignore); **git does not record it**. Successor to the deleted
wakewordlab add-on ([[wakewordlab-addon]] has the full compat verification).

Key engineering facts:
- **The Wyoming server is OUR bridge** (`wyoming_livekit_wakeword/`), not
  upstream. Engine is incremental/openWakeWord-style: per 1280 samples
  (80 ms) → mel over trailing 12640 samples (= exactly 76 frames; hop 160,
  effective win 640) → 1 embedding → classifiers on last-16 deque.
  ~4 ms/frame M-series (Pi 4 est ~36 ms) vs ~23 ms (Pi 4 ~200 ms) for
  upstream's stateless 2 s predict — don't switch back.
- Audio scale **[-1,1] float32**; oWW classifiers verified fine on it.
  Classifiers are window-position-sensitive → keep the 80 ms cadence.
- Built-ins in `const.KNOWN_MODELS` (sha256-pinned downloads → /data/models):
  hey_livekit (raw file at pinned livekit commit `_LK_REF` — upstream has no
  registry/release for models) + oWW v0.5.1 release zoo (alexa, hey_jarvis,
  hey_mycroft, hey_rhasspy). Custom `*.onnx` auto-load from
  `/share/livekit-wakeword` (input contract `(1,16,96)`) — destination for
  the planned self-trained Korean conv_attention model.
- `trigger_level` option = consecutive-frame mitigation for transient hard-
  negative spikes (hey_livekit's own negative fixture hits 0.90 for ~3
  frames at one alignment; reproduced with upstream stateless API too).
- Validated end-to-end: say-Daniel "hey jarvis" → Detection, fixture
  "hey livekit" via custom dir → Detection, silence → NotDetected; identical
  in venv and container; s6 boot parses options.json correctly.

**Korean wake word "빅스비" training** (user's choice of phrase): smoke run
completed end-to-end on the Mac (MPS) 2026-06-12 — VoxCPM2 synthesizes Korean
fine at ~30 s/clip, train/export/bridge-inference all work. Full pipeline
notes + gotchas (SSL_CERT_FILE via certifi, nltk cmudict, [export] extra) in
`livekit-wakeword/notes/training/SMOKE_RESULTS.md`; configs `bixby_smoke.yaml`
(validated) and `bixby_prod.yaml` (conv_attention/small, 25k samples, Korean
personas + manual negatives) are ready. **Production run is not viable on the
Mac** (~20 days of TTS; ACAV100M needs 16 GB vs ~12 free) — needs a CUDA GPU
box (~1 day, ~$5–20); decision pending.
