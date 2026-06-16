# Dev container: running Home Assistant

This repo opens in the official Home Assistant **add-on** devcontainer
(`ghcr.io/home-assistant/devcontainer:2-addons`, pinned in
[`devcontainer.json`](../../.devcontainer/devcontainer.json)). The workspace is
bind-mounted under `/mnt/supervisor/addons/local/ha-apps`.

Runtime on this Mac is **Docker Desktop** — Apple `container` and Podman are
both removed. See the `container-runtime-preference` memory.

## Normal flow (VS Code)

1. **Reopen in Container** — runs `postStartCommand` (`devcontainer_bootstrap`,
   regenerates machine-id and bind-mounts the workspace; does **not** start
   Docker or HA).
2. Run **Start Home Assistant** task — execs `supervisor_run`.
3. HA boots at <http://localhost:7123> (observer: <http://localhost:7357>).
   First boot pulls Supervisor + plugin images — several minutes.

## From the host CLI

Find the container name once and reuse it:

```bash
CNAME=$(docker ps -a --filter "ancestor=ghcr.io/home-assistant/devcontainer:2-addons" --format '{{.Names}}' | head -n1)
```

### Boot (up)

```bash
# 1. Start container if stopped
docker start "$CNAME"

# 2. Mount each app dir into apps/local BEFORE starting the Supervisor
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
  done
  ls "$APPS"
'

# 3. Start Supervisor (needs a TTY — use -dt, never -d)
docker exec -dt "$CNAME" bash -lc \
  'sudo mkdir -p /run/supervisor && sudo -E supervisor_run > /tmp/supervisor_run.log 2>&1'

# 4. Wait for HA
until curl -sf -o /dev/null http://localhost:7123; do echo -n "."; sleep 5; done && echo " up!"
```

### Restart (apps missing on already-running HA)

```bash
# Stop Supervisor and its containers, then re-mount and boot fresh
docker exec "$CNAME" bash -lc \
  'sudo pkill -x supervisor_run 2>/dev/null; docker rm -f hassio_supervisor 2>/dev/null; true'
# then run the Boot steps above from step 2
```

### Status / log

```bash
# Inner container status
docker exec "$CNAME" docker ps --format '{{.Names}}\t{{.Status}}'
# HA HTTP check
curl -s -o /dev/null -w "host :7123 -> HTTP %{http_code}\n" http://localhost:7123

# Supervisor log
docker exec "$CNAME" bash -lc 'tail -40 /tmp/supervisor_run.log'
```

## Why apps need bind-mounting

Supervisor renamed the local custom-app folder `addons/local` → `apps/local`
([supervisor PR #6837](https://github.com/home-assistant/supervisor/pull/6837),
merged 2026-05-13; live in the 2026.06 dev builds). The devcontainer still
mounts the workspace at `addons/local/ha-apps` and this is a monorepo (apps in
subdirs), so Supervisor scans an empty `apps/local` and the store shows no local
apps.

Mounting must happen **before** `supervisor_run` — the Supervisor's fresh
`-v /mnt/supervisor:/data` rbind captures them at boot time. Mounts made after
it starts do not propagate in. Apps appear as `local_<slug>` (e.g.
`local_supertonic`).

## Gotchas

1. **The container entrypoint only idles** — it does not start `dockerd` or the
   Supervisor. `supervisor_run` does. A plain `docker start` leaves nothing on
   7123/7357.
2. **Do not pre-start `dockerd`.** `supervisor_run` launches its own
   docker-in-docker. A second daemon fights over `/run/docker.sock` and the boot
   hangs at *"Waiting for Docker to initialize..."*. Fix: kill the stray daemon,
   remove `/run/docker.pid` + `/run/docker.sock`, re-run.
3. **`supervisor_run` needs a TTY.** Under `docker exec -d` its `stty sane` call
   fails and `set -e` aborts before the Supervisor starts. Always use `-dt`.

## Ports

| Host   | Container | Service     |
|--------|-----------|-------------|
| `7123` | `8123`    | HA frontend |
| `7357` | `4357`    | observer    |
