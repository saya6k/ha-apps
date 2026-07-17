# CRW Web Tools

Web search and page scraping for Assist conversation agents, supplied over
MCP (Model Context Protocol).

## How it works

One container runs three services, mirroring crw's own docker-compose stack:

- **SearXNG** — privacy-respecting meta search (loopback only, same version
  crw's sidecar pins)
- **crw-server** — fast Rust scraper; search traffic flows exclusively
  through its `/v1/search`, backed by the bundled SearXNG
- **mcp-bridge** — MCP server (streamable HTTP at `/mcp`, port 8099) exposing
  two tools: `web_search` and `web_scrape`

Home Assistant's official **Model Context Protocol** integration connects to
the bridge and makes both tools available to conversation agents.

## Connect to Home Assistant

1. Start this add-on.
2. Go to **Settings → Devices & services → Add integration** and pick
   **Model Context Protocol**.
3. Enter the URL: `http://03f32180-crw:8099/mcp`
4. In your Assist pipeline's conversation agent, enable the new tool provider.

No port mapping is needed — Home Assistant reaches the add-on over the
internal network. Only map port 8099 if an MCP client *outside* the host
needs access.

## Options

| Option | Default | Description |
|---|---|---|
| `max_search_results` | `3` | Upper bound on results `web_search` returns (1-6) |
| `outgoing_proxy` | empty | HTTP/SOCKS proxy URL for all outgoing search and scrape traffic — useful when engines or sites block your network's address (anti-bot). Empty = direct |
| `safe_search` | `1` | SearXNG safe search: 0 off, 1 moderate, 2 strict |
| `search_engines` | empty | Multi-select of every SearXNG engine in the bundled version — selected engines become the whole active set (`keep_only`, force-enabled) and required engine dependencies are added automatically. Empty = SearXNG defaults minus a few engines that fail or spam errors in typical deployments: `wikidata` (startup 403), `ahmia`/`torch` (need a Tor proxy), `startpage` (broken response parser), `qwant` (instant rate limiting) |

## Privacy

Search queries go through the bundled SearXNG instance directly to the search
engines it aggregates — no third-party search API, no API keys, and nothing
is logged outside the container.

## Licenses

This add-on bundles [crw](https://github.com/us/crw) (AGPL-3.0) and
[SearXNG](https://github.com/searxng/searxng) (AGPL-3.0). Source for both is
available at the linked repositories; the add-on's own source lives at
<https://github.com/saya6k/ha-app-crw>. The icon and logo are the CRW brand
assets from the [us/crw](https://github.com/us/crw) repository (AGPL-3.0).

## Troubleshooting

- **Tools don't appear in Assist** — verify the MCP integration is configured
  with the exact URL above and that the add-on log shows the bridge listening
  on 8099.
- **Search returns nothing** — some SearXNG engines rate-limit; retry or
  lower `max_search_results`.
- **`Too many request (suspended_time=180)` in the log** — an engine
  rate-limited your address; SearXNG suspends it for 180 s and recovers on
  its own. If it happens constantly, set `outgoing_proxy` or trim
  `search_engines` to engines that tolerate your network.
