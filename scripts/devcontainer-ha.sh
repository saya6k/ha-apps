#!/usr/bin/env bash
# Boot Home Assistant inside the ha-apps add-on devcontainer from the host CLI,
# with this monorepo's apps exposed in HA's local store.
#
# The normal path is VS Code "Reopen in Container" + the "Start Home Assistant"
# task. This helper covers booting from the host (e.g. after `docker start`) and
# bridges a path mismatch the official devcontainer hasn't caught up to.
#
# Boot gotchas (learned the hard way; all handled below):
#   1. The container entrypoint only idles — it does NOT start dockerd or the
#      Supervisor. `supervisor_run` does.
#   2. `supervisor_run` starts its OWN docker-in-docker via start_docker. Do
#      NOT pre-start dockerd by hand — two daemons fight over /run/docker.sock
#      and the boot hangs forever at "Waiting for Docker to initialize...".
#   3. `supervisor_run` needs a TTY: under `docker exec -d` (no tty) its
#      `stty sane` call fails and `set -e` aborts before the Supervisor runs.
#      We allocate one with `-dt`.
#
# Local-app gotcha (the reason for mount_apps):
#   Supervisor renamed the local custom-app folder addons/local -> apps/local
#   (home-assistant/supervisor PR #6837, merged 2026-05-13; live since the
#   2026.06 dev builds). The devcontainer still bind-mounts the workspace at
#   .../addons/local/ha-apps, and this is a monorepo (apps in subdirs), so the
#   Supervisor scans an empty apps/local and shows no local apps. Fix: bind-mount
#   each app dir into /mnt/supervisor/apps/local/<app> BEFORE supervisor_run, so
#   its fresh `-v /mnt/supervisor:/data` rbind picks them up (mounts made after
#   the Supervisor starts do NOT propagate into it).
#
# First boot pulls the Supervisor + plugin images (minutes). HA UI is published
# on the host at http://localhost:7123 (observer on :7357).
set -euo pipefail

IMAGE="ghcr.io/home-assistant/devcontainer:2-addons"
HA_URL="http://localhost:7123"
CMD="${1:-up}"

# Workspace mount (devcontainer, old path) and the folder Supervisor scans.
REPO_DIR="/mnt/supervisor/addons/local/ha-apps"
APPS_DIR="/mnt/supervisor/apps/local"

cname="$(docker ps -a --filter "ancestor=${IMAGE}" --format '{{.Names}}' | head -n1)"
if [[ -z "${cname}" ]]; then
    echo "No devcontainer found for image ${IMAGE}." >&2
    echo "Open the repo in VS Code and 'Reopen in Container' first." >&2
    exit 1
fi

ensure_running() {
    if [[ "$(docker inspect -f '{{.State.Status}}' "${cname}")" != "running" ]]; then
        echo "Starting container ${cname}..."
        docker start "${cname}" >/dev/null
    fi
}

# Bind-mount every app dir (one containing config.yaml) into apps/local.
mount_apps() {
    echo "Mounting apps into ${APPS_DIR} ..."
    docker exec "${cname}" bash -lc '
        set -e
        sudo mkdir -p "'"${APPS_DIR}"'"
        for d in "'"${REPO_DIR}"'"/*/; do
            app=$(basename "$d")
            [ -f "${d}config.yaml" ] || continue
            if ! mountpoint -q "'"${APPS_DIR}"'/$app"; then
                sudo mkdir -p "'"${APPS_DIR}"'/$app"
                sudo mount --bind "$d" "'"${APPS_DIR}"'/$app"
            fi
        done
        ls "'"${APPS_DIR}"'"
    '
}

boot_supervisor() {
    echo "Launching supervisor_run (first boot pulls images, can take minutes)..."
    docker exec -dt "${cname}" bash -lc \
        'sudo mkdir -p /run/supervisor && sudo -E supervisor_run > /tmp/supervisor_run.log 2>&1'
    echo -n "Waiting for ${HA_URL} "
    for _ in $(seq 1 120); do
        if curl -sf -o /dev/null "${HA_URL}" 2>/dev/null; then
            echo " up!"
            docker exec "${cname}" docker exec hassio_cli ha store reload >/dev/null 2>&1 || true
            docker exec "${cname}" docker ps \
                --format '{{.Names}}\t{{.Status}}' 2>/dev/null || true
            return 0
        fi
        echo -n "."
        sleep 5
    done
    echo
    echo "Timed out. Last log lines:" >&2
    docker exec "${cname}" bash -lc 'tail -20 /tmp/supervisor_run.log' >&2 || true
    return 1
}

case "${CMD}" in
up)
    ensure_running
    mount_apps
    if curl -sf -o /dev/null "${HA_URL}" 2>/dev/null; then
        echo "Home Assistant already up at ${HA_URL}."
        echo "If local apps are missing, run: $0 restart"
        exit 0
    fi
    boot_supervisor
    ;;
restart)
    # Reliable "make local apps show up": stop Supervisor, (re)mount apps,
    # boot fresh so the rbind captures apps/local.
    ensure_running
    docker exec "${cname}" bash -lc 'sudo pkill -x supervisor_run 2>/dev/null; docker rm -f hassio_supervisor 2>/dev/null; true'
    mount_apps
    boot_supervisor
    ;;
mount-apps)
    ensure_running
    mount_apps
    ;;
status)
    docker exec "${cname}" docker ps \
        --format '{{.Names}}\t{{.Status}}' 2>/dev/null || echo "dind not running"
    curl -s -o /dev/null -w "host ${HA_URL} -> HTTP %{http_code}\n" "${HA_URL}" || true
    ;;
log)
    docker exec "${cname}" bash -lc 'tail -40 /tmp/supervisor_run.log'
    ;;
*)
    echo "Usage: $0 {up|restart|mount-apps|status|log}" >&2
    exit 2
    ;;
esac
