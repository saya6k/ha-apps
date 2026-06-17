---
name: devcontainer-ha-boot
description: How to boot HA in the ha-apps add-on devcontainer + 3 boot gotchas
metadata: 
  node_type: memory
  type: reference
  originSessionId: b48825e3-322d-4dd6-b12a-01d00425c54c
---

To run HA for ha-apps app smoke-tests, the repo opens in the official HA add-on
devcontainer (`ghcr.io/home-assistant/devcontainer:5-apps`); workspace mounts
at `/mnt/supervisor/addons/local/ha-apps`. HA UI = host `:7123` (→ container
8123), observer = host `:7357` (→ 4357). Runtime is Docker Desktop (see
[[container-runtime-preference]] — Apple container can't do the privileged dind
this needs).

Host-CLI helper added 2026-06-16: **`scripts/devcontainer-ha.sh {up|status|log}`**
(tracked via a `!/scripts/` whitelist line in the default-deny root `.gitignore`).
Procedure also written to `.devcontainer/README.md`.

Three boot gotchas (cost a long debugging session — all encoded in the helper):
1. The container entrypoint only idles; it does NOT start dockerd or Supervisor.
   `supervisor_run` (VS Code "Start Home Assistant" task) does. A plain
   `docker start` of the container leaves nothing on 7123/7357.
2. Do NOT pre-start `dockerd` by hand. `supervisor_run`'s `start_docker` spawns
   its own docker-in-docker; a second daemon fights over `/run/docker.sock` and
   the boot hangs at "Waiting for Docker to initialize...". Recover: kill stray
   dockerd, `rm /run/docker.pid /run/docker.sock`, re-run.
3. `supervisor_run` needs a TTY: under `docker exec -d` (no tty) its `stty sane`
   fails and `set -e` aborts before the Supervisor starts (you see dbus/udev
   output then silence). Use `docker exec -dt`.

Local-app gotcha (the `up` helper handles it via `mount_apps`): Supervisor
renamed the local custom-app folder `addons/local` → `apps/local`
(home-assistant/supervisor PR #6837, merged 2026-05-13; live since the 2026.06
dev builds — NOT a 2026.7.0 change; the `:2-addons` image pulls the latest dev
supervisor, e.g. 2026.06.2.dev1510, which already uses `apps/local`). The
devcontainer still mounts the workspace at `addons/local/ha-apps`, and this is a
monorepo (apps in subdirs), so Supervisor scans an empty `apps/local` and shows
zero local apps. Configs there are valid; they're just in the wrong folder. Fix
(per user 2026-06-16): bind-mount each app dir (one with a config.yaml) into
`/mnt/supervisor/apps/local/<app>` BEFORE supervisor_run, so its fresh
`-v /mnt/supervisor:/data` rbind captures them — mounts made AFTER the
Supervisor starts do not propagate in (use `... restart` to remount + reboot).
Apps then show under the `local` repository as `local_<slug>`. Slug comes from
config.yaml's `slug:`, not the dir name.

Wyoming auto-discovery caveat (devcontainer limitation, NOT an app bug): the
devcontainer Supervisor runs **unhealthy** (`ha resolution info` →
`docker_gateway_unprotected`, because the dev docker gateway isn't firewalled
like real HA OS). That blocks/degrades Supervisor ops — add-on installs get
`AppManager.install blocked ... docker_gateway_unprotected`, and the
Supervisor↔core discovery handoff is unreliable, so the "Discovered Wyoming"
card often never appears. `ha discovery` CLI is also gone in these dev builds.
The add-on side is fine (logs "Successfully send discovery information"; its
`discovery: - wyoming` run script sends `uri=tcp://<hostname>:10209`, same
pattern as Piper/Whisper). Workaround in the devcontainer: **add the Wyoming
integration manually** (host `local-<slug>`, e.g. `local-supertonic:10209`) —
that works and serves audio. Auto-discovery works on real HA OS/Supervised.

Prebuilt-image gotcha (bit us 2026-06-16): an app whose `config.yaml` has an
`image:` key (e.g. supertonic's `ghcr.io/saya6k/{arch}-addon-supertonic`) is
installed by **pulling that published GHCR image**, NOT by building local source
(`"build": false` in `ha addons` info). So local/unreleased code changes are
NOT in the running add-on — `import wyoming_supertonic.normalize` failed and the
running image was `...-supertonic:2.1.1`. To test local changes in the
devcontainer you must force a local build: temporarily comment out the `image:`
line in config.yaml (dev-only — never commit; production needs it), then rebuild
the add-on. The unhealthy Supervisor (docker_gateway_unprotected) may block the
build, so the reliable path is merge → republish GHCR → update the add-on.

First boot pulls Supervisor + plugin images (minutes); later boots reach
`:7123` in ~10s. **How to apply:** when asked to smoke-test an app in real HA,
`scripts/devcontainer-ha.sh up`, then install the app from the local store —
don't `docker start` the container and expect HA to be up.
