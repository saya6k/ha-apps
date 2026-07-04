# Home Assistant App: Registry Cache

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/saya6k)

[![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=4fdf9462_registry-cache&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps%23beta)

A pull-through cache for `docker.io` and `ghcr.io` container registries.
Repeated image pulls are served from local disk instead of upstream, behind
a single nginx-fronted port, with per-registry storage isolation and
build-time-extensible support for additional upstreams.

## ⚠️ THIS IS A BETA VERSION

This build comes from the beta channel — a pre-release (rc) of this app.

- It may not work at all.
- It might stop working or change without notice.
- It could have a negative impact on your system.

If you want the stable release: <https://github.com/saya6k/ha-apps>

See [DOCS.md](DOCS.md) for client setup and [SPEC.md](SPEC.md) for the full
design.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
