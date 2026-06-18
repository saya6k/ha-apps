---
name: app-dev-pr
description: Drives this monorepo's dev-first flow — work integrates on `dev`, and a user-approved `dev → main` promotion triggers a release (release-please runs on `main` only, gated on CI success). Use when committing and shipping any app change. Defer to [[conventional-commit]] for message wording.
---

# App dev flow (integrate on `dev`, release on `main`)

Two long-lived branches:

- **`dev`** — integration branch. All app work lands here first. Branch
  protection: "CI passed" required on PRs (`enforce_admins: false`). No
  release-please here.
- **`main`** (released/stable) — advanced **only** by an explicit,
  user-approved `dev → main` PR. Branch protection: PR + "CI passed" required
  (`enforce_admins: false`). Deletion blocked on both branches.

> Commit message wording: [[conventional-commit]]. Per-app sanity checks:
> [[app-preflight]].

## 1. Branch off `dev`
- `git fetch origin && git switch -c <type>/<short-slug> origin/dev`.
- Never commit directly on `main`.

## 2. Pre-merge checks
- Run [[app-preflight]] for the changed app (Python parse, yamllint, shellcheck;
  docker build / Wyoming `describe` on request).

## 3. Integrate into `dev`
- Commit per [[conventional-commit]] — exactly one scope per commit; split
  commits that span apps. Never `--no-verify` / `--no-gpg-sign` — fix hook
  failures at the root cause.
- Land it on `dev`: `gh pr create --base dev ...` (GitHub defaults base to
  `main` — always pass `--base dev`; the PR title must be a valid Conventional
  Commit).
- **Merge method:** single-scope PR → squash is fine. Multi-scope PR → **do
  not squash** — rebase-merge or split into one PR per scope.
  See [[release-please-squash-gotcha]].
- No release is cut at this step.

## 4. Promote `dev → main` — REQUIRES explicit user approval
- **STOP. Never advance `main` without the user's explicit approval for that
  specific promotion.** Approval of dev-side work does NOT imply approval to
  promote; ask every time, naming what is promoted:
  `git log --oneline origin/main..origin/dev`
- Pre-conditions: `dev` CI green + app smoke-tested on a real HA pipeline.
- On approval, open a PR and let auto-merge handle it:
  ```
  gh pr create --base main --head dev \
    --title "chore(repo): promote dev to main" \
    --body "Promotion. CI must pass before merge."
  gh pr merge <number> --squash --auto
  ```
  `main` branch protection requires PR + "CI passed". release-please fires via
  `workflow_run` only after CI succeeds on `main` — never on a failing commit.

## 5. Release (fully automatic after promotion merges)

The pipeline runs without manual steps:

1. **release-please** (`release.yml`, `workflow_run` on CI success on `main`)
   opens `chore(main): release <ver>` PRs — one per changed app.
2. **automerge-release** (`automerge-release.yml`) detects `release-please--`
   head branches and immediately enables squash auto-merge.
3. **CI** runs on each release PR — build-image is **skipped** for
   `release-please--` branches (CHANGELOG + version bump only, no code change);
   lint and version-check still run.
4. Each release PR merges automatically once CI passes → tags `<addon>-v<ver>`.
5. **sync-dev** (`sync-dev.yml`, triggered on every `main` push) fast-forwards
   `dev` to `main` if dev is behind. Skips if dev is ahead (active dev) or has
   diverged (manual `git merge origin/main` needed before next promotion).

Review the auto-generated release PR diff (CHANGELOG / config.yaml /
pyproject.toml) — don't edit it.

## Never
- Commit directly on `main`, or advance `main` without explicit per-promotion approval.
- Force-push `main` or `dev`.
