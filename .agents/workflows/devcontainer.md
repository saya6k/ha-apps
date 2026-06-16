# Dev container: running Home Assistant

This repo opens in the official Home Assistant **add-on** devcontainer
(`ghcr.io/home-assistant/devcontainer:2-addons`, pinned in
[`devcontainer.json`](./devcontainer.json)). It mirrors
`alexbelgium/hassio-addons`: the workspace is bind-mounted under
`/mnt/supervisor/addons/local/ha-apps`, so this repo's apps appear in HA's
store under **local**.

Runtime on this Mac is **Docker Desktop** (see the `container-runtime-preference`
memory). Apple's `container` / container-machine is **not** usable here: VS Code
Dev Containers has no Apple-container backend, and the HA Supervisor needs
`--privileged` nested docker-in-docker, which Apple container's VM-per-container
model doesn't support. Podman was also removed. Stick with Docker Desktop.

## Normal flow (VS Code)

1. **Reopen in Container.** This runs the `postStartCommand`
   (`devcontainer_bootstrap` — regenerates machine-id and bind-mounts the
   workspace; it does **not** start docker or HA).
2. Run the **Start Home Assistant** task (it execs `supervisor_run`).
3. HA boots at <http://localhost:7123> (observer on <http://localhost:7357>).
   First boot pulls the Supervisor + plugin images — several minutes.

## From the host CLI

If the container was started outside VS Code (e.g. `docker start`), the
devcontainer lifecycle is skipped and HA never boots. Use the helper:

```bash
.agents/workflows/devcontainer-ha.sh up         # mount apps + boot HA, wait for :7123
.agents/workflows/devcontainer-ha.sh restart    # stop + remount + reboot (apps not showing)
.agents/workflows/devcontainer-ha.sh mount-apps # (re)bind apps into apps/local only
.agents/workflows/devcontainer-ha.sh status     # inner containers + HA HTTP status
.agents/workflows/devcontainer-ha.sh log        # tail supervisor_run.log
```

## Why the local apps need bind-mounting

Supervisor renamed the local custom-app folder `addons/local` → `apps/local`
([supervisor PR #6837](https://github.com/home-assistant/supervisor/pull/6837),
merged 2026-05-13; live in the 2026.06 dev builds the `:2-addons` image pulls).
The devcontainer still mounts the workspace at `addons/local/ha-apps`, and this
is a **monorepo** (apps in subdirs), so Supervisor scans an empty `apps/local`
and the store shows no local apps.

The helper's `mount_apps` bind-mounts each app dir (anything with a
`config.yaml`) into `/mnt/supervisor/apps/local/<app>` **before** `supervisor_run`,
so the Supervisor's fresh `-v /mnt/supervisor:/data` rbind captures them. Mounts
created *after* the Supervisor starts do not propagate into it — hence
`restart` (stop → remount → boot) if apps are missing on an already-running HA.
After boot the apps appear under the **local** repository as `local_<slug>`
(e.g. `local_supertonic`).

## Gotchas (why a naive boot hangs or dies)

These are baked into the helper; know them if you boot HA by hand:

1. **The container entrypoint only idles.** It does not start `dockerd` or the
   Supervisor — `supervisor_run` does. A plain `docker start` leaves nothing
   listening on 7123/7357.
2. **Do not pre-start `dockerd`.** `supervisor_run`'s `start_docker` launches
   its own docker-in-docker. If you start a second `dockerd` by hand, the two
   fight over `/run/docker.sock` and the boot hangs forever at
   *"Waiting for Docker to initialize..."*. Fix: kill the stray daemon, remove
   `/run/docker.pid` + `/run/docker.sock`, re-run.
3. **`supervisor_run` needs a TTY.** Under `docker exec -d` (no tty) its
   `stty sane` call fails and `set -e` aborts the script before the Supervisor
   ever starts — you get dbus/udev output then silence. Run it with a tty
   (`docker exec -dt`). The helper does this.

## Ports

| Host          | Container | Service     |
| ------------- | --------- | ----------- |
| `7123`        | `8123`    | HA frontend |
| `7357`        | `4357`    | observer    |
