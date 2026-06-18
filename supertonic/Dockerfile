# Base image is set here (build.yaml is retired since Supervisor 2026.04.0).
# The generic, un-prefixed tag is a multi-arch manifest — BuildKit resolves
# amd64 / aarch64 automatically. Debian (glibc) is required: MNN / numpy ship
# manylinux wheels that don't run on the Alpine (musl) default base. The CI
# builder may still override BUILD_FROM; the default keeps local builds working.
ARG BUILD_FROM=ghcr.io/home-assistant/base-debian:trixie

# ---- builder: install the Python deps (needs git + pip), discarded after ----
FROM ${BUILD_FROM} AS builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

WORKDIR /usr/src/app
ENV PIP_BREAK_SYSTEM_PACKAGES=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# supertonic-mnn 0.2.0 (with v3 / 31-language support and a lang= kwarg)
# is not yet on PyPI — the latest published release is 0.1.3, which is
# v2-only and doesn't take a language argument. Pin to a known-good
# commit on main until upstream cuts a release.
ARG SUPERTONIC_MNN_REF=ce5d7b25e2581293cd9d4ac0a462ac6e5e7d1cd0

RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        git \
        patchelf \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir --no-compile \
        "git+https://github.com/vra/supertonic-mnn.git@${SUPERTONIC_MNN_REF}" \
        "wyoming==1.9.0" \
        "sentence-stream" \
        "unicode-rbnf" \
        "numpy" \
    # MNN's x86_64 wheel ships _mnncengine.so / _tools.so with an executable
    # stack (GNU_STACK RWE) because its asm objects lack a .note.GNU-stack
    # marker. Newer loaders reject it at import ("cannot enable executable
    # stack ... Invalid argument"). MNN never executes from the stack, so
    # clearing the flag is safe. No-op on the aarch64 wheel (already RW).
    && patchelf --clear-execstack \
        /usr/local/lib/python3.*/dist-packages/_mnncengine*.so \
        /usr/local/lib/python3.*/dist-packages/_tools*.so

# Our Wyoming bridge. pip's PEP 517 build isolation pulls setuptools/wheel into
# a throwaway env, so we never install them into /usr/local — nothing extra
# rides along in the COPY of /usr/local into the runtime stage.
COPY pyproject.toml /usr/src/app/
COPY wyoming_supertonic/ /usr/src/app/wyoming_supertonic/
RUN pip3 install --no-cache-dir --no-compile --no-deps /usr/src/app

# ---- final: runtime only — no pip, no setuptools, no git, no build tooling ----
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV HF_HUB_DISABLE_TELEMETRY=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        netcat-traditional \
        python3 \
        libsndfile1 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python deps + our bridge, built in the builder stage. /usr/local is where
# pip (with PIP_BREAK_SYSTEM_PACKAGES) writes packages and console scripts;
# Debian's site.py keeps /usr/local/lib/pythonX.Y/dist-packages on sys.path,
# so `python3 -m wyoming_supertonic` resolves without a local pip install.
COPY --from=builder /usr/local /usr/local

COPY rootfs /

RUN chmod +x \
    /etc/s6-overlay/s6-rc.d/supertonic/run \
    /etc/s6-overlay/s6-rc.d/supertonic/finish \
    /etc/s6-overlay/s6-rc.d/discovery/run

HEALTHCHECK --start-period=10m \
    CMD echo '{ "type": "describe" }' \
        | nc -w 1 localhost 10209 \
        | grep -q "Supertonic" \
        || exit 1
