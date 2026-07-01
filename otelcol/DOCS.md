# OpenTelemetry Collector

Collects logs, metrics, and traces from your Home Assistant system and exports
them via OTLP to Grafana LGTM (Loki, Tempo, Mimir) or any OTLP-compatible
backend — no extra integrations, no HACS dependency.

## Installation

1. **Settings** → **Apps** → **App Store**, add this repository.
2. Install **OpenTelemetry Collector** and open **Configuration**.
3. Set `otlp_endpoint` to your OTLP gateway (see [Backend setup](#backend-setup)).
4. **Start** the add-on. The sidebar panel shows the live pipeline debug view.

## Backend setup

### Grafana Cloud

1. In Grafana Cloud, go to **Connections** → **OpenTelemetry**.
2. Copy the OTLP endpoint and your API token.
3. Configure the add-on:

```yaml
otlp_endpoint: "otlp-gateway-prod-01.grafana.net:443"
otlp_protocol: grpc
otlp_headers:
  - name: Authorization
    value: "Basic <base64(instanceId:token)>"
```

### Self-hosted LGTM stack

Point the add-on at your Grafana Alloy or OpenTelemetry Collector gateway:

```yaml
otlp_endpoint: "alloy.local:4317"
otlp_protocol: grpc
otlp_tls_insecure: true   # if using self-signed certs
```

## What gets collected

By default, all four signal types are on:

| Signal | Source | Toggle |
|---|---|---|
| Logs | `/config/home-assistant.log` tailed by filelog receiver | `ha_logs_enabled` |
| Metrics | Numeric entity states — seeded from REST on connect, live via WebSocket | `ha_metrics_enabled` |
| Logs (structured) | `system_log_event` errors/warnings with stack traces | `ha_events_enabled` |
| Traces | `call_service`, `automation_triggered`, `script_started`, `timer_finished`, `homeassistant_start/stop`, `component_loaded`, `persistent_notifications_updated`, `device_registry_updated` — linked by `context.id` into parent→child spans | `ha_traces_enabled` |
| Logs (lifecycle) | `homeassistant_start/stop`, `component_loaded`, notification and device registry changes as OTLP log records | `ha_events_enabled` |
| Metrics (entity count) | `ha.entity.count{ha.domain}` — entity count per domain, seeded on connect and updated live | `ha_metrics_enabled` |
| Metrics (event rate) | `ha.events.total{ha.event_type}` — event throughput counter per type | `ha_metrics_enabled` |
| Metrics (bridge health) | `ha.bridge.context_lru_size` — active context entries in the span-linking LRU | `ha_metrics_enabled` |
| Logs + Metrics | Container stdout and CPU/memory% for Supervisor, HA Core, and all add-ons via Supervisor API | `container_logs_enabled` |
| Metrics (host) | Host CPU, memory, load, disk I/O, filesystem usage via `hostmetrics` — `service.name: homeassistant-host` | `host_metrics_enabled` |

The Python bridge (`ha-otel-bridge`) connects to HA's WebSocket API, subscribes to the
events above, and pushes everything as OTLP to the local collector on `localhost:4318`.
No Docker socket access or custom component required.

## How telemetry is attributed (`service.name`)

Each signal is attributed to the component that produced it, following
OpenTelemetry semantic conventions. When an OTLP backend is configured:

| Source | `service.name` |
|---|---|
| Home Assistant Core (entity metrics, event traces, Core logs, `system_log_event`) | `homeassistant` |
| Each add-on's container logs and CPU/memory stats | the add-on slug (e.g. `d5369777_music_assistant`) |
| Supervisor logs and stats | `supervisor` |
| Host metrics (`host_metrics_enabled`) | `homeassistant-host` |
| This add-on (its own stats, bridge health) | its install slug (e.g. `03f32180_otelcol`) |

`service.version` carries the producing add-on's version where available, and all
HA-origin signals share `service.namespace=home-assistant`. The
`supervisor.addon.*` gauges keep their per-add-on dimension as the `service.name`
label, so you can still compare add-ons fleet-wide by grouping on `service_name`.

Structured-log attributes follow semconv: `code.namespace` (logger) and
`code.filepath` (source). Externally-instrumented add-ons that send OTLP to this
collector keep their own `service.name` untouched.

> **Migration:** earlier versions tagged everything as `service.name=ha-otel-bridge`
> with a global `ha.addon.version`. Both are gone — query per-source `service.name`
> (or `service.namespace="home-assistant"` for all HA sources) and `service.version`.
> Standard otelcol collector dashboards keyed on `service.name=otelcol-contrib`
> should point at this add-on's install slug instead.

## Options

| Option | Default | Description |
|---|---|---|
| `log_level` | `info` | `trace` / `debug` / `info` / `warning` / `error` / `fatal` |
| `otlp_endpoint` | `""` | `host:port` of the OTLP gateway. Empty = self-monitoring only (no export). |
| `otlp_protocol` | `grpc` | `grpc` or `http` — must match the target endpoint. |
| `otlp_headers` | `[]` | `name`/`value` pairs added to every OTLP request (`Authorization`, `X-Scope-OrgID`, …). |
| `otlp_tls_insecure` | `false` | Skip TLS certificate verification. Local/testing only. |
| `ha_logs_enabled` | `true` | Tail `/config/home-assistant.log` as OTLP log records. |
| `ha_metrics_enabled` | `true` | Numeric entity states → OTLP gauges. No HA integration required. |
| `ha_events_enabled` | `true` | `system_log_event` → structured OTLP log records with stack traces. Requires `fire_event: true` (see below). |
| `ha_traces_enabled` | `true` | HA event context graph → OTLP traces. No HA configuration required. |
| `container_logs_enabled` | `false` | Logs and CPU/memory stats for the Supervisor, HA Core, and every add-on via the Supervisor API. |
| `host_metrics_enabled` | `false` | Host CPU, memory, load, disk I/O, and filesystem usage via the `hostmetrics` receiver. See [Host metrics](#host-metrics-host_metrics_enabled). |
| `raw_config` | `""` | Full otelcol YAML pipeline. Overrides all structured options when non-empty. |

## Enabling structured log events (`ha_events_enabled`)

HA's System Log integration does not broadcast events over the WebSocket API by
default. To enable it, add to `configuration.yaml`:

```yaml
logger:
  default: info
  fire_event: true
```

Restart HA Core after the change. Without this, `ha_events_enabled: true` is
harmless — the bridge receives no `system_log_event` messages.

## Container logs and stats (`container_logs_enabled`)

When enabled, the bridge enumerates all add-ons via the Supervisor API and
polls logs + CPU/memory stats for each one (plus the Supervisor and HA
Core). Each add-on's logs and stats are attributed to its own `service.name`
(see [How telemetry is attributed](#how-telemetry-is-attributed-servicename)).

- **Logs** appear as OTLP log records under the add-on's `service.name`.
- **Resource stats** appear as `supervisor.addon.*` metrics, one `service.name`
  per add-on:
  - Gauges: `cpu_percent`, `memory_percent`, `memory_usage_bytes`.
  - Cumulative byte counters (graph with `rate()`): `network_rx_bytes`,
    `network_tx_bytes`, `blk_read_bytes`, `blk_write_bytes`.

No Docker socket access is required. Protection mode stays ON. New add-ons are
picked up automatically within 5 minutes.

## Host metrics (`host_metrics_enabled`)

When enabled, the OpenTelemetry `hostmetrics` receiver collects host-level
resource metrics every 30 s, exported under `service.name: homeassistant-host`
(namespace `home-assistant`):

- **CPU** — `system.cpu.*` (utilisation and time per state)
- **Memory** — `system.memory.*` (used/free/cached bytes)
- **Load** — `system.cpu.load_average.{1m,5m,15m}`
- **Disk I/O** — `system.disk.*` (read/write bytes and operations)
- **Filesystem** — `system.filesystem.usage` per real partition

In a Home Assistant add-on container, `/proc/stat`, `/proc/meminfo`,
`/proc/loadavg`, and `/proc/diskstats` already report **host** values, and the
bind-mounted `/config`, `/share`, and `/data` filesystems reflect the host data
partition — so these metrics are meaningful with **no protection-mode change
and no extra privileges**. Virtual/overlay filesystems (`tmpfs`, `overlay`,
`proc`, `sysfs`, …) are filtered out.

**Network is intentionally not collected.** Without `host_network`, the add-on
only sees its own network namespace, so host interface counters aren't
available. To collect host network metrics, run a dedicated node-level
collector (or Grafana Alloy) on the host and point its OTLP exporter at this
add-on's receiver.

## Receiving traces from other add-ons

OTLP ports 4317 (gRPC) and 4318 (HTTP) are closed to the host by default. To
accept traces from add-ons on other hosts or from the host network:

1. Open the **Network** tab and assign a host port (e.g. `4318 → 4318`).
2. Point the other service's OTLP exporter at `http://<ha-host>:4318`.

## Power-user path: `raw_config`

Paste a complete otelcol YAML pipeline into `raw_config` to bypass the
structured options. The self-monitoring baseline (health check, zpages, pprof)
is always merged in regardless.

Example — send HA logs directly to Grafana Cloud Loki:

```yaml
receivers:
  filelog/ha:
    include: [/config/home-assistant.log]
    multiline:
      line_start_pattern: '^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'

processors:
  batch:
    timeout: 10s

exporters:
  otlphttp/grafana:
    endpoint: https://logs-prod-006.grafana.net/otlp
    headers:
      authorization: Basic <base64-userid:token>

service:
  pipelines:
    logs:
      receivers: [filelog/ha]
      processors: [batch]
      exporters: [otlphttp/grafana]
```

## Self-monitoring

| Endpoint | Port | Description |
|---|---|---|
| Health check | 13133 | `GET /` → 200 when otelcol is healthy |
| zpages | 55679 | Live pipeline and trace debug view (sidebar panel, behind HA auth) |
| pprof | 1777 | Go profiler — localhost only, not host-exposed |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Container exits immediately | Invalid `raw_config` YAML — check the add-on log for parse errors |
| No data in backend | Verify `otlp_endpoint` and `otlp_protocol` match the gateway |
| TLS errors | Set `otlp_tls_insecure: true` for self-signed certs |
| No `system_log_event` data | Add `fire_event: true` to HA's `logger:` config and restart Core |
| Bridge not connecting | Check the add-on log; requires `homeassistant_api: true` (set automatically) |
| Container logs missing | Confirm `container_logs_enabled: true` and check the log for Supervisor API errors |

## Acknowledgements

Built on [OpenTelemetry Collector Contrib](https://github.com/open-telemetry/opentelemetry-collector-releases)
0.154.0. Inspired by
[cedricziel/otelcol](https://github.com/cedricziel/ha-addons/tree/main/otelcol)
and [rhizomatics/remote_logger](https://github.com/rhizomatics/remote_logger).
