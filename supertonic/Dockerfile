ARG BUILD_FROM
FROM ${BUILD_FROM}

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
        netcat-traditional \
        python3 \
        python3-pip \
        libsndfile1 \
        ca-certificates \
        git \
    && pip3 install --no-cache-dir -U setuptools wheel \
    && pip3 install --no-cache-dir \
        "git+https://github.com/vra/supertonic-mnn.git@${SUPERTONIC_MNN_REF}" \
        "wyoming==1.7.2" \
        "sentence-stream" \
        "num2words" \
        "numpy<2.0" \
    && apt-get purge -y --auto-remove git \
    && rm -rf /var/lib/apt/lists/* /root/.cache

# Our Wyoming bridge.
COPY pyproject.toml /usr/src/app/
COPY wyoming_supertonic/ /usr/src/app/wyoming_supertonic/
RUN pip3 install --no-cache-dir --no-deps /usr/src/app

WORKDIR /
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
