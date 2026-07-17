# CRW Web Tools

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

Web search and page scraping for Assist conversation agents over MCP. Bundles
[SearXNG](https://github.com/searxng/searxng) meta search and the
[crw](https://github.com/us/crw) scraper in one container, exposed as
`web_search` and `web_scrape` tools via streamable HTTP.

Upstream: <https://github.com/us/crw> · <https://github.com/searxng/searxng>

## Quick start

1. Install **CRW Web Tools** from the add-on store and click **Start**.
2. Add the **Model Context Protocol** integration in Home Assistant with URL
   `http://03f32180-crw:8099/mcp`.
3. Enable the tools for your Assist conversation agent.

See **[DOCS.md](DOCS.md)** for configuration, architecture, and
troubleshooting.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
