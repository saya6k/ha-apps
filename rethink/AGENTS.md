# AGENTS.md

Guidance for AI coding agents working on this repository. Detailed history
lives in `CHANGELOG.md` — read that for the *why* behind older decisions.

## What this repo is

A single Home Assistant **app** packaging
[`anszom/rethink`](https://github.com/anszom/rethink) so that supported LG
ThinQ appliances talk to Home Assistant over MQTT instead of LG's cloud. The
whole repo *is* the app. As of **0.1.0** the upstream version is pinned to
`054407c` (2026-05-11). rethink itself is GPL-2.0; this packaging layer
follows suit.

## Layout

```
config.yaml / build.yaml / Dockerfile     app packaging
rootfs/etc/s6-overlay/s6-rc.d/            rethink longrun service + s6 wiring
translations/en.yaml + ko.yaml            option UI strings
CHANGELOG.md / DOCS.md / README.md        user-facing docs (HA renders the first two)
```

Follow the [Piper app](https://github.com/home-assistant/addons/tree/master/piper)
for s6 / healthcheck conventions; deviate only with reason. CI / build is
delegated to [`hassio-addons/workflows`](https://github.com/hassio-addons/workflows)
reusable workflows — `.github/workflows/{ci,deploy,lock,stale}.yaml` are thin
callers; do not duplicate their logic locally.

## Documentation layout

| File | Role | Length target |
| ---- | ---- | ------------- |
| `README.md`        | One-paragraph blurb. Keep tiny. | ~15 lines |
| `DOCS.md`          | User-facing options + DNS setup. HA renders it as the "Documentation" tab. | ≤ ~80 lines |
| `AGENTS.md`        | This file — agent/dev guidance for the *current* code. Symlinked as `CLAUDE.md`. | ~100 lines |
| `CHANGELOG.md`     | Per-version headline. HA renders this in the app UI. 5–15 lines per version. | — |
| `notes/`           | Local dev decision logs / postmortems. **Gitignored** — never link from shipped docs. | free-form |
| `translations/<lang>.yaml` | Option UI labels/descriptions. | — |

**CHANGELOG = what changed**, **AGENTS = current state**,
**DOCS = user-visible knobs**, **`notes/` = why**.

## How the s6 service works

`rootfs/etc/s6-overlay/s6-rc.d/rethink/run` is a long-run service. It:

1. Validates the MQTT service is available via `bashio::services.available`.
2. Reads MQTT host / port / user / pass from the Supervisor service API.
3. Renders `/data/config.json` from `/data/options.json` + the MQTT creds via
   `jq`. **Always re-rendered on each boot** — editing `/data/config.json` by
   hand is futile, change add-on options instead.
4. `exec`s `node dist/rethink-cloud.js /data/config.json`.

`/data/{ca.key, ca.cert, state/}` persist across rebuilds. `state/` is in
`backup_exclude` because it can be large and is recreated on next pair.

## Options → rethink config.json

| Add-on option       | rethink config field                                     |
| ------------------- | -------------------------------------------------------- |
| `hostname`          | `hostname` (top-level)                                   |
| `discovery_prefix`  | `homeassistant.discovery_prefix`                         |
| `rethink_prefix`    | `homeassistant.rethink_prefix`                           |
| `log_levels`        | `log`                                                    |
| (Supervisor MQTT)   | `homeassistant.{mqtt_url, mqtt_user, mqtt_pass}`         |

`hostname` *must* be a real DNS A record. Raw IPs and mDNS names are rejected
by rethink at startup.

## Pins & build

- `Dockerfile` `ARG RETHINK_REV` pins the upstream commit SHA. Bump when
  upstream adds device support or fixes.
- `build.yaml` uses HA's Alpine base per-arch — rethink upstream already
  builds on Alpine.
- `HEALTHCHECK` probes the management UI on port 44401.
- `image:` line in `config.yaml` is staged-commented; uncomment once
  `deploy.yaml` has actually published amd64 + aarch64 tags to GHCR so
  users get prebuilt images instead of a long local build.

## Don'ts

- Don't add a Matter exposure path. Decided 2026-05-24 to stay MQTT-only;
  forking rethink to embed `matter.js` is weeks of work for marginal gain
  over chaining through `Luligu/matterbridge` downstream (mentioned in DOCS
  only).
- Don't default bridge mode on. It requires a user LG OAuth login and adds
  a single point of failure for the device's cloud connectivity. Documented
  in DOCS as a reverse-engineering capture tool only.
- Don't try to handle DNS hijacking inside the add-on. That's the user's
  Pi-hole / AdGuard responsibility — documented in DOCS, not implemented
  here.
- Don't expose ingress for the management UI. Port 44401 serves an
  unauthenticated HTML/WebSocket app that won't play nice with an ingress
  path prefix — expose via `webui` only.
- Don't add armv7 / i386 without confirming Node + rethink deps build cleanly
  on those archs.
- Don't forget the `chmod +x` block in `Dockerfile` when adding a new s6
  script.
