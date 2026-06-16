---
name: new-app-scaffold
description: Scaffolds a new Home Assistant app in this monorepo and registers it across the root .github config and conventions. Use when adding a new app subproject.
---

# Scaffold a new app

Create a new app subproject plus every place its slug must be registered. The
authoritative conventions are in `.github/copilot-instructions.md`; follow them.
Ask for the slug (bare, no `ha-` prefix) and stage (`experimental` | `stable`)
first.

## Steps
1. **Subproject files** in `<slug>/`:
   - `config.yaml` (slug, name, `stage`, `arch: [amd64, aarch64]`, options +
     schema, ports; `discovery: [wyoming]` for Wyoming services). `config.yaml`
     lives only at the subproject root.
   - `Dockerfile` (+ `build.yaml` if needed). The s6 scripts get a `chmod +x`
     block in the `Dockerfile` — s6 silently ignores non-executable scripts.
   - `rootfs/etc/s6-overlay/s6-rc.d/<slug>/{run,type}` (+ `discovery` oneshot for
     Wyoming). LF line endings only.
   - `translations/{en,ko}.yaml` for the option UI strings.
   - `AGENTS.md` (deep invariants/build/don'ts), `DOCS.md` (user knobs),
     `CHANGELOG.md`, `README.md`. Symlink `CLAUDE.md -> AGENTS.md`.
   - `icon.png` (256², square) + `logo.png` — see the `app-icon` skill.
2. **Register the slug at the repo root** (`repo` scope):
   - `.github/release-please-config.json` + `.github/.release-please-manifest.json`
     (start `0.1.0`; `simple` releaser, no `version.txt`).
   - `.github/labels.yml` + `.github/labeler.yml` (`addon:<slug>` label by path).
   - `.github/ISSUE_TEMPLATE/{bug,feature}.yml` dropdowns.
   - The allowed-scopes list in `.github/copilot-instructions.md` **and**
     `CONTRIBUTING.md` (keep them in lockstep).
3. **Stage gating** (root `.gitignore`):
   - `experimental` → add a `/<slug>/` line (local-only, not tracked).
   - `stable` → no gitignore line; `git add` the subproject. Before stable, host
     any large model as a pinned release asset, not vendored in git.
4. Optionally set up the agent dir: `.agents/` + `.claude -> .agents`.
5. Run the `app-preflight` skill on the new app.

## IMPORTANT
- Keep the `ha-` prefix in GitHub project name / brand / URLs / Wyoming Info,
  but NOT in the directory slug.
- An unregistered slug = release-please can't route its commits. Don't skip
  step 2.

## Output format
- A checklist of files created and each registration touched, with anything
  left for the user (e.g. real Dockerfile contents, model hosting).
