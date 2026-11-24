# Changelog

## [0.1.0-rc.0](https://github.com/saya6k/ha-app-embedding/releases/tag/v0.1.0-rc.0)

## What's Changed

First release: a shared text embedding server for Home Assistant and other apps.

* EmbeddingGemma 2 (Q8_0) on llama.cpp b11496, serving the OpenAI-compatible `/v1/embeddings` on port 8080 of the Home Assistant network
* Same build and flags as the Memory app's built-in sidecar, so Memory can switch to it without re-embedding
* `context_size` defaults to 1024 tokens; longer inputs are refused rather than cut short
* Optional `api_key`, passed through the environment so it stays out of the process list

