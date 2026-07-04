# Registry Cache

A pull-through cache for `docker.io` and `ghcr.io`. Repeated image pulls are
served from local disk instead of upstream, and Docker Hub's anonymous-pull
rate limit stops being a factor.

## Installation

1. **Settings** → **Apps** → **App Store**, add this repository.
2. Install **Registry Cache** and **Start** it.
3. Point your Docker/containerd client at it — see below. This app does not
   configure clients for you.

## Client setup

The cache is reachable on port `5000`, routed by hostname:
`docker-cache.local` for docker.io, `ghcr-cache.local` for ghcr.io. **Both
hostnames must resolve to the Home Assistant host from wherever your client
runs** — via `/etc/hosts`, local DNS, or HA's own DNS if the client is
another app on the `hassio` network. This app does not manage that DNS entry
for you.

### containerd (recommended — works for any registry, not just docker.io)

Add a `hosts.toml` per upstream you want mirrored, e.g. for `ghcr.io`:

```toml
# /etc/containerd/certs.d/ghcr.io/hosts.toml
server = "https://ghcr.io"

[host."http://ghcr-cache.local:5000"]
  capabilities = ["pull", "resolve"]
```

And for `docker.io`:

```toml
# /etc/containerd/certs.d/docker.io/hosts.toml
server = "https://registry-1.docker.io"

[host."http://docker-cache.local:5000"]
  capabilities = ["pull", "resolve"]
```

Restart `containerd` after adding these.

### dockerd (docker.io only)

Docker's daemon only supports a single mirror list, and only for docker.io:

```json
{
  "registry-mirrors": ["http://docker-cache.local:5000"]
}
```

in `/etc/docker/daemon.json`, then restart `dockerd`. There is no equivalent
dockerd-level mechanism for mirroring `ghcr.io` — use containerd's
`hosts.toml` (above) if you need that, or point tooling at
`ghcr-cache.local:5000` directly.

## Options

| Option | Default | Description |
|---|---|---|
| `docker_enabled` | `true` | Run the docker.io cache. |
| `docker_cache_ttl` | `168h` | How long a docker.io blob/manifest stays cached before GC. |
| `ghcr_enabled` | `true` | Run the ghcr.io cache. |
| `ghcr_cache_ttl` | `168h` | How long a ghcr.io blob/manifest stays cached before GC. |
| `prefetch` | `[]` | Image refs to warm at startup, e.g. `ghcr.io/home-assistant/amd64-base:latest`. |

Disabling a registry (and restarting the app) stops only that registry's
process; the other registry's cache is untouched.

## Prefetch

Entries in `prefetch` must start with a registry host this app knows about
(`docker.io/...` or `ghcr.io/...`). At startup, each ref's manifest (and, for
multi-arch images, every platform sub-manifest) is fetched through the local
cache, followed by every blob it references — so the first real pull is
already warm. A ref that 404s or can't be reached is logged and skipped; it
never blocks the app from starting.

## Troubleshooting

- **"connection refused" from a client** — check the app is started and
  port `5000` is reachable from the client's network.
- **Client falls through to the real upstream** — usually a DNS problem:
  confirm `docker-cache.local` / `ghcr-cache.local` actually resolve to the
  HA host from the client, not just from inside the app's own container.
- **Cache never shrinks** — GC only removes a blob once its `cache_ttl` has
  elapsed since it was cached; it isn't refreshed by repeat pulls of the
  same tag.
