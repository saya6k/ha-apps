"""Entry point: argparse + Wyoming AsyncServer.

All HA-side state and tools come from HA's built-in `mcp_server`
integration. Inside an addon, the URL is `http://supervisor/core/api/mcp`
authenticated with the `SUPERVISOR_TOKEN` env var (auto-set when
`homeassistant_api: true`). Outside an addon (local dev), pass
`--ha-mcp-url` + `--ha-mcp-token` explicitly, or set
`--ha-mcp-url=disabled` to skip HA delegation.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from functools import partial
from pathlib import Path

from wyoming.server import AsyncServer

from .agent import Agent, AgentConfig
from .const import (
    DEFAULT_BASE_URL,
    DEFAULT_HA_TOOLS_MODE,
    DEFAULT_HISTORY_TURNS,
    DEFAULT_LANGUAGES,
    DEFAULT_MAX_TOOL_ITERATIONS,
    DEFAULT_MODEL,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_URI,
    HA_TOOLS_MODES,
)
from .embedding import EmbeddingClient, EmbeddingConfig
from .handler import EventHandler
from .llm import LLMClient, LLMConfig
from .mcp_client import MCPServerConfig
from .mcp_client import discover_tools as discover_mcp_tools
from .mcp_client import fetch_session_snapshot, parse_mcp_servers
from .mcp_listener import MCPListenerRegistry
from .metrics_http import serve_metrics
from .preflight import check_function_calling
from .sandbox import probe_sandbox
from .memory import MemoryStore
from .skill_fetcher import fetch_mcp_skills, fetch_skill_urls
from .skills import load_skills_dir
from .workspace import load_workspace

_LOGGER = logging.getLogger(__name__)

# Default HA mcp_server endpoint when running inside an HA addon (the
# supervisor proxies /api/* to core).
DEFAULT_HA_MCP_URL = "http://supervisor/core/api/mcp"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="wyoming_llm_agent")
    p.add_argument("--uri", default=DEFAULT_URI, help="Wyoming server URI (default: %(default)s)")

    # HA mcp_server (Streamable HTTP). Set to the literal string "disabled" to
    # run without any HA delegation (useful for local dev where no HA exists).
    p.add_argument(
        "--ha-mcp-url", default=DEFAULT_HA_MCP_URL,
        help="HA mcp_server URL (default: %(default)s, suitable inside an addon). "
             "Pass 'disabled' to skip HA delegation entirely.",
    )
    p.add_argument(
        "--ha-mcp-token", default=os.environ.get("SUPERVISOR_TOKEN", ""),
        help="Bearer token for HA mcp_server. Defaults to $SUPERVISOR_TOKEN.",
    )

    # LLM upstream.
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p.add_argument("--api-key", default="")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--request-timeout", type=float, default=DEFAULT_REQUEST_TIMEOUT)
    p.add_argument(
        "--verify-ssl", default="true",
        choices=("true", "false"),
        help="Verify TLS certs for all outbound HTTP (LLM, embedding, MCP, "
             "skill_urls). Set false only for trusted local self-hosted "
             "endpoints with self-signed certs.",
    )
    p.add_argument(
        "--extra-header",
        action="append", default=[],
        help="Extra header for upstream calls, in NAME=VALUE form. May repeat.",
    )

    # Agent behavior.
    p.add_argument("--max-tool-iterations", type=int, default=DEFAULT_MAX_TOOL_ITERATIONS)
    p.add_argument("--history-turns", type=int, default=DEFAULT_HISTORY_TURNS)
    p.add_argument(
        "--language",
        action="append", default=None,
        help="Language to advertise (ISO code). Repeat for multiple. "
             "Default: a broad set of common languages.",
    )

    # External MCP servers (startup-discovered tool sources).
    p.add_argument(
        "--mcp-servers", type=_json_arg, default=[],
        help="JSON array (or @/path/to/file.json) of remote MCP servers to connect to.",
    )

    # Embedding-based tool filtering.
    p.add_argument(
        "--embedding-base-url", default="",
        help="OpenAI-compatible /embeddings base URL. Empty = reuse --base-url.",
    )
    p.add_argument(
        "--embedding-api-key", default="",
        help="API key for the embedding endpoint. Empty = reuse --api-key.",
    )
    p.add_argument(
        "--embedding-model", default="",
        help="Embedding model name (e.g. text-embedding-3-small, nomic-embed-text). "
             "Empty disables embedding-based filtering.",
    )
    p.add_argument(
        "--tool-filter-top-k", type=int, default=20,
        help="When > 0 AND --embedding-model is set, filter the per-turn "
             "non-meta tool list down to the top-K by cosine similarity to "
             "the user transcript. Meta tools (skill_* / memory_* / "
             "working_memory_* / journal_*) are budget-free and always "
             "included. Effective only when total non-meta tools exceed "
             "top-K. Default: 20.",
    )
    # Skills (agentskills.io format under /config/skills/<slug>/SKILL.md).
    p.add_argument(
        "--skills-enabled", default="true", choices=("true", "false"),
        help="Scan the skills directory at startup and register "
             "agentskills.io-format Skills. The LLM gets list_skills / "
             "load_skill / unload_skill meta-tools to activate them "
             "(progressive disclosure); run_skill_script runs bundled "
             "scripts in a bubblewrap sandbox when available.",
    )
    p.add_argument(
        "--skills-dir", default="/config/skills",
        help="Skills directory (dev/test only — production uses the hardcoded "
             "/config/skills/ which the s6 run script auto-creates). "
             "Outside an addon, pass an absolute path. Default: %(default)s",
    )
    p.add_argument(
        "--skill-url", action="append", default=[], metavar="URL",
        help="Fetch a skill from URL at startup into /config/skills/. "
             "GitHub repo URL (https://github.com/user/repo[@ref]) or a "
             "direct .tar.gz / .tgz / .zip archive URL. Repeatable. The "
             "addon tracks upstream commit SHA / ETag in "
             "/data/skill_install_state.json and only re-extracts when "
             "the upstream actually changed.",
    )
    p.add_argument(
        "--skill-state-path", default="/data/skill_install_state.json",
        help="Path to the addon-private file that records each --skill-url's "
             "last-installed identifier. Default: %(default)s",
    )
    # Per-user persistent memory (R2). When enabled, the LLM gets
    # memory_save / memory_read / memory_delete meta-tools and a
    # MEMORY.md index in the system prompt. Routes to per-user buckets
    # when HA delivers context["user_id"] (HA 2026.6.0+); otherwise to
    # /config/memory/shared/.
    p.add_argument(
        "--memory-enabled", default="true", choices=("true", "false"),
        help="Enable per-user persistent memory under --memory-dir. The LLM "
             "gets memory_save / memory_read / memory_delete meta-tools and "
             "an index in the system prompt. Default: true.",
    )
    p.add_argument(
        "--memory-dir", default="/config/memory",
        help="Root directory for per-user memory buckets (dev/test only — "
             "production uses /config/memory/ which the s6 run script "
             "auto-creates). Default: %(default)s",
    )
    # Workspace (R3). SOUL.md / IDENTITY.md / HEARTBEAT.md / BOOTSTRAP.md
    # at the addon's /config/ root. The system prompt follows a
    # 10-section cache-stable order (SOUL → IDENTITY → HA api → skills →
    # shared mem → USER profile → user mem → active skill → HEARTBEAT).
    # Per-user USER.md is auto-seeded the first time the agent sees a
    # new household member.
    p.add_argument(
        "--workspace-dir", default="/config",
        help="Workspace root (dev/test only — production uses /config/). "
             "Default: %(default)s",
    )

    p.add_argument(
        "--ha-tools-mode", default=DEFAULT_HA_TOOLS_MODE,
        choices=HA_TOOLS_MODES,
        help="How HA mcp_server tools interact with --tool-filter-top-k. "
             "'always' (default) — HA tools bypass the filter; preserves "
             "upstream prompt-cache stability (the `tools:` array stays "
             "constant across turns). 'embedding' — HA tools also go through "
             "top-K scoring; saves tokens with large HA setups (50+ exposed "
             "entities) but invalidates the prompt cache whenever the top-K "
             "shifts. Only meaningful when --tool-filter-top-k > 0.",
    )

    # Prometheus /metrics HTTP server (separate from the Wyoming TCP socket).
    p.add_argument(
        "--metrics-enabled", default="true",
        choices=("true", "false"),
        help="Start a Prometheus /metrics HTTP server alongside the Wyoming port.",
    )
    p.add_argument(
        "--metrics-port", type=int, default=9099,
        help="Bind port for the /metrics endpoint.",
    )

    # Debug / satellite fallbacks.
    p.add_argument("--device-id", help="Default satellite device id when not supplied by HA.")
    p.add_argument("--satellite-id", help="Default satellite entity id when not supplied by HA.")
    p.add_argument("--debug", action="store_true")
    p.add_argument(
        "--no-preflight", action="store_true",
        help="Skip the startup tool-calling probe (useful if upstream is slow to come up).",
    )
    p.add_argument(
        "--self-test-sandbox", action="store_true",
        help=(
            "Run behavioural self-tests against the live bwrap sandbox and "
            "exit. Each test runs in a real subprocess via the production "
            "run_sandboxed_script() path; prints a pass/fail table and exits "
            "0 if all enforced isolation claims hold (or are validly skipped)."
        ),
    )
    p.add_argument(
        "--self-test-slow", action="store_true",
        help=(
            "With --self-test-sandbox: also run slow tests (rlimit-cpu, "
            "wall-clock timeout). Adds ~15-20s."
        ),
    )

    return p.parse_args()


def _json_arg(v: str):
    """argparse type: parse JSON inline or read from `@/path/to/file.json`."""
    if v.startswith("@"):
        return json.loads(Path(v[1:]).read_text(encoding="utf-8"))
    return json.loads(v)


def _parse_extra_headers(raw: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in raw or []:
        if "=" not in item:
            _LOGGER.warning("Ignoring --extra-header without '=': %r", item)
            continue
        name, value = item.split("=", 1)
        if name.strip():
            out[name.strip()] = value
    return out


_REDACTED_ARGS = {"ha_mcp_token", "api_key", "embedding_api_key", "extra_header"}


def _redacted(args: argparse.Namespace) -> dict[str, object]:
    """Args dict with secret values masked. Safe to log at DEBUG."""
    out: dict[str, object] = {}
    for k, v in vars(args).items():
        if k in _REDACTED_ARGS:
            if isinstance(v, str):
                out[k] = "***" if v else ""
            elif isinstance(v, list):
                out[k] = [f"{item.split('=', 1)[0]}=***" if "=" in item else "***" for item in v]
            else:
                out[k] = "***" if v else v
        elif k == "mcp_servers" and isinstance(v, list):
            out[k] = [_redact_tool(t) for t in v]
        else:
            out[k] = v
    return out


def _redact_tool(tool: object) -> object:
    if not isinstance(tool, dict):
        return tool
    redacted = dict(tool)
    headers = redacted.get("headers")
    if isinstance(headers, list):
        redacted["headers"] = [
            {**h, "value": "***"} if isinstance(h, dict) and h.get("value") else h
            for h in headers
        ]
    return redacted


def _build_ha_mcp_server(
    args: argparse.Namespace, *, verify_ssl: bool,
) -> MCPServerConfig | None:
    if args.ha_mcp_url == "disabled":
        _LOGGER.info("HA mcp_server delegation disabled (--ha-mcp-url=disabled).")
        return None
    if not args.ha_mcp_token:
        _LOGGER.warning(
            "HA mcp_server enabled but no token (SUPERVISOR_TOKEN unset and "
            "--ha-mcp-token not provided). HA tools will be unavailable until "
            "a token is supplied."
        )
        return None
    return MCPServerConfig(
        name="ha",
        url=args.ha_mcp_url,
        transport="streamable_http",
        headers={"Authorization": f"Bearer {args.ha_mcp_token}"},
        verify_ssl=verify_ssl,
    )


async def _run_sandbox_self_test(*, include_slow: bool) -> int:
    """Handle `--self-test-sandbox`: probe sandbox, run behavioural checks,
    print a table, return shell exit code (0 = all pass/skip, 1 = any fail).
    """
    from . import sandbox as _sb  # module-attr access so we see post-probe globals
    print("== sandbox self-test ==")
    ok, reason = await _sb.probe_sandbox()
    if not ok:
        print(f"FATAL: probe_sandbox failed: {reason}")
        return 1
    print(f"  probe: ok")
    print(f"  bwrap --unshare-pid (strict mode) : {_sb._BWRAP_SUPPORTS_PID_UNSHARE}")
    print(f"  libseccomp available : {_sb._SECCOMP_AVAILABLE}")
    print(
        f"  rlimits (preexec_fn): "
        f"AS={_sb.MAX_MEMORY_BYTES // (1024 * 1024)}MB "
        f"CPU={_sb.MAX_CPU_SECONDS}s "
        f"FSIZE={_sb.MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB "
        f"NOFILE={_sb.MAX_OPEN_FILES}"
    )
    print(f"  include slow tests : {include_slow}")
    print()
    checks = await _sb.verify_sandbox_behavior(include_slow=include_slow)
    name_w = max(len(c.name) for c in checks) if checks else 8
    cat_w = max(len(c.category) for c in checks) if checks else 8
    pass_n = sum(1 for c in checks if c.passed)
    skip_n = sum(1 for c in checks if c.skipped_reason)
    fail_n = len(checks) - pass_n - skip_n
    for c in checks:
        status = "SKIP" if c.skipped_reason else ("PASS" if c.passed else "FAIL")
        print(f"  [{status}] {c.name:<{name_w}}  {c.category:<{cat_w}}  {c.detail}")
    print()
    print(f"  total: {len(checks)} | pass: {pass_n} | fail: {fail_n} | skip: {skip_n}")
    if fail_n:
        print(f"  → {fail_n} isolation claim(s) NOT enforced; see notes/sandbox.md")
    return 0 if fail_n == 0 else 1


async def _run() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if not args.debug:
        # httpx logs every request at INFO ("HTTP Request: GET ... 200 OK"),
        # which floods the log during MCP discovery + per-turn HA fetches.
        # mcp.client.streamable_http adds session-ID and protocol-version
        # INFO lines on top of that. Demote both to WARNING; --debug
        # restores INFO via basicConfig above.
        for noisy in ("httpx", "mcp.client.streamable_http"):
            logging.getLogger(noisy).setLevel(logging.WARNING)
    _LOGGER.debug("Args: %s", _redacted(args))

    # Short-circuit: sandbox self-test mode runs the suite and exits.
    if args.self_test_sandbox:
        rc = await _run_sandbox_self_test(include_slow=args.self_test_slow)
        sys.exit(rc)

    verify_ssl = args.verify_ssl == "true"
    if not verify_ssl:
        _LOGGER.warning(
            "TLS verification DISABLED for all outbound HTTP "
            "(LLM, embedding, MCP, skill_urls). Self-signed and expired "
            "certs will silently pass. Use only on trusted local networks."
        )

    llm = LLMClient(LLMConfig(
        base_url=args.base_url,
        api_key=args.api_key,
        model=args.model,
        request_timeout=args.request_timeout,
        verify_ssl=verify_ssl,
        extra_headers=_parse_extra_headers(args.extra_header),
    ))

    mcp_servers = parse_mcp_servers(args.mcp_servers, verify_ssl=verify_ssl)
    mcp_tools: list = []
    if mcp_servers:
        _LOGGER.info(
            "Discovering tools from %d external MCP server(s): %s",
            len(mcp_servers), ", ".join(s.name for s in mcp_servers),
        )
        mcp_tools = await discover_mcp_tools(mcp_servers)
        _LOGGER.info(
            "External MCP discovery complete: %d tool(s) cached.", len(mcp_tools),
        )

    skills: list = []
    if args.skills_enabled == "true":
        skills_dir_path = Path(args.skills_dir)
        skill_state = Path(args.skill_state_path)
        if args.skill_url:
            try:
                await fetch_skill_urls(
                    list(args.skill_url), skills_dir_path, skill_state,
                    verify_ssl=verify_ssl,
                )
            except Exception:  # noqa: BLE001 — never block startup on skill fetch
                _LOGGER.exception(
                    "Skill URL fetch had an unexpected error; "
                    "continuing with whatever is already in %s",
                    args.skills_dir,
                )
        # MCP-resource skill discovery is bound to the (later-started)
        # listener so that any URIs we install are also subscribed to
        # for live updates. The listener instance is created up-front,
        # passed `on_install` to track URIs, and started after the agent
        # is constructed (so the on_updated callback can call back into
        # agent.reload_skills).
        mcp_listener_registry: MCPListenerRegistry | None = None
        listener_tracked: list[tuple[str, list[str]]] = []
        if mcp_servers:
            def _record_install(server_name: str, uris: list[str]) -> None:
                listener_tracked.append((server_name, uris))
            try:
                await fetch_mcp_skills(
                    mcp_servers, skills_dir_path, skill_state,
                    on_install=_record_install,
                )
            except Exception:  # noqa: BLE001 — never block startup on skill fetch
                _LOGGER.exception(
                    "MCP-served skill fetch had an unexpected error; "
                    "continuing with whatever is already in %s",
                    args.skills_dir,
                )
        skills = load_skills_dir(args.skills_dir)
        if skills:
            _LOGGER.info(
                "Loaded %d skill(s) from %s: %s",
                len(skills), args.skills_dir,
                ", ".join(s.name for s in skills),
            )
        else:
            _LOGGER.info(
                "No skills loaded from %s (empty, missing, or all malformed).",
                args.skills_dir,
            )

    ha_mcp_server = _build_ha_mcp_server(args, verify_ssl=verify_ssl)
    if ha_mcp_server is not None:
        _LOGGER.info(
            "HA mcp_server delegation: %s (per-turn tools+prompt fetch)",
            ha_mcp_server.url,
        )
        # Startup probe with retry/backoff. HA often boots slower than this
        # addon (especially right after a host reboot); a single one-shot
        # probe almost always sees an empty tool list and operators are
        # left wondering whether HA control will ever work. Retry with
        # exponential backoff so HA gets a real chance, then surface a
        # clear actionable message if it really is unreachable.
        # Total wait budget: 3+6+12+24 = 45 seconds before giving up.
        # The Wyoming server isn't blocked — voice turns lazy-fetch HA
        # tools every turn regardless of probe outcome.
        probe_delays = (3, 6, 12, 24)
        for attempt in range(len(probe_delays) + 1):
            probe = await fetch_session_snapshot(
                ha_mcp_server, prompt_name=None,
            )
            if probe.tools:
                _LOGGER.info(
                    "HA mcp_server: %d tool(s) discovered (%s)",
                    len(probe.tools),
                    ", ".join(ref.openai_name for ref in probe.tools),
                )
                break
            if attempt < len(probe_delays):
                delay = probe_delays[attempt]
                _LOGGER.info(
                    "HA mcp_server probe returned no tools "
                    "(attempt %d/%d). Retrying in %ds…",
                    attempt + 1, len(probe_delays) + 1, delay,
                )
                await asyncio.sleep(delay)
        else:
            _LOGGER.warning(
                "HA mcp_server still returns no tools after %d attempts "
                "(~%ds). Voice commands needing HA control will fail "
                "until this resolves. Common causes:\n"
                "  1. HA still booting — wait, then check this log again.\n"
                "  2. No entities exposed — open HA: Settings → Voice "
                "assistants → Expose, and toggle on the devices you want "
                "voice control over.\n"
                "  3. Supervisor proxy / SUPERVISOR_TOKEN issue — check "
                "addon logs for 401/403 on requests to %s.\n"
                "  4. HA mcp_server integration not installed.\n"
                "The addon will keep trying lazily on each voice turn.",
                len(probe_delays) + 1, sum(probe_delays),
                ha_mcp_server.url,
            )

    embedding_client: EmbeddingClient | None = None
    if args.embedding_model and args.tool_filter_top_k > 0:
        embedding_client = EmbeddingClient(EmbeddingConfig(
            base_url=(args.embedding_base_url or args.base_url),
            api_key=(args.embedding_api_key or args.api_key),
            model=args.embedding_model,
            verify_ssl=verify_ssl,
            extra_headers=_parse_extra_headers(args.extra_header),
        ))
        _LOGGER.info(
            "Embedding-based tool filter enabled: model=%s, top_k=%d, base_url=%s",
            args.embedding_model, args.tool_filter_top_k,
            embedding_client.config.base_url,
        )

    memory_store: MemoryStore | None = None
    if args.memory_enabled == "true":
        memory_root = Path(args.memory_dir)
        try:
            memory_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            _LOGGER.warning(
                "Could not create memory dir %s (%s); memory disabled.",
                memory_root, exc,
            )
        else:
            memory_store = MemoryStore(root=memory_root)
            _LOGGER.info("Per-user memory enabled at %s", memory_root)
    else:
        _LOGGER.info("Per-user memory disabled (--memory-enabled=false).")

    workspace = load_workspace(Path(args.workspace_dir))
    _LOGGER.info(
        "Workspace loaded from %s: SOUL=%d chars, IDENTITY=%d chars, "
        "BOOTSTRAP body=%d chars, HEARTBEAT=%d chars, auto_load_skills=%s",
        args.workspace_dir,
        len(workspace.soul), len(workspace.identity),
        len(workspace.bootstrap_body),
        len(workspace.heartbeat_template),
        ", ".join(workspace.auto_load_skills) or "—",
    )

    agent = Agent(
        llm=llm,
        config=AgentConfig(
            max_tool_iterations=args.max_tool_iterations,
            history_turns=args.history_turns,
            mcp_tools=mcp_tools,
            ha_mcp_server=ha_mcp_server,
            tool_filter_top_k=args.tool_filter_top_k,
            ha_tools_mode=args.ha_tools_mode,
            skills=skills,
            memory_store=memory_store,
            workspace=workspace,
            verify_ssl=verify_ssl,
        ),
        embedding_client=embedding_client,
    )
    await agent.warmup_embeddings()

    # Sandbox self-test. Only meaningful when skills are registered AND
    # at least one ships a runnable script; we always probe so the log
    # surfaces the capability state, but the LLM-side cost (hiding /
    # showing run_skill_script in the tool list) only matters with
    # skills installed.
    sandbox_ok, sandbox_reason = await probe_sandbox()
    agent.sandbox_available = sandbox_ok
    if sandbox_ok:
        _LOGGER.info("Skill sandbox available (bubblewrap probe ok).")
    elif skills:
        _LOGGER.warning(
            "Skill sandbox UNAVAILABLE: %s. The run_skill_script meta-tool "
            "will be hidden from the LLM; skill instructions + tool gating "
            "still work.", sandbox_reason,
        )
    else:
        _LOGGER.info(
            "Skill sandbox unavailable (%s) — no skills loaded so this "
            "doesn't affect anything.", sandbox_reason,
        )

    languages = args.language or DEFAULT_LANGUAGES

    if not args.no_preflight:
        await check_function_calling(llm)

    metrics_server = None
    if args.metrics_enabled == "true":
        metrics_server = await serve_metrics("0.0.0.0", args.metrics_port)

    mcp_listener_registry = None
    if args.skills_enabled == "true" and mcp_servers:
        skills_dir_for_reload = args.skills_dir
        skill_state_for_reload = Path(args.skill_state_path)

        async def _on_resource_updated(
            server: MCPServerConfig, uri: str,
        ) -> None:
            await _refresh_one_server(
                server, Path(skills_dir_for_reload),
                skill_state_for_reload, agent,
            )

        async def _on_list_changed(server: MCPServerConfig) -> None:
            await _refresh_one_server(
                server, Path(skills_dir_for_reload),
                skill_state_for_reload, agent,
            )

        mcp_listener_registry = MCPListenerRegistry(
            on_resource_updated=_on_resource_updated,
            on_list_changed=_on_list_changed,
        )
        await mcp_listener_registry.start_all(mcp_servers)
        for server_name, uris in listener_tracked:
            mcp_listener_registry.track(server_name, uris)
        _LOGGER.info(
            "Started %d MCP resource listener(s); subscribed to %d skill URI(s).",
            len(mcp_servers), sum(len(u) for _, u in listener_tracked),
        )

    server = AsyncServer.from_uri(args.uri)
    _LOGGER.info(
        "Wyoming LLM agent ready on %s (model=%s, base_url=%s, languages=%d)",
        args.uri, args.model, args.base_url, len(languages),
    )
    _LOGGER.info(
        "Entities exposed to Assist (HA: Settings > Voice assistants > Expose) "
        "are visible via the HA mcp_server tools; this addon never reads HA "
        "state directly. Note: HA mcp_server currently does not propagate "
        "the requesting device's area to the LLM — generic 'turn on the "
        "lights' commands won't auto-target the speaker's room."
    )
    try:
        await server.run(partial(EventHandler, agent, args, languages))
    finally:
        if mcp_listener_registry is not None:
            await mcp_listener_registry.stop_all()
        await llm.aclose()
        await agent.aclose()
        if metrics_server is not None:
            metrics_server.close()
            await metrics_server.wait_closed()


async def _refresh_one_server(
    server: MCPServerConfig, skills_dir: Path, state_path: Path, agent: Agent,
) -> None:
    """Re-fetch skill bundles for one server and reload the agent's registry.

    Called from MCP listener callbacks on resource_updated / list_changed.
    Errors are caught + logged — listener keeps running even if a refresh
    fails (e.g., transient network glitch).
    """
    try:
        await fetch_mcp_skills([server], skills_dir, state_path)
    except Exception:  # noqa: BLE001
        _LOGGER.exception(
            "Refresh of skills from MCP server %s failed", server.name,
        )
        return
    try:
        agent.reload_skills(str(skills_dir))
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Agent.reload_skills failed after MCP refresh")


def run() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    run()
