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
Embedding model not present — downloading ggml-org/embeddinggemma-2-GGUF/...
This is a one-time download of several hundred MB and can take a while.
Model verified and ready: /data/models/embeddinggemma-2-Q8_0.gguf
Starting embedding sidecar on /run/llama/embed.sock (threads=4)
...
Embedding sidecar is ready.
Starting MCP server on 0.0.0.0:8099 (/mcp)
```

The default model is ~296 MiB (Q8_0). Fetching it is a one-shot startup step: if
the download fails or the checksum does not match, the add-on **stops** with the
error on screen rather than retrying. That is deliberate — a wrong `model_repo`,
`model_file` or `model_sha256` is a configuration mistake, and retrying it would
just re-download hundreds of megabytes every few seconds.

## Memory

Measured peak resident size of the embedding sidecar with the default model,
after serving requests: **about 460 MiB**. The sidecar is started with flags
tuned for embeddings (single slot, no prompt cache, no weight repacking) rather
than llama.cpp's text-generation defaults, which reserve far more.

If the add-on log shows:

```text
Service llama-server exited with code 256 (by signal 9)
The embedding sidecar was killed with SIGKILL (9).
```

then the sidecar was killed from outside the process — nearly always the
out-of-memory killer. Note that llama.cpp reports the *host's* free memory, so
its "no changes needed" line can look fine even when the add-on's own container
limit is much smaller. Either free up memory, or drop to a smaller quantization:

| `model_repo` | `model_file` | `model_sha256` | Size | Sidecar peak |
|---|---|---|---|---|
| `ggml-org/embeddinggemma-2-GGUF` | `embeddinggemma-2-Q8_0.gguf` | `2188ac1deca4b77dffefd603c2776a9d76d9d74ec01841392982ebb840b09135` | 296 MiB | ~460 MiB |
| `unsloth/embeddinggemma-2-GGUF` | `embeddinggemma-2-UD-Q4_K_XL.gguf` | `ea905fd08e8061db77a0031cbb5096d459d7cfd2bdd0ad2ba66e483f16719493` | 168 MiB | ~335 MiB |

Both are the same model at 768 dimensions, so `embedding_dimensions` and the
two prefixes stay as they are. Heavier quantization does cost some retrieval
accuracy, so only step down if memory forces it. Changing quantization changes
the vectors; stored facts are re-embedded automatically on the next start.

Avoid the **F16** files some repositories publish: EmbeddingGemma 2's
activations overflow float16 and produce broken vectors. Q8_0, Q4 and BF16 are
fine.

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
| `model_repo` | `ggml-org/embeddinggemma-2-GGUF` | Hugging Face repo |
| `model_file` | `embeddinggemma-2-Q8_0.gguf` | File within that repo |
| `model_sha256` | *(unset)* | Optional. When set, the download must match it or startup fails. When unset, the download is not verified and the actual hash is printed so you can pin it. |
| `embedding_dimensions` | `768` | Must match the model's native output size |
| `query_prefix` | `"task: search result \| query: "` | Prepended to every search query before embedding. See below. |
| `document_prefix` | `"title: none \| text: "` | Prepended to every fact before embedding. See below. |
| `threads` | `4` | CPU threads for the embedding sidecar |
| `log_level` | *(unset → `info`)* | Optional. `trace` / `debug` / `info` / `notice` / `warning` / `error` / `fatal`. Applies to both the MCP server and the embedding sidecar. |

`model_sha256` and `log_level` are optional and stay hidden until you add them
(use **Show unused optional configuration options** in the add-on's
Configuration tab).

### Query and document prefixes

Some embedding models are trained to see a short task prefix in front of the
text, and a different one for a search query than for a stored passage. The
default model, EmbeddingGemma 2, expects:

```yaml
query_prefix: "task: search result | query: "
document_prefix: "title: none | text: "
```

Keep the trailing space. For a model without task prefixes, clear both. Changing `query_prefix` takes effect on the next
search. Changing `document_prefix` changes every stored vector, so it is
handled like a model change: all facts are re-embedded on the next start.

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
             ("embeddinggemma-2-Q8_0.gguf" -> "embeddinggemma-2-UD-Q4_K_XL.gguf")
```

Changing `embedding_dimensions` is handled the same way — the vector table is
rebuilt at the new width. Nothing is lost, because the fact text itself is what
gets re-embedded. Note this also applies to changing quantization (Q8_0 → Q4),
since that produces different vectors too.

### Upgrading from Qwen3-Embedding

Earlier versions defaulted to Qwen3-Embedding-0.6B. EmbeddingGemma 2 replaced
it because it finds facts stored in Korean far more reliably, at about half the
memory. What an update does depends on whether you ever saved the add-on's
configuration:

- **Never saved it** — you are on the new defaults. On the next start every
  fact is re-embedded with EmbeddingGemma 2 (see the log lines above), and
  nothing else is needed.
- **Saved it before** — your saved `model_repo`, `model_file` and
  `embedding_dimensions` still name Qwen3, but the two prefix options are new
  and take EmbeddingGemma 2's values. Pick one:
  - to switch, use **⋮ → Reset to defaults** in the Configuration tab (re-set
    `threads` or anything else you had changed), or
  - to stay on Qwen3, clear `query_prefix` and `document_prefix`.

The old model file is not deleted. Remove
`/data/models/Qwen3-Embedding-0.6B-Q8_0.gguf` (~609 MiB) once you have
switched, if you want the space back.

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
