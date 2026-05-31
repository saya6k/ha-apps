#!/usr/bin/with-contenv bash
set -euo pipefail

# PostgreSQL persistence:
#   /data/postgres/data/      →  PGDATA (excluded from HA backups via backup_exclude)
#   /var/lib/postgresql/data  →  symlink to /data/postgres/data
#
# Runs AFTER 00-init.sh, which may have just `initdb`'d a fresh cluster into
# the real /var/lib/postgresql/data directory. We move that into place before
# swapping in the symlink, otherwise the freshly-created cluster would be lost.

DATA_ROOT="/data/postgres"
DATA_DIR="${DATA_ROOT}/data"
PGDATA="/var/lib/postgresql/data"

echo "[postgres-init] start"

mkdir -p "$DATA_ROOT"

# Capture a freshly-initdb'd cluster from /var/lib/postgresql/data
if [ -d "$PGDATA" ] && [ ! -L "$PGDATA" ] && [ -f "$PGDATA/PG_VERSION" ] && [ ! -e "$DATA_DIR" ]; then
  echo "[postgres-init] capturing fresh cluster: ${PGDATA} → ${DATA_DIR}"
  mv "$PGDATA" "$DATA_DIR"
fi

if [ ! -e "$DATA_DIR" ]; then
  echo "[postgres-init] creating empty ${DATA_DIR}"
  mkdir -p "$DATA_DIR"
fi
chown -R postgres:postgres "$DATA_ROOT"
chmod 700 "$DATA_DIR"

if [ -L "$PGDATA" ] && [ "$(readlink "$PGDATA")" = "$DATA_DIR" ]; then
  echo "[postgres-init] PGDATA already linked"
else
  echo "[postgres-init] linking PGDATA → ${DATA_DIR}"
  rm -rf "$PGDATA"
  ln -s "$DATA_DIR" "$PGDATA"
fi

echo "[postgres-init] done"
