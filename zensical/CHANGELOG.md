# Changelog

Releases from the next version onward are tracked in
[ha-app-* releases](https://github.com/saya6k/ha-app-zensical/releases).




## [0.3.8](https://github.com/saya6k/ha-app-zensical/releases/tag/v0.3.8)

Re-dispatch after notify job fix.

## [0.3.7](https://github.com/saya6k/ha-apps/compare/zensical-v0.3.6...zensical-v0.3.7) (2026-06-23)


### Bug Fixes

* **zensical:** add master_process off to silence initgroups emerg ([#413](https://github.com/saya6k/ha-apps/issues/413)) ([5d1abc8](https://github.com/saya6k/ha-apps/commit/5d1abc88428ec36f20a6e9dd18cc46e0cd03409f))
* **zensical:** fix nginx crash loop in HA containers (no CAP_CHOWN/SETGID) ([21e8180](https://github.com/saya6k/ha-apps/commit/21e8180a7fa7b8ce8c5ffd66c96ec0ee5d919d9b))
* **zensical:** redirect nginx temp dirs to /tmp; add user nginx ([#409](https://github.com/saya6k/ha-apps/issues/409)) ([3aa8347](https://github.com/saya6k/ha-apps/commit/3aa8347854732ad15d7eec22a267813972721259))
* **zensical:** redirect nginx temp dirs to /tmp; run as root without user directive ([#411](https://github.com/saya6k/ha-apps/issues/411)) ([04905b3](https://github.com/saya6k/ha-apps/commit/04905b30ef77fe59d6a93b1bd1b96068b0d9a2eb))
* **zensical:** run nginx as nginx user via s6-setuidgid; move pid to /tmp ([#410](https://github.com/saya6k/ha-apps/issues/410)) ([85bc05f](https://github.com/saya6k/ha-apps/commit/85bc05f52bb94ae1159e15562a1cd1a5e7ce1d88))
* **zensical:** set user root in nginx.conf to make temp-dir chown a no-op ([#412](https://github.com/saya6k/ha-apps/issues/412)) ([d3ac5b6](https://github.com/saya6k/ha-apps/commit/d3ac5b6516fb043e96124a03a375d15d8e8b1cad))

## [0.3.6](https://github.com/saya6k/ha-apps/compare/zensical-v0.3.5...zensical-v0.3.6) (2026-06-23)


### Bug Fixes

* **zensical,wardrowbe:** remove runtime chown; fix ownership at Dockerfile build time ([68cd371](https://github.com/saya6k/ha-apps/commit/68cd3714ba342e6cbf15b1af10431af470c13d84))
* **zensical:** pre-create nginx temp dirs with ownership at build time ([a32a55d](https://github.com/saya6k/ha-apps/commit/a32a55d3554d492252c00974d4d0df5814aeb78a))

## [0.3.5](https://github.com/saya6k/ha-apps/compare/zensical-v0.3.4...zensical-v0.3.5) (2026-06-23)


### Bug Fixes

* **zensical:** remove temp_path overrides; fix pre-config error log path ([6b3b492](https://github.com/saya6k/ha-apps/commit/6b3b492e721d0a32f2b87ceb8be7281dcefdf59f))
* **zensical:** remove temp_path overrides; fix pre-config error log path ([fceca93](https://github.com/saya6k/ha-apps/commit/fceca932a1f7453f5567757b6b18c773aabf891c))

## [0.3.4](https://github.com/saya6k/ha-apps/compare/zensical-v0.3.3...zensical-v0.3.4) (2026-06-23)


### Bug Fixes

* **zensical:** remove duplicate daemon directive and fix pre-config error log ([d7ce93f](https://github.com/saya6k/ha-apps/commit/d7ce93f81d382f374e0f08bfded2fb1a837815fd))
* **zensical:** remove duplicate daemon directive and fix pre-config error log ([b2f6519](https://github.com/saya6k/ha-apps/commit/b2f6519479803542cdf384d3078a12c94ce3ce70))

## [0.3.3](https://github.com/saya6k/ha-apps/compare/zensical-v0.3.2...zensical-v0.3.3) (2026-06-23)


### Bug Fixes

* **zensical:** redirect nginx logs to stderr, temp to /tmp ([335f6ac](https://github.com/saya6k/ha-apps/commit/335f6acd041c47ddbdfa322f0b94849b1c208622))

## [0.3.2](https://github.com/saya6k/ha-apps/compare/zensical-v0.3.1...zensical-v0.3.2) (2026-06-23)


### Bug Fixes

* **repo:** replace {,**} with explicit dir+glob rules in all AppArmor profiles ([6903c13](https://github.com/saya6k/ha-apps/commit/6903c1329a95f5833114dd3aabdc9849fbf8e7b8))

## [0.3.1](https://github.com/saya6k/ha-apps/compare/zensical-v0.3.0...zensical-v0.3.1) (2026-06-23)


### Bug Fixes

* **zensical:** allow AppArmor write access to /var/lib/nginx ([f27aa3e](https://github.com/saya6k/ha-apps/commit/f27aa3e83ef37cafdf0209f95564b41d7726ed2d))

## [0.2.3](https://github.com/saya6k/ha-apps/compare/zensical-v0.2.2...zensical-v0.2.3) (2026-06-22)


### Documentation

* **zensical:** reorder README shields — Show add-on below for-the-badge badges ([c8961d9](https://github.com/saya6k/ha-apps/commit/c8961d92aff8d56f2ecbc4d2ed8fc1cfde2b4c98))


### CI

* **repo:** tighten markdownlint scope and disable style-only rules ([9fe6f97](https://github.com/saya6k/ha-apps/commit/9fe6f97b9fee3e1c010f2ee534b36ea8de2a74fe))

## [0.2.2](https://github.com/saya6k/ha-apps/compare/zensical-v0.2.1...zensical-v0.2.2) (2026-06-18)


### Bug Fixes

* **repo:** add apparmor: true to all add-ons, remove custom profiles ([6ccfe5d](https://github.com/saya6k/ha-apps/commit/6ccfe5d4b5daf805d66b7dbcdc1c71ab95e106e1))
* **repo:** add apparmor: true to all add-ons, remove custom profiles ([a8b8a61](https://github.com/saya6k/ha-apps/commit/a8b8a6163024fa611e2b661b90f37093640419fa))
* **repo:** remove redundant apparmor: true (linter default) ([423ac7f](https://github.com/saya6k/ha-apps/commit/423ac7ff0c4fbde79abdec4e86a08f5c91f6fe1f))

## [0.2.1](https://github.com/saya6k/ha-apps/compare/zensical-v0.2.0...zensical-v0.2.1) (2026-06-18)


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))
* **zensical:** persist example-seeded marker so a deleted example stays gone ([29d198e](https://github.com/saya6k/ha-apps/commit/29d198ee3b34c37313bf52c6b54b23008c9fd5d5))


### Documentation

* **zensical:** note local build instead of prebuilt GHCR image ([a17591c](https://github.com/saya6k/ha-apps/commit/a17591ce79675f1ef7ab99e8b853811979f61ef2))


### Build System

* **zensical:** build add-on locally, drop GHCR image reference ([55d524c](https://github.com/saya6k/ha-apps/commit/55d524c0df052a4f9e77ffbca9e7fce3fbdeacc7))
* **zensical:** migrate off build.yaml, pin base image, mark stable ([84f46d1](https://github.com/saya6k/ha-apps/commit/84f46d188f544041dd1a3dabbf3b8c0daca43515))
* **zensical:** reference prebuilt public GHCR image ([e49b1be](https://github.com/saya6k/ha-apps/commit/e49b1bedba90e33967ae71561ef39a2ee69338ad))

## [0.1.4](https://github.com/saya6k/ha-apps/compare/zensical-v0.1.3...zensical-v0.1.4) (2026-06-18)


### Documentation

* **zensical:** note local build instead of prebuilt GHCR image ([a17591c](https://github.com/saya6k/ha-apps/commit/a17591ce79675f1ef7ab99e8b853811979f61ef2))


### Build System

* **zensical:** build add-on locally, drop GHCR image reference ([55d524c](https://github.com/saya6k/ha-apps/commit/55d524c0df052a4f9e77ffbca9e7fce3fbdeacc7))

## [0.1.3](https://github.com/saya6k/ha-apps/compare/zensical-v0.1.2...zensical-v0.1.3) (2026-06-17)


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))

## [0.1.2](https://github.com/saya6k/ha-apps/compare/zensical-v0.1.1...zensical-v0.1.2) (2026-06-15)


### Build System

* **zensical:** reference prebuilt public GHCR image ([e49b1be](https://github.com/saya6k/ha-apps/commit/e49b1bedba90e33967ae71561ef39a2ee69338ad))

## [0.1.1](https://github.com/saya6k/ha-apps/compare/zensical-v0.1.0...zensical-v0.1.1) (2026-06-15)


### Bug Fixes

* **zensical:** persist example-seeded marker so a deleted example stays gone ([29d198e](https://github.com/saya6k/ha-apps/commit/29d198ee3b34c37313bf52c6b54b23008c9fd5d5))


### Build System

* **zensical:** migrate off build.yaml, pin base image, mark stable ([84f46d1](https://github.com/saya6k/ha-apps/commit/84f46d188f544041dd1a3dabbf3b8c0daca43515))

## 0.1.0

- First release. Renders `/config/docs/` as a
  [Zensical](https://zensical.org/) site (the Material for MkDocs team's
  successor SSG) exposed through the Home Assistant ingress side panel.
  Configuration uses Zensical's native `zensical.toml` format; the same
  keys (`site_name`, `theme.features`, `theme.palette`,
  `markdown_extensions.*`) that users know from `mkdocs.yml` carry over
  with minor syntactic differences.
- Landing page is `/config/docs/index.md`; a placeholder is rendered
  if the user hasn't supplied one yet. `/config/README.md` is not read
  by the add-on.
- File watcher (`inotifywait`) detects edits to `/config/docs/` or
  `/addon_config/` and rebuilds the site within ~1 second; nginx
  serves the latest build.
- Seeds `/config/docs/` (with `index.md` + `getting-started.md`) on
  first start *only* if the directory is missing — existing user
  files are never overwritten.
- Single-source customisation via `/config/zensical.toml`: the same
  file that the add-on uses for rendering is also what you publish to
  GitHub Pages. On first start the add-on writes a starter
  `/config/zensical.example.toml` (relative paths, GH-Pages-ready)
  that you can rename to `zensical.toml` to activate.
- Add-on-only override via `/addon_config/zensical.toml` is also
  honoured as a middle-priority fallback if you prefer to keep
  add-on-specific settings out of the published /config directory.
- Resolved config goes through `effective-config.py` before each
  build — `docs_dir` and `site_dir` are always rewritten to `"docs"`
  / `"site"` and the effective TOML is written to
  `/var/lib/zensical/zensical.toml`, so those relative paths resolve
  to the container locations nginx and sync.sh rely on. The user's
  publish-side values (e.g. `docs_dir = "docs"`, `site_dir = "_site"`)
  are honoured by external `zensical build` but transparently
  overridden inside the add-on. Required because Zensical 0.0.43
  panics on absolute `docs_dir` / `site_dir`.
- Standard `log_level` option (default `info`; one of `trace` / `debug` /
  `info` / `notice` / `warning` / `error` / `fatal`) controls bashio
  log filtering. Translated EN + KO. Zensical itself has no verbosity
  flags, so this only affects the add-on's own log lines.
- amd64 + aarch64 multi-arch build via
  [`hassio-addons/workflows`](https://github.com/hassio-addons/workflows).
  Pre-built `musllinux_1_2` wheels for Zensical make Alpine install
  fast — no Rust toolchain needed in the image.
