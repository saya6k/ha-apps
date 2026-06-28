# Changelog

Releases from the next version onward are tracked in
[ha-app-* releases](https://github.com/saya6k/ha-app-livekit-wakeword/releases).


## [0.10.1](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.10.0...livekit-wakeword-v0.10.1) (2026-06-23)


### Bug Fixes

* **repo:** replace {,**} with explicit dir+glob rules in all AppArmor profiles ([6903c13](https://github.com/saya6k/ha-apps/commit/6903c1329a95f5833114dd3aabdc9849fbf8e7b8))

## [0.10.0](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.9.1...livekit-wakeword-v0.10.0) (2026-06-23)


### Features

* **livekit-wakeword:** add AppArmor profile ([d227413](https://github.com/saya6k/ha-apps/commit/d2274132016811f5eecca809d6a967f95448109c))

## [0.9.1](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.9.0...livekit-wakeword-v0.9.1) (2026-06-22)


### CI

* **repo:** tighten markdownlint scope and disable style-only rules ([9fe6f97](https://github.com/saya6k/ha-apps/commit/9fe6f97b9fee3e1c010f2ee534b36ea8de2a74fe))

## [0.9.0](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.8.0...livekit-wakeword-v0.9.0) (2026-06-18)


### Bug Fixes

* **repo:** add apparmor: true to all add-ons, remove custom profiles ([a8b8a61](https://github.com/saya6k/ha-apps/commit/a8b8a6163024fa611e2b661b90f37093640419fa))
* **repo:** remove redundant apparmor: true (linter default) ([423ac7f](https://github.com/saya6k/ha-apps/commit/423ac7ff0c4fbde79abdec4e86a08f5c91f6fe1f))

## [0.3.0](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.2.4...livekit-wakeword-v0.3.0) (2026-06-18)


### Features

* **livekit-wakeword:** add custom AppArmor profile ([dbd72a9](https://github.com/saya6k/ha-apps/commit/dbd72a9b1f909132acb3109ab75d73069ae4c0a2))
* **livekit-wakeword:** add Wyoming wake word add-on with incremental oWW-compatible bridge ([8355f66](https://github.com/saya6k/ha-apps/commit/8355f6608fc638fb8b8c6ac103d2d60482513b6c))


### Bug Fixes

* **livekit-wakeword:** add yaml document start, gitignore training data ([66356f3](https://github.com/saya6k/ha-apps/commit/66356f3f24f39f9c9628a7dcbbb32abb46640fdd))
* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **livekit-wakeword:** add Show add-on badge and arch shields to README ([b00064d](https://github.com/saya6k/ha-apps/commit/b00064d15d2e1b8fcfac083ce16167876995d8e7))
* **livekit-wakeword:** update Git tracking section — app is now tracked in git ([079b62d](https://github.com/saya6k/ha-apps/commit/079b62d1ac3148a692bc8b5bcfeaee770ae3984e))
* **zensical:** add Show add-on badge to README ([57ccc5c](https://github.com/saya6k/ha-apps/commit/57ccc5c3f992cedb2f76b78cc5dac01b2054746c))


### Build System

* **livekit-wakeword:** --no-compile pip install in builder stage ([04536c4](https://github.com/saya6k/ha-apps/commit/04536c4866ca7302361b8134bc378cd3bc86b82a))
* **livekit-wakeword:** add GHCR image reference to config.yaml ([#51](https://github.com/saya6k/ha-apps/issues/51)) ([c43289d](https://github.com/saya6k/ha-apps/commit/c43289de9d83ac0f06346e34298c867eb1b7a9f9))
* **livekit-wakeword:** build add-on locally, drop GHCR image reference ([416892c](https://github.com/saya6k/ha-apps/commit/416892cbf7f4a627b3591703b2c6b62d65a3785a))
* **livekit-wakeword:** clean apt cache in builder stage ([0f62e04](https://github.com/saya6k/ha-apps/commit/0f62e047f19cef40c58c4410328c30df56ab3ec4))


### CI

* **repo:** promote dev to main (CI hardening + workflow automation) ([#171](https://github.com/saya6k/ha-apps/issues/171)) ([c0f9c03](https://github.com/saya6k/ha-apps/commit/c0f9c03dded8e86a1b09df2d0ea5d366684cfa6e))

## [0.8.0](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.7.0...livekit-wakeword-v0.8.0) (2026-06-18)


### Features

* **livekit-wakeword:** add custom AppArmor profile ([dbd72a9](https://github.com/saya6k/ha-apps/commit/dbd72a9b1f909132acb3109ab75d73069ae4c0a2))
* **livekit-wakeword:** add Wyoming wake word add-on with incremental oWW-compatible bridge ([8355f66](https://github.com/saya6k/ha-apps/commit/8355f6608fc638fb8b8c6ac103d2d60482513b6c))


### Bug Fixes

* **livekit-wakeword:** add yaml document start, gitignore training data ([66356f3](https://github.com/saya6k/ha-apps/commit/66356f3f24f39f9c9628a7dcbbb32abb46640fdd))
* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **livekit-wakeword:** add Show add-on badge and arch shields to README ([b00064d](https://github.com/saya6k/ha-apps/commit/b00064d15d2e1b8fcfac083ce16167876995d8e7))
* **livekit-wakeword:** update Git tracking section — app is now tracked in git ([079b62d](https://github.com/saya6k/ha-apps/commit/079b62d1ac3148a692bc8b5bcfeaee770ae3984e))


### Build System

* **livekit-wakeword:** --no-compile pip install in builder stage ([04536c4](https://github.com/saya6k/ha-apps/commit/04536c4866ca7302361b8134bc378cd3bc86b82a))
* **livekit-wakeword:** add GHCR image reference to config.yaml ([#51](https://github.com/saya6k/ha-apps/issues/51)) ([c43289d](https://github.com/saya6k/ha-apps/commit/c43289de9d83ac0f06346e34298c867eb1b7a9f9))
* **livekit-wakeword:** build add-on locally, drop GHCR image reference ([416892c](https://github.com/saya6k/ha-apps/commit/416892cbf7f4a627b3591703b2c6b62d65a3785a))
* **livekit-wakeword:** clean apt cache in builder stage ([0f62e04](https://github.com/saya6k/ha-apps/commit/0f62e047f19cef40c58c4410328c30df56ab3ec4))


### CI

* **repo:** promote dev to main (CI hardening + workflow automation) ([#171](https://github.com/saya6k/ha-apps/issues/171)) ([c0f9c03](https://github.com/saya6k/ha-apps/commit/c0f9c03dded8e86a1b09df2d0ea5d366684cfa6e))

## [0.7.0](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.6.0...livekit-wakeword-v0.7.0) (2026-06-18)


### Features

* **livekit-wakeword:** add custom AppArmor profile ([dbd72a9](https://github.com/saya6k/ha-apps/commit/dbd72a9b1f909132acb3109ab75d73069ae4c0a2))
* **livekit-wakeword:** add Wyoming wake word add-on with incremental oWW-compatible bridge ([8355f66](https://github.com/saya6k/ha-apps/commit/8355f6608fc638fb8b8c6ac103d2d60482513b6c))


### Bug Fixes

* **livekit-wakeword:** add yaml document start, gitignore training data ([66356f3](https://github.com/saya6k/ha-apps/commit/66356f3f24f39f9c9628a7dcbbb32abb46640fdd))
* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **livekit-wakeword:** add Show add-on badge and arch shields to README ([b00064d](https://github.com/saya6k/ha-apps/commit/b00064d15d2e1b8fcfac083ce16167876995d8e7))
* **livekit-wakeword:** update Git tracking section — app is now tracked in git ([079b62d](https://github.com/saya6k/ha-apps/commit/079b62d1ac3148a692bc8b5bcfeaee770ae3984e))


### Build System

* **livekit-wakeword:** --no-compile pip install in builder stage ([04536c4](https://github.com/saya6k/ha-apps/commit/04536c4866ca7302361b8134bc378cd3bc86b82a))
* **livekit-wakeword:** add GHCR image reference to config.yaml ([#51](https://github.com/saya6k/ha-apps/issues/51)) ([c43289d](https://github.com/saya6k/ha-apps/commit/c43289de9d83ac0f06346e34298c867eb1b7a9f9))
* **livekit-wakeword:** build add-on locally, drop GHCR image reference ([416892c](https://github.com/saya6k/ha-apps/commit/416892cbf7f4a627b3591703b2c6b62d65a3785a))
* **livekit-wakeword:** clean apt cache in builder stage ([0f62e04](https://github.com/saya6k/ha-apps/commit/0f62e047f19cef40c58c4410328c30df56ab3ec4))


### CI

* **repo:** promote dev to main (CI hardening + workflow automation) ([#171](https://github.com/saya6k/ha-apps/issues/171)) ([c0f9c03](https://github.com/saya6k/ha-apps/commit/c0f9c03dded8e86a1b09df2d0ea5d366684cfa6e))

## [0.6.0](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.5.0...livekit-wakeword-v0.6.0) (2026-06-18)


### Features

* **livekit-wakeword:** add custom AppArmor profile ([dbd72a9](https://github.com/saya6k/ha-apps/commit/dbd72a9b1f909132acb3109ab75d73069ae4c0a2))
* **livekit-wakeword:** add Wyoming wake word add-on with incremental oWW-compatible bridge ([8355f66](https://github.com/saya6k/ha-apps/commit/8355f6608fc638fb8b8c6ac103d2d60482513b6c))


### Bug Fixes

* **livekit-wakeword:** add yaml document start, gitignore training data ([66356f3](https://github.com/saya6k/ha-apps/commit/66356f3f24f39f9c9628a7dcbbb32abb46640fdd))
* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **livekit-wakeword:** add Show add-on badge and arch shields to README ([b00064d](https://github.com/saya6k/ha-apps/commit/b00064d15d2e1b8fcfac083ce16167876995d8e7))
* **livekit-wakeword:** update Git tracking section — app is now tracked in git ([079b62d](https://github.com/saya6k/ha-apps/commit/079b62d1ac3148a692bc8b5bcfeaee770ae3984e))


### Build System

* **livekit-wakeword:** --no-compile pip install in builder stage ([04536c4](https://github.com/saya6k/ha-apps/commit/04536c4866ca7302361b8134bc378cd3bc86b82a))
* **livekit-wakeword:** add GHCR image reference to config.yaml ([#51](https://github.com/saya6k/ha-apps/issues/51)) ([c43289d](https://github.com/saya6k/ha-apps/commit/c43289de9d83ac0f06346e34298c867eb1b7a9f9))
* **livekit-wakeword:** build add-on locally, drop GHCR image reference ([416892c](https://github.com/saya6k/ha-apps/commit/416892cbf7f4a627b3591703b2c6b62d65a3785a))
* **livekit-wakeword:** clean apt cache in builder stage ([0f62e04](https://github.com/saya6k/ha-apps/commit/0f62e047f19cef40c58c4410328c30df56ab3ec4))


### CI

* **repo:** promote dev to main (CI hardening + workflow automation) ([#171](https://github.com/saya6k/ha-apps/issues/171)) ([c0f9c03](https://github.com/saya6k/ha-apps/commit/c0f9c03dded8e86a1b09df2d0ea5d366684cfa6e))

## [0.5.0](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.4.0...livekit-wakeword-v0.5.0) (2026-06-18)


### Features

* **livekit-wakeword:** add custom AppArmor profile ([dbd72a9](https://github.com/saya6k/ha-apps/commit/dbd72a9b1f909132acb3109ab75d73069ae4c0a2))
* **livekit-wakeword:** add Wyoming wake word add-on with incremental oWW-compatible bridge ([8355f66](https://github.com/saya6k/ha-apps/commit/8355f6608fc638fb8b8c6ac103d2d60482513b6c))


### Bug Fixes

* **livekit-wakeword:** add yaml document start, gitignore training data ([66356f3](https://github.com/saya6k/ha-apps/commit/66356f3f24f39f9c9628a7dcbbb32abb46640fdd))
* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **livekit-wakeword:** add Show add-on badge and arch shields to README ([b00064d](https://github.com/saya6k/ha-apps/commit/b00064d15d2e1b8fcfac083ce16167876995d8e7))
* **livekit-wakeword:** update Git tracking section — app is now tracked in git ([079b62d](https://github.com/saya6k/ha-apps/commit/079b62d1ac3148a692bc8b5bcfeaee770ae3984e))


### Build System

* **livekit-wakeword:** --no-compile pip install in builder stage ([04536c4](https://github.com/saya6k/ha-apps/commit/04536c4866ca7302361b8134bc378cd3bc86b82a))
* **livekit-wakeword:** add GHCR image reference to config.yaml ([#51](https://github.com/saya6k/ha-apps/issues/51)) ([c43289d](https://github.com/saya6k/ha-apps/commit/c43289de9d83ac0f06346e34298c867eb1b7a9f9))
* **livekit-wakeword:** build add-on locally, drop GHCR image reference ([416892c](https://github.com/saya6k/ha-apps/commit/416892cbf7f4a627b3591703b2c6b62d65a3785a))
* **livekit-wakeword:** clean apt cache in builder stage ([0f62e04](https://github.com/saya6k/ha-apps/commit/0f62e047f19cef40c58c4410328c30df56ab3ec4))


### CI

* **repo:** promote dev to main (CI hardening + workflow automation) ([#171](https://github.com/saya6k/ha-apps/issues/171)) ([c0f9c03](https://github.com/saya6k/ha-apps/commit/c0f9c03dded8e86a1b09df2d0ea5d366684cfa6e))

## [0.4.0](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.3.0...livekit-wakeword-v0.4.0) (2026-06-18)


### Features

* **livekit-wakeword:** add custom AppArmor profile ([dbd72a9](https://github.com/saya6k/ha-apps/commit/dbd72a9b1f909132acb3109ab75d73069ae4c0a2))
* **livekit-wakeword:** add Wyoming wake word add-on with incremental oWW-compatible bridge ([8355f66](https://github.com/saya6k/ha-apps/commit/8355f6608fc638fb8b8c6ac103d2d60482513b6c))


### Bug Fixes

* **livekit-wakeword:** add yaml document start, gitignore training data ([66356f3](https://github.com/saya6k/ha-apps/commit/66356f3f24f39f9c9628a7dcbbb32abb46640fdd))
* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))


### Documentation

* **livekit-wakeword:** add Show add-on badge and arch shields to README ([b00064d](https://github.com/saya6k/ha-apps/commit/b00064d15d2e1b8fcfac083ce16167876995d8e7))
* **livekit-wakeword:** update Git tracking section — app is now tracked in git ([079b62d](https://github.com/saya6k/ha-apps/commit/079b62d1ac3148a692bc8b5bcfeaee770ae3984e))


### Build System

* **livekit-wakeword:** --no-compile pip install in builder stage ([04536c4](https://github.com/saya6k/ha-apps/commit/04536c4866ca7302361b8134bc378cd3bc86b82a))
* **livekit-wakeword:** add GHCR image reference to config.yaml ([#51](https://github.com/saya6k/ha-apps/issues/51)) ([c43289d](https://github.com/saya6k/ha-apps/commit/c43289de9d83ac0f06346e34298c867eb1b7a9f9))
* **livekit-wakeword:** build add-on locally, drop GHCR image reference ([416892c](https://github.com/saya6k/ha-apps/commit/416892cbf7f4a627b3591703b2c6b62d65a3785a))
* **livekit-wakeword:** clean apt cache in builder stage ([0f62e04](https://github.com/saya6k/ha-apps/commit/0f62e047f19cef40c58c4410328c30df56ab3ec4))


### CI

* **repo:** promote dev to main (CI hardening + workflow automation) ([#171](https://github.com/saya6k/ha-apps/issues/171)) ([c0f9c03](https://github.com/saya6k/ha-apps/commit/c0f9c03dded8e86a1b09df2d0ea5d366684cfa6e))

## [0.3.0](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.2.4...livekit-wakeword-v0.3.0) (2026-06-18)


### Features

* **livekit-wakeword:** add custom AppArmor profile ([dbd72a9](https://github.com/saya6k/ha-apps/commit/dbd72a9b1f909132acb3109ab75d73069ae4c0a2))


### Documentation

* **livekit-wakeword:** add Show add-on badge and arch shields to README ([b00064d](https://github.com/saya6k/ha-apps/commit/b00064d15d2e1b8fcfac083ce16167876995d8e7))

## [0.2.4](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.2.3...livekit-wakeword-v0.2.4) (2026-06-18)


### CI

* **repo:** promote dev to main (CI hardening + workflow automation) ([#171](https://github.com/saya6k/ha-apps/issues/171)) ([c0f9c03](https://github.com/saya6k/ha-apps/commit/c0f9c03dded8e86a1b09df2d0ea5d366684cfa6e))

## [0.2.4](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.2.3...livekit-wakeword-v0.2.4) (2026-06-18)


### CI

* **repo:** promote dev to main (CI hardening + workflow automation) ([#171](https://github.com/saya6k/ha-apps/issues/171)) ([c0f9c03](https://github.com/saya6k/ha-apps/commit/c0f9c03dded8e86a1b09df2d0ea5d366684cfa6e))

## [0.2.3](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.2.2...livekit-wakeword-v0.2.3) (2026-06-18)


### Bug Fixes

* **livekit-wakeword:** add yaml document start, gitignore training data ([66356f3](https://github.com/saya6k/ha-apps/commit/66356f3f24f39f9c9628a7dcbbb32abb46640fdd))


### Build System

* **livekit-wakeword:** build add-on locally, drop GHCR image reference ([416892c](https://github.com/saya6k/ha-apps/commit/416892cbf7f4a627b3591703b2c6b62d65a3785a))

## [0.2.2](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.2.1...livekit-wakeword-v0.2.2) (2026-06-17)


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))

## [0.2.1](https://github.com/saya6k/ha-apps/compare/livekit-wakeword-v0.2.0...livekit-wakeword-v0.2.1) (2026-06-16)


### Build System

* **livekit-wakeword:** add GHCR image reference to config.yaml ([#51](https://github.com/saya6k/ha-apps/issues/51)) ([c43289d](https://github.com/saya6k/ha-apps/commit/c43289de9d83ac0f06346e34298c867eb1b7a9f9))

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
