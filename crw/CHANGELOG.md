# Changelog

Releases are tracked in
[ha-app-crw releases](https://github.com/saya6k/ha-app-crw/releases).

## [0.1.0](https://github.com/saya6k/ha-app-crw/releases/tag/v0.1.0)

Initial release — CRW Web Tools for Home Assistant.

- `web_search` / `web_scrape` MCP tools (streamable HTTP `/mcp`, port 8099)
  for Assist conversation agents
- Bundles crw-server v0.25.1 (prebuilt, checksum-pinned) + SearXNG 2026.5.9
  per the fastcrw sidecar pattern
- Connect via the Model Context Protocol integration:
  `http://03f32180-crw:8099/mcp`
