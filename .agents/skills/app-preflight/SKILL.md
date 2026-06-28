---
name: app-preflight
description: Runs an app's pre-PR sanity checks. Context-aware — lighter for ha-apps metadata-only dirs, full source checks for ha-app-* repos. Use before committing or opening a PR.
---

# App preflight checks

## Which repo am I in?

- **ha-apps** (`/Users/saya6k/Projects/ha-apps`): catalog repo, metadata-only for most apps.
  Source lives in ha-app-* repos. Checks are lighter here.
- **ha-app-\*** (`/Users/saya6k/Projects/ha-app-<slug>`): source repo.
  Full checks apply.

---

## ha-apps preflight (metadata changes)

1. Determine changed app dirs: `git status --porcelain | grep -oE '^.. [a-z-]+/' | sort -u`
2. For each changed app dir:
   - **YAML:** `yamllint <slug>/config.yaml <slug>/translations/*.yaml`
   - **Markdown:** `markdownlint-cli2 '<slug>/DOCS.md' '<slug>/README.md' '<slug>/CHANGELOG.md'`
   - Confirm `image: ghcr.io/saya6k/app-<slug>` line is present in `config.yaml`
     (metadata-only apps must have it).
3. **Repo-wide invariants:**
   - LF line endings only (no CRLF)
   - `config.yaml` exists only at the subproject root (not nested)
   - `packages: {}` in `.github/release-please-config.json` (no per-app entries)

---

## ha-app-* preflight (source changes)

Each repo's `<slug>/AGENTS.md` has a **"Sanity checks before PR"** section —
that is authoritative. This is the common baseline:

1. **Python** (if it has a `wyoming_*` dir):
   `python3 -c "import ast,glob;[ast.parse(open(f).read()) for f in glob.glob('<pkg>/*.py')]"`
2. **YAML:** `yamllint <slug>/config.yaml <slug>/translations/*.yaml`
3. **Shell / s6:** `shellcheck -x <slug>/rootfs/etc/s6-overlay/s6-rc.d/*/run` (and `finish`)
4. **Schema drift** where the app mirrors a `list(...)` schema in a `const`: confirm they match.
5. Only when asked (slow): `docker build .` from the `<slug>/` dir.
6. Only when a service is running locally: Wyoming smoke —
   `echo '{"type":"describe"}' | nc -w 1 localhost <port> | grep -qi <slug>`
   (port + grep term in the app's `AGENTS.md`).
7. **Repo-wide invariants:** LF line endings, no `image:` line in `<slug>/config.yaml`
   (image lives in ha-apps; ha-app-* config.yaml should have `version: dev` or current ver).

---

## Devcontainer runtime check

Only when HA devcontainer is up. Detect:
```bash
CNAME=$(docker ps --filter "ancestor=ghcr.io/home-assistant/devcontainer:2-addons" \
  --format '{{.Names}}' | head -n1)
```
If `$CNAME` is empty → `SKIPPED (devcontainer not running)`.

**Note:** apps in ha-app-* repos publish to GHCR; HA Supervisor pulls the image via
`image:` in ha-apps config.yaml. Local source testing requires either a local docker build
or pointing config.yaml at a locally-built image tag.

---

## IMPORTANT
- Report pass/fail per check with actual output; never claim passed if skipped.
- Do not fix unrelated findings here — just run and report.

## Output format
- One line per check: `OK` / `FAIL` (+ first error) / `SKIPPED` (+ why).
- End with an overall verdict: ready / not ready for PR.
