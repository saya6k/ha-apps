---
name: app-dev-pr
description: Make a metadata change in ha-apps (catalog repo) and integrate it into dev. For changes to app source code, work in the ha-app-<slug> repo using its own [[app-dev-pr]] skill. For ha-apps promotion to main, use [[app-promote-to-main]].
---

# Integrate a ha-apps change into `dev`

ha-apps is the **catalog** — metadata, docs, CI config. Source code lives in
ha-app-* repos. All changes here land on `dev` first.

- **`dev`** — integration branch. CI required on PRs.
- **`main`** — stable. Advanced only via [[app-promote-to-main]].

> Commit message: [[conventional-commit]] with scope (e.g. `fix(otelcol):`,
> `ci(repo):`). Sanity checks: [[app-preflight]].

## 1. Branch off `dev`
```
git fetch origin && git switch -c <type>/<scope> origin/dev
```
Never commit directly on `dev` or `main`.

## 2. Pre-merge checks
Run [[app-preflight]] — for metadata-only apps: yamllint + markdownlint.

## 3. Integrate into `dev`
- One scope per commit. Never `--no-verify` / `--no-gpg-sign`.
- Open PR targeting `dev`:
  ```
  gh pr create --base dev --title "<type>(<scope>): <subject>" ...
  ```
  GitHub defaults to `main` — always pass `--base dev`.
- Single-scope PR → squash OK. Multi-scope → rebase-merge or split.
  See [[release-please-squash-gotcha]].
