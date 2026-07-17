# Wardrowbe

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

Self-hosted AI-powered wardrobe management. Snap photos of your clothes, let AI
tag them, and get daily outfit suggestions based on weather and occasion.

Upstream: <https://github.com/Anyesh/wardrowbe>

## ⚠️ THIS IS A BETA VERSION

This build comes from the beta channel — a pre-release (rc) of this app.

- It may not work at all.
- It might stop working or change without notice.
- It could have a negative impact on your system.

If you want the stable release: <https://github.com/saya6k/ha-apps>

## Quick start

1. Install **Wardrowbe** from the add-on store.
2. Configure the AI endpoint (defaults to a local Ollama on the HA host).
3. Click **Start**, then open Wardrowbe from the sidebar panel.

## Key paths

| HA Mount | Container Path | Content |
|----------|----------------|---------|
| `addon_config` | `/config/` | Secrets, persistent config |
| `data` | `/data/photos/` | Wardrobe photos |
| `share` | `/share/wardrowbe/backups/` | DB exports |
| `data` | `/data/` | PostgreSQL, Redis (internal) |

See **[DOCS.md](DOCS.md)** for full configuration, OIDC setup, architecture, and
troubleshooting.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
