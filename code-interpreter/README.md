# Code Interpreter

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

Stateful Python code execution for Assist conversation agents over MCP. Each
session runs in a bubblewrap sandbox inside the app, with no network by
default, an analysis stack preinstalled (pandas, numpy, scikit-learn,
matplotlib, …), files exchanged through `/share`, and a JSONL audit log.
Runs with protection mode on.

## Quick start

1. Install **Code Interpreter** from the app store and click **Start**.
2. Add the discovered **Model Context Protocol** integration under
   **Settings → Devices & services**.
3. Enable the tools for your Assist conversation agent and ask it to
   calculate, analyze a file from `/share`, or draw a chart.

See **[DOCS.md](DOCS.md)** for tools, limits, network access and the
security model.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
