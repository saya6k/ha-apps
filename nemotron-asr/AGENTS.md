# AGENTS.md

Guidance for AI coding agents working on the **Nemotron ASR** add-on. Read
`CHANGELOG.md` for the *why* behind older decisions. This file is symlinked as
`CLAUDE.md` — edit `AGENTS.md`, the symlink follows.

## What this is

A single Home Assistant add-on running **NVIDIA Nemotron 3.5 Streaming ASR
(0.6B)** as a Wyoming **speech-to-text** service. It runs the **ONNX export**
([`nub235/nemotron-3.5-asr-streaming-onnx`](https://huggingface.co/nub235/nemotron-3.5-asr-streaming-onnx))
on CPU via `onnxruntime` — no NeMo/PyTorch, no GPU, no CoreML. Created as an
alternative to sherpa-onnx whose ASR accuracy was unsatisfactory.

## Git / repo tracking

Part of the `ha-apps` monorepo (one git repo at the root). Tracking is
**stage-gated** by the root `.gitignore`: only `stage: stable` add-ons are
committed; experimental ones stay local-only.

**This add-on:** `stage: experimental` → **local-only** (gitignored via
`/nemotron-asr/` in the root `.gitignore`, not committed, not in
`.github/release-please-config.json` / `.release-please-manifest.json` /
labels / labeler / issue templates). The `nemotron-asr` scope is still kept in
the allowed-scope tables in the root `AGENTS.md` / `CONTRIBUTING.md` so commits
read `feat(nemotron-asr): …`. To promote: set the add-on stable by removing the
`stage: experimental` key, delete the `/nemotron-asr/` line from the root
`.gitignore`, and register the slug in release-please config + manifest +
labels + labeler + issue templates.

## Layout

```
config.yaml / Dockerfile        app packaging (base pinned in Dockerfile FROM)
pyproject.toml                  bridge package metadata
wyoming_nemotron_asr/
  __main__.py    argparse + server boot (download + build engine, then serve)
  handler.py     Wyoming ASR events; incremental TranscriptChunk + final Transcript
  engine.py      NemotronASR (shared sessions) + NemotronStream (per-conn state):
                 streaming encoder loop + greedy RNN-T decode (reads config.json)
  featurizer.py  NeMo-compatible log-mel (numpy only; full + incremental paths)
  models.py      HuggingFace snapshot download into /data/models/<name>
  diag.py        boot CPU diagnostics (governor/freq/ISA) — encoder is clock-bound
  const.py       port, dirs, advertised languages, defaults
rootfs/etc/s6-overlay/s6-rc.d/  nemotron-asr (longrun) + discovery (oneshot)
translations/en.yaml + ko.yaml  option UI strings
CHANGELOG.md / DOCS.md / README.md   user-facing docs
```

Follows the sibling `sherpa-onnx` add-on for s6 / discovery / healthcheck /
HF-download conventions (it's the closest template — also a Wyoming STT bridge).

## How the model works (the non-obvious part)

It's a NeMo **cache-aware streaming Conformer-Transducer** exported to two ONNX
graphs. All shapes/params come from the model's `config.json` (the engine reads
it at runtime — do not hardcode):

- **encoder.onnx** — `processed_signal[1,128,T]` (log-mel) + 3 cache tensors
  (`cache_last_channel[24,1,56,1024]`, `cache_last_time[24,1,1024,8]`,
  `cache_last_channel_len[1]`) + `prompt_index[1]` (language id) →
  `encoded[1,1024,T']` + updated `*_next` caches. INT4 k-quant weights live in
  `encoder.onnx.data` (external).
- **decoder_joint.onnx** — fused 2-layer LSTM prediction net (hidden 640) +
  joint. `encoder_outputs[1,1024,1]` + `targets[1,1]` int32 + `target_length` +
  `input_states_1/2[2,1,640]` → `outputs[...,13088]` logits + new states.
  Plain RNN-T (vocab 13087 + blank 13087; **no** TDT duration head).

Streaming constants (from config, cross-checked vs the Microsoft Olive export
recipe `microsoft/olive-recipes/nvidia-nemotron-asr-streaming-multilingual-0.6b`):
`chunk_mel = chunk_size_output_frames(7) * subsampling(8) = 56`;
`static_mel = config.test_input.mel_shape[-1] = 65`;
`pre_encode = static_mel - chunk_mel = 9`. Each encoder step feeds 65 mel
frames = 9 left-overlap + 56 new; the cache carries cross-chunk context.

**Decode strategy (incremental streaming):** `NemotronStream` holds per-
connection state (encoder caches, RNN-T LSTM state, last token, audio buffer,
emitted tokens). As audio arrives, `accept_audio()` feeds every *stable*
56-mel-frame chunk (frames whose STFT window no longer depends on future audio)
through the encoder + greedy decode, so partial text is available mid-utterance;
the handler emits `TranscriptChunk` deltas. `finalize()` (on `AudioStop`)
flushes the tail (zero-padded partial chunk + legitimate end reflect-padding)
and the handler sends `TranscriptStop` + the final `Transcript`.
`supports_transcript_streaming=True`. Feeding chunked with the persistent cache
is **bit-identical** to a single offline pass — verified for EN + KO.

Mel is computed incrementally: `featurizer.logmel_frames(audio, i0, i1)` FFTs
only new stable frames (interior frames are plain slices of the pre-emphasized
signal, no reflect padding), cached in the stream — avoids O(n²) re-featurizing
on every chunk. `finalize()` does one full `featurizer(audio)` for the
end-padded tail. The stream **must** only call `logmel_frames` up to the stable
count; the tail is the full path's job. The offline `engine.transcribe()` is a
thin wrapper (one `accept_audio` + `finalize`) kept for tests / non-streaming
clients.

**Language:** `prompt_index` selects the locale (`config.json.prompt_dictionary`,
e.g. `ko-KR`/`ko` → 14, `auto` → 101). `engine.resolve_prompt()` maps the
per-request `Transcribe.language` (or the `language` option fallback) to it.

## Validation status

The full inference path was validated end-to-end against the real ONNX model:

- **English** (whisper's `jfk.wav`): transcribed accurately.
- **Korean** (macOS `say -v Yuna`, prompt_index 14): near-perfect.
- Streaming (chunked `accept_audio`) output is **bit-identical** to the offline
  pass for both; the incremental featurizer is bit-identical to the full path on
  the stable-frame domain (maxdiff 0.0).
- RTF ≈ 0.18 (offline) / 0.34 (streaming) on a dev Mac.

## Performance (encoder-bound, clock-sensitive)

Profiling (dev Mac, 4.5s clip): **encoder ≈ 82%** of runtime (~67 ms per
65-frame chunk, 24-layer conformer), decoder ≈ 17% (~1.4 ms × ~dozens of
per-frame `decoder_joint` calls), featurizer < 1%. The encoder weights are INT4
`MatMulNBits` with `accuracy_level=4` (int8/VNNI compute) — already the optimal
CPU config; do not "fix" the quantization.

Because the encoder is matmul-heavy it scales with **clock speed**. On Intel
N100 the measured RTF was **7.5 when the host was pinned at base clock** (turbo
off / powersave) vs an expected ~0.5–1.0 with turbo. `diag.py` logs governor +
freqs + `no_turbo` at boot so this is diagnosable. The fix is host-side (BIOS
turbo, `performance` governor, cooling) — not code. Don't chase model-level
optimizations for a throttled host.

If transcripts ever come out garbled, the **mel featurizer** is the first
suspect — it must match NeMo's `AudioToMelSpectrogramPreprocessor` (hann
periodic=False, slaney mel norm, `log(x+2^-24)`, `normalize="NA"`, params from
`config.json`). Diff `MelFeaturizer(...)(wav)` against the real `.nemo`
preprocessor on a known wav. Encoder shape anchor:
`config.json.test_input` (mel `[1,128,65]`) → `test_output.encoded_shape
[1,1024,7]`.

## Sanity checks before PR

- `python3 -c "import ast,glob; [ast.parse(open(f).read()) for f in glob.glob('wyoming_nemotron_asr/*.py')]"`
- yamllint `config.yaml translations/*.yaml`; `shellcheck` the s6 `run`/`finish`/`discovery/run`.
- `docker build .` for one arch.
- Smoke: `echo '{"type":"describe"}' | nc -w 1 localhost 10350 | grep -qi nemotron`.
- End-to-end: send a known wav through the HA voice pipeline (or a Wyoming
  client) and confirm the transcript is sane — this is the only test that
  exercises the featurizer + decode for real.

## Branding

`icon.png` / `logo.png` use Google's Material Icons **record_voice_over** glyph
(Apache-2.0), recoloured to green `#76B900`; `logo.png` adds a "Nemotron ASR"
wordmark in SF Pro. Same glyph/colour as the sibling `nemo-asr-cpp` add-on.
Update `NOTICE` if you swap them.

## Don'ts

- Don't hardcode shapes/prompt indices — read `config.json`.
- Don't add `armv7`/`armhf`/`i386` without confirming onnxruntime wheels exist.
- Don't pre-download the model in the Dockerfile; it lives on `/data` (~1.4 GB).
- Don't forget the `chmod +x` block in `Dockerfile` when adding an s6 script.
- Don't bump only one version: keep `config.yaml`, `pyproject.toml`, and
  `wyoming_nemotron_asr/__init__.py` in sync on release.
- Model is under the **NVIDIA Open Model License** — honor its terms if/when
  this add-on is published.
