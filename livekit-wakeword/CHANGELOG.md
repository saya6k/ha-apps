# Changelog

## [0.2.0](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.1.0...livekit-wakeword-v0.2.0) (2026-06-16)


### Features

* **livekit-wakeword:** add Wyoming wake word add-on with incremental oWW-compatible bridge ([8355f66](https://github.com/saya6k/ha-apps/commit/8355f6608fc638fb8b8c6ac103d2d60482513b6c))


### Documentation

* **livekit-wakeword:** update Git tracking section — app is now tracked in git ([079b62d](https://github.com/saya6k/ha-apps/commit/079b62d1ac3148a692bc8b5bcfeaee770ae3984e))

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
