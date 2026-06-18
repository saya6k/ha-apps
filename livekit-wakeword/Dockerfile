# Debian (glibc) base — onnxruntime/numpy ship manylinux wheels that don't run
# on the Alpine (musl) default base. livekit-wakeword itself is a pure-Python
# wheel (frontend ONNX models bundled), so no compilation happens anywhere.
ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:trixie

# ---- builder: pip install everything into /usr/local, discarded after ----
FROM ${BUILD_FROM} AS builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV PIP_BREAK_SYSTEM_PACKAGES=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY pyproject.toml /usr/src/app/
COPY wyoming_livekit_wakeword/ /usr/src/app/wyoming_livekit_wakeword/
RUN pip3 install --no-cache-dir --no-compile /usr/src/app

# ---- runtime: no pip, no build tooling ----
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        ca-certificates \
        netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Python deps + the bridge from the builder stage. Debian's site.py keeps
# /usr/local/lib/pythonX.Y/dist-packages on sys.path.
COPY --from=builder /usr/local /usr/local

COPY rootfs /

RUN chmod +x \
    /etc/s6-overlay/s6-rc.d/livekit-wakeword/run \
    /etc/s6-overlay/s6-rc.d/livekit-wakeword/finish \
    /etc/s6-overlay/s6-rc.d/discovery/run

HEALTHCHECK --start-period=10m \
    CMD echo '{ "type": "describe" }' \
        | nc -w 1 localhost 10400 \
        | grep -qi "livekit" \
        || exit 1
