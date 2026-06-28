# Changelog

Releases from the next version onward are tracked in
[ha-app-* releases](https://github.com/saya6k/ha-app-otelcol/releases).


## [0.3.10](https://github.com/saya6k/ha-app-otelcol/releases/tag/v0.3.10)

## What's Changed

* fix: drop UNSPECIFIED-severity records from the debug exporter pipeline (#12) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-otelcol/compare/v0.3.9...v0.3.10

## [0.3.9](https://github.com/saya6k/ha-app-otelcol/releases/tag/v0.3.9)

## What's Changed

* fix: split logs pipeline so debug exporter respects log_level (#11) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-otelcol/compare/v0.3.8...v0.3.9

## [0.3.8](https://github.com/saya6k/ha-app-otelcol/releases/tag/v0.3.8)

## What's Changed

* fix: decouple log_level from OTLP severity filtering (#9) @saya6k
* docs(otelcol): update host_metrics_enabled description (#8) @saya6k
* fix: handle SIGTERM gracefully to flush pending telemetry (#7) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-otelcol/compare/v0.3.7...v0.3.8

## [0.3.7](https://github.com/saya6k/ha-app-otelcol/releases/tag/v0.3.7)

## What's Changed

* fix: fall back to /logs polling for add-ons without journald (#6) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-otelcol/compare/v0.3.6...v0.3.7

## [0.3.6](https://github.com/saya6k/ha-app-otelcol/releases/tag/v0.3.6)

## What's Changed

* fix: filter collected log records by severity based on log_level (#5) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-otelcol/compare/v0.3.5...v0.3.6

## [0.3.5](https://github.com/saya6k/ha-app-otelcol/releases/tag/v0.3.5)

## What's Changed

* docs: update ha_logs_enabled description to reflect Supervisor API streaming (#4) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-otelcol/compare/v0.3.4...v0.3.5

## [0.3.4](https://github.com/saya6k/ha-app-otelcol/releases/tag/v0.3.4)

## What's Changed

* fix: replace deprecated filelog/ha with Supervisor API log streaming (#2) @saya6k
* fix: apply log_level to otelcol internal telemetry output (#3) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-otelcol/compare/v0.3.3...v0.3.4

## [0.3.3](https://github.com/saya6k/ha-app-otelcol/releases/tag/v0.3.3)

## What's Changed

* fix: switch container log collection to streaming /logs/follow endpoint (#1) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-otelcol/compare/v0.3.2...v0.3.3

## [0.3.2](https://github.com/saya6k/ha-app-otelcol/releases/tag/v0.3.2)

Re-dispatch after notify job fix.

## [0.3.1](https://github.com/saya6k/ha-apps/compare/otelcol-v0.3.0...otelcol-v0.3.1) (2026-06-28)


### Bug Fixes

* **otelcol:** remove unused addon_config mount to fix HA backup failure ([#475](https://github.com/saya6k/ha-apps/issues/475)) ([43ef1c2](https://github.com/saya6k/ha-apps/commit/43ef1c246081ccba970c6994477c423189b9cbd9))

## [0.3.0](https://github.com/saya6k/ha-apps/compare/otelcol-v0.2.3...otelcol-v0.3.0) (2026-06-27)


### Features

* **otelcol:** add lifecycle traces, entity/event metrics to HA bridge ([8855e66](https://github.com/saya6k/ha-apps/commit/8855e66b685c17ddd818fa3ed76fe25dc3cf1ed6))
* **otelcol:** add lifecycle traces, entity/event metrics to HA bridge ([#469](https://github.com/saya6k/ha-apps/issues/469)) ([ea43d1c](https://github.com/saya6k/ha-apps/commit/ea43d1c148b708d7df958d323bf27e0fcedc1601))

## [0.2.3](https://github.com/saya6k/ha-apps/compare/otelcol-v0.2.2...otelcol-v0.2.3) (2026-06-23)


### Build System

* **otelcol:** promote to stable — remove stage: experimental ([72f5da2](https://github.com/saya6k/ha-apps/commit/72f5da25bb75eb1b8d708977728847eeeb5876e1))
* **otelcol:** promote to stable — remove stage: experimental ([#426](https://github.com/saya6k/ha-apps/issues/426)) ([7339a7c](https://github.com/saya6k/ha-apps/commit/7339a7cd18c2ed459b051bb89370fca67b29824c))

## [0.2.2](https://github.com/saya6k/ha-apps/compare/otelcol-v0.2.1...otelcol-v0.2.2) (2026-06-23)


### Bug Fixes

* **repo:** replace {,**} with explicit dir+glob rules in all AppArmor profiles ([6903c13](https://github.com/saya6k/ha-apps/commit/6903c1329a95f5833114dd3aabdc9849fbf8e7b8))

## [0.2.1](https://github.com/saya6k/ha-apps/compare/otelcol-v0.2.0...otelcol-v0.2.1) (2026-06-23)


### Bug Fixes

* **otelcol:** add custom AppArmor profile covering /init, /bin, /opt/bridge-venv ([#376](https://github.com/saya6k/ha-apps/issues/376)) ([28272ce](https://github.com/saya6k/ha-apps/commit/28272ce033250a20fbcb9eeed65b06723ba4424e))
* **otelcol:** allow exec on /package/** for s6-overlay-suexec ([#377](https://github.com/saya6k/ha-apps/issues/377)) ([d19f1bf](https://github.com/saya6k/ha-apps/commit/d19f1bfc917e61861b18a1bf478695abec231782))
* **otelcol:** allow exec on /run/s6/** for s6-overlay stage0 ([#378](https://github.com/saya6k/ha-apps/issues/378)) ([f5e2d22](https://github.com/saya6k/ha-apps/commit/f5e2d22563068f00636dcbe40f6e591af5d6af98))
* **otelcol:** rewrite AppArmor profile using official HA example pattern ([#379](https://github.com/saya6k/ha-apps/issues/379)) ([1251318](https://github.com/saya6k/ha-apps/commit/1251318eebcf76bb81194bdc688766a5643d56bd))

## [0.2.0](https://github.com/saya6k/ha-apps/compare/otelcol-v0.1.0...otelcol-v0.2.0) (2026-06-22)


### Features

* **otelcol:** add Python HA-API bridge for metrics, logs, and traces ([a30672d](https://github.com/saya6k/ha-apps/commit/a30672daec122d3186214e9a6a203331c07fb3df))
* **otelcol:** collect HA Core logs via filelog receiver ([b221b67](https://github.com/saya6k/ha-apps/commit/b221b6782c72a5946a5eb29ef8318ab60b6a941f))
* **otelcol:** generate collector config with OTLP receiver/exporter ([2f293f2](https://github.com/saya6k/ha-apps/commit/2f293f281e6ec8e481f4ad056b78def8ea4ab078))
* **otelcol:** harden with apparmor profile, auth_api, and ingress zpages ([2246701](https://github.com/saya6k/ha-apps/commit/224670179676d2005adf4d741308ededeb436ae3))
* **otelcol:** opt-in container log + stats via Supervisor API ([b120a71](https://github.com/saya6k/ha-apps/commit/b120a7117fc5597fd82f6a3ab53a6dc0bf015b79))
* **otelcol:** real icon/logo + setup docs and changelog ([95b6980](https://github.com/saya6k/ha-apps/commit/95b69807bb51218f4c4e411055be14fae5409a63))
* **otelcol:** replace placeholder icon/logo with official OTel artwork ([8cbc73d](https://github.com/saya6k/ha-apps/commit/8cbc73d8d1e93830701723e3309a65bedc1eddf1))


### Bug Fixes

* **otelcol:** add aiodns dep and fallback resolver for bridge ([4b676dd](https://github.com/saya6k/ha-apps/commit/4b676ddf9b816e9b5bd13ccb601846306edad8ae))
* **otelcol:** correct ingress_entry path and stop container-log feedback loop ([56baf9a](https://github.com/saya6k/ha-apps/commit/56baf9a4c6324b44c4e1aaf2c86ed08fe48b7efc))
* **otelcol:** disable AppArmor to resolve /init permission denied on startup ([2036952](https://github.com/saya6k/ha-apps/commit/2036952108527fd970f24dee163b796f099ac312))
* **otelcol:** fix Observation import in gauge callbacks ([9ce759c](https://github.com/saya6k/ha-apps/commit/9ce759c6e740d1326a7f14f8ad6ab52fb2b87ca2))
* **otelcol:** remove incorrect apparmor: otelcol key from config.yaml ([4dcf46c](https://github.com/saya6k/ha-apps/commit/4dcf46c13cd624f6966281ca28dfe6abea8c7a22))
* **otelcol:** replace custom AppArmor profile with HA default ([1a9bbb3](https://github.com/saya6k/ha-apps/commit/1a9bbb30374188c535602ec35ed0e2288c34de87))
* **otelcol:** sanitize non-ASCII unit_of_measurement before creating OTel gauge ([528c89e](https://github.com/saya6k/ha-apps/commit/528c89e3e4fdef796d7f84a481319f9b327e9e2f))
* **otelcol:** set ingress_entry to /debug/pipelinez ([db6520d](https://github.com/saya6k/ha-apps/commit/db6520db00697004df2fa61e2f06a30812701a8d))
* **otelcol:** wire s6 bundle registration and fix multi-arch Dockerfile ([52f6472](https://github.com/saya6k/ha-apps/commit/52f6472cdaab7ff5422a7a1d45037e7cdcc0288a))


### Documentation

* **otelcol:** reorder README shields — Show add-on below for-the-badge badges ([8cf7ec9](https://github.com/saya6k/ha-apps/commit/8cf7ec92011a4e5aad7ad7ace6aa5c1a7c6226c1))
* **otelcol:** rewrite README with shields, restructure DOCS to match repo style ([d84c4b8](https://github.com/saya6k/ha-apps/commit/d84c4b8758644e080f2beece08624d7265515e75))


### CI

* **otelcol:** register in CI path filters and update AGENTS docs ([c29ebdf](https://github.com/saya6k/ha-apps/commit/c29ebdff08e17395c867663c54d6e91260ebeffa))
* **repo:** tighten markdownlint scope and disable style-only rules ([9fe6f97](https://github.com/saya6k/ha-apps/commit/9fe6f97b9fee3e1c010f2ee534b36ea8de2a74fe))

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
