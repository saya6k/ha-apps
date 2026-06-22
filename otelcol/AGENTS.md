# AGENTS.md

Guidance for AI coding agents. **Keep this file under ~100 lines** —
describe the *current shape* only. *Why* lives under `.agents/` (gitignored;
AGENTS may name files there, README/DOCS/CHANGELOG must not).
CHANGELOG.md has the *what changed*.

## What this app is

A single Home Assistant **add-on** that packages the OpenTelemetry
Collector Contrib distribution (`otelcol-contrib`) to collect logs,
metrics, and traces from HA Core, the Supervisor, and add-on containers.
Exports everything via OTLP to an LGTM stack (Loki, Grafana, Tempo,
Mimir) or any OTLP-compatible backend.

Merges the capabilities of
[remote_logger](https://github.com/rhizomatics/remote_logger) (HA log
capture) and [cedricziel/otelcol](https://github.com/cedricziel/ha-addons/tree/main/otelcol)
(collector packaging) into a single turn-key add-on. See `SPEC.md` for
the full design.

## Git / repo tracking

Part of the `ha-apps` monorepo. Registered in `.gitignore` (`!/otelcol/`),
release-please config, CI, labeler, and issue templates — fully tracked.

**Stage:** `stage: experimental` in `config.yaml` (shows as experimental
in the HA store). To promote: remove the `stage:` key from `config.yaml`.

## Layout

```
config.yaml / Dockerfile                     add-on packaging
rootfs/etc/s6-overlay/s6-rc.d/otelcol/       s6 service (type/run/finish)
rootfs/etc/otelcol-contrib/                   bundled self-monitoring config
translations/{en,ko}.yaml                     option UI strings
CHANGELOG.md / DOCS.md / README.md           user-facing docs
```

## Architecture

```
HA log file (/config/home-assistant.log) ──→ filelog receiver ──┐
HA Prometheus (/api/prometheus) ───────────→ prometheus receiver │
Container stdout/stderr (Docker socket) ────→ docker_stats rcvr  │
Self-metrics (:8888) ──────────────────────→ prometheus/internal │
                                                                  ├── batch ──→ memory_limiter ──→ otlp exporter ──→ LGTM
Add-on traces (OTLP SDKs) ─────────────────→ otlp receiver ─────┘
```

The add-on runs `otelcol-contrib` (the full contrib binary, statically
linked Go) under s6 supervision. Configuration is generated at startup
from structured HA options; power users can paste raw otelcol YAML via
`raw_config` to override everything.

## Implementation phases

(Design spec lives in `SPEC.md` locally — gitignored.)

1. **Skeleton** (this scaffold) — builds, starts, health-checks
2. **Config generation** — `run` script generates otelcol YAML from structured options
3. **HA log collection** — `filelog` receiver tailing `/config/home-assistant.log`
4. **HA metrics collection** — `prometheus` receiver scraping `/api/prometheus`
5. **Container log collection** — Docker socket or journald (opt-in)
6. **Polish & docs** — DOCS.md setup guide, error messages

## Map / mount layout

```yaml
map:
  - type: homeassistant_config   # /config in container (read-only — we tail logs + scrape metrics)
    read_only: true
  - type: addon_config           # /addon_config in container
    read_only: false
  - type: share                  # /share in container
    read_only: false
  - type: ssl                    # /ssl in container (read-only)
    read_only: true
```

## otelcol-contrib pin

Binary pinned to `0.154.0` via per-arch upstream tags (`-amd64` /
`-arm64`). Bump the pin explicitly in CHANGELOG; test the config merge
+ health check before merging. Upstream releases are frequent (multiple
per month) — we do NOT track `@latest`.

## Don'ts

- **Don't add a custom_component inside the add-on.** The `filelog`
  receiver reads HA logs from the config mount; no HACS dependency.
- **Don't expose OTLP ports to the host by default.** Ports 4317/4318
  default to `null` in `config.yaml`.
- **Don't generate otelcol config in Python** unless bash becomes
  unmaintainable. The config generation is YAML templating — adding
  Python adds ~50 MB to the image for no benefit.
- **Don't bundle Loki/Tempo/Mimir/Grafana.** This add-on is the
  *producer* side, not the consumer.
- **Don't require disabling protection mode by default.** Container
  log collection is opt-in (`container_logs_enabled: false` default).
- **Don't add a web UI / ingress panel.** Configuration is via HA
  options only.
- **Don't support i386 or armv7.** `amd64` + `aarch64` only, matching
  the rest of the monorepo.
- **Don't drop the `raw_config` escape hatch.** Power users need a way
  to use any receiver/processor/exporter the contrib distro ships.
- **Don't bump `otelcol-contrib` blindly.** Every version can change
  receiver config formats. Test locally before lifting the pin.

## Sanity checks before PR

- `yamllint config.yaml translations/*.yaml`
- `shellcheck rootfs/etc/s6-overlay/s6-rc.d/otelcol/{run,finish}`
- `docker build .` (succeeds on both amd64 and aarch64)
- Container starts, health check passes (`curl -f http://localhost:13133/`)

## Documentation layout

| File | Role | Length target |
| ---- | ---- | ------------- |
| `README.md`        | One-paragraph blurb. | ~15 lines |
| `DOCS.md`          | User-facing options + setup guide. HA renders as "Documentation". | ≤ ~200 lines |
| `AGENTS.md`        | This file — agent/dev guidance. | ~100 lines |
| `CHANGELOG.md`     | Per-version headline. | 5–15 / ver |
| `.agents/`         | *Why* / decision logs. Gitignored. | free-form |
