# Memory

Personal fact memory for Home Assistant Assist, exposed over MCP with vector
semantic search. Embeddings are produced by a local llama.cpp sidecar — there is
no external API and no internet access at query time.

## Install (local add-on)

1. Copy the `memory/` directory of this repo into your HA `/addons/` share, so
   you end up with `/addons/memory/config.yaml`.
2. **Settings → Add-ons → Add-on Store → ⋮ → Check for updates**, then open the
   local **Memory** add-on and press **Install**.
3. Start it, and watch the **Log** tab for the first boot (see below).

## First boot

The embedding model is not baked into the image. On first start the add-on
downloads it into `/data/models/` (persists across add-on updates) and verifies
its SHA-256 before use:

```text
Embedding model not present — downloading Qwen/Qwen3-Embedding-0.6B-GGUF/...
This is a one-time download of several hundred MB and can take a while.
Model verified and ready: /data/models/Qwen3-Embedding-0.6B-Q8_0.gguf
Starting embedding sidecar on /run/llama/embed.sock (threads=4)
...
Embedding sidecar is ready.
Starting MCP server on 0.0.0.0:8099 (/mcp)
```

The default model is ~609 MiB (Q8_0). Fetching it is a one-shot startup step: if
the download fails or the checksum does not match, the add-on **stops** with the
error on screen rather than retrying. That is deliberate — a wrong `model_repo`,
`model_file` or `model_sha256` is a configuration mistake, and retrying it would
just re-download hundreds of megabytes every few seconds.

## Memory

Measured resident size of the embedding sidecar with the default model, after
serving a request: **about 890 MiB**. The sidecar is started with flags tuned
for embeddings (single slot, no prompt cache, no weight repacking); the stock
llama.cpp generation defaults would use ~1.32 GiB for the same work.

If the add-on log shows:

```text
Service llama-server exited with code 256 (by signal 9)
The embedding sidecar was killed with SIGKILL (9).
```

then the sidecar was killed from outside the process — nearly always the
out-of-memory killer. Note that llama.cpp reports the *host's* free memory, so
its "no changes needed" line can look fine even when the add-on's own container
limit is much smaller. Either free up memory, or drop to a smaller quantization:

| `model_repo` | `model_file` | `model_sha256` | Size |
|---|---|---|---|
| `Qwen/Qwen3-Embedding-0.6B-GGUF` | `Qwen3-Embedding-0.6B-Q8_0.gguf` | `06507c7b…9c3e439` | 609 MiB |
| `Mungert/Qwen3-Embedding-0.6B-GGUF` | `Qwen3-Embedding-0.6B-q5_k_m.gguf` | `c2618de5cb2c4e09391c727d89d329f35d0e1190340073c3ccd1427b5e0375cc` | 425 MiB |
| `Mungert/Qwen3-Embedding-0.6B-GGUF` | `Qwen3-Embedding-0.6B-q4_k_m.gguf` | `c608745221a03d45ee7328aab5ae180ef5db54c9a47eda43ef05f73156ba824b` | 376 MiB |

All three are the same model at 1024 dimensions, so `embedding_dimensions` stays
`1024`. Heavier quantization does cost retrieval accuracy — Q8_0 is close to
lossless, Q4 measurably less precise — so only step down if memory forces it.
Changing quantization changes the vectors, so re-embed anything already stored.

## Connecting it to Assist

The add-on announces its MCP endpoint to Home Assistant via Supervisor
discovery on every start. If HA does not pick it up automatically, add it
manually with the URL printed in the log:

```text
http://<add-on hostname>:8099/mcp
```

Then attach it to your conversation agent as an MCP server, and the six tools
become available to the LLM.

## Tools

| Tool | Purpose |
|---|---|
| `save` | Store a fact (`content`, optional `tags`); embeds and returns an id |
| `get` | Fetch a single fact by id |
| `search` | Semantic search by meaning, optional `tags` filter, `limit` (default 5, max 20) |
| `similar` | Facts similar to a given id, excluding itself |
| `update` | Change `content` and/or `tags`; re-embeds only when content changed |
| `delete` | Hard-delete one fact by id |

Search works across languages: a fact stored in Korean is retrieved by an
English question about the same thing, and vice versa.

## Options

| Option | Default | Notes |
|---|---|---|
| `model_repo` | `Qwen/Qwen3-Embedding-0.6B-GGUF` | Hugging Face repo |
| `model_file` | `Qwen3-Embedding-0.6B-Q8_0.gguf` | File within that repo |
| `model_sha256` | *(unset)* | Optional. When set, the download must match it or startup fails. When unset, the download is not verified and the actual hash is printed so you can pin it. |
| `embedding_dimensions` | `1024` | Must match the model's native output size |
| `threads` | `4` | CPU threads for the embedding sidecar |
| `log_level` | *(unset → `info`)* | Optional. `trace` / `debug` / `info` / `notice` / `warning` / `error` / `fatal`. Applies to both the MCP server and the embedding sidecar. |

`model_sha256` and `log_level` are optional and stay hidden until you add them
(use **Show unused optional configuration options** in the add-on's
Configuration tab).

### Changing the model

Existing vectors are **not** migrated, and vectors from a different embedding
model are not comparable even at the same width — so a model change means older
memories can no longer be found by meaning.

The add-on handles this for you. On start it compares the configured model
against the one recorded in the database, and if they differ it **re-embeds
every stored fact** from its content before the server comes up:

```text
[db-migrate] re-embedded 3/3 facts
[db-migrate] migrated 3 facts — embedding model changed
             ("Qwen3-Embedding-0.6B-Q8_0.gguf" -> "Qwen3-Embedding-0.6B-q4_k_m.gguf")
```

Changing `embedding_dimensions` is handled the same way — the vector table is
rebuilt at the new width. Nothing is lost, because the fact text itself is what
gets re-embedded. Note this also applies to changing quantization (Q8_0 → Q4),
since that produces different vectors too.

Migration takes roughly as long as saving that many facts did in the first
place, and only runs when something actually changed; an unchanged model logs
`up to date` and skips straight past.

If the sidecar fails part-way through, **the database is left exactly as it
was** — all the new vectors are computed before anything is written, so there is
no half-migrated state. The add-on stops with the error rather than starting on
a partly-rewritten memory.

## Where data lives

- `/data/facts.sqlite` — the facts and their vectors (SQLite + sqlite-vec)
- `/data/models/` — the downloaded GGUF model

Both survive add-on updates. Neither is exposed over the network.

## Security notes

- The MCP port (8099) is internal to the Home Assistant network and is not
  published to the host.
- The embedding sidecar listens on a **unix domain socket**
  (`/run/llama/embed.sock`, in a `0700` root-owned directory) rather than a TCP
  port, so it has no network address at all.
- Fact contents are never written to the log — only lengths and counts.
