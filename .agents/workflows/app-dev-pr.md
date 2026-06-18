---
name: app-dev-pr
description: Drives this monorepo's dev-first flow — app changes land on `dev` via Conventional-Commit PRs, release-please cuts release PRs on `dev`, and the `dev → main` promotion is gated on the user's explicit per-promotion approval. Use when shipping any app change. Defer to [[ship-pr]] for the mechanical commit/PR steps and [[conventional-commit]] for message wording.
---

# App dev flow (dev-first, `main` gated)

`main` is the **released / stable** branch — frozen at the last release and moved
forward **only** by an explicit, user-approved `dev → main` promotion. All active
work integrates on `dev` first. release-please watches `dev` and opens its
`chore(<addon>): release <ver>` PRs against `dev` (`.github/workflows/release.yml`,
`target-branch: dev`).

> Mechanics (branch-first, Conventional-Commit titles, merge method) are in
> [[ship-pr]]; this workflow only changes the **base branch to `dev`** and adds
> the `main` promotion gate. Per-app checks: [[app-preflight]].

## 1. Branch off `dev`
- `git fetch origin && git switch -c <type>/<short-slug> origin/dev`.
- **Never commit on `dev` or `main` directly.**

## 2. Pre-PR checks
- Run [[app-preflight]] for the changed app (Python parse, yamllint, shellcheck;
  docker build / Wyoming `describe` on request).

## 3. Commit & open the PR against `dev`
- Commit per [[conventional-commit]] — exactly one scope per commit.
- `git push -u origin <branch>`.
- `gh pr create --base dev ...` — **base MUST be `dev`.** GitHub still defaults
  the base to `main` (the repo default branch), so pass `--base dev` explicitly
  or the New-PR button targets the frozen branch. The PR title must itself be a
  valid Conventional Commit.

## 4. Merge into `dev`
- Single-scope PR → squash is fine; multi-scope → rebase (see [[ship-pr]] §5,
  [[release-please-squash-gotcha]]).
- Merging a `feat`/`fix`/etc. onto `dev` makes release-please open/update a
  `chore(<addon>): release <ver>` PR **against `dev`**. Merge that release PR to
  land the version bump + CHANGELOG on `dev` and tag `<addon>-v<ver>` (the tag
  fires `build.yml`).

## 5. Promote `dev → main` — REQUIRES explicit user approval
- **STOP. Never merge `dev` into `main` without the user's explicit approval for
  that specific promotion.** Approval of dev-side work does NOT imply approval to
  promote; ask every time.
- Pre-conditions before you even ask:
  - `dev` CI is green.
  - The app was smoke-tested on a real HA pipeline (not just unit tests).
  - Any open `chore(<addon>): release <ver>` PR on `dev` is already merged, so
    `dev` carries a coherent released state.
- Ask the user to confirm, naming exactly what is promoted — the commits and
  releases on `dev` not yet on `main` (`git log --oneline origin/main..origin/dev`).
- On approval, promote by **fast-forward only** so release-please's commit SHAs
  and `<addon>-v<ver>` tags stay attached:
  ```
  git fetch origin
  git switch main
  git merge --ff-only origin/dev
  git push origin main
  ```
  `--ff-only` fails loudly if `main` has diverged — resolve that explicitly, do
  not paper over it. Do **not** promote via a squash/rebase PR (it rewrites SHAs
  and detaches the release tags).
- After promotion `main == dev`; continue new work from `dev` (step 1).

## Never
- Open an app PR against `main`, or commit directly to `dev`/`main`.
- Merge / fast-forward `dev → main` without explicit per-promotion user approval.
- **Force-push `main`.** (The one-time backward reset that established this flow
  was a deliberate setup step, not the steady state.)
