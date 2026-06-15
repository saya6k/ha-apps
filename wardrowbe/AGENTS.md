# AGENTS.md

Guidance for AI coding agents. **Keep this file under ~100 lines** —
describe the *current shape* only. *Why* lives under `.agents/` (gitignored;
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

## Git / repo tracking

Part of the `ha-apps` monorepo — one git repo at the root, no per-app
`.git` checkouts. Tracking is **stage-gated** by the root `.gitignore`:
only `stage: stable` add-ons are committed; experimental ones are
gitignored and stay local-only. Promote one by setting `stage: stable`
in `config.yaml`, deleting its line from the root `.gitignore`, then
`git add` it.

**This add-on:** tracked (`stage: stable`).

## Layout

```
config.yaml / Dockerfile                  app packaging
rootfs/etc/cont-init.d/                   00-init.sh, 10-postgres-persist.sh
rootfs/etc/s6-overlay/s6-rc.d/<svc>/      postgres redis backend worker frontend
                                          nginx backup (each: type/run/finish)
rootfs/etc/nginx/nginx.conf               reverse proxy + HA-ingress sub_filter
translations/{en,ko}.yaml                 option UI strings
.agents/                                    decision logs (gitignored)
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
| `.agents/` | *Why* / decision logs. Gitignored. | free-form |

## Storage

| Mount | Path | In HA snapshot? |
| --- | --- | --- |
| `addon_config` | `/config/.*` (secrets) | yes (tiny) |
| `addon_config` | `/config/photos/` (clothing photos) | yes (can grow large) |
| `data` | `/data/postgres/data/`, `/data/redis/` | **excluded** (`backup_exclude`) |
| `share` | `/share/wardrowbe/backups/` (daily `pg_dump`) | HA share snapshot |

Rationale: `.agents/storage-layout.md`.

## Auth modes

Dev login (any email) and OIDC — mutually exclusive in practice because
OIDC can't traverse HA ingress. Precedence + `_is_dev_mode()`:
`.agents/auth-modes.md`.

## Branding assets

`icon.png` / `logo.png` come from the upstream wardrowbe mark
(`Anyesh/wardrowbe` → `frontend/public/icon-512.png` + `logo.svg`, MIT,
© 2026 Anish S.). `icon.png` is that mark downscaled to 256×256; `logo.png`
pairs it with a "wardrowbe" wordmark set in Avenir Next. Keep `NOTICE` in
lockstep if you swap them.

## Build & pinning

Dockerfile `ARG WARDROWBE_VERSION` pins upstream tag (build.yaml is gone —
deprecated by Supervisor 2026.04; base image + labels now live in the
Dockerfile). Two `sed` patches into the frontend at build time; worker shim
auto-detects v1.2.1 vs v1.2.2+ `WorkerSettings`. Pipeline:
`.agents/build-and-pinning.md`.

## Sanity checks before PR

- `yamllint config.yaml translations/*.yaml`
- `shellcheck rootfs/etc/cont-init.d/*.sh rootfs/etc/s6-overlay/s6-rc.d/*/run`
- `docker build .`  (or `--build-arg BUILD_FROM=…` to override the base)
- Backend: `curl -fsS http://127.0.0.1:8099/api/v1/health`

## Don'ts (always paired with the alternative)

Each line: **don't X → do Y** — see notes for the reasoning.

- **PGDATA at `/data/postgres/` with `backup_exclude`** (not `/config/`); HA-snapshotted dumps come from `backup` → `/share/`. — `.agents/storage-layout.md`
- **Add `options:`/`schema:` keys additively** with defaults; rename/drop only with a dual-read deprecation window. — `.agents/config-evolution.md`
- **`chmod +x` for s6 files goes in the Dockerfile `find … -exec` block** — survives rootfs `COPY` on hosts that strip exec bits. — `.agents/architecture-non-goals.md`
- **`arch:` stays `amd64` + `aarch64`** — sharp/asyncpg/Next.js standalone wheels not validated elsewhere. — `.agents/architecture-non-goals.md`
- **Pin every version explicitly**, document bumps in CHANGELOG; never `@latest`. — `.agents/architecture-non-goals.md`
- **Keep `images.unoptimized: true` in the Next.js patch** — backend serves images directly; nginx must not proxy `/_next/image`. — `.agents/architecture-non-goals.md`
