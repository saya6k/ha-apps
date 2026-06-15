# Changelog

## [0.2.0](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.1.0...voiceprint-v0.2.0) (2026-06-15)


### Features

* **voiceprint:** add speaker-verifying Wyoming STT proxy add-on ([eaac8c1](https://github.com/saya6k/ha-apps/commit/eaac8c1bc7dd2f26246fb8c5b23234b4a47ba22e))

## 0.1.0

- Initial release: speaker-verifying Wyoming STT proxy (pass-through gate).
- On-device CAM++ (3D-Speaker) speaker embeddings on LiteRT.
- Enrollment from `/share/voiceprint/<speaker>/*.wav`.
- Options: `upstream_uri`, `threshold`, `require_match`, `tag_speaker`,
  `debug_logging`.
