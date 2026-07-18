# Changelog

Releases are tracked in
[ha-app-playwright releases](https://github.com/saya6k/ha-app-playwright/releases).

## [0.3.0](https://github.com/saya6k/ha-app-playwright/releases/tag/v0.3.0)

## What's Changed

## New Features

* feat(playwright): secrets v3 — secretd privilege separation + embedded 1Password Connect (#5) @saya6k

## Maintenance

* chore(playwright): transparent icon/logo from official Playwright mark (#4) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-playwright/compare/v0.2.0...v0.3.0

## [0.2.0](https://github.com/saya6k/ha-app-playwright/releases/tag/v0.2.0)

## What's Changed

## New Features

* feat(playwright): secrets v2 — Vaultwarden/1P Connect providers, env-wins config, passkey client (#3) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-playwright/compare/v0.1.2...v0.2.0

## [0.1.2](https://github.com/saya6k/ha-app-playwright/releases/tag/v0.1.2)

## What's Changed

## Bug Fixes

* fix(playwright): stop mcp-bridge crash-loop on missing secret config (#2) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-playwright/compare/v0.1.1...v0.1.2

## [0.1.1](https://github.com/saya6k/ha-app-playwright/releases/tag/v0.1.1)

First stable release.

- Promoted out of experimental after successful HA end-to-end verification: conversation agent logged into the demo site via {{secret:...}} references with no secret values in the conversation or add-on logs; ingress session viewer confirmed live (screencast + timeline + kill switch).
- Identical runtime content to v0.1.1-rc.1 plus the stage promotion.

**Full Changelog**: https://github.com/saya6k/ha-app-playwright/compare/v0.1.0...v0.1.1

## [0.1.0](https://github.com/saya6k/ha-app-playwright/releases/tag/v0.1.0)

Initial release — Playwright browser automation over MCP with domain
allowlist, bridge-side secret injection (local/1Password/Bitwarden), and
an ingress session viewer.
