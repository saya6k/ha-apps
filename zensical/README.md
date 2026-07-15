# Home Assistant Add-on: Zensical

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/saya6k)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Shell](https://img.shields.io/badge/Shell-4EAA25?style=for-the-badge&logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)

[![Show add-on](https://my.home-assistant.io/badges/supervisor_addon.svg)](https://my.home-assistant.io/redirect/supervisor_addon/?addon=4fdf9462_zensical&repository_url=https%3A%2F%2Fgithub.com%2Fsaya6k%2Fha-apps%23beta)

Renders `/config/docs/` as a [Zensical][zensical] site — the Material
for MkDocs team's successor SSG — and serves it through the Home
Assistant ingress side panel. Edits are picked up within ~1 second;
refresh the browser to see the rebuild.

The bundled config is a `zensical.toml`. Most knobs map 1:1 from
`mkdocs.yml` so users coming from Material for MkDocs will recognise
the structure (`site_name`, `theme.features`, `theme.palette`,
`markdown_extensions.*`).

Configuration, file layout, and the alpha-status caveat are in `DOCS.md`.

## ⚠️ THIS IS A BETA VERSION

This build comes from the beta channel — a pre-release (rc) of this app.

- It may not work at all.
- It might stop working or change without notice.
- It could have a negative impact on your system.

If you want the stable release: <https://github.com/saya6k/ha-apps>

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[zensical]: https://zensical.org/
