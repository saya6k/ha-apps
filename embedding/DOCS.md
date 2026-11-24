# Embedding

A shared text embedding server for Home Assistant and other apps. It runs a
local [llama.cpp](https://github.com/ggml-org/llama.cpp) server with
[EmbeddingGemma 2](https://huggingface.co/google/embeddinggemma-2) and answers
the OpenAI-compatible `POST /v1/embeddings`, so every app that searches by
meaning can use one model instead of loading its own. There is no external API
and no internet access at query time.

## Install (local app)

1. Copy the `embedding/` directory of this repo into your HA `/addons/` share,
   so you end up with `/addons/embedding/config.yaml`.
2. **Settings → Apps → App Store → ⋮ → Check for updates**, then open the local
   **Embedding** app and press **Install**.
3. Start it, and watch the **Log** tab for the first boot (see below).

## First boot

The embedding model is not baked into the image. On first start the app
downloads it into `/data/models/` (persists across app updates):

```text
Embedding model not present — downloading ggml-org/embeddinggemma-2-GGUF/embeddinggemma-2-Q8_0.gguf
This is a one-time download of several hundred MB and can take a while.
Model ready: /data/models/embeddinggemma-2-Q8_0.gguf
Starting embedding server on :8080 (threads=4, context=1024, parallel=1, no API key)
...
llama_server: listening on http://0.0.0.0:8080
```

The default model is ~296 MiB (Q8_0). Fetching it is a one-shot startup step: if
the download fails or the checksum does not match, the app **stops** with the
error on screen rather than retrying. A wrong `model_repo`, `model_file` or
`model_sha256` is a configuration mistake, and retrying it would just
re-download hundreds of megabytes every few seconds.

## Using it

The server is reached over Home Assistant's internal network at:

```text
http://<hostname>:8080/v1
```

`<hostname>` is shown on the app's **Info** tab — for an app installed from a
repository it looks like `a0d7b954-embedding`, for a local app
`local-embedding`. Give a client that URL as an OpenAI-compatible embeddings
API. The `model` field of a request is accepted but ignored: the server always
answers with the configured model.

```shell
curl http://<hostname>:8080/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"input": ["task: search result | query: 거실 불 꺼줘"]}'
```

`input` can be one string or a list. Vectors are 768 values long and already
normalised to unit length, so the dot product of two vectors is their cosine
similarity.

### Task prefixes

EmbeddingGemma 2 is trained to see a short task prefix in front of the text,
and a different one for a search query than for a stored passage. The server
does **not** add them — the client does, so each client can choose its own
task:

```yaml
query: "task: search result | query: "     # a search query
passage: "title: none | text: "            # a stored fact, document or tool description
```

Keep the trailing space. Without the prefixes, search still works but is
noticeably less precise.

### The Memory app

[Memory](https://github.com/saya6k/ha-app-memory) can use this server instead
of its own built-in one:

```yaml
embedding_provider: openai
embedding_url: http://<hostname>:8080/v1
embedding_model: embeddinggemma-2-Q8_0.gguf
```

Leave its `query_prefix` and `document_prefix` as they are. With the same model
file the vectors are the same as before, so nothing needs to be re-embedded.

## Memory

The server needs about **430 MiB** once the model is loaded. Embedding a text
temporarily takes more, growing with the length of the longest text it has
been sent, not with `context_size` itself. Measured with the default model on
aarch64:

| Longest input | Peak resident size | Time (4 threads) |
|---|---|---|
| a short question | ~430 MiB | ~40 ms |
| ~450 tokens | ~920 MiB | ~1.4 s |
| ~1000 tokens | ~1.5 GiB | ~3.8 s |
| ~1600 tokens | ~2.2 GiB | ~8 s |

`context_size` is the cap: an input longer than it is refused with an error
instead of being cut short, which also bounds the peak. The default, 1024,
keeps it near 1.5 GiB. Raise it only if a client really sends longer texts.
`parallel` multiplies the cap, since each concurrent request can be that long.

If the app log shows:

```text
Service llama-server exited with code 256 (by signal 9)
The embedding server was killed with SIGKILL (9).
```

then the server was killed from outside the process — nearly always the
out-of-memory killer. Lower `context_size` or `parallel`, free up memory, or
drop to a smaller quantization.

## Options

| Option | Default | Notes |
|---|---|---|
| `model_repo` | `ggml-org/embeddinggemma-2-GGUF` | Hugging Face repo |
| `model_file` | `embeddinggemma-2-Q8_0.gguf` | File within that repo |
| `model_sha256` | *(unset)* | Optional. When set, the download must match it or startup fails. When unset, the download is not verified and the actual hash is printed so you can pin it. |
| `threads` | `4` | CPU threads |
| `context_size` | `1024` | The longest single input, in tokens. See [Memory](#memory). |
| `parallel` | `1` | Requests embedded at the same time |
| `api_key` | *(unset)* | Optional. When set, clients must send `Authorization: Bearer <key>`. |
| `log_level` | *(unset → `info`)* | Optional. `trace` / `debug` / `info` / `notice` / `warning` / `error` / `fatal` |

`model_sha256`, `api_key` and `log_level` stay hidden until you add them (use
**Show unused optional configuration options** in the app's Configuration
tab).

### Changing the model

Vectors from different models — and from different quantizations of the same
model — cannot be compared. After changing `model_repo` or `model_file`, every
client has to re-embed what it stored, and its prefixes and vector size have to
match the new model. The Memory app does this by itself on its next start when
its `embedding_model` changes too.

## Where data lives

- `/data/models/` — the downloaded GGUF model

It is left out of the app's backups: restoring a backup downloads the model
again on the next start, so that start needs internet access.

## Security notes

- Port 8080 is internal to the Home Assistant network and is not published to
  the host. Any app on that network can reach it.
- Set `api_key` before mapping the port to the host. The key is passed to the
  server through the environment, so it does not appear in the process list,
  and it is never logged.
- `/health` answers without a key, so a client can wait for the server to come
  up.
