# Container workflow: standalone build/smoke-test (no devcontainer)

> **Historical note:** this repo used to open in an HA add-on VS Code
> devcontainer (`ghcr.io/home-assistant/devcontainer:2-addons`, since renamed
> upstream to `ghcr.io/home-assistant/devcontainer:apps` —
> [home-assistant/devcontainer](https://github.com/home-assistant/devcontainer),
> which also ships a sibling `:supervisor` image for Supervisor-core
> development). Use the floating `:apps` tag, not a numbered one
> (`5-apps` etc.) — the numbered tag keeps bumping on non-backwards-compatible
> changes, so pinning one in docs goes stale fast. That devcontainer
> was removed from *this repo* in #496 (2026-06-28) when
> `ha-apps` became metadata-only — app source, Dockerfiles, and builds now
> live in each `ha-app-*` repo. The upstream image itself is still maintained
> and works the same way it always did; there is just no `devcontainer.json`
> here anymore, so no Supervisor-based integration test flow currently has a
> home. See "Why this can't just be ported" below.

## Current workflow

Docker Desktop is no longer installed on this Mac. The container runtime is
Apple's **`container` CLI** (Virtualization.framework-based, arm64-native).
Each `ha-app-*` repo builds and smoke-tests its own Dockerfile directly with
it — there's no devcontainer and no running HA Supervisor involved.

### Build

```bash
# Builder VM's default memory (2G) starves RAM-heavy native builds
# (e.g. dx_rt's install.sh check needs >=4G). Bump before building:
container builder start --memory 6G

container build -t <tag> .
```

### Smoke-test (no HA Supervisor)

Add-on images normally boot via bashio/s6-overlay, which expects a running
Supervisor. To smoke-test standalone, override the entrypoint and exercise the
app directly instead of relying on the add-on's own startup:

```bash
container run --rm -it --entrypoint /bin/bash <tag>
# then import/run the app's modules by hand, or curl its HTTP endpoints
```

### Status / cleanup

```bash
container system status
container builder status
container list -a
container image list
```

## Apple Container CLI limitations

- **No `devcontainer.json` support.** VS Code's Dev Containers extension has
  an experimental *"Attach to Running Apple Container"* command, but it
  bypasses `devcontainer.json` entirely — you pre-create and start the
  container yourself (`container create`/`start`), then attach; there's no
  auto-build, `postStartCommand`, `runArgs`, or `mounts` handling. The actual
  `devcontainer.json` engine ([devcontainers/cli](https://github.com/devcontainers/cli))
  calls out to the `docker` CLI surface directly (with special-cased podman
  support) and has no provider abstraction for other runtimes — so "Reopen in
  Container" isn't an option with Apple container regardless
  ([apple/container#912](https://github.com/apple/container/discussions/912)).
- **No privileged docker-in-docker.** Apple container's VM-per-container
  model has no equivalent of `--privileged` nested dind, which the HA
  Supervisor needs to manage its own add-on containers.
- **Builder VM memory isn't auto-sized.** Default builder memory (2G) is too
  low for RAM-heavy native builds; must explicitly
  `container builder start --memory <N>G` beforehand.
- **Native build arch is arm64 only** on Apple Silicon — no local amd64 build
  path. Matters for dependencies only published as x86_64 wheels/binaries.
- **No HA Supervisor in a standalone `container run`.** bashio/s6-overlay
  add-on entrypoints assume a Supervisor is present; smoke tests must
  override the entrypoint and drive the app directly instead.

## Why this can't just be ported to a full HA test flow

The previous devcontainer used Docker Desktop specifically because the HA
Supervisor needs privileged nested docker-in-docker to manage its own add-on
containers, and `devcontainer.json`'s build/launch engine has no Apple-container
provider (only an experimental "attach to an already-running container" path
that skips `devcontainer.json` handling entirely — see limitations above).
Neither constraint has changed. If a real Supervisor-based
integration test flow (boot HA, install the app from the local store, hit
`:7123`) is needed again, it would have to live in a `ha-app-*` repo and would
still need Docker (or Podman) — Apple `container` cannot replace it for that
specific use case.
