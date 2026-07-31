# Memory

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

Personal fact memory for Assist conversation agents over MCP. Facts are stored
with vector embeddings and retrieved by meaning rather than by keyword, so the
conversation agent can remember things across turns and across conversations.

Embeddings are produced locally by a [llama.cpp](https://github.com/ggml-org/llama.cpp)
sidecar running [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF) —
no external API, no API key, and no internet access at query time. Search works
across languages: a fact stored in Korean is found by an English question about
the same thing.

Upstream: <https://github.com/ggml-org/llama.cpp> · <https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF>

## ⚠️ THIS IS A BETA VERSION

This build comes from the beta channel — a pre-release (rc) of this app.

- It may not work at all.
- It might stop working or change without notice.
- It could have a negative impact on your system.

If you want the stable release: <https://github.com/saya6k/ha-apps>

## Quick start

1. Install **Memory** from the add-on store and click **Start**. The first
   start downloads the embedding model (~609 MiB), so give it a few minutes.
2. Add the **Model Context Protocol** integration in Home Assistant with URL
   `http://4fdf9462-memory:8099/mcp`.
3. Enable the tools for your Assist conversation agent.

Ask it to remember something, then ask about it in a later conversation.

See **[DOCS.md](DOCS.md)** for configuration, memory requirements, and
what happens when you change the embedding model.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
