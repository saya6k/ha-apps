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
   - `Dockerfile` (+ `build.yaml` if needed). s6 silently ignores non-executable
     scripts — add a wildcard `chmod +x` block:
     `RUN shopt -s nullglob && chmod +x /etc/s6-overlay/s6-rc.d/*/{run,up,finish,down}`
   - `rootfs/etc/s6-overlay/s6-rc.d/<slug>/{run,finish,type}` (+ `discovery` oneshot
     for Wyoming). LF line endings only.
     - `run` — exec the service (see [[conventional-commit]] for go template).
     - **`finish` — MUST use the 3-way template below.** The common copy-paste
       `halt`-on-any-error pattern causes a restart loop on bootstrap failure
       (model download, dependency, etc.). Distinguish transient exits (signal /
       exit 0 → halt) from permanent failure (exit >0 → stay down).
   - `translations/{en,ko}.yaml` for the option UI strings.
   - `AGENTS.md` (deep invariants/build/don'ts), `DOCS.md` (user knobs),
     `CHANGELOG.md`, `README.md` (see **README template** below). Symlink `CLAUDE.md -> AGENTS.md`.
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

## s6 finish template

Every app's `rootfs/etc/s6-overlay/s6-rc.d/<slug>/finish` must use this pattern.
The common copy-paste from s6-overlay docs halts on **any** non-zero exit, which
causes a restart loop when a startup dependency (model download, C library, etc.)
fails permanently. This template distinguishes transient from permanent:

```bash
#!/command/with-contenv bashio
# shellcheck shell=bash
# ==============================================================================
# Service finish handler.
#
# s6-supervise restarts the service ONLY when finish exits 0.  Bootstrap /
# non-transient failures exit non-zero -> service stays down (no restart loop).
# A manual add-on stop sends SIGTERM -> the run script exits cleanly (0) or is
# killed by signal (256).  Both are transient -> halt the container.
# ==============================================================================
# shellcheck disable=SC2155
readonly exit_code_container=$(</run/s6-linux-init-container-results/exitcode)
readonly exit_code_service="${1}"
readonly exit_code_signal="${2}"

bashio::log.info \
  "Service exited with code ${exit_code_service}" \
  "(by signal ${exit_code_signal})"

if [[ "${exit_code_signal}" -ne 0 ]]; then
  # Killed by signal — transient (manual stop / resource limit).  Halt.
  if [[ "${exit_code_container}" -eq 0 ]]; then
    echo $((128 + exit_code_signal)) > /run/s6-linux-init-container-results/exitcode
  fi
  exec /run/s6/basedir/bin/halt
elif [[ "${exit_code_service}" -eq 0 ]]; then
  # Clean exit — transient (graceful shutdown).  Halt.
  exec /run/s6/basedir/bin/halt
else
  # Non-zero exit — permanent failure (bootstrap, model download, conversion,
  # etc.).  Exit non-zero so s6-supervise does NOT restart.  Container stays up
  # so the user can read logs via the HA UI and fix the configuration.
  bashio::log.error \
    "<slug>: permanent failure (exit ${exit_code_service}) —" \
    "service will not be restarted. Fix the configuration and restart the add-on."
  if [[ "${exit_code_container}" -eq 0 ]]; then
    echo "${exit_code_service}" > /run/s6-linux-init-container-results/exitcode
  fi
  exit "${exit_code_service}"
fi
```

Replace `<slug>` with the app directory name.

## README template

Every app's `README.md` must use this badge order. **Arch badges first, then
for-the-badge badges (Claude Code + Coffee + tech stack), then Show add-on at the
very bottom of the shield block, then the one-paragraph description.**

```markdown
# Home Assistant App: <Name>

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/saya6k)
[![<Tech>](https://img.shields.io/badge/<Tech>-<color>?style=for-the-badge&logo=<logo>&logoColor=white)](<tech-url>)

[![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=03f32180_<slug>&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps)

One-paragraph description. Details go in `DOCS.md`.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
```

Add or remove tech-stack badges as appropriate. Show add-on is always last among
the shields, immediately before the description.

## Output format
- A checklist of files created and each registration touched, with anything
  left for the user (e.g. real Dockerfile contents, model hosting).
