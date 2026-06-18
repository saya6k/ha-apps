---
name: app-dev-pr
description: Drives this monorepo's dev-first flow — work integrates on `dev`, and a user-approved `dev → main` promotion is what triggers a release (release-please runs on `main` only). Use when committing and shipping any app change. Defer to [[conventional-commit]] for message wording.
---

# App dev flow (integrate on `dev`, release on `main`)

Two long-lived branches:

- **`dev`** — integration branch. All app work lands here first (a PR based on
  `dev`, or a local merge pushed to `origin/dev`). **release-please does NOT run
  on `dev`** — no releases are cut here.
- **`main`** (default, released/stable) — advanced **only** by an explicit,
  user-approved `dev → main` promotion. release-please runs on `main`
  (`.github/workflows/release.yml`, `on: push: branches: [main]`) and opens the
  `chore(main): release <ver>` PR there.

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
- Land it on `dev`: a PR with `gh pr create --base dev ...` (GitHub defaults the
  base to `main`, so pass `--base dev` explicitly; the PR title must itself be a
  valid Conventional Commit), or a local merge into `dev` pushed to `origin/dev`.
- **Merge method:** single-scope PR → squash is fine (the title becomes the one
  commit). Multi-scope PR → **do not squash** — it collapses every scope into the
  title's, so release-please drops the rest; rebase-merge to keep each commit
  intact, or split into one PR per scope. See [[release-please-squash-gotcha]].
- No release is cut at this step.

## 4. Promote `dev → main` — REQUIRES explicit user approval
- **STOP. Never advance `main` without the user's explicit approval for that
  specific promotion.** Approval of dev-side work does NOT imply approval to
  promote; ask every time, naming what is promoted
  (`git log --oneline origin/main..origin/dev`).
- Pre-conditions before you ask: `dev` CI green, and the app smoke-tested on a
  real HA pipeline (not just unit tests).
- On approval, fast-forward `main` to `dev`:
  ```
  git fetch origin
  git switch main
  git merge --ff-only origin/dev
  git push origin main
  ```
  `--ff-only` fails loudly if `main` has diverged — resolve explicitly. Never
  force-push `main`.

## 5. Release on `main`, then re-sync `dev`
- The promotion push to `main` triggers release-please, which opens
  `chore(main): release <ver>` against `main`. Its diff (CHANGELOG / config.yaml
  / pyproject.toml / manifest) is auto-generated — review, don't edit.
- Merge that release PR to land the version bump on `main` and tag
  `<addon>-v<ver>` (no image is published — HA builds the add-on locally from
  its Dockerfile; CI build-tests it on PRs and `main`/`dev` pushes).
- `main` now carries a release commit `dev` lacks. Fast-forward `dev` back up so
  the next promotion stays linear:
  ```
  git switch dev && git merge --ff-only origin/main && git push origin dev
  ```

## Never
- Commit directly on `main`, or advance `main` without explicit per-promotion approval.
- **Force-push `main`.** (The one-time backward reset that set up this flow was a
  deliberate setup step, not the steady state.)
