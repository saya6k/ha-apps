# Memory

The household's memory for Home Assistant Assist, exposed over MCP. It keeps
remembered facts — each person's own and shared ones — personal documents, and
the shared appliance manuals (PDF and Markdown), and finds any of them by
meaning with one `search`. A **Memory** panel lets everyone read and manage what
is theirs. By default, embeddings are produced by a local llama.cpp sidecar —
there is no external API and no internet access at query time. An OpenAI,
Hugging Face or Ollama embedding service can be used instead; see
[Using a remote embedding service](#using-a-remote-embedding-service).

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
fine. For the same reason the sidecar runs with flash attention off, which
keeps attention in float32 (with it on, llama.cpp handles keys and values as
float16).

## Connecting it to Assist

The add-on announces its MCP endpoint to Home Assistant via Supervisor
discovery on every start. If HA does not pick it up automatically, add it
manually with the URL printed in the log:

```text
http://<add-on hostname>:8099/mcp
```

Then attach it to your conversation agent as an MCP server, and the six tools
become available to the LLM. To keep memories per person, also add the line
in [Each person's own memory](#each-persons-own-memory) to the agent's prompt.

## Tools

| Tool | Purpose |
|---|---|
| `search` | One lookup over remembered facts, the shared manuals and the user's own documents, by meaning; optional `tags` filter (facts only), `limit` (default 5, max 20) |
| `save` | Remember a fact (`content`, optional `tags`); the user's own unless `shared` |
| `get` | Fetch a single fact by id |
| `similar` | Facts similar to a given id, excluding itself |
| `update` | Change `content` and/or `tags`; re-embeds only when content changed |
| `delete` | Hard-delete one fact by id |

Every tool takes an optional `user` — the name of the person asking. Each
`search` result has a `type`: `memory` (a fact, with `personal` saying whether
it is the user's own), `manual` or `document` (a passage, with its `page` for a
PDF or `section` for Markdown).

Search works across languages: a fact stored in Korean is retrieved by an
English question about the same thing, and vice versa.

## Each person's own memory

Facts and documents belong either to the household (shared) or to one person.
A person sees the shared ones and their own, never anyone else's.

Home Assistant does not tell an MCP server who is speaking, so the model passes
it along. Add this line to your conversation agent's prompt (**Settings → Voice
assistants → your assistant → conversation agent → Instructions**):

```text
The current user is {{ user_name }}. Pass this name as `user` to every Memory tool.
```

`{{ user_name }}` is filled in by Home Assistant with the signed-in user's name.
The add-on matches it to a **person** (by name or by the person's id, e.g.
`dad` for `person.dad`) that is linked to that user, so each household member
needs a person with their login selected under **Settings → People**.

Things to know:

- This separates people for convenience, not for security: the model is
  trusted to pass the right name, and anyone who can talk to Assist could ask
  it for someone else's memories by name.
- When nobody is signed in — typically a voice satellite — `{{ user_name }}` is
  empty and only shared memories and manuals are used; anything saved is shared.
- An unknown name is refused with the list of known people, so the model can
  correct itself rather than silently losing memories.
- Facts saved before this version are shared.

## Manuals and documents

Two kinds of files are indexed, **PDF** (`.pdf`) and **Markdown** (`.md`,
`.markdown`):

- **Shared manuals** in `/share/manuals/` — upload them from the panel, or copy
  them there with the Samba or File editor add-on. The add-on creates the
  folder when it starts.
- **Personal documents** — uploaded from the panel with **Upload to my
  documents**. They are kept inside the add-on (`/data/users/<user id>/documents/`),
  not in `/share`, and only their owner can find, read or delete them.

Subfolders are fine, and the file name without its extension becomes the
manual's name, so name them after the device: `Drum washer.pdf`,
`kitchen/Oven.md`.

The add-on reads the folders on every start, after every upload or delete in the
panel, and when you press the rescan button. Indexing runs in the background and does not hold up the
rest of the add-on; the panel shows its progress.

Within one owner, a file is identified by its content (a SHA-256 hash), so only
content the index has never seen is embedded:

- A file whose size and modification time are unchanged is skipped without
  being read.
- Otherwise it is hashed. Renaming or moving a file, or copying it over with
  the same content, only updates its path — nothing is re-embedded.
- Two files with identical content are indexed once, under the first path in
  alphabetical order; the panel reports the other as a duplicate. If that first
  file is deleted, the copy takes over without being re-embedded.
- A changed file is re-embedded, and a deleted one is dropped.

Then:

- **Assist** finds them through `search` — "what does E3 mean on the washer?"
  finds the PDF page or Markdown section about error E3, in any language.
- The **Memory** panel in the sidebar has a **Documents** tab that lists them,
  and its search box covers everything. A search hit opens the file at its page
  or section. Its **Memories** tab lists your own facts and the shared ones to
  add, edit or delete. Every Home Assistant user can open the panel and sees
  only the shared things and their own.

PDFs need a text layer to be searchable. Manufacturers' own PDFs nearly always
have one; a scan of a paper manual does not, and is listed as
**not searchable** — it can still be read in the panel. Text recognition (OCR)
is not included. Markdown is shown with its formatting, but images and links to
other files in the folder do not resolve: use web addresses for those.

### Uploading and deleting

- **Upload** (the arrow at the top of the panel) takes one or more `.pdf`,
  `.md` or `.markdown` files of up to 100 MiB each, into your documents or the
  shared manuals. If a file of the same name is already there, the panel asks
  before replacing it. A `.pdf` that is not actually a PDF is refused.
- **Delete** (the bin above an open file) deletes it **permanently** after a
  confirmation; there is no trash to restore it from. If another file with the
  same content exists, it takes the deleted one's place in the list.

Anyone can upload or delete shared manuals; personal documents only their owner.

New files are indexed straight away, and deleted ones dropped from search.

### Rebuilding or clearing the index

The panel's **⋮** menu has two more actions, each confirmed first:

- **Reindex everything** clears the document index and reads and embeds every
  manual and personal document again. Use it if search results look wrong.
- **Clear the index** removes every manual and document from search and from the
  panel. The index is rebuilt on the next rescan or add-on start, since the
  files are still there.

Both touch only the document index, for everyone. The files themselves and the
remembered facts are never affected.

The add-on maps `/share` writable for the panel's upload and delete, and only
ever writes inside `/share/manuals/`; nothing else changes the files. If the model or
document prefix changes, the manual index is rebuilt in the background after
the next start.

## Options

| Option | Default | Notes |
|---|---|---|
| `embedding_provider` | `local` | `local`, `openai`, `huggingface` or `ollama`. See below. |
| `embedding_url` | *(unset)* | Optional. A remote provider's address; see below. |
| `embedding_api_key` | *(unset)* | Optional. Sent as a Bearer token to a remote provider. |
| `embedding_model` | *(unset)* | Optional. The model to ask a remote provider for; required for one. |
| `model_repo` | `ggml-org/embeddinggemma-2-GGUF` | Hugging Face repo |
| `model_file` | `embeddinggemma-2-Q8_0.gguf` | File within that repo |
| `model_sha256` | *(unset)* | Optional. When set, the download must match it or startup fails. When unset, the download is not verified and the actual hash is printed so you can pin it. |
| `embedding_dimensions` | `768` | Must match the model's native output size |
| `query_prefix` | `"task: search result \| query: "` | Prepended to every search query before embedding. See below. |
| `document_prefix` | `"title: none \| text: "` | Prepended to every fact before embedding. See below. |
| `threads` | `4` | CPU threads for the embedding sidecar |
| `context_size` | `512` | The longest input the local sidecar takes, in tokens. More costs memory. |
| `chunk_size` | `400` | Characters per piece a manual or document is split into. Changing it re-indexes the documents. |
| `log_level` | *(unset → `info`)* | Optional. `trace` / `debug` / `info` / `notice` / `warning` / `error` / `fatal`. Applies to both the MCP server and the embedding sidecar. |

`model_sha256`, `log_level` and the three remote settings are optional and
stay hidden until you add them (use **Show unused optional configuration
options** in the add-on's Configuration tab). `model_repo`, `model_file`,
`model_sha256`, `threads` and `context_size` only matter for the `local`
provider.

### Using a remote embedding service

Instead of the bundled model, the add-on can ask an embedding service. The
local sidecar is then not started and no model is downloaded, which saves the
~460 MiB it uses — but **the text of every fact, document and question is sent
to that service**.

| `embedding_provider` | `embedding_url` | `embedding_api_key` |
|---|---|---|
| `openai` | API base including `/v1`. Default `https://api.openai.com/v1`; any OpenAI-compatible server works (LocalAI, vLLM, LM Studio, …). | Your API key |
| `huggingface` | The feature-extraction endpoint. Default: the Inference Providers router for the model (`https://router.huggingface.co/hf-inference/models/<model>/pipeline/feature-extraction`). For a Text Embeddings Inference server, `http://host:port/embed`. | A token with Inference Providers permission (not needed for your own TEI server) |
| `ollama` | The server, e.g. `http://192.168.1.10:11434`. Required. | Not needed |

Set `embedding_model` to the model name (`text-embedding-3-small`,
`BAAI/bge-m3`, `embeddinggemma`, …) and `embedding_dimensions` to its vector
size: 1536 for `text-embedding-3-small`, 1024 for `bge-m3`, 768 for
EmbeddingGemma. If they do not match, the add-on stops at startup and logs the
size the model actually returned. Clear `query_prefix` and `document_prefix`
unless the model expects task prefixes (EmbeddingGemma in Ollama does).

On every start the add-on embeds one short text to check the service. If the
service is unreachable or busy (HTTP 429 or 5xx — Ollama or Hugging Face
loading the model, say), it waits up to five minutes; a rejected key, an
unknown model or a wrong `embedding_dimensions` stops the add-on at once, with
the reason in the log.

Switching provider or model is handled like any model change: every fact is
re-embedded on the next start, and the documents are re-indexed in the
background. If the service fails part-way, the add-on stops with the error
instead of starting on half-converted memories.

For Hugging Face, the model has to produce one sentence embedding per text —
a model listed for feature extraction, typically a sentence-transformers model.
One that returns a vector per token is refused with a message saying so.

### Chunk and context size

Manuals and documents are split into pieces of at most `chunk_size` characters
before embedding, and a search finds the matching piece. Each piece, together
with the document's title and `document_prefix`, has to fit the model's
context: with the local sidecar that is `context_size` tokens. Korean can take
about one token per character, so keep `chunk_size` comfortably below
`context_size` — the defaults, 400 and 512, leave room for the title and
prefix. To raise both, for example to 1500 and 2048, expect the sidecar to use
noticeably more memory. EmbeddingGemma 2 takes at most 2048 tokens.

A remote service has its own limit (8191 tokens for OpenAI's models). Ollama is
asked not to cut a long piece short, so one that does not fit fails with an
error rather than being indexed incompletely.

Changing `chunk_size` re-indexes the documents on the next start; facts are
always embedded whole and are not affected.

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

- `/data/facts.sqlite` — the facts and their vectors (SQLite + sqlite-vec),
  plus the index of the manuals and documents
- `/data/users/<user id>/documents/` — personal documents
- `/data/models/` — the downloaded GGUF model
- `/share/manuals/` — your manuals. The add-on only changes them when you
  upload or delete from the panel

Everything under `/data` survives add-on updates, is included in the add-on's
backups, and is not exposed over the network.

## Security notes

- The MCP port (8099) is internal to the Home Assistant network and is not
  published to the host.
- The embedding sidecar listens on a **unix domain socket**
  (`/run/llama/embed.sock`, in a `0700` root-owned directory) rather than a TCP
  port, so it has no network address at all.
- The Memory panel (port 8100) only answers Home Assistant's ingress proxy, so
  it is reached through Home Assistant's own login and nothing else. It knows
  who is using it from the proxy, and shows each person only the shared things
  and their own. It writes only inside `/share/manuals/` and `/data/users/`.
- In Assist, who is asking comes from the model (see
  [Each person's own memory](#each-persons-own-memory)), so separating people
  there is a convenience, not a security boundary.
- With a remote `embedding_provider`, the text of every fact, document and
  question is sent to that service. The API key is passed to the server
  process only and never logged.
- Fact contents are never written to the log — only lengths and counts.
