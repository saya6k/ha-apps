# build.yaml is deprecated (Supervisor warns) — base image + labels live here
# now.
ARG BUILD_FROM=ghcr.io/home-assistant/base:3.21
ARG BUILD_ARCH=amd64

# ── Stage 1: otelcol-contrib binary ───────────────────────────────────────────
# The plain (un-suffixed) tag is a multi-arch manifest — BuildKit resolves
# amd64 / arm64 automatically from the build platform, same pattern used by
# other add-ons in this repo.
FROM ghcr.io/open-telemetry/opentelemetry-collector-releases/opentelemetry-collector-contrib:0.154.0 AS otelcol-binary

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
        aiodns \
        opentelemetry-sdk \
        opentelemetry-exporter-otlp-proto-http

ENV PATH="/opt/bridge-venv/bin:${PATH}"

# Copy the otelcol-contrib binary for the target architecture
COPY --from=otelcol-binary /otelcol-contrib /usr/bin/otelcol-contrib

# Copy the root filesystem (s6 services, bundled config)
COPY rootfs /

# s6-overlay: ensure service scripts are executable; bridge script is executable
RUN find /etc/s6-overlay/s6-rc.d -type f \( -name run -o -name finish -o -name up -o -name down \) -exec chmod +x {} \; \
    && chmod +x /usr/bin/ha-otel-bridge \
    && mkdir -p /addon_config

HEALTHCHECK --start-period=10s --interval=5m --timeout=3s --retries=3 \
    CMD /usr/bin/otelcol-contrib --feature-gates=-component.UseLocalHostAsDefaultHost healthcheck 2>/dev/null || \
        wget -qO- http://localhost:13133/ >/dev/null 2>&1 || exit 1
