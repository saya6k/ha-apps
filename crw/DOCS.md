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
  `web_search` and `web_scrape`, plus `video_search` / `image_search` /
  `news_search` / `wiki_search` when their providers are configured
  (a tool with no providers is not offered to the agent at all)

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
| `brave_api_key` | empty | Optional [Brave Search API](https://brave.com/search/api/) key — adds the Brave API as an extra `web_search` source |
| `flickr_api_key` | empty | Optional [Flickr API](https://www.flickr.com/services/api/) key — adds Flickr as an extra `image_search` provider |
| `image_search_providers` | empty | Providers for `image_search` (google, bing, naver, baidu, flickr, unsplash, …). Empty = tool disabled |
| `max_search_results` | `3` | Upper bound on results any search tool returns (1-6) |
| `news_search_providers` | empty | Providers for `news_search` (google, naver, reuters, yahoo, …). Empty = tool disabled |
| `outgoing_proxy` | empty | HTTP/SOCKS proxy URL for all outgoing search and scrape traffic — useful when engines or sites block your network's address (anti-bot). Empty = direct |
| `safe_search` | `1` | SearXNG safe search: 0 off, 1 moderate, 2 strict |
| `video_search_providers` | empty | Providers for `video_search` (youtube, naver, vimeo, bilibili, …) — picking `naver` searches Naver Video, etc. Empty = tool disabled |
| `wiki_search_providers` | empty | Wikis for `wiki_search` (wikipedia, wiktionary, …). Empty = tool disabled |
| `youtube_api_key` | empty | Optional [YouTube Data API v3](https://developers.google.com/youtube/v3) key — adds the official API as an extra `video_search` provider |

## Privacy

Search queries go through the bundled SearXNG instance directly to the search
engines it aggregates — no third-party search API is required, and nothing
is logged outside the container. The optional `*_api_key` options send
queries to that provider's official API when set.

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
  its own. If it happens constantly, set `outgoing_proxy`.
