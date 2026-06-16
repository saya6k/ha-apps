# Base image is set here (build.yaml is retired since Supervisor 2026.04.0).
# The generic, un-prefixed tag is a multi-arch manifest — BuildKit resolves
# amd64 / aarch64 automatically. Debian (glibc) base: onnxruntime ships
# manylinux CPU wheels that don't run on Alpine (musl).
ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:trixie

# ---- builder: install Python deps, then discard pip/build tooling ----
FROM ${BUILD_FROM} AS builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /usr/src/app
ENV PIP_BREAK_SYSTEM_PACKAGES=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_TELEMETRY=1

RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
    && pip3 install --no-cache-dir \
        "onnxruntime" \
        "sentencepiece" \
        "wyoming>=1.9,<2" \
        "huggingface_hub" \
        "numpy"

# Our bridge — installed with --no-deps so no build tooling rides into /usr/local.
COPY pyproject.toml /usr/src/app/
COPY wyoming_nemotron_asr/ /usr/src/app/wyoming_nemotron_asr/
RUN pip3 install --no-cache-dir --no-deps /usr/src/app

# ---- final: runtime only ----
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_TELEMETRY=1

# libgomp1: OpenMP runtime used by onnxruntime threads.
# ca-certificates: HuggingFace downloads. netcat: Wyoming healthcheck.
RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        libgomp1 \
        ca-certificates \
        netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Python deps + our bridge. Debian's site.py keeps /usr/local/lib/pythonX.Y/
# dist-packages on sys.path, so `python3 -m wyoming_nemotron_asr` resolves.
COPY --from=builder /usr/local /usr/local

COPY rootfs /

RUN chmod +x \
    /etc/s6-overlay/s6-rc.d/nemotron-asr/run \
    /etc/s6-overlay/s6-rc.d/nemotron-asr/finish \
    /etc/s6-overlay/s6-rc.d/discovery/run

HEALTHCHECK --start-period=10m \
    CMD echo '{ "type": "describe" }' \
        | nc -w 1 localhost 10350 \
        | grep -qi "nemotron" \
        || exit 1
