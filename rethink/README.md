# Home Assistant App: rethink

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

[![Built with Claude Code](https://img.shields.io/badge/Built%20with%20Claude%20Code-D97757?style=for-the-badge&logo=claude&logoColor=white)](https://claude.ai/code)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/saya6k)
[![Node.js](https://img.shields.io/badge/Node.js-339933?style=for-the-badge&logo=nodedotjs&logoColor=white)](https://nodejs.org/)
[![Shell](https://img.shields.io/badge/Shell-4EAA25?style=for-the-badge&logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)

Home Assistant app that runs [`anszom/rethink`](https://github.com/anszom/rethink)
as a local replacement for LG's ThinQ cloud, so supported LG appliances can be
controlled fully on your LAN through MQTT — no LG cloud, no internet
dependency for the appliance itself.

Only models that rethink has reverse-engineered work; for the rest, keep using
your existing PAT-based ThinQ integration. Configuration, DNS setup
(Pi-hole / AdGuard Home), and the supported-device list are in `DOCS.md`.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
