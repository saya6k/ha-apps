# LiveKit WakeWord add-on

Runs the [`livekit/livekit-wakeword`](https://github.com/livekit/livekit-wakeword)
runtime (Apache 2.0) as a Wyoming **wake word** service for Home Assistant
voice pipelines. Because it shares a byte-identical frozen frontend with
openWakeWord, it serves the openWakeWord pretrained zoo (`alexa`,
`hey_jarvis`, `hey_mycroft`, `hey_rhasspy`) alongside `hey_livekit` and any
custom-trained `.onnx` model (including conv-attention heads) dropped into
`/share/livekit-wakeword`.
