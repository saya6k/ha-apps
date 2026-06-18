---
name: app-dev-pr
description: Branch off dev, run checks, and integrate a change into the `dev` branch. Use at the start of any app change. For promotion to main, use [[app-promote-to-main]]. Defer to [[conventional-commit]] for message wording.
---

# Integrate a change into `dev`

- **`dev`** — integration branch. Branch protection: "CI passed" required on
  PRs (`enforce_admins: false`). release-please creates prerelease PRs here
  (versions like `0.5.1-dev.0`) after CI succeeds.
- **`main`** — released/stable. Advanced only via [[app-promote-to-main]].

> Commit message wording: [[conventional-commit]]. Per-app sanity checks:
> [[app-preflight]].

## 1. Branch off `dev`
```
git fetch origin && git switch -c <type>/<short-slug> origin/dev
```
Never commit directly on `dev` or `main`.

## 2. Pre-merge checks
Run [[app-preflight]] for the changed app (Python parse, yamllint, shellcheck;
docker build / Wyoming `describe` on request).

## 3. Integrate into `dev`
- Commit per [[conventional-commit]] — exactly one scope per commit; split
  commits that span apps. Never `--no-verify` / `--no-gpg-sign`.
- Open a PR targeting `dev`:
  ```
  gh pr create --base dev --title "<type>(<scope>): <subject>" ...
  ```
  GitHub defaults base to `main` — always pass `--base dev`.
- **Merge method:** single-scope PR → squash is fine. Multi-scope PR → **do
  not squash** — rebase-merge or split into one PR per scope.
  See [[release-please-squash-gotcha]].

After merge, release-please will open a prerelease PR on `dev` once CI passes.
When dev is stable and the user approves, use [[app-promote-to-main]].
