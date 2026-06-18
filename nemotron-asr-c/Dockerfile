# Debian (glibc) base — we compile libnemotron_asr.so from source. The generic
# tag is a multi-arch manifest; BuildKit resolves amd64 / aarch64 and the build
# runs natively per arch, so SIMD kernels (AVX2 / NEON) match the target CPU.
ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:trixie

# Pin upstream nemotron-asr-streaming.c commit (branch w8a8). Bump to follow.
ARG NEMOTRON_C_REF=4fde8b47cdc00c3544135c9d8f38c3f66a8431e6

# ---- builder: compile libnemotron_asr.so from source ----
FROM ${BUILD_FROM} AS builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG NEMOTRON_C_REF

RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        build-essential \
        ca-certificates

WORKDIR /src
RUN git init -q . \
    && git remote add origin https://github.com/kdrkdrkdr/nemotron-asr-streaming.c.git \
    && git fetch --depth 1 origin "${NEMOTRON_C_REF}" \
    && git checkout FETCH_HEAD

# Vendored patches: shared-library build target (+ any future patches).
COPY patches/ /tmp/patches/
RUN git apply --stat /tmp/patches/*.patch \
    && git apply /tmp/patches/*.patch

# Build shared library (position-independent, no CLI). SIMD kernels: NEON on
# aarch64, AVX2/FMA on amd64, generic C fallback otherwise.
RUN make -j"$(nproc)" shared \
    && mkdir -p /opt/nemotron-c/lib \
    && cp libnemotron_asr.so /opt/nemotron-c/lib/

# ---- builder-py: install Python deps + our bridge ----
FROM ${BUILD_FROM} AS builder-py

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV PIP_BREAK_SYSTEM_PACKAGES=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /usr/src/app
RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && pip3 install --no-cache-dir "wyoming>=1.9,<2" "huggingface_hub[hf-xet]>=0.32" "numpy" "torch" "pyyaml" "sentencepiece"
COPY pyproject.toml /usr/src/app/
COPY wyoming_nemotron_asr_c/ /usr/src/app/wyoming_nemotron_asr_c/
RUN pip3 install --no-cache-dir --no-deps /usr/src/app

# ---- runtime ----
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_TELEMETRY=1

# Runtime deps: python3 for the bridge, netcat for healthcheck.
# PyTorch comes from builder-py (for boot-time .nemo -> .bin conversion).
RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        netcat-traditional \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# C shared library.
COPY --from=builder /opt/nemotron-c/lib/libnemotron_asr.so /usr/local/lib/
# Python deps + our bridge (includes torch, numpy, wyoming, huggingface_hub).
COPY --from=builder-py /usr/local /usr/local

# Converter script vendored from upstream.
COPY tools/ /usr/src/app/tools/

COPY rootfs /

RUN ldconfig \
    && shopt -s nullglob \
    && chmod +x /etc/s6-overlay/s6-rc.d/*/{run,up,finish,down}

HEALTHCHECK --start-period=10m \
    CMD echo '{ "type": "describe" }' \
        | nc -w 1 localhost 10370 \
        | grep -qi "nemo" \
        || exit 1
