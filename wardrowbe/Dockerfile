ARG BUILD_FROM
ARG WARDROWBE_VERSION=wardrowbe-v1.2.2

# =========================================================================
# Stage 0 — Clone source from GitHub release tag
# =========================================================================
FROM alpine:3.20 AS source
ARG WARDROWBE_VERSION
RUN apk add --no-cache git \
 && git clone --depth 1 --branch "${WARDROWBE_VERSION}" \
      https://github.com/Anyesh/wardrowbe.git /src

# =========================================================================
# Stage 1 — Frontend build (Next.js standalone)
# =========================================================================
FROM node:20-alpine AS frontend-builder

RUN apk add --no-cache libc6-compat
WORKDIR /build

COPY --from=source /src/frontend/package.json /src/frontend/package-lock.json ./
RUN npm ci --ignore-scripts && npm rebuild sharp

COPY --from=source /src/frontend ./

# Enable dev-credentials login outside NODE_ENV=development so that the
# add-on works out-of-the-box without an external OIDC provider.
RUN sed -i \
  "s|process\.env\.NODE_ENV === 'development'|process.env.NODE_ENV === 'development' \|\| process.env.DEV_LOGIN === 'true'|" \
  lib/auth.ts

# Disable Next.js built-in compression (nginx handles this)
# Disable Next.js Image Optimization — images are served directly from backend
# This avoids all remotePatterns/rewrites issues with the /_next/image proxy
RUN sed -i "s|output: 'standalone'|output: 'standalone', compress: false, images: { unoptimized: true }|" next.config.js

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
 && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# =========================================================================
# Stage 3 — Final image (HA add-on base + all services)
# =========================================================================
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

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
    npm \
    postgresql \
    postgresql-client \
    python3 \
    py3-pip \
    py3-virtualenv \
    redis \
    su-exec

# ---- Directory scaffold -------------------------------------------------
RUN mkdir -p \
      /app/backend \
      /app/frontend \
      /media/wardrowbe \
      /share/wardrowbe/backups \
      /data/redis \
      /var/lib/postgresql/data \
      /run/postgresql \
      /run/nginx \
 && chown -R postgres:postgres /var/lib/postgresql /run/postgresql \
 && chmod 700 /var/lib/postgresql/data

# ---- Backend (Python) ---------------------------------------------------
COPY --from=backend-builder /wheels /wheels
COPY --from=source /src/backend /app/backend

RUN python3 -m venv /opt/venv \
 && . /opt/venv/bin/activate \
 && pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir /wheels/* \
 && rm -rf /wheels

# Verify backend app exists
RUN ls -la /app/backend/app/__init__.py

# Create worker launcher that auto-detects WorkerSettings location
# v1.2.2+ has app.workers.worker, v1.2.1 has app.workers.tagging
RUN printf '#!/opt/venv/bin/python3\nimport sys, os\nsys.path.insert(0, "/app/backend")\nos.chdir("/app/backend")\ntry:\n    from app.workers.worker import WorkerSettings\nexcept ImportError:\n    from app.workers.tagging import WorkerSettings\nfrom arq.worker import run_worker\nrun_worker(WorkerSettings)\n' \
    > /app/backend/run_worker.py \
 && chmod +x /app/backend/run_worker.py

# ---- Frontend (Next.js standalone) --------------------------------------
COPY --from=frontend-builder /build/.next/standalone /app/frontend/
COPY --from=frontend-builder /build/.next/static     /app/frontend/.next/static
COPY --from=frontend-builder /build/public            /app/frontend/public

# ---- rootfs (s6, nginx, init) -------------------------------------------
COPY rootfs /

RUN chmod a+x /etc/cont-init.d/*.sh \
 && find /etc/s6-overlay/s6-rc.d -type f \( -name run -o -name finish \) -exec chmod a+x {} \; \
 && find /etc/s6-overlay/s6-rc.d -type f -name type -exec chmod 644 {} \;

WORKDIR /
