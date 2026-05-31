ARG BUILD_FROM
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

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
    && mkdir -p /run/nginx /var/lib/zensical/docs /var/lib/zensical/site

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
