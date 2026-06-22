# Changelog

## 0.1.0

### Features

- **Three-pillar observability out of the box** — logs, metrics, and traces
  from Home Assistant with no extra integrations required.
- **HA log collection** — `filelog` receiver tails `/config/home-assistant.log`
  with multiline grouping for Python tracebacks and full severity mapping.
- **HA metrics** — Python bridge subscribes to `state_changed` via the WebSocket
  API and exports numeric entity states as OTLP gauges, seeded from `/api/states`
  on connect. No Prometheus integration dependency.
- **HA structured event logs** — `system_log_event` broadcast (requires
  `logger: fire_event: true` in HA config) exported as structured OTLP log
  records including stack traces and source location.
- **HA traces** — event context graph (`context.id` → `context.parent_id`)
  mapped to OTLP spans, linking `call_service → automation_triggered →
  state_changed` chains into a single trace automatically.
- **Container logs and stats** (opt-in, `container_logs_enabled: false`) —
  streams logs and polls CPU/memory stats for every add-on plus the Supervisor
  and HA Core via the Supervisor API. No Docker socket, protection mode stays ON.
- **OTLP receiver** — accepts traces/logs/metrics from other add-ons or the
  host network on ports 4317 (gRPC) and 4318 (HTTP); both default to null
  (host-unexposed).
- **Raw config escape hatch** — `raw_config` option accepts a full otelcol YAML
  pipeline, overriding structured options while keeping the self-monitoring baseline.
- **zpages sidebar panel** — pipeline and trace debug view behind HA's auth proxy
  via the ingress panel.

### Security

- Custom AppArmor profile (`apparmor.txt`) — denies Docker socket access,
  `sys_admin`, `net_admin`, and `sys_ptrace`; permits only required paths.
- `auth_api: true` + `homeassistant_api: true` for authenticated Supervisor and
  HA API access.
- `hassio_api: true` + `hassio_role: manager` for Supervisor API access to
  other add-ons' logs and stats (used only when `container_logs_enabled: true`).
- OTLP ports default to `null`; pprof restricted to localhost.

### Infrastructure

- `otelcol-contrib` pinned to **0.154.0** (per-arch upstream image tags).
- Two s6-overlay v3 services: `otelcol` (collector) and `ha-bridge` (Python bridge).
- Python bridge in `/opt/bridge-venv` — `aiohttp`, `opentelemetry-sdk`,
  `opentelemetry-exporter-otlp-proto-http`.
- Reconnect loop with exponential backoff (2 s → 60 s) for the HA WebSocket connection.
- `amd64` + `aarch64` only.
