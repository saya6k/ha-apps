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
| Metrics | Numeric entity states via HA WebSocket API | `ha_metrics_enabled` |
| Logs (structured) | `system_log_event` errors/warnings with stack traces | `ha_events_enabled` |
| Traces | HA event context graph (`call_service → automation → state_changed`) | `ha_traces_enabled` |

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
streams logs + polls CPU/memory stats for each one (plus the Supervisor and HA
Core). Data is tagged with `addon.slug` and `addon.name`.

- **Logs** appear as OTLP log records in the `ha-containers` source.
- **CPU%** / **memory%** appear as `supervisor.addon.cpu_percent` /
  `supervisor.addon.memory_percent` gauges keyed by `addon.slug`.

No Docker socket access is required. Protection mode stays ON. New add-ons are
picked up automatically within 5 minutes.

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
