# OpenTelemetry Collector — Documentation

Collect logs, metrics, and traces from your Home Assistant system and
export them via OTLP to Grafana LGTM or any OTLP-compatible backend.

## Quick start

1. **Install the add-on.** It appears as "OpenTelemetry Collector" in the
   add-on store.
2. **Point it at your LGTM stack.** Set `otlp_endpoint` to your OTLP
   gateway (e.g. `lgtm.local:4317` for gRPC, `lgtm.local:4318` for HTTP).
3. **Start the add-on.** By default it collects:
   - HA Core logs (`/config/home-assistant.log`)
   - HA Core metrics (`/api/prometheus` — requires the Prometheus
     integration enabled in HA)
4. **Check the logs** to confirm data is flowing. The health check
   endpoint at port 13133 should return HTTP 200.

## Configuration

### Structured options

| Option | Type | Default | Description |
| ------ | ---- | ------- | ----------- |
| `log_level` | enum | `info` | One of `trace`, `debug`, `info`, `notice`, `warning`, `error`, `fatal`. |
| `otlp_endpoint` | string | `""` | `host:port` of the OTLP gateway. Leave empty for self-monitoring only. |
| `otlp_protocol` | enum | `grpc` | `grpc` or `http`. Must match the target endpoint. |
| `otlp_headers` | list | `[]` | Extra headers (name/value pairs) for OTLP requests. Use for `Authorization`, `X-Scope-OrgID`. |
| `otlp_tls_insecure` | bool | `false` | Skip TLS verification (local/testing only). |
| `ha_logs_enabled` | bool | `true` | Tail `/config/home-assistant.log` as OTLP log records. |
| `ha_metrics_enabled` | bool | `true` | Scrape HA's `/api/prometheus` as OTLP metrics. |
| `container_logs_enabled` | bool | `false` | Collect container stdout/stderr (requires disabling protection mode). **Not yet implemented — use `raw_config`.** |
| `host_metrics_enabled` | bool | `false` | Collect host CPU/memory/disk/network. **Not yet implemented — use `raw_config`.** |
| `raw_config` | string | `""` | Full otelcol YAML config. When set, overrides all structured options above. |

### Power-user path: `raw_config`

If you already know your otelcol pipeline, paste it directly into
`raw_config`. It is layered on top of the bundled self-monitoring
baseline (prometheus scraping `localhost:8888` + health check).

Example — collect HA logs + send to Grafana Cloud:

```yaml
receivers:
  filelog:
    include: [/config/home-assistant.log]
    include_file_path: true
    multiline:
      line_start_pattern: '^\d{4}-\d{2}-\d{2}'

processors:
  batch:
    timeout: 10s
    send_batch_size: 100

exporters:
  otlp:
    endpoint: tempo-prod-04-prod-us-east-0.grafana.net:443
    headers:
      authorization: Basic <base64-userid-token>

service:
  pipelines:
    logs:
      receivers: [filelog]
      processors: [batch]
      exporters: [otlp]
```

## Receiving traces from other add-ons

This add-on exposes OTLP receivers on ports 4317 (gRPC) and 4318 (HTTP).
To let other add-ons send traces here:

1. Set the port to a host port in the add-on's Network tab (e.g. `4318:4318`).
2. Configure the other add-on's OTLP exporter to point at
   `http://<ha-host>:4318`.

The ports default to `null` (not exposed) for security.

## Mount points

| Mount | Container path | Access | Purpose |
| ----- | -------------- | ------ | ------- |
| `homeassistant_config` | `/config` | read-only | Tail `home-assistant.log`, resolve SSL certs |
| `addon_config` | `/addon_config` | read-write | Add-on's own config (persistent across rebuilds) |
| `share` | `/share` | read-write | Shared data with other add-ons |
| `ssl` | `/ssl` | read-only | TLS certificates for OTLP export |

## Troubleshooting

| Symptom | Likely cause |
| ------- | ------------ |
| Container exits immediately | Check add-on logs — likely invalid `raw_config` YAML |
| Health check fails (port 13133) | otelcol-contrib didn't start. Check logs for config parse errors. |
| No data in LGTM | Verify `otlp_endpoint` and protocol. Try `otlp_tls_insecure: true` for local endpoints. |
| HA metrics missing | Enable the `prometheus` integration in HA Core first. |
| "ha_logs_enabled is true but config generation is not yet implemented" | Config generation from structured options is Phase 2. Use `raw_config` for now. |

## Self-monitoring

The add-on always scrapes its own Prometheus endpoint (`localhost:8888`)
every 5 seconds and logs the metrics via the debug exporter (visible
when `log_level` is `debug` or `trace`). The health check extension
listens on port 13133.

## Acknowledgements

Built on the [OpenTelemetry Collector Contrib](https://github.com/open-telemetry/opentelemetry-collector-releases)
distribution. Inspired by [cedricziel/otelcol](https://github.com/cedricziel/ha-addons/tree/main/otelcol)
(HA add-on packaging) and [rhizomatics/remote_logger](https://github.com/rhizomatics/remote_logger)
(HA log capture patterns).
