# Debian (glibc) base — we compile libparakeet + ggml from source and link the
# stock libstdc++/libgomp. The generic tag is a multi-arch manifest; BuildKit
# resolves amd64 / aarch64 and the build runs natively per arch in the HA
# builder, so the compiled libs match the target CPU.
ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:trixie

# Pin upstream parakeet.cpp (ggml comes in via its submodule). Bump this to
# follow upstream — there are no release tags, so we pin a commit SHA. GGML
# NATIVE is OFF for a portable build (ggml still picks AVX2/NEON kernels at
# runtime), matching mudler's published CPU image.
ARG PARAKEET_REF=e270af73b94c9a5c37ec516230219ed4580e1db6

# ---- builder: compile libparakeet.so (+ ggml), then install Python deps ----
FROM ${BUILD_FROM} AS builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG PARAKEET_REF
ENV PIP_BREAK_SYSTEM_PACKAGES=1 PYTHONDONTWRITEBYTECODE=1

RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        cmake \
        ninja-build \
        build-essential \
        ca-certificates \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git init -q . \
    && git remote add origin https://github.com/mudler/parakeet.cpp.git \
    && git fetch --depth 1 --recurse-submodules origin "${PARAKEET_REF}" \
    && git checkout -q FETCH_HEAD \
    && git submodule update --init --recursive --depth 1

# Vendored patches (e.g. hotword biasing, C ABI v5) — upstream-PR-shaped; when
# upstream ships the feature, delete the patch + this step and bump
# PARAKEET_REF. `git apply` fails loudly if a REF bump breaks a patch.
COPY patches/ /tmp/patches/
RUN git apply --stat /tmp/patches/*.patch \
    && git apply /tmp/patches/*.patch

# Shared library + flat C API only (no CLI, no tests). GGML_NATIVE=OFF for
# portability; GGML_BLAS=OFF / METAL=OFF to keep the runtime dep list to just
# libggml*. cmake --install is skipped — we only need the .so files, not the
# headers; find gathers every built .so directly into /usr/local/lib so the
# single COPY --from=builder /usr/local covers both the libs and Python packages.
RUN cmake -B build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DPARAKEET_SHARED=ON \
        -DPARAKEET_BUILD_CLI=OFF \
        -DPARAKEET_BUILD_TESTS=OFF \
        -DGGML_NATIVE=OFF \
        -DGGML_METAL=OFF \
        -DGGML_BLAS=OFF \
    && cmake --build build -j \
    && find build -name '*.so*' -type f -exec cp -a {} /usr/local/lib/ \; \
    && find /usr/local/lib -name '*.so' -type f -exec strip --strip-unneeded {} \;

RUN pip3 install --no-cache-dir --no-compile "wyoming>=1.9,<2" "huggingface_hub" "numpy" "gguf"
COPY pyproject.toml /usr/src/app/
COPY wyoming_nemo_asr_cpp/ /usr/src/app/wyoming_nemo_asr_cpp/
RUN pip3 install --no-cache-dir --no-compile --no-deps /usr/src/app

# ---- runtime ----
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_DISABLE_TELEMETRY=1

# libgomp1: ggml OpenMP threads. libstdc++6: C++ runtime for libparakeet/ggml.
RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        libgomp1 \
        libstdc++6 \
        ca-certificates \
        netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# parakeet.cpp shared libs (libparakeet + libggml*) + Python deps + our bridge,
# all placed in /usr/local by the builder stage.
COPY --from=builder /usr/local /usr/local

COPY rootfs /

RUN ldconfig \
    && chmod +x \
        /etc/s6-overlay/s6-rc.d/nemo-asr-cpp/run \
        /etc/s6-overlay/s6-rc.d/nemo-asr-cpp/finish \
        /etc/s6-overlay/s6-rc.d/discovery/run

HEALTHCHECK --start-period=10m \
    CMD echo '{ "type": "describe" }' \
        | nc -w 1 localhost 10360 \
        | grep -qi "nemo" \
        || exit 1
