# LiveKit WakeWord add-on

![Supports amd64 Architecture][amd64-shield] ![Supports aarch64 Architecture][aarch64-shield]

[![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=4fdf9462_livekit-wakeword&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps%23beta)

Runs the [`livekit/livekit-wakeword`](https://github.com/livekit/livekit-wakeword)
runtime (Apache 2.0) as a Wyoming **wake word** service for Home Assistant
voice pipelines. Because it shares a byte-identical frozen frontend with
openWakeWord, it serves the openWakeWord pretrained zoo (`alexa`,
`hey_jarvis`, `hey_mycroft`, `hey_rhasspy`) alongside `hey_livekit` and any
custom-trained `.onnx` model (including conv-attention heads) dropped into
`/share/livekit-wakeword`.

## ⚠️ THIS IS A BETA VERSION

This build comes from the beta channel — a pre-release (rc) of this app.

- It may not work at all.
- It might stop working or change without notice.
- It could have a negative impact on your system.

If you want the stable release: <https://github.com/saya6k/ha-apps>

[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
