# AGENTS.md

Guidance for humans + AI agents. *Why* lives in `CHANGELOG.md`,
deep dives in `notes/`. Read them before reintroducing removed
behaviour or second-guessing a non-obvious choice.

## What this repo is

A single Home Assistant **app** running a Wyoming conversation agent
backed by any OpenAI-compatible LLM. The agent delegates everything
HA-side (entity exposure, tool schemas, dispatch, entity-overview
prompt) to HA's built-in **`mcp_server`** integration over Streamable
HTTP. We own the LLM loop + MCP/HTTP tool plumbing; HA owns itself.

Follow [`OHF-Voice/apps/default-agent`](https://github.com/OHF-Voice/apps/tree/main/default-agent)
for app packaging + Wyoming discovery conventions; deviate only with reason.

## Layout

| Path | Role |
|---|---|
| `config.yaml`, `Dockerfile`, `apparmor.txt` | app packaging (no `build.yaml` — deprecated upstream; base image pinned via `ARG BUILD_FROM=` in Dockerfile). `apparmor.txt` is a custom profile that allows bwrap's mount/pivot_root primitives — the Supervisor-auto profile blocks them and `apparmor: false` would cost a security-rating point. |
| `wyoming_llm_agent/__main__.py` | argparse + AsyncServer |
| `wyoming_llm_agent/handler.py` | Wyoming events (Describe / Transcript) |
| `wyoming_llm_agent/agent.py` | orchestration: HA snapshot → tools → LLM → dispatch |
| `wyoming_llm_agent/{llm,embedding,mcp_client}.py` | LLM client, embeddings, MCP I/O |
| `wyoming_llm_agent/mcp_listener.py` | Persistent MCP session per server — `resources/{updated,list_changed}` notifications → live skill refresh |
| `wyoming_llm_agent/skill_fetcher.py` | Download agentskills.io skills from URLs / MCP resources into `/config/skills/` (hash-based update) |
| `wyoming_llm_agent/memory.py` | Per-user persistent memory store — markdown files under `/config/memory/{shared,users/<id>}/`, atomic writes, path-traversal-safe slug regex |
| `wyoming_llm_agent/workspace.py` | Workspace files (SOUL / IDENTITY / HEARTBEAT / BOOTSTRAP) at `/config/` root — seed-on-first-boot, BOOTSTRAP YAML manifest (`seed_templates`, `auto_load_skills`), HEARTBEAT Jinja2 render |
| `wyoming_llm_agent/{metrics,metrics_http,preflight,const}.py` | Prometheus, /metrics server, startup probe, defaults |
| `rootfs/etc/s6-overlay/s6-rc.d/` | `llm-agent` (longrun) + `discovery` (oneshot) |
| `translations/{en,ko}.yaml` | option UI strings |
| `scripts/probe_ha_mcp.py` | dev utility — probe HA mcp_server |
| `notes/` | deep dives (see index below) |

## Notes index — read on demand

| Topic | File |
|---|---|
| `ha_tools_mode`, embedding hashing, upstream cache (OpenAI/vLLM APC) | [caching-and-tool-filtering.md](notes/caching-and-tool-filtering.md) |
| `mcp_server` hardcoded `device_id=None`, missing `satellite_id`, workarounds | [ha-mcp-server-internals.md](notes/ha-mcp-server-internals.md) |
| `config.yaml` option → `--cli-flag` table | [options-cli-mapping.md](notes/options-cli-mapping.md) |
| Skills — agentskills.io format, parser, security, PR roadmap | [skills.md](notes/skills.md) |
| Skill design decisions — chosen vs rejected, with rationale | [skill-design-decisions.md](notes/skill-design-decisions.md) |
| Skill sandbox — bwrap policy, seccomp, trap inventory, failure modes | [sandbox.md](notes/sandbox.md) |
| HA version limitations (L1–L6) — what works per HA release, PR refs, watch list | [ha-version-limitations.md](notes/ha-version-limitations.md) |
| Roadmap — per-user memory (R2, v1 landed), workspace (R3, v1 landed), rich display (R4) | [roadmap.md](notes/roadmap.md) |
| Workspace (R3) — SOUL/IDENTITY/HEARTBEAT/BOOTSTRAP, 12-section system prompt order, per-user BOOTSTRAP, deprecation policy | [workspace.md](notes/workspace.md) |

## Invariants (DO NOT regress)

- **HA is delegated, not abstracted.** No self-built HA WS/REST client.
- **HA snapshot is fetched per turn.** Caching → silent stale state.
- **Tool loop has a hard `max_tool_iterations` cap.** Prevents runaway models.
- **Transient HTTP retries once.** Half-closed keepalive sockets are the case.
- **`HandleProgram.supports_home_control = True`** (wyoming ≥ 1.9).
- **HEARTBEAT.md is Jinja2, sandboxed, render-failure → raw + WARNING.** Same sandbox env as the agent's `_jinja_env`. Variables: `date`, `time`, `weekday`, `language`, `device_id`, `satellite_id`, `conversation_id`, `user_id`.
- **Embedding cache keys hash the description** (`name:sha256(desc)[:16]`) — renames invalidate automatically.
- **`_filter_tools()` splits HA vs other.** `ha_tools_mode` controls scoring pool membership; default `always` preserves upstream prompt cache.
- **User-visible defaults live in `config.yaml options:`, not Python constants.** `const.py` holds empty/sentinel fallbacks only.
- **Skills follow agentskills.io standard verbatim — no vendor metadata namespace.** Parser in `skills.py`; bad SKILL.md logs WARNING + skip (never crash). LLM-exposed via 4 meta-tools (`list_skills`/`load_skill`/`unload_skill`/`run_skill_script`) that bypass the embedding filter; loaded SKILL.md bodies appended to the END of the system message so the prefix stays cache-stable. `allowed-tools` (fnmatch) gates tool visibility: matching tools hidden until the owning skill is loaded; meta tools never hidden. See [notes/skills.md](notes/skills.md) and [notes/skill-design-decisions.md](notes/skill-design-decisions.md).
- **Skill script execution is bubblewrap-sandboxed.** Single meta-tool (`run_skill_script`), no escape hatch. Always-on: `--unshare-{net,user,ipc,uts,cgroup}`, seccomp BPF denying ptrace/mount/bpf/etc. (loaded via `--seccomp <fd>` with the libseccomp Python bindings — **must use `fdopen(closefd=False)`, NOT a raw int fd**, or the BPF program never loads and we silently run unfiltered), `env={}`, no host fs except `/usr` `/lib` read-only, `/tmp` tmpfs **capped at 64 MiB via `--size`**, asyncio `wait_for(10s)` wall-clock + SIGTERM/SIGKILL fallback. **Per-child rlimits via `preexec_fn=_set_skill_rlimits`** (RLIMIT_AS 200MB / CPU 5s / FSIZE 16MB / NOFILE 64) — set in the forked child before exec(bwrap), Linux propagates them through exec + namespace creation. NOT bwrap flags: upstream bubblewrap has no `--rlimit-*` family (verified through 0.11.0); the 1.14.0 self-test caught that 1.13.x and earlier had been silently running without rlimits because of this misattribution. **Probed-and-conditional**: `--unshare-pid` (strict mode) only when the outer container allows nested `proc` mount — otherwise host pidns + `--ro-bind /proc /proc` (relaxed mode, common on HAOS/LXC nested). Probe runs once at startup via `probe_sandbox()`; result cached in `_BWRAP_SUPPORTS_PID_UNSHARE`. On total probe failure `run_skill_script` is hidden from the LLM entirely. Requires `privileged: [SYS_ADMIN]` **and** our custom `apparmor.txt` (Supervisor-auto profile blocks bwrap's `mount(MS_SLAVE|MS_REC)` even with `CAP_SYS_ADMIN`). See [notes/sandbox.md](notes/sandbox.md).
- **Per-user memory mirrors the skill meta-tool pattern.** Adding to `META_TOOL_NAMES` is the only registration step — `_filter_tools()` always-in path and `_compute_skill_tool_gating()` "never hide meta tools" both key off the frozenset. `MemoryStore` enforces slug regex `^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$`, 32KB body cap, atomic writes (tmp → rename), and bucket-resolve path-traversal defense. Index injected into `_compose_system` just before loaded skill bodies — save/delete touches only the tail of the system prompt. `user_id` threaded handler → agent → store; falls back to `shared` bucket when HA hasn't delivered `context["user_id"]` (pre-2026.6.0). Memory tools hidden entirely when `MemoryStore is None`.
- **Daily journal lives under per-user bucket; lazy-loaded.** `memory/users/<id>/journal/YYYY-MM-DD.md`, append-only with `## HH:MM` headings. Two meta-tools (`journal_append` / `load_journal_day`) — NOT auto-injected into the system prompt. The LLM fetches when needed. Per-entry cap 4KB, per-day cap 64KB. No shared journal (unsafe / missing `user_id` → error).
- **Meta tools are budget-free in `_filter_tools`.** All names in `META_TOOL_NAMES` (skill_*, memory_*, working_memory_*, journal_*) are pulled out of the scoring pool into a `meta_tail` list and appended unconditionally — they do not count toward `tool_filter_top_k`. So raising the top-K default to 20 only affects non-meta scoring tools (external MCP + custom HTTP).
- **Workspace is the only system-prompt composition path — no toggle, no `system_prompt:` option.** Every system prompt is composed in a strict 12-section cache-stable order (SOUL → IDENTITY → BOOTSTRAP body → HA api → skill catalog → shared mem → user BOOTSTRAP → USER profile → user mem → active skill bodies → working memory → HEARTBEAT). Order is by mutation frequency (lowest → highest), with per-user slots (user BOOTSTRAP, USER profile, user mem) grouped after the shared prefix so cross-user cache shares the whole shared-content prefix. Never reorder without checking [notes/workspace.md](notes/workspace.md). **Hot reload is enabled**: every `respond()` stats the 4 workspace files and re-calls `load_workspace()` on mtime change — no addon restart needed for edits. Per-user `USER.md` + `BOOTSTRAP.md` are both seeded automatically on the first turn where the agent sees a new safe `user_id`. BOOTSTRAP body (slot 3) is the markdown after the YAML frontmatter; injected as LLM boot instructions until the user blanks it out. **Per-user BOOTSTRAP (slot 7)** at `memory/users/<id>/BOOTSTRAP.md` is the per-household-member sibling — same seed-on-encounter policy, 8KB cap, but `render_user_bootstrap` strips heading/italic-only lines via `_strip_bootstrap_placeholder` so a fresh placeholder costs zero tokens until the user writes real instructions. Working memory (slot 11) is the LLM's conversation-scoped scratchpad — capped at 8KB, mutated via `working_memory_set` / `working_memory_clear`, lives in `_Conversation.working_memory`, dies on eviction. BOOTSTRAP `auto_load_skills` populates new conversations' `loaded_skills` at `_get_conversation` time, filtered against the live skill registry. When `/config/` is unmounted (dev/test), `Workspace()` is constructed with empty fields and the agent just skips the empty slots — graceful degradation, no separate code path.
- **MCP sessions split by purpose.** Tool dispatch uses ephemeral per-call sessions (simple, robust to half-closed sockets). Resource notification listening uses one persistent session per `mcp_servers:` entry — `mcp_listener.py` opens it at boot, subscribes to tracked SKILL.md URIs, processes `resources/{updated,list_changed}` notifications, reconnects with bounded backoff. Listener crashes never propagate; worst case is "no live updates; next addon restart picks up changes."
- **Wyoming discovery URI publishes the container IP, not `$(hostname)`.** `rootfs/etc/s6-overlay/s6-rc.d/discovery/run` uses `hostname -i | awk '{print $1}'`. The upstream OHF-Voice pattern (`tcp://$(hostname):10500`) is RFC-952-fragile (addon container hostnames have underscores) and HA Core's `getaddrinfo` occasionally returns `EAI_NODATA`, surfacing as "Error communicating with service: [Errno -5] Name has no usable address". IP is unambiguous; discovery re-fires every addon start so it stays current. Fallback to `$(hostname)` only when `hostname -i` returns nothing.
- **`apparmor.txt` uses only bare top-level verbs.** Profile body is `file, capability, network, mount, umount, pivot_root, ptrace, signal` plus `#include <abstractions/base>` — nothing else. Richer rules (`mount options=(...)`, per-path `r,w,ix`, alternated globs, `ptrace (trace,read,readby,tracedby)`, `unix,` standalone) get rejected by `apparmor_parser` on some HAOS versions with no useful stderr — Supervisor surfaces `Can't load profile … exit status 1` and falls back to the auto-generated profile, which then blocks bwrap. Outer profile is NOT our confinement boundary; **inner bwrap argv + seccomp denylist + rlimits** do the real isolation. Defense-in-depth here costs reliability without buying security.

## Local dev

Host Python ≠ production. Match the Alpine target (3.13 on `base:3.23`).

```bash
uv venv .venv --python 3.13 && uv pip install -e .   # one-time
.venv/bin/python smoke_test.py                       # day-to-day
docker build .                                       # pre-PR truth
```

## Sanity checks before PR

- `yamllint **/*.yaml`, `shellcheck` the s6 scripts.
- `.venv/bin/python smoke_test.py` — all green.
- `docker build .` for one arch.
- `echo '{"type":"describe"}' | nc -w 1 localhost 10500` → Info with `"LLM Conversation Agent"`.
- When touching `apparmor.txt`, `_bwrap_argv()`, the seccomp denylist, or the rlimit constants: inside the running addon container, run `python -m wyoming_llm_agent --self-test-sandbox` and confirm every non-skipped test passes. `--self-test-slow` adds the rlimit-cpu + wait_for ceilings (~20s). See [notes/sandbox.md](notes/sandbox.md) for the table of tests and what each claim covers.

## Known limitations (intentional)

HA-side gaps that this addon cannot fix on its own. Full matrix + PR refs + workarounds in [ha-version-limitations.md](notes/ha-version-limitations.md). Re-audit on every monthly HA release.

| # | Limitation | Fixed in |
|---|---|---|
| L2 | Stream LLM reply to HA TTS (`HandledChunk` etc. — silently dropped, 300s pipeline timeout) | not scheduled — **do NOT advertise `supports_handled_streaming`** |
| L3 | Pipeline debug UI empty `data.success` / `data.failed` for HandleProgram agents | not scheduled (IntentProgram path got partial fix in 2026.6.0) |
| L4 | Area-aware routing — HA mcp_server hardcodes `device_id=None` in `LLMContext` | not scheduled |
| L5 | HA per-pipeline "Instructions" textarea not delivered to Wyoming | not scheduled — edit `/config/SOUL.md` / `IDENTITY.md` instead |
| L6 | `Transcript.context["user_id"]` not populated — per-user BOOTSTRAP / USER profile / user MEMORY layers stay silent, all turns route to `shared` bucket | not scheduled — upstream `wyoming/conversation.py` discards `user_input.context.user_id` before building the Transcript. Code is ready; activates the moment HA sends it. |

## Don'ts (and what to do instead)

- **Don't build an HA WS/REST client** → fix the gap upstream in `mcp_server` (or via `intent_script:` for app-side intents).
- **Don't reintroduce `custom_intents:`** → use HA's `intent_script:` — `mcp_server` exposes it as a tool automatically.
- **Don't cache the HA snapshot across turns** → `_fetch_ha_snapshot()` per Transcript; the supervisor proxy is fast.
- **Don't bump `homeassistant:` floor below 2026.3.0** → required for `mcp_server`.
- **Don't add destructive tools** (irreversible service calls, file writes) → expose via HA `intent_script:` with a user-side confirm step instead.
- **Don't skip `chmod +x` in `Dockerfile` when adding s6 scripts** → add the new script to the existing `chmod +x` line; s6 silently ignores non-executable scripts.
- **Don't commit raw `config.yaml`/`config.json` outside repo root** → use `example_config.yaml` / `*.tmpl`; supervisor's repo scanner reads every `config.*` and chokes on templates.
- **Don't put user-tunable text defaults in Python constants** → put them in `config.yaml options:` (multi-line `|` if needed) so the addon UI shows them.
- **Don't enrich `apparmor.txt` with `mount options=(...)`, per-path rules, alternated globs, or `unix,` standalone** → `apparmor_parser` on the HAOS host rejects them silently (Supervisor swallows stderr); profile load fails and Supervisor falls back to the auto-generated profile that blocks bwrap. Keep the profile to bare top-level verbs only. Inner bwrap argv + seccomp + rlimits do the confinement.
- **Don't revert `discovery/run` to `tcp://$(hostname):10500`** → HA Core's `getaddrinfo` returns `EAI_NODATA` intermittently for the addon hostname (RFC-952-invalid underscores), surfacing as "Error communicating with service" to the user. Use `hostname -i` so HA Core never has to resolve our name.
- **Don't skip hooks / sign-bypass on git** → if a hook fails, fix the root cause; never `--no-verify` / `--no-gpg-sign`.
