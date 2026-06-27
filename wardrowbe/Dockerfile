# BUILD_FROM is no longer injected by the Supervisor (>=2026.04.0) — default to
# the multi-arch HA base manifest, pinned to an Alpine version tag (3.23 →
# Node 24.14.1) instead of the moving :latest. Overridable with --build-arg.
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23
ARG WARDROWBE_VERSION=wardrowbe-v1.3.1

# =========================================================================
# Stage 0 — Clone source from GitHub release tag
# =========================================================================
FROM ${BUILD_FROM} AS source
ARG WARDROWBE_VERSION
RUN apk add --no-cache git \
 && git clone --depth 1 --branch "${WARDROWBE_VERSION}" \
      https://github.com/Anyesh/wardrowbe.git /src

# =========================================================================
# Stage 1 — Frontend build (Next.js standalone)
# =========================================================================
FROM ${BUILD_FROM} AS frontend-builder

RUN apk add --no-cache libc6-compat nodejs npm
WORKDIR /build

COPY --from=source /src/frontend/package.json /src/frontend/package-lock.json ./
RUN npm ci --ignore-scripts

COPY --from=source /src/frontend ./

# Enable dev-credentials login outside NODE_ENV=development so that the
# add-on works out-of-the-box without an external OIDC provider.
RUN sed -i \
  "s|process\.env\.NODE_ENV === 'development'|process.env.NODE_ENV === 'development' \|\| process.env.DEV_LOGIN === 'true'|" \
  lib/auth.ts

# Disable Next.js built-in compression (nginx handles this)
# Disable Next.js Image Optimization — images are served directly from backend
# This avoids all remotePatterns/rewrites issues with the /_next/image proxy
# Disable font optimization — next/font/google fetches from googleapis at build
# time; QEMU-emulated arm64 CI runners have no external network access.
RUN sed -i "s|output: 'standalone'|output: 'standalone', compress: false, images: { unoptimized: true }, optimizeFonts: false|" next.config.js

ENV NEXT_TELEMETRY_DISABLED=1
# Set backend URL at build time — rewrites() bakes this into standalone output
ENV BACKEND_URL=http://127.0.0.1:8000
RUN npm run build

# =========================================================================
# Stage 2 — Python wheels (built on same base so Python version matches)
# =========================================================================
FROM ${BUILD_FROM} AS backend-builder

RUN apk add --no-cache \
    build-base \
    cargo \
    libffi-dev \
    linux-headers \
    openssl-dev \
    postgresql-dev \
    python3-dev \
    py3-pip
WORKDIR /build
COPY --from=source /src/backend/requirements.txt ./
RUN pip install --no-cache-dir --break-system-packages wheel \
 && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt \
 && python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir /wheels/* \
 && find /opt/venv -name '*.so' -exec strip --strip-unneeded {} \; \
 && rm -rf /wheels

# =========================================================================
# Stage 3 — Final image (HA add-on base + all services)
# =========================================================================
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Image metadata — migrated from the deprecated build.yaml `labels:` block.
LABEL \
    org.opencontainers.image.title="Home Assistant Add-on: Wardrowbe" \
    org.opencontainers.image.description="Self-hosted AI-powered wardrobe management" \
    org.opencontainers.image.source="https://github.com/Anyesh/wardrowbe" \
    org.opencontainers.image.licenses="MIT"

ENV LANG=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend \
    PATH="/opt/venv/bin:$PATH" \
    PIP_NO_CACHE_DIR=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# ---- Runtime packages ---------------------------------------------------
RUN apk add --no-cache \
    bash \
    curl \
    jq \
    libc6-compat \
    libstdc++ \
    nginx \
    nodejs \
    postgresql \
    postgresql-client \
    python3 \
    redis

# ---- Directory scaffold -------------------------------------------------
# Keep all dirs root-owned; postgres runs as root via LD_PRELOAD shim
# (HA containers lack CAP_SETUID/SETGID/DAC_OVERRIDE — no runtime user-switch).
# PGDATA is /data/postgres/data (volume); /var/lib/postgresql is only the
# postgres home dir. chmod 755 lets root traverse it at runtime.
# apk add postgresql creates /var/lib/postgresql as postgres:postgres:700.
RUN mkdir -p \
      /app/backend \
      /app/frontend \
      /data/photos \
      /share/wardrowbe/backups \
      /data/redis \
      /run/postgresql \
      /run/nginx \
      /var/lib/nginx/logs \
 && chmod 755 /var/lib/postgresql /run/postgresql /var/lib/nginx/logs \
 && chown 0:0 /var/lib/nginx /var/lib/nginx/logs \
 && chmod 755 /var/lib/nginx

# ---- postgres root-bypass shim -------------------------------------------
# libfakeeuid.so: LD_PRELOAD shim — postgres/initdb see geteuid()=999 (non-root).
# 00-init.sh top-down-chowns any pre-v4.1.x postgres-owned cluster to root
# (CAP_CHOWN) before initdb runs, so this shim handles all cases uniformly.
COPY libfakeeuid.c /tmp/libfakeeuid.c
RUN apk add --no-cache --virtual .build-tmp gcc musl-dev \
 && gcc -shared -fPIC -o /usr/local/lib/libfakeeuid.so /tmp/libfakeeuid.c -ldl \
 && apk del .build-tmp \
 && rm /tmp/libfakeeuid.c

# ---- Backend (Python) ---------------------------------------------------
COPY --from=backend-builder /opt/venv /opt/venv
COPY --from=source /src/backend /app/backend

# ---- Frontend (Next.js standalone) --------------------------------------
COPY --from=frontend-builder /build/.next/standalone /app/frontend/
COPY --from=frontend-builder /build/.next/static     /app/frontend/.next/static
COPY --from=frontend-builder /build/public            /app/frontend/public

# ---- rootfs (s6, nginx, init) -------------------------------------------
COPY rootfs /

RUN chmod a+x /etc/cont-init.d/*.sh /app/backend/run_worker.py \
 && find /etc/s6-overlay/s6-rc.d -type f \( -name run -o -name finish \) -exec chmod a+x {} \; \
 && find /etc/s6-overlay/s6-rc.d -type f -name type -exec chmod 644 {} \;

WORKDIR /

# Supervisor uses the container HEALTHCHECK for health-based auto-restart —
# the replacement for the removed (deprecated) `watchdog:` config option. The
# backend health endpoint is served through nginx on the web port 8099.
HEALTHCHECK --start-period=3m --interval=30s --timeout=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8099/api/v1/health || exit 1
