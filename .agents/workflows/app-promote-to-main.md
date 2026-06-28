---
name: app-promote-to-main
description: Promote the `dev` branch to `main` in ha-apps and verify the sync pipeline. REQUIRES explicit user approval every time. Use after [[app-dev-pr]] when dev is stable.
---

# Promote `dev → main` (ha-apps)

> **STOP. Never advance `main` without the user's explicit approval for that
> specific promotion.** Ask every time, naming what will be promoted.

## 1. Show what's being promoted
```
git fetch origin && git log --oneline origin/main..origin/dev
```
If empty, dev and main are already in sync — nothing to promote.

## 2. Pre-conditions (verify before asking)
- `dev` CI green
- Any app changes smoke-tested on a real HA pipeline

## 3. Open promotion PR — on user approval
```
gh pr create --base main --head dev \
  --title "chore(repo): promote dev to main" \
  --body "Promotion. CI must pass before merge."
gh pr merge <number> --merge --auto
```
**PR title must be `chore(repo): promote dev to main`** — never `feat`/`fix`/`perf`.
`chore` is not included in the CHANGELOG and does not trigger any release, so
it doesn't interfere with ha-app-* sync PRs that land on dev.

**Must use `--merge` (merge commit), not `--squash` or `--rebase`.**
- `--squash`: collapses everything into the PR title, losing individual commit
  metadata. See [[release-please-squash-gotcha]].
- `--rebase`: new SHAs → dev's originals are no longer ancestors of main →
  sync-dev FF fails every time.
- `--merge`: merge commit on main with dev as parent → sync-dev FF works cleanly.

## 4. Verify after merge

**a. CI passes on `main`**
```
gh run list --repo saya6k/ha-apps --workflow CI --branch main --limit 1 \
  --json status,conclusion
```

**b. sync-dev fast-forwards `dev` to `main`** (`sync-dev.yml` runs on every
`main` push). Confirm dev is in sync:
```
git fetch origin && git log --oneline origin/main..origin/dev
```
Should be empty. If diverged, force-sync dev: `git push origin origin/main:refs/heads/dev --force`.

**c. Pull locally** once in sync:
```
git switch dev && git pull --ff-only origin dev
git switch main && git pull --ff-only origin main
```

> **Note:** ha-apps no longer runs release-please on promotion — `packages: {}`.
> Versioning and CHANGELOG updates for each app arrive automatically via
> `sync-app-version.yml` when ha-app-* releases are published (opens a
> `chore(<slug>): release <ver>` PR to dev).

## Never
- Advance `main` without explicit per-promotion approval.
- Force-push `main` or `dev` (except the controlled force-sync above when
  SHA divergence occurs).
