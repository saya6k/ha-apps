# Changelog

## 0.1.0

- Initial release: Wyoming wake word service on the
  [livekit-wakeword](https://github.com/livekit/livekit-wakeword) runtime
  with our own streaming bridge (openWakeWord-style incremental features:
  one embedding per 80 ms, ~10x less CPU than upstream's stateless API).
- Built-in models: `hey_livekit` plus the openWakeWord zoo (`alexa`,
  `hey_jarvis`, `hey_mycroft`, `hey_rhasspy`) — the two runtimes share a
  byte-identical frontend. Downloads are sha256-pinned.
- Custom `.onnx` models auto-load from `/share/livekit-wakeword`
  (livekit-trained conv-attention heads and openWakeWord classifiers both
  work).
- Options: `models`, `threshold`, `trigger_level`, `debug_logging`.
