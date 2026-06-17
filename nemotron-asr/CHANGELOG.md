# Changelog

## [0.2.2](https://github.com/saya6k/ha-apps/compare/nemotron-asr-v0.2.1...nemotron-asr-v0.2.2) (2026-06-17)


### Bug Fixes

* **nemotron-asr:** revert stage experimental and image config ([e65288a](https://github.com/saya6k/ha-apps/commit/e65288a963d3bc0d3f2a6f9377b3e52daaa1d0d8))
* **nemotron-asr:** set stage experimental, comment image, switch to canonical HF model repo ([196d7b6](https://github.com/saya6k/ha-apps/commit/196d7b67ac3ac6660847733bc5abd7599fe5711f))


### CI

* **repo:** consolidate AI harness under .agents/ as canonical SoT ([#57](https://github.com/saya6k/ha-apps/issues/57)) ([d339325](https://github.com/saya6k/ha-apps/commit/d33932542b92887f10b4f18536227c8396aa5c4d))

## [0.2.1](https://github.com/saya6k/ha-apps/compare/nemotron-asr-v0.2.0...nemotron-asr-v0.2.1) (2026-06-16)


### Build System

* **nemotron-asr:** add GHCR image reference to config.yaml ([#55](https://github.com/saya6k/ha-apps/issues/55)) ([1525e86](https://github.com/saya6k/ha-apps/commit/1525e86c8bf26e6ff64537005ad41159a27feaf8))


## [0.2.0](https://github.com/saya6k/ha-apps/compare/nemotron-asr-v0.1.0...nemotron-asr-v0.2.0) (2026-06-16)


### Features

* **nemotron-asr:** add Wyoming STT add-on (Nemotron 0.6B ONNX/CPU) ([#53](https://github.com/saya6k/ha-apps/issues/53)) ([00c6c0b](https://github.com/saya6k/ha-apps/commit/00c6c0bce83296cb7fbb6cdc02fc8b560148db62))

## 0.1.0

- Initial scaffold. Wyoming **speech-to-text** add-on running
  [NVIDIA Nemotron 3.5 Streaming ASR (0.6B)](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b)
  from its [ONNX export](https://huggingface.co/nub235/nemotron-3.5-asr-streaming-onnx)
  on CPU via `onnxruntime` (no GPU, NeMo, or CoreML).
- **Incremental streaming transcription** (`supports_transcript_streaming`):
  per-connection `NemotronStream` feeds each stable 56-mel-frame chunk through
  the cache-aware encoder + greedy RNN-T decode as audio arrives, emitting
  `TranscriptChunk` deltas, then a final `Transcript` on `AudioStop`. Chunked
  decoding is bit-identical to a single offline pass (verified EN + KO).
- NeMo-compatible log-mel featurizer implemented in numpy (no librosa/scipy),
  with an incremental path that FFTs only new frames (no O(n²) re-featurize).
- Model auto-downloaded from Hugging Face to `/data/models` on first start.
- Language selected per-request via the encoder's prompt index
  (`config.json.prompt_dictionary`); the `language` option is a native-name
  dropdown (37 languages + `Auto`) as a fallback. `resolve_prompt` accepts
  dropdown labels, HA ISO codes, and locales.
- Wyoming on port `10350`; auto-discovery via the HA Wyoming integration.
- **Hotword / vocabulary biasing**: `hotwords` (room/entity/person names) get a
  per-token logit bonus (`hotword_boost`, default 2.0) during greedy decode, so
  known vocabulary is recognized more reliably. Best-effort with greedy decoding;
  raise the boost for stubborn cases.
- **Boot warm-up** runs one dummy utterance so the first real command doesn't pay
  the ONNX cold-start (several seconds on a Pi).
- Boot-time CPU diagnostics (governor, per-core freq, ISA flags, ORT thread
  count/providers) — the encoder is clock-sensitive, so this surfaces host
  throttling (e.g. N100 turbo disabled) that otherwise looks like model slowness.
- **Experimental**: inference validated end-to-end (EN + KO) against the real
  model, but not yet exercised on low-power target hardware — see `AGENTS.md`.
