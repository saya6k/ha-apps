#!/command/with-contenv bash
# shellcheck shell=bash
# Create /data/options.json and /data/addon.json with safe defaults when the
# Supervisor hasn't pre-created them (e.g. standalone / local container testing).
# In a real HA installation the Supervisor writes these files before the
# container starts, so this script is a no-op there.

mkdir -p /data

if [[ ! -f /data/options.json ]]; then
    cat > /data/options.json << 'EOF'
{
  "log_level": "debug",
  "otlp_endpoint": "",
  "otlp_protocol": "grpc",
  "otlp_headers": [],
  "otlp_tls_insecure": false,
  "ha_logs_enabled": false,
  "ha_metrics_enabled": false,
  "ha_events_enabled": false,
  "ha_traces_enabled": false,
  "container_logs_enabled": false,
  "host_metrics_enabled": false,
  "raw_config": ""
}
EOF
fi

if [[ ! -f /data/addon.json ]]; then
    cat > /data/addon.json << 'EOF'
{
  "slug": "otelcol",
  "version": "0.1.0-local"
}
EOF
fi
