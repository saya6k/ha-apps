---
name: app-dev-pr
description: Make a metadata change in ha-apps (catalog repo) and land it on main. For changes to app source code, work in the ha-app-<slug> repo using its own [[app-dev-pr]] skill.
---

# Land a ha-apps change on `main`

ha-apps is the **catalog** — metadata, docs, CI config. Source code lives in
ha-app-* repos. Changes PR directly to `main`.

> Commit message: [[conventional-commit]] with scope (e.g. `fix(otelcol):`,
> `ci(repo):`). Sanity checks: [[app-preflight]].

## 1. Branch off `main`
```
git fetch origin && git switch -c <type>/<scope> origin/main
```

## 2. Pre-merge checks
Run [[app-preflight]] — yamllint + markdownlint.

## 3. PR to `main`
- One scope per commit. Never `--no-verify` / `--no-gpg-sign`.
- Open PR targeting `main`:
  ```
  gh pr create --base main --title "<type>(<scope>): <subject>" ...
  ```
- CI ("CI passed") must be green before merge.
