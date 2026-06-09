# Changelog

## 0.1.0

- Initial scaffold. Wyoming **speech-to-text** add-on running NVIDIA Nemotron
  3.5 Streaming ASR (0.6B, multilingual incl. Korean) on the **ggml** runtime
  via [`mudler/parakeet.cpp`](https://github.com/mudler/parakeet.cpp).
- The Dockerfile **builds `libparakeet.so` + ggml from upstream source** (pinned
  `PARAKEET_REF`, portable `GGML_NATIVE=OFF` CPU build); the Python bridge calls
  the flat **C API** (`parakeet_capi.h`) via ctypes. No fork — we follow
  upstream.
- **Model resident**: loaded once at boot, transcribed per utterance from
  in-memory PCM (`transcribe_pcm_lang`) — no per-command reload. Buffered
  (transcribe on `AudioStop`) for clean output.
- **Quantization option** (`q4_k` default → `f16`) downloads the matching GGUF
  from `mudler/parakeet-cpp-gguf`; `q4_k` is ~720 MB.
- Native-name **language dropdown** (37 + `Auto`) → parakeet `--lang` locale;
  inline `<xx-XX>` language tags stripped from transcripts.
- Wyoming on port `10360`; auto-discovery via the HA Wyoming integration.
- **Why this exists**: the speed/RAM-focused sibling of the onnxruntime
  `nemotron-asr` add-on for resource-limited HAOS (N100, Pi 4/5). ~1.4× faster
  on CPU; no hotword biasing (that stays in `nemotron-asr`).
- **Experimental**: ctypes C-API path validated on a dev Mac (model resident,
  Korean output clean, RTF ~0.14); not yet measured on the target Pi/N100.
