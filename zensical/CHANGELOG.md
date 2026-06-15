# Changelog

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
