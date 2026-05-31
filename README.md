# Home Assistant add-on repository

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/saya6k)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Node.js](https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![Shell](https://img.shields.io/badge/Shell-4EAA25?style=for-the-badge&logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)

A small collection of self-hosted Home Assistant add-ons. Each top-level
directory is one independent add-on with its own version, Dockerfile,
and release cycle.

## Add-ons in this repository

| Directory | Add-on |
| --- | --- |
| [`llm-conversation-agent/`](llm-conversation-agent/) | Wyoming conversation agent backed by any OpenAI-compatible LLM. Delegates entity exposure to Home Assistant's built-in `mcp_server`. |
| [`rethink/`](rethink/) | Packages [`anszom/rethink`](https://github.com/anszom/rethink) so supported LG ThinQ appliances talk to Home Assistant over MQTT instead of LG's cloud. |
| [`supertonic/`](supertonic/) | Lightweight multilingual Wyoming TTS service running the [`supertonic-mnn`](https://github.com/vra/supertonic-mnn) engine. |
| [`wardrowbe/`](wardrowbe/) | Self-hosted AI-powered wardrobe management. Packages [`Anyesh/wardrowbe`](https://github.com/Anyesh/wardrowbe) (Postgres, Redis, FastAPI, arq, Next.js, nginx) in a single container. |
| [`zensical/`](zensical/) | Renders `/config/docs/` as a [Zensical](https://zensical.org/) site served through the Home Assistant ingress side panel. |

Each directory's `DOCS.md` is rendered as the Documentation tab inside
Home Assistant; `CHANGELOG.md` is rendered in the add-on UI; `AGENTS.md`
is for humans and AI agents working on the code.

## Installing

In Home Assistant, go to **Settings → Add-ons → Add-on Store**, open the
overflow menu (⋮) in the top right, choose **Repositories**, paste the
URL of this repository, and click **Add**. The add-ons listed above will
appear under their own section in the store.

## Contributing

PRs welcome — please read [CONTRIBUTING.md](CONTRIBUTING.md) first. The
key requirement is **Conventional Commit titles with the add-on slug as
the scope** (e.g. `feat(supertonic): add Korean voice F5`); release-please
routes commits to per-add-on changelogs based on that scope.

Security reports: see [SECURITY.md](SECURITY.md) — use GitHub's private
vulnerability reporting, not a public issue.

## License

The root [LICENSE](LICENSE) (MIT) covers repository scaffolding. Some
add-on subdirectories carry their own licenses that override the root for
that directory's files — see the table inside `LICENSE`.
