# otelcol — Observability Add-on for Home Assistant

> **Status:** Spec (pre-implementation)
> **Slug:** `otelcol`
> **Stage:** experimental
> **Scope for commits:** `otelcol`

## 1. Objective

A single Home Assistant add-on that collects **logs**, **metrics**, and **traces**
from HA Core, the Supervisor, and every add-on container, then exports them via
OpenTelemetry (OTLP) to an LGTM stack (Loki, Grafana, Tempo, Mimir) or any
OTLP-compatible backend.

This merges the capabilities of two existing projects into one cohesive add-on:

| Source | What it does | Gap this add-on fills |
|--------|--------------|----------------------|
| [remote_logger](https://github.com/rhizomatics/remote_logger) (custom component) | Captures HA Core's Python logs + events, sends via OTLP or Syslog | Runs *inside* HA Core as a custom component — can't see container logs, supervisor logs, or system metrics |
| [cedricziel/otelcol](https://github.com/cedricziel/ha-addons/tree/main/otelcol) (add-on) | Bare otelcol-contrib binary with self-monitoring only | Ships no receivers for HA logs, container logs, or HA metrics — user must wire everything manually |

**Target user:** HA power users who run (or want to run) a Grafana LGTM stack
and need a turn-key observability pipeline that saturates it without stitching
together multiple components.

## 2. Core Features

### 2.1 Log Collection

| Source | Method | Protocol |
|--------|--------|----------|
| **HA Core logs** (`home-assistant.log`, Python logging) | `filelog` receiver tailing `/config/home-assistant.log` from the `homeassistant_config` mount | OTLP logs |
| **HA Core system_log events** (structured: source file, line number, stack trace, exception count) | `filelog` receiver with multi-line parser for tracebacks | OTLP logs |
| **Supervisor logs** | Docker socket → `docker_stats` receiver or `journald` receiver (TBD during implementation — Docker socket requires disabling protection mode) | OTLP logs |
| **Add-on container logs** (stdout/stderr of every add-on) | Same mechanism as supervisor logs | OTLP logs |

### 2.2 Metric Collection

| Source | Method | Protocol |
|--------|--------|----------|
| **HA Core Prometheus** (`/api/prometheus`) | `prometheus` receiver scraping HA Core's internal metrics endpoint | OTLP metrics |
| **otelcol self-metrics** | `prometheus/internal` receiver (bundled) | OTLP metrics |
| **Container resource metrics** (CPU, memory per add-on) | `docker_stats` receiver (if Docker socket available) or `hostmetrics` receiver | OTLP metrics |
| **Host system metrics** (optional — disk, network, CPU of the HAOS host) | `hostmetrics` receiver (opt-in) | OTLP metrics |

### 2.3 Trace Collection

| Source | Method | Protocol |
|--------|--------|----------|
| **HA Core traces** (if HA exports OTLP traces — TBD; may require HA Core config) | `otlp` receiver | OTLP traces |
| **Add-on traces** (apps instrumented with OTLP SDKs) | `otlp` receiver (gRPC:4317, HTTP:4318) | OTLP traces |

### 2.4 Export

- **Primary target:** OTLP/gRPC or OTLP/HTTP to a user-configured endpoint (Grafana Tempo for traces, Grafana Mimir for metrics, Grafana Loki for logs — all via the OTLP gateway pattern)
- **Secondary:** Debug exporter (for troubleshooting)
- **Configurable batch + memory_limiter processors** to protect against overload

### 2.5 User-Facing Configuration

The user configures:

1. **Where to send data** — one or more OTLP endpoints (the "LGTM stack" address)
2. **What to collect** — toggles for each log/metric/trace source
3. **Authentication** — headers/tokens for the OTLP endpoint
4. **Log level** — standard HA add-on option

The add-on generates the full `otelcol-contrib` config YAML from these options at
startup. Power users can also paste a raw otelcol config to override everything.

## 3. Non-Goals (v0.1.0)

- **Syslog export** — OTLP only. Syslog can be added later if requested.
- **HA event forwarding** (state changes, service calls, registry updates) — log + metric + trace focus only. The remote_logger's rich HA event surface is out of scope for v1.
- **Built-in LGTM stack** — this add-on is the *producer* side. It does not ship Loki/Tempo/Mimir/Grafana itself.
- **Ingress UI** — no web dashboard. Configuration via the HA add-on options panel only.
- **i386 / armv7 support** — `amd64` and `aarch64` only (matching the rest of the ha-apps monorepo).

## 4. Architecture

### 4.1 Container Layout

```
otelcol/
├── config.yaml              # HA add-on manifest
├── Dockerfile               # Multi-stage: pull otelcol-contrib binary + ha base
├── rootfs/
│   └── etc/
│       └── s6-overlay/s6-rc.d/
│           └── otelcol/
│               ├── type      # "longrun"
│               ├── run        # Config merge → exec otelcol-contrib
│               └── finish     # Halt on transient, stay-down on permanent failure
├── translations/
│   ├── en.yaml
│   └── ko.yaml
├── AGENTS.md / CLAUDE.md
├── CHANGELOG.md
├── DOCS.md
├── README.md
├── icon.png
└── logo.png
```

### 4.2 Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ HAOS Host                                                    │
│                                                              │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                 │
│  │ HA Core  │   │Supervisor│   │ Add-on 1 │  ...            │
│  │          │   │          │   │          │                 │
│  │ .log ────┼───┼──────────┼───┼──────────┼──┐              │
│  │ metrics  │   │ stdout   │   │ stdout   │  │              │
│  └──────────┘   └──────────┘   └──────────┘  │              │
│       │                                       │              │
│       │  /config mount (logs)                 │ Docker sock  │
│       │  /api/prometheus (metrics)            │ or journald  │
│       ▼                                       ▼              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 otelcol add-on                        │   │
│  │                                                       │   │
│  │  ┌──────────┐  ┌───────────┐  ┌──────────────────┐  │   │
│  │  │ filelog   │  │ container │  │  prometheus       │  │   │
│  │  │ receiver  │  │ receiver  │  │  receiver          │  │   │
│  │  │ (HA log)  │  │ (stdout)  │  │  (HA metrics)      │  │   │
│  │  └─────┬─────┘  └─────┬─────┘  └────────┬─────────┘  │   │
│  │        │              │                 │             │   │
│  │        ▼              ▼                 ▼             │   │
│  │  ┌─────────────────────────────────────────────────┐  │   │
│  │  │              processors (batch, memory_limiter)  │  │   │
│  │  └─────────────────────┬───────────────────────────┘  │   │
│  │                        │                              │   │
│  │                        ▼                              │   │
│  │  ┌─────────────────────────────────────────────────┐  │   │
│  │  │         exporters (otlp → LGTM, debug)          │  │   │
│  │  └─────────────────────┬───────────────────────────┘  │   │
│  └────────────────────────┼──────────────────────────────┘   │
│                           │                                  │
└───────────────────────────┼──────────────────────────────────┘
                            │ OTLP (gRPC/HTTP)
                            ▼
              ┌─────────────────────────┐
              │    LGTM Stack            │
              │  (Loki / Tempo / Mimir)  │
              │  + Grafana frontend      │
              └─────────────────────────┘
```

### 4.3 otelcol Pipeline Design

```
Receivers:
  filelog/ha:
    include: [/config/home-assistant.log]
    multiline: traceback pattern
    operators: severity parser, timestamp parser

  docker_stats/containers:    # or journald receiver
    endpoint: unix:///var/run/docker.sock
    # Collect stdout/stderr from all containers

  prometheus/ha:
    config:
      scrape_configs:
        - job_name: ha-core
          scrape_interval: 60s
          metrics_path: /api/prometheus
          static_configs:
            - targets: [homeassistant.local:8123]

  prometheus/self:
    # Built-in self-monitoring (scrapes otelcol's own :8888)

  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

Processors:
  batch:       # Batches telemetry before export
  memory_limiter:  # Spikes memory on overload
  resource:    # Tags all data with ha.instance metadata
  attributes:  # Enrich with add-on version, arch

Exporters:
  otlp/lgtm:
    endpoint: <user-configured>
    headers: <user-configured auth>
  debug:       # Optional — enabled via log_level: trace

Extensions:
  health_check:
  pprof:       # Optional debugging
  zpages:      # Optional debugging

Pipelines:
  logs:    filelog → batch → memory_limiter → otlp
  metrics: prometheus → batch → memory_limiter → otlp
  traces:  otlp → batch → memory_limiter → otlp
```

## 5. Configuration Design

### 5.1 `config.yaml` Options Schema

```yaml
options:
  log_level: info
  otlp_endpoint: ""
  otlp_protocol: grpc
  otlp_headers: []
  otlp_tls_insecure: false
  ha_logs_enabled: true
  ha_metrics_enabled: true
  container_logs_enabled: false
  host_metrics_enabled: false
  docker_socket_path: /var/run/docker.sock
  raw_config: ""

schema:
  log_level: list(trace|debug|info|notice|warning|error|fatal)
  otlp_endpoint: str
  otlp_protocol: list(grpc|http)
  otlp_headers: [{name: str, value: str}]
  otlp_tls_insecure: bool
  ha_logs_enabled: bool
  ha_metrics_enabled: bool
  container_logs_enabled: bool
  host_metrics_enabled: bool
  docker_socket_path: str
  raw_config: str?
```

### 5.2 Priority

1. If `raw_config` is non-empty → use it directly as the otelcol config
2. Otherwise → generate config from the structured options above

This gives power users an escape hatch while keeping the default path simple.

### 5.3 Map / Mounts

```yaml
map:
  - type: homeassistant_config
    read_only: true          # We only read logs + scrape metrics
  - type: addon_config
    read_only: false
  - type: share
    read_only: false
  - type: ssl
    read_only: true
```

### 5.4 Ports

```yaml
ports:
  4317/tcp: 4317    # OTLP gRPC (default null — only exposed if user enables)
  4318/tcp: 4318    # OTLP HTTP (default null)
ports_description:
  4317/tcp: OTLP/gRPC receiver (for other add-ons to send traces)
  4318/tcp: OTLP/HTTP receiver (for other add-ons to send traces)
```

## 6. Implementation Plan

### Phase 1: Skeleton (file scaffold)

**Deliverable:** All files exist, container builds, otelcol-contrib starts and passes health check.

- `config.yaml` with options schema, ports, map
- `Dockerfile` — multi-stage: extract otelcol-contrib binary from upstream image → copy into HA base
- `rootfs/etc/s6-overlay/s6-rc.d/otelcol/{type,run,finish}`
- `translations/{en,ko}.yaml`
- `AGENTS.md`, `DOCS.md`, `README.md`, `CHANGELOG.md`
- `icon.png` + `logo.png` (OpenTelemetry logo, or a derived mark)

**Verify:** `docker build .` succeeds, container starts, `curl http://localhost:13133/` returns 200.

### Phase 2: Config generation (the bridge)

**Deliverable:** `run` script reads HA options, generates `/tmp/otelcol-config.yaml`, and launches otelcol-contrib with it.

- Config template logic in the run script (bash + bashio)
- Merge user options into a valid otelcol YAML
- Health check on port 13133

**Verify:** Change `log_level: debug` in add-on options → restart → debug exporter is enabled.

### Phase 3: HA log collection

**Deliverable:** otelcol tails `/config/home-assistant.log` and exports log entries as OTLP.

- `filelog` receiver configured to tail `/config/home-assistant.log`
- Multi-line parser for Python tracebacks
- Severity mapping (HA log levels → OTLP severity numbers)
- Resource attributes tagged with `ha.instance`

**Verify:** Start add-on with a valid `otlp_endpoint` → HA log lines appear in the LGTM backend.

### Phase 4: HA metrics collection

**Deliverable:** otelcol scrapes `/api/prometheus` from HA Core and exports as OTLP metrics.

- `prometheus` receiver scraping HA Core's internal endpoint
- Auth: HA long-lived access token (read from options)
- Resource attributes

**Verify:** HA entity state counts, automation triggers, etc. appear in Mimir/Grafana.

### Phase 5: Container log collection

**Deliverable:** otelcol collects stdout/stderr from supervisor and add-on containers.

- Research phase: Docker socket (`docker_stats` receiver) vs file-based (`journald` receiver) vs Supervisor API polling
- Docker socket approach: requires `protection: false` — document the security trade-off
- Tag each log line with `container.name`, `container.id`

**Verify:** Supervisor logs and other add-on logs appear as distinct streams in Loki.

### Phase 6: Polish & docs

- `DOCS.md` with setup guide for common LGTM stacks (Grafana Cloud, self-hosted Docker Compose)
- Example otelcol receiver configs users can paste via `raw_config`
- HA add-on self-check: verify OTLP endpoint reachability on startup
- Error messages that surface common misconfigurations (wrong port, TLS mismatch, auth failure)

## 7. Design Decisions

### 7.1 Why otelcol-contrib, not a custom Python bridge

- **Correctness:** The OpenTelemetry Collector is the reference implementation for OTLP pipelines. Reimplementing its batch, retry, memory-limiting, and multi-exporter logic in Python is a large maintenance burden.
- **Ecosystem:** Every LGTM-compatible backend already documents its otelcol config. Users can copy-paste exporter blocks from Grafana docs.
- **Extensibility:** Users who outgrow the generated config can use `raw_config` to add any receiver/processor/exporter the contrib distro ships — no code changes needed.

### 7.2 Why `filelog` receiver, not a custom_component like remote_logger

- **No HA Core dependency:** The `filelog` receiver reads the log file from the `homeassistant_config` mount. It doesn't need a custom_component installed inside HA Core.
- **No HACS requirement:** Users don't need to install anything beyond this add-on.
- **Trade-off:** We lose the structured log capture that remote_logger's Python handler provides (source file path, line number, function name extracted by HA's own `LogEntry` logic). The `filelog` approach sees the rendered log line, not the structured record. For v0.1.0 this is acceptable; a future version could optionally bundle the custom component for structured capture.

### 7.3 Why Docker socket for container logs (tentative — Phase 5 research)

- **Completeness:** The Docker socket sees stdout/stderr from every container — supervisor + all add-ons. No per-container configuration needed.
- **Trade-off:** Disabling protection mode gives the add-on broad system access. We document this clearly and make it opt-in (`container_logs_enabled: false` by default).

### 7.4 HA base image, not Debian

- **Consistency:** Every app in this monorepo uses `ghcr.io/home-assistant/base` (Alpine).
- **Size:** Alpine base is ~6 MB vs Debian's ~50 MB. The otelcol-contrib binary is the dominant size factor (~100 MB extracted) — minimizing the base keeps total image size down.
- The upstream otelcol-contrib releases are statically linked Go binaries — they run on musl (Alpine) without issue.

## 8. otelcol-contrib Version Pinning

- **Pin a specific version** of `otelcol-contrib` (e.g., `0.124.0`). Do not use `@latest`.
- The contrib distro includes: `filelog`, `docker_stats`, `prometheus`, `hostmetrics`, `otlp`, `batch`, `memory_limiter`, `resource`, `attributes`, `debug`, `health_check`, `pprof`, `zpages`.
- Bump the pin explicitly in CHANGELOG; test the config merge + health check before merging.

## 9. Boundaries

### Always Do

- **Use bashio for all user-facing output** (`bashio::log.info`, `bashio::config`, etc.)
- **LF line endings everywhere**
- **Validate the generated otelcol config** before launching (catch YAML errors early)
- **Document the health check port** (13133) — it's the signal that the add-on is working
- **Pin the otelcol-contrib version**
- **Use the s6 finish template** from `.agents/workflows/new-app-scaffold.md`

### Ask First

- **Container log collection mechanism** — Docker socket vs journald has security implications. Research both and present trade-offs before committing.
- **HA auth token handling** — scraping `/api/prometheus` requires an HA token. How should the add-on receive it? Options field? Read from `/config/.storage/auth`? Ask before implementing.
- **Icon/logo design** — OpenTelemetry has brand guidelines. Confirm whether a derived mark is acceptable or if we use a generic observability icon.

### Never Do

- **Don't ship a custom_component inside the add-on** for v0.1.0. The `filelog` receiver is the primary log capture path. Bundling remote_logger or a derivative custom component adds install complexity (HA API calls at boot, restart orchestration) for marginal gain in structured log fidelity.
- **Don't require disabling protection mode by default**. Container log collection is opt-in.
- **Don't expose OTLP ports to the host network by default**. They're for intra-add-on communication or explicit opt-in.
- **Don't generate otelcol config in Python** unless bash becomes unmaintainable. The config merge for v0.1.0 is string templating — a Python dependency adds ~50 MB to the image for no benefit.
- **Don't add a web UI / ingress panel**. Configuration is via HA options only.
- **Don't bundle Loki/Tempo/Mimir/Grafana**. This add-on is the producer, not the consumer.

## 10. Success Criteria (v0.1.0)

1. `docker build .` succeeds on both `amd64` and `aarch64`
2. Add-on starts, health check passes (port 13133)
3. With `ha_logs_enabled: true` and a valid `otlp_endpoint`, HA log lines appear in the configured backend
4. With `ha_metrics_enabled: true`, HA Prometheus metrics appear in the configured backend
5. Changing options in the HA UI and restarting the add-on produces the expected config change
6. `yamllint config.yaml translations/*.yaml` passes
7. `shellcheck rootfs/etc/s6-overlay/s6-rc.d/otelcol/*` passes
8. The add-on appears in the HA add-on store UI with translated option descriptions

## 11. References

- [OpenTelemetry Collector Contrib Distro](https://github.com/open-telemetry/opentelemetry-collector-releases)
- [otelcol Filelog Receiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/filelogreceiver)
- [otelcol Prometheus Receiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/prometheusreceiver)
- [otelcol Docker Stats Receiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/dockerstatsreceiver)
- [cedricziel/ha-addons otelcol](https://github.com/cedricziel/ha-addons/tree/main/otelcol) — reference add-on structure
- [rhizomatics/remote_logger](https://github.com/rhizomatics/remote_logger) — reference for HA log capture logic
- [Grafana LGTM Stack](https://grafana.com/products/cloud/) — primary export target
