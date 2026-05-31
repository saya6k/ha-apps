# Multi-arch manifest tag — covers amd64 + aarch64 in one image. No build.yaml
# needed; Supervisor builds straight from this Dockerfile. Tag format is
# <alpine>-<release>; bump both halves together when refreshing.
FROM ghcr.io/home-assistant/base:3.23-2026.05.0

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Upstream rethink commit pin. Bump when upstream adds device support or fixes.
ARG RETHINK_REV=054407cbcff446a2bd7896925005bd73573886ef

ENV LANG=C.UTF-8

WORKDIR /app

# jq, curl, tar, bash already in HA base. Node + npm + openssl are not.
RUN apk add --no-cache nodejs npm openssl \
    && curl -fsSL "https://github.com/anszom/rethink/archive/${RETHINK_REV}.tar.gz" \
        | tar -xz --strip-components=1 \
    && cd rethink \
    && npm ci --ignore-scripts \
    && npm run build \
    && npm prune --omit=dev \
    && apk del npm \
    && rm -rf /root/.npm /tmp/*

# Runtime-only — kept out of the build stage so `npm ci` still installs
# devDependencies (tsc etc.) for the build.
ENV NODE_ENV=production

WORKDIR /
COPY rootfs /

RUN chmod +x \
    /etc/s6-overlay/s6-rc.d/rethink/run \
    /etc/s6-overlay/s6-rc.d/rethink/finish

HEALTHCHECK --start-period=2m --interval=30s --timeout=5s --retries=3 \
    CMD curl -fs http://127.0.0.1:44401/ >/dev/null || exit 1
