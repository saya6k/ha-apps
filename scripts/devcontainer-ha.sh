#!/usr/bin/env bash
# Boot Home Assistant inside the ha-apps add-on devcontainer from the host CLI.
#
# The normal path is VS Code "Reopen in Container" + the "Start Home Assistant"
# task. This helper covers the case where the container was started outside
# VS Code (e.g. `docker start`), which skips the devcontainer lifecycle and
# leaves HA unbooted. It encodes three gotchas learned the hard way:
#
#   1. The container entrypoint only idles — it does NOT start dockerd or the
#      Supervisor. `supervisor_run` (the "Start Home Assistant" task) does.
#   2. `supervisor_run` starts its OWN docker-in-docker via start_docker. Do
#      NOT pre-start dockerd by hand — two daemons fight over /run/docker.sock
#      and the boot hangs forever at "Waiting for Docker to initialize...".
#   3. `supervisor_run` needs a TTY: under `docker exec -d` (no tty) its
#      `stty sane` call fails and `set -e` aborts the script before the
#      Supervisor ever runs. We allocate one with `-dt`.
#
# First boot pulls the Supervisor + plugin images (several minutes). HA UI is
# published on the host at http://localhost:7123 (observer on :7357).
set -euo pipefail

IMAGE="ghcr.io/home-assistant/devcontainer:2-addons"
HA_URL="http://localhost:7123"
CMD="${1:-up}"

find_container() {
    docker ps -a --filter "ancestor=${IMAGE}" --format '{{.Names}}' | head -n1
}

cname="$(find_container)"
if [[ -z "${cname}" ]]; then
    echo "No devcontainer found for image ${IMAGE}." >&2
    echo "Open the repo in VS Code and 'Reopen in Container' first." >&2
    exit 1
fi

case "${CMD}" in
up)
    if [[ "$(docker inspect -f '{{.State.Status}}' "${cname}")" != "running" ]]; then
        echo "Starting container ${cname}..."
        docker start "${cname}" >/dev/null
    fi

    if curl -sf -o /dev/null "${HA_URL}" 2>/dev/null; then
        echo "Home Assistant already up at ${HA_URL}"
        exit 0
    fi

    # -dt: detached but WITH a tty (gotcha #3). Let supervisor_run own dockerd
    # (gotcha #2) — we never start it ourselves.
    echo "Launching supervisor_run (first boot pulls images, can take minutes)..."
    docker exec -dt "${cname}" bash -lc \
        'sudo mkdir -p /run/supervisor && sudo -E supervisor_run > /tmp/supervisor_run.log 2>&1'

    echo -n "Waiting for ${HA_URL} "
    for _ in $(seq 1 120); do
        if curl -sf -o /dev/null "${HA_URL}" 2>/dev/null; then
            echo " up!"
            docker exec "${cname}" docker ps \
                --format '{{.Names}}\t{{.Status}}' 2>/dev/null || true
            exit 0
        fi
        echo -n "."
        sleep 5
    done
    echo
    echo "Timed out. Last log lines:" >&2
    docker exec "${cname}" bash -lc 'tail -20 /tmp/supervisor_run.log' >&2 || true
    exit 1
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
    echo "Usage: $0 {up|status|log}" >&2
    exit 2
    ;;
esac
