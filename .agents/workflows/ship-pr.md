---
name: ship-pr
description: Drives this monorepo's commit → push → PR → merge flow so release-please routes every change correctly. Use when committing and shipping a change as a pull request — it enforces branch-first, Conventional-Commit titles, and the right merge method so release PRs don't get dropped.
---

# Ship a change (commit → push → PR → merge)

This monorepo's release pipeline (release-please) parses commits on `main`. A
malformed commit/PR title, or the wrong merge method, silently drops a change
from its app CHANGELOG. This skill is the end-to-end flow; defer to
[[conventional-commit]] for message wording and to [[app-preflight]] for the
per-app sanity checks.

## 1. Branch
- **Never commit on `main`.** Branch first:
  `git switch -c <type>/<short-slug>` (e.g. `ci/fix-release-pr-title`,
  `fix/voiceprint-threshold`).
- One scope per branch where practical — it keeps the PR title valid (below).

## 2. Pre-PR checks
- Run the changed app's sanity checks via [[app-preflight]] (Python parse,
  yamllint, shellcheck; docker build / Wyoming `describe` on request).
- Root CI repeats the cross-cutting linters but does **not** replace per-app
  smoke tests.

## 3. Commit
- Use [[conventional-commit]]: `<type>(<scope>): <subject>`, exactly one
  allowed scope per commit, split commits that span multiple apps.
- Allowed scopes: `livekit-wakeword`, `nemotron-asr-c, `nemotron-asr-cp`,
  `nemotron-asr-c`, `supertonic`, `voiceprint`, `wardrowbe`, `zensical`, `repo`.
- **Never `--no-verify` / `--no-gpg-sign`.** If a hook fails, fix the cause.
- End the message with the `Co-Authored-By:` trailer your harness specifies.

## 4. Push & open PR
- `git push -u origin <branch>`.
- `gh pr create` — **the PR title MUST itself be a valid Conventional Commit**
  (`<type>(<scope>): <subject>`). On squash merge the title *becomes* the
  commit on `main`, so a bad title means release-please never sees the change.
- The `addon:<slug>` label auto-applies by changed path (`.github/labeler.yml`);
  don't set it by hand. PRs are restricted to collaborators.

## 5. Merge — pick the method deliberately
- **Single-scope PR → squash merge is fine** (the title is the one commit).
- **Multi-scope PR → do NOT squash.** Squashing collapses every scope into one
  commit and release-please only routes the title's scope; the rest are
  dropped. Use **rebase merge** so each Conventional commit lands intact, or
  split the work into one PR per scope. (See [[release-please-squash-gotcha]];
  recover a dropped release with revert + cherry-pick.)
- After merge, GitHub auto-deletes the head branch
  (`deleteBranchOnMerge: true`). For release-please's own
  `release-please--branches--main--components--<addon>` branch this is safe —
  it recreates it next cycle; never delete it by hand while its PR is open.

## 6. After merge
- `git switch main && git pull --ff-only origin main`.
- Delete the local branch: `git branch -d <branch>` (squash merges trigger a
  "not merged to HEAD" warning — expected, the change is in `main` as the
  squash commit). The remote branch is already gone via auto-delete.
- Merging a `feat`/`fix`/etc. PR makes release-please open (or update) a
  `chore(<addon>): release <ver>` PR. When you later **merge that release PR**,
  it lands the version bump + CHANGELOG on `main` and tags `<addon>-v<ver>` —
  so `git switch main && git pull --ff-only origin main` again afterward to
  keep local in sync (and pick up the manifest/`config.yaml` bumps).

## IMPORTANT
- The diff of a `chore(<addon>): release <ver>` PR is auto-generated
  (`config.yaml` / `CHANGELOG.md` / `pyproject.toml`) — review, don't edit.
- Image build/publish to GHCR is not yet automated in monorepo mode; run it
  manually after a release until that workflow exists.
