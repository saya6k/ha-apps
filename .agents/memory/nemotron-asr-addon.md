---
name: nemotron-asr-addon
description: New nemotron-asr Wyoming STT add-on scaffolded to replace sherpa-onnx ASR
metadata: 
  node_type: memory
  type: project
  originSessionId: 2242e1f6-2a09-479a-89f7-311f6187a041
---

A new `nemotron-asr/` add-on was scaffolded (2026-06-08) in the ha-apps monorepo
as a replacement for `sherpa-onnx` STT, whose ASR accuracy the user found
unsatisfactory.

- Runs NVIDIA Nemotron 3.5 Streaming ASR 0.6B from its **ONNX export**
  (`nub235/nemotron-3.5-asr-streaming-onnx`) on **CPU** via onnxruntime — no
  GPU/NeMo/CoreML. (The NeMo original needs an NVIDIA GPU; the CoreML variant is
  Apple-only — both unusable in HA containers.)
- Architecture: cache-aware streaming Conformer-Transducer, two graphs
  (encoder.onnx + fused decoder_joint.onnx), plain RNN-T (blank=13087), language
  selected via encoder `prompt_index` (ko→14). Hand-written numpy log-mel
  featurizer + greedy decode in `wyoming_nemotron_asr/engine.py`.
- **Validated end-to-end** against the real model: English JFK sample
  transcribed accurately; Korean (macOS `say` Yuna) near-perfect. Wyoming port 10350.
- **Incremental streaming** implemented (`supports_transcript_streaming=True`):
  per-connection `NemotronStream` decodes stable 56-frame chunks as audio
  arrives → `TranscriptChunk` deltas + final `Transcript`. Chunked decode is
  bit-identical to offline (verified EN+KO); incremental featurizer FFTs only
  new frames (no O(n²)). RTF ~0.18 offline / ~0.34 streaming on dev Mac.
- **Status: promoted to `stage: stable`** (2026-06-09) → removed from root
  .gitignore (tracked now), registered in release-please config+manifest (0.1.0),
  root AGENTS.md/CONTRIBUTING.md scope tables, labels.yml/labeler.yml, and the
  three issue templates. Commits use scope `nemotron-asr`.
- **Pi5 (full clock 2400MHz, not throttled) measured: RTF ~1.16 warm, ~2.81 cold**
  (Korean "안녕 반가워" → "안녕 방가워", minor int4 error). Since it's streaming,
  perceived post-speech tail ≈ (RTF−1)×duration ≈ ~0.5s for a 3s command — usable
  for short commands, degrades on long dictation. Confirms **N100's 7.51 was
  throttling** (same model, full-clock Pi5 = 1.16). Added boot **warm-up**
  (`engine.warmup`) to kill the cold-start penalty on the first command.
- A HA pipeline `[object Object]` STT error turned out to be **browser mic over
  HTTP (insecure context)** — getUserMedia blocked, no audio ever reached the
  add-on (no logs). Not an add-on bug; fixed by using HTTPS / localhost / mobile app.
- **N100 measurement (first run): RTF 7.51** (22.8s for 3s audio) — unusable.
  Profiling shows the **encoder dominates (~82%)**; INT4 MatMulNBits is already
  accuracy_level=4 (int8/VNNI), so not a quant problem. The encoder is
  matmul/clock-bound; RTF 7.5 ≈ host pinned at base clock (turbo off / powersave
  governor). Added `diag.py` boot CPU diagnostics (governor/freq/ISA/no_turbo) to
  confirm. **Next: user redeploys, checks boot diag for throttling; fix is
  host-side (BIOS turbo, performance governor, cooling).** Expected ~0.5–1.0 RTF
  with turbo. If still too slow even unthrottled, the 0.6B model may just be too
  heavy for N100 and sherpa/whisper-tiny would be the pragmatic fallback.

Quantization findings (benchmarked same Mac, 4 threads): **quant does NOT change
encoder speed** — nub235 INT4 (MatMulNBits) RTF 0.120 vs soniqo INT8
(MatMulInteger/dynamic) RTF 0.127, ~identical. soniqo INT8 has a documented
accuracy cost (+5.6 WER EN); FP16 = best quality but slow on CPU (no native x86
fp16). So for CPU, **INT4 is the speed/quality sweet spot**; the N100 RTF 7.5 is
host throttling, not quant. Alternative exports (soniqo INT8/FP16,
onnx-community INT4, GAURAV-321 docker) all use the same ORT kernel class → same
speed; soniqo also ships **LiteRT/TFLite** variants (XNNPACK = the real on-device
accel path, ARM-favored) but that needs a runtime+engine rewrite. soniqo/
onnx-community use a 3-graph layout (separate decoder.onnx + joint.onnx,
language_mask one-hot, separate pre_cache input, 320ms chunk) — NOT drop-in with
our fused decoder_joint engine.

`att_context_size` (e.g. [56,13]) is **baked at ONNX export**, not a runtime
knob (cache shapes static, single value in config.json) — can't be exposed; needs
a `.nemo` re-export. Nemotron has **no Whisper-style text prompt**; its only
"prompt" is the language one-hot (= the `language` dropdown). Added **hotword
biasing** instead: `hotwords` + `hotword_boost` (default 2.0) add a per-token
logit bonus in the greedy decode. Verified: `거실 불` at boost 5.0 flipped a
misread `것이`→`거실`; boost 2.0 was too weak for that case; unrelated English
unaffected. The real "faster/snappier" path = the soniqo INT8 **[56,3]** (0.32s
chunk) model, but it's a 3-graph layout needing a second engine path (offered,
not yet built). Added boot **warm-up** (kills first-command cold start).

Added a `transcript_streaming` option (default on) → `--no-transcript-streaming`
flag: when off, send only the final Transcript (no TranscriptStart/Chunk/Stop).
Added to debug a Pi-pipeline `[object Object]` error (HA frontend masking the
real STT error; the real error + RTF are in the add-on log).

Repo conventions/template for STT add-ons: mirror the sibling `sherpa-onnx`
add-on. Root AGENTS.md carries the monorepo rules.
