# AGENTS.md

Guidance for AI coding agents working on the **NeMo ASR (cpp)** add-on. Read
`CHANGELOG.md` for the *why* behind older decisions. Symlinked as `CLAUDE.md` —
edit `AGENTS.md`, the symlink follows.

## What this is

A Home Assistant add-on running **NVIDIA Nemotron 3.5 Streaming ASR (0.6B)** as
a Wyoming **speech-to-text** service, on the **ggml** runtime via
[`mudler/parakeet.cpp`](https://github.com/mudler/parakeet.cpp) (C++/GGUF). It's
the **fast/light** sibling of the `nemotron-asr` add-on (which runs the same
model on onnxruntime): ggml is ~1.4× faster on CPU and the q4_k GGUF is ~720 MB
(vs ~1.5 GB) — chosen for resource-limited HAOS (N100, Pi 4/5).

Same model → same Korean/40-locale support and (near-)identical transcripts.
**No hotword biasing here** (parakeet.cpp has none upstream) — that lives in the
`nemotron-asr` (onnxruntime) add-on. If upstream adds it, we inherit it by
bumping `PARAKEET_REF`. **We do not fork parakeet.cpp** — we track upstream and
call its flat C API.

## Git / repo tracking

Stage-gated by the root `.gitignore`. **This add-on:** `stage: stable` →
tracked (registered in release-please + the scope/label/issue-template tables;
no `/nemo-asr-cpp/` line in the root `.gitignore`). Released via release-please
under the `nemo-asr-cpp` scope like its siblings.

## Architecture (the load-bearing part)

```
config.yaml / Dockerfile        packaging; Dockerfile BUILDS libparakeet.so + ggml
                                from mudler/parakeet.cpp source (ARG PARAKEET_REF)
pyproject.toml                  bridge package metadata
wyoming_nemo_asr_cpp/
  __main__.py   download GGUF -> load model ONCE -> warmup -> serve
  engine.py     ctypes wrapper over parakeet.cpp's flat C API (parakeet_capi.h)
  handler.py    Wyoming ASR; buffer utterance, transcribe on AudioStop
  models.py     hf_hub_download one GGUF quant into /data/models
  const.py      port, lib/model dirs, language dropdown, quant list
rootfs/.../s6-rc.d/             nemo-asr-cpp (longrun) + discovery (oneshot)
```

- **Model resident, no per-utterance reload.** `parakeet_capi_load()` runs once
  at boot (`engine.ParakeetASR.__init__`). Each utterance calls
  `parakeet_capi_transcribe_pcm_lang(ctx, pcm, n, 16000, 0, locale)`. This is
  *the* reason to use the C API over the CLI — per-call CLI reloads the ~720 MB
  model every command, which is brutal on a Pi.
- **Buffered, not streaming.** We accumulate PCM and transcribe once on
  `AudioStop`. The C API's live `stream_feed` works but chunked feeding produced
  token-boundary spacing artifacts and was slower; one buffered call matches the
  CLI output exactly. `supports_transcript_streaming=False`.
- **Language tags stripped.** The model emits inline `<ko-KR>` tags in the text;
  `engine._TAG_RE` removes them + collapses whitespace.
- **Threads:** the C API exposes no thread setter; ggml uses all cores (right
  for these 4-core hosts). Don't add a `num_threads` option that can't take
  effect.

## Build (Dockerfile)

- **Compiles libparakeet from source**, pinned to `PARAKEET_REF` (a commit SHA —
  no upstream release tags). `git fetch --recurse-submodules` pulls ggml.
- `cmake -DPARAKEET_SHARED=ON -DPARAKEET_BUILD_CLI=OFF -DGGML_NATIVE=OFF
  -DGGML_BLAS=OFF -DGGML_METAL=OFF`. `NATIVE=OFF` is portable (ggml still picks
  AVX2/NEON at runtime); `BLAS/METAL=OFF` keeps the runtime deps to just
  `libparakeet.so` + `libggml{,-base,-cpu}.so`, copied to `/usr/local/lib` +
  `ldconfig`. Runtime apt deps: `libgomp1`, `libstdc++6`.
- Builds run natively per-arch in the HA builder, so the compiled libs match the
  target CPU. **Follow upstream = bump `PARAKEET_REF`** and re-test the smoke.

## Pins & cache

- `PARAKEET_REF` in `Dockerfile` = the upstream commit. Bump to update.
- GGUF cached at `/data/models/nemotron-3.5-asr-streaming-0.6b-<quant>.gguf`
  (`backup_exclude: ["models/**"]`). Changing `quantization` re-downloads.
- C ABI is versioned (`parakeet_capi_abi_version()`, currently 4). If a
  `PARAKEET_REF` bump changes the ABI, update `engine.py` signatures.

## Sanity checks before PR

- `python3 -c "import ast,glob;[ast.parse(open(f).read()) for f in glob.glob('wyoming_nemo_asr_cpp/*.py')]"`
- yamllint `config.yaml translations/*.yaml`; `shellcheck` the s6 scripts.
- `docker build .` (compiles ggml — a few min per arch).
- Smoke: `echo '{"type":"describe"}' | nc -w 1 localhost 10360 | grep -qi nemo`.
- End-to-end: speak through the HA pipeline; confirm transcript + check the
  `RTF=` log line for the host's real speed.

## Don'ts

- **Don't fork parakeet.cpp.** Track upstream via `PARAKEET_REF` + the C API.
- **Don't use the CLI per-utterance** — it reloads the model each call.
- **Don't add `num_threads`** — the C API can't honor it.
- **Don't re-enable GGML_BLAS/METAL** without a reason — they add runtime deps
  for no CPU benefit here.
- The model is **NVIDIA Open Model License**; parakeet.cpp code is MIT. Honor
  both if this is ever published.
