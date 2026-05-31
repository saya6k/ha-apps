# Multi-arch base. The HA `base:<ver>` tag is a multi-arch manifest, so
# Docker (with BuildKit) picks the right layer per `--platform`. The
# ARG default means we no longer rely on `build.yaml` injection — that
# file is deprecated upstream and the Supervisor 2026.04+ fallback was
# removed (see https://developers.home-assistant.io/docs/add-ons/configuration).
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23
FROM ${BUILD_FROM}

SHELL ["/bin/ash", "-o", "pipefail", "-c"]

WORKDIR /usr/src/app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# HA Alpine base ships python3 (3.11 on :3.19, 3.12 on :3.20, 3.13 on
# :3.22+). bubblewrap 0.11+ on :3.22+ supports --rlimit-as / --rlimit-cpu.
RUN apk add --no-cache \
        python3 \
        py3-pip \
        netcat-openbsd \
        bubblewrap \
        py3-libseccomp \
    && pip3 install --no-cache-dir --break-system-packages \
        "wyoming==1.9.*" \
        "httpx==0.28.*" \
        "mcp>=1.27,<2" \
        "prometheus_client>=0.21,<1" \
        "Jinja2>=3.1,<4" \
        "PyYAML>=6,<7"

# Install our agent package (--no-deps; runtime deps came from pip above).
COPY pyproject.toml /usr/src/app/
COPY wyoming_llm_agent/ /usr/src/app/wyoming_llm_agent/
RUN pip3 install --no-cache-dir --break-system-packages --no-deps /usr/src/app

WORKDIR /
COPY rootfs /

RUN chmod +x \
    /etc/s6-overlay/s6-rc.d/llm-agent/run \
    /etc/s6-overlay/s6-rc.d/llm-agent/finish \
    /etc/s6-overlay/s6-rc.d/discovery/run

HEALTHCHECK --start-period=30s --interval=30s --timeout=5s --retries=3 \
    CMD echo '{ "type": "describe" }' \
        | nc -w 1 localhost 10500 \
        | grep -q "LLM Conversation Agent" \
        || exit 1
