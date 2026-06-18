# Changelog

## [0.6.0](https://github.com/saya6k/ha-apps/compare/nemotron-asr-c-v0.5.0...nemotron-asr-c-v0.6.0) (2026-06-18)


### Features

* **nemotron-asr-c:** add custom AppArmor profile ([93132e3](https://github.com/saya6k/ha-apps/commit/93132e385ce4cfb8f80ca6d878d645bd0e3fb342))


### Documentation

* **nemotron-asr-c:** fix streaming description, add badge and arch shields ([d3d8f29](https://github.com/saya6k/ha-apps/commit/d3d8f29c7fe98849998d92ddc14ed4814b0fc71f))

## [0.5.0](https://github.com/saya6k/ha-apps/compare/nemotron-asr-c-v0.4.0...nemotron-asr-c-v0.5.0) (2026-06-18)


### Features

* **nemotron-asr-c:** implement true streaming with TranscriptChunk events ([#147](https://github.com/saya6k/ha-apps/issues/147)) ([1cd6c8b](https://github.com/saya6k/ha-apps/commit/1cd6c8be90124fd1a2e0f7144df6383a39ed0f78))


### Bug Fixes

* **nemotron-asr-c:** auto-detect .nemo compression with tar mode r:* ([a66aeb2](https://github.com/saya6k/ha-apps/commit/a66aeb24bae70216a4eb958eedfcd3286971f254))
* **nemotron-asr-c:** drive the stateful C streaming cascade ([c74503b](https://github.com/saya6k/ha-apps/commit/c74503b78d31af01e3ab9a4e6f916b63fa5d6875))


### Build System

* **nemotron-asr-c:** add GHCR image reference to config.yaml ([22a7488](https://github.com/saya6k/ha-apps/commit/22a7488c2d3a66934a0cb33a1aa02897bc4767db))
* **nemotron-asr-c:** build add-on locally, drop GHCR image reference ([b44a52a](https://github.com/saya6k/ha-apps/commit/b44a52a7389288bf75456b863e2bf82f47ace923))

## [0.4.0](https://github.com/saya6k/ha-apps/compare/nemotron-asr-c-v0.3.11...nemotron-asr-c-v0.4.0) (2026-06-18)


### Features

* **nemotron-asr-c:** promote to stable ([2c526a8](https://github.com/saya6k/ha-apps/commit/2c526a877fdc1709c7381d48e6a78443436ce8fb))

## [0.3.11](https://github.com/saya6k/ha-apps/compare/nemotron-asr-c-v0.3.10...nemotron-asr-c-v0.3.11) (2026-06-17)


### Bug Fixes

* **nemotron-asr-c:** support plain-tar .nemo files alongside gzip ([4a74b19](https://github.com/saya6k/ha-apps/commit/4a74b1916c322b5ef50a6bc00bc5080be389e3de))

## [0.3.10](https://github.com/saya6k/ha-apps/compare/nemotron-asr-c-v0.3.9...nemotron-asr-c-v0.3.10) (2026-06-17)


### Bug Fixes

* **nemotron-asr-c:** add hf-xet extra for Xet-only model repos ([884e48e](https://github.com/saya6k/ha-apps/commit/884e48e7322dca3a6b91f41eabbf3d42f0b225d1))

## [0.3.9](https://github.com/saya6k/ha-apps/compare/nemotron-asr-c-v0.3.8...nemotron-asr-c-v0.3.9) (2026-06-17)


### Bug Fixes

* **nemotron-asr-c:** prevent restart loop on bootstrap failure, support Xet models ([f178b29](https://github.com/saya6k/ha-apps/commit/f178b29035a8928407ecd5455317868d702e84cb))

## [0.3.8](https://github.com/saya6k/ha-apps/compare/nemotron-asr-c-v0.3.7...nemotron-asr-c-v0.3.8) (2026-06-17)


### Code Refactoring

* **repo:** rename nemo-asr-c to nemotron-asr-c, delete nemotron-asr (ONNX) ([#128](https://github.com/saya6k/ha-apps/issues/128)) ([2b822a3](https://github.com/saya6k/ha-apps/commit/2b822a3653f1d9e3c70b0fa4f2fd54d94b56e6f2))

## [0.3.7](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.3.6...nemo-asr-c-v0.3.7) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** switch to fully-buffered transcription, strip language tags ([#125](https://github.com/saya6k/ha-apps/issues/125)) ([0cc998f](https://github.com/saya6k/ha-apps/commit/0cc998f19fe5e6caa771dab67bfc77845a392967))

## [0.3.6](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.3.5...nemo-asr-c-v0.3.6) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** buffer audio chunks before feeding C runtime to prevent backpressure ([#122](https://github.com/saya6k/ha-apps/issues/122)) ([5830d92](https://github.com/saya6k/ha-apps/commit/5830d92fa5b73f0d56b6a08f4fc0c41a87b95b05))

## [0.3.5](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.3.4...nemo-asr-c-v0.3.5) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** add debug logging for every incoming Wyoming event ([#120](https://github.com/saya6k/ha-apps/issues/120)) ([84e9c52](https://github.com/saya6k/ha-apps/commit/84e9c5286db4d888966f842e41e326c4c504c5ef))

## [0.3.4](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.3.3...nemo-asr-c-v0.3.4) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** drop streaming transcript events, narrow lock to C calls ([#118](https://github.com/saya6k/ha-apps/issues/118)) ([f0f060a](https://github.com/saya6k/ha-apps/commit/f0f060ad997ec39c90e7d7a2bf07e6f31747602a))

## [0.3.3](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.3.2...nemo-asr-c-v0.3.3) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** send TranscriptStart on Transcribe, not AudioStart ([#116](https://github.com/saya6k/ha-apps/issues/116)) ([7171bf2](https://github.com/saya6k/ha-apps/commit/7171bf25e0c3bad3715c7533a76d95f0a586da36))

## [0.3.2](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.3.1...nemo-asr-c-v0.3.2) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** pass hf_token, hotwords, hotword_boost from config to run script ([4ec149c](https://github.com/saya6k/ha-apps/commit/4ec149c5db5f9fdbd3525fabbfde485f238f690f))

## [0.3.1](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.3.0...nemo-asr-c-v0.3.1) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** replace typeof() casts with plain void* assigns for -pedantic ([33b904c](https://github.com/saya6k/ha-apps/commit/33b904cb6a4f4e7f5af174538e8ca18fdda3a44a))

## [0.3.0](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.15...nemo-asr-c-v0.3.0) (2026-06-17)


### Features

* **nemo-asr-c:** add RNN-T hotword biasing for contextual word boosting ([5b8cf99](https://github.com/saya6k/ha-apps/commit/5b8cf99725825bbf6a77f93dcbbe8a4e5b208493))

## [0.2.15](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.14...nemo-asr-c-v0.2.15) (2026-06-17)


### Code Refactoring

* **nemo-asr-c:** remove unimplemented w8a16 and q4p quantization stubs ([#108](https://github.com/saya6k/ha-apps/issues/108)) ([43b7e70](https://github.com/saya6k/ha-apps/commit/43b7e7041f2f8b2b5688c35c587273a079b8b030))

## [0.2.14](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.13...nemo-asr-c-v0.2.14) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** cleanup old models on config change and detect upstream updates ([5fc24a7](https://github.com/saya6k/ha-apps/commit/5fc24a7af52e1949e9141702c025323bb114d312))
* **nemo-asr-c:** cleanup old models on config change and detect upstream updates ([5fc24a7](https://github.com/saya6k/ha-apps/commit/5fc24a7af52e1949e9141702c025323bb114d312))
* **repo:** derive __version__ from pyproject.toml, drop generic extra-file ([be97102](https://github.com/saya6k/ha-apps/commit/be971024b32236c91fb56d3eef09077df8869fc0))

## [0.2.13](https://github.com/saya6k/ha-apps/compare/nemo-asr-c-v0.2.12...nemo-asr-c-v0.2.13) (2026-06-17)


### Bug Fixes

* **nemo-asr-c:** normalize patch path prefixes for git apply compatibility ([6a9cbbd](https://github.com/saya6k/ha-apps/commit/6a9cbbd2ae0dee4b372b8d72bc387814ba944e17))

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
