# Home Assistant App: Nemotron ASR

![Supports amd64 Architecture][amd64-shield] ![Supports aarch64 Architecture][aarch64-shield]

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

Home Assistant app that runs [NVIDIA Nemotron 3.5 Streaming ASR](https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b)
(0.6B, multilingual) as a [Wyoming](https://github.com/rhasspy/wyoming)
speech-to-text service. It runs the
[ONNX export](https://huggingface.co/nub235/nemotron-3.5-asr-streaming-onnx)
on **CPU** via `onnxruntime` — no GPU, no NeMo/PyTorch, no CoreML.

> **Experimental — local-only.** This app is not published to the add-on
> store. Install it by copying this folder into `/addons/local/` (or
> `/root/addons/` on HAOS), then **Settings → Add-ons → Add-on Store → ⋮ →
> Check for updates**. For a lighter, store-ready alternative on the same
> model, see the **NeMo ASR (cpp)** app.

The ONNX model (encoder + fused decoder/joint + SentencePiece tokenizer) is
downloaded automatically from Hugging Face on first start and cached under
`/data/models` (~1.4 GB) so it survives restarts. The Wyoming integration
auto-discovers the service.

Transcription is **incremental/streaming** — partial text is produced while you
speak (Wyoming `TranscriptChunk`), with a final transcript on end-of-speech.

Validated end-to-end (English + Korean) against the real model and on a
Raspberry Pi 5 at full clock. It runs in real time on a healthy desktop/Pi 5
CPU; on low-power CPUs (Intel N100) check the boot CPU diagnostics for clock
throttling — see the Performance section in `DOCS.md`.

[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
