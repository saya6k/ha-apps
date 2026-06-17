# AGENTS.md

Guidance for AI coding agents working on the **NeMo ASR (cpp)** add-on. Read
`CHANGELOG.md` for the *why* behind older decisions. Symlinked as `CLAUDE.md` —
edit `AGENTS.md`, the symlink follows.

## What this is

A Home Assistant add-on for **streaming, hotword-boosted** speech-to-text over
Wyoming, running NVIDIA NeMo streaming ASR on the **ggml** runtime via
[`mudler/parakeet.cpp`](https://github.com/mudler/parakeet.cpp) (C++/GGUF). It's
the **fast/light** sibling of the `nemotron-asr-c` add-on (which runs Nemotron on
a pure C runtime): ggml is ~1.4× faster on CPU and the q4_k GGUF is ~720 MB
(vs ~1.5 GB) — chosen for resource-limited HAOS (N100, Pi 4/5).

The add-on's identity is **streaming + hotword boost**, so every entry in the
`model` dropdown (`const.MODELS`) is a streaming RNN-T transducer our vendored
hotword patch can bias. Current models: **Nemotron 3.5 Streaming 0.6b**
(multilingual, the only entry; same Korean/40-locale support as `nemotron-asr-c`).
parakeet.cpp auto-detects the architecture from the GGUF and `decoder=0` picks
the right head, so the engine is model-agnostic — `ModelSpec` flags
(`multilingual`, `hotwords`) only drive UX/metadata.

There is **no `language` option**: the model auto-detects and the Wyoming
pipeline's per-request language (`Transcribe.language`, set to the pipeline's
STT language) is passed straight through (`handler.py`), so a fallback knob was
redundant. The full locale list is still advertised in the Wyoming `Info` for
the multilingual model.

An English-specific **Nemotron-Speech-Streaming-En-0.6b** is wanted but **not
yet shipped**: the only GGUF (`m1el/nemotron-speech-streaming-0.6B-gguf`,
MIT) is converted for a *different* runtime (`library_name: nemotron-asr.cpp`)
with an incompatible quant scheme (`Q4_0/Q8_0/f32`, `-v0.1.` infix, separate HF
repo). Adding it needs per-model `repo`/quant handling in `const.MODELS` +
`models.ensure_gguf`, and a `docker build` smoke test to confirm our
parakeet.cpp build can even load it. Blocked on that verification.

**Hotword biasing is a vendored patch** (`patches/0001-rnnt-hotword-biasing.patch`,
applied by the Dockerfile after checkout — upstream parakeet.cpp has none).
**We do not fork parakeet.cpp** — we track upstream and call its flat C API;
the patch is the one deliberate, upstream-PR-shaped exception (see below).

## Git / repo tracking

Stage-gated by the root `.gitignore`. **This add-on:** `stage: stable` →
tracked (registered in release-please + the scope/label/issue-template tables;
no `/nemo-asr-cpp/` line in the root `.gitignore`). Released via release-please
under the `nemo-asr-cpp` scope like its siblings.

## Architecture (the load-bearing part)

```
config.yaml / Dockerfile        packaging; Dockerfile BUILDS libparakeet.so + ggml
                                from mudler/parakeet.cpp source (ARG PARAKEET_REF)
patches/                        vendored upstream patches, `git apply`'d in the
                                builder stage right after checkout
pyproject.toml                  bridge package metadata
wyoming_nemo_asr_cpp/
  __main__.py   download GGUF -> load model ONCE -> warmup -> serve
  engine.py     ctypes wrapper over parakeet.cpp's flat C API (parakeet_capi.h)
  handler.py    Wyoming ASR; buffer utterance, transcribe on AudioStop
  models.py     hf_hub_download <basename>-<quant>.gguf into /data/models
  tokenizer.py  hotword phrase -> token ids (greedy match over the GGUF's
                embedded vocab via the `gguf` package; no extra downloads)
  const.py      port, lib/model dirs, MODELS registry, language dropdown, quants
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
- **`chunk_size` option = accuracy↔speed dial via a GGUF KV edit.** Nemotron's
  cache-aware lookahead (right att-context) is the scalar GGUF KV
  `parakeet.encoder.att_context_right`. The C++ loader (`model_loader.cpp`) reads
  that scalar and the **offline** encoder applies the resulting chunked-limited
  mask (`relpos_attention.cpp`; parity.md 5a confirms offline honors it), so it
  changes our buffered transcript. `models.set_att_context_right()` patches that
  4-byte INT32 KV in place at boot (no re-download/re-quant); `const.CHUNK_CHOICES`
  maps the dropdown to `{0,3,6,13}` = 80/320/560/1120 ms (chunk = right+1, ms =
  chunk×80). Shipped default is `att_context_right=3` (320 ms). Only the model's
  **trained** presets are exposed — `att_context_presets` (`[[56,3],[56,0],[56,6],
  [56,13]]`) is informational and not read by the loader; `[56,1]`=160 ms is not a
  trained preset, so it's omitted. The `PARAKEET_ATT_CONTEXT` env var is a
  *different* mechanism (symmetric long-audio OOM banding) — do not use it here.
- **Language tags stripped.** The model emits inline `<ko-KR>` tags in the text;
  `engine._TAG_RE` removes them + collapses whitespace.
- **Threads:** the C API exposes no thread setter; ggml uses all cores (right
  for these 4-core hosts). Don't add a `num_threads` option that can't take
  effect.
- **Hotword biasing (vendored patch, C ABI v5).** The patch adds
  `parakeet_capi_set_hotwords(ctx, ids, lens, n_phrases, boost)` — token-id
  sequences, set once at boot, applies to every transcribe. The bridge
  tokenizes phrases against the GGUF's embedded vocab
  (`parakeet.tokenizer.pieces`, same index order as the logits). The GGUF has
  no SentencePiece scores, so exact unigram segmentation is impossible —
  instead each phrase is registered as **up to two greedy variants**
  (boundary-marker and marker-less): whichever matches the model's actual
  emission stream does the biasing, the other is inert. Two sharp edges,
  both verified empirically: (1) a leading bare `▁` token is dropped —
  boosting that ubiquitous token as a phrase start destabilizes decoding at
  boost ≥ ~4 (degenerate repetition loops); (2) without the marker-less
  variant, unigram-vs-greedy divergence ('▁'+'일' vs '▁일') silently disables
  a phrase. Default boost 2.0 — validated to fix real misrecognitions with
  multiple simultaneous Korean hotwords and no EN regression.
  `engine._set_hotwords` degrades gracefully (warn + ignore) when the lib
  reports ABI < 5, so an unpatched lib still boots.

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
  **Bumping re-applies `patches/*.patch`** — `git apply` fails the build
  loudly if upstream drifted under a patch; rebase the patch against the new
  REF (it is kept upstream-PR-shaped: regenerate with `git diff` from a
  patched checkout). If upstream ships hotword biasing itself, delete the
  patch + the Dockerfile apply step and re-point `engine.py` at the upstream
  API if it differs.
- GGUF cached at `/data/models/nemotron-3.5-asr-streaming-0.6b-<quant>.gguf`
  (`backup_exclude: ["models/**"]`). Changing `quantization` re-downloads.
- C ABI is versioned (`parakeet_capi_abi_version()`; upstream 4, **5 with the
  hotword patch**). If a `PARAKEET_REF` bump changes the ABI, update
  `engine.py` signatures and the patch's ABI define.

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
- `icon.png` / `logo.png` use Google's Material Icons **record_voice_over**
  glyph (Apache-2.0), recoloured to green `#76B900`; the logo adds a "NeMo ASR
  (cpp)" wordmark. Add an Apache-2.0 NOTICE/attribution when publishing.
