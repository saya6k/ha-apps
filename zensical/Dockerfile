# build.yaml is deprecated (Supervisor warns) — base image + labels live here
# now. Pinned to the multi-arch base:3.21 manifest (Alpine 3.21 → Python 3.12);
# the old per-arch :3.19 pin has no multi-arch tag, so a single ARG default
# can't reference it. Overridable with --build-arg.
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.21
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

LABEL \
    org.opencontainers.image.title="Home Assistant Add-on: Zensical" \
    org.opencontainers.image.description="Render /config/docs/ as a Zensical site, served via the ingress panel" \
    org.opencontainers.image.source="https://github.com/saya6k/ha-mkdocs" \
    org.opencontainers.image.licenses="MIT"

ENV LANG=C.UTF-8 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

RUN apk add --no-cache \
        python3 \
        py3-pip \
        nginx \
        inotify-tools \
        rsync \
    && python3 -m venv /opt/venv \
    && mkdir -p \
         /run/nginx \
         /var/lib/zensical/docs \
         /var/lib/zensical/site \
         /var/lib/nginx/tmp/client_body \
         /var/lib/nginx/tmp/proxy \
         /var/lib/nginx/tmp/fastcgi \
         /var/lib/nginx/tmp/uwsgi \
         /var/lib/nginx/tmp/scgi \
     && chown -R nginx:nginx /var/lib/nginx

COPY requirements.txt /tmp/requirements.txt
RUN . /opt/venv/bin/activate \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

COPY rootfs /

RUN find /etc/s6-overlay/s6-rc.d -type f \( -name run -o -name finish -o -name up \) -exec chmod +x {} \; \
    && chmod +x /opt/zensical/bin/* \
    && mkdir -p /addon_config

HEALTHCHECK --start-period=30s --interval=30s --timeout=5s --retries=3 \
    CMD curl -fs http://127.0.0.1:8099/index.html >/dev/null || exit 1
