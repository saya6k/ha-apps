# Debian (glibc) base — we compile libnemotron_asr.so from source. The generic
# tag is a multi-arch manifest; BuildKit resolves amd64 / aarch64 and the build
# runs natively per arch, so SIMD kernels (AVX2 / NEON) match the target CPU.
ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:trixie

# Pin upstream nemotron-asr-streaming.c commit (branch w8a8). Bump to follow.
ARG NEMOTRON_C_REF=4fde8b47cdc00c3544135c9d8f38c3f66a8431e6

# Pin upstream fastenhancer.c.wasm commit (optional speech-enhancement filter).
ARG FASTENHANCER_REF=e69c3bf56bbd0fda42b6c4a7edc11f38ab198758

# ---- builder: compile .so and install Python deps/bridge into /usr/local ----
FROM ${BUILD_FROM} AS builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG NEMOTRON_C_REF
ARG FASTENHANCER_REF
ENV PIP_BREAK_SYSTEM_PACKAGES=1 PYTHONDONTWRITEBYTECODE=1

RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        build-essential \
        ca-certificates \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

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
# Drop into /usr/local/lib so the single COPY --from=builder /usr/local captures both
# the .so and the Python packages in one layer.
RUN make -j"$(nproc)" shared \
    && strip --strip-unneeded libnemotron_asr.so \
    && cp libnemotron_asr.so /usr/local/lib/

# ---- FastEnhancer: optional speech-enhancement pre-filter (denoise) ----
# Vendored + pinned. Built natively WITHOUT -msimd128: every wasm_simd128 hot
# path is guarded by `#ifdef __wasm_simd128__` and falls back to scalar C, so a
# plain gcc build is pure portable C. Denoise-only at runtime (dereverb/AGC off);
# webrtc_agc.h is header-only (static inline) so no extra TU is needed.
WORKDIR /src-fe
RUN git init -q . \
    && git remote add origin https://github.com/kdrkdrkdr/fastenhancer.c.wasm.git \
    && git fetch --depth 1 origin "${FASTENHANCER_REF}" \
    && git checkout FETCH_HEAD
RUN gcc -O3 -fPIC -shared -ffast-math \
        -Isrc -Isrc/denoise -Isrc/dereverb \
        src/main.c src/denoise/*.c src/dereverb/*.c \
        -o /usr/local/lib/libfastenhancer.so -lm \
    && strip --strip-unneeded /usr/local/lib/libfastenhancer.so \
    && install -D -m 0644 weights/fe_tiny.bin \
        /usr/local/share/fastenhancer/fe_tiny.bin

RUN pip3 install --no-cache-dir --no-compile \
    "wyoming>=1.9,<2" \
    "huggingface_hub[hf-xet]>=0.32" \
    "numpy" \
    "pyyaml" \
    "sentencepiece"

# torch is only used for boot-time .nemo -> .bin conversion (torch.load on CPU;
# quantization math is numpy). The default PyPI wheel is the CUDA build, which
# drags in nvidia/* (~2.9 GB) + triton (~650 MB) we never touch. Pull the CPU
# wheel from PyTorch's index (deps still resolve from PyPI) — ~3.5 GB smaller.
RUN pip3 install --no-cache-dir --no-compile \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple \
    "torch" \
    && TORCH=$(python3 -c "import torch,os;print(os.path.dirname(torch.__file__))") \
    && rm -rf "${TORCH}/test" "${TORCH}/include"

COPY pyproject.toml /usr/src/app/
COPY wyoming_nemotron_asr_c/ /usr/src/app/wyoming_nemotron_asr_c/
RUN pip3 install --no-cache-dir --no-compile --no-deps /usr/src/app

# ---- runtime ----
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HOME=/data/models/.hf_cache

# Runtime deps: python3 for the bridge, netcat for healthcheck.
# PyTorch comes from builder (for boot-time .nemo -> .bin conversion).
RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        netcat-traditional \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# C shared library + Python deps + our bridge (all in /usr/local from builder).
COPY --from=builder /usr/local /usr/local

# rootfs includes s6 scripts, discovery, and tools/convert_nemo.py.
COPY rootfs /

RUN ldconfig \
    && shopt -s nullglob \
    && chmod +x /etc/s6-overlay/s6-rc.d/*/{run,up,finish,down}

HEALTHCHECK --start-period=10m \
    CMD echo '{ "type": "describe" }' \
        | nc -w 1 localhost 10370 \
        | grep -qi "nemo" \
        || exit 1
