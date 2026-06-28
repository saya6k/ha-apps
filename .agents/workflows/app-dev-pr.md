---
name: app-dev-pr
description: Integrate a change into the right branch. For ha-apps (catalog metadata), branch from dev and PR to dev. For ha-app-* (source repos), branch from main and PR to main. Use at the start of any change. For ha-apps promotion to main, use [[app-promote-to-main]].
---

# Integrate a change

There are two distinct repos to work in:

| Repo | Branch model | Scope in commits | Release trigger |
|---|---|---|---|
| **ha-apps** (catalog) | `dev` → PR → `dev` → [[app-promote-to-main]] → `main` | required (e.g. `fix(otelcol):`) | sync PR from ha-app-* dispatch |
| **ha-app-\*** (source) | feature branch → PR → `main` | optional (`feat:` prefix for autolabeler) | manual draft publish |

---

## Working in ha-apps (metadata changes: config.yaml, docs, CI)

- **`dev`** — integration branch. CI required on PRs.
- **`main`** — stable. Advanced only via [[app-promote-to-main]].

### 1. Branch off `dev`
```
git fetch origin && git switch -c <type>/<short-slug> origin/dev
```
Never commit directly on `dev` or `main`.

### 2. Pre-merge checks
Run [[app-preflight]] — for metadata-only apps this is yamllint + markdownlint.

### 3. Integrate into `dev`
- Commit per [[conventional-commit]] — one scope per commit.
  Never `--no-verify` / `--no-gpg-sign`.
- Open PR targeting `dev`:
  ```
  gh pr create --base dev --title "<type>(<scope>): <subject>" ...
  ```
  GitHub defaults base to `main` — always pass `--base dev`.
- **Merge method:** single-scope → squash OK. Multi-scope → rebase-merge or
  split. See [[release-please-squash-gotcha]].

---

## Working in ha-app-* (source changes: Dockerfile, bridge code, config.yaml)

ha-app-* repos have **only `main`** — no `dev` branch.

### 1. Branch off `main`
```
cd ~/Projects/ha-app-<slug>
git fetch origin && git switch -c <type>/<short-desc> origin/main
```

### 2. Pre-merge checks
Run [[app-preflight]] from inside the ha-app-* repo directory.

### 3. PR to `main`
- Use a conventional-commit-style PR **title** — the autolabeler picks up
  `feat:` / `fix:` / `chore:` prefixes to categorise the release draft.
  No scope required (whole repo is one app).
- Squash merge is fine (single app, no multi-scope concern).
  ```
  gh pr create --base main --title "feat: <subject>" ...
  ```

### 4. After merge → release
- release-drafter updates the draft for `v<next-patch>`.
- When ready to ship: publish the draft on GitHub.
- `build.yml` triggers → GHCR images pushed → ha-apps sync PR opened automatically.
