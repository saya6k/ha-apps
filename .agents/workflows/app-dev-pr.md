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
  gh pr merge <number> --merge --auto
  ```
  **Must use `--merge` (merge commit), not `--squash` or `--rebase`.**
  - `--squash`: collapses everything into the PR title — release-please
    ignores it. See [[release-please-squash-gotcha]].
  - `--rebase`: rebases each commit onto main, creating new SHAs. dev's
    original SHAs are no longer ancestors of main, so sync-dev's FF fails
    every time, requiring a manual force-push to re-sync.
  - `--merge`: creates a merge commit on main with dev as a parent. dev's
    commits remain ancestors of main → sync-dev FF works cleanly. release-
    please reads commits through the merge commit and routes them correctly.
  `main` branch protection requires PR + "CI passed". release-please fires via
  `workflow_run` only after CI succeeds on `main` — never on a failing commit.

## 5. Verify and sync after promotion

Once the promotion PR merges, wait for and confirm this sequence before doing
anything else:

1. **CI passes on `main`** — check Actions tab or:
   ```
   gh run list --repo saya6k/ha-apps --workflow CI --branch main --limit 1 \
     --json status,conclusion
   ```
2. **release-please opens release PRs** (`release.yml` fires via `workflow_run`
   after CI succeeds). **automerge-release** immediately sets squash auto-merge
   on each. CI on release PRs skips build-image; lint/version-check still run.
   Each PR auto-merges once CI passes → tags `<addon>-v<ver>`.
3. **sync-dev runs** (`sync-dev.yml`) — fast-forwards `dev` to `main` after
   each release PR merge. Confirm dev is in sync:
   ```
   git fetch origin && git log --oneline origin/main..origin/dev
   ```
   Should be empty. If dev diverged (cherry-pick or force-reset scenario), sync
   it manually with a temporary force-push window (see Never section caveat).
4. **Pull locally** once dev and main are confirmed in sync:
   ```
   git switch dev && git pull --ff-only origin dev
   git switch main && git pull --ff-only origin main
   ```

Review the auto-generated release PR diff (CHANGELOG / config.yaml /
pyproject.toml) — don't edit it.

## Never
- Commit directly on `main`, or advance `main` without explicit per-promotion approval.
- Force-push `main` or `dev`.
