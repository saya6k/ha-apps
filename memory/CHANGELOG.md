# Changelog

## [0.2.0](https://github.com/saya6k/ha-app-memory/releases/tag/v0.2.0)

## What's Changed

## New Features

* feat: switch the default embedding model to EmbeddingGemma 2 (#11) @saya6k
* feat: optional query/document prefixes for asymmetric embedding models (#10) @saya6k

## Maintenance

* chore: bump llama.cpp b10199 → b11496 (#9) @saya6k

## Upgrade notes

The default embedding model is now **EmbeddingGemma 2** (768 dimensions, ~296 MiB download, ~460 MiB sidecar memory — about half of before). It finds facts stored in Korean much more reliably.

- **Never changed the add-on configuration?** Nothing to do. On the first start every stored fact is re-embedded with the new model automatically.
- **Saved the configuration before?** Your saved settings still point at Qwen3, but the new `query_prefix` / `document_prefix` options take EmbeddingGemma 2's values. Either use **⋮ → Reset to defaults** in the Configuration tab to switch, or clear both prefixes to stay on Qwen3.
- The old model file `/data/models/Qwen3-Embedding-0.6B-Q8_0.gguf` (~609 MiB) is not removed automatically.

See DOCS → *Upgrading from Qwen3-Embedding* for details.

**Full Changelog**: https://github.com/saya6k/ha-app-memory/compare/v0.1.1...v0.2.0

## [0.1.1](https://github.com/saya6k/ha-app-memory/releases/tag/v0.1.1)

Fix OpenAI function schema compatibility for memory search limits.

## [0.1.0](https://github.com/saya6k/ha-app-memory/releases/tag/v0.1.0)

First stable release.

Personal fact memory for Home Assistant Assist, over MCP (streamable HTTP),
with vector semantic search. Embeddings are produced by a local llama.cpp
sidecar running Qwen3-Embedding-0.6B — no external API, no internet at query
time, no API key.

## What it does

Six tools, namespaced by Home Assistant as `memory__*`:
`save`, `get`, `search`, `similar`, `update`, `delete`.

Search matches by meaning and works across languages — a fact stored in Korean
is found by an English question about the same thing.

## Notes

- First boot downloads ~609 MiB and needs roughly 890 MiB resident once loaded.
- Changing the embedding model or its dimensions re-embeds every stored fact
  automatically. Nothing is lost, and a failure part-way leaves the database
  untouched.
- The embedding sidecar binds a unix socket rather than a TCP port, so it has
  no network address at all.

Verified in CI on both `amd64` and `aarch64`: image build plus a full container
smoke test with the real model download and real embeddings.

See [memory/DOCS.md](memory/DOCS.md) for install and options.

## Changes since v0.1.0-rc.0

* fix: put the wordmark next to the logo glyph (#5) @saya6k
* feat: add the catalog sync assets (#4) @saya6k
* chore: match the standard README, untrack SPEC.md (#3) @saya6k
* chore: untrack tasks/ (#2) @saya6k

