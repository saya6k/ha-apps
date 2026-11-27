# Code Interpreter

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

A sandboxed code runner for Assist conversation agents over MCP. The agent
writes one JavaScript script per call that can read and control Home
Assistant (only what the person speaking may use), run Python for analysis
and charts (pandas, numpy, scikit-learn, matplotlib, …), and exchange files
through `/share`. Each session runs in a bubblewrap sandbox with no network
by default and a JSONL audit log. Runs with protection mode on.

## ⚠️ THIS IS A BETA VERSION

This build comes from the beta channel — a pre-release (rc) of this app.

- It may not work at all.
- It might stop working or change without notice.
- It could have a negative impact on your system.

If you want the stable release: <https://github.com/saya6k/ha-apps>

## Quick start

1. Install **Code Interpreter** from the app store and click **Start**.
2. Add the discovered **Model Context Protocol** integration under
   **Settings → Devices & services**.
3. Add the **Model Context Protocol Server** integration, so scripts can
   reach Home Assistant.
4. Enable the tools for your Assist conversation agent and ask it to turn
   off every light but one room, analyze a file from `/share`, or chart
   last week's energy use.

See **[DOCS.md](DOCS.md)** for tools, limits, network access and the
security model.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
