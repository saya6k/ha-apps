# Changelog

## [0.1.0-rc.0](https://github.com/saya6k/ha-app-memory/releases/tag/v0.1.0-rc.0)

First release candidate.

Personal fact memory for Home Assistant Assist, over MCP (streamable HTTP),
with vector semantic search. Embeddings are produced by a local llama.cpp
sidecar running Qwen3-Embedding-0.6B — no external API, no internet at query
time, no API key.

## What it does

Six tools, namespaced by Home Assistant as `memory__*`:
`save`, `get`, `search`, `similar`, `update`, `delete`.

Search matches by meaning and works across languages — a fact stored in Korean
is found by an English question about the same thing (verified end to end on a
real Assist conversation, and in CI on both architectures).

## Verified in CI

Both `amd64` and `aarch64` build the image and pass the full container smoke
test, including the real model download and real embeddings.

## Notes for this RC

- First boot downloads ~609 MiB and needs roughly 890 MiB resident once loaded.
- Changing the embedding model or its dimensions re-embeds every stored fact
  automatically; nothing is lost and a failure part-way leaves the database
  untouched.
- The embedding sidecar binds a unix socket rather than a TCP port, so it has
  no network address at all.

See [memory/DOCS.md](memory/DOCS.md) for install and options.

