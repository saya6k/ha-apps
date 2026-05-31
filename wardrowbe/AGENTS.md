# AGENTS.md

Guidance for AI coding agents. **Keep this file under ~100 lines** —
describe the *current shape* only. *Why* lives under `notes/` (gitignored;
AGENTS may name files there, README/DOCS/CHANGELOG must not).
CHANGELOG.md has the *what changed*.

## What this repo is

A single Home Assistant **app** packaging
[`Anyesh/wardrowbe`](https://github.com/Anyesh/wardrowbe). Seven
processes (PostgreSQL, Redis, FastAPI backend, arq worker, Next.js
frontend, nginx, daily `backup`) in one s6-overlay v3 container.

MCP server lives in a separate repo
([`saya6k/mcp-wardrowbe`](https://github.com/saya6k/mcp-wardrowbe)) as a
standalone PyPI package; it's no longer bundled here. Run it alongside
the add-on (or against any other Wardrowbe instance) if you want LLM
tool access.

## Layout

```
config.yaml / build.yaml / Dockerfile     app packaging
rootfs/etc/cont-init.d/                   00-init.sh, 10-postgres-persist.sh
rootfs/etc/s6-overlay/s6-rc.d/<svc>/      postgres redis backend worker frontend
                                          nginx backup (each: type/run/finish)
rootfs/etc/nginx/nginx.conf               reverse proxy + HA-ingress sub_filter
translations/{en,ko}.yaml                 option UI strings
notes/                                    decision logs (gitignored)
CHANGELOG.md / DOCS.md / README.md        user-facing docs
```

CI / build delegated to `hassio-addons/workflows` reusable workflows —
`.github/workflows/*.yaml` are thin callers.

## Documentation layout

| File | Role | Length |
| --- | --- | --- |
| `README.md` | One-paragraph blurb. | ~15 |
| `DOCS.md` | User-facing options + auth + storage. HA renders. | ≤ ~200 |
| `AGENTS.md` | This file — *current shape*. Symlinked `CLAUDE.md`. | ≤ ~100 |
| `CHANGELOG.md` | Per-version *what changed*. HA renders. | 5–15 / ver |
| `notes/` | *Why* / decision logs. Gitignored. | free-form |

## Storage

| Mount | Path | In HA snapshot? |
| --- | --- | --- |
| `addon_config` | `/config/.*` (secrets) | yes (tiny) |
| `addon_config` | `/config/photos/` (clothing photos) | yes (can grow large) |
| `data` | `/data/postgres/data/`, `/data/redis/` | **excluded** (`backup_exclude`) |
| `share` | `/share/wardrowbe/backups/` (daily `pg_dump`) | HA share snapshot |

Rationale: `notes/storage-layout.md`.

## Auth modes

Dev login (any email) and OIDC — mutually exclusive in practice because
OIDC can't traverse HA ingress. Precedence + `_is_dev_mode()`:
`notes/auth-modes.md`.

## Build & pinning

`build.yaml` `WARDROWBE_VERSION` pins upstream tag. Two `sed` patches
into the frontend at build time; worker shim auto-detects v1.2.1 vs
v1.2.2+ `WorkerSettings`. Pipeline: `notes/build-and-pinning.md`.

## Sanity checks before PR

- `yamllint config.yaml build.yaml translations/*.yaml`
- `shellcheck rootfs/etc/cont-init.d/*.sh rootfs/etc/s6-overlay/s6-rc.d/*/run`
- `docker build --build-arg BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest .`
- Backend: `curl -fsS http://127.0.0.1:8099/api/v1/health`

## Don'ts (always paired with the alternative)

Each line: **don't X → do Y** — see notes for the reasoning.

- **PGDATA at `/data/postgres/` with `backup_exclude`** (not `/config/`); HA-snapshotted dumps come from `backup` → `/share/`. — `notes/storage-layout.md`
- **Add `options:`/`schema:` keys additively** with defaults; rename/drop only with a dual-read deprecation window. — `notes/config-evolution.md`
- **`chmod +x` for s6 files goes in the Dockerfile `find … -exec` block** — survives rootfs `COPY` on hosts that strip exec bits. — `notes/architecture-non-goals.md`
- **`arch:` stays `amd64` + `aarch64`** — sharp/asyncpg/Next.js standalone wheels not validated elsewhere. — `notes/architecture-non-goals.md`
- **Pin every version explicitly**, document bumps in CHANGELOG; never `@latest`. — `notes/architecture-non-goals.md`
- **Keep `images.unoptimized: true` in the Next.js patch** — backend serves images directly; nginx must not proxy `/_next/image`. — `notes/architecture-non-goals.md`
