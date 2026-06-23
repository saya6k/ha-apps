#!/usr/bin/with-contenv bashio
# shellcheck shell=bash
set -euo pipefail

bashio::log.info "Initializing Wardrowbe add-on …"

# ── Helper: write a value into the s6 container-environment directory ─────
S6_ENV_DIR=/var/run/s6/container_environment

set_env() {
  printf '%s' "$2" > "${S6_ENV_DIR}/$1"
}

# ══════════════════════════════════════════════════════════════════════════
# Storage layout:
#
#   /config/               (addon_config — private to this addon)
#     ├── .nextauth_secret   auto-generated NextAuth session secret
#     └── .secret_key        auto-generated backend JWT secret
#
#   /data/                 (data — private to this addon)
#     ├── photos/            clothing photos + thumbnails (in addon snapshot)
#     ├── postgres/data/     PostgreSQL cluster (backup_exclude'd)
#     └── redis/             Redis AOF + RDB (backup_exclude'd)
#
#   /share/wardrowbe/      (share — HA-wide, included in HA backups)
#     └── backups/           daily pg_dump output
# ══════════════════════════════════════════════════════════════════════════

# ── 1. Read options from HA config and expose as env vars ─────────────────
PG_USER="$(bashio::config  'postgres_user')"
PG_PASS="$(bashio::config  'postgres_password')"
PG_DB="$(bashio::config    'postgres_db')"
PG_PORT=5432
REDIS_PORT=6379
BACKEND_PORT=8000
FRONTEND_PORT=3000

set_env POSTGRES_USER     "$PG_USER"
set_env POSTGRES_PASSWORD "$PG_PASS"
set_env POSTGRES_DB       "$PG_DB"
set_env POSTGRES_PORT     "$PG_PORT"
set_env REDIS_PORT        "$REDIS_PORT"
set_env BACKEND_PORT      "$BACKEND_PORT"
set_env FRONTEND_PORT     "$FRONTEND_PORT"

# ── 2. Secrets (persisted in addon_config for migration) ──────────────────
SECRET_KEY="$(bashio::config 'secret_key')"
NEXTAUTH_SECRET="$(bashio::config 'nextauth_secret')"

# ── 2b. Determine auth mode ───────────────────────────────────────────────
DEV_LOGIN_OPT="$(bashio::config 'dev_login')"
OIDC_ISSUER="$(bashio::config 'oidc_issuer_url')"
OIDC_CLIENT="$(bashio::config 'oidc_client_id')"
OIDC_CONFIGURED=false
if [ -n "$OIDC_ISSUER" ] && [ -n "$OIDC_CLIENT" ]; then
  OIDC_CONFIGURED=true
fi

# Auto-detect: if OIDC is configured, switch to production regardless
if [ "$OIDC_CONFIGURED" = "true" ]; then
  DEV_LOGIN_OPT="false"
  bashio::log.info "OIDC configured → production mode (dev login disabled)"
fi

# Guard: dev_login=false requires OIDC
if [ "$DEV_LOGIN_OPT" = "false" ] && [ "$OIDC_CONFIGURED" = "false" ]; then
  bashio::log.warning "dev_login is OFF but OIDC is not configured!"
  bashio::log.warning "Forcing dev_login back ON — configure OIDC to use production mode."
  DEV_LOGIN_OPT="true"
fi

# ── 2c. SECRET_KEY — handle per auth mode ─────────────────────────────────
if [ -z "$SECRET_KEY" ]; then
  SK_FILE="/config/.secret_key"
  if [ "$DEV_LOGIN_OPT" = "true" ]; then
    # Dev mode: use wardrowbe's built-in default
    SECRET_KEY="change-me-in-production"
    bashio::log.info "secret_key → dev-mode default"
  else
    # Production mode: auto-generate a real key and persist
    if [ -f "$SK_FILE" ]; then
      SECRET_KEY="$(cat "$SK_FILE")"
      bashio::log.info "secret_key loaded from /config/.secret_key"
    else
      SECRET_KEY="$(head -c32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
      echo -n "$SECRET_KEY" > "$SK_FILE"
      chmod 600 "$SK_FILE"
      bashio::log.info "secret_key generated → saved to /config/.secret_key"
    fi
  fi
fi

# NEXTAUTH_SECRET — always auto-generate and persist if empty
if [ -z "$NEXTAUTH_SECRET" ]; then
  NA_FILE="/config/.nextauth_secret"
  if [ -f "$NA_FILE" ]; then
    NEXTAUTH_SECRET="$(cat "$NA_FILE")"
    bashio::log.info "nextauth_secret loaded from /config/.nextauth_secret"
  else
    NEXTAUTH_SECRET="$(head -c32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
    echo -n "$NEXTAUTH_SECRET" > "$NA_FILE"
    chmod 600 "$NA_FILE"
    bashio::log.info "nextauth_secret generated → saved to /config/.nextauth_secret"
  fi
  # Migrate from old location if present
  OLD_NA="/data/wardrobe/.nextauth_secret"
  if [ -f "$OLD_NA" ] && [ ! -f "/config/.nextauth_secret" ]; then
    cp "$OLD_NA" "/config/.nextauth_secret"
    chmod 600 "/config/.nextauth_secret"
    NEXTAUTH_SECRET="$(cat "/config/.nextauth_secret")"
    bashio::log.info "Migrated nextauth_secret from /data/ to /config/"
  fi
fi

# ── 2d. Set auth env vars ─────────────────────────────────────────────────
set_env SECRET_KEY         "$SECRET_KEY"
set_env NEXTAUTH_SECRET    "$NEXTAUTH_SECRET"

if [ "$DEV_LOGIN_OPT" = "true" ]; then
  set_env DEBUG            "true"
  set_env DEV_LOGIN        "true"
  bashio::log.info "Auth mode: Dev Login (any email/name accepted)"
else
  set_env DEBUG            "false"
  set_env DEV_LOGIN        "false"
  bashio::log.info "Auth mode: OIDC (production)"
fi

# OIDC (optional) ----------------------------------------------------------
set_env OIDC_ISSUER_URL    "$OIDC_ISSUER"
set_env OIDC_CLIENT_ID     "$OIDC_CLIENT"
set_env OIDC_CLIENT_SECRET "$(bashio::config 'oidc_client_secret')"
set_env OIDC_MOBILE_CLIENT_ID "$(bashio::config 'oidc_mobile_client_id')"

# AI -----------------------------------------------------------------------
set_env AI_BASE_URL        "$(bashio::config 'ai_base_url')"
set_env AI_API_KEY         "$(bashio::config 'ai_api_key')"
set_env AI_VISION_MODEL    "$(bashio::config 'ai_vision_model')"
set_env AI_TEXT_MODEL       "$(bashio::config 'ai_text_model')"

# Notifications (optional) ------------------------------------------------
set_env NTFY_SERVER            "$(bashio::config 'ntfy_server')"
set_env NTFY_TOKEN             "$(bashio::config 'ntfy_token')"
set_env MATTERMOST_WEBHOOK_URL "$(bashio::config 'mattermost_webhook_url')"

# Backups (DB pg_dump scheduler) ------------------------------------------
set_env BACKUP_ENABLED         "$(bashio::config 'backup_enabled')"
set_env BACKUP_RETENTION_DAYS  "$(bashio::config 'backup_retention_days')"
set_env BACKUP_HOUR            "$(bashio::config 'backup_hour')"

# ── 3. Derived / internal env vars ────────────────────────────────────────
# Wardrobe photos live under /data/photos (data mount). The dir name
# reflects the content (photos), not the app (wardrowbe) — /data/ is
# already scoped per-addon so the addon name would be redundant.
# Photos are private to this addon — NOT visible in the HA media browser,
# which is the right default for personal clothing photos. Trade-off: /data/
# is in every HA addon snapshot, so heavy wardrobes inflate snapshot size.
# See DOCS.md "Data & Storage".
set_env STORAGE_PATH        "/data/photos"
set_env REDIS_URL           "redis://127.0.0.1:${REDIS_PORT}/0"
set_env DATABASE_URL        "postgresql+asyncpg://${PG_USER}:${PG_PASS}@127.0.0.1:${PG_PORT}/${PG_DB}"
set_env BACKEND_URL         "http://127.0.0.1:${BACKEND_PORT}"
set_env NEXT_PUBLIC_API_URL "http://127.0.0.1:${BACKEND_PORT}"
set_env AUTH_TRUST_HEADER   "true"
set_env PYTHONPATH          "/app/backend"
set_env PATH                "/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# ── 3b. NEXTAUTH_URL + CORS ──────────────────────────────────────────────
# external_url is the publicly reachable URL where wardrowbe is served.
# Required for OIDC callbacks to work. Not needed for dev login.
EXTERNAL_URL="$(bashio::config 'external_url')"

if [ -n "$EXTERNAL_URL" ]; then
  # Strip trailing slash
  EXTERNAL_URL="${EXTERNAL_URL%/}"
  set_env NEXTAUTH_URL  "$EXTERNAL_URL"
  set_env CORS_ORIGINS  "[\"http://127.0.0.1:3000\",\"http://localhost:3000\",\"${EXTERNAL_URL}\"]"
  bashio::log.info "NEXTAUTH_URL = ${EXTERNAL_URL}"
  bashio::log.info "─── OIDC Redirect URI ─────────────────────────────"
  bashio::log.info "  ${EXTERNAL_URL}/api/auth/callback/oidc"
  bashio::log.info "  Register this URL with your OIDC provider."
  bashio::log.info "───────────────────────────────────────────────────"
else
  set_env NEXTAUTH_URL  "http://127.0.0.1:${FRONTEND_PORT}"
  set_env CORS_ORIGINS  '["http://127.0.0.1:3000","http://localhost:3000"]'
  if [ "$OIDC_CONFIGURED" = "true" ]; then
    bashio::log.warning "OIDC is configured but external_url is empty!"
    bashio::log.warning "OIDC callbacks will fail. Set external_url in addon config."
    bashio::log.warning "  Example: https://wardrowbe.your-domain.tld"
  fi
fi

# ── 4. Create directories ─────────────────────────────────────────────────
mkdir -p /data/photos                  # wardrobe photos (data mount, private)
mkdir -p /share/wardrowbe/backups      # DB backups (share mount)
mkdir -p /data/redis                   # Redis persistence (data mount)
mkdir -p /run/postgresql /run/nginx    # runtime sockets

# ── 5. One-shot photo migration to /data/photos ──────────────────────────
# Temporary: photos used to live at /config/photos (1.2.0–1.4.x),
# /media/wardrowbe (1.0.0–1.1.x), /data/wardrobe (≤ 0.x), or /config/wardrobe
# (1.2.0 dev iteration). Move them once, then clear the old dir. Drop this
# block in a later release once installs are fully on /data/photos.
for SRC in /config/photos /media/wardrowbe /data/wardrobe /config/wardrobe; do
  [ -d "$SRC" ] && [ -n "$(ls -A "$SRC" 2>/dev/null)" ] \
    && [ -z "$(ls -A /data/photos 2>/dev/null)" ] || continue
  bashio::log.info "Migrating photos: ${SRC} → /data/photos"
  cp -a "$SRC"/. /data/photos/
  rm -rf "${SRC:?}"/*
  rmdir "$SRC" 2>/dev/null || true
done

# ── 6. Initialise PostgreSQL cluster (first-run only) ─────────────────────
mkdir -p /data/postgres

# One-time migration: pre-v4.1.x clusters are owned by the postgres OS user
# (UID 70 or 100). HA containers have CAP_CHOWN but NOT CAP_DAC_OVERRIDE, so
# standard chown -R and s6 fix-attrs.d both fail (they call opendir before
# chown and can't traverse a 700 dir they don't own). Top-down chown works:
# chown the directory first → root becomes owner → can enter via owner rwx.
_pg_chown_r() {
  chown 0:0 "$1"
  [ -d "$1" ] || return 0
  for _child in "$1"/*; do
    [ -e "$_child" ] || continue
    _pg_chown_r "$_child"
  done
}
_pg_uid=$(stat -c '%u' /data/postgres 2>/dev/null || echo 0)
if [ "$_pg_uid" != "0" ]; then
  bashio::log.info "Migrating PostgreSQL cluster from UID ${_pg_uid} to root …"
  _pg_chown_r /data/postgres
  bashio::log.info "Ownership migration complete."
fi
unset _pg_uid _pg_chown_r

if ! env LD_PRELOAD=/usr/local/lib/libfakeeuid.so test -f /data/postgres/data/PG_VERSION; then
  rmdir /data/postgres/data 2>/dev/null || true
  bashio::log.info "First run – creating PostgreSQL cluster …"
  env LD_PRELOAD=/usr/local/lib/libfakeeuid.so \
    initdb -D /data/postgres/data --encoding=UTF-8 --locale=C
fi

# Configure listen address + port ------------------------------------------
POSTGRES_CONF=/data/postgres/data/postgresql.conf
PG_HBA=/data/postgres/data/pg_hba.conf

sed -i "s/^#\?listen_addresses.*/listen_addresses = '127.0.0.1'/" "$POSTGRES_CONF" \
  || echo "listen_addresses = '127.0.0.1'" >> "$POSTGRES_CONF"
sed -i "s/^#\?port =.*/port = ${PG_PORT}/" "$POSTGRES_CONF" \
  || echo "port = ${PG_PORT}" >> "$POSTGRES_CONF"

cat > "$PG_HBA" <<EOF
local   all   all                 trust
host    all   all   127.0.0.1/32  md5
host    all   all   ::1/128       md5
EOF
# Low-IOPS storage optimizations (SD card, eMMC, USB) ----------------------
# Rewritten every boot so changes take effect without manual cluster edits.
cat > /data/postgres/data/wardrowbe.conf <<'PGCONF'
# wardrowbe managed — regenerated each start; edit 00-init.sh to change.

# WAL / durability: biggest write-amplification reduction on slow storage
synchronous_commit = off
wal_compression    = on
wal_buffers        = 4MB

# Checkpoint: flush dirty pages less often (default 5 min / 1 GB WAL)
checkpoint_timeout         = 15min
checkpoint_completion_target = 0.9
max_wal_size               = 256MB

# Memory: adequate for wardrowbe's small schema
shared_buffers = 32MB
work_mem       = 4MB

# I/O profile: SD/eMMC random reads are slow relative to sequential
random_page_cost        = 4.0
effective_io_concurrency = 0

# Connections: wardrowbe backend + worker only
max_connections = 10

# Autovacuum: gentler write bursts on flash storage
autovacuum_vacuum_cost_delay = 20ms

# Logging: no collector process, logs go straight to s6
logging_collector = off
PGCONF

grep -qF "include_if_exists = 'wardrowbe.conf'" "$POSTGRES_CONF" \
  || echo "include_if_exists = 'wardrowbe.conf'" >> "$POSTGRES_CONF"

bashio::log.info "Initialization complete."
bashio::log.info "  Photos:  /data/photos"
bashio::log.info "  Config:  /config/"
bashio::log.info "  Backups: /share/wardrowbe/backups"
bashio::log.info "  DB data: /data/"
