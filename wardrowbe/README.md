# Wardrowbe — Home Assistant Add-on

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/saya6k)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)

Self-hosted AI-powered wardrobe management.
Snap photos of your clothes, let AI tag them, and get daily outfit suggestions.

Upstream: <https://github.com/Anyesh/wardrowbe>

## Quick Start

1. Copy this folder into `/addons/local/` on your HA instance.
2. **Settings → Add-ons → Add-on Store** → ⋮ → **Check for updates**.
3. Install **Wardrowbe**, configure AI endpoint, click **Start**.
4. Open via the sidebar panel.

## Updating wardrowbe version

Edit `build.yaml` and rebuild:

```yaml
args:
  WARDROWBE_VERSION: wardrowbe-v1.2.2   # ← change to desired tag or branch
```

## Key paths

| HA Mount | Container Path | Content |
|----------|---------------|---------|
| `addon_config` | `/config/` | Secrets, persistent config |
| `media` | `/media/wardrowbe/` | Wardrobe photos |
| `share` | `/share/wardrowbe/backups/` | DB exports |
| `data` | `/data/` | PostgreSQL, Redis (internal) |

See **[DOCS.md](DOCS.md)** for full configuration, OIDC setup, architecture, and troubleshooting.
