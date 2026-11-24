# Embedding

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

A shared text embedding server for Home Assistant and other apps. It runs
[EmbeddingGemma 2](https://huggingface.co/google/embeddinggemma-2) on a local
[llama.cpp](https://github.com/ggml-org/llama.cpp) server and answers the
OpenAI-compatible `/v1/embeddings`, so apps that search by meaning can share
one model instead of each loading its own — no external API and no internet
access at query time.

Upstream: <https://github.com/ggml-org/llama.cpp> · <https://huggingface.co/ggml-org/embeddinggemma-2-GGUF>

## ⚠️ THIS IS A BETA VERSION

This build comes from the beta channel — a pre-release (rc) of this app.

- It may not work at all.
- It might stop working or change without notice.
- It could have a negative impact on your system.

If you want the stable release: <https://github.com/saya6k/ha-apps>

## Quick start

1. Install **Embedding** from the app store and click **Start**. The first
   start downloads the embedding model (~296 MiB), so give it a few minutes.
2. Point a client at `http://4fdf9462-embedding:8080/v1` as an
   OpenAI-compatible embeddings API.

See **[DOCS.md](DOCS.md)** for configuration, memory requirements, and the
task prefixes the default model expects.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
