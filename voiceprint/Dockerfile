# Debian (glibc) base — ai-edge-litert/numpy/kaldi-native-fbank ship manylinux
# wheels that don't run on the Alpine (musl) default base.
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
COPY wyoming_voiceprint/ /usr/src/app/wyoming_voiceprint/
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

# The 14 MB CAM++ speaker model is NOT baked into the image — it is fetched
# once into the persistent /data volume on first run (see wyoming_voiceprint
# /models.py) and verified against const.MODEL_SHA256.

COPY rootfs /

RUN chmod +x \
    /etc/s6-overlay/s6-rc.d/voiceprint/run \
    /etc/s6-overlay/s6-rc.d/voiceprint/finish \
    /etc/s6-overlay/s6-rc.d/discovery/run

HEALTHCHECK --start-period=10m \
    CMD echo '{ "type": "describe" }' \
        | nc -w 1 localhost 10350 \
        | grep -qi "voiceprint" \
        || exit 1
