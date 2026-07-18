# Changelog

Releases are tracked in
[ha-app-crw releases](https://github.com/saya6k/ha-app-crw/releases).

## [0.3.0](https://github.com/saya6k/ha-app-crw/releases/tag/v0.3.0)

## What's Changed

## New Features

* feat(crw)!: fixed web engine set + named API key options (#5) @saya6k
* feat(crw): video/image/news/wiki search tools with provider options (#4) @saya6k

## Bug Fixes

* fix(crw): key-gated engines need legal names (no underscores) (#6) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-crw/compare/v0.2.0...v0.3.0

## [0.2.0](https://github.com/saya6k/ha-app-crw/releases/tag/v0.2.0)

## What's Changed

## New Features

* feat(crw): engine multi-select whitelist + graceful crash shutdown (#3) @saya6k

## Bug Fixes

* fix(crw): remove the whole qwant engine family together (#2) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-crw/compare/v0.1.0...v0.2.0

## [0.1.0](https://github.com/saya6k/ha-app-crw/releases/tag/v0.1.0)

Initial release — CRW Web Tools for Home Assistant.

- `web_search` / `web_scrape` MCP tools (streamable HTTP `/mcp`, port 8099)
  for Assist conversation agents
- Bundles crw-server v0.25.1 (prebuilt, checksum-pinned) + SearXNG 2026.5.9
  per the fastcrw sidecar pattern
- Connect via the Model Context Protocol integration:
  `http://03f32180-crw:8099/mcp`
