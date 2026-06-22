# Home Assistant App: NeMo ASR (cpp)

![Supports amd64 Architecture][amd64-shield] ![Supports aarch64 Architecture][aarch64-shield]

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/saya6k)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Shell](https://img.shields.io/badge/Shell-4EAA25?style=for-the-badge&logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)

[![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=03f32180_nemo-asr-cpp&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps)

Fast, light Home Assistant **speech-to-text** over [Wyoming](https://github.com/rhasspy/wyoming):
NVIDIA Nemotron 3.5 Streaming ASR (0.6B, multilingual incl. Korean) running on
the **ggml** runtime via [`mudler/parakeet.cpp`](https://github.com/mudler/parakeet.cpp).

It's the speed-focused sibling of the **Nemotron ASR** add-on (same model on
onnxruntime): ggml is ~1.4× faster on CPU and the default `q4_k` GGUF is ~720 MB
(about half the RAM/disk) — built for resource-limited HAOS (Intel N100,
Raspberry Pi 4/5). The model loads once and stays resident (no per-command
reload). Pick the weight precision with the `quantization` option (`q4_k` →
`f16`).

No hotword biasing here — use the **Nemotron ASR** (onnxruntime) add-on if you
need that.

[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
