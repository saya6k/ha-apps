# Home Assistant App: OpenTelemetry Collector

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/saya6k)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-000000?style=for-the-badge&logo=opentelemetry&logoColor=white)](https://opentelemetry.io)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Shell](https://img.shields.io/badge/Shell-4EAA25?style=for-the-badge&logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)

[![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=03f32180_otelcol&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps)

Packages [OpenTelemetry Collector Contrib](https://github.com/open-telemetry/opentelemetry-collector-releases)
as a Home Assistant add-on and bridges it to the HA WebSocket/REST API —
collecting logs, metrics, and traces from HA Core, the Supervisor, and every
add-on container, then exporting them via OTLP to Grafana LGTM (Loki, Tempo,
Mimir) or any OTLP-compatible backend.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
