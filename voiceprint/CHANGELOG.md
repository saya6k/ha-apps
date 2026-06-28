# Changelog

Releases from the next version onward are tracked in
[ha-app-* releases](https://github.com/saya6k/ha-app-voiceprint/releases).


## [0.10.1](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.10.0...voiceprint-v0.10.1) (2026-06-23)


### Bug Fixes

* **repo:** replace {,**} with explicit dir+glob rules in all AppArmor profiles ([6903c13](https://github.com/saya6k/ha-apps/commit/6903c1329a95f5833114dd3aabdc9849fbf8e7b8))

## [0.10.0](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.9.2...voiceprint-v0.10.0) (2026-06-23)


### Features

* **voiceprint:** add AppArmor profile ([84396c8](https://github.com/saya6k/ha-apps/commit/84396c8e0c0f75d7d4f488772ceba254d9dd27bb))


### Documentation

* **voiceprint:** add tech stack shields to README ([e9b5a8a](https://github.com/saya6k/ha-apps/commit/e9b5a8af862ea640627a3b8ceb7380ff0173ff70))

## [0.9.2](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.9.1...voiceprint-v0.9.2) (2026-06-22)


### Bug Fixes

* **voiceprint:** fix ruff E741/F841 in __main__.py ([72ad539](https://github.com/saya6k/ha-apps/commit/72ad539e975ed18a0f6382dcbbb4a0f50fe4a872))


### CI

* **repo:** tighten markdownlint scope and disable style-only rules ([9fe6f97](https://github.com/saya6k/ha-apps/commit/9fe6f97b9fee3e1c010f2ee534b36ea8de2a74fe))

## [0.9.1](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.9.0...voiceprint-v0.9.1) (2026-06-18)


### Bug Fixes

* **repo:** add apparmor: true to all add-ons, remove custom profiles ([6ccfe5d](https://github.com/saya6k/ha-apps/commit/6ccfe5d4b5daf805d66b7dbcdc1c71ab95e106e1))
* **repo:** add apparmor: true to all add-ons, remove custom profiles ([a8b8a61](https://github.com/saya6k/ha-apps/commit/a8b8a6163024fa611e2b661b90f37093640419fa))
* **repo:** remove redundant apparmor: true (linter default) ([423ac7f](https://github.com/saya6k/ha-apps/commit/423ac7ff0c4fbde79abdec4e86a08f5c91f6fe1f))

## [0.9.0](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.8.0...voiceprint-v0.9.0) (2026-06-18)


### Features

* **voiceprint:** add custom AppArmor profile ([3c39a1f](https://github.com/saya6k/ha-apps/commit/3c39a1fe6b8175c1d5a47d2c2247d19ecef72e9b))
* **voiceprint:** add speaker-verifying Wyoming STT proxy add-on ([eaac8c1](https://github.com/saya6k/ha-apps/commit/eaac8c1bc7dd2f26246fb8c5b23234b4a47ba22e))
* **voiceprint:** default upstream to nemo-asr-cpp and ship GHCR image ([03f0096](https://github.com/saya6k/ha-apps/commit/03f0096020ebdebacac7be16be7444436339407d))


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **voiceprint:** add Show add-on badge and arch shields to README ([e3f0429](https://github.com/saya6k/ha-apps/commit/e3f0429717ecddf93ec69583ba783cae2c3e50bc))


### Build System

* **voiceprint:** --no-compile pip install in builder stage ([e7493ab](https://github.com/saya6k/ha-apps/commit/e7493abc414174faf975425d65095ac4b4aeee54))
* **voiceprint:** build add-on locally, drop GHCR image reference ([e2ad20f](https://github.com/saya6k/ha-apps/commit/e2ad20fec1e9a28e32bfc83bf11f32416e5ffdf1))
* **voiceprint:** clean apt cache in builder stage ([1cc8700](https://github.com/saya6k/ha-apps/commit/1cc8700a585e8b9ed1de0008ea7ecdccc878e120))

## [0.8.0](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.7.0...voiceprint-v0.8.0) (2026-06-18)


### Features

* **voiceprint:** add custom AppArmor profile ([3c39a1f](https://github.com/saya6k/ha-apps/commit/3c39a1fe6b8175c1d5a47d2c2247d19ecef72e9b))
* **voiceprint:** add speaker-verifying Wyoming STT proxy add-on ([eaac8c1](https://github.com/saya6k/ha-apps/commit/eaac8c1bc7dd2f26246fb8c5b23234b4a47ba22e))
* **voiceprint:** default upstream to nemo-asr-cpp and ship GHCR image ([03f0096](https://github.com/saya6k/ha-apps/commit/03f0096020ebdebacac7be16be7444436339407d))


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **voiceprint:** add Show add-on badge and arch shields to README ([e3f0429](https://github.com/saya6k/ha-apps/commit/e3f0429717ecddf93ec69583ba783cae2c3e50bc))


### Build System

* **voiceprint:** --no-compile pip install in builder stage ([e7493ab](https://github.com/saya6k/ha-apps/commit/e7493abc414174faf975425d65095ac4b4aeee54))
* **voiceprint:** build add-on locally, drop GHCR image reference ([e2ad20f](https://github.com/saya6k/ha-apps/commit/e2ad20fec1e9a28e32bfc83bf11f32416e5ffdf1))
* **voiceprint:** clean apt cache in builder stage ([1cc8700](https://github.com/saya6k/ha-apps/commit/1cc8700a585e8b9ed1de0008ea7ecdccc878e120))

## [0.7.0](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.6.0...voiceprint-v0.7.0) (2026-06-18)


### Features

* **voiceprint:** add custom AppArmor profile ([3c39a1f](https://github.com/saya6k/ha-apps/commit/3c39a1fe6b8175c1d5a47d2c2247d19ecef72e9b))
* **voiceprint:** add speaker-verifying Wyoming STT proxy add-on ([eaac8c1](https://github.com/saya6k/ha-apps/commit/eaac8c1bc7dd2f26246fb8c5b23234b4a47ba22e))
* **voiceprint:** default upstream to nemo-asr-cpp and ship GHCR image ([03f0096](https://github.com/saya6k/ha-apps/commit/03f0096020ebdebacac7be16be7444436339407d))


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **voiceprint:** add Show add-on badge and arch shields to README ([e3f0429](https://github.com/saya6k/ha-apps/commit/e3f0429717ecddf93ec69583ba783cae2c3e50bc))


### Build System

* **voiceprint:** --no-compile pip install in builder stage ([e7493ab](https://github.com/saya6k/ha-apps/commit/e7493abc414174faf975425d65095ac4b4aeee54))
* **voiceprint:** build add-on locally, drop GHCR image reference ([e2ad20f](https://github.com/saya6k/ha-apps/commit/e2ad20fec1e9a28e32bfc83bf11f32416e5ffdf1))
* **voiceprint:** clean apt cache in builder stage ([1cc8700](https://github.com/saya6k/ha-apps/commit/1cc8700a585e8b9ed1de0008ea7ecdccc878e120))

## [0.6.0](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.5.0...voiceprint-v0.6.0) (2026-06-18)


### Features

* **voiceprint:** add custom AppArmor profile ([3c39a1f](https://github.com/saya6k/ha-apps/commit/3c39a1fe6b8175c1d5a47d2c2247d19ecef72e9b))
* **voiceprint:** add speaker-verifying Wyoming STT proxy add-on ([eaac8c1](https://github.com/saya6k/ha-apps/commit/eaac8c1bc7dd2f26246fb8c5b23234b4a47ba22e))
* **voiceprint:** default upstream to nemo-asr-cpp and ship GHCR image ([03f0096](https://github.com/saya6k/ha-apps/commit/03f0096020ebdebacac7be16be7444436339407d))


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **voiceprint:** add Show add-on badge and arch shields to README ([e3f0429](https://github.com/saya6k/ha-apps/commit/e3f0429717ecddf93ec69583ba783cae2c3e50bc))


### Build System

* **voiceprint:** --no-compile pip install in builder stage ([e7493ab](https://github.com/saya6k/ha-apps/commit/e7493abc414174faf975425d65095ac4b4aeee54))
* **voiceprint:** build add-on locally, drop GHCR image reference ([e2ad20f](https://github.com/saya6k/ha-apps/commit/e2ad20fec1e9a28e32bfc83bf11f32416e5ffdf1))
* **voiceprint:** clean apt cache in builder stage ([1cc8700](https://github.com/saya6k/ha-apps/commit/1cc8700a585e8b9ed1de0008ea7ecdccc878e120))

## [0.5.0](https://github.com/saya6k/ha-apps/compare/voiceprint-v0.4.0...voiceprint-v0.5.0) (2026-06-18)


### Features

* **voiceprint:** add custom AppArmor profile ([3c39a1f](https://github.com/saya6k/ha-apps/commit/3c39a1fe6b8175c1d5a47d2c2247d19ecef72e9b))
* **voiceprint:** add speaker-verifying Wyoming STT proxy add-on ([eaac8c1](https://github.com/saya6k/ha-apps/commit/eaac8c1bc7dd2f26246fb8c5b23234b4a47ba22e))
* **voiceprint:** default upstream to nemo-asr-cpp and ship GHCR image ([03f0096](https://github.com/saya6k/ha-apps/commit/03f0096020ebdebacac7be16be7444436339407d))


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **voiceprint:** add Show add-on badge and arch shields to README ([e3f0429](https://github.com/saya6k/ha-apps/commit/e3f0429717ecddf93ec69583ba783cae2c3e50bc))


### Build System

* **voiceprint:** --no-compile pip install in builder stage ([e7493ab](https://github.com/saya6k/ha-apps/commit/e7493abc414174faf975425d65095ac4b4aeee54))
* **voiceprint:** build add-on locally, drop GHCR image reference ([e2ad20f](https://github.com/saya6k/ha-apps/commit/e2ad20fec1e9a28e32bfc83bf11f32416e5ffdf1))
* **voiceprint:** clean apt cache in builder stage ([1cc8700](https://github.com/saya6k/ha-apps/commit/1cc8700a585e8b9ed1de0008ea7ecdccc878e120))

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
