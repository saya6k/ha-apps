# Changelog

## [0.2.0](https://github.com/saya6k/ha-app-crw/releases/tag/v0.2.0)

## What's Changed

## New Features

* feat(crw): engine multi-select whitelist + graceful crash shutdown (#3) @saya6k

## Bug Fixes

* fix(crw): remove the whole qwant engine family together (#2) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-crw/compare/v0.1.0...v0.2.0

## [0.2.0-rc.3](https://github.com/saya6k/ha-app-crw/releases/tag/v0.2.0-rc.3)

## What's Changed

## New Features

* feat(crw): engine multi-select whitelist + graceful crash shutdown (#3) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-crw/compare/v0.2.0-rc.2...v0.2.0-rc.3

## [0.2.0-rc.2](https://github.com/saya6k/ha-app-crw/releases/tag/v0.2.0-rc.2)

## What's Changed

## Bug Fixes

* fix(crw): remove the whole qwant engine family together (#2) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-crw/compare/v0.2.0-rc.1...v0.2.0-rc.2

## [0.2.0-rc.1](https://github.com/saya6k/ha-app-crw/releases/tag/v0.2.0-rc.1)

Release candidate — search customization & clean startup.

## Features
* `outgoing_proxy` option — HTTP/SOCKS egress proxy for search+scrape (anti-bot bypass)
* `search_engines` option — SearXNG engine keep_only list
* Settings rendered by a tested Python renderer (was sed)

## Fixes
* Default engine set drops noisy/broken engines: wikidata (startup 403), ahmia/torch (need Tor), startpage (broken parser), qwant (instant 429)
* crw waits for SearXNG readiness — no more UNREACHABLE warning at boot
* limiter.toml warning silenced; granian capped at 4 blocking threads

## Branding
* Transparent crw mark as icon/logo (AGPL brand assets from us/crw)

