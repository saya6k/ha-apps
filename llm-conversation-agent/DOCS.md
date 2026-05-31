# Home Assistant App: LLM Conversation Agent

A Wyoming conversation agent that wraps any OpenAI-compatible LLM and
delegates all Home Assistant state and tool execution to HA's built-in
**Model Context Protocol Server** integration.

## Installation

1. **Settings** > **Add-ons** > **Add-on Store**, add this repository.
2. **Enable HA's Model Context Protocol Server integration**: Settings >
   Devices & services > **Add Integration** > "Model Context Protocol
   Server". Pick "Assist" as the LLM API. This addon won't work without
   it.
3. Install **LLM Conversation Agent**, fill in `base_url` + `api_key` +
   `model`, and start it.
4. HA auto-discovers the Wyoming agent and offers to add it under
   **Settings** > **Devices & services**.

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=wyoming)

5. **Settings** > **Voice assistants** > pick your pipeline and set the
   **Conversation agent** to the discovered one.
6. **Settings** > **Voice assistants** > **Expose** the entities you
   want voice control over. HA's mcp_server only exposes entities you
   mark here.

Requires Home Assistant **2026.3.0+** for `supports_home_control` in
Wyoming 1.9, and the `mcp_server` integration on the same version.

## Options

| Option                  | Default                            | Description |
| ----------------------- | ---------------------------------- | ----------- |
| `base_url`              | `https://api.openai.com/v1`        | Upstream OpenAI-compatible base URL. |
| `api_key`               | _empty_                            | Sent as `Authorization: Bearer ...`. |
| `model`                 | `gpt-4o-mini`                      | Chat model. Must support function calling. |
| `request_timeout`       | `60`                               | Upstream read timeout (seconds). |
| `verify_ssl`            | `true`                             | Verify TLS certs on every outbound HTTP call. Set `false` only for trusted local self-hosted endpoints with self-signed certs — applies to LLM, embedding, MCP, and skill_urls together. |
| `max_tool_iterations`   | `8`                                | Safety cap on tool→LLM→tool loops per request. |
| `history_turns`         | `6`                                | Past user+assistant turns to keep per conversation. |
| `languages`             | `[]` (broad default set)           | ISO codes advertised in the Wyoming Info. |
| `system_prompt`         | (see below — Jinja2 with device-context block) | Rendered as a Jinja2 template each turn, then prepended to HA's `api_prompt`. Available variables: `device_id`, `satellite_id`, `language`, `conversation_id`. |
| `extra_headers`         | `[]`                               | Extra HTTP headers for upstream calls. |
| `ha_mcp_enabled`        | `true`                             | Delegate HA tools + entity prompt to HA's mcp_server. Default on (uses supervisor proxy + SUPERVISOR_TOKEN automatically). Turn off only if you run the agent without HA. |
| `mcp_servers`           | `[]`                               | External MCP servers (memory, vector search, …). |
| `embedding_base_url`    | _empty_                            | Embeddings `/embeddings` endpoint. Empty = reuse `base_url`. |
| `embedding_api_key`     | _empty_                            | Empty = reuse `api_key`. |
| `embedding_model`       | _empty_                            | Empty disables tool filtering. |
| `tool_filter_top_k`     | `0`                                | When > 0, send only top-K tools by similarity each turn. |
| `ha_tools_mode`         | `always`                           | `always`: HA tools bypass the filter (cache-friendly). `embedding`: HA tools also get top-K scoring (token-saving but breaks upstream prompt cache). Meaningful only when `tool_filter_top_k > 0`. |
| `metrics_enabled`       | `true`                             | Expose Prometheus `/metrics` on `metrics_port`. |
| `metrics_port`          | `9099`                             | TCP port for the `/metrics` endpoint. |
| `debug_logging`         | `false`                            | Verbose DEBUG logs. |

## How it works

```
User speaks  →  STT (Whisper etc.)
              →  Transcript("turn on the bedroom lights")
                 │
                 ▼
        ┌────────────────────────────────────────────────┐
        │ this addon (Wyoming, tcp://*:10500)            │
        │                                                │
        │  1. Open one session to HA mcp_server          │
        │     - tools/list  → HassTurnOn, HassLightSet…  │
        │     - prompts/get("Assist") → HA's curated     │
        │       system prompt + exposed-entity overview  │
        │  2. Compose: user.system_prompt + HA.api_prompt│
        │  3. POST /v1/chat/completions with tools       │
        │  4. If tool_calls:                             │
        │     - HA tools → MCP call back into HA         │
        │     - External MCP tools → call MCP server     │
        │  5. Loop until LLM replies with text           │
        │  6. Return Handled(text=reply)                 │
        └────────────────────────────────────────────────┘
                 │
                 ▼
              TTS  →  User hears the reply
```

Each turn fetches a fresh `tools/list` + `prompts/get` from HA, so
newly-exposed entities and updated state appear immediately without an
addon restart.

## Custom HA actions (intent_script)

To expose a custom HA automation/script to the LLM, define it as an
`intent_script:` in HA's `configuration.yaml`:

```yaml
intent_script:
  StartLaundry:
    action:
      - service: script.start_laundry
    speech:
      text: "Laundry started."
```

It will appear as a tool through HA's mcp_server automatically — no
addon-side configuration needed.

## System prompt (Jinja2)

The `system_prompt:` option is rendered as a Jinja2 template every turn.
The default visible in the addon UI already includes a device-context
block:

```yaml
system_prompt: |
  You are the voice assistant for a Home Assistant smart home. Reply briefly...
  {% if device_id %}

  The user is speaking from voice satellite device_id="{{ device_id }}"{% if satellite_id %} (satellite_id="{{ satellite_id }}"){% endif %}. When calling tools that accept device_id, area_id, or location parameters, default to these values unless the user explicitly overrides.
  {%- endif %}
```

**Available variables** (all None-safe):

| Variable          | Source                                                    |
| ----------------- | --------------------------------------------------------- |
| `device_id`       | Wyoming `Transcript.context["device_id"]` from HA Voice   |
| `satellite_id`    | Wyoming `Transcript.context["satellite_id"]`              |
| `language`        | The transcript's language (ISO code)                      |
| `conversation_id` | HA's conversation thread id (for multi-turn tracking)     |

Time / date variables are intentionally **not** exposed — they'd change
every turn and invalidate the upstream prompt cache.

**Where the device block is useful:**

- **ha-mcp** (third-party MCP at `homeassistant-ai/ha-mcp`) — tools like
  `ha_get_device(device_id=...)` and `ha_call_service(area_id=...)`
  accept these as parameters; the LLM fills them in from the prompt.
- **HA's built-in mcp_server** ignores `device_id` (hard-coded `None` in
  `homeassistant/components/mcp_server/http.py:133`) — the block is a
  no-op there but harmless.

**This is NOT Home Assistant's Jinja2.** HA-specific functions like
`states()`, `state_attr()`, `is_state()`, `device_attr()` are *not*
available — the addon runs in a separate container and has no direct
access to HA state. For runtime state, expose MCP tools (e.g.
`GetLiveContext` via HA's mcp_server) and let the LLM call them.

**Render failure policy:** a template with bad syntax or an undefined
variable falls back to the raw text as-is, with a `WARNING` logged.
Voice operation takes priority over template strictness.

Leave the field blank if you want no user-side prompt — HA's `api_prompt`
and the language hint still apply.

## External MCP servers

[MCP](https://modelcontextprotocol.io/) is the standard plug-in
protocol for LLM tool/resource servers. Mount memory, vector search,
GitHub access, etc. by URL:

```yaml
mcp_servers:
  - name: memory
    url: "http://192.168.1.50:8765/mcp"
    transport: streamable_http   # default; "sse" for legacy servers
    headers: []
  - name: search
    url: "https://my-search.example.com/sse"
    transport: sse
    headers:
      - name: Authorization
        value: "Bearer token-xyz"
```

Their tools are discovered once at startup and exposed as
`mcp_<server>_<tool>`. Per-call dispatch (~50–200 ms overhead vs LLM
inference time, robust to dropped sessions).

Recommended servers:

| Need | Server |
| --- | --- |
| Long-term memory | `@modelcontextprotocol/server-memory` |
| Semantic search / RAG | `mcp-server-qdrant`, `mcp-chroma`, `mcp-pgvector` |
| Filesystem | `@modelcontextprotocol/server-filesystem` |
| GitHub | `@modelcontextprotocol/server-github` |
| Richer HA tool surface (~88 tools vs HA built-in's ~10) | [`homeassistant-ai/ha-mcp`](https://github.com/homeassistant-ai/ha-mcp) — add as a regular `mcp_servers:` entry alongside the built-in `ha_mcp_enabled`. They coexist fine. |

stdio (subprocess) MCP servers are not supported — run them in a
separate container with an HTTP/SSE shim.

## Tool filtering via embeddings

Once your tool count crosses **30–50** (typical with multiple MCP
servers), LLMs start mis-selecting tools. With `embedding_model` set
and `tool_filter_top_k > 0`, the addon embeds every static tool
description at startup, embeds the user transcript per turn, and keeps
only the top-K by cosine similarity.

```yaml
embedding_model: "text-embedding-3-small"   # or nomic-embed-text on Ollama
tool_filter_top_k: 25
```

For vLLM users running chat and embeddings on separate instances:

```yaml
base_url: "http://my-vllm-chat:8000/v1"
embedding_base_url: "http://my-vllm-embed:8001/v1"
embedding_model: "BAAI/bge-small-en-v1.5"
tool_filter_top_k: 25
```

### How HA mcp_server tools interact with the filter

The `ha_tools_mode` option controls whether HA tools join the top-K pool:

| Mode | HA tools | Tokens per turn | Upstream prompt cache | Best for |
|---|---|---|---|---|
| `always` (default) | Bypass filter — all pass | Higher (full HA set every turn) | **High hit rate** — `tools:` array stays constant across turns | Stable cost/latency; OpenAI Cloud's automatic prefix cache; vLLM Automatic Prefix Caching (APC) |
| `embedding` | Score with the rest, keep top-K | Lower (only top-K HA tools) | **Lower hit rate** — top-K shifts per utterance → prefix changes | Large HA setups (50+ exposed entities); LLMs that struggle with tool selection; when token budget dominates cache savings |

In `embedding` mode the addon pre-warms HA tool embeddings at startup
(best-effort — if HA isn't reachable yet, it falls through to per-turn
lazy fill). Cache keys include a SHA-256 hash of the tool description,
so renaming or redescribing an entity in HA invalidates that single
entry automatically — no manual reload needed.

When the embedding endpoint fails for HA tools mid-turn, those tools
fall through to **include-all** (safer than dropping — a `WARNING` is
logged). Track this with `llm_agent_embedding_calls_total{outcome="error"}`
on the `/metrics` endpoint.

### Cache hit telemetry

The addon records `usage.prompt_tokens_details.cached_tokens` (reported
by both OpenAI Cloud and vLLM APC) as
`llm_agent_cached_prompt_tokens_total{model="..."}`. Compute cache hit
rate in Prometheus / Grafana:

```
sum(rate(llm_agent_cached_prompt_tokens_total[5m])) by (model)
  / sum(rate(llm_agent_prompt_tokens_total[5m])) by (model)
```

Use this to measure the trade-off when toggling `ha_tools_mode` —
typically `always` → 80–95% hit rate after warmup, `embedding` → drops
sharply when top-K shifts per utterance.

## Metrics (Prometheus)

The addon exposes a Prometheus-format `/metrics` endpoint on a separate
TCP port (default 9099, configurable). Plug it into HA's
[prometheus integration](https://www.home-assistant.io/integrations/prometheus/),
a standalone Prometheus server, or anything else that scrapes the text
format.

```yaml
# In your Prometheus config:
scrape_configs:
  - job_name: ha-llm-agent
    static_configs:
      - targets: ['<addon-host>:9099']
```

Metrics exposed (all prefixed `llm_agent_`):

| Metric | Type | Labels | Meaning |
| --- | --- | --- | --- |
| `requests_total`               | counter   | model, outcome (success/error) | Upstream chat-completion calls |
| `prompt_tokens_total`          | counter   | model | Cumulative prompt tokens (from upstream `usage`) |
| `completion_tokens_total`      | counter   | model | Cumulative completion tokens |
| `request_duration_seconds`     | histogram | model | Wall-clock duration of one chat call |
| `tool_calls_total`             | counter   | tool_name, source (ha/mcp/http), outcome | Tool dispatches |
| `mcp_session_duration_seconds` | histogram | server | Per-MCP-session round-trip time |
| `embedding_calls_total`        | counter   | outcome | Embedding API requests |
| `turns_total`                  | counter   | language, handled (true/false) | User transcripts processed |
| `turn_duration_seconds`        | histogram | — | Wall-clock from Transcript to Handled |
| `active_conversations`         | gauge     | — | Distinct in-memory conversations being tracked |

**Cost ($) is not exposed**: prices vary per model and provider too
much to bake in. Compute from `prompt_tokens_total` / `completion_tokens_total`
via a Prometheus recording rule or a Grafana panel using your account's rates.

Example PromQL queries:

```promql
# Tokens per minute, by model
rate(llm_agent_prompt_tokens_total[5m]) * 60
rate(llm_agent_completion_tokens_total[5m]) * 60

# 95th-percentile response latency
histogram_quantile(0.95, sum by (le, model) (rate(llm_agent_request_duration_seconds_bucket[5m])))

# Tool dispatch breakdown
sum by (source) (rate(llm_agent_tool_calls_total[5m]))
```

## Known limitations

- **"This assistant cannot control your home" UI banner on HA ≤ 2026.5.x.**
  The addon correctly advertises `supports_home_control=True` but HA
  2026.5.4 pins `wyoming==1.7.2` (no such field) and its wyoming
  integration doesn't read the flag for handle-only services. **Tool
  execution still works** — `HassTurnOff`, `HassLightSet`, etc. all
  run via mcp_server and your lights actually respond; only the UI
  banner is wrong. Fixed in HA 2026.6.0 via
  [PR#170682](https://github.com/home-assistant/core/pull/170682) +
  [PR#171615](https://github.com/home-assistant/core/pull/171615).
  No addon-side workaround.
- **Pipeline debug UI shows empty `data.success` / `data.failed` for
  every voice command.** The Wyoming `Handled` event carries only
  `text` + `context` — there is no protocol channel for an external
  conversation agent to populate the per-tool execution trace HA's
  in-process integrations (OpenAI Conversation, Anthropic Conversation,
  etc.) fill via `intent_response.async_set_results(...)`. To verify a
  tool actually fired, enable `debug_logging: true` and look for
  `MCP call <server>.<tool> args=... -> ok=... text=...` in the addon
  log. Same constraint applies to every Wyoming conversation agent
  (including OHF-Voice's `intent-gemma4`).
- **Streaming the LLM reply to HA TTS is not supported.** Wyoming
  defines `HandledStart` / `HandledChunk` / `HandledStop` events but
  HA's wyoming conversation integration (as of HA dev 2026-05) does
  not consume them — they fall through every branch in
  `_async_process` and the pipeline hangs until the 300s timeout.
  `supports_handled_streaming` is similarly ignored. The addon
  always emits one terminal `Handled` per Transcript. If HA ever
  wires up streaming events for the conversation domain, this
  limitation can be revisited.
- **Area-aware routing is currently disabled.** HA's `mcp_server`
  hard-codes `device_id=None` in the LLM context, so prompts like
  "turn on the lights" without an explicit area can't be auto-targeted
  to the voice satellite's room. Until HA core fixes this upstream,
  the LLM either asks for clarification or relies on the user naming
  an area / entity explicitly. (This is purely a HA-side limitation;
  nothing we can change in the addon.)
- **HA's per-pipeline "Instructions" textarea is not delivered to
  Wyoming agents.** Wyoming protocol carries no field for it, and
  HA's mcp_server prompt (`api_prompt`) doesn't include it either.
  Use this addon's `system_prompt:` option instead.

## Network

| Port    | Description                                                       |
| ------- | ----------------------------------------------------------------- |
| `10500` | Wyoming conversation agent (auto-discovered by HA).               |

## Support

[Open an issue on GitHub](https://github.com/saya6k/ha-llm-conversation-agent/issues).
