# otelcol add-on — implementation plan (v0.1.0)

## Architecture

```
HA WebSocket/REST ─(Python bridge)→ OTLP/HTTP localhost:4318 ─┐  (logs+metrics+traces)
   states→metrics · system_log/events→logs · context graph→traces
HA log file ──────────────────────→ filelog receiver ─────────┤
Supervisor API (opt-in, all add-ons logs+stats) ─(bridge)─────┤→ memory_limiter → batch
otelcol self-metrics ─────────────→ prometheus/internal ──────┤   → resource → otlp/lgtm → LGTM
External add-on traces (opt-in) ──→ otlp receiver ────────────┘
                                      + zpages via HA-auth ingress
```

Two s6 services in one container: **otelcol** (Collector hub) + **ha-bridge** (Python, HA→OTLP).
The bridge pushes OTLP/HTTP to `localhost:4318`; otelcol handles batch/memory/export.

## Key design decisions

- **Metrics:** bridge reads `state_changed` via WebSocket + seeds from `/api/states`; no `prometheus:` integration required.
- **Logs:** `filelog` tails `home-assistant.log` (full stream) + bridge forwards structured `system_log_event` records.
- **Traces:** bridge maps HA `context.id→trace_id`, `context.parent_id→parent_span` across `call_service/automation_triggered/script_started/state_changed`.
- **Container logs/stats:** Supervisor API (`hassio_api: true`, `hassio_role: manager`) — no raw Docker socket, protection mode stays ON.
- **AppArmor:** custom `apparmor.txt` named profile; never `apparmor: true` (would ignore the custom file).
- **Ingress:** zpages on `:55679` behind HA-auth proxy; pprof on `127.0.0.1` only; OTLP ports default `null`.

## Tasks

| ID | Slice | Status |
|----|-------|--------|
| 0 | Feature branch + scaffold commit | ✅ done |
| A | Security hardening (apparmor.txt, ingress, auth_api) | pending |
| B | Config generator + OTLP receiver/exporter | pending |
| C | HA raw log collection via filelog | pending |
| D | Python HA-API bridge (D1 connect · D2 metrics · D3 events/logs · D4 traces) | pending |
| E | Container & Supervisor logs/stats via Supervisor API (opt-in) | pending |
| F | Icon/logo, polish, docs | pending |

## Dependency order

`0` → `A` → `B` → `C` & `D` (parallel) → `E` → `F`

## Checkpoints (human review required)

- After A — AppArmor profile + ingress wiring
- After B — generator output shape + bridge OTLP ingestion point
- After D — full MVP (logs+metrics+traces); decide ship vs continue to E/F
- Before E — confirm `hassio_role: manager` scope; review RBAC trade-off

## Commits (release-please, scope `otelcol`)

- `feat(otelcol): harden with apparmor profile, auth_api, and ingress zpages` (A)
- `feat(otelcol): generate collector config with OTLP receiver/exporter` (B)
- `feat(otelcol): collect HA Core logs via filelog receiver` (C)
- `feat(otelcol): add Python HA-API bridge for metrics, logs, and traces` (D)
- `feat(otelcol): opt-in container log + stats via Supervisor API` (E)
- `feat(otelcol): real icon/logo + setup docs and translations` (F)
