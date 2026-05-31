# Changelog

## 1.14.5

- **Memory hygiene — tighter limits + bucket-total cap + status tool.**
  `memory_save` per-entry cap dropped from 32 KB → 4 KB so a single
  memory has to be a focused fact, not a wall of text. New bucket-
  total cap (`MAX_BUCKET_MEMORY_BYTES = 32 KB`) — `memory_save` is
  now rejected when the user's bucket sum would exceed it, with a
  Hermes-style directive: *"Memory bucket at X/Y bytes. Adding this
  entry (N bytes) would push it to M. Call memory_delete or
  memory_save over an existing slug to consolidate first."* Forces
  the LLM to prune rather than accumulate.

  Per-entry rejection message also updated: *"body exceeds 4096-byte
  per-entry limit (got N). Consolidate this memory — keep only the
  essentials, or split it across two focused slugs."*

  New always-on meta-tool `memory_status` returns the bucket label,
  entry count, total bytes, the two byte limits, percent full, and
  every entry sorted by size. LLM can call it before `memory_save`
  to plan a consolidation, or after a rejected save to see what to
  delete. Bypasses the embedding filter (META_TOOL_NAMES).

  Why now: surveying Hermes Agent's `tools/memory_tool.py` showed
  their `(memory_char_limit=2200, user_char_limit=1375)` defaults
  are deliberately tight to make the model curate its own memory.
  Our prior 32 KB-per-entry cap let memories accumulate silently;
  by the time a user noticed, the bucket was unscannable noise.

  Unaffected: USER.md (16 KB) and per-user BOOTSTRAP.md (8 KB) caps
  unchanged — those are hand-edited by the household member, not
  written by the LLM, so tightening them risks silent truncation of
  existing user content. Read paths still honor those caps as a
  safety net only.

  Existing users with >4 KB memory entries: reads still work
  (the cap is enforced on write, not read). Next `memory_save` over
  the same slug will fail with the new error message, prompting the
  LLM to split or consolidate.

  See `notes/roadmap.md` → R2 v1.1 for follow-up items (end-of-turn
  nudge, consolidation prompt injection) and the rationale for
  skipping a pluggable provider abstraction.

## 1.14.4

- **New metric: `llm_agent_embedding_tokens_total{model}`** — cumulative
  embedding tokens billed by upstream. Source: OpenAI-compatible
  `/embeddings` response `usage.total_tokens`. `record_embedding` gained
  optional `model` and `tokens` parameters; legacy 2-arg call sites still
  work (error paths and tests). When upstream omits `usage` from the
  embedding response (some vLLM builds), the call still counts in
  `embedding_calls_total` but contributes 0 to `embedding_tokens_total` —
  dashboards can spot this as "calls > 0 but tokens = 0 for that model".

  Why: chat-completion tokens were already tracked, but `text-embedding-*`
  cost was completely invisible. Even though it's <1% of chat cost for
  typical workloads, the Grafana dashboard's "예상 비용" panel was
  silently missing it. Now the cost panel sums prompt + completion +
  embedding × their respective `$/1M` template variables.

  Companion change in `grafana-dashboards/LLM_Agent.json`:
  - New textbox variable `price_embedding` (default `0.02`).
  - "예상 비용 (USD)" formula extended with embedding term.
  - "임베딩" row: stat panel now shows calls + tokens; timeseries shows
    call rate (success/error) on left axis + token rate on right axis.

## 1.14.3

- **Fix: `rlimit_cpu` self-test failed with exit=137 on bwrap-wrapped
  child.** 1.14.2 set RLIMIT_CPU with `soft == hard == 5`, so SIGXCPU
  at the soft limit was immediately followed by SIGKILL at the hard
  limit — the script died with SIGKILL before SIGXCPU could terminate
  it cleanly. Plus the `expect_killed` predicate only recognised the
  Python direct-signal convention (`exit_code < 0`), not bwrap's
  shell-convention wrapping (`128 + signum`), so even when the right
  signal fired the predicate said FAIL.

  Two fixes:
  - `_set_skill_rlimits`: RLIMIT_CPU now uses `(soft=5, hard=5+5)`.
    SIGXCPU at 5s gives a sane process room to terminate; a script
    that catches and ignores SIGXCPU still gets SIGKILLed at 10s.
    Either way the cap is < 10s.
  - `_evaluate`: `expect_killed` predicate now accepts both
    `exit_code < 0` (direct subprocess) and `128 < exit_code < 160`
    (shell convention from bwrap supervising the child). bwrap
    propagates `WIFSIGNALED` → exit `128 + WTERMSIG`, so SIGXCPU
    surfaces as 152 and SIGKILL as 137 — both indicate the
    rlimit-cpu fired, both pass.

  Smoke test extended: predicate verified against both conventions
  (direct -24, shell 152, shell 137) and rejects exit_code=0.

## 1.14.2

- **🔴 Fix: rlimits were never enforced — bwrap has no `--rlimit-*`
  flags.** All prior releases emitted `--rlimit-as / --rlimit-cpu /
  --rlimit-fsize / --rlimit-nofile` as bwrap arguments behind a
  `_detect_bwrap_rlimit_support()` probe that grepped `bwrap --help`
  for `--rlimit-as`. The probe always returned False because upstream
  **bubblewrap (verified through 0.11.0) has no such flag family** —
  the interface was misattributed during initial design. So skill
  scripts were running with the kernel's default resource limits, NOT
  our intended 200 MiB / 5s / 16 MiB / 64-fd caps. The 1.14.0 self-test
  exposed this: even on Alpine 3.23 (bwrap 0.11.0), the rlimit tests
  reported `(skipped: bwrap lacks --rlimit-*)` — no real bwrap version
  has them.

  Fix: enforce rlimits via `preexec_fn=_set_skill_rlimits` passed to
  `asyncio.create_subprocess_exec`. The hook runs in the forked child
  between fork() and execve(bwrap); Linux propagates RLIMIT_* across
  exec and namespace creation, so the cap reaches the skill script
  unchanged. Always-on, no bwrap-version dependency.

  Removed: `_detect_bwrap_rlimit_support()`, `_BWRAP_SUPPORTS_RLIMIT`
  module flag, `requires_rlimit` field on `_BehaviorTest`, the
  `bwrap_no_rlimit` skip path. The `rlimit_fsize` / `rlimit_nofile` /
  `rlimit_cpu` self-tests now run unconditionally.

  Net behaviour change: bumping from 1.14.1 → 1.14.2 turns on per-
  script memory / CPU / file-size / fd caps that were nominally part
  of the threat model but missing in practice.

## 1.14.1

- **🔴 Fix: seccomp filter never loaded** (regression caught by 1.14.0's
  `--self-test-sandbox`). `_build_seccomp_fd()` passed a raw int fd to
  `libseccomp.SyscallFilter.export_bpf()`, but the Python binding wants
  a file-LIKE object with `.fileno()`. The call raised
  `'int' object has no attribute 'fileno'` on every script run, the
  exception got caught + logged at WARNING, and the sandbox proceeded
  without `--seccomp`. Every prior addon release was effectively
  shipping skill scripts with no BPF syscall filter — relying solely
  on `--unshare-{net,user,...}` + bwrap rlimits for isolation.

  Fix: wrap fd with `os.fdopen(fd, "wb", closefd=False)`; libseccomp
  now serialises the BPF program correctly and bwrap loads it via
  `--seccomp <fd>`. Verify by re-running `--self-test-sandbox` —
  `seccomp_blocks_unshare` and `seccomp_blocks_mount` should both
  report PASS (EPERM from libseccomp's ALLOW-by-default + ERRNO rules).

- **Fix: `env_sterile` self-test treated bwrap-auto-`PWD` as a leak.**
  bwrap sets `PWD` to match `--chdir` (bwrap.c `set_env_unless_existing`),
  which is expected, not a credential leak. Test now includes `PWD` in
  the allowed set; the check that fails is "any OTHER var" (e.g. an
  accidentally-leaked `OPENAI_API_KEY`).

- **Fix: `wall_clock_timeout` self-test was masked by a 25s suite
  timeout.** `verify_sandbox_behavior()` was passing `timeout=25.0` for
  all `slow` tests, so the 10s `wait_for` was never reached — the 20s
  sleep completed normally and the test reported a false FAIL. New
  per-test `timeout_s` override on `_BehaviorTest`; `wall_clock_timeout`
  pins to `DEFAULT_TIMEOUT_S` (10s) so the contract under test
  ("default wait_for kills runaway") is what's actually exercised.

- **Fix: `rlimit_cpu` self-test gave false FAIL on bwrap < 0.10.**
  The test only knew about `slow`, not about `rlimit` support, so on
  bwrap <0.10 (Alpine base ≤3.21) the script would loop into the
  wall-clock fallback and look "not killed by signal". Added
  `requires_rlimit` flag on `_BehaviorTest`; cross-cutting tests
  (currently just `rlimit_cpu`) now skip with `bwrap_no_rlimit` when
  the rlimit family is absent.

## 1.14.0

- **Sandbox behavioural self-test (`--self-test-sandbox`).** New CLI mode
  that runs end-to-end verification of every isolation claim in
  [notes/sandbox.md](notes/sandbox.md) against the live bwrap sandbox.
  Each test is a small Python script that *tries to violate* one claim
  (resolve DNS despite `--unshare-net`, write past `--rlimit-fsize`,
  read `/etc/shadow`, see host PID tree, etc.) and exits 0 if blocked.
  Tests run via the production `run_sandboxed_script()` code path so
  a green suite means the claims hold for THIS deployment's bwrap +
  apparmor + seccomp + kernel combination — not just "bwrap launches".
  15 tests across 6 categories (`always`, `rlimit`, `tmpfs`, `seccomp`,
  `pid_strict`, `slow`); skips are explicit and per-category. Opt-in
  only — zero cost to normal boot. Add `--self-test-slow` for the
  rlimit-cpu / wait_for ceilings (~20s extra).

  Usage: `python -m wyoming_llm_agent --self-test-sandbox`. Recommended
  after HAOS / kernel updates, after touching `apparmor.txt` or
  `_bwrap_argv()`, or when investigating "is sandbox X actually
  enforced?". Returns exit 0 on all-pass-or-skip, 1 on any real failure.

## 1.13.1

- **Fix: AppArmor profile rewritten to minimal/conservative form.**
  The detailed allowlist shipped in 1.13.0 (per-cap, explicit
  `mount options=(...)`, ptrace mode list, per-path file rules with
  alternated globs) was rejected by `apparmor_parser` on the HAOS
  host (Supervisor surfaced `Can't load profile … exit status 1`
  without parser stderr). The addon image built fine but the
  install failed at the profile-load step.

  New profile uses only bare top-level verbs (`file`, `capability`,
  `network`, `mount`, `umount`, `pivot_root`, `ptrace`, `signal`)
  that have been stable in apparmor for years. Outer profile
  permits bwrap to set up the sandbox; **inner** bwrap argv +
  seccomp denylist remain the actual confinement boundary for skill
  scripts (see [notes/sandbox.md](notes/sandbox.md)). Security
  rating stays at **4**.

## 1.13.0

- **Per-user BOOTSTRAP (workspace slot 7).** New file at
  `/config/memory/users/<id>/BOOTSTRAP.md`, sibling to USER.md.
  Same seed-on-first-encounter pattern as USER.md: written once the
  first time the agent sees a new safe `user_id`, capped at 8KB.
  Rendered between **shared MEMORY** (slot 6) and **USER profile**
  (slot 8) — placing per-user override instructions right next to
  per-user identity. `_strip_bootstrap_placeholder` (memory.py)
  drops heading-only / italic-only seeded content so the placeholder
  costs zero tokens until the user writes substantive guidance.
  `_compose_system` expanded 11 → 12 sections; ordering invariant
  in [AGENTS.md](AGENTS.md) and [notes/workspace.md](notes/workspace.md)
  updated. Activates only when HA delivers `context["user_id"]` —
  still gated on L6 (see below).
- **Skill sandbox hardening (`wyoming_llm_agent/sandbox.py`).**
  - Dynamic capability probes at startup for both `--rlimit-as`
    family support (`_detect_bwrap_rlimit_support`) and nested-`proc`-
    mount support (`_detect_bwrap_pid_unshare_support`). Each probe
    runs once, caches a module flag, and `_bwrap_argv()` branches off
    of it — no static feature assumption.
  - **Strict vs relaxed PID mode.** When the outer container allows
    bwrap to mount a fresh `proc` (HA Container, docker-direct),
    we use `--unshare-pid` + `--proc /proc` (strict). When it doesn't
    (HAOS / nested LXC — common), we fall back to host pidns +
    `--ro-bind /proc /proc` (relaxed). `--unshare-user` + seccomp
    `ptrace`/`kill` denial still prevent the script from acting on
    visible processes; PID visibility is the only difference. Both
    modes log a clear INFO line so operators see which path their
    deploy took.
  - **More rlimits when bwrap supports them** (bwrap ≥0.10, Alpine
    base ≥3.22): `--rlimit-fsize 16MB` (single-file write cap),
    `--rlimit-nofile 64` (fd cap), alongside the existing
    `--rlimit-as 200MB` and `--rlimit-cpu 5`. `--tmpfs /tmp` now
    has `--size 64MB` so a runaway write can't exhaust addon RAM.
  - Threat table + bwrap argv block in [notes/sandbox.md](notes/sandbox.md)
    refreshed.
- **Base image: Alpine 3.19 → 3.23.** `Dockerfile` sets
  `ARG BUILD_FROM=ghcr.io/home-assistant/base:3.23` directly (the
  legacy `build.yaml` is deleted — Supervisor 2026.04+ removed the
  fallback). Brings Python 3.13 + bubblewrap 0.11 with full
  `--rlimit-*` family, which the dynamic probe now picks up
  automatically.
- **Custom AppArmor profile (`apparmor.txt`) + `apparmor: true`.**
  The Supervisor-auto profile blocks bwrap's `mount(MS_SLAVE|MS_REC)`
  even with `CAP_SYS_ADMIN`. Setting `apparmor: false` worked but
  cost a security-rating point. Now we ship a custom profile that
  enumerates the exact mount-option set bwrap performs
  (`mount options=(rw, silent, slave, rec),` and friends —
  bare `mount,` doesn't cover propagation-flag-only remounts on
  all kernel/AppArmor combos). Inner bwrap argv still does the
  actual confinement; this profile only needs to **not block** the
  outer process. Security rating: **3 → 4**.
- **Fix: discovery URI now publishes the container IP**
  (`rootfs/etc/s6-overlay/s6-rc.d/discovery/run`). HA Core's
  `wyoming/conversation.py` was intermittently raising
  `OSError([Errno -5] Name has no usable address)` when trying to
  `getaddrinfo` our addon's hostname, surfacing to the user as
  `"Error communicating with service: ..."`. Underscored
  addon-container hostnames are RFC-952-invalid; Docker DNS
  tolerates them but HA Core's resolver sometimes returns
  NOERROR-with-empty-answer = `EAI_NODATA`. `hostname -i` gives the
  unambiguous container IP; discovery re-fires every restart so the
  IP stays current. Falls back to `$(hostname)` if `hostname -i`
  returns nothing.
- **L6 documented** (`Transcript.context["user_id"]` not populated by
  HA Core). Detail section in [notes/ha-version-limitations.md](notes/ha-version-limitations.md);
  `handler.py` comment corrected (the prior wording implied a
  scheduled fix that doesn't exist). Per-user code paths land in
  this release but stay dormant until HA Core upstream ships the
  ~10-line fix to `wyoming/conversation.py`.
- **Version alignment.** `wyoming_llm_agent/__init__.py`,
  `pyproject.toml`, and `config.yaml` all now report **1.13.0**
  (previously drifted across 1.12.0 / 1.12.1 / 1.12.1).

## 1.12.1

- **Startup HA mcp_server probe.** After the `HA mcp_server delegation:` log,
  the addon now runs a one-shot `fetch_session_snapshot()` and logs the
  HA-side tool inventory (`HA mcp_server: N tool(s) discovered (...)`)
  so operators see counts and names in boot logs without enabling DEBUG.
  Result is discarded — the per-turn fetch invariant is unchanged. On
  failure or empty inventory, a single INFO line notes the lazy fallback.
- **Quieter INFO logs.** `httpx` and `mcp.client.streamable_http` are
  demoted to WARNING unless `--debug` is set. Eliminates the per-request
  `HTTP Request: GET ... 200 OK` flood and the session-ID / protocol-version
  chatter during MCP discovery and per-turn HA fetches.

## 1.12.0

- **Persistent MCP resource listener** (new `wyoming_llm_agent/mcp_listener.py`).
  One background asyncio task per configured `mcp_servers:` entry holds
  an open MCP session, subscribes to every tracked SKILL.md URI, and
  receives `notifications/resources/updated` + `notifications/resources/list_changed`
  per the MCP spec. Reconnects on disconnect with bounded backoff
  (1s → 30s cap), re-subscribes after reconnect. Tool dispatch stays
  on ephemeral per-call sessions — the listener is a parallel channel,
  not a replacement.
- **Live skill refresh.** When the listener gets `resources/updated`
  for a tracked URI, the addon re-fetches that server's bundles,
  re-installs anything whose `sha256(SKILL.md + sorted siblings)`
  changed, and calls `Agent.reload_skills()` so the new SKILL.md body
  becomes available on the next conversation turn. `list_changed`
  triggers a full re-discovery of that server's bundles. All driven
  by the spec's notification flow — no polling.
- **`resources/list` pagination.** `_list_resources_paginated()` follows
  `nextCursor` until exhausted; sanity-capped at 10000 entries per
  server. Older MCP SDKs that lack the `cursor` kwarg fall back to
  single-page behaviour.
- **`Agent.reload_skills(skills_dir)`** new public method: atomically
  replaces `_skills_by_name`, prunes `loaded_skills` entries in active
  conversations for skills that disappeared, retains the rest. Updates
  the `loaded_skills` Prometheus gauge.
- New invariant in [AGENTS.md](AGENTS.md): "Tool dispatch sessions are
  ephemeral; resource notification sessions are persistent per
  `mcp_servers:` entry."

## 1.11.0

- **New: MCP-resource skill auto-discovery**. Each server configured
  under `mcp_servers:` is scanned at startup for `resources/list`
  entries whose URI ends in `/SKILL.md` (`text/markdown`). Sibling
  resources sharing the same URI prefix become the skill's bundled
  files, written to `/config/skills/<frontmatter-name>/`. Lets a server
  author who controls both the MCP server and the skill (the wardrowbe
  case) deliver tools + skill from one config entry. Servers without
  `resources` capability return an empty list — single DEBUG log,
  zero cost.
- This is **not an agentskills.io standard**; the SKILL.md file format
  is agentskills.io-compliant, but the "URI-ending-in-/SKILL.md as
  manifest, same-prefix siblings as bundle" convention is this addon's
  own. Documented in [notes/skills.md](notes/skills.md).
- Hash-based update tracking shares the same `/data/skill_install_state.json`
  as `skill_urls:`, with key format `mcp://<server-name>#<skill-name>`
  and identifier `sha256(SKILL.md + sorted siblings)`. Unchanged
  bundles install nothing on restart.
- Per-server and per-skill failures are logged WARNING and never block
  startup or other servers.
- New public API: `wyoming_llm_agent.mcp_client.MCPSkillBundle` +
  `fetch_skill_bundles(server)`, consumed by
  `wyoming_llm_agent.skill_fetcher.fetch_mcp_skills(servers, target_dir, state_path)`.

## 1.10.1

- **Remove `custom_tools` (custom HTTP tools) feature**: config option,
  CLI flag, `wyoming_llm_agent/extensions.py` module, agent dispatch
  path, smoke tests, docs all deleted. Reason: the feature overlapped
  with two cleaner paths — `intent_script:` in HA's configuration.yaml
  (surfaces automatically via HA mcp_server) for in-HA automations,
  and `mcp_servers:` for arbitrary outside-HA tool sources. Keeping
  a third HTTP tool path complicated the config schema and added
  surface area for no unique capability.
- Tool dispatch reduces to two sources: HA mcp_server (per-turn) and
  external MCP servers (startup-cached). The `tool_calls_total`
  Prometheus metric label `source` now only takes values `ha` /
  `mcp` / `unknown` (was `ha` / `mcp` / `http` / `unknown`).

## 1.10.0

- **New: `skill_urls` config option** — list of URLs the addon downloads
  into `/config/skills/<slug>/` at startup. Each entry is a GitHub repo
  URL (`https://github.com/user/repo`, optional `@ref` for branch / tag
  / commit) or a direct `.tar.gz` / `.tgz` / `.zip` archive URL.
- **Hash-based update tracking**: per-URL upstream identifier (GitHub
  commit SHA, ETag, or sha256 fallback) persisted to
  `/data/skill_install_state.json`. Unchanged URLs cost only one API
  request per restart; when upstream changes, the matching skill folder
  is overwritten (so don't local-edit skills you also auto-fetch).
- Path-traversal entries and symlinks pointing outside the extraction
  root are rejected before extraction. 100 MiB archive cap. Failures
  per URL log WARNING and never block startup.
- Multi-skill repos supported — `rglob("SKILL.md")` finds every skill
  in the archive and installs each into its own slug folder based on
  the frontmatter `name`. Same behaviour handles repos that bundle an
  MCP server alongside an agentskills.io skill: the SKILL.md gets
  installed, the MCP server source files are discarded (use
  `mcp_servers:` if you want to also connect to it at runtime).
- Wired via `--skill-url URL` (repeatable) + `--skill-state-path PATH`
  CLI flags; s6 run script forwards from `skill_urls:` config (`jq`
  iteration, no `bashio::config 'key|keys'` indirection — direct
  `.skill_urls[]?` for unambiguous handling).

## 1.9.3

- **DEBUG: log MCP tool call results** (`ref.server.tool args=... -> ok=
  text=... structured=...`). Previously we logged the request but not
  the response, so when HA's mcp_server returned a "0 entities matched"
  success the LLM hallucinated "거실 불을 껐어요" and we had no trail
  to debug it.
- **Docs**: documented two HA-side limitations users will hit:
  1. "This assistant cannot control your home" UI banner on HA ≤
     2026.5.x. The addon advertises `supports_home_control=True`
     correctly; HA 2026.5.4 just doesn't read it (wyoming dep pinned
     at 1.7.2 which lacks the field, and the conversation integration
     code wouldn't check it anyway). Both gaps close in HA 2026.6.0
     via [PR#170682](https://github.com/home-assistant/core/pull/170682)
     and [PR#171615](https://github.com/home-assistant/core/pull/171615).
     **Tool execution itself is unaffected** — only the cosmetic banner.
  2. Pipeline debug UI shows empty `data.success` / `data.failed` for
     every voice command. Wyoming `Handled` event has no channel for
     per-tool execution trace; ground truth is the addon's DEBUG log.

## 1.9.2

- **Fix: 5-minute HA pipeline timeout on every conversation turn.**
  HA's wyoming conversation integration does not consume
  `HandledStart` / `HandledChunk` / `HandledStop` events for the
  conversation domain — `_async_process` only branches on `Handled`
  / `NotHandled`. The `supports_handled_streaming` flag is defined
  in the wyoming protocol library but is read nowhere in HA core.
  So with `streaming_enabled: true` we emitted events HA silently
  discarded and the pipeline waited 300s for a terminal event that
  never came. Verified against OHF-Voice's own newest experimental
  conversation agent `intent-gemma4` (May 2026): it too emits single
  `Handled`, not streaming.
- Streaming removed end-to-end: `--streaming-enabled` CLI flag,
  `streaming_enabled` config option, `handler._run_streaming`,
  `agent._run_loop_streaming`, `llm.chat_stream`,
  `supports_handled_streaming` advertisement, the s6 branch, and the
  matching translations. Handler always emits one terminal `Handled`
  / `NotHandled` per Transcript.
- The previous 1.9.2 and 1.9.3 (`asyncio.timeout` and
  background-task patches on `dispatch_mcp_tool`) were chasing the
  wrong layer — the MCP path was healthy. Reverted to the simple
  open-session + call-tool + return-digest implementation.

## 1.9.1

- **Fix: multi-line `system_prompt` broke addon startup.** The s6 run
  script's final `exec` line expanded `${flags[@]}` unquoted, so a
  multi-line Jinja2 system_prompt was word-split into many positional
  args, tripping argparse's "unrecognized arguments". Quoting to
  `"${flags[@]}"` fixes it. Affects every install whose
  `system_prompt:` contains spaces — i.e. the default value as of 1.5.0.

## 1.9.0

- **Skill script execution via bubblewrap sandbox.** New
  `run_skill_script(skill_name, script_path, args, stdin)` meta-tool
  runs Python scripts bundled in a loaded skill's directory inside an
  isolated subprocess. Strong isolation, permissive commands — no
  per-script approval prompt (voice UX) but no host access either.
- **Isolation policy** (see notes/sandbox.md for the full inventory):
  `--unshare-all` (no net, fresh user/mount/pid/ipc/uts/cgroup ns),
  seccomp BPF denying ptrace/mount/bpf/unshare/setns/kexec/perf_event/
  pivot_root/chroot etc., scrubbed env (no SUPERVISOR_TOKEN, no
  api_key), `--ro-bind` only /usr + /lib + skill dir, `/tmp` tmpfs,
  rlimit-as 200MB, rlimit-cpu 5s, asyncio wait_for 10s, stdout/stderr
  capped 256 KB each.
- **Path validation** rejects abs paths, `..` segments, non-`.py`,
  and `/proc/self/root` rebinds before bwrap ever launches.
- **Startup probe.** `probe_sandbox()` runs `bwrap --unshare-all --
  /bin/true` end-to-end. Failure → log specific hint
  (CAP_SYS_ADMIN missing / kernel userns / nested container) and set
  `agent.sandbox_available = False`. `run_skill_script` is then
  hidden from `_meta_tool_defs` — LLM never sees a tool that can't
  work. Other skill features keep working.
- **Loaded-skill enforcement.** `run_skill_script` rejects with
  `ok=False, error="...not loaded..."` unless the skill is already in
  `convo.loaded_skills`. Forces the LLM through `load_skill` first so
  the SKILL.md body is in context.
- New deps: `bubblewrap`, `py3-libseccomp` (alpine packages, image-only).
- `config.yaml`: `privileged: [SYS_ADMIN]` required so bwrap can
  create user namespaces inside the addon container.
- Docs: `notes/sandbox.md` (full design + 8 escape-pattern defences),
  `notes/skill-design-decisions.md` (16 decisions PR2→sandbox with
  chosen vs rejected + rationale).

## 1.8.0

- **`allowed-tools` tool gating.** When a skill registers
  `allowed-tools: pattern1 pattern2 ...`, those tools become invisible
  to the LLM until the skill is loaded. Real lazy disclosure — schema
  tokens for niche tools (50–200 each) stop hitting every turn.
- Patterns use Python `fnmatch` (`*`, `?`, `[seq]`); case-sensitive.
  Prefix (`xbloom_*`), suffix (`*_pour`), and middle wildcards all
  supported. No brace expansion (`{a,b}`).
- **Same-turn unlock.** After `load_skill` in iteration N,
  `_dispatch_tool_calls` returns a `skill_state_changed` flag → the
  loop calls `_recompute_tools` so iteration N+1 in the same user
  turn sees the newly unlocked tools.
- **Meta tools (`list_skills` / `load_skill` / `unload_skill`) are
  never hidden,** even if a pathological skill pattern matches their
  names. The LLM must always be able to activate skills.
- Internal: `_TurnContext` dataclass bundles ha_tools / other_tools /
  query / system_ctx for the loop. `_filter_tools` gains
  `skill_force_include` / `skill_hidden` kwargs (replaces the
  placeholder `extra_candidates` / `forced_companions`).

## 1.7.0

- **Skills exposed to the LLM via agentskills.io progressive disclosure.**
  Every turn's system message now ends with `Available skills (call
  load_skill to activate when relevant):` + one line per registered
  skill (`- name: description`, ~30 tokens each). Same content across
  turns → upstream prompt cache keeps hitting.
- **Three always-on meta-tools** added (bypass `tool_filter_top_k`):
  - `list_skills()` returns `{available, loaded}` for mid-turn checks.
  - `load_skill(name)` activates a skill for the conversation; its
    `SKILL.md` body is appended to the system message at the end and
    visible from the very next round-trip in the **same user turn**.
  - `unload_skill(name)` removes it.
- **Per-conversation state** (`_Conversation.loaded_skills: set[str]`)
  persists across turns until the conversation is evicted (30 min TTL)
  or the user explicitly unloads.
- **Cache-friendly system layout**: stable prefix (user prompt + HA
  api_prompt + language + skill catalog) → suffix (active skill
  bodies) shifts only on load/unload, never per-utterance.
- Internal: `_SystemContext` dataclass + `_compose_system_from_ctx`
  helper. `_run_loop_blocking` / `_run_loop_streaming` /
  `_dispatch_tool_calls` now take `convo` + `system_ctx` so a meta-tool
  call can rebuild `messages[0]` in place.

## 1.6.0

- **agentskills.io-format Skill loader.** New `skills_enabled` option
  + `addon_config:rw` mount. Skill folders live at the hardcoded path
  `/config/skills/<slug>/SKILL.md` (host:
  `/addon_configs/{repo}_llm_conversation_agent/skills/`); the s6 run
  script `mkdir -p`s the directory on boot so users can drop files in
  without manual setup. Parser implements the
  spec's standard frontmatter fields verbatim — `name`, `description`,
  `license`, `compatibility`, `metadata`, `allowed-tools`. **No
  vendor metadata namespace** — skills authored here work as-is in
  Claude / OpenAI Codex / OpenClaw, and theirs work here.
- **Strict validation, soft failure.** Bad SKILL.md (missing required
  field, name regex violation, oversized) logs WARNING + skip. Addon
  never crashes on a malformed skill.
- **Path-traversal defense.** Symlinks rejected for both the
  subdirectory and `SKILL.md` itself; each skill's resolved realpath
  must stay inside `/config/skills/`. 256 KB cap per file.
- **No LLM exposure yet.** PR2 registers skills only; `list_skills` /
  `load_skill` meta-tools land in PR3 (agentskills.io progressive
  disclosure). `scripts/` / `assets/` / `references/` directories are
  not read — sandboxed execution comes in a future PR-sandbox using
  bubblewrap + s6 user separation.
- New Prometheus gauge `llm_agent_loaded_skills`.
- New dependency: `PyYAML>=6,<7`.
- Docs: `notes/skills.md` covers the format, security model, and PR
  roadmap. `notes/options-cli-mapping.md` updated. AGENTS.md gains one
  invariant line.

## 1.5.0

- **`system_prompt` is now a Jinja2 template**, rendered per turn with
  variables `device_id`, `satellite_id`, `language`, `conversation_id`.
  Default (visible in `config.yaml` / addon UI) includes a device-context
  block that turns generic phrases into area-aware requests when the
  active tools accept device/area parameters — works immediately with
  ha-mcp third-party MCP server and custom HTTP tools. No-op for HA's
  built-in mcp_server (hard-codes `device_id=None`); harmless extra
  context otherwise.
- **User-visible default moved into `config.yaml`** (multi-line `|`
  block). `const.DEFAULT_SYSTEM_PROMPT` is now empty — clearing the UI
  field produces a truly empty user prompt rather than reverting to a
  hidden built-in text. Inspect or partially edit from the addon UI.
- **Jinja2 sandbox**: `SandboxedEnvironment` + `StrictUndefined` so
  typos / unknown variables surface at render time. Render failure
  falls back to the raw text + WARNING — voice operation never breaks
  on a bad template.
- Time/date variables (e.g. `now`) intentionally not exposed — per-turn
  values invalidate the upstream prompt cache.
- Not HA's Jinja2: `states()`, `state_attr()`, etc. are unavailable
  (addon runs in a separate container). Use MCP tools at runtime for
  state.
- New dependency: `Jinja2>=3.1,<4`.
- Docs: `AGENTS.md` slimmed; deep-dive sections moved to `notes/`
  (`caching-and-tool-filtering.md`, `system-prompt-jinja2.md`,
  `ha-mcp-server-internals.md`, `options-cli-mapping.md`). Runtime
  unchanged.

## 1.4.0

- **`ha_tools_mode` option** (`always` | `embedding`, default `always`).
  Controls whether HA mcp_server tools join the embedding-based top-K
  filter alongside custom HTTP / external MCP tools. Previously HA tools
  were hardcoded as always-include. Default preserves that behaviour;
  setting `embedding` opts into token savings at the cost of upstream
  prompt-cache stability.
- **Cache hit telemetry**: `llm_agent_cached_prompt_tokens_total{model}`
  Prometheus counter, sourced from `usage.prompt_tokens_details.cached_tokens`
  in the upstream response (supported by OpenAI Cloud and vLLM APC).
  Cache hit rate = `cached / prompt` — compute in Prometheus/Grafana.
- **Embedding-cache keys now include a description hash**: `name:sha256(desc)[:16]`.
  HA renaming or redescribing an entity invalidates the entry automatically
  on next lookup. No manual reload after entity config changes.
- **HA tool embedding pre-warm at startup** (when `ha_tools_mode=embedding`).
  Best-effort: silent fallthrough to per-turn lazy fill if HA isn't
  reachable yet — addon boot order doesn't matter.
- **Embedding failure fallback for HA tools**: a failed batch this turn
  degrades to include-all (never drops tools), with a `WARNING` logged.
- Internal: `Agent._filter_tools()` signature reshuffled — now takes
  `ha_tools` and `other_tools` as keyword args separately. Placeholder
  keyword args `extra_candidates` / `forced_companions` reserved for
  the upcoming skill system (no-op now).

## 1.3.0

- **`verify_ssl` option** (default `true`). Single global switch that
  controls TLS verification on every outbound HTTP call the addon
  makes — LLM chat, embedding, MCP sessions, and custom_tools alike.
  Set `false` for trusted local self-hosted endpoints (Ollama / vLLM /
  custom proxy) terminating TLS with self-signed certs. A loud
  `WARNING` is logged at startup whenever verification is disabled.
- Threaded through `LLMConfig`, `EmbeddingConfig`, `MCPServerConfig`,
  and `AgentConfig`. For MCP, a custom `httpx_client_factory` is passed
  to `streamablehttp_client` / `sse_client` so the SDK's transport
  uses our `verify` setting too.
- Common preflight failure mode this fixes: base_url HTTP → server
  301-redirects to HTTPS → SSL verify rejects self-signed cert →
  `Preflight: could not connect to upstream … CERTIFICATE_VERIFY_FAILED`.

## 1.2.0

- **Streaming responses** (`streaming_enabled: true`, opt-in). When on,
  the agent emits Wyoming `HandledStart` → `HandledChunk(text)` × N →
  `HandledStop` instead of one `Handled(text)` event. HA TTS can start
  synthesizing audio before the LLM finishes generating the full reply
  — meaningful win on long replies. Short control replies see no
  difference. Default off because non-streaming is simpler and adequate
  for the common case.
- New `LLMClient.chat_stream()` async generator yielding parsed SSE
  events (`content`, `tool_call_partial`, `usage`, `finish`, `error`).
  Caller assembles tool_call argument fragments by `index`.
- `Agent.respond()` gained an optional `on_chunk` async callback.
  When provided, runs the streaming loop; when None, runs the
  non-streaming loop (existing behavior). Both produce the same final
  state, history, and metrics.
- `HandleProgram.supports_handled_streaming` is now dynamic — `True`
  when `streaming_enabled`, `False` otherwise.
- Streaming requests include OpenAI's `stream_options:
  {include_usage: true}` so the `usage` field still arrives (in the
  final pre-`[DONE]` SSE frame), keeping the prompt/completion token
  metrics accurate.
- **Dev tooling**: Local development standardized on
  [`uv`](https://github.com/astral-sh/uv) (~10× faster venv setup,
  hardlinked global wheel cache → near-zero marginal disk per addon
  in a multi-repo workspace). `python3 -m venv` still works
  identically — uv is a speed/disk optimization, not a requirement.
  See AGENTS.md "Local development" for both paths plus a docker-only
  alternative.

## 1.1.0

- **Prometheus `/metrics` endpoint** (default port 9099, configurable).
  Counters / histograms / gauges cover upstream LLM call volume, token
  consumption (from the OpenAI-shape `usage` field every compliant
  provider returns), per-call latency, tool dispatches by source
  (HA / external MCP / custom HTTP), MCP session round-trip times,
  embedding calls, conversation count, and per-turn duration.
  Compatible with HA's `prometheus` integration or any external
  Prometheus server.
- Cost ($) is **not** exposed — prices vary too much per
  model/provider. Compute it in a Prometheus recording rule or Grafana
  panel from `prompt_tokens_total` / `completion_tokens_total`.
- New options: `metrics_enabled` (bool, default `true`) and
  `metrics_port` (default `9099`).
- New dependency: `prometheus_client>=0.21,<1` (~50 KB).
- Tiny asyncio-only HTTP server in `metrics_http.py` (no aiohttp /
  starlette dep) to keep the image lean.

## 1.0.0

Initial release. A Wyoming conversation agent backed by any
OpenAI-compatible LLM, delegating all Home Assistant access to HA's
built-in `mcp_server` integration over Streamable HTTP. The addon
acts purely as a Wyoming server and an MCP client; HA owns
entity exposure, tool schemas, and the per-call system prompt.

Architecture and operation:

- Each turn the agent opens one session to HA's `mcp_server`, fetches
  `tools/list` (entity enums current) and `prompts/get("Assist")`
  (entity overview + HA's curated instructions), composes a system
  message, runs the LLM tool loop, and emits `Handled(text)`. HA
  state is never cached across turns; newly exposed entities appear
  immediately.
- HA's `mcp_server` is auto-configured at
  `http://supervisor/core/api/mcp` using `SUPERVISOR_TOKEN`
  (auto-set by `homeassistant_api: true`). The `ha_mcp_enabled`
  boolean toggles delegation; off means no HA tools are visible.
- Tool sources merged each turn:
  - HA mcp_server (`HassTurnOn`, `HassLightSet`, …) — fetched fresh
  - External MCP servers (memory, vector search, GitHub, etc.) —
    discovered once at startup
  - `custom_tools` — arbitrary outside-HA HTTP endpoints with
    `{placeholder}` URL templating
- Optional embedding-based filter (`embedding_model` +
  `tool_filter_top_k > 0`) keeps the LLM tool list small when the
  total crosses the model's degradation threshold (~30–50 tools).
  HA tools always pass the filter regardless.

Wyoming-side features:

- Auto-discovers as a Wyoming conversation agent (HA picks it up
  under Settings > Devices & services).
- `HandleProgram.supports_home_control=True` (requires Wyoming 1.9+)
  unlocks Assist control routing.
- Multi-turn conversation memory keyed by HA's `conversation_id`,
  trimmed to `history_turns` last turns.
- Per-turn `max_tool_iterations` cap prevents runaway models from
  looping forever on the same query.

Resilience:

- `LLMClient.chat()` and `EmbeddingClient.embed()` retry once on
  transient transport errors (`RemoteProtocolError`, `ReadError`,
  `ConnectError`, …) so half-closed keepalive sockets after network
  blips don't fail the first request silently.
- Startup function-calling probe sends one tools-bearing chat
  completion and logs a loud error if the model doesn't actually
  return `tool_calls` — catches the common "I picked a model that
  can't call tools" misconfiguration before the user wonders why
  nothing turns on.
- Cold-load tolerant: probe uses a 180 s floor on its read timeout
  so local Ollama / vLLM with lazy-loaded models doesn't trip on
  the steady-state `request_timeout`.

Requirements:

- Home Assistant **2026.3.0+** and the "Model Context Protocol
  Server" integration enabled (Settings > Devices & services >
  Add Integration > "Model Context Protocol Server", LLM API
  "Assist").
- Wyoming **1.9+**, MCP Python SDK **1.27+**.

Known limitations (intentional, not bugs):

- **Area-aware routing is offline.** HA's `mcp_server` hard-codes
  `device_id=None` in the LLM context, so "turn on the lights"
  without naming an area can't be auto-targeted to the speaker's
  room. The LLM asks for clarification or requires the user to
  name an area explicitly. Resolution requires an HA core change.
- **HA's per-pipeline "Instructions" textarea is not delivered to
  Wyoming agents.** Wyoming protocol has no field for it and HA's
  `mcp_server.api_prompt` doesn't include it. Use this addon's
  `system_prompt:` option instead.
