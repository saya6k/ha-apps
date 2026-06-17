# Changelog

## [0.2.3](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.2...nemo-asr-c-v0.2.3) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** add s6-overlay user bundle and dependency declarations ([#80](https://github.com/saya6k/ha-apps/issues/80)) ([6b86e8d](https://github.com/saya6k/ha-apps/commit/6b86e8d043b652ddc2b3b257067a56f9e7060bac))

## [0.2.2](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.1...nemo-asr-c-v0.2.2) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** use nullglob for wildcard chmod ([#77](https://github.com/saya6k/ha-apps/issues/77)) ([36f018c](https://github.com/saya6k/ha-apps/commit/36f018c031ee14e0bb0f06d11613671fc29d79af))

## [0.2.1](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.0...nemo-asr-c-v0.2.1) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** add missing discovery up file for s6-rc oneshot service ([#74](https://github.com/saya6k/ha-apps/issues/74)) ([1f234ca](https://github.com/saya6k/ha-apps/commit/1f234ca76f8892dcb83933ca1cae3a39e864c73c))

## [0.2.0](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.1.0...nemo-asr-c-v0.2.0) (2026-06-17)


### Features

* **nemo-asr-c:** add pure-C Nemotron ASR Wyoming STT add-on ([#68](https://github.com/saya6k/ha-apps/issues/68)) ([ec6d1dd](https://github.com/saya6k/ha-apps/commit/ec6d1dd67843ea62d4d5856c285e226cc46d8902))


### Bug Fixes

* **nemo-asr-c:** pin Dockerfile to upstream commit SHA ([#70](https://github.com/saya6k/ha-apps/issues/70)) ([e23e564](https://github.com/saya6k/ha-apps/commit/e23e564a57ba249687477800b630f6fe4ce84b41))

## 0.1.0 (unreleased)

- Initial scaffold: Wyoming STT add-on running nemotron-asr-streaming.c.
  Boot-time .nemo → .bin conversion with multiple quantization formats.
