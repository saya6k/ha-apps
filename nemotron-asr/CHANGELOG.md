# Changelog

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
