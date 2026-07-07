# Home Assistant App: Transcribe.cpp

![Supports amd64 Architecture][amd64-shield] ![Supports aarch64 Architecture][aarch64-shield]

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/saya6k)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Shell](https://img.shields.io/badge/Shell-4EAA25?style=for-the-badge&logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)

[![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=03f32180_transcribe-cpp&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps)

Home Assistant **speech-to-text** over
[Wyoming](https://github.com/rhasspy/wyoming): the full
[`transcribe.cpp`](https://github.com/handy-computer/transcribe.cpp) GGUF
model catalog — Whisper, Parakeet, Canary, Qwen3-ASR, Moonshine and more —
running on the **ggml** runtime (CPU, quantized).

Pick any catalog model and weight precision (`q4_k_m` → `f16`) from the
configuration; the model downloads once to `/data` and stays resident.

[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
