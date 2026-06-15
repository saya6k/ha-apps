# Changelog

## [0.3.0](https://github.com/saya6k/ha-apps/compare/nemo-asr-cpp-v0.2.0...nemo-asr-cpp-v0.3.0) (2026-06-15)


### Features

* **nemo-asr-cpp:** add chunk_size accuracy/speed option ([#13](https://github.com/saya6k/ha-apps/issues/13)) ([1d8f683](https://github.com/saya6k/ha-apps/commit/1d8f6833b78ecc021f521a4e208a7e356a3168e2))

## [0.2.0](https://github.com/saya6k/ha-apps/compare/nemo-asr-cpp-v0.1.0...nemo-asr-cpp-v0.2.0) (2026-06-15)


### Features

* **nemo-asr-cpp:** add hotword biasing via vendored parakeet.cpp patch ([eb28feb](https://github.com/saya6k/ha-apps/commit/eb28feb82e8351835760054f4c52f636d26b7deb))
* **nemo-asr-cpp:** add icon and logo ([c8e44c7](https://github.com/saya6k/ha-apps/commit/c8e44c7f6abd0264fff2cb0620e40a7f0c7e18a6))
* **nemo-asr-cpp:** add model selector, drop language option ([7655fa6](https://github.com/saya6k/ha-apps/commit/7655fa61643bb7c221586352695800636f98862c))
* **nemo-asr-cpp:** add NeMo ASR (cpp) ggml/parakeet.cpp STT add-on ([b037404](https://github.com/saya6k/ha-apps/commit/b0374048fc46d2df248bfe91ac728d7544c48e36))

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
