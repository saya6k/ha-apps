# Home Assistant add-on repository

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-41BDF5?style=for-the-badge&logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Node.js](https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![Shell](https://img.shields.io/badge/Shell-4EAA25?style=for-the-badge&logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/saya6k)

A small collection of self-hosted Home Assistant add-ons. Source and CI
live in each app's own `ha-app-*` repository; this repo holds the catalog
metadata (`config.yaml`, docs, changelogs) that Home Assistant reads.

## Add-ons in this repository

| Directory | Add-on | |
| --- | --- | --- |
| [`livekit-wakeword/`](livekit-wakeword/) | Wyoming wake-word service. Runs the openWakeWord zoo plus custom `/share` models via an incremental bridge (~80 ms cadence). | [![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=03f32180_livekit-wakeword&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps) |
| [`nemotron-asr-c/`](nemotron-asr-c/) | Buffered Wyoming STT running NVIDIA Nemotron ASR on a pure C runtime ([`kdrkdrkdr/nemotron-asr-streaming.c`](https://github.com/kdrkdrkdr/nemotron-asr-streaming.c)), with hotword boosting. | [![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=03f32180_nemotron-asr-c&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps) |
| [`nemo-asr-cpp/`](nemo-asr-cpp/) | Streaming Wyoming STT running NVIDIA Nemotron ASR on the ggml runtime via [`mudler/parakeet.cpp`](https://github.com/mudler/parakeet.cpp), with hotword boosting. | [![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=03f32180_nemo-asr-cpp&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps) |
| [`otelcol/`](otelcol/) | OpenTelemetry Collector Contrib packaged as a HA add-on. Collects logs, metrics, and traces from HA Core, the Supervisor, and add-on containers; exports via OTLP. | [![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=03f32180_otelcol&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps) |
| [`supertonic/`](supertonic/) | Lightweight multilingual Wyoming TTS service running the [`supertonic-mnn`](https://github.com/vra/supertonic-mnn) engine. | [![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=03f32180_supertonic&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps) |
| [`voiceprint/`](voiceprint/) | Speaker-verifying Wyoming STT proxy — a pass-through gate that only forwards utterances from enrolled voices to a downstream ASR. | [![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=03f32180_voiceprint&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps) |
| [`wardrowbe/`](wardrowbe/) | Self-hosted AI-powered wardrobe management. Packages [`Anyesh/wardrowbe`](https://github.com/Anyesh/wardrowbe) (Postgres, Redis, FastAPI, arq, Next.js, nginx) in a single container. | [![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=03f32180_wardrowbe&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps) |
| [`zensical/`](zensical/) | Renders `/config/docs/` as a [Zensical](https://zensical.org/) site served through the Home Assistant ingress side panel. | [![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=03f32180_zensical&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps) |

Each directory's `DOCS.md` is rendered as the Documentation tab inside
Home Assistant; `CHANGELOG.md` is rendered in the add-on UI; `AGENTS.md`
is for humans and AI agents working on the code.

## Installing

[![Add repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps)

Or manually: go to **Settings → Add-ons → Add-on Store**, open the overflow
menu (⋮) in the top right, choose **Repositories**, paste the URL of this
repository, and click **Add**. The add-ons listed above will appear under
their own section in the store.

## Contributing

This is a personal add-on repository. **Direct contributions (PRs) are
limited to repository collaborators**; if you aren't one, please open an
issue instead of a pull request. Collaborators: read
[CONTRIBUTING.md](CONTRIBUTING.md) first. The key requirement is
**Conventional Commit titles with the add-on slug as the scope** (e.g.
`feat(supertonic): add Korean voice F5`).

Security reports: see [SECURITY.md](SECURITY.md) — use GitHub's private
vulnerability reporting, not a public issue.

## License

The root [LICENSE](LICENSE) (MIT) covers repository scaffolding. Some
add-on subdirectories carry their own licenses that override the root for
that directory's files — see the table inside `LICENSE`.
