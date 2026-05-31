# Home Assistant App: Supertonic

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/saya6k)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Shell](https://img.shields.io/badge/Shell-4EAA25?style=for-the-badge&logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)

Home Assistant app that runs [Supertonic](https://huggingface.co/yunfengwang/supertonic-tts-mnn)
as a [Wyoming](https://github.com/rhasspy/wyoming) text-to-speech service,
powered by the lightweight [supertonic-mnn](https://github.com/vra/supertonic-mnn)
(MNN) inference engine.

Supertonic is a high-quality multilingual neural TTS engine from Supertone.
The MNN model is downloaded automatically from Hugging Face on first start
and cached under `/data/.cache/supertonic-mnn` so it survives restarts.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
