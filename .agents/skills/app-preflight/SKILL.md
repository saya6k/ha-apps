---
name: app-preflight
description: Runs an app's pre-PR sanity checks in this Home Assistant app monorepo — Python parse, yamllint, shellcheck, and (on request) docker build + a Wyoming `describe` smoke. Use before committing or opening a PR for any app under a subproject directory.
---

# App preflight checks

Run the checks an app must pass before a PR. Each subproject's `AGENTS.md` has a
**"Sanity checks before PR"** section — that is authoritative; this skill runs
the common baseline and defers to it for per-app extras.

## Steps
1. Decide which app(s) to check: the argument, else the subproject dirs with
   changes (`git status --porcelain | grep -oE '^.. [a-z-]+/' | sort -u`).
2. `cd` into the app and **read its `AGENTS.md` "Sanity checks before PR"** — run
   exactly those. The baseline every app shares:
   - **Python** (if it has a `wyoming_*`/package dir):
     `python3 -c "import ast,glob;[ast.parse(open(f).read()) for f in glob.glob('<pkg>/*.py')]"`
   - **YAML:** `yamllint config.yaml translations/*.yaml`
   - **Shell / s6:** `shellcheck -x rootfs/etc/s6-overlay/s6-rc.d/*/run` (and any `finish`)
   - **Schema drift** where the app mirrors a `list(...)` schema in a `const`
     (e.g. nemo's `SCHEMA_MODELS`): confirm they match.
3. Only when asked (slow): `docker build .` from the app dir.
4. Only when a service is running locally: Wyoming smoke —
   `echo '{"type":"describe"}' | nc -w 1 localhost <port> | grep -qi <slug>`
   (port + grep term are in the app's `AGENTS.md`).
5. Repo-wide invariants to spot-check: LF line endings (no CRLF), no
   `version.txt`, `config.yaml` only at the subproject root.
6. **Devcontainer runtime check** (only when HA devcontainer is up):
   Detect the running devcontainer:
   ```bash
   CNAME=$(docker ps --filter "ancestor=ghcr.io/home-assistant/devcontainer:2-addons" --format '{{.Names}}' | head -n1)
   ```
   If `$CNAME` is empty, skip and report `SKIPPED (devcontainer not running)`.

   **If HA is not yet booted** (HA not responding at `http://localhost:7123`), boot it:
   ```bash
   # 1. Bind-mount each app dir into apps/local before starting Supervisor
   docker exec "$CNAME" bash -lc '
     REPO=/mnt/supervisor/addons/local/ha-apps
     APPS=/mnt/supervisor/apps/local
     sudo mkdir -p "$APPS"
     for d in "$REPO"/*/; do
       app=$(basename "$d")
       [ -f "${d}config.yaml" ] || continue
       mountpoint -q "$APPS/$app" && continue
       sudo mkdir -p "$APPS/$app"
       sudo mount --bind "$d" "$APPS/$app"
     done'
   # 2. Start Supervisor (must use -dt — supervisor_run needs a TTY)
   docker exec -dt "$CNAME" bash -lc \
     'sudo mkdir -p /run/supervisor && sudo -E supervisor_run > /tmp/supervisor_run.log 2>&1'
   # 3. Wait for HA
   until curl -sf -o /dev/null http://localhost:7123; do echo -n "."; sleep 5; done
   ```
   Gotcha: **never pre-start dockerd** inside the container — supervisor_run
   launches its own docker-in-docker; a second daemon fights over the socket.

   **Once HA is up**, verify the add-on under test:
   - HA health: `curl -sf http://localhost:7123` → HTTP 200 `OK`
   - Add-on container running:
     `docker exec "$CNAME" docker ps --format '{{.Names}}' | grep -q <slug>` → found `OK`
   - App-specific health check from the app's `AGENTS.md` (e.g. otelcol:
     `docker exec "$CNAME" docker exec <container> curl -sf http://localhost:13133/`)
   - Supervisor log for errors:
     `docker exec "$CNAME" tail -20 /tmp/supervisor_run.log`

## IMPORTANT
- Report pass/fail per check with the actual output; do not claim a check passed
  if it was skipped (e.g. docker build, smoke).
- Do not "fix" unrelated findings here — just run and report. Fixes are a
  separate step.

## Output format
- One line per check: `OK` / `FAIL` (+ first error) / `SKIPPED` (+ why).
- End with an overall verdict: ready / not ready for PR.
