# Changelog

## [0.9.0](https://github.com/saya6k/ha-apps/compare/nemo-asr-cpp-v0.8.0...nemo-asr-cpp-v0.9.0) (2026-06-18)


### Features

* **nemo-asr-cpp:** add chunk_size accuracy/speed option ([#13](https://github.com/saya6k/ha-apps/issues/13)) ([1d8f683](https://github.com/saya6k/ha-apps/commit/1d8f6833b78ecc021f521a4e208a7e356a3168e2))
* **nemo-asr-cpp:** add custom AppArmor profile ([eb25e7d](https://github.com/saya6k/ha-apps/commit/eb25e7d7c8c8b79e114a052ada9e508a0d4cb996))
* **nemo-asr-cpp:** add hotword biasing via vendored parakeet.cpp patch ([eb28feb](https://github.com/saya6k/ha-apps/commit/eb28feb82e8351835760054f4c52f636d26b7deb))
* **nemo-asr-cpp:** add icon and logo ([c8e44c7](https://github.com/saya6k/ha-apps/commit/c8e44c7f6abd0264fff2cb0620e40a7f0c7e18a6))
* **nemo-asr-cpp:** add model selector, drop language option ([7655fa6](https://github.com/saya6k/ha-apps/commit/7655fa61643bb7c221586352695800636f98862c))
* **nemo-asr-cpp:** add NeMo ASR (cpp) ggml/parakeet.cpp STT add-on ([b037404](https://github.com/saya6k/ha-apps/commit/b0374048fc46d2df248bfe91ac728d7544c48e36))


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **nemo-asr-cpp:** add Show add-on badge to README ([95d5f40](https://github.com/saya6k/ha-apps/commit/95d5f4032065bfd200a501804167441e6433c98e))
* **nemo-asr-cpp:** align README shields with sibling apps ([ec0195e](https://github.com/saya6k/ha-apps/commit/ec0195e19c07645cc163ca044c18fbfa309b2f09))
* **repo:** drop per-subproject .claude aliases; root alias only ([4b7018f](https://github.com/saya6k/ha-apps/commit/4b7018f2f589b8d6c0b65b47e8852cbec786e197))


### Code Refactoring

* **repo:** rename nemo-asr-c to nemotron-asr-c, delete nemotron-asr (ONNX) ([#128](https://github.com/saya6k/ha-apps/issues/128)) ([2b822a3](https://github.com/saya6k/ha-apps/commit/2b822a3653f1d9e3c70b0fa4f2fd54d94b56e6f2))


### Build System

* **nemo-asr-cpp:** build add-on locally, drop GHCR image reference ([d3fb1ed](https://github.com/saya6k/ha-apps/commit/d3fb1ed64ecd7a4c1465bc0623f19635516e9f76))
* **nemo-asr-cpp:** merge builder stages; .so direct to /usr/local/lib ([ab90c73](https://github.com/saya6k/ha-apps/commit/ab90c73f63102a8f260e09fb9f08dd06f8c049ad))
* **nemo-asr-cpp:** merge ldconfig + chmod into single RUN layer ([873e7ec](https://github.com/saya6k/ha-apps/commit/873e7ec65db88b122310c3e36e075aef48a644cf))
* **nemo-asr-cpp:** reference prebuilt public GHCR image ([59d9d61](https://github.com/saya6k/ha-apps/commit/59d9d61bcde43798905f9bd86d3e6297d3b5f155))
* **nemo-asr-cpp:** strip .so symbols, --no-compile pip, clean builder apt cache ([bface7d](https://github.com/saya6k/ha-apps/commit/bface7dd338e9eafcb1a0c982017be8c84c87149))

## [0.8.0](https://github.com/saya6k/ha-apps/compare/nemo-asr-cpp-v0.7.0...nemo-asr-cpp-v0.8.0) (2026-06-18)


### Features

* **nemo-asr-cpp:** add chunk_size accuracy/speed option ([#13](https://github.com/saya6k/ha-apps/issues/13)) ([1d8f683](https://github.com/saya6k/ha-apps/commit/1d8f6833b78ecc021f521a4e208a7e356a3168e2))
* **nemo-asr-cpp:** add custom AppArmor profile ([eb25e7d](https://github.com/saya6k/ha-apps/commit/eb25e7d7c8c8b79e114a052ada9e508a0d4cb996))
* **nemo-asr-cpp:** add hotword biasing via vendored parakeet.cpp patch ([eb28feb](https://github.com/saya6k/ha-apps/commit/eb28feb82e8351835760054f4c52f636d26b7deb))
* **nemo-asr-cpp:** add icon and logo ([c8e44c7](https://github.com/saya6k/ha-apps/commit/c8e44c7f6abd0264fff2cb0620e40a7f0c7e18a6))
* **nemo-asr-cpp:** add model selector, drop language option ([7655fa6](https://github.com/saya6k/ha-apps/commit/7655fa61643bb7c221586352695800636f98862c))
* **nemo-asr-cpp:** add NeMo ASR (cpp) ggml/parakeet.cpp STT add-on ([b037404](https://github.com/saya6k/ha-apps/commit/b0374048fc46d2df248bfe91ac728d7544c48e36))


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **nemo-asr-cpp:** add Show add-on badge to README ([95d5f40](https://github.com/saya6k/ha-apps/commit/95d5f4032065bfd200a501804167441e6433c98e))
* **nemo-asr-cpp:** align README shields with sibling apps ([ec0195e](https://github.com/saya6k/ha-apps/commit/ec0195e19c07645cc163ca044c18fbfa309b2f09))


### Code Refactoring

* **repo:** rename nemo-asr-c to nemotron-asr-c, delete nemotron-asr (ONNX) ([#128](https://github.com/saya6k/ha-apps/issues/128)) ([2b822a3](https://github.com/saya6k/ha-apps/commit/2b822a3653f1d9e3c70b0fa4f2fd54d94b56e6f2))


### Build System

* **nemo-asr-cpp:** build add-on locally, drop GHCR image reference ([d3fb1ed](https://github.com/saya6k/ha-apps/commit/d3fb1ed64ecd7a4c1465bc0623f19635516e9f76))
* **nemo-asr-cpp:** merge builder stages; .so direct to /usr/local/lib ([ab90c73](https://github.com/saya6k/ha-apps/commit/ab90c73f63102a8f260e09fb9f08dd06f8c049ad))
* **nemo-asr-cpp:** merge ldconfig + chmod into single RUN layer ([873e7ec](https://github.com/saya6k/ha-apps/commit/873e7ec65db88b122310c3e36e075aef48a644cf))
* **nemo-asr-cpp:** reference prebuilt public GHCR image ([59d9d61](https://github.com/saya6k/ha-apps/commit/59d9d61bcde43798905f9bd86d3e6297d3b5f155))
* **nemo-asr-cpp:** strip .so symbols, --no-compile pip, clean builder apt cache ([bface7d](https://github.com/saya6k/ha-apps/commit/bface7dd338e9eafcb1a0c982017be8c84c87149))

## [0.7.0](https://github.com/saya6k/ha-apps/compare/nemo-asr-cpp-v0.6.0...nemo-asr-cpp-v0.7.0) (2026-06-18)


### Features

* **nemo-asr-cpp:** add chunk_size accuracy/speed option ([#13](https://github.com/saya6k/ha-apps/issues/13)) ([1d8f683](https://github.com/saya6k/ha-apps/commit/1d8f6833b78ecc021f521a4e208a7e356a3168e2))
* **nemo-asr-cpp:** add custom AppArmor profile ([eb25e7d](https://github.com/saya6k/ha-apps/commit/eb25e7d7c8c8b79e114a052ada9e508a0d4cb996))
* **nemo-asr-cpp:** add hotword biasing via vendored parakeet.cpp patch ([eb28feb](https://github.com/saya6k/ha-apps/commit/eb28feb82e8351835760054f4c52f636d26b7deb))
* **nemo-asr-cpp:** add icon and logo ([c8e44c7](https://github.com/saya6k/ha-apps/commit/c8e44c7f6abd0264fff2cb0620e40a7f0c7e18a6))
* **nemo-asr-cpp:** add model selector, drop language option ([7655fa6](https://github.com/saya6k/ha-apps/commit/7655fa61643bb7c221586352695800636f98862c))
* **nemo-asr-cpp:** add NeMo ASR (cpp) ggml/parakeet.cpp STT add-on ([b037404](https://github.com/saya6k/ha-apps/commit/b0374048fc46d2df248bfe91ac728d7544c48e36))


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **nemo-asr-cpp:** add Show add-on badge to README ([95d5f40](https://github.com/saya6k/ha-apps/commit/95d5f4032065bfd200a501804167441e6433c98e))
* **nemo-asr-cpp:** align README shields with sibling apps ([ec0195e](https://github.com/saya6k/ha-apps/commit/ec0195e19c07645cc163ca044c18fbfa309b2f09))


### Code Refactoring

* **repo:** rename nemo-asr-c to nemotron-asr-c, delete nemotron-asr (ONNX) ([#128](https://github.com/saya6k/ha-apps/issues/128)) ([2b822a3](https://github.com/saya6k/ha-apps/commit/2b822a3653f1d9e3c70b0fa4f2fd54d94b56e6f2))


### Build System

* **nemo-asr-cpp:** build add-on locally, drop GHCR image reference ([d3fb1ed](https://github.com/saya6k/ha-apps/commit/d3fb1ed64ecd7a4c1465bc0623f19635516e9f76))
* **nemo-asr-cpp:** merge builder stages; .so direct to /usr/local/lib ([ab90c73](https://github.com/saya6k/ha-apps/commit/ab90c73f63102a8f260e09fb9f08dd06f8c049ad))
* **nemo-asr-cpp:** merge ldconfig + chmod into single RUN layer ([873e7ec](https://github.com/saya6k/ha-apps/commit/873e7ec65db88b122310c3e36e075aef48a644cf))
* **nemo-asr-cpp:** reference prebuilt public GHCR image ([59d9d61](https://github.com/saya6k/ha-apps/commit/59d9d61bcde43798905f9bd86d3e6297d3b5f155))
* **nemo-asr-cpp:** strip .so symbols, --no-compile pip, clean builder apt cache ([bface7d](https://github.com/saya6k/ha-apps/commit/bface7dd338e9eafcb1a0c982017be8c84c87149))

## [0.6.0](https://github.com/saya6k/ha-apps/compare/nemo-asr-cpp-v0.5.0...nemo-asr-cpp-v0.6.0) (2026-06-18)


### Features

* **nemo-asr-cpp:** add chunk_size accuracy/speed option ([#13](https://github.com/saya6k/ha-apps/issues/13)) ([1d8f683](https://github.com/saya6k/ha-apps/commit/1d8f6833b78ecc021f521a4e208a7e356a3168e2))
* **nemo-asr-cpp:** add custom AppArmor profile ([eb25e7d](https://github.com/saya6k/ha-apps/commit/eb25e7d7c8c8b79e114a052ada9e508a0d4cb996))
* **nemo-asr-cpp:** add hotword biasing via vendored parakeet.cpp patch ([eb28feb](https://github.com/saya6k/ha-apps/commit/eb28feb82e8351835760054f4c52f636d26b7deb))
* **nemo-asr-cpp:** add icon and logo ([c8e44c7](https://github.com/saya6k/ha-apps/commit/c8e44c7f6abd0264fff2cb0620e40a7f0c7e18a6))
* **nemo-asr-cpp:** add model selector, drop language option ([7655fa6](https://github.com/saya6k/ha-apps/commit/7655fa61643bb7c221586352695800636f98862c))
* **nemo-asr-cpp:** add NeMo ASR (cpp) ggml/parakeet.cpp STT add-on ([b037404](https://github.com/saya6k/ha-apps/commit/b0374048fc46d2df248bfe91ac728d7544c48e36))


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **nemo-asr-cpp:** add Show add-on badge to README ([95d5f40](https://github.com/saya6k/ha-apps/commit/95d5f4032065bfd200a501804167441e6433c98e))
* **nemo-asr-cpp:** align README shields with sibling apps ([ec0195e](https://github.com/saya6k/ha-apps/commit/ec0195e19c07645cc163ca044c18fbfa309b2f09))


### Code Refactoring

* **repo:** rename nemo-asr-c to nemotron-asr-c, delete nemotron-asr (ONNX) ([#128](https://github.com/saya6k/ha-apps/issues/128)) ([2b822a3](https://github.com/saya6k/ha-apps/commit/2b822a3653f1d9e3c70b0fa4f2fd54d94b56e6f2))


### Build System

* **nemo-asr-cpp:** build add-on locally, drop GHCR image reference ([d3fb1ed](https://github.com/saya6k/ha-apps/commit/d3fb1ed64ecd7a4c1465bc0623f19635516e9f76))
* **nemo-asr-cpp:** merge builder stages; .so direct to /usr/local/lib ([ab90c73](https://github.com/saya6k/ha-apps/commit/ab90c73f63102a8f260e09fb9f08dd06f8c049ad))
* **nemo-asr-cpp:** merge ldconfig + chmod into single RUN layer ([873e7ec](https://github.com/saya6k/ha-apps/commit/873e7ec65db88b122310c3e36e075aef48a644cf))
* **nemo-asr-cpp:** reference prebuilt public GHCR image ([59d9d61](https://github.com/saya6k/ha-apps/commit/59d9d61bcde43798905f9bd86d3e6297d3b5f155))
* **nemo-asr-cpp:** strip .so symbols, --no-compile pip, clean builder apt cache ([bface7d](https://github.com/saya6k/ha-apps/commit/bface7dd338e9eafcb1a0c982017be8c84c87149))

## [0.5.0](https://github.com/saya6k/ha-apps/compare/nemo-asr-cpp-v0.4.0...nemo-asr-cpp-v0.5.0) (2026-06-18)


### Features

* **nemo-asr-cpp:** add chunk_size accuracy/speed option ([#13](https://github.com/saya6k/ha-apps/issues/13)) ([1d8f683](https://github.com/saya6k/ha-apps/commit/1d8f6833b78ecc021f521a4e208a7e356a3168e2))
* **nemo-asr-cpp:** add custom AppArmor profile ([eb25e7d](https://github.com/saya6k/ha-apps/commit/eb25e7d7c8c8b79e114a052ada9e508a0d4cb996))
* **nemo-asr-cpp:** add hotword biasing via vendored parakeet.cpp patch ([eb28feb](https://github.com/saya6k/ha-apps/commit/eb28feb82e8351835760054f4c52f636d26b7deb))
* **nemo-asr-cpp:** add icon and logo ([c8e44c7](https://github.com/saya6k/ha-apps/commit/c8e44c7f6abd0264fff2cb0620e40a7f0c7e18a6))
* **nemo-asr-cpp:** add model selector, drop language option ([7655fa6](https://github.com/saya6k/ha-apps/commit/7655fa61643bb7c221586352695800636f98862c))
* **nemo-asr-cpp:** add NeMo ASR (cpp) ggml/parakeet.cpp STT add-on ([b037404](https://github.com/saya6k/ha-apps/commit/b0374048fc46d2df248bfe91ac728d7544c48e36))


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **nemo-asr-cpp:** add Show add-on badge to README ([95d5f40](https://github.com/saya6k/ha-apps/commit/95d5f4032065bfd200a501804167441e6433c98e))
* **nemo-asr-cpp:** align README shields with sibling apps ([ec0195e](https://github.com/saya6k/ha-apps/commit/ec0195e19c07645cc163ca044c18fbfa309b2f09))


### Code Refactoring

* **repo:** rename nemo-asr-c to nemotron-asr-c, delete nemotron-asr (ONNX) ([#128](https://github.com/saya6k/ha-apps/issues/128)) ([2b822a3](https://github.com/saya6k/ha-apps/commit/2b822a3653f1d9e3c70b0fa4f2fd54d94b56e6f2))


### Build System

* **nemo-asr-cpp:** build add-on locally, drop GHCR image reference ([d3fb1ed](https://github.com/saya6k/ha-apps/commit/d3fb1ed64ecd7a4c1465bc0623f19635516e9f76))
* **nemo-asr-cpp:** merge builder stages; .so direct to /usr/local/lib ([ab90c73](https://github.com/saya6k/ha-apps/commit/ab90c73f63102a8f260e09fb9f08dd06f8c049ad))
* **nemo-asr-cpp:** merge ldconfig + chmod into single RUN layer ([873e7ec](https://github.com/saya6k/ha-apps/commit/873e7ec65db88b122310c3e36e075aef48a644cf))
* **nemo-asr-cpp:** reference prebuilt public GHCR image ([59d9d61](https://github.com/saya6k/ha-apps/commit/59d9d61bcde43798905f9bd86d3e6297d3b5f155))
* **nemo-asr-cpp:** strip .so symbols, --no-compile pip, clean builder apt cache ([bface7d](https://github.com/saya6k/ha-apps/commit/bface7dd338e9eafcb1a0c982017be8c84c87149))

## [0.4.0](https://github.com/saya6k/ha-apps/compare/nemo-asr-cpp-v0.3.5...nemo-asr-cpp-v0.4.0) (2026-06-18)


### Features

* **nemo-asr-cpp:** add custom AppArmor profile ([eb25e7d](https://github.com/saya6k/ha-apps/commit/eb25e7d7c8c8b79e114a052ada9e508a0d4cb996))


### Documentation

* **nemo-asr-cpp:** add Show add-on badge to README ([95d5f40](https://github.com/saya6k/ha-apps/commit/95d5f4032065bfd200a501804167441e6433c98e))

## [0.3.5](https://github.com/saya6k/ha-apps/compare/nemo-asr-cpp-v0.3.4...nemo-asr-cpp-v0.3.5) (2026-06-18)


### Build System

* **nemo-asr-cpp:** build add-on locally, drop GHCR image reference ([d3fb1ed](https://github.com/saya6k/ha-apps/commit/d3fb1ed64ecd7a4c1465bc0623f19635516e9f76))

## [0.3.4](https://github.com/saya6k/ha-apps/compare/nemo-asr-cpp-v0.3.3...nemo-asr-cpp-v0.3.4) (2026-06-17)


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))

## [0.3.3](https://github.com/saya6k/ha-apps/compare/nemo-asr-cpp-v0.3.2...nemo-asr-cpp-v0.3.3) (2026-06-17)


### Code Refactoring

* **repo:** rename nemo-asr-c to nemotron-asr-c, delete nemotron-asr (ONNX) ([#128](https://github.com/saya6k/ha-apps/issues/128)) ([2b822a3](https://github.com/saya6k/ha-apps/commit/2b822a3653f1d9e3c70b0fa4f2fd54d94b56e6f2))

## [0.3.2](https://github.com/saya6k/ha-apps/compare/nemo-asr-cpp-v0.3.1...nemo-asr-cpp-v0.3.2) (2026-06-15)


### Documentation

* **nemo-asr-cpp:** align README shields with sibling apps ([ec0195e](https://github.com/saya6k/ha-apps/commit/ec0195e19c07645cc163ca044c18fbfa309b2f09))

## [0.3.1](https://github.com/saya6k/ha-apps/compare/nemo-asr-cpp-v0.3.0...nemo-asr-cpp-v0.3.1) (2026-06-15)


### Build System

* **nemo-asr-cpp:** reference prebuilt public GHCR image ([59d9d61](https://github.com/saya6k/ha-apps/commit/59d9d61bcde43798905f9bd86d3e6297d3b5f155))

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
