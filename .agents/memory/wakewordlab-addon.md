---
name: wakewordlab-addon
description: "wakewordlab add-on was built then DELETED 2026-06-12 (poor detection quality); livekit/livekit-wakeword evaluated as the successor — Apache 2.0, clean PyPI wheel, validated 0.98/0.004 separation, but no Wyoming server and only one pretrained model"
metadata: 
  node_type: memory
  type: project
  originSessionId: 88d78d9d-5fd8-4d2d-bd99-664dec394d7e
---

**wakewordlab add-on: deleted 2026-06-12.** It was fully scaffolded and
docker-validated, but the user judged detection quality too poor and had it
removed (directory, root-.gitignore line, docker image). Don't re-package it.
If ever revisited, the packaging landmine was: no aarch64/cp313 wheels +
unbuildable sdist (ships `loader.c`, setup.py cythonizes the absent
`loader.pyx`) → install with `--no-build-isolation` and no cython to get the
pure-Python fallback loader. Commercial contact: launch@ubermorgen.land /
ubermorgen.land (Ubermorgen LTD; GitHub org profile only, not in the repo).

**Successor candidate: [livekit/livekit-wakeword](https://github.com/livekit/livekit-wakeword)**
(evaluated same day, verdict positive):
- Apache 2.0, LiveKit-backed; `pip install livekit-wakeword` is a pure-Python
  `py3-none-any` wheel (~1.9 MB, deps numpy+onnxruntime only, py3.11–3.13) —
  zero packaging hacks. Frontend ONNX (mel + Google speech embedding, same as
  openWakeWord) bundled in the wheel.
- Verified locally: repo fixture positive.wav → 0.9806, negative → 0.0042.
  macOS `say` voices score 0.04–0.14 (out-of-distribution robot TTS — they
  failed on wakewordlab too; not a model defect).
- API: stateless `WakeWordModel.predict(2 s float32/int16 @16 kHz) ->
  {name: score}`; ~23 ms/call on M-series → Pi 4 ≈ 180–230 ms, so poll every
  250–500 ms in a bridge (window 2 s, phrase stays in-window across strides).
- Gaps: **no Wyoming server** (a ~100-line bridge must be written; the
  openwakeword/wakewordlab handler pattern applies). Pretrained `hey_livekit`
  is distributed ad hoc inside the repo
  (`examples/ios_wakeword/.../Resources/hey_livekit.onnx`, swift fixtures,
  livekit-examples/hello-wakeword), not via a registry/release.
- **openWakeWord compatibility — VERIFIED both directions** (2026-06-12):
  livekit bundles the *byte-identical* frozen frontend (sha256 of
  melspectrogram.onnx + embedding_model.onnx match oWW v0.5.1 release
  assets) → (a) **oWW's pretrained .onnx zoo (alexa, hey_jarvis, hey_mycroft,
  hey_rhasspy, timer, weather; GH release dscripka/openWakeWord v0.5.1)
  loads and scores 0.998 in livekit's runtime** — so a livekit-based add-on
  is not single-model after all; (b) livekit-trained models export to
  oWW-loadable TFLite (static (1,16,96)) but **`dnn` head only** —
  conv_attention/rnn can't convert, ONNX-only. Sharp edge: oWW classifiers
  are window-POSITION-sensitive (fire when the phrase ends near the buffer
  end); a coarse-stride sweep scored 0.0000 on a clip the oWW lib scored
  0.9979 — a bridge must poll fine-grained (~80–160 ms stride), then 0.9984.
- Custom (incl. Korean) wake words: train with the included pipeline (single
  YAML; VoxCPM2 TTS voice-design for 30 langs incl. Korean, torch≥2.5 +
  CUDA recommended, SkyPilot example incl.). Auto adversarial negatives are
  English/CMUdict-biased → add manual Korean negatives; README admits
  multilingual accuracy < English (English-trained embeddings).

Related: [[nemotron-asr-addon]]
