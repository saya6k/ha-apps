---
name: nemo-asr-cpp-nemo-source
description: .nemo source support for nemo-asr-cpp was evaluated and rejected — nemo_toolkit image bloat kills the value prop
metadata:
  type: project
---

# .nemo Model Source Support (evaluated, not pursued)

.nemo → GGUF conversion for nemo-asr-cpp was specced and reviewed on 2026-06-18.
The user decided not to proceed after seeing the tradeoffs.

## What was designed

Add an optional `nemo_repo` field to `ModelSpec`. When set, the add-on would:
1. Download .nemo from HF (via `convert_parakeet_to_gguf.py` which handles this
   automatically — `ASRModel.from_pretrained()`)
2. Convert to F32 GGUF → `/data/models/<basename>/model.gguf`
3. Optionally quantize via `parakeet-cli quantize` → `model_<quant>.gguf`
4. Cache with sentinel files (`.conversion-ok`) for idempotent restart

Two source paths: `nemo_repo=None` (existing GGUF download) and `nemo_repo=<hf-id>`
(new .nemo path). Engine/handler/Wyoming pipeline unchanged — they only see a GGUF
path.

## Why it was rejected

**`nemo_toolkit[asr]` + PyTorch adds ~3 GB to the Docker image.** The conversion
script (`scripts/convert_parakeet_to_gguf.py`) needs `nemo.collections.asr.models.ASRModel`
to load the checkpoint and extract weights/config. The add-on already ships a
~720 MB GGUF; adding 3 GB of ML framework for a one-time boot conversion puts the
image at ~4 GB — unjustifiable for HAOS targets (N100, Pi 4/5 with limited storage).

Alternative considered: build-time conversion (bake the GGUF into the image via a
builder stage, keep runtime small). Tradeoff: model is fixed at build time, needs
a rebuild to change. Rejected as too inflexible for v1.

## Reference

- Conversion: https://github.com/mudler/parakeet.cpp/blob/master/docs/conversion.md
  - Script: `scripts/convert_parakeet_to_gguf.py` — `--model <hf-id|.nemo> --output <gguf> [--dtype f32|f16|q8_0]`
  - Deps: `gguf`, `nemo_toolkit[asr]`, `numpy`
- Quantization: https://github.com/mudler/parakeet.cpp/blob/master/docs/quantization.md
  - f16/q8_0: converter `--dtype` flag
  - q4_k/q5_k/q6_k: `parakeet-cli quantize <in.gguf> <out.gguf> <type>`
  - K-quants need `PARAKEET_BUILD_CLI=ON` (currently OFF)

## How to apply

If revisiting: the spec was written to `specs/nemo-source-support.md` then deleted.
The design is sound — the only blocker is image size. If `nemo_toolkit` ever ships
a lightweight checkpoint-loader-only package, or if the target hardware moves to
devices with more storage, pick up from the spec above.

For the English-only Nemotron model (`nvidia/nemotron-speech-streaming-en-0.6b`),
the GGUF path is still blocked on incompatible quant scheme (see [[nemo-asr-cpp-chunk-size]]
for context on the add-on's model registry). The .nemo path would bypass that, but
at the cost above.
