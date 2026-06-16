---
name: container-runtime-preference
description: On this Mac use Docker Desktop for containers; podman was removed
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b54e27a2-53cd-4ed1-9030-97ce4c287b64
---

For container/Docker work on this machine (saya6k's Mac, arm64), use **Docker
Desktop** (`/Applications/Docker.app`, context `desktop-linux`). Do **not** use
or reinstall podman — it was uninstalled on 2026-06-15 to free space (~1.06GB:
886M user data + 175M `/opt/podman` pkg + the applehv machine's 22GB disk
allocation).

The Apple `container` CLI was also removed on 2026-06-15 (4.8G data dir +
57M `.pkg` binary at `/usr/local/bin/container`, receipt
`com.apple.container-installer`). Note: macOS's own `com.apple.containermanagerd`
/ `com.apple.ContainerMigrationService` launchd daemons are OS components,
unrelated to the CLI — never touch them.

Apple `container` was reconsidered on 2026-06-16 for the HA add-on devcontainer
and rejected again: VS Code Dev Containers has no Apple-container backend, and
the HA Supervisor needs `--privileged` nested docker-in-docker, which Apple
container's VM-per-container model (incl. `container-machine`) doesn't support;
its docs don't even mention privileged/dind/socket bind. Docker Desktop stays
the only viable runtime for [[devcontainer-ha-boot]].

**Why:** user explicitly chose Docker over podman/Apple-container and asked to delete them.
**How to apply:** if a container runtime is needed and Docker's daemon isn't up,
launch/wait on Docker.app rather than spinning up a `podman machine`. Disk is
tight (~14Gi free), so avoid creating large VM disks. Removing the podman pkg's
root-owned bits (`/opt/podman`, `/etc/paths.d/podman-pkg`, pkgutil receipt
`com.redhat.podman`) needs sudo — hand the command to the user via `!`.
Relates to [[container-cli-setup]].
