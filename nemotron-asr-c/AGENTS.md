# AGENTS.md

Guidance for AI coding agents working on the **Nemotron ASR (C)** add-on. Read
`CHANGELOG.md` for the *why* behind older decisions. Symlinked as `CLAUDE.md` —
edit `AGENTS.md`, the symlink follows.

## What this is

A Home Assistant add-on for **buffered** speech-to-text over Wyoming, running
NVIDIA Nemotron ASR on a **pure C runtime** ([`kdrkdrkdr/nemotron-asr-streaming.c`](https://github.com/kdrkdrkdr/nemotron-asr-streaming.c)).
It converts `.nemo` model files to a C-native `.bin` format at boot, supporting
**any Nemotron-architecture .nemo** (including fine-tuned variants).

The C runtime is dependency-free (libc/libm/pthread only), with per-arch SIMD
kernels (AVX2 on amd64, NEON on aarch64). This add-on is the **any-model**
sibling of `nemo-asr-cpp` (ggml/GGUF, buffered).

## Git / repo tracking

**This add-on:** `stage: experimental` → committed with `stage: experimental` in
`config.yaml`. The `nemotron-asr-c` scope is registered in allowed-scope tables,
release-please config/manifest, labels, labeler, and issue templates — commits
already use the scope. To promote: remove `stage: experimental` from
`config.yaml` (no gitignore change needed).

## Architecture

```
config.yaml / Dockerfile        packaging; Dockerfile BUILDS libnemotron_asr.so
                                from kdrkdrkdr/nemotron-asr-streaming.c source
tools/convert_nemo.py           vendored from upstream; .nemo → .bin conversion
pyproject.toml                  bridge package metadata
wyoming_nemotron_asr_c/
  __main__.py   download .nemo → convert to .bin(s) → load → serve
  engine.py     ctypes wrapper over nemotron_asr.h (C API)
  handler.py    Wyoming ASR; buffered (accumulate audio, transcribe on AudioStop)
  models.py     hf_hub_download .nemo → convert_nemo.py → data/${model}/${quant}/
  const.py      port, dirs, model registry, quants, chunk choices
rootfs/.../s6-rc.d/             nemotron-asr-c (longrun) + discovery (oneshot)
```

- **Boot-time conversion (Option C).** The add-on downloads the `.nemo` from
  HuggingFace at boot and runs `convert_nemo.py` to produce the quantized `.bin`.
  This needs PyTorch in the runtime image (~2 GB) but enables any fine-tuned
  .nemo model without pre-conversion.
- **Multiple quantization outputs.** One .nemo → N .bin files (one per quant).
  Stored as `data/${model_slug}/${quant}/model.bin`. Changing `quantization`
  re-converts on next start.
- **Buffered (not streaming).** The RNN-T greedy decoder produces looping
  artifacts when fed chunk-by-chunk (same finding as nemo-asr-cpp). Audio is
  accumulated in a bytearray and transcribed once on AudioStop.
  `supports_transcript_streaming=False`.
- **Hotword biasing.** Vendored patch (`patches/0003-rnnt-hotword-biasing.patch`)
  adds `nemo_set_hotwords()` to the C API. Phrases are tokenized via SentencePiece
  and applied globally at boot (same pattern as the now-removed nemotron-asr ONNX
  add-on).
- **Language.** The model's prompt index is set via `nemo_set_language()`. The
  Wyoming pipeline's per-request `Transcribe.language` is passed through.

## Quantization formats

| Key | Name | Weight bits | Activation | Notes |
|---|---|---|---|---|
| `f32` | Float32 | 32 | f32 | Bit-exact reference |
| `bf16` | BFloat16 | 16 | f32 | Linear weights only |
| `q8p` | Q8P (W8A8) | 8 | int8 | Packed per-row int8, default |

Upstream ships: f32, bf16, q8p (W8A8 Q8P packed).

## Build (Dockerfile)

- **Compiles libnemotron_asr from source.** Pinned to `NEMOTRON_C_REF`.
- The upstream Makefile builds a static executable (`nemotron_asr`). We need a
  **shared library** (`libnemotron_asr.so`) for ctypes — this requires Makefile
  modifications (add `-fPIC`, produce `.so`).
- SIMD kernels auto-detected by the Makefile (`-march=native`).

## Converter (tools/convert_nemo.py)

Vendored from upstream. Depends on **PyTorch** (`torch.load` for the .ckpt) and
**PyYAML** (`model_config.yaml`). Runs at boot inside the add-on container.

Key modifications vs upstream:
- Output multiple quantization formats in one invocation

## Sanity checks before PR

- `python3 -c "import ast,glob;[ast.parse(open(f).read()) for f in glob.glob('wyoming_nemotron_asr_c/*.py')]"`
- yamllint `config.yaml translations/*.yaml`; `shellcheck` the s6 scripts.
- `docker build .` for one arch.
- Smoke: `echo '{"type":"describe"}' | nc -w 1 localhost 10370 | grep -qi nemotron`.
- End-to-end: send a known wav through the HA voice pipeline.

## Don'ts

- Don't hardcode model shapes/prompt indices — read from `config.json` / model.
- Don't add `armv7`/`armhf`/`i386` without confirming SIMD kernel support.
- Don't pre-convert the model in the Dockerfile — conversion is at boot (Option C).
- Don't forget the `chmod +x` block in `Dockerfile` when adding an s6 script.
- Model is under **NVIDIA Open Model License**; honor its terms.
