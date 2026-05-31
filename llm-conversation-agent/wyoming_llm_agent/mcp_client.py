"""MCP (Model Context Protocol) client integration — HTTP / SSE transports.

The user configures one or more remote MCP servers. On startup we:

  1. Connect to each server.
  2. Call `tools/list` and cache the result.
  3. Convert each MCP tool into an OpenAI function-tool definition,
     prefixed by `mcp_<server>_<tool>` so two servers with the same
     tool name don't collide.

At LLM-tool-call dispatch time we look up the matching MCPToolRef by
its OpenAI-facing name, reconnect to the server, and invoke
`tools/call`. The result's text content is fed back to the LLM as the
tool result.

We do NOT keep persistent MCP sessions in v1.2 — per-call reconnect is
simple, robust to disconnects, and the latency overhead (~50-200 ms per
call) is dwarfed by LLM inference time.

Supported transports:
- `streamable_http` (current MCP spec, default — single endpoint)
- `sse` (legacy spec — separate POST/GET endpoints)
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from mcp import ClientSession, types
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

from .metrics import time_mcp_session

_LOGGER = logging.getLogger(__name__)

# OpenAI function names must match ^[a-zA-Z0-9_-]+$ (max 64 chars).
_NAME_SAFE = re.compile(r"[^a-zA-Z0-9_-]")
_NAME_MAX = 64

_DISCOVERY_TIMEOUT = 15.0  # seconds for "connect + initialize + list_tools"


@dataclass
class MCPServerConfig:
    name: str
    url: str
    transport: str = "streamable_http"  # "streamable_http" | "sse"
    headers: dict[str, str] = field(default_factory=dict)
    verify_ssl: bool = True


@dataclass
class MCPToolRef:
    """One LLM-callable tool sourced from an MCP server."""

    openai_name: str          # the prefixed name we expose to the LLM
    server: MCPServerConfig   # which server to dispatch to
    mcp_name: str             # the original tool name on the MCP server
    description: str
    input_schema: dict[str, Any]


def parse_mcp_servers(
    raw: list[dict[str, Any]] | None, *, verify_ssl: bool = True,
) -> list[MCPServerConfig]:
    out: list[MCPServerConfig] = []
    for item in raw or []:
        name = (item.get("name") or "").strip()
        url = (item.get("url") or "").strip()
        if not name or not url:
            _LOGGER.warning("Skipping MCP server with empty name or url: %r", item)
            continue
        transport = (item.get("transport") or "streamable_http").strip().lower()
        if transport not in ("streamable_http", "sse"):
            _LOGGER.warning(
                "Unknown MCP transport %r for server %s; defaulting to streamable_http.",
                transport, name,
            )
            transport = "streamable_http"
        headers_list = item.get("headers") or []
        headers = {
            str(h.get("name", "")).strip(): str(h.get("value", ""))
            for h in headers_list
            if isinstance(h, dict) and str(h.get("name", "")).strip()
        }
        out.append(MCPServerConfig(
            name=name, url=url, transport=transport, headers=headers,
            verify_ssl=verify_ssl,
        ))
    return out


async def discover_tools(servers: list[MCPServerConfig]) -> list[MCPToolRef]:
    """Fan out tool discovery; one bad server doesn't block the rest."""
    if not servers:
        return []
    results = await asyncio.gather(
        *(_discover_one(s) for s in servers),
        return_exceptions=False,  # _discover_one catches its own
    )
    return [t for batch in results for t in batch]


async def _discover_one(server: MCPServerConfig) -> list[MCPToolRef]:
    try:
        async with time_mcp_session(server.name), asyncio.timeout(_DISCOVERY_TIMEOUT):
            async with _open(server) as session:
                tool_list = await session.list_tools()
    except (Exception, asyncio.TimeoutError) as exc:  # noqa: BLE001
        _LOGGER.error(
            "MCP server %s (%s, %s): discovery failed (%s: %s). "
            "Its tools will be unavailable to the LLM until next restart.",
            server.name, server.url, server.transport, type(exc).__name__, exc,
        )
        return []

    refs: list[MCPToolRef] = []
    for tool in tool_list.tools:
        ref = _make_ref(server, tool)
        refs.append(ref)
    _LOGGER.info(
        "MCP server %s: %d tool(s) discovered (%s)",
        server.name, len(refs), ", ".join(r.openai_name for r in refs),
    )
    return refs


def _make_ref(server: MCPServerConfig, tool: types.Tool) -> MCPToolRef:
    openai_name = _safe_name(f"mcp_{server.name}_{tool.name}")
    # The MCP tool's inputSchema is JSON Schema — directly usable as an
    # OpenAI function `parameters` schema. We still defensively ensure
    # `type: object` since some servers omit it.
    schema = dict(tool.inputSchema or {})
    schema.setdefault("type", "object")
    schema.setdefault("properties", {})
    return MCPToolRef(
        openai_name=openai_name,
        server=server,
        mcp_name=tool.name,
        description=tool.description or f"MCP tool {tool.name} on {server.name}",
        input_schema=schema,
    )


def _safe_name(name: str) -> str:
    cleaned = _NAME_SAFE.sub("_", name)
    return cleaned[:_NAME_MAX]


def build_mcp_tools(refs: list[MCPToolRef]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": ref.openai_name,
                "description": ref.description,
                "parameters": ref.input_schema,
            },
        }
        for ref in refs
    ]


@dataclass
class MCPSkillBundle:
    """One SKILL.md served by an MCP server, plus its sibling files.

    Servers expose skills by registering one resource whose URI ends in
    `/SKILL.md` (mimeType text/markdown), and zero or more sibling
    resources sharing the same URI path prefix. We treat the prefix
    (everything up to and including the directory containing SKILL.md)
    as the skill bundle root; sibling URIs' suffix becomes the file's
    relative path under the installed skill directory.
    """

    server_name: str
    skill_md_uri: str
    skill_md_text: str
    # rel_path -> file content. rel_path is relative to the skill root
    # (excluding `SKILL.md` itself; that one is on `skill_md_text`).
    siblings: dict[str, bytes]


_SKILL_MD_SUFFIX = "/SKILL.md"


_RESOURCE_PAGE_CAP = 10_000  # sanity bound — protect against runaway servers


async def _list_resources_paginated(session: ClientSession) -> list[Any]:
    """Walk every page via nextCursor. Caps at _RESOURCE_PAGE_CAP."""
    resources: list[Any] = []
    cursor: str | None = None
    while True:
        try:
            listing = await session.list_resources(cursor=cursor)
        except TypeError:
            # Older SDKs don't accept cursor kwarg; fall through to single-page.
            listing = await session.list_resources()
            resources.extend(listing.resources or [])
            return resources
        resources.extend(listing.resources or [])
        if len(resources) >= _RESOURCE_PAGE_CAP:
            _LOGGER.warning(
                "Resource list exceeded sanity cap %d; truncating",
                _RESOURCE_PAGE_CAP,
            )
            return resources[:_RESOURCE_PAGE_CAP]
        cursor = listing.nextCursor
        if not cursor:
            return resources


async def fetch_skill_bundles(server: MCPServerConfig) -> list[MCPSkillBundle]:
    """List the server's resources (paginated), find every SKILL.md +
    its sibling files, and return one bundle per discovered skill.

    Servers without the `resources` capability (or whose list is empty)
    yield an empty list. Per-skill failures are logged WARNING and
    skipped — one bad skill doesn't kill the server's other skills.
    """
    try:
        async with time_mcp_session(server.name), asyncio.timeout(_DISCOVERY_TIMEOUT):
            async with _open(server) as session:
                try:
                    resources = await _list_resources_paginated(session)
                except Exception as exc:  # noqa: BLE001
                    _LOGGER.debug(
                        "MCP server %s: list_resources unsupported or failed "
                        "(%s: %s); no MCP-served skills available",
                        server.name, type(exc).__name__, exc,
                    )
                    return []
                if not resources:
                    return []
                uri_to_mime: dict[str, str | None] = {}
                for r in resources:
                    uri_to_mime[str(r.uri)] = r.mimeType
                skill_md_uris = [
                    u for u in uri_to_mime
                    if u.endswith(_SKILL_MD_SUFFIX) or u.rsplit("/", 1)[-1] == "SKILL.md"
                ]
                bundles: list[MCPSkillBundle] = []
                for skill_uri in skill_md_uris:
                    try:
                        bundle = await _read_skill_bundle(
                            session, server.name, skill_uri, list(uri_to_mime),
                        )
                    except Exception as exc:  # noqa: BLE001
                        _LOGGER.warning(
                            "MCP server %s: failed to read skill bundle at %s "
                            "(%s: %s); skipping",
                            server.name, skill_uri, type(exc).__name__, exc,
                        )
                        continue
                    bundles.append(bundle)
                return bundles
    except (Exception, asyncio.TimeoutError) as exc:  # noqa: BLE001
        _LOGGER.warning(
            "MCP server %s: skill resource discovery failed (%s: %s); "
            "no MCP-served skills installed this run",
            server.name, type(exc).__name__, exc,
        )
        return []


async def _read_skill_bundle(
    session: ClientSession, server_name: str, skill_uri: str, all_uris: list[str],
) -> MCPSkillBundle:
    """Read SKILL.md + every sibling resource sharing its directory prefix."""
    prefix = skill_uri[: -len("SKILL.md")]  # keeps the trailing "/"
    skill_md_text = await _read_text(session, skill_uri)
    siblings: dict[str, bytes] = {}
    for uri in all_uris:
        if uri == skill_uri:
            continue
        if not uri.startswith(prefix):
            continue
        rel = uri[len(prefix):]
        if not rel or rel.startswith("/") or ".." in rel.split("/"):
            continue
        siblings[rel] = await _read_bytes(session, uri)
    return MCPSkillBundle(
        server_name=server_name, skill_md_uri=skill_uri,
        skill_md_text=skill_md_text, siblings=siblings,
    )


async def _read_text(session: ClientSession, uri: str) -> str:
    result = await session.read_resource(uri)
    for c in result.contents or []:
        text = getattr(c, "text", None)
        if text is not None:
            return text
        blob = getattr(c, "blob", None)
        if blob is not None:
            import base64
            return base64.b64decode(blob).decode("utf-8")
    raise ValueError(f"Resource {uri} returned no readable text/blob content")


async def _read_bytes(session: ClientSession, uri: str) -> bytes:
    result = await session.read_resource(uri)
    for c in result.contents or []:
        text = getattr(c, "text", None)
        if text is not None:
            return text.encode("utf-8")
        blob = getattr(c, "blob", None)
        if blob is not None:
            import base64
            return base64.b64decode(blob)
    raise ValueError(f"Resource {uri} returned no readable text/blob content")


@dataclass
class MCPSessionSnapshot:
    """One round of tools/list + an optional prompt body, fetched in a
    single session. Used by the agent each turn for the HA mcp_server so
    a newly-exposed entity surfaces without an addon restart.
    """

    tools: list[MCPToolRef]
    prompt_text: str | None = None


async def fetch_session_snapshot(
    server: MCPServerConfig,
    *,
    prompt_name: str | None = None,
) -> MCPSessionSnapshot:
    """Open one session, fetch tools/list and (optionally) prompts/get.

    Designed for the HA mcp_server case where the system prompt + tool
    list both update with HA state and need to be fresh each turn. For
    static MCP servers (memory, etc.), keep using `discover_tools` once
    at startup instead.
    """
    try:
        async with time_mcp_session(server.name), asyncio.timeout(_DISCOVERY_TIMEOUT):
            async with _open(server) as session:
                tool_list = await session.list_tools()
                prompt_text: str | None = None
                if prompt_name is not None:
                    try:
                        got = await session.get_prompt(prompt_name)
                        chunks: list[str] = []
                        for msg in got.messages:
                            content = msg.content
                            text = getattr(content, "text", None)
                            if text:
                                chunks.append(text)
                        prompt_text = "\n".join(chunks).strip() or None
                    except Exception as exc:  # noqa: BLE001 — prompt is optional
                        _LOGGER.debug(
                            "MCP server %s: prompts/get(%r) failed (%s: %s); "
                            "continuing without it",
                            server.name, prompt_name, type(exc).__name__, exc,
                        )
    except (Exception, asyncio.TimeoutError) as exc:  # noqa: BLE001
        _LOGGER.warning(
            "MCP server %s: session snapshot failed (%s: %s); "
            "tools and prompt unavailable this turn",
            server.name, type(exc).__name__, exc,
        )
        return MCPSessionSnapshot(tools=[], prompt_text=None)

    refs = [_make_ref(server, t) for t in tool_list.tools]
    return MCPSessionSnapshot(tools=refs, prompt_text=prompt_text)


async def dispatch_mcp_tool(ref: MCPToolRef, args: dict[str, Any]) -> dict[str, Any]:
    """Re-open a session to the MCP server, call the tool, return a digest."""
    try:
        async with time_mcp_session(ref.server.name):
            async with _open(ref.server) as session:
                result = await session.call_tool(
                    ref.mcp_name, arguments=args or {},
                )
    except Exception as exc:  # noqa: BLE001
        _LOGGER.exception("MCP call %s.%s failed", ref.server.name, ref.mcp_name)
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    digest = _result_to_digest(result)
    _LOGGER.debug(
        "MCP call %s.%s args=%s -> ok=%s text=%r structured=%r",
        ref.server.name, ref.mcp_name, args,
        digest.get("ok"), digest.get("text"), digest.get("structured"),
    )
    return digest


def _result_to_digest(result: types.CallToolResult) -> dict[str, Any]:
    """Flatten an MCP CallToolResult into something the LLM can consume."""
    text_chunks: list[str] = []
    other_kinds: list[str] = []
    for block in result.content or []:
        if isinstance(block, types.TextContent):
            text_chunks.append(block.text)
        elif isinstance(block, types.ImageContent):
            other_kinds.append("image")
        elif isinstance(block, types.EmbeddedResource):
            other_kinds.append("resource")
        else:
            other_kinds.append(type(block).__name__)

    text = "\n".join(text_chunks).strip()
    digest: dict[str, Any] = {
        "ok": not bool(result.isError),
        "text": text,
    }
    if other_kinds:
        digest["other_content"] = other_kinds
    # Prefer structured content if the server returned it; some tools
    # respond with JSON encoded as TextContent — try to parse for free.
    if getattr(result, "structuredContent", None) is not None:
        digest["structured"] = result.structuredContent
    elif text:
        try:
            digest["structured"] = json.loads(text)
        except (ValueError, TypeError):
            pass
    return digest


def _make_factory(verify_ssl: bool):
    """httpx_client_factory matching MCP SDK's signature, with verify wired in.

    The SDK's default factory (`mcp.shared._httpx_utils.create_mcp_http_client`)
    constructs an `AsyncClient` itself, so we can't post-hoc set `verify`.
    We provide our own factory that mirrors the SDK's expected interface.
    """
    import httpx as _httpx

    def factory(headers=None, timeout=None, auth=None):
        return _httpx.AsyncClient(
            headers=headers or {},
            timeout=timeout if timeout is not None else 30,
            auth=auth,
            verify=verify_ssl,
            follow_redirects=True,
        )
    return factory


@asynccontextmanager
async def _open(server: MCPServerConfig):
    """Open an MCP ClientSession over the configured transport."""
    factory = _make_factory(server.verify_ssl)
    if server.transport == "sse":
        cm = sse_client(
            server.url, headers=server.headers or None,
            httpx_client_factory=factory,
        )
        async with cm as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session
    else:  # streamable_http
        cm = streamablehttp_client(
            server.url, headers=server.headers or None,
            httpx_client_factory=factory,
        )
        async with cm as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                yield session
