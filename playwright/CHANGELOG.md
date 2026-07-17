# Changelog

Releases are tracked in
[ha-app-playwright releases](https://github.com/saya6k/ha-app-playwright/releases).

## [0.1.1](https://github.com/saya6k/ha-app-playwright/releases/tag/v0.1.1)

First stable release.

- Promoted out of experimental after successful HA end-to-end verification: conversation agent logged into the demo site via {{secret:...}} references with no secret values in the conversation or add-on logs; ingress session viewer confirmed live (screencast + timeline + kill switch).
- Identical runtime content to v0.1.1-rc.1 plus the stage promotion.

**Full Changelog**: https://github.com/saya6k/ha-app-playwright/compare/v0.1.0...v0.1.1

## [0.1.1-rc.1](https://github.com/saya6k/ha-app-playwright/releases/tag/v0.1.1-rc.1)

Beta-channel exercise of the release pipeline — identical content to v0.1.0.

## [0.1.0](https://github.com/saya6k/ha-app-playwright/releases/tag/v0.1.0)

Initial release — Playwright browser automation over MCP with domain
allowlist, bridge-side secret injection (local/1Password/Bitwarden), and
an ingress session viewer.
