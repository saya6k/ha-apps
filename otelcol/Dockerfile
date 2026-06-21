# build.yaml is deprecated (Supervisor warns) — base image + labels live here
# now.
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.21
ARG BUILD_ARCH=amd64

# ── Stage 1: extract otelcol-contrib binary per architecture ──────────
# Upstream publishes single-arch tags: <ver>-amd64 / <ver>-arm64.
# We pull both into a scratch stage, then COPY the right one at the end.
FROM ghcr.io/open-telemetry/opentelemetry-collector-releases/opentelemetry-collector-contrib:0.154.0-amd64 AS otelcol-amd64
FROM ghcr.io/open-telemetry/opentelemetry-collector-releases/opentelemetry-collector-contrib:0.154.0-arm64 AS otelcol-aarch64

FROM scratch AS container
COPY --from=otelcol-amd64 /otelcol-contrib /amd64/otelcol-contrib
COPY --from=otelcol-aarch64 /otelcol-contrib /aarch64/otelcol-contrib

# ── Final stage ───────────────────────────────────────────────────────
FROM ${BUILD_FROM}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

LABEL \
    org.opencontainers.image.title="Home Assistant Add-on: OpenTelemetry Collector" \
    org.opencontainers.image.description="Collect logs, metrics, and traces from HA Core, Supervisor, and add-on containers. Export via OTLP to LGTM." \
    org.opencontainers.image.source="https://github.com/saya6k/ha-apps" \
    org.opencontainers.image.licenses="MIT"

ENV LANG=C.UTF-8

# ── Python bridge dependencies ─────────────────────────────────────────
# Install in a venv to isolate from system Python and bound layer size.
RUN apk add --no-cache python3 py3-pip \
    && python3 -m venv /opt/bridge-venv \
    && /opt/bridge-venv/bin/pip install --no-cache-dir \
        aiohttp \
        opentelemetry-sdk \
        opentelemetry-exporter-otlp-proto-http

ENV PATH="/opt/bridge-venv/bin:${PATH}"

# Copy the otelcol-contrib binary for the target architecture
COPY --from=container /${BUILD_ARCH}/otelcol-contrib /usr/bin/otelcol-contrib

# Copy the root filesystem (s6 services, bundled config)
COPY rootfs /

# s6-overlay: ensure service scripts are executable; bridge script is executable
RUN find /etc/s6-overlay/s6-rc.d -type f \( -name run -o -name finish -o -name up -o -name down \) -exec chmod +x {} \; \
    && chmod +x /usr/bin/ha-otel-bridge \
    && mkdir -p /addon_config

HEALTHCHECK --start-period=10s --interval=5m --timeout=3s --retries=3 \
    CMD /usr/bin/otelcol-contrib --feature-gates=-component.UseLocalHostAsDefaultHost healthcheck 2>/dev/null || \
        wget -qO- http://localhost:13133/ >/dev/null 2>&1 || exit 1
