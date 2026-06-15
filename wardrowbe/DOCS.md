# Wardrowbe — Documentation

## Architecture

All services run in a single container under s6-overlay v3:

| Service    | Role                                          | Port |
|------------|-----------------------------------------------|------|
| PostgreSQL | Database (items, outfits, users, preferences) | 5432 |
| Redis      | Job queue + cache                             | 6379 |
| Backend    | FastAPI API server                            | 8000 |
| Worker     | arq background worker (AI tagging, cron)      | —    |
| Frontend   | Next.js web UI                                | 3000 |
| Nginx      | Reverse proxy (single entry point)            | 8099 |

## Configuration

### AI Service

Wardrowbe needs an OpenAI-compatible API for vision (image tagging) and text (outfit recommendations).

**Ollama (recommended — free, local):**

```yaml
ai_base_url: "http://homeassistant.local:11434/v1"
ai_api_key: ""
ai_vision_model: "gemma3:latest"
ai_text_model: "gemma3:latest"
```

Pull the model first: `ollama pull gemma3`

**OpenAI (paid):**

```yaml
ai_base_url: "https://api.openai.com/v1"
ai_api_key: "sk-..."
ai_vision_model: "gpt-4o"
ai_text_model: "gpt-4o"
```

### All Options

| Option | Default | Description |
|---|---|---|
| `ai_base_url` | `http://homeassistant.local:11434/v1` | OpenAI-compatible API endpoint |
| `ai_api_key` | *(empty)* | API key (not needed for Ollama) |
| `ai_vision_model` | `gemma3:latest` | Vision model for image analysis |
| `ai_text_model` | `gemma3:latest` | Text model for recommendations |
| `dev_login` | `true` | Dev login toggle (see Authentication) |
| `external_url` | *(empty)* | Public URL for OIDC (e.g. `https://wardrowbe.example.com`) |
| `oidc_issuer_url` | *(empty)* | OIDC provider URL |
| `oidc_client_id` | *(empty)* | OIDC client ID |
| `oidc_client_secret` | *(empty)* | OIDC client secret |
| `oidc_mobile_client_id` | *(empty)* | OIDC public client ID for mobile app |
| `postgres_user` | `wardrobe` | PostgreSQL user |
| `postgres_password` | `wardrobe` | PostgreSQL password |
| `postgres_db` | `wardrobe` | Database name |
| `secret_key` | *(auto)* | Backend JWT secret |
| `nextauth_secret` | *(auto)* | NextAuth session secret |
| `ntfy_server` | *(empty)* | ntfy.sh push notification server |
| `ntfy_token` | *(empty)* | ntfy.sh token |
| `mattermost_webhook_url` | *(empty)* | Mattermost webhook |
| `backup_enabled` | `true` | Daily `pg_dump` into `/share/wardrowbe/backups/` |
| `backup_retention_days` | `7` | Delete dumps older than this (0 = keep forever) |
| `backup_hour` | `3` | Hour of day (0–23, container TZ) when the dump runs |

## Authentication

### Ingress (default)

By default, Wardrowbe runs in **dev login** mode. You enter any email/name to create an account. This is safe because HA ingress already requires HA login.

### OIDC (external domain)

OIDC does **not** work through HA ingress — ingress URLs contain dynamic session tokens that can't be pre-registered as OIDC redirect URIs.

To use OIDC, expose the addon via a reverse proxy on its own domain:

| Setting | Example |
|---|---|
| `dev_login` | `false` |
| `external_url` | `https://wardrowbe.your-domain.tld` |
| `oidc_issuer_url` | `https://auth.your-domain.tld` |
| `oidc_client_id` | `wardrowbe` |
| `oidc_client_secret` | `your-secret` |

Then register this redirect URI with your OIDC provider:

```
https://wardrowbe.your-domain.tld/api/auth/callback/oidc
```

The exact URI is also printed in the addon startup log.

### Mobile App Setup

The wardrowbe mobile app uses a **public OIDC client** (no secret, PKCE only).

1. Create a second client in your OIDC provider (e.g. `wardrowbe-mobile`)
2. Set it as a **public client** (no client secret)
3. Add redirect URI: `wardrowbe://`
4. In the addon config, set `oidc_mobile_client_id` to the new client ID

| Setting | Example |
|---|---|
| `oidc_mobile_client_id` | `wardrowbe-mobile` |

**Auth mode logic:**

| `dev_login` | OIDC set | Result |
|:-----------:|:--------:|--------|
| `true` | No | Dev Login (default) |
| any | Yes | OIDC (auto-switch) |
| `false` | No | ⚠️ Forced back to Dev Login |

**Ingress and external domain can coexist.** Ingress uses dev login (behind HA auth), the external domain uses OIDC. Both share the same data.

## Data & Storage

| HA Mount | Container Path | Purpose | In HA snapshot? |
|---|---|---|:---:|
| `addon_config` | `/config/.secret_key`, `.nextauth_secret` | Auto-generated secrets | ✅ (tiny) |
| `data` | `/data/photos/` | **Clothing photos & thumbnails** | ✅ (in addon snapshot) |
| `share` | `/share/wardrowbe/backups/` | DB backup exports (daily `pg_dump`) | HA share snapshot |
| `data` | `/data/postgres/data/` | PostgreSQL cluster | ❌ excluded |
| `data` | `/data/redis/` | Redis AOF + RDB | ❌ excluded |

Photos are **private to this addon** — they do *not* appear in the HA
Media Browser. If you want them shared across HA, set up your own
symlink under `/media/` manually.

> ⚠️ Heads-up — photos sit under `/data/`, so they're included in every
> HA add-on snapshot. A wardrobe with a few hundred items can push snapshot
> size into the hundreds of MB. If that matters to you, either snapshot
> less often or move the photo dir manually (see `.agents/storage-layout.md`).

### Backup size & DB dumps

The live PostgreSQL cluster and Redis AOF/RDB live under `/data/` and are
explicitly excluded from HA add-on snapshots via `backup_exclude` —
otherwise a few thousand clothing items would balloon every snapshot.

Instead, the addon runs a daily `pg_dump` (see `backup_*` options above)
into `/share/wardrowbe/backups/wardrowbe-<timestamp>.sql.gz`. `/share/`
is part of HA's wider snapshot, so these dumps **are** included in HA
backups — which is what you actually want.

To restore: copy a `.sql.gz` back, then from the addon shell:

```bash
gunzip -c /share/wardrowbe/backups/wardrowbe-YYYYMMDDTHHMMSS.sql.gz \
  | su-exec postgres psql -d wardrobe
```

### Migrating to a new HA instance

1. Copy `/addon_configs/03f32180_wardrowbe/` → secrets, and `/data/photos/`
   → all clothing photos
2. Copy a recent `wardrowbe-*.sql.gz` from `/share/wardrowbe/backups/`
3. On the new HA, install the addon, then restore the SQL dump (see the
   "Backup size & DB dumps" section above for the restore command).

Secrets are auto-generated on first run and persisted in `addon_config`.
If you set `secret_key` or `nextauth_secret` explicitly in the addon
config, those take precedence.

## MCP server (LLM tool access)

The MCP server used to ship inside this add-on. As of v1.3.1 it lives
in a separate repository,
[`saya6k/mcp-wardrowbe`](https://github.com/saya6k/mcp-wardrowbe),
distributed as a standalone Python package (`pip install wardrowbe-mcp`).

It connects to **any** Wardrowbe instance — this add-on, a self-hosted
deployment behind a reverse proxy, or a cloud-hosted Wardrowbe — over
the REST API, with the same dev / OIDC auth modes. See that repo's
README for install and configuration.

## Troubleshooting

**Startup log shows healthy boot sequence:**

```
[backend]  ensuring database and role exist …
[backend]  running database migrations …
[backend]  starting uvicorn on port 8000 …
[frontend] starting Next.js on port 3000 …
[worker]   starting arq worker …
```

**AI features not working:**
Verify your Ollama/OpenAI endpoint is reachable from the HA host.
Check worker logs for errors.

**OIDC callback goes to 127.0.0.1:**
Set `external_url` to your public domain in the addon config.

**"Development Mode" banner won't go away:**
Configure OIDC — `dev_login` is auto-disabled when OIDC is set.

**Blank page in ingress:**
Hard-refresh (Ctrl+Shift+R). If persistent, check the addon log for nginx errors.

**JWT decryption errors after restart:**
Secrets are now persisted in `/config/`. If you see this after an upgrade from an older version, log out and log back in.
