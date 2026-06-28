---
name: new-app-scaffold
description: Scaffold a new app — create the ha-app-<slug> source repo and add metadata-only entry to ha-apps. Use when adding a new app. Ask for slug and stage first.
---

# Scaffold a new app

Two things happen in parallel: create the **ha-app-`<slug>`** source repo and
add a **metadata-only entry** to ha-apps.

Ask for:
- `<slug>` — bare name, no `ha-` prefix (e.g. `otelcol`, `supertonic`)
- `stage` — `experimental` | `stable`

---

## Part A — ha-app-`<slug>` source repo

### 1. Create GitHub repo
```
gh repo create saya6k/ha-app-<slug> --public --description "<one-line desc>"
```

### 2. Scaffold locally (use ha-app-wardrowbe as template)

Copy from an existing ha-app-* repo (wardrowbe is the reference):
```
rsync -a \
  --exclude='.agents/' --exclude='wardrowbe/' \
  ~/Projects/ha-app-wardrowbe/ ~/Projects/ha-app-<slug>/
```

Then create `<slug>/` subdir with:
- `config.yaml` — slug, name, stage, `arch: [amd64, aarch64]`, options/schema.
  **No `image:` line** here — that lives in ha-apps.
- `Dockerfile` — `ARG BUILD_FROM`, labels, `COPY rootfs /`. s6 `chmod +x` block:
  ```dockerfile
  RUN find /etc/s6-overlay/s6-rc.d -name 'run' -o -name 'finish' | xargs chmod +x
  ```
- `rootfs/etc/s6-overlay/s6-rc.d/<slug>/` — `run`, `finish` (use s6 finish template
  from ha-apps old `new-app-scaffold`), `type`
- `translations/{en,ko}.yaml`
- `AGENTS.md`, `DOCS.md`, `README.md` (see README template below)
- `icon.png` (256×256) + `logo.png`

### 3. CI / release workflows

`.github/workflows/` from the template already has:
- `ci.yml` — lint + build-test (update slug references)
- `build.yml` — GHCR publish on release + `repository_dispatch` to ha-apps
- `release-drafter.yml` + `.github/release-drafter.yml` — with autolabeler

Substitute `wardrowbe` → `<slug>` in `ci.yml` and `build.yml`.

### 4. .agents/ + .claude/ structure

```
mkdir -p .agents/{workflows,skills/app-preflight} .claude
cp ~/Projects/ha-app-wardrowbe/.agents/workflows/app-dev-pr.md .agents/workflows/
cp ~/Projects/ha-app-wardrowbe/.agents/skills/app-preflight/SKILL.md .agents/skills/app-preflight/
ln -s ../.agents/workflows .claude/commands
ln -s ../.agents/skills .claude/skills
```

### 5. Set CATALOG_PAT secret
```
gh secret set CATALOG_PAT --repo saya6k/ha-app-<slug> --body "$(gh auth token)"
```

### 6. Enable workflow write permissions
```
gh api -X PUT repos/saya6k/ha-app-<slug>/actions/permissions/workflow \
  -f default_workflow_permissions=write \
  -F can_approve_pull_request_reviews=true
```

### 7. Initial commit + push
```
cd ~/Projects/ha-app-<slug>
git init -b main && git add . && git commit -m "chore: initial repo setup"
git remote add origin https://github.com/saya6k/ha-app-<slug>.git
git push -u origin main
```

### 8. Create base release
```
gh release create v<ver> --repo saya6k/ha-app-<slug> \
  --title "v<ver>" --notes "Initial release." --latest
```
This gives release-drafter a base to compute the next version from.

---

## Part B — ha-apps metadata entry

### 1. Add `<slug>/` to ha-apps

Files to create in ha-apps (metadata-only — no Dockerfile, no source):
- `<slug>/config.yaml` — same as ha-app-* but WITH `image: ghcr.io/saya6k/app-<slug>`
  and the current version
- `<slug>/CHANGELOG.md` — minimal stub
- `<slug>/DOCS.md`, `<slug>/README.md`
- `<slug>/icon.png`, `<slug>/logo.png`
- `<slug>/translations/{en,ko}.yaml`
- `<slug>/apparmor.txt` (if needed)

### 2. Register in ha-apps root

- `.github/labels.yml` — add `addon:<slug>` label
- `.github/labeler.yml` — add path rule for `<slug>/`
- `.github/ISSUE_TEMPLATE/{bug,feature}.yml` — add slug to dropdowns
- `AGENTS.md` — add row to the Apps table
- `.github/workflows/sync-app-version.yml` — no changes needed (dispatch-driven,
  slug comes from payload)

**No release-please registration** — `packages: {}` stays empty. Versioning is
driven entirely by ha-app-* dispatch.

### 3. Open PR to dev
```
git switch -c feat/<slug>-initial origin/dev
git add <slug>/ .github/
git commit -m "feat(<slug>): add <Name> app"
gh pr create --base dev --title "feat(<slug>): add <Name> app"
```

---

## s6 finish template

```bash
#!/command/with-contenv bashio
# shellcheck shell=bash
readonly exit_code_container=$(</run/s6-linux-init-container-results/exitcode)
readonly exit_code_service="${1}"
readonly exit_code_signal="${2}"
bashio::log.info "Service exited with code ${exit_code_service} (by signal ${exit_code_signal})"
if [[ "${exit_code_signal}" -ne 0 ]]; then
  [[ "${exit_code_container}" -eq 0 ]] && echo $((128 + exit_code_signal)) > /run/s6-linux-init-container-results/exitcode
  exec /run/s6/basedir/bin/halt
elif [[ "${exit_code_service}" -eq 0 ]]; then
  exec /run/s6/basedir/bin/halt
else
  bashio::log.error "<slug>: permanent failure (exit ${exit_code_service}) — fix config and restart."
  [[ "${exit_code_container}" -eq 0 ]] && echo "${exit_code_service}" > /run/s6-linux-init-container-results/exitcode
  exit "${exit_code_service}"
fi
```

## README template

```markdown
# Home Assistant App: <Name>

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/saya6k)

[![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=03f32180_<slug>&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps)

One-paragraph description.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
```

## Output format
- Checklist: files created (ha-app-* and ha-apps), registrations touched.
- Flag anything left for the user (Dockerfile content, model hosting, icon design).
