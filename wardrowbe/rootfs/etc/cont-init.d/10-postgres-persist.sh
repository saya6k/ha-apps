#!/usr/bin/with-contenv bash
# shellcheck shell=bash
set -euo pipefail

# Ensure the postgres data parent directory exists on the persistent volume.
# The cluster itself lives in /data/postgres/data, initialised by 00-init.sh.
mkdir -p /data/postgres
echo "[postgres-init] /data/postgres ready"
