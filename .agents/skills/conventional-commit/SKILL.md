---
name: conventional-commit
description: "Writes and validates Conventional Commit messages for this monorepo so release-please routes each change to the right app CHANGELOG. Use whenever committing — it enforces `<type>(<scope>): subject` with an allowed scope and splits commits that span multiple apps."
---

# Conventional commit (release-please-aware)

release-please parses every commit on `main`; a wrong type/scope means the
change never reaches a CHANGELOG. The authoritative tables live in
`AGENTS.md` → **"Commits"**. Follow them.

## Steps
1. Inspect what changed: `git status --porcelain` / `git diff --cached --stat`.
2. **Map paths → scope** (exactly one per commit):
   - a single app dir → that app's slug
     (`livekit-wakeword`, `nemo-asr-cpp`, `nemotron-asr`,
     `supertonic`, `voiceprint`, `wardrowbe`, `zensical`)
   - `.github/`, root docs, `repository.yaml`, `.gitignore` → `repo`
3. **If the change spans multiple apps, split it** into one commit per scope
   (use `git commit --only <paths> -m ...` to stage-split without disturbing
   other staged work).
4. Pick the **type**: `feat` (minor), `fix`/`perf`/`revert` (patch),
   `docs`/`refactor`/`build`/`ci` (patch, in CHANGELOG), `chore`/`test`/`style`
   (no release). Breaking: `type!` or a `BREAKING CHANGE:` footer (major).
5. Compose `^(feat|fix|...)\(<scope>\): <imperative subject>` + optional body.
   End the message with the `Co-Authored-By:` trailer your harness specifies.
6. Validate before committing: scope is in the allowed set, exactly one scope,
   subject is imperative and ≤ ~72 chars.

## IMPORTANT
- Never `--no-verify` / `--no-gpg-sign`; if a hook fails, fix the root cause.
- An invalid/unlisted scope = release-please drops the change silently — reject it.
- On the default branch, branch first before committing.

## Output format
- The proposed commit message(s), one per scope, in a code block.
- If split, list which paths go in each commit.
