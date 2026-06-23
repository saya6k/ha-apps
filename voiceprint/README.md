# Home Assistant Add-on: Voiceprint

![Supports amd64 Architecture][amd64-shield] ![Supports aarch64 Architecture][aarch64-shield]

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/saya6k)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Shell](https://img.shields.io/badge/Shell-4EAA25?style=for-the-badge&logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)

[![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=03f32180_voiceprint&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps)

A speaker-verifying Wyoming STT proxy. It sits between Home Assistant and
your speech-to-text service, streams audio through unchanged, and checks the
voice against enrolled voiceprints in parallel — commands from voices you
haven't enrolled (a TV, a guest, an ad) come back as an empty transcript and
never execute. Speaker embeddings run on-device via a CAM++ model
([3D-Speaker](https://github.com/modelscope/3D-Speaker), Apache 2.0) on the
LiteRT runtime.

Enroll a speaker by dropping a few WAV recordings into
`/share/voiceprint/<name>/` and restarting the add-on.

[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
