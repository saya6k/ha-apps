#!/usr/bin/env python3
"""Probe a Home Assistant MCP server endpoint.

Run from the project root with the venv:

    .venv/bin/python scripts/probe_ha_mcp.py \\
        --url http://homeassistant.local:8123/api/mcp \\
        --token <long-lived-access-token>

What it reports:

  1. Connection + auth — does the supplied token work?
  2. tools/list — every tool HA exposes via MCP, with its name +
     description + JSON schema preview. Compare against the 11 tools
     our addon currently builds itself in `wyoming_llm_agent/tools.py`.
  3. prompts/list — if HA's MCP server exposes prompts, dump the
     content of each. This is the load-bearing check for whether the
     user's Assist "Instructions" field reaches MCP clients.
  4. Round-trip latency for one tool call (HassGetState on the first
     exposed entity it sees, if any).

This script reuses `wyoming_llm_agent.mcp_client._open` so it tests
the exact same transport path the addon would use at runtime.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Make the addon package importable when running from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from wyoming_llm_agent.mcp_client import MCPServerConfig, _open


async def probe(url: str, token: str, transport: str) -> None:
    cfg = MCPServerConfig(
        name="hass",
        url=url,
        transport=transport,
        headers={"Authorization": f"Bearer {token}"} if token else {},
    )

    print(f"\n[1] Connecting to {url} via {transport} …")
    t0 = time.monotonic()
    try:
        async with _open(cfg) as session:
            print(f"    OK ({(time.monotonic() - t0) * 1000:.0f} ms)\n")

            # ---- tools/list ---------------------------------------------
            print("[2] tools/list:")
            try:
                tool_resp = await session.list_tools()
            except Exception as exc:
                print(f"    FAILED: {type(exc).__name__}: {exc}\n")
                tool_resp = None

            if tool_resp:
                print(f"    {len(tool_resp.tools)} tool(s) exposed:\n")
                for t in tool_resp.tools:
                    print(f"    • {t.name}")
                    if t.description:
                        print(f"        {t.description}")
                    schema_preview = json.dumps(t.inputSchema or {}, indent=2)
                    if len(schema_preview) > 600:
                        schema_preview = schema_preview[:600] + "  …"
                    print(f"        schema:\n{_indent(schema_preview, 10)}")
                    print()

            # ---- prompts/list -------------------------------------------
            print("[3] prompts/list (does HA expose the user's Instructions here?):")
            try:
                prompt_resp = await session.list_prompts()
            except Exception as exc:
                print(f"    FAILED: {type(exc).__name__}: {exc}")
                print("    (Probably means HA's MCP server doesn't implement prompts/list,")
                print("     so the Instructions field is NOT reachable via MCP. Use the")
                print("     addon's `system_prompt:` option instead.)\n")
                prompt_resp = None

            if prompt_resp:
                print(f"    {len(prompt_resp.prompts)} prompt(s) exposed:\n")
                for p in prompt_resp.prompts:
                    print(f"    • {p.name}")
                    if p.description:
                        print(f"        {p.description}")
                    try:
                        got = await session.get_prompt(p.name)
                        for msg in got.messages:
                            content = msg.content
                            text = getattr(content, "text", None) or str(content)
                            preview = text if len(text) <= 600 else text[:600] + "  …"
                            print(f"        [{msg.role}]:\n{_indent(preview, 12)}")
                    except Exception as exc:
                        print(f"        get_prompt failed: {exc}")
                    print()

            # ---- one tool call for latency ------------------------------
            if tool_resp and tool_resp.tools:
                # Find a low-risk read-only tool to invoke for a latency sample.
                candidate = next(
                    (t for t in tool_resp.tools
                     if "get" in t.name.lower() or "state" in t.name.lower()),
                    tool_resp.tools[0],
                )
                print(f"[4] Round-trip sample on `{candidate.name}` "
                      "(no-args; may fail if args required — that's fine, we just want timing):")
                t0 = time.monotonic()
                try:
                    await session.call_tool(candidate.name, arguments={})
                    print(f"    Round-trip OK in {(time.monotonic() - t0) * 1000:.0f} ms")
                except Exception as exc:
                    print(f"    Errored in {(time.monotonic() - t0) * 1000:.0f} ms "
                          f"({type(exc).__name__}: {exc})")
                    print("    Timing still useful as a connect+initialize+call lower bound.")

    except Exception as exc:
        print(f"\n    CONNECTION FAILED: {type(exc).__name__}: {exc}")
        sys.exit(1)


def _indent(s: str, n: int) -> str:
    pad = " " * n
    return "\n".join(pad + line for line in s.splitlines())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--url", required=True,
                   help="HA MCP endpoint, e.g. http://homeassistant.local:8123/api/mcp")
    p.add_argument("--token", required=True,
                   help="HA long-lived access token (Profile → Security → Long-lived tokens)")
    p.add_argument("--transport", default="streamable_http",
                   choices=["streamable_http", "sse"])
    args = p.parse_args()
    asyncio.run(probe(args.url, args.token, args.transport))


if __name__ == "__main__":
    main()
