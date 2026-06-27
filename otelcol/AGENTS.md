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

**Stage:** stable (no `stage:` key in `config.yaml`).

## Layout

```
config.yaml / Dockerfile                          add-on packaging
rootfs/usr/bin/ha-otel-bridge                     Python bridge (WebSocket → OTLP)
rootfs/etc/s6-overlay/s6-rc.d/otelcol/           s6 service for otelcol-contrib
rootfs/etc/s6-overlay/s6-rc.d/ha-bridge/         s6 service for Python bridge
rootfs/etc/otelcol-contrib/                       bundled self-monitoring config
translations/{en,ko}.yaml                         option UI strings
CHANGELOG.md / DOCS.md / README.md               user-facing docs
```

## Architecture

Two processes under s6 supervision in one container:

```
── ha-otel-bridge (Python sidecar) ───────────────────────────────────────────
HA WebSocket API:
  state_changed                    ──→ OTLP gauges  (numeric entity states)
                                       + ha.entity.count{domain} aggregate
  system_log_event                 ──→ OTLP logs    (structured + stack traces)
  call_service                     ──┐
  automation_triggered             ──┤
  script_started                   ──┤ OTLP spans   (context.id chains parent→child)
  timer_finished                   ──┤
  homeassistant_start/stop         ──┤ + OTLP logs  (lifecycle)
  component_loaded                 ──┤ + OTLP logs
  persistent_notifications_updated ──┤ + OTLP logs
  device_registry_updated          ──┘ + OTLP logs
HA REST /api/states      ──→ gauge seed + entity domain map on connect
Supervisor API (opt-in):
  /addons/*/logs         ──→ OTLP logs    (tagged addon.slug / addon.name)
  /addons/*/stats        ──→ OTLP gauges  (CPU % / memory %)
        │
        │  OTLP/HTTP  localhost:4318
        ▼
── otelcol-contrib ───────────────────────────────────────────────────────────
Receivers:
  otlp            ← bridge signals + external add-on SDKs (4317 gRPC / 4318 HTTP)
  filelog/ha      ← /config/home-assistant.log (multiline + severity mapping)
  prometheus/int  ← localhost:8888 (self-metrics)
Processors: memory_limiter → batch → resource (ha.addon.version tag)
Exporters:  otlp[http]/lgtm  +  debug
        │
        ▼
LGTM stack (Loki / Grafana / Tempo / Mimir) or any OTLP backend
```

Config is generated at startup from structured HA options; power users can
paste raw otelcol YAML via `raw_config` to override everything.

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
