# Changelog

## [0.4.0](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.3.2...voiceprint-v0.4.0) (2026-06-18)


### Features

* **voiceprint:** add custom AppArmor profile ([3c39a1f](https://github.com/saya6k/ha-apps/commit/3c39a1fe6b8175c1d5a47d2c2247d19ecef72e9b))


### Documentation

* **voiceprint:** add Show add-on badge and arch shields to README ([e3f0429](https://github.com/saya6k/ha-apps/commit/e3f0429717ecddf93ec69583ba783cae2c3e50bc))

## [0.3.2](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.3.1...voiceprint-v0.3.2) (2026-06-18)


### Build System

* **voiceprint:** build add-on locally, drop GHCR image reference ([e2ad20f](https://github.com/saya6k/ha-apps/commit/e2ad20fec1e9a28e32bfc83bf11f32416e5ffdf1))

## [0.3.1](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.3.0...voiceprint-v0.3.1) (2026-06-17)


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))

## [0.3.0](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.2.0...voiceprint-v0.3.0) (2026-06-15)


### Features

* **voiceprint:** default upstream to nemo-asr-cpp and ship GHCR image ([03f0096](https://github.com/saya6k/ha-apps/commit/03f0096020ebdebacac7be16be7444436339407d))

## [0.2.0](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.1.0...voiceprint-v0.2.0) (2026-06-15)


### Features

* **voiceprint:** add speaker-verifying Wyoming STT proxy add-on ([eaac8c1](https://github.com/saya6k/ha-apps/commit/eaac8c1bc7dd2f26246fb8c5b23234b4a47ba22e))

## 0.1.0

- Initial release: speaker-verifying Wyoming STT proxy (pass-through gate).
- On-device CAM++ (3D-Speaker) speaker embeddings on LiteRT.
- Enrollment from `/share/voiceprint/<speaker>/*.wav`.
- Options: `upstream_uri`, `threshold`, `require_match`, `tag_speaker`,
  `debug_logging`.
