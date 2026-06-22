# OpenTelemetry Collector — Documentation

Collect logs, metrics, and traces from your Home Assistant system and
export them to Grafana LGTM (Loki, Tempo, Mimir) or any OTLP-compatible
backend — no extra integrations required.

## Quick start

1. **Install the add-on** from the store.
2. **Set `otlp_endpoint`** to your OTLP gateway:
   - gRPC: `lgtm.local:4317`
   - HTTP: `lgtm.local:4318` (set `otlp_protocol: http`)
3. **Start the add-on.** The status panel ("OpenTelemetry Collector" in the sidebar)
   shows the zpages debug view — a quick sanity check that the pipeline is running.
4. **Check the add-on log** for `Bridge running` and confirmed batch exports.

By default the add-on collects:

| Signal | Source |
|---|---|
| Logs | `/config/home-assistant.log` tailed by the filelog receiver |
| Metrics | Numeric entity states via the HA WebSocket API |
| Logs (structured) | `system_log_event` errors/warnings via the HA WebSocket API |
| Traces | HA event context graph (`context.id` → `context.parent_id` chains) |

## Configuration options

| Option | Type | Default | Description |
|---|---|---|---|
| `log_level` | enum | `info` | `trace` `debug` `info` `notice` `warning` `error` `fatal` |
| `otlp_endpoint` | string | `""` | `host:port` of the OTLP gateway. Empty = self-monitoring only. |
| `otlp_protocol` | enum | `grpc` | `grpc` or `http` — must match the target endpoint. |
| `otlp_headers` | list | `[]` | `name`/`value` pairs for OTLP requests (`Authorization`, `X-Scope-OrgID`, …). |
| `otlp_tls_insecure` | bool | `false` | Skip TLS verification (local/testing only). |
| `ha_logs_enabled` | bool | `true` | Tail `/config/home-assistant.log` as structured OTLP log records. |
| `ha_metrics_enabled` | bool | `true` | Numeric entity states → OTLP gauges. No HA integration required. |
| `ha_events_enabled` | bool | `true` | `system_log_event` → structured OTLP log records with stack traces. |
| `ha_traces_enabled` | bool | `true` | HA event context graph → OTLP traces. No HA configuration required. |
| `container_logs_enabled` | bool | `false` | Supervisor, HA Core, and every add-on's logs + CPU/memory stats via the Supervisor API. See note below. |
| `host_metrics_enabled` | bool | `false` | Host CPU/memory/disk/network. Not yet implemented — use `raw_config`. |
| `raw_config` | string | `""` | Full otelcol YAML. When non-empty, overrides all structured options (layered on the self-monitoring baseline). |

## Setting up HA structured log events (`ha_events_enabled`)

By default HA's System Log integration does **not** broadcast events over the
WebSocket API. To enable it, add to `configuration.yaml`:

```yaml
logger:
  default: info
  fire_event: true
```

Restart HA Core after the change. Without this, `ha_events_enabled: true` is
harmless — the bridge simply receives no `system_log_event` messages.

## Container logs and stats (`container_logs_enabled`)

When enabled, the bridge enumerates all installed add-ons via the Supervisor API
and starts a log-stream + stats poller for each one (plus the Supervisor and HA Core
themselves). Data is tagged with `addon.slug` and `addon.name`.

- **Logs** appear as OTLP log records in the `ha-containers` source.
- **CPU %** and **memory %** appear as `supervisor.addon.cpu_percent` and
  `supervisor.addon.memory_percent` gauges, keyed by `addon.slug`.

No Docker socket access is required. Protection mode stays ON.
Re-enumeration happens every 5 minutes to pick up newly installed add-ons.

## Receiving traces from other add-ons

The OTLP receivers on ports 4317 (gRPC) and 4318 (HTTP) default to `null`
(host-unexposed). To accept traces from add-ons on other machines or from the
host network:

1. Open the **Network** tab and assign a host port (e.g. `4318 → 4318`).
2. Point the other add-on's OTLP exporter at `http://<ha-host>:4318`.

## Power-user path: `raw_config`

Paste a complete otelcol YAML pipeline into `raw_config` to override the
structured options entirely. The bundled self-monitoring baseline (health check,
zpages, pprof) is always merged in regardless.

Example — send HA logs to Grafana Cloud Loki:

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

The add-on always exposes:

| Endpoint | Port | Purpose |
|---|---|---|
| Health check | 13133 | `GET /` → 200 OK when otelcol is healthy |
| zpages | 55679 | Pipeline and trace debug view (via sidebar panel, behind HA auth) |
| pprof | 1777 | Go profiler — localhost only, not host-exposed |

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Container exits immediately | Invalid `raw_config` YAML — check the add-on log for parse errors |
| Health check fails | otelcol didn't start; see logs for config errors |
| No data in backend | Verify `otlp_endpoint` and `otlp_protocol` match the gateway |
| TLS errors | Try `otlp_tls_insecure: true` for self-signed certs |
| No `system_log_event` metrics | Enable `fire_event: true` in HA's `logger:` config |
| Bridge not connecting | Check `SUPERVISOR_TOKEN` is set (requires `homeassistant_api: true`) |
| Container logs missing | Confirm `container_logs_enabled: true` and check the add-on log for Supervisor API errors |

## Acknowledgements

Built on [OpenTelemetry Collector Contrib](https://github.com/open-telemetry/opentelemetry-collector-releases)
0.154.0. Inspired by
[cedricziel/otelcol](https://github.com/cedricziel/ha-addons/tree/main/otelcol)
(HA add-on packaging) and
[rhizomatics/remote_logger](https://github.com/rhizomatics/remote_logger)
(HA event-to-OTLP patterns).
