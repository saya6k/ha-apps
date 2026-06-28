---
name: app-promote-to-main
description: Promote the `dev` branch to `main` and verify the automated release pipeline. REQUIRES explicit user approval every time. Use after [[app-dev-pr]] when dev is stable and smoke-tested.
---

# Promote `dev → main`

> **STOP. Never advance `main` without the user's explicit approval for that
> specific promotion.** Ask every time, naming what will be promoted.

## 1. Show what's being promoted
```
git fetch origin && git log --oneline origin/main..origin/dev
```
If empty, dev and main are already in sync — nothing to promote.

## 2. Pre-conditions (verify before asking)
- `dev` CI green
- App smoke-tested on a real HA pipeline (not just unit tests)

## 3. Open promotion PR — on user approval
```
gh pr create --base main --head dev \
  --title "chore(repo): promote dev to main" \
  --body "Promotion. CI must pass before merge."
gh pr merge <number> --merge --auto
```
**PR title must be `chore(repo): promote dev to main`** — never use a
`feat`/`fix`/`perf` type here. release-please reads PR titles via the GitHub
API in addition to git commit messages. If the promotion PR title is a
conventional `feat(...)`, release-please counts it alongside the original
squash commit on dev, producing duplicate CHANGELOG entries.
`chore` is not included in the CHANGELOG and does not trigger a release, so
only the actual feature/fix commits in the merge parent chain are counted.

**Must use `--merge` (merge commit), not `--squash` or `--rebase`.**
- `--squash`: collapses everything into the PR title — release-please ignores
  individual commits. See [[release-please-squash-gotcha]].
- `--rebase`: new SHAs for each commit → dev's originals are no longer
  ancestors of main → sync-dev FF fails every time.
- `--merge`: merge commit on main with dev as parent → dev's commits stay as
  ancestors → sync-dev FF works cleanly → release-please reads all commits
  through the merge commit parent chain.

## 4. Verify after merge

Wait for and confirm this sequence in order:

**a. CI passes on `main`**
```
gh run list --repo saya6k/ha-apps --workflow CI --branch main --limit 1 \
  --json status,conclusion
```

**b. release-please opens stable release PRs** (`release.yml` fires via
`workflow_run` after CI succeeds on `main`). `automerge-release` sets squash
auto-merge immediately. CI skips build-image on these PRs; lint/version-check
still run. Each PR auto-merges → tags `<addon>-v<ver>`.

**c. sync-dev fast-forwards `dev` to `main`** (`sync-dev.yml` runs on every
`main` push). Confirm dev is in sync:
```
git fetch origin && git log --oneline origin/main..origin/dev
```
Should be empty. If not empty (diverged SHA scenario from a prior rebase),
contact the AI agent to force-sync.

**d. Pull locally** once dev and main are confirmed in sync:
```
git switch dev && git pull --ff-only origin dev
git switch main && git pull --ff-only origin main
```

## Never
- Advance `main` without explicit per-promotion approval.
- Force-push `main` or `dev` (except the controlled force-sync procedure
  when SHA divergence occurs after a rebase mishap).
