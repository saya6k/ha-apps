---
name: ai-harness-structure
description: .agents/ is canonical AI SoT; directory layout and symlink map after 2026-06-16 restructure
metadata: 
  node_type: memory
  type: project
  originSessionId: e7824dcf-4a1b-4bd9-8b54-db4a12f3dd7f
---

`.agents/` is the canonical AI harness directory. Subdirectories:

- `skills/` — per-app GitHub Copilot instruction files (`*.instructions.md`). `.github/instructions` symlinks here.
- `workflows/` — Claude Code slash commands (app-preflight, ship-pr, etc.). `.claude/commands` symlinks here.
- `agents/` — Claude Code agent definitions. `.claude/agents` symlinks here.
- `memory/` — project context notes (gitignored, not tracked in git).
- `settings.json` — shared Claude Code project settings (tracked).
- `settings.local.json` — local overrides (gitignored).

**Repo-level instructions SoT: `AGENTS.md` at the repo root** (real file, not a symlink). `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` all symlink to `AGENTS.md`. The `manifests/` subdirectory was removed 2026-06-16.

`.claude/` is a real directory (not a full symlink) with individual symlinks:
- `.claude/commands` → `../.agents/workflows`
- `.claude/agents` → `../.agents/agents`
- `.claude/settings.json` → `../.agents/settings.json`
- `.claude/settings.local.json` → `../.agents/settings.local.json` (gitignored)

`.gemini/` is still a full symlink → `.agents/`.

**Session memory sync:** `.claude/projects/<hash>/memory/` is the Claude Code
session-scoped memory directory (harness reads/writes here). Individual files
should symlink to `.agents/memory/` so `.agents/memory/` remains the SoT.
Example: `nemotron-asr-c-addon.md` was migrated 2026-06-17.

**Why:** `AGENTS.md` is the universal convention across AI tools; `.agents/manifests/repo.md` was an unnecessary extra layer.

**How to apply:** when editing repo-level AI instructions, edit `AGENTS.md` at the repo root. When adding Claude Code commands, add under `.agents/workflows/`.
