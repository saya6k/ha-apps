# Changelog

## [0.2.12](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.11...nemo-asr-c-v0.2.12) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** sync __init__.py version to 0.2.11 ([cba60d2](https://github.com/saya6k/ha-apps/commit/cba60d294a962c23fe62124d7f1d8c6cf6c39963))

## [0.2.11](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.10...nemo-asr-c-v0.2.11) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** address code review findings ([ca90cc3](https://github.com/saya6k/ha-apps/commit/ca90cc32ac3d14eda1993fada13bd902756652c1))
* **nemo-asr-c:** set restype=None for void nemo_set_att_right ([507dffd](https://github.com/saya6k/ha-apps/commit/507dffdd93a39bb27533ac31d38466c8793f7d2c))
* **nemo-asr-c:** use Attribution object for AsrProgram, not plain string ([ea904bd](https://github.com/saya6k/ha-apps/commit/ea904bdaf52ec3832f62ec1414688c515866bf5b))
* **nemo-asr-c:** wire up att_right, drop unimplemented hotword options, sync version ([6bc0767](https://github.com/saya6k/ha-apps/commit/6bc0767331a36748b629861d953b9d3c6cc9d037))

## [0.2.10](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.9...nemo-asr-c-v0.2.10) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** add graceful shutdown via s6 down and halt-on-failure finish ([#96](https://github.com/saya6k/ha-apps/issues/96)) ([df9e8c5](https://github.com/saya6k/ha-apps/commit/df9e8c55363a5f6afb62c7247487b174854dcfb1))

## [0.2.9](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.8...nemo-asr-c-v0.2.9) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** disable zeroconf by default to prevent boot crash ([#94](https://github.com/saya6k/ha-apps/issues/94)) ([26fda73](https://github.com/saya6k/ha-apps/commit/26fda73f3ba4058df86601138cb28f4f1c81868d))

## [0.2.8](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.7...nemo-asr-c-v0.2.8) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** prevent double-free in close() and add missing AsrModel args ([#92](https://github.com/saya6k/ha-apps/issues/92)) ([021ae09](https://github.com/saya6k/ha-apps/commit/021ae09695a3f20e57c116671010b52c847491cd))

## [0.2.7](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.6...nemo-asr-c-v0.2.7) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** set rnnt=None after finish to prevent double-free in close() ([#90](https://github.com/saya6k/ha-apps/issues/90)) ([0f18208](https://github.com/saya6k/ha-apps/commit/0f1820829e2f54653e42ae4101458ce9041fad9a))

## [0.2.6](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.5...nemo-asr-c-v0.2.6) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** remove broken hf_hub_download call with filename=None ([#88](https://github.com/saya6k/ha-apps/issues/88)) ([6803dba](https://github.com/saya6k/ha-apps/commit/6803dba76f358fbeecb3320af0c091b4ba8f46cc))

## [0.2.5](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.4...nemo-asr-c-v0.2.5) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** fix debug_logging flag concatenation in run script ([bf03661](https://github.com/saya6k/ha-apps/commit/bf03661c3cc9f967a9077aa0c9f7f9f93aa34bdc))

## [0.2.4](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.3...nemo-asr-c-v0.2.4) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** use bashio::discovery instead of python3 -m wyoming ([#84](https://github.com/saya6k/ha-apps/issues/84)) ([4e5fc4d](https://github.com/saya6k/ha-apps/commit/4e5fc4d9e1d996921a18e10d951b95c7afaa90be))

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
