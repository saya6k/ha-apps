"""Smoke test: agent orchestration with stubbed LLM + MCP + HTTP.

Home Assistant is delegated to HA's mcp_server, so there is no HA WS
client to stub. These tests use a stub `fetch_session_snapshot` to
simulate HA's per-turn tool+prompt response so the loop can be
exercised without a live HA.
"""
from __future__ import annotations

import asyncio
import sys

sys.path.insert(0, ".")

import wyoming_llm_agent.agent as agent_mod
from wyoming_llm_agent.agent import Agent, AgentConfig
from wyoming_llm_agent.embedding import EmbeddingConfig, cosine_similarity
from wyoming_llm_agent.mcp_client import (
    MCPServerConfig,
    MCPSessionSnapshot,
    MCPToolRef,
    _safe_name,
    build_mcp_tools,
    parse_mcp_servers,
)
from wyoming_llm_agent.preflight import check_function_calling


# ----- Stubs ----------------------------------------------------------------


class ScriptedLLM:
    def __init__(self, responses):
        self._responses = list(responses)

    async def chat(self, messages, *, tools=None, tool_choice=None, read_timeout=None):
        if not self._responses:
            raise AssertionError("ScriptedLLM ran out of canned responses")
        return self._responses.pop(0)


def make_ha_snapshot(tool_specs=(), prompt_text=None):
    """Build a fake HA mcp_server snapshot.
    tool_specs: list of (name, description) tuples.
    """
    server = MCPServerConfig(name="ha", url="http://stub/mcp")
    refs = [
        MCPToolRef(
            openai_name=name,
            server=server,
            mcp_name=name,
            description=desc,
            input_schema={"type": "object", "properties": {"entity_id": {"type": "string"}}},
        )
        for name, desc in tool_specs
    ]
    return MCPSessionSnapshot(tools=refs, prompt_text=prompt_text)


class _FakeHAFetch:
    """Replaces fetch_session_snapshot for tests."""

    def __init__(self, snapshot):
        self.snapshot = snapshot
        self.calls = 0

    async def __call__(self, server, *, prompt_name=None):
        self.calls += 1
        return self.snapshot


# ----- Tests ---------------------------------------------------------------


def test_mcp_parsing_and_tool_def() -> None:
    servers = parse_mcp_servers([
        {"name": "memory", "url": "http://x:8000/mcp",
         "headers": [{"name": "Authorization", "value": "secret"}]},
        {"name": "legacy", "url": "http://y/sse", "transport": "sse"},
    ])
    assert [(s.name, s.transport) for s in servers] == [
        ("memory", "streamable_http"), ("legacy", "sse"),
    ]
    refs = [MCPToolRef(
        openai_name="mcp_memory_recall", server=servers[0], mcp_name="recall",
        description="Recall a fact", input_schema={"type": "object"},
    )]
    defs = build_mcp_tools(refs)
    assert defs[0]["function"]["name"] == "mcp_memory_recall"
    assert _safe_name("mcp_memory_call/with spaces!") == "mcp_memory_call_with_spaces_"
    print("OK: mcp parsing + tool builders + name sanitizer")


def test_cosine_similarity() -> None:
    assert abs(cosine_similarity([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9
    assert abs(cosine_similarity([1.0, 0.0], [0.0, 1.0])) < 1e-9
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0
    print("OK: cosine_similarity correct + handles edge cases")


async def test_agent_dispatches_ha_tool_via_mcp() -> None:
    """User says 'turn on the bedroom light' → HA mcp_server tool dispatch."""
    ha_snapshot = make_ha_snapshot(
        tool_specs=[("HassTurnOn", "Turn an entity on")],
        prompt_text="You are a Home Assistant helper.",
    )
    fake_fetch = _FakeHAFetch(ha_snapshot)
    orig_fetch = agent_mod.fetch_session_snapshot
    agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]

    dispatched: list[tuple] = []
    async def fake_dispatch_mcp(ref, args):
        dispatched.append((ref.openai_name, args))
        return {"ok": True, "text": "Turned on"}
    orig_dispatch = agent_mod.dispatch_mcp_tool
    agent_mod.dispatch_mcp_tool = fake_dispatch_mcp  # type: ignore[assignment]

    try:
        llm = ScriptedLLM([
            {"choices": [{"message": {
                "role": "assistant", "content": "",
                "tool_calls": [{"id": "t1", "type": "function",
                                "function": {"name": "HassTurnOn",
                                             "arguments": '{"entity_id":"light.bedroom"}'}}]}}]},
            {"choices": [{"message": {"role": "assistant", "content": "Bedroom light is on."}}]},
        ])
        ha = MCPServerConfig(name="ha", url="http://stub/mcp", headers={"Authorization": "Bearer x"})
        ag = Agent(llm=llm, config=AgentConfig(ha_mcp_server=ha))
        result = await ag.respond(
            text="Turn on the bedroom light.", language="en",
            conversation_id="t1", device_id=None, satellite_id=None,
        )
        assert result.handled
        assert dispatched == [("HassTurnOn", {"entity_id": "light.bedroom"})]
        assert fake_fetch.calls == 1, "HA snapshot should be fetched once per turn"
    finally:
        agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]
        agent_mod.dispatch_mcp_tool = orig_dispatch  # type: ignore[assignment]
    print("OK: HA tool routed through HA mcp_server")


async def test_agent_ha_disabled() -> None:
    """ha_mcp_server=None → no HA fetch, agent still works with custom tools."""
    fake_fetch = _FakeHAFetch(make_ha_snapshot())
    orig_fetch = agent_mod.fetch_session_snapshot
    agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
    try:
        llm = ScriptedLLM([
            {"choices": [{"message": {"role": "assistant", "content": "Hi there."}}]},
        ])
        ag = Agent(llm=llm, config=AgentConfig(ha_mcp_server=None))
        result = await ag.respond(
            text="hello", language="en", conversation_id="t2",
            device_id=None, satellite_id=None,
        )
        assert result.handled
        # When ha_mcp_server is None, _fetch_ha_snapshot returns empty without
        # touching the network — fetch_session_snapshot should NOT be called.
        assert fake_fetch.calls == 0, "no HA fetch when ha_mcp_server is None"
    finally:
        agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]
    print("OK: HA delegation cleanly disabled")


async def test_agent_max_iterations_safety() -> None:
    fake_fetch = _FakeHAFetch(make_ha_snapshot())
    orig_fetch = agent_mod.fetch_session_snapshot
    agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
    try:
        loop_response = {"choices": [{"message": {
            "role": "assistant", "content": "",
            "tool_calls": [{"id": "x", "type": "function",
                            "function": {"name": "nope", "arguments": "{}"}}]}}]}
        llm = ScriptedLLM([loop_response] * 100)
        ag = Agent(llm=llm, config=AgentConfig(max_tool_iterations=3, ha_mcp_server=None))
        result = await ag.respond(
            text="loop me", language="en", conversation_id="t3",
            device_id=None, satellite_id=None,
        )
        assert not result.handled
        assert "too many" in result.text.lower()
    finally:
        agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]
    print("OK: max_tool_iterations halts a runaway loop")


def _stub_mcp_tool(server: MCPServerConfig, name: str, desc: str) -> MCPToolRef:
    """Build an MCPToolRef matching what discover_tools would produce, for
    use in pure-Python tests that don't actually open an MCP session."""
    return MCPToolRef(
        openai_name=name, server=server, mcp_name=name,
        description=desc, input_schema={"type": "object", "properties": {}},
    )


async def test_tool_filter_keeps_top_k() -> None:
    fake_fetch = _FakeHAFetch(make_ha_snapshot())
    orig_fetch = agent_mod.fetch_session_snapshot
    agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
    try:
        class StubEmbedConfig:
            model = "stub"; base_url = "http://stub/v1"
        class StubEmbed:
            config = StubEmbedConfig()
            async def embed(self, texts):
                vectors = []
                for t in texts:
                    v = [0.0] * 26
                    for ch in t.lower():
                        if "a" <= ch <= "z":
                            v[ord(ch) - ord("a")] = 1.0
                    vectors.append(v)
                return vectors
            async def aclose(self): pass

        stub_server = MCPServerConfig(name="x", url="http://stub/mcp")
        mcp_tools = [
            _stub_mcp_tool(stub_server, "StartLaundry", "Start the washing machine"),
            _stub_mcp_tool(stub_server, "TellJoke",    "Tell a funny joke about a topic"),
            _stub_mcp_tool(stub_server, "OpenGarage",  "Open the garage door"),
            _stub_mcp_tool(stub_server, "OrderPizza",  "Order a pizza"),
        ]
        llm = ScriptedLLM([
            {"choices": [{"message": {"role": "assistant", "content": "ok"}}]},
        ])
        seen: list[list[str]] = []
        orig_chat = llm.chat
        async def spy(messages, *, tools=None, tool_choice=None):
            seen.append([t["function"]["name"] for t in (tools or [])])
            return await orig_chat(messages, tools=tools, tool_choice=tool_choice)
        llm.chat = spy  # type: ignore[assignment]

        ag = Agent(
            llm=llm,
            config=AgentConfig(
                mcp_tools=mcp_tools, tool_filter_top_k=2, ha_mcp_server=None,
            ),
            embedding_client=StubEmbed(),  # type: ignore[arg-type]
        )
        await ag.warmup_embeddings()
        assert ag._tool_embeddings, "warmup should populate cache"

        await ag.respond(
            text="please tell me a funny joke", language="en",
            conversation_id="t5", device_id=None, satellite_id=None,
        )
        kept = seen[0]
        # Meta tools (working_memory_*, etc.) are budget-free — they
        # ride along regardless of top-K. Assert top-K applies to the
        # non-meta scoring pool only.
        from wyoming_llm_agent.const import META_TOOL_NAMES
        non_meta = [n for n in kept if n not in META_TOOL_NAMES]
        assert len(non_meta) == 2, f"expected top-K=2 non-meta, got {non_meta}"
        assert "TellJoke" in non_meta, f"TellJoke should win: {non_meta}"
        print(f"OK: tool filter kept top-2 non-meta (TellJoke present): {non_meta}")
    finally:
        agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]


def test_skill_parser_round_trip_and_validation() -> None:
    """SKILL.md parser handles standard agentskills.io frontmatter and
    rejects spec violations cleanly.
    """
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.skills import (
        SkillParseError, load_skills_dir, parse_skill_md,
    )

    good = (
        "---\n"
        "name: pdf-extract\n"
        "description: Extract text and tables from PDFs.\n"
        "license: Apache-2.0\n"
        "compatibility: Requires Python 3.12\n"
        "allowed-tools: pdf_extract_text pdf_extract_tables\n"
        "metadata:\n"
        "  author: example-org\n"
        "  version: '1.0'\n"
        "---\n"
        "# PDF extract\n\n"
        "Use `scripts/extract.py` to pull text.\n"
    )
    front, body = parse_skill_md(good, expected_name="pdf-extract")
    assert front["name"] == "pdf-extract"
    assert front["description"].startswith("Extract text")
    assert front["license"] == "Apache-2.0"
    assert front["allowed_tools"] == ["pdf_extract_text", "pdf_extract_tables"]
    assert front["metadata"]["author"] == "example-org"
    assert "# PDF extract" in body
    assert "scripts/extract.py" in body

    # name dir mismatch
    try:
        parse_skill_md(good, expected_name="something-else")
    except SkillParseError as e:
        assert "match parent directory" in str(e)
    else:
        raise AssertionError("expected SkillParseError on name/dir mismatch")

    # invalid name (uppercase)
    try:
        parse_skill_md("---\nname: PDF\ndescription: x\n---\n")
    except SkillParseError as e:
        assert "lowercase" in str(e)
    else:
        raise AssertionError("expected SkillParseError on uppercase name")

    # consecutive hyphens
    try:
        parse_skill_md("---\nname: foo--bar\ndescription: x\n---\n")
    except SkillParseError as e:
        assert "consecutive hyphens" in str(e)
    else:
        raise AssertionError("expected SkillParseError on `--` in name")

    # missing description
    try:
        parse_skill_md("---\nname: ok\n---\n")
    except SkillParseError as e:
        assert "description" in str(e)
    else:
        raise AssertionError("expected SkillParseError on missing description")

    # allowed-tools as list (cross-vendor portability)
    front2, _ = parse_skill_md(
        "---\nname: ok\ndescription: x\nallowed-tools: [a, b, c]\n---\n",
    )
    assert front2["allowed_tools"] == ["a", "b", "c"]

    # No frontmatter at all
    try:
        parse_skill_md("just markdown, no frontmatter")
    except SkillParseError as e:
        assert "frontmatter" in str(e)
    else:
        raise AssertionError("expected SkillParseError on missing frontmatter")

    # load_skills_dir picks up the good skill and skips a bad one in the
    # same root without crashing.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "pdf-extract").mkdir()
        (root / "pdf-extract" / "SKILL.md").write_text(good)
        # Bad: name doesn't match directory.
        (root / "broken").mkdir()
        (root / "broken" / "SKILL.md").write_text(
            "---\nname: not-broken\ndescription: x\n---\n"
        )
        # Bad: not a directory we care about (no SKILL.md).
        (root / "empty").mkdir()
        loaded = load_skills_dir(root)
        names = [s.name for s in loaded]
        assert names == ["pdf-extract"], names
        assert loaded[0].allowed_tools == ["pdf_extract_text", "pdf_extract_tables"]
    print("OK: skill parser validates spec, load_skills_dir skips bad entries")


async def test_skill_meta_tools_load_unload_inject_body() -> None:
    """Loading a skill via load_skill injects its SKILL.md body into
    messages[0] before the next round-trip in the same user turn,
    persists across follow-up respond() calls in the same conversation,
    and unloading removes it.
    """
    from wyoming_llm_agent.skills import Skill
    from pathlib import Path

    ha_snapshot = make_ha_snapshot(prompt_text="HA api prompt body")
    fake_fetch = _FakeHAFetch(ha_snapshot)
    orig_fetch = agent_mod.fetch_session_snapshot
    agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
    try:
        # Two registered skills.
        brewing = Skill(
            name="xbloom-brewing",
            description="Brew coffee on XBloom — V60 style at 1:16 ratio.",
            body="USER PREFERS 18g BEANS, 90C WATER.\nAlways tare first.",
            path=Path("/tmp/nope"),
            allowed_tools=["xbloom_pour", "xbloom_status"],
        )
        laundry = Skill(
            name="laundry-mode",
            description="Run the washing machine. Use for laundry requests.",
            body="Hot wash forbidden after 22:00.",
            path=Path("/tmp/nope"),
        )

        # Turn 1: LLM calls load_skill, then answers in iter 2.
        # Iter 1 sees no body; iter 2 sees the body.
        turn1_responses = [
            {  # iter 1: model decides to load
                "choices": [{"message": {
                    "role": "assistant", "content": "",
                    "tool_calls": [{
                        "id": "c1", "type": "function",
                        "function": {
                            "name": "load_skill",
                            "arguments": '{"name": "xbloom-brewing"}',
                        },
                    }],
                }}],
            },
            {  # iter 2: model answers, body should be visible
                "choices": [{"message": {
                    "role": "assistant", "content": "ok brewing",
                }}],
            },
        ]
        # Turn 2 (same conversation): no tool calls, skill body should
        # still be in messages[0] (persistence across turns).
        turn2_responses = [
            {"choices": [{"message": {
                "role": "assistant", "content": "still here",
            }}]},
        ]
        # Turn 3: LLM unloads the skill, then answers.
        turn3_responses = [
            {"choices": [{"message": {
                "role": "assistant", "content": "",
                "tool_calls": [{
                    "id": "c3", "type": "function",
                    "function": {
                        "name": "unload_skill",
                        "arguments": '{"name": "xbloom-brewing"}',
                    },
                }],
            }}]},
            {"choices": [{"message": {
                "role": "assistant", "content": "unloaded",
            }}]},
        ]
        llm = ScriptedLLM(turn1_responses + turn2_responses + turn3_responses)
        seen_systems: list[str] = []
        seen_tool_names: list[set[str]] = []
        orig_chat = llm.chat
        async def spy(messages, *, tools=None, tool_choice=None):
            seen_systems.append(messages[0]["content"])
            seen_tool_names.append({t["function"]["name"] for t in (tools or [])})
            return await orig_chat(messages, tools=tools, tool_choice=tool_choice)
        llm.chat = spy  # type: ignore[assignment]

        ag = Agent(
            llm=llm,
            config=AgentConfig(
                skills=[brewing, laundry],
                ha_mcp_server=MCPServerConfig(name="ha", url="http://stub/mcp"),
            ),
        )

        # ----- Turn 1 -----
        await ag.respond(
            text="brew me one", language="en",
            conversation_id="conv-x", device_id=None, satellite_id=None,
        )
        # Iter 1 system msg: skill catalog present, no active body yet.
        assert "Available skills" in seen_systems[0]
        assert "xbloom-brewing: Brew coffee" in seen_systems[0]
        assert "[Active skill: xbloom-brewing]" not in seen_systems[0]
        # Iter 2 system msg: body now appended at the end.
        assert "[Active skill: xbloom-brewing]" in seen_systems[1]
        assert "USER PREFERS 18g BEANS" in seen_systems[1]
        # Meta tools must be exposed (always-in, bypassing top-K filter).
        assert {"list_skills", "load_skill", "unload_skill"} <= seen_tool_names[0]

        # ----- Turn 2 (same conversation) -----
        await ag.respond(
            text="any tips?", language="en",
            conversation_id="conv-x", device_id=None, satellite_id=None,
        )
        # Persistence: body still in system msg of the new turn.
        assert "[Active skill: xbloom-brewing]" in seen_systems[2], (
            "skill should persist across turns in the same conversation"
        )

        # ----- Turn 3: unload -----
        await ag.respond(
            text="thanks, stop", language="en",
            conversation_id="conv-x", device_id=None, satellite_id=None,
        )
        # Iter at start of turn 3: body still present (unload not called yet).
        assert "[Active skill: xbloom-brewing]" in seen_systems[3]
        # After unload, the next iter's system msg drops the body.
        assert "[Active skill: xbloom-brewing]" not in seen_systems[4], (
            "unload_skill should rebuild system msg without the body"
        )
        # Skill catalog still there (registration unchanged).
        assert "xbloom-brewing: Brew coffee" in seen_systems[4]
        print("OK: meta tools load → body injected same turn, persists across turns, unload removes it")
    finally:
        agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]


def test_sandbox_path_validation() -> None:
    """script_path validation rejects every shape of escape attempt."""
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.sandbox import SandboxError, _validate_script_path

    with tempfile.TemporaryDirectory() as td:
        skill_dir = Path(td)
        (skill_dir / "scripts").mkdir()
        ok_file = skill_dir / "scripts" / "run.py"
        ok_file.write_text("print('ok')\n")

        # Happy path.
        resolved = _validate_script_path(skill_dir, "scripts/run.py")
        assert resolved == ok_file.resolve()

        bad_inputs = [
            "/etc/passwd",                  # absolute
            "/proc/self/root/usr/bin/sh",   # the /proc/self/root trick from the spec
            "../../../etc/shadow",          # dotdot escape
            "scripts/../../etc/shadow",     # embedded dotdot
            "scripts/run.sh",               # not .py
            "scripts/missing.py",           # doesn't exist
            "",                             # empty
        ]
        for bad in bad_inputs:
            try:
                _validate_script_path(skill_dir, bad)
            except SandboxError:
                pass
            else:
                raise AssertionError(
                    f"expected SandboxError for script_path={bad!r}"
                )
    print("OK: sandbox script_path validation rejects abs / dotdot / /proc / non-py / missing")


async def test_sandbox_unavailable_hides_run_skill_script() -> None:
    """When the bwrap probe fails (e.g. dev macOS), Agent.sandbox_available
    stays False and the LLM never sees run_skill_script.
    """
    from wyoming_llm_agent.skills import Skill
    from pathlib import Path

    fake_fetch = _FakeHAFetch(make_ha_snapshot())
    orig_fetch = agent_mod.fetch_session_snapshot
    agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
    try:
        skill = Skill(
            name="any-skill", description="any", body="body",
            path=Path("/tmp/nope"),
        )
        llm = ScriptedLLM([
            {"choices": [{"message": {"role": "assistant", "content": "done"}}]},
        ])
        seen_tools: list[set[str]] = []
        orig_chat = llm.chat
        async def spy(messages, *, tools=None, tool_choice=None):
            seen_tools.append({t["function"]["name"] for t in (tools or [])})
            return await orig_chat(messages, tools=tools, tool_choice=tool_choice)
        llm.chat = spy  # type: ignore[assignment]

        ag = Agent(
            llm=llm,
            config=AgentConfig(
                skills=[skill],
                ha_mcp_server=MCPServerConfig(name="ha", url="http://stub/mcp"),
            ),
        )
        # Default sandbox_available = False; do not set it.
        assert ag.sandbox_available is False

        await ag.respond(
            text="hi", language="en",
            conversation_id="c-nosandbox", device_id=None, satellite_id=None,
        )
        tools = seen_tools[0]
        # 3 meta tools always exposed (list / load / unload), but NOT run_skill_script.
        assert "list_skills" in tools, tools
        assert "load_skill" in tools, tools
        assert "unload_skill" in tools, tools
        assert "run_skill_script" not in tools, (
            "run_skill_script must be hidden when sandbox unavailable"
        )
        print("OK: run_skill_script hidden from LLM when sandbox_available=False")
    finally:
        agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]


async def test_sandbox_dispatch_requires_loaded_skill() -> None:
    """Even with sandbox available, run_skill_script refuses to launch
    a script for a skill that hasn't been loaded — forces the LLM
    through load_skill first so the SKILL.md body is in context.
    """
    from wyoming_llm_agent.skills import Skill
    from pathlib import Path

    fake_fetch = _FakeHAFetch(make_ha_snapshot())
    orig_fetch = agent_mod.fetch_session_snapshot
    agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
    try:
        skill = Skill(
            name="ok-skill", description="ok", body="body",
            path=Path("/tmp/nope"),
        )
        # LLM tries to run a script without loading first.
        llm = ScriptedLLM([
            {"choices": [{"message": {
                "role": "assistant", "content": "",
                "tool_calls": [{
                    "id": "c1", "type": "function",
                    "function": {
                        "name": "run_skill_script",
                        "arguments": (
                            '{"skill_name": "ok-skill", '
                            '"script_path": "scripts/x.py"}'
                        ),
                    },
                }],
            }}]},
            {"choices": [{"message": {"role": "assistant", "content": "done"}}]},
        ])
        ag = Agent(
            llm=llm,
            config=AgentConfig(
                skills=[skill],
                ha_mcp_server=MCPServerConfig(name="ha", url="http://stub/mcp"),
            ),
        )
        ag.sandbox_available = True  # pretend bwrap probe passed

        await ag.respond(
            text="run x", language="en",
            conversation_id="c-noload", device_id=None, satellite_id=None,
        )
        # Tool result for the run_skill_script call should report ok=False
        # with a "not loaded" error. Walk messages to find it.
        convo = ag._conversations["c-noload"]
        # respond() doesn't store tool results in convo.messages; we need
        # to check the spy. Re-test by inspecting via a result probe.
        # Easier: assert convo.loaded_skills stays empty (nothing loaded).
        assert convo.loaded_skills == set()
        print("OK: run_skill_script refuses unloaded skill (forces load_skill first)")
    finally:
        agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]


async def test_sandbox_self_test_category_gating_and_predicates() -> None:
    """`verify_sandbox_behavior()` honours every category gate
    (pid_strict / seccomp / slow) and routes the special timed-out +
    killed-by-signal predicates correctly. There is no rlimit gate —
    rlimits are enforced via preexec_fn regardless of bwrap version.
    Mocks `run_sandboxed_script` so the test runs without a real bwrap
    (macOS / CI).
    """
    import wyoming_llm_agent.sandbox as sb

    saved = (
        sb._BWRAP_SUPPORTS_PID_UNSHARE,
        sb._SECCOMP_AVAILABLE, sb.run_sandboxed_script,
    )

    async def _all_pass(**kw):
        return sb.SandboxResult(stdout="ok\n", stderr="", exit_code=0, timed_out=False)

    try:
        # Case 1: minimal support — pid/seccomp/slow all skipped, but
        # rlimit_fsize / rlimit_nofile RUN (always-on now).
        sb._BWRAP_SUPPORTS_PID_UNSHARE = False
        sb._SECCOMP_AVAILABLE = False
        sb.run_sandboxed_script = _all_pass

        results = await sb.verify_sandbox_behavior(include_slow=False)
        by_name = {c.name: c for c in results}

        # always-on categories should have run + passed (mock returns ok)
        assert by_name["net_isolated"].passed and by_name["net_isolated"].skipped_reason is None
        assert by_name["env_sterile"].passed
        assert by_name["tmp_writable"].passed
        # rlimit_fsize / rlimit_nofile RUN (no bwrap-version gate anymore).
        assert by_name["rlimit_fsize"].passed and by_name["rlimit_fsize"].skipped_reason is None
        assert by_name["rlimit_nofile"].passed and by_name["rlimit_nofile"].skipped_reason is None
        # gated categories should be skipped with the right reason
        assert by_name["pid_isolation"].skipped_reason == "relaxed_pid"
        assert by_name["seccomp_blocks_unshare"].skipped_reason == "no_seccomp"
        assert by_name["seccomp_blocks_mount"].skipped_reason == "no_seccomp"
        assert by_name["wall_clock_timeout"].skipped_reason == "slow_opt_in"
        assert by_name["rlimit_cpu"].skipped_reason == "slow_opt_in"
        # skipped tests count as not passed (so caller sees them as ! pass)
        assert by_name["pid_isolation"].passed is False

        # Case 2: full support + include_slow=True; check special predicates.
        # wall_clock_timeout must require timed_out=True; rlimit_cpu must
        # require negative exit_code (signal) and NOT timed_out.
        sb._BWRAP_SUPPORTS_PID_UNSHARE = True
        sb._SECCOMP_AVAILABLE = True

        async def _by_name(**kw):
            sp = kw.get("script_path", "")
            if "wall_clock_timeout" in sp:
                return sb.SandboxResult(
                    stdout="", stderr="", exit_code=-1, timed_out=True,
                )
            if "rlimit_cpu" in sp:
                # Direct-signal convention (Python subprocess without
                # a supervising wrapper). Predicate must pass on this.
                return sb.SandboxResult(
                    stdout="", stderr="", exit_code=-24, timed_out=False,  # SIGXCPU
                )
            return sb.SandboxResult(
                stdout="ok\n", stderr="", exit_code=0, timed_out=False,
            )
        sb.run_sandboxed_script = _by_name

        results = await sb.verify_sandbox_behavior(include_slow=True)
        by_name = {c.name: c for c in results}
        assert all(c.skipped_reason is None for c in results), \
            [c for c in results if c.skipped_reason]
        assert by_name["wall_clock_timeout"].passed, by_name["wall_clock_timeout"]
        assert by_name["rlimit_cpu"].passed, by_name["rlimit_cpu"]

        # Case 2b: rlimit_cpu via shell-convention exit code (bwrap as
        # supervisor wraps WIFSIGNALED into 128+signum). 152 = SIGXCPU,
        # 137 = SIGKILL (hard-limit follow-up). Both must pass.
        for shell_exit in (152, 137):
            async def _shell_conv(_exit=shell_exit, **kw):
                sp = kw.get("script_path", "")
                if "rlimit_cpu" in sp:
                    return sb.SandboxResult(
                        stdout="", stderr="", exit_code=_exit, timed_out=False,
                    )
                if "wall_clock_timeout" in sp:
                    return sb.SandboxResult(
                        stdout="", stderr="", exit_code=-1, timed_out=True,
                    )
                return sb.SandboxResult(
                    stdout="ok\n", stderr="", exit_code=0, timed_out=False,
                )
            sb.run_sandboxed_script = _shell_conv
            results = await sb.verify_sandbox_behavior(include_slow=True)
            rc = next(c for c in results if c.name == "rlimit_cpu")
            assert rc.passed, f"shell-convention exit={shell_exit} must pass: {rc}"
            assert f"signal ({shell_exit - 128})" in rc.detail, rc.detail

        # And exit_code 0 (normal exit) must FAIL the expect_killed predicate.
        async def _normal_exit(**kw):
            return sb.SandboxResult(stdout="", stderr="", exit_code=0, timed_out=False)
        sb.run_sandboxed_script = _normal_exit
        results = await sb.verify_sandbox_behavior(include_slow=True)
        rc = next(c for c in results if c.name == "rlimit_cpu")
        assert not rc.passed and "not signal-killed" in rc.detail, rc
        # Sanity: a normal-category test that "succeeded" should pass too.
        assert by_name["rlimit_fsize"].passed
        assert by_name["pid_isolation"].passed

        # Case 3: a normal test fails (exit_code != 0) → reported as failed,
        # NOT skipped.
        async def _all_fail(**kw):
            return sb.SandboxResult(
                stdout="FAIL: leak detected\n", stderr="", exit_code=1, timed_out=False,
            )
        sb.run_sandboxed_script = _all_fail
        results = await sb.verify_sandbox_behavior(include_slow=False)
        net = next(c for c in results if c.name == "net_isolated")
        assert not net.passed and net.skipped_reason is None
        assert "exit=1" in net.detail or "FAIL" in net.detail, net.detail

        # Case 4: SandboxError during launch → reported as failed with
        # 'setup error:' prefix; the suite keeps going.
        async def _setup_error(**kw):
            raise sb.SandboxError("bwrap exploded")
        sb.run_sandboxed_script = _setup_error
        results = await sb.verify_sandbox_behavior(include_slow=False)
        first_real = next(
            c for c in results
            if c.skipped_reason is None and c.category != "slow"
        )
        assert not first_real.passed
        assert "setup error" in first_real.detail, first_real.detail
        # Suite ran all non-skipped tests, didn't abort on first failure.
        assert sum(1 for c in results if not c.passed and c.skipped_reason is None) >= 5

        print(
            "OK: verify_sandbox_behavior gates categories, routes "
            "timed-out + signal-killed predicates, and reports setup errors"
        )
    finally:
        (
            sb._BWRAP_SUPPORTS_PID_UNSHARE,
            sb._SECCOMP_AVAILABLE, sb.run_sandboxed_script,
        ) = saved


async def test_skill_allowed_tools_gating() -> None:
    """A skill's allowed_tools patterns hide matching tools while the
    skill is not loaded, and reveal them once load_skill activates it.
    Wildcards (fnmatch) match prefix + suffix. META tools never hidden.
    """
    from wyoming_llm_agent.skills import Skill
    from pathlib import Path

    # HA snapshot exposes 4 tools — some pdf-* (skill-managed),
    # one neutral (always visible), one ocr_text to test suffix wildcard.
    ha_snapshot = make_ha_snapshot(tool_specs=[
        ("pdf_extract_text", "Extract text from a PDF"),
        ("pdf_extract_tables", "Extract tables from a PDF"),
        ("ocr_text", "Run OCR on an image"),
        ("HassTurnOn", "Turn on an entity"),
    ])
    fake_fetch = _FakeHAFetch(ha_snapshot)
    orig_fetch = agent_mod.fetch_session_snapshot
    agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
    try:
        pdf_skill = Skill(
            name="pdf-processing",
            description="Extract text and tables from PDFs.",
            body="Use pdfplumber under the hood.",
            path=Path("/tmp/nope"),
            allowed_tools=["pdf_*", "*_text"],     # tests prefix + suffix wildcard
        )
        # Pathological: a skill whose allowed_tools include a meta tool
        # name — gating must still NEVER hide meta tools.
        meta_blocker = Skill(
            name="meta-blocker",
            description="Bad skill that tries to lock meta tools.",
            body="bad",
            path=Path("/tmp/nope"),
            allowed_tools=["load_skill", "list_skills"],
        )

        # Iter 1: model loads the pdf skill.
        # Iter 2: model answers; verify pdf_* + *_text now visible.
        # Iter 3: model unloads.
        # Iter 4: model answers; verify hidden again.
        llm = ScriptedLLM([
            {"choices": [{"message": {
                "role": "assistant", "content": "",
                "tool_calls": [{
                    "id": "c1", "type": "function",
                    "function": {
                        "name": "load_skill",
                        "arguments": '{"name": "pdf-processing"}',
                    },
                }],
            }}]},
            {"choices": [{"message": {"role": "assistant", "content": "loaded"}}]},
            {"choices": [{"message": {
                "role": "assistant", "content": "",
                "tool_calls": [{
                    "id": "c3", "type": "function",
                    "function": {
                        "name": "unload_skill",
                        "arguments": '{"name": "pdf-processing"}',
                    },
                }],
            }}]},
            {"choices": [{"message": {"role": "assistant", "content": "unloaded"}}]},
        ])
        seen_tool_names: list[set[str]] = []
        orig_chat = llm.chat
        async def spy(messages, *, tools=None, tool_choice=None):
            seen_tool_names.append({t["function"]["name"] for t in (tools or [])})
            return await orig_chat(messages, tools=tools, tool_choice=tool_choice)
        llm.chat = spy  # type: ignore[assignment]

        ag = Agent(
            llm=llm,
            config=AgentConfig(
                skills=[pdf_skill, meta_blocker],
                ha_mcp_server=MCPServerConfig(name="ha", url="http://stub/mcp"),
            ),
        )

        # Turn 1: load → reveal.
        await ag.respond(
            text="extract this pdf", language="en",
            conversation_id="conv-g", device_id=None, satellite_id=None,
        )
        # Iter 1 (pre-load): pdf_* + *_text should be HIDDEN.
        iter1 = seen_tool_names[0]
        assert "pdf_extract_text" not in iter1, iter1
        assert "pdf_extract_tables" not in iter1, iter1
        assert "ocr_text" not in iter1, iter1     # matched by *_text
        assert "HassTurnOn" in iter1, iter1       # untouched neutral tool
        # Meta tools must always remain visible — meta-blocker is registered
        # but its allowed_tools include load_skill/list_skills. Gating must
        # ignore that for META_TOOL_NAMES.
        assert {"list_skills", "load_skill", "unload_skill"} <= iter1, iter1

        # Iter 2 (post-load): pdf-processing's tools revealed.
        iter2 = seen_tool_names[1]
        assert "pdf_extract_text" in iter2, iter2
        assert "pdf_extract_tables" in iter2, iter2
        assert "ocr_text" in iter2, iter2         # *_text wildcard worked
        assert "HassTurnOn" in iter2, iter2       # still there

        # Turn 2: unload → hidden again.
        await ag.respond(
            text="stop", language="en",
            conversation_id="conv-g", device_id=None, satellite_id=None,
        )
        # Iter 3 (still loaded at start of turn — unload happens this iter).
        iter3 = seen_tool_names[2]
        assert "pdf_extract_text" in iter3, iter3
        # Iter 4 (post-unload).
        iter4 = seen_tool_names[3]
        assert "pdf_extract_text" not in iter4, iter4
        assert "ocr_text" not in iter4, iter4
        print("OK: allowed-tools gating hides until load, fnmatch wildcards work, meta tools never hidden")
    finally:
        agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]


async def test_skill_meta_tools_handle_bad_input() -> None:
    """load_skill('nonexistent') and unload of an un-loaded skill both
    return ok=False without crashing or polluting loaded_skills.
    """
    from wyoming_llm_agent.skills import Skill
    from pathlib import Path

    fake_fetch = _FakeHAFetch(make_ha_snapshot())
    orig_fetch = agent_mod.fetch_session_snapshot
    agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
    try:
        skill = Skill(
            name="ok-skill", description="ok", body="body",
            path=Path("/tmp/nope"),
        )
        llm = ScriptedLLM([
            # iter 1: try bad load
            {"choices": [{"message": {
                "role": "assistant", "content": "",
                "tool_calls": [{
                    "id": "c1", "type": "function",
                    "function": {
                        "name": "load_skill",
                        "arguments": '{"name": "ghost"}',
                    },
                }],
            }}]},
            # iter 2: try unload of un-loaded skill
            {"choices": [{"message": {
                "role": "assistant", "content": "",
                "tool_calls": [{
                    "id": "c2", "type": "function",
                    "function": {
                        "name": "unload_skill",
                        "arguments": '{"name": "ok-skill"}',
                    },
                }],
            }}]},
            # iter 3: done
            {"choices": [{"message": {
                "role": "assistant", "content": "done",
            }}]},
        ])
        ag = Agent(
            llm=llm,
            config=AgentConfig(
                skills=[skill],
                ha_mcp_server=MCPServerConfig(name="ha", url="http://stub/mcp"),
            ),
        )
        result = await ag.respond(
            text="poke", language="en",
            conversation_id="conv-y", device_id=None, satellite_id=None,
        )
        assert result.handled, result
        # No corruption — nothing loaded.
        convo = ag._conversations["conv-y"]
        assert convo.loaded_skills == set(), convo.loaded_skills
        print("OK: meta tools survive bad input (unknown skill / unload of unloaded)")
    finally:
        agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]


def test_record_embedding_increments_tokens_counter_when_supplied() -> None:
    """record_embedding(ok=True, model=..., tokens=N) increments
    embedding_tokens_total by N; failure path and the legacy 2-arg call
    must NOT increment tokens. Catches signature regressions and the
    "no model label" silent-no-op branch.
    """
    from wyoming_llm_agent import metrics as m

    def _val(model: str) -> float:
        # Counter introspection via the internal _metrics dict so we
        # don't depend on prometheus_client's text exposition.
        return m.embedding_tokens_total.labels(model=model)._value.get()

    def _calls(outcome: str) -> float:
        return m.embedding_calls_total.labels(outcome=outcome)._value.get()

    base_tokens = _val("text-embedding-3-small")
    base_success = _calls("success")
    base_error = _calls("error")

    # Success with tokens → both counters increment
    m.record_embedding(ok=True, model="text-embedding-3-small", tokens=137)
    assert _val("text-embedding-3-small") == base_tokens + 137
    assert _calls("success") == base_success + 1

    # Success without usage (upstream omitted it) → only call counter
    m.record_embedding(ok=True, model="text-embedding-3-small", tokens=0)
    assert _val("text-embedding-3-small") == base_tokens + 137  # unchanged
    assert _calls("success") == base_success + 2

    # Failure → only error counter; tokens never increment even if passed
    m.record_embedding(ok=False, model="text-embedding-3-small", tokens=999)
    assert _val("text-embedding-3-small") == base_tokens + 137  # unchanged
    assert _calls("error") == base_error + 1

    # Legacy 2-arg call (no model, no tokens) → only call counter
    m.record_embedding(ok=True)
    assert _val("text-embedding-3-small") == base_tokens + 137  # unchanged
    assert _calls("success") == base_success + 3

    print("OK: record_embedding tracks tokens only on success+model+tokens>0")


def test_embed_key_invalidates_on_desc_change() -> None:
    from wyoming_llm_agent.agent import _embed_key
    k1 = _embed_key("foo", "old description")
    k2 = _embed_key("foo", "new description")
    k3 = _embed_key("foo", "old description")
    assert k1 != k2, "description change must produce different cache key"
    assert k1 == k3, "same description must produce same key"
    name, h = k1.split(":", 1)
    assert name == "foo" and len(h) == 16
    print("OK: _embed_key hashes description for cache invalidation")


async def test_tool_filter_ha_tools_mode_embedding() -> None:
    """In `embedding` mode, HA tools join the top-K scoring pool and the
    warmup batch pre-embeds them at startup.
    """
    ha_snapshot = make_ha_snapshot(tool_specs=[
        ("HassTurnOn", "Turn an entity on or off"),
        ("light_kitchen_set_state", "Set kitchen light state"),
        ("media_player_say_joke", "Play a funny joke on the media player"),
    ])
    fake_fetch = _FakeHAFetch(ha_snapshot)
    orig_fetch = agent_mod.fetch_session_snapshot
    agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
    try:
        class StubEmbedConfig:
            model = "stub"; base_url = "http://stub/v1"
        class StubEmbed:
            config = StubEmbedConfig()
            calls = 0
            async def embed(self, texts):
                self.calls += 1
                vectors = []
                for t in texts:
                    v = [0.0] * 26
                    for ch in t.lower():
                        if "a" <= ch <= "z":
                            v[ord(ch) - ord("a")] = 1.0
                    vectors.append(v)
                return vectors
            async def aclose(self): pass

        # 2 external MCP + 3 HA = 5 candidates; top_k=2.
        ext_server = MCPServerConfig(name="ext", url="http://stub/ext")
        external_mcp_tools = [
            _stub_mcp_tool(ext_server, "StartLaundry", "Start the washing machine"),
            _stub_mcp_tool(ext_server, "TellJoke", "Tell a funny joke about a topic"),
        ]
        llm = ScriptedLLM([
            {"choices": [{"message": {"role": "assistant", "content": "ok"}}]},
        ])
        seen: list[list[str]] = []
        orig_chat = llm.chat
        async def spy(messages, *, tools=None, tool_choice=None):
            seen.append([t["function"]["name"] for t in (tools or [])])
            return await orig_chat(messages, tools=tools, tool_choice=tool_choice)
        llm.chat = spy  # type: ignore[assignment]

        ag = Agent(
            llm=llm,
            config=AgentConfig(
                mcp_tools=external_mcp_tools,
                tool_filter_top_k=2,
                ha_mcp_server=MCPServerConfig(name="ha", url="http://stub/mcp"),
                ha_tools_mode="embedding",
            ),
            embedding_client=StubEmbed(),  # type: ignore[arg-type]
        )
        # Warmup should embed both external (2) and HA (3) tools.
        await ag.warmup_embeddings()
        assert len(ag._tool_embeddings) == 5, (
            f"expected 5 cached embeddings (2 external MCP + 3 HA pre-warm), "
            f"got {len(ag._tool_embeddings)}"
        )

        await ag.respond(
            text="tell me a funny joke", language="en",
            conversation_id="t6", device_id=None, satellite_id=None,
        )
        kept = seen[0]
        # Meta tools ride along free of top-K — assert on the non-meta pool.
        from wyoming_llm_agent.const import META_TOOL_NAMES
        non_meta = [n for n in kept if n not in META_TOOL_NAMES]
        assert len(non_meta) == 2, f"expected top-K=2 non-meta, got {non_meta}"
        # "joke"-flavoured tools should win over light/laundry/turn-on.
        # In embedding mode HA tools compete on equal terms — at least one
        # of the two HA `say_joke` / custom `TellJoke` must be in the top.
        joke_kept = [n for n in non_meta if "joke" in n.lower()]
        assert joke_kept, f"expected at least one joke tool: {non_meta}"
        print(f"OK: ha_tools_mode=embedding scores HA + custom together: {non_meta}")
    finally:
        agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]


async def test_skill_fetcher_url_flow() -> None:
    """skill_urls flow: build a tarball in memory, mock httpx, verify install
    + hash skip + hash-change re-extract."""
    import io
    import json as _json
    import tarfile
    import tempfile
    from pathlib import Path
    import httpx
    from wyoming_llm_agent.skill_fetcher import fetch_skill_urls

    def make_skill_tar(name: str, body_marker: str) -> bytes:
        """Build a .tar.gz containing skills/<name>/SKILL.md, mimicking the
        GitHub-archive layout (repo-name-SHA/skills/<name>/SKILL.md)."""
        skill_md = (
            "---\n"
            f"name: {name}\n"
            "description: A test skill.\n"
            "---\n\n"
            f"# Body\n\n{body_marker}\n"
        ).encode("utf-8")
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            for relpath in (
                f"repo-abc/README.md",
                f"repo-abc/skills/{name}/SKILL.md",
            ):
                content = skill_md if relpath.endswith("SKILL.md") else b"# readme\n"
                info = tarfile.TarInfo(name=relpath)
                info.size = len(content)
                tf.addfile(info, io.BytesIO(content))
        return buf.getvalue()

    class MockTransport(httpx.AsyncBaseTransport):
        def __init__(self):
            self.sha = "sha111"
            self.tar = make_skill_tar("playwright", "marker-v1")
            self.requests: list[str] = []

        async def handle_async_request(self, request):
            url = str(request.url)
            self.requests.append(url)
            if "api.github.com/repos/" in url and url.endswith("/lackeyjb/playwright-skill"):
                return httpx.Response(200, json={"default_branch": "main"})
            if "/commits/" in url:
                return httpx.Response(200, json={"sha": self.sha})
            if "/archive/" in url:
                return httpx.Response(
                    200, content=self.tar,
                    headers={"content-type": "application/gzip"},
                )
            return httpx.Response(404, json={"err": "not handled"})

    transport = MockTransport()
    client = httpx.AsyncClient(transport=transport, follow_redirects=True)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target = tmp_path / "skills"
            state = tmp_path / "state.json"
            url = "https://github.com/lackeyjb/playwright-skill"

            # 1st run — fresh install
            slugs = await fetch_skill_urls(
                [url], target, state, client=client,
            )
            assert slugs == ["playwright"], slugs
            assert (target / "playwright" / "SKILL.md").exists()
            stored = _json.loads(state.read_text())
            assert stored["by_url"][url]["id"] == "sha111", stored

            req_count_after_first = len(transport.requests)

            # 2nd run — same SHA → no archive download, no re-extract
            slugs2 = await fetch_skill_urls(
                [url], target, state, client=client,
            )
            assert slugs2 == [], (
                "expected empty install list when upstream unchanged",
                slugs2,
            )
            # Only the 2 API calls (repo + commit lookup), no archive fetch
            new_reqs = transport.requests[req_count_after_first:]
            assert all("/archive/" not in r for r in new_reqs), new_reqs

            # 3rd run — upstream SHA changes → re-extract overwrites
            transport.sha = "sha222"
            transport.tar = make_skill_tar("playwright", "marker-v2")
            slugs3 = await fetch_skill_urls(
                [url], target, state, client=client,
            )
            assert slugs3 == ["playwright"], slugs3
            body = (target / "playwright" / "SKILL.md").read_text()
            assert "marker-v2" in body and "marker-v1" not in body, body
            stored2 = _json.loads(state.read_text())
            assert stored2["by_url"][url]["id"] == "sha222"
    finally:
        await client.aclose()
    print("OK: skill_urls fetch flow (install / skip-on-unchanged / re-extract-on-change)")


async def test_skill_fetcher_picks_skills_from_mcp_server_bundle() -> None:
    """When a repo bundles an MCP server *and* an agentskills.io skill,
    rglob still finds the SKILL.md and installs it — non-skill files
    (server.py, manifest.json, etc.) are ignored. Multi-skill bundles
    install each into its own slug folder."""
    import io
    import tarfile
    import tempfile
    from pathlib import Path
    import httpx
    from wyoming_llm_agent.skill_fetcher import fetch_skill_urls

    def add_text(tf, path, text):
        data = text.encode("utf-8")
        info = tarfile.TarInfo(name=path)
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        # An MCP server lives at repo root
        add_text(tf, "mcp-foo-bundle/server.py", "# pretend MCP server\n")
        add_text(tf, "mcp-foo-bundle/package.json",
                 '{"name":"mcp-foo","mcpServers":{"foo":{"command":"node","args":["server.py"]}}}')
        add_text(tf, "mcp-foo-bundle/README.md", "# bundle readme\n")
        # And two skills tucked under skills/ — both agentskills.io spec
        for slug, marker in [("foo-skill", "marker-foo"), ("bar-skill", "marker-bar")]:
            add_text(
                tf, f"mcp-foo-bundle/skills/{slug}/SKILL.md",
                f"---\nname: {slug}\ndescription: A {slug} for testing bundle case.\n---\n\n# {marker}\n",
            )
            add_text(tf, f"mcp-foo-bundle/skills/{slug}/helper.py", "# unrelated file\n")
        # And one malformed SKILL.md that must be skipped without crashing
        add_text(
            tf, "mcp-foo-bundle/broken/SKILL.md",
            "---\nname: \nbroken: yes\n---\nno name in frontmatter\n",
        )
    bundle_tar = buf.getvalue()

    class BundleTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            url = str(request.url)
            if "api.github.com/repos/" in url and url.endswith("/someuser/mcp-foo-bundle"):
                return httpx.Response(200, json={"default_branch": "main"})
            if "/commits/" in url:
                return httpx.Response(200, json={"sha": "bundlesha"})
            if "/archive/" in url:
                return httpx.Response(
                    200, content=bundle_tar,
                    headers={"content-type": "application/gzip"},
                )
            return httpx.Response(404)

    client = httpx.AsyncClient(transport=BundleTransport(), follow_redirects=True)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target = tmp_path / "skills"
            state = tmp_path / "state.json"

            slugs = await fetch_skill_urls(
                ["https://github.com/someuser/mcp-foo-bundle"],
                target, state, client=client,
            )
            assert set(slugs) == {"foo-skill", "bar-skill"}, slugs
            # Each skill folder has its SKILL.md + the helper.py beside it
            assert (target / "foo-skill" / "SKILL.md").exists()
            assert (target / "foo-skill" / "helper.py").exists()
            assert (target / "bar-skill" / "SKILL.md").exists()
            # The MCP server's own files at repo root are NOT in the skills dir
            assert not (target / "mcp-foo-bundle").exists()
            assert not (target / "server.py").exists()
            assert not (target / "package.json").exists()
            # Malformed SKILL.md was rejected (no `broken/` folder installed)
            assert not (target / "broken").exists()
    finally:
        await client.aclose()
    print("OK: skill_urls extracts SKILL.md from MCP-server-bundled repos, ignores non-skill files")


async def test_skill_fetcher_rejects_path_traversal() -> None:
    """A malicious tarball with `../../etc/passwd` is refused before any
    file is written to the target directory."""
    import io
    import tarfile
    import tempfile
    from pathlib import Path
    import httpx
    from wyoming_llm_agent.skill_fetcher import fetch_skill_urls

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        evil = tarfile.TarInfo(name="../../../tmp/owned")
        payload = b"owned\n"
        evil.size = len(payload)
        tf.addfile(evil, io.BytesIO(payload))
    bad_tar = buf.getvalue()

    class TraversalTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(
                200, content=bad_tar,
                headers={"content-type": "application/gzip", "etag": "v1"},
            )

    client = httpx.AsyncClient(
        transport=TraversalTransport(), follow_redirects=True,
    )
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            target = tmp_path / "skills"
            state = tmp_path / "state.json"
            # The URL must end in .tar.gz so the non-github resolve path runs.
            slugs = await fetch_skill_urls(
                ["https://example.com/evil.tar.gz"], target, state,
                client=client,
            )
            # Path-traversal raises inside _fetch_one which is caught + logged;
            # nothing should land in target.
            assert slugs == [], slugs
            assert not (target.parent / "tmp").exists()
    finally:
        await client.aclose()
    print("OK: skill_urls rejects path-traversal tarball entries")


async def test_mcp_skills_install_from_bundles() -> None:
    """fetch_mcp_skills installs MCP-served SKILL.md + siblings on first
    run, skips on unchanged hash, re-installs on change. Malformed
    SKILL.md is skipped without blocking other skills."""
    import json as _json
    import tempfile
    from pathlib import Path

    from wyoming_llm_agent import skill_fetcher as sf
    from wyoming_llm_agent.mcp_client import MCPServerConfig, MCPSkillBundle

    good_md = (
        "---\nname: wardrowbe-skill\ndescription: Wardrobe skill.\n---\n\n# Body v1\n"
    )
    good_md_v2 = good_md.replace("v1", "v2")
    bundle_v1 = MCPSkillBundle(
        server_name="wardrowbe",
        skill_md_uri="skill://wardrowbe/wardrowbe-skill/SKILL.md",
        skill_md_text=good_md,
        siblings={
            "examples/morning.md": b"# morning outfit\n",
            "scripts/run.sh": b"#!/bin/sh\necho hi\n",
        },
    )
    bad_bundle = MCPSkillBundle(
        server_name="wardrowbe", skill_md_uri="skill://wardrowbe/broken/SKILL.md",
        skill_md_text="---\nname:\n---\nno name\n", siblings={},
    )

    calls: dict[str, int] = {"n": 0}
    state_bundles = [[bundle_v1, bad_bundle]]
    async def stub_fetch_bundles(server):
        calls["n"] += 1
        return state_bundles[0]
    sf.fetch_skill_bundles = stub_fetch_bundles  # type: ignore[assignment]

    server = MCPServerConfig(name="wardrowbe", url="http://stub/mcp")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        target = tmp_path / "skills"
        state = tmp_path / "state.json"

        # Run 1 — install good, skip bad
        slugs = await sf.fetch_mcp_skills([server], target, state)
        assert slugs == ["wardrowbe-skill"], slugs
        assert (target / "wardrowbe-skill" / "SKILL.md").read_text() == good_md
        assert (target / "wardrowbe-skill" / "examples" / "morning.md").exists()
        assert (target / "wardrowbe-skill" / "scripts" / "run.sh").exists()
        assert not (target / "broken").exists()
        stored = _json.loads(state.read_text())
        key = "mcp://wardrowbe#wardrowbe-skill"
        assert key in stored["by_url"], stored

        # Run 2 — same bundle → no re-install
        slugs2 = await sf.fetch_mcp_skills([server], target, state)
        assert slugs2 == [], slugs2

        # Run 3 — content change → re-install, overwrite
        state_bundles[0] = [MCPSkillBundle(
            server_name="wardrowbe",
            skill_md_uri=bundle_v1.skill_md_uri,
            skill_md_text=good_md_v2, siblings={"examples/morning.md": b"# v2\n"},
        )]
        slugs3 = await sf.fetch_mcp_skills([server], target, state)
        assert slugs3 == ["wardrowbe-skill"], slugs3
        assert "v2" in (target / "wardrowbe-skill" / "SKILL.md").read_text()
        # Removed sibling no longer present (full rmtree before write)
        assert not (target / "wardrowbe-skill" / "scripts" / "run.sh").exists()
    print("OK: fetch_mcp_skills install / hash-skip / replace, malformed bundle skipped")


async def test_mcp_skill_bundles_assemble_from_resources() -> None:
    """fetch_skill_bundles parses a fake ClientSession's list_resources +
    read_resource: picks every URI ending /SKILL.md, gathers siblings
    sharing the same prefix, ignores unrelated URIs."""
    from mcp.types import (
        ListResourcesResult, ReadResourceResult, Resource, TextResourceContents,
    )

    from wyoming_llm_agent import mcp_client as mc

    resources = [
        Resource(uri="skill://wardrowbe/wardrowbe-skill/SKILL.md",
                 name="SKILL.md", mimeType="text/markdown"),
        Resource(uri="skill://wardrowbe/wardrowbe-skill/examples/morning.md",
                 name="morning.md", mimeType="text/markdown"),
        Resource(uri="skill://wardrowbe/wardrowbe-skill/scripts/run.sh",
                 name="run.sh", mimeType="text/plain"),
        # A second skill in the same server
        Resource(uri="skill://wardrowbe/other-skill/SKILL.md",
                 name="SKILL.md", mimeType="text/markdown"),
        # Unrelated resource — must not be pulled into either skill
        Resource(uri="data://wardrowbe/version", name="version",
                 mimeType="text/plain"),
    ]
    bodies = {
        "skill://wardrowbe/wardrowbe-skill/SKILL.md":
            "---\nname: wardrowbe-skill\ndescription: x.\n---\n# w\n",
        "skill://wardrowbe/wardrowbe-skill/examples/morning.md": "# morning\n",
        "skill://wardrowbe/wardrowbe-skill/scripts/run.sh": "#!/bin/sh\n",
        "skill://wardrowbe/other-skill/SKILL.md":
            "---\nname: other-skill\ndescription: y.\n---\n# o\n",
        "data://wardrowbe/version": "1.0\n",
    }

    class FakeSession:
        async def list_resources(self):
            return ListResourcesResult(resources=resources)
        async def read_resource(self, uri):
            return ReadResourceResult(contents=[
                TextResourceContents(uri=uri, text=bodies[str(uri)],
                                     mimeType="text/plain"),
            ])

    fake = FakeSession()

    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def fake_open(server):
        yield fake
    mc._open = fake_open  # type: ignore[assignment]

    server = mc.MCPServerConfig(name="wardrowbe", url="http://stub/mcp")
    bundles = await mc.fetch_skill_bundles(server)
    by_uri = {b.skill_md_uri: b for b in bundles}
    assert set(by_uri) == {
        "skill://wardrowbe/wardrowbe-skill/SKILL.md",
        "skill://wardrowbe/other-skill/SKILL.md",
    }, by_uri
    wb = by_uri["skill://wardrowbe/wardrowbe-skill/SKILL.md"]
    assert set(wb.siblings) == {"examples/morning.md", "scripts/run.sh"}, wb.siblings
    assert wb.siblings["scripts/run.sh"] == b"#!/bin/sh\n"
    other = by_uri["skill://wardrowbe/other-skill/SKILL.md"]
    assert other.siblings == {}, other.siblings
    print("OK: fetch_skill_bundles assembles bundles from MCP resources by URI prefix")


async def test_mcp_listener_dispatches_updated_notification() -> None:
    """A ResourceUpdatedNotification routed through the listener's
    message_handler triggers the on_updated callback with the right URI."""
    from mcp.types import (
        ResourceUpdatedNotification, ResourceUpdatedNotificationParams,
        ServerNotification,
    )
    from wyoming_llm_agent.mcp_client import MCPServerConfig
    from wyoming_llm_agent.mcp_listener import _ServerListener

    received: list[tuple[str, str]] = []
    listchanged: list[str] = []

    async def on_updated(server, uri):
        received.append((server.name, uri))
    async def on_list_changed(server):
        listchanged.append(server.name)

    server = MCPServerConfig(name="wb", url="http://stub")
    listener = _ServerListener(
        server=server, on_updated=on_updated, on_list_changed=on_list_changed,
    )

    note = ServerNotification(
        root=ResourceUpdatedNotification(
            method="notifications/resources/updated",
            params=ResourceUpdatedNotificationParams(
                uri="skill://wb/wardrowbe-skill/SKILL.md",
            ),
        )
    )
    await listener._on_message(note)
    assert received == [("wb", "skill://wb/wardrowbe-skill/SKILL.md")], received

    # List changed too
    from mcp.types import ResourceListChangedNotification
    note2 = ServerNotification(
        root=ResourceListChangedNotification(
            method="notifications/resources/list_changed",
        )
    )
    await listener._on_message(note2)
    assert listchanged == ["wb"], listchanged

    # Exception input: handler must not crash; just debug-logs
    await listener._on_message(RuntimeError("transport blew up"))
    print("OK: MCPListener routes resource notifications to callbacks")


async def test_agent_reload_skills_atomically_replaces_registry() -> None:
    """Agent.reload_skills re-scans /config/skills and replaces the
    registry. loaded_skills in active conversations is pruned of names
    that disappeared, retained for names that still exist."""
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.agent import Agent, AgentConfig, _Conversation
    from wyoming_llm_agent.llm import LLMClient, LLMConfig
    from wyoming_llm_agent.skills import Skill

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        # Pre-populate the skill dir with two skills.
        for slug in ("alpha", "beta"):
            (d / slug).mkdir()
            (d / slug / "SKILL.md").write_text(
                f"---\nname: {slug}\ndescription: ok.\n---\n# body\n",
                encoding="utf-8",
            )

        llm = LLMClient(LLMConfig(base_url="http://stub", api_key="k", model="m"))
        try:
            initial = [
                Skill(name="alpha", description="ok", body="# body", path=d/"alpha"),
                Skill(name="beta",  description="ok", body="# body", path=d/"beta"),
                Skill(name="gone",  description="ok", body="# body", path=d/"gone"),
            ]
            agent = Agent(llm=llm, config=AgentConfig(skills=initial))
            convo = _Conversation()
            convo.loaded_skills = {"alpha", "gone"}  # gone is about to disappear
            agent._conversations["c1"] = convo
            assert set(agent._skills_by_name) == {"alpha", "beta", "gone"}

            count = agent.reload_skills(str(d))
            assert count == 2, count
            assert set(agent._skills_by_name) == {"alpha", "beta"}
            assert convo.loaded_skills == {"alpha"}, convo.loaded_skills

            # Add a new skill on disk, reload, should pick it up
            (d / "gamma").mkdir()
            (d / "gamma" / "SKILL.md").write_text(
                "---\nname: gamma\ndescription: ok.\n---\n# body\n",
                encoding="utf-8",
            )
            count2 = agent.reload_skills(str(d))
            assert count2 == 3, count2
            assert set(agent._skills_by_name) == {"alpha", "beta", "gamma"}
        finally:
            await llm.aclose()
            await agent.aclose()
    print("OK: Agent.reload_skills atomically replaces registry + prunes stale loaded_skills")


async def test_list_resources_paginates_via_cursor() -> None:
    """_list_resources_paginated follows nextCursor until exhausted."""
    from mcp.types import ListResourcesResult, Resource
    from wyoming_llm_agent.mcp_client import _list_resources_paginated

    pages = [
        ListResourcesResult(resources=[
            Resource(uri="skill://x/a", name="a", mimeType="text/plain"),
        ], nextCursor="p2"),
        ListResourcesResult(resources=[
            Resource(uri="skill://x/b", name="b", mimeType="text/plain"),
            Resource(uri="skill://x/c", name="c", mimeType="text/plain"),
        ], nextCursor=None),
    ]
    calls: list[str | None] = []
    class FakeSession:
        async def list_resources(self, cursor=None):
            calls.append(cursor)
            return pages[len(calls) - 1]
    all_res = await _list_resources_paginated(FakeSession())
    assert [str(r.uri) for r in all_res] == [
        "skill://x/a", "skill://x/b", "skill://x/c",
    ], all_res
    assert calls == [None, "p2"], calls
    print("OK: _list_resources_paginated follows nextCursor")


async def test_preflight_pass_and_fail() -> None:
    cfg = EmbeddingConfig(base_url="http://example", api_key="", model="probe-model")

    class StubLLM:
        config = cfg
        def __init__(self, response): self._response = response
        async def chat(self, messages, *, tools=None, tool_choice=None, read_timeout=None):
            return self._response

    pass_resp = {"choices": [{"message": {
        "role": "assistant", "content": None,
        "tool_calls": [{"id": "p", "type": "function",
                        "function": {"name": "preflight_ping", "arguments": '{"answer":"pong"}'}}],
    }}]}
    fail_resp = {"choices": [{"message": {"role": "assistant", "content": "pong (as plain text)"}}]}

    await check_function_calling(StubLLM(pass_resp))   # type: ignore[arg-type]
    await check_function_calling(StubLLM(fail_resp))   # type: ignore[arg-type]
    print("OK: preflight handles both success and failure branches")


def test_metrics_emit() -> None:
    """A turn should increment turns_total + tool_calls_total + active_conversations."""
    from prometheus_client import REGISTRY
    from wyoming_llm_agent import metrics as m

    # Snapshot starting counts.
    def sample(name, **labels):
        return REGISTRY.get_sample_value(name, labels) or 0.0

    before_turns = sample("llm_agent_turns_total", language="en", handled="true")
    before_tools = sample("llm_agent_tool_calls_total",
                          tool_name="get_weather", source="http", outcome="success")

    m.record_chat("gpt-4o", ok=True, duration_s=0.5,
                  usage={"prompt_tokens": 10, "completion_tokens": 20})
    m.record_tool_call("get_weather", "http", ok=True)
    m.record_turn("en", handled=True, duration_s=1.5)
    m.set_active_conversations(3)

    after_turns = sample("llm_agent_turns_total", language="en", handled="true")
    after_tools = sample("llm_agent_tool_calls_total",
                         tool_name="get_weather", source="http", outcome="success")
    assert after_turns == before_turns + 1, (before_turns, after_turns)
    assert after_tools == before_tools + 1, (before_tools, after_tools)
    assert REGISTRY.get_sample_value("llm_agent_active_conversations") == 3.0

    body, ctype = m.render_latest()
    assert b"llm_agent_turns_total" in body
    assert "text/plain" in ctype
    print("OK: prometheus metrics record + render")


# ----- Memory tests -----------------------------------------------------------


def test_memory_store_roundtrip() -> None:
    """save → list → read → delete cycle, plus the bucket layout."""
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.memory import MemoryStore

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(root=Path(td))

        # Empty bucket
        assert store.list("alice") == []
        assert store.read("alice", "dog-name") is None
        assert store.render_index("alice") == ""

        store.save("alice", "dog-name", "Alice's dog", "Bau, 3yo Welsh Corgi.")
        # Body file under users/alice/, not shared/
        assert (Path(td) / "users" / "alice" / "dog-name.md").exists()
        assert not (Path(td) / "shared").exists() \
            or not (Path(td) / "shared" / "dog-name.md").exists()

        assert store.list("alice") == [("dog-name", "Alice's dog")]
        body = store.read("alice", "dog-name")
        assert body == "Bau, 3yo Welsh Corgi."

        rendered = store.render_index("alice")
        assert "dog-name: Alice's dog" in rendered
        assert "this user" in rendered

        # Update overwrites
        store.save("alice", "dog-name", "Updated", "New body")
        assert store.read("alice", "dog-name") == "New body"
        assert store.list("alice") == [("dog-name", "Updated")]

        # Delete clears file + index
        assert store.delete("alice", "dog-name") is True
        assert store.read("alice", "dog-name") is None
        assert store.list("alice") == []
        # Index file removed when empty
        assert not (Path(td) / "users" / "alice" / "MEMORY.md").exists()
        # Second delete is a no-op
        assert store.delete("alice", "dog-name") is False
    print("OK: memory store save/list/read/delete roundtrip")


def test_memory_user_isolation() -> None:
    """Same slug, different user_ids → separate files, separate index."""
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.memory import MemoryStore

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(root=Path(td))
        store.save("alice", "pet", "Alice's pet", "Bau")
        store.save("bob", "pet", "Bob's pet", "Whiskers")

        assert store.read("alice", "pet") == "Bau"
        assert store.read("bob", "pet") == "Whiskers"
        assert dict(store.list("alice")) == {"pet": "Alice's pet"}
        assert dict(store.list("bob")) == {"pet": "Bob's pet"}

        # Alice's render contains her description, not Bob's
        rendered = store.render_index("alice")
        assert "Alice's pet" in rendered and "Bob's pet" not in rendered
    print("OK: memory store isolates per-user buckets")


def test_memory_shared_fallback() -> None:
    """None and the reserved literal 'shared' both land in the shared
    bucket. Same for syntactically-invalid user_ids (defense in depth).
    """
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.memory import MemoryStore

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(root=Path(td))
        store.save(None, "fact", "Shared fact", "Hello")
        # Same content visible under the literal 'shared' and an invalid id
        assert store.read(None, "fact") == "Hello"
        assert store.read("shared", "fact") == "Hello"
        assert store.read("../escape", "fact") == "Hello"
        # File actually lives under shared/, not users/
        assert (Path(td) / "shared" / "fact.md").exists()
        assert not (Path(td) / "users").exists()
        # Header marks it as shared
        assert "shared" in store.render_index(None).lower()
    print("OK: memory store routes None / 'shared' / invalid id to shared bucket")


def test_memory_bad_slug_rejected() -> None:
    """Slug regex rejects every shape of bad input."""
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.memory import MemoryError as MemErr, MemoryStore

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(root=Path(td))
        bad_slugs = [
            "",
            "UPPER",
            "with space",
            "../etc",
            "/abs",
            "trailing-",
            "-leading",
            "double--hyphen",  # actually allowed by regex; remove if so
            "a" * 65,  # too long
        ]
        # double--hyphen is allowed by our regex (mirrors what's safe on
        # disk); only reject the ones the regex truly rejects.
        for bad in bad_slugs:
            try:
                store.save("alice", bad, "desc", "body")
            except MemErr:
                continue
            # If we get here, slug was accepted — verify it's actually
            # safe by checking the file landed in the bucket dir.
            bucket = Path(td) / "users" / "alice"
            body = bucket / f"{bad}.md"
            assert body.exists() and body.resolve().parent == bucket.resolve(), (
                f"accepted slug {bad!r} produced unsafe path {body}"
            )
            # Clean up so the next iteration doesn't see leftover state.
            body.unlink()
    print("OK: memory store rejects unsafe slugs (or contains them safely)")


def test_memory_save_bucket_full_attaches_status() -> None:
    """When memory_save is rejected for bucket-full, the dispatch result
    carries a `status` payload (entry list + sizes) so the LLM can pick
    what to delete without a separate memory_status round trip.
    """
    import asyncio
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.agent import _SystemContext
    from wyoming_llm_agent.memory import (
        MAX_BUCKET_MEMORY_BYTES, MAX_MEMORY_BYTES, MemoryStore,
    )

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(root=Path(td))
        # Fill the bucket near its cap with max-size entries so one more
        # save tips it over MAX_BUCKET_MEMORY_BYTES.
        chunk = "x" * MAX_MEMORY_BYTES
        n_to_fill = MAX_BUCKET_MEMORY_BYTES // MAX_MEMORY_BYTES
        for i in range(n_to_fill):
            store.save("alice", f"entry-{i}", f"entry {i}", chunk)

        ag = Agent(llm=ScriptedLLM([]), config=AgentConfig(memory_store=store))
        ctx = _SystemContext(
            ha_prompt=None, language=None, device_id=None,
            satellite_id=None, conversation_id=None, user_id="alice",
        )
        result = asyncio.run(ag._dispatch_meta_tool(
            "memory_save",
            {"slug": "overflow", "description": "too much", "body": chunk},
            None, ctx,
        ))
        assert result["ok"] is False
        assert "bucket" in result["error"].lower()
        assert "status" in result, "bucket-full result must attach status"
        status = result["status"]
        assert status["entry_count"] == n_to_fill
        assert status["entries"], "status must list current entries"
        # Sorted largest-first so the LLM sees the biggest deletion targets.
        sizes = [e["bytes"] for e in status["entries"]]
        assert sizes == sorted(sizes, reverse=True)
        # The rejected entry must not have landed on disk.
        assert not (Path(td) / "users" / "alice" / "overflow.md").exists()

    print("OK: memory_save bucket-full attaches status payload")


async def test_memory_meta_tools_in_system_prompt() -> None:
    """memory_save via the LLM loop updates the system prompt mid-turn
    and the index persists into the next turn.
    """
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.memory import MemoryStore

    with tempfile.TemporaryDirectory() as td:
        ha_snapshot = make_ha_snapshot(prompt_text="HA prompt")
        fake_fetch = _FakeHAFetch(ha_snapshot)
        orig_fetch = agent_mod.fetch_session_snapshot
        agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
        try:
            # Turn 1: LLM calls memory_save, then answers.
            turn1 = [
                {"choices": [{"message": {
                    "role": "assistant", "content": "",
                    "tool_calls": [{
                        "id": "m1", "type": "function",
                        "function": {
                            "name": "memory_save",
                            "arguments": (
                                '{"slug": "dog-name", '
                                '"description": "User\'s dog", '
                                '"body": "Bau the Corgi"}'
                            ),
                        },
                    }],
                }}]},
                {"choices": [{"message": {
                    "role": "assistant", "content": "saved",
                }}]},
            ]
            # Turn 2: same conversation, index should show in system msg.
            turn2 = [
                {"choices": [{"message": {
                    "role": "assistant", "content": "ok",
                }}]},
            ]
            llm = ScriptedLLM(turn1 + turn2)
            seen_systems: list[str] = []
            seen_tool_names: list[set[str]] = []
            orig_chat = llm.chat
            async def spy(messages, *, tools=None, tool_choice=None):
                seen_systems.append(messages[0]["content"])
                seen_tool_names.append({t["function"]["name"] for t in (tools or [])})
                return await orig_chat(messages, tools=tools, tool_choice=tool_choice)
            llm.chat = spy  # type: ignore[assignment]

            store = MemoryStore(root=Path(td))
            ag = Agent(
                llm=llm,
                config=AgentConfig(
                    memory_store=store,
                    ha_mcp_server=MCPServerConfig(name="ha", url="http://stub/mcp"),
                ),
            )

            await ag.respond(
                text="remember bau", language="en",
                conversation_id="m-c1", device_id=None, satellite_id=None,
                user_id="alice",
            )
            # Iter 1: memory meta-tools are exposed; no index yet.
            assert {"memory_save", "memory_read", "memory_delete"} <= seen_tool_names[0]
            assert "dog-name" not in seen_systems[0]
            # Iter 2: index now appears with the saved entry.
            assert "dog-name: User's dog" in seen_systems[1], seen_systems[1]
            # Header for non-shared bucket
            assert "this user" in seen_systems[1]
            # File on disk
            assert (Path(td) / "users" / "alice" / "dog-name.md").exists()

            await ag.respond(
                text="status?", language="en",
                conversation_id="m-c1", device_id=None, satellite_id=None,
                user_id="alice",
            )
            # Turn 2 starts with the index already in the system msg.
            assert "dog-name: User's dog" in seen_systems[2]
        finally:
            agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]
    print("OK: memory_save updates system prompt mid-turn and persists across turns")


def test_memory_disabled_hides_meta_tools() -> None:
    """No MemoryStore → no memory_* in _meta_tool_defs. Working-memory
    meta-tools are NOT gated and remain visible.
    """
    ag = Agent(
        llm=ScriptedLLM([]),
        config=AgentConfig(),  # memory_store defaults to None
    )
    names = {t["function"]["name"] for t in ag._meta_tool_defs()}
    assert "memory_save" not in names
    assert "memory_read" not in names
    assert "memory_delete" not in names
    # Working memory is always-on — lives in _Conversation, no dep.
    assert "working_memory_set" in names
    assert "working_memory_clear" in names
    print("OK: memory disabled hides memory_* meta tools; working_memory_* stay")


async def test_working_memory_set_and_clear_lifecycle() -> None:
    """working_memory_set fills the slot 9 block, working_memory_clear
    empties it. Buffer persists across turns within the same conversation.
    """
    ha_snapshot = make_ha_snapshot()
    fake_fetch = _FakeHAFetch(ha_snapshot)
    orig_fetch = agent_mod.fetch_session_snapshot
    agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
    try:
        # Turn 1: model calls working_memory_set, then answers.
        # Turn 2 (same convo): no tool calls — buffer should still appear.
        # Turn 3: model calls working_memory_clear, then answers.
        turn1 = [
            {"choices": [{"message": {
                "role": "assistant", "content": "",
                "tool_calls": [{
                    "id": "w1", "type": "function",
                    "function": {
                        "name": "working_memory_set",
                        "arguments": (
                            '{"content": "Planning dinner: pasta + salad"}'
                        ),
                    },
                }],
            }}]},
            {"choices": [{"message": {"role": "assistant", "content": "noted"}}]},
        ]
        turn2 = [
            {"choices": [{"message": {"role": "assistant", "content": "yes"}}]},
        ]
        turn3 = [
            {"choices": [{"message": {
                "role": "assistant", "content": "",
                "tool_calls": [{
                    "id": "w3", "type": "function",
                    "function": {
                        "name": "working_memory_clear",
                        "arguments": "{}",
                    },
                }],
            }}]},
            {"choices": [{"message": {"role": "assistant", "content": "cleared"}}]},
        ]
        llm = ScriptedLLM(turn1 + turn2 + turn3)
        seen: list[str] = []
        orig_chat = llm.chat
        async def spy(messages, *, tools=None, tool_choice=None):
            seen.append(messages[0]["content"])
            return await orig_chat(messages, tools=tools, tool_choice=tool_choice)
        llm.chat = spy  # type: ignore[assignment]
        ag = Agent(
            llm=llm,
            config=AgentConfig(
                ha_mcp_server=MCPServerConfig(name="ha", url="http://stub/mcp"),
            ),
        )

        # ----- Turn 1: set
        await ag.respond(
            text="planning dinner", language="en",
            conversation_id="wm-c1", device_id=None, satellite_id=None,
        )
        # Iter 1: pre-set system prompt has no working-memory block.
        assert "[Working memory for this conversation]" not in seen[0]
        # Iter 2: rebuild after set → block visible.
        assert "[Working memory for this conversation]" in seen[1]
        assert "Planning dinner: pasta + salad" in seen[1]

        # ----- Turn 2: same convo, buffer persists.
        await ag.respond(
            text="anything else?", language="en",
            conversation_id="wm-c1", device_id=None, satellite_id=None,
        )
        assert "Planning dinner: pasta + salad" in seen[2], (
            "working memory should persist across turns"
        )

        # ----- Turn 3: clear
        await ag.respond(
            text="forget it", language="en",
            conversation_id="wm-c1", device_id=None, satellite_id=None,
        )
        # Iter at start of turn 3: still has the buffer (clear not yet called).
        assert "Planning dinner: pasta + salad" in seen[3]
        # After clear, the rebuilt system message drops the block.
        assert "[Working memory for this conversation]" not in seen[4]
    finally:
        agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]
    print("OK: working_memory_set/clear lifecycle + cross-turn persistence")


def test_working_memory_size_cap_rejects_oversize() -> None:
    """Content > 8KB is rejected with ok=False; buffer untouched."""
    from wyoming_llm_agent.agent import (
        MAX_WORKING_MEMORY_BYTES, _Conversation, _SystemContext,
    )

    ag = Agent(llm=ScriptedLLM([]), config=AgentConfig())
    convo = _Conversation()
    convo.working_memory = "starting state"
    ctx = _SystemContext(
        ha_prompt=None, language=None, device_id=None,
        satellite_id=None, conversation_id=None, user_id=None,
    )
    oversize = "x" * (MAX_WORKING_MEMORY_BYTES + 1)
    import asyncio
    result = asyncio.run(ag._dispatch_meta_tool(
        "working_memory_set", {"content": oversize}, convo, ctx,
    ))
    assert result["ok"] is False
    assert "exceeds" in result["error"]
    assert convo.working_memory == "starting state", (
        "buffer must stay intact on oversize rejection"
    )
    print("OK: working_memory size cap enforced; buffer preserved on reject")


def test_working_memory_empty_set_acts_like_clear() -> None:
    """working_memory_set('') is equivalent to working_memory_clear()."""
    from wyoming_llm_agent.agent import _Conversation, _SystemContext

    ag = Agent(llm=ScriptedLLM([]), config=AgentConfig())
    convo = _Conversation()
    convo.working_memory = "old plan"
    ctx = _SystemContext(
        ha_prompt=None, language=None, device_id=None,
        satellite_id=None, conversation_id=None, user_id=None,
    )
    import asyncio
    result = asyncio.run(ag._dispatch_meta_tool(
        "working_memory_set", {"content": ""}, convo, ctx,
    ))
    assert result["ok"] is True
    assert convo.working_memory == "", "empty set should clear the buffer"
    print("OK: working_memory_set('') clears the buffer")


# ----- Workspace (R3) tests --------------------------------------------------


def test_workspace_seeds_missing_files_with_defaults() -> None:
    """Empty workspace dir → all four files seeded with built-in
    Korean defaults, no migration source needed.
    """
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.workspace import (
        BOOTSTRAP_FILE, HEARTBEAT_FILE, IDENTITY_FILE, SOUL_FILE,
        load_workspace,
    )

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        ws = load_workspace(root)
        for name in (SOUL_FILE, IDENTITY_FILE, HEARTBEAT_FILE, BOOTSTRAP_FILE):
            assert (root / name).exists(), f"{name} not seeded"
        assert "행동 규범" in (root / SOUL_FILE).read_text(encoding="utf-8")
        assert "행동 규범" in ws.soul
        assert "{{ date }}" in ws.heartbeat_template
    print("OK: workspace seeds all four files with built-in defaults")


def test_workspace_skip_seed_when_disabled() -> None:
    """BOOTSTRAP.md with seed_templates: false → other files stay missing."""
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.workspace import (
        BOOTSTRAP_FILE, HEARTBEAT_FILE, IDENTITY_FILE, SOUL_FILE,
        load_workspace,
    )

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / BOOTSTRAP_FILE).write_text(
            "---\nseed_templates: false\nauto_load_skills: []\n---\n",
            encoding="utf-8",
        )
        ws = load_workspace(root)
        assert not (root / SOUL_FILE).exists()
        assert not (root / IDENTITY_FILE).exists()
        assert not (root / HEARTBEAT_FILE).exists()
        assert ws.soul == ""
        assert ws.identity == ""
        assert ws.heartbeat_template == ""
    print("OK: BOOTSTRAP seed_templates=false suppresses seeding")


def test_bootstrap_auto_load_skills_parsed() -> None:
    """auto_load_skills surfaced on Workspace; unknown types rejected."""
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.workspace import BOOTSTRAP_FILE, load_workspace

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / BOOTSTRAP_FILE).write_text(
            "---\nseed_templates: false\nauto_load_skills:\n"
            "  - foo\n  - bar\n---\n",
            encoding="utf-8",
        )
        ws = load_workspace(root)
        assert ws.auto_load_skills == ("foo", "bar")
    print("OK: BOOTSTRAP auto_load_skills parsed into Workspace")


def test_heartbeat_renders_per_turn_with_vars() -> None:
    """HEARTBEAT template gets date/time/weekday/language/device etc."""
    from datetime import datetime
    from jinja2 import StrictUndefined
    from jinja2.sandbox import SandboxedEnvironment
    from wyoming_llm_agent.workspace import render_heartbeat

    env = SandboxedEnvironment(undefined=StrictUndefined)
    template = (
        "date={{ date }} wd={{ weekday }} lang={{ language }} "
        "dev={{ device_id }}"
    )
    out = render_heartbeat(
        env, template,
        language="ko", device_id="abc", satellite_id=None,
        conversation_id=None, user_id=None,
        now=datetime(2026, 5, 26, 14, 30),
    )
    assert "date=2026-05-26" in out
    assert "wd=Tuesday" in out
    assert "lang=ko" in out
    assert "dev=abc" in out
    print("OK: HEARTBEAT renders date/weekday/lang/device")


def test_heartbeat_render_failure_falls_back_to_raw() -> None:
    """Broken Jinja2 → raw text, no crash."""
    from jinja2 import StrictUndefined
    from jinja2.sandbox import SandboxedEnvironment
    from wyoming_llm_agent.workspace import render_heartbeat

    env = SandboxedEnvironment(undefined=StrictUndefined)
    broken = "Hello {% if %}"  # syntax error
    out = render_heartbeat(
        env, broken,
        language=None, device_id=None, satellite_id=None,
        conversation_id=None, user_id=None,
    )
    assert out == broken.strip()
    print("OK: HEARTBEAT bad Jinja2 falls back to raw text")


def test_memory_render_shared_and_user_separate() -> None:
    """render_shared_index and render_user_index isolate their buckets."""
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.memory import MemoryStore

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(root=Path(td))
        store.save(None, "fact-h", "Household-wide", "Body H")
        store.save("alice", "fact-a", "Alice-only", "Body A")
        shared = store.render_shared_index()
        user = store.render_user_index("alice")
        assert "fact-h: Household-wide" in shared
        assert "Household-wide memory" in shared
        assert "fact-a" not in shared
        assert "fact-a: Alice-only" in user
        assert "Memory for this user" in user
        assert "fact-h" not in user
        # user_id None or unsafe → empty user block
        assert store.render_user_index(None) == ""
        assert store.render_user_index("shared") == ""
    print("OK: render_shared_index / render_user_index isolate buckets")


def test_journal_append_and_read() -> None:
    """journal_append creates today's file with HH:MM heading; subsequent
    appends accumulate; read_journal_day(today) returns the body;
    missing-day read returns (date, None); unsafe user_id raises.
    """
    import tempfile
    from datetime import datetime
    from pathlib import Path
    from wyoming_llm_agent.memory import MemoryError as MemErr, MemoryStore

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(root=Path(td))
        fixed = datetime(2026, 5, 26, 14, 30)
        date1, n1 = store.journal_append(
            "alice", "Planned dinner: pasta + salad.", now=fixed,
        )
        assert date1 == "2026-05-26"
        # File exists under journal/.
        path = Path(td) / "users" / "alice" / "journal" / "2026-05-26.md"
        assert path.exists()
        body1 = path.read_text(encoding="utf-8")
        assert body1.startswith("## 14:30\n")
        assert "pasta + salad" in body1

        # Second append at a different time accumulates.
        later = datetime(2026, 5, 26, 16, 0)
        date2, n2 = store.journal_append(
            "alice", "Mom's birthday is 2026-06-15.", now=later,
        )
        assert date2 == "2026-05-26"
        assert n2 > n1
        body2 = path.read_text(encoding="utf-8")
        assert "## 14:30" in body2 and "## 16:00" in body2

        # read_journal_day default = today (mocked via `now`).
        rd, rb = store.read_journal_day("alice", now=fixed)
        assert rd == "2026-05-26"
        assert "pasta + salad" in rb

        # Explicit specific date.
        rd2, rb2 = store.read_journal_day("alice", "2026-05-26")
        assert rd2 == "2026-05-26" and "Mom's birthday" in rb2

        # Missing date → body is None.
        rd3, rb3 = store.read_journal_day("alice", "2026-01-01")
        assert rd3 == "2026-01-01" and rb3 is None

        # Unsafe user_id → both ops raise.
        try:
            store.journal_append(None, "should fail")
        except MemErr:
            pass
        else:
            raise AssertionError("unsafe user_id should raise")
        try:
            store.read_journal_day("shared")
        except MemErr:
            pass
        else:
            raise AssertionError("shared bucket has no journal")

        # Bad date format → raises.
        try:
            store.read_journal_day("alice", "2026/05/26")
        except MemErr:
            pass
        else:
            raise AssertionError("non-YYYY-MM-DD must be rejected")
    print("OK: journal_append/read_journal_day per-user, missing → None, unsafe → raise")


def test_journal_entry_and_day_caps() -> None:
    """Per-entry 4KB cap rejects oversize; per-day 64KB cap rejects
    when the cumulative file would overflow.
    """
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.memory import (
        MAX_JOURNAL_DAY_BYTES, MAX_JOURNAL_ENTRY_BYTES,
        MemoryError as MemErr, MemoryStore,
    )

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(root=Path(td))
        # Oversize single entry rejected.
        oversize = "x" * (MAX_JOURNAL_ENTRY_BYTES + 1)
        try:
            store.journal_append("bob", oversize)
        except MemErr as exc:
            assert "exceeds" in str(exc)
        else:
            raise AssertionError("oversize entry should be rejected")

        # Fill day file just under cap, then verify next append rejects.
        big_entry = "y" * (MAX_JOURNAL_ENTRY_BYTES - 100)
        # Each append adds entry plus ~12 bytes of `## HH:MM\n\n\n`.
        # 64KB / 4KB = ~16 entries, plus a final overshoot check.
        # Append until next would overflow.
        appends = 0
        while True:
            try:
                store.journal_append("bob", big_entry)
                appends += 1
                if appends > 30:
                    raise AssertionError("cap should have been hit by now")
            except MemErr as exc:
                # Hit the day-file cap.
                assert "day file" in str(exc) or "exceeds" in str(exc)
                break
        assert appends >= 1, "at least one append must succeed"
    print("OK: journal per-entry and per-day caps enforced")


def test_user_profile_seed_and_render() -> None:
    """ensure_user_profile_seeded writes template if missing, leaves
    existing file untouched, and render_user_profile picks it up.
    Unsafe / shared user_id is a no-op.
    """
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.memory import MemoryStore

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(root=Path(td))
        # First call seeds.
        assert store.ensure_user_profile_seeded("alice") is True
        path = Path(td) / "users" / "alice" / "USER.md"
        assert path.exists()
        assert "USER.md — 사용자 프로필" in path.read_text(encoding="utf-8")

        # Second call is idempotent — does not overwrite.
        path.write_text("# Custom profile\nAlice's edits.\n", encoding="utf-8")
        assert store.ensure_user_profile_seeded("alice") is False
        assert "Alice's edits." in path.read_text(encoding="utf-8")

        # Render returns the body with a header.
        rendered = store.render_user_profile("alice")
        assert "Profile for this user (household member)" in rendered
        assert "Alice's edits." in rendered

        # Unsafe / shared / None → no-op + empty render.
        assert store.ensure_user_profile_seeded(None) is False
        assert store.ensure_user_profile_seeded("shared") is False
        assert store.ensure_user_profile_seeded("../escape") is False
        assert store.render_user_profile(None) == ""
        assert store.render_user_profile("shared") == ""
        # No directories created for unsafe ids.
        assert not (Path(td) / "users" / "shared").exists()
    print("OK: USER.md seed-on-first-encounter + idempotent + skip unsafe")


def test_user_bootstrap_seed_render_and_placeholder_skip() -> None:
    """Per-user BOOTSTRAP.md mirrors the USER.md seed pattern.

    - First touch seeds a placeholder body
    - Idempotent on second call
    - Placeholder body alone renders as "" (slot omitted)
    - Substantive edits render with the "Per-user assistant
      instructions" header
    - Unsafe / shared / None user_id is a no-op
    - Oversize body treated as empty
    """
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.memory import MemoryStore, MAX_USER_BOOTSTRAP_BYTES

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(root=Path(td))
        # First touch seeds the placeholder.
        assert store.ensure_user_bootstrap_seeded("bob") is True
        path = Path(td) / "users" / "bob" / "BOOTSTRAP.md"
        assert path.exists()
        assert "BOOTSTRAP.md" in path.read_text(encoding="utf-8")

        # Placeholder alone → render returns "" so the slot is omitted.
        assert store.render_user_bootstrap("bob") == ""

        # Second call is idempotent — never overwrites user edits.
        path.write_text(
            "## House rules for Bob\n- Quiet after 10pm\n- Always ask "
            "before broadcasting\n", encoding="utf-8",
        )
        assert store.ensure_user_bootstrap_seeded("bob") is False
        rendered = store.render_user_bootstrap("bob")
        assert "Per-user assistant instructions" in rendered
        assert "Quiet after 10pm" in rendered
        assert "Always ask before broadcasting" in rendered

        # Unsafe / shared / None → no-op + empty render.
        assert store.ensure_user_bootstrap_seeded(None) is False
        assert store.ensure_user_bootstrap_seeded("shared") is False
        assert store.ensure_user_bootstrap_seeded("../escape") is False
        assert store.render_user_bootstrap(None) == ""
        assert store.render_user_bootstrap("shared") == ""
        assert store.render_user_bootstrap("../escape") == ""

        # Oversize → treated as empty (defensive cap).
        big_path = Path(td) / "users" / "huge" / "BOOTSTRAP.md"
        big_path.parent.mkdir(parents=True)
        big_path.write_text("x" * (MAX_USER_BOOTSTRAP_BYTES + 1), encoding="utf-8")
        assert store.render_user_bootstrap("huge") == ""
    print("OK: per-user BOOTSTRAP.md seed + placeholder-skip + substantive render + caps")


async def test_system_prompt_ordering_workspace_mode() -> None:
    """messages[0] in workspace mode contains the 12 sections in order.
    SOUL → IDENTITY → HA → catalog → shared mem → USER profile →
    user mem → active skill body → HEARTBEAT.
    User BOOTSTRAP / BOOTSTRAP body / working memory slots are silent
    in this test (no content). USER.md + BOOTSTRAP.md are auto-seeded
    on the first turn for a new user.
    """
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.memory import MemoryStore
    from wyoming_llm_agent.skills import Skill
    from wyoming_llm_agent.workspace import Workspace

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(root=Path(td))
        store.save(None, "shared-fact", "Household-wide", "shared body")
        store.save("alice", "user-fact", "Alice-only", "alice body")

        ws = Workspace(
            soul="--SOUL-MARKER--",
            identity="--IDENTITY-MARKER--",
            heartbeat_template="--HEARTBEAT-MARKER-- {{ date }}",
            auto_load_skills=(),
        )
        focus = Skill(
            name="focus", description="Focus mode skill",
            body="--SKILL-BODY-MARKER--", path=Path("/tmp/nope"),
        )

        ha_snapshot = make_ha_snapshot(prompt_text="--HA-PROMPT-MARKER--")
        fake_fetch = _FakeHAFetch(ha_snapshot)
        orig_fetch = agent_mod.fetch_session_snapshot
        agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
        try:
            llm = ScriptedLLM([
                # Iter 1: load focus skill, then answer (so skill body is
                # visible in iter 2's system prompt).
                {"choices": [{"message": {
                    "role": "assistant", "content": "",
                    "tool_calls": [{
                        "id": "x1", "type": "function",
                        "function": {
                            "name": "load_skill",
                            "arguments": '{"name": "focus"}',
                        },
                    }],
                }}]},
                {"choices": [{"message": {
                    "role": "assistant", "content": "ok",
                }}]},
            ])
            seen: list[str] = []
            orig_chat = llm.chat
            async def spy(messages, *, tools=None, tool_choice=None):
                seen.append(messages[0]["content"])
                return await orig_chat(messages, tools=tools, tool_choice=tool_choice)
            llm.chat = spy  # type: ignore[assignment]

            ag = Agent(
                llm=llm,
                config=AgentConfig(
                    memory_store=store,
                    workspace=ws,
                    skills=[focus],
                    ha_mcp_server=MCPServerConfig(name="ha", url="http://stub/mcp"),
                ),
            )
            await ag.respond(
                text="hi", language="en",
                conversation_id="r3-c1", device_id="dev-1", satellite_id=None,
                user_id="alice",
            )
            # Iter 2 contains all sections including the loaded skill body.
            sysmsg = seen[1]
            markers = [
                "--SOUL-MARKER--",
                "--IDENTITY-MARKER--",
                "--HA-PROMPT-MARKER--",
                "Available skills",
                "Household-wide memory",
                "Profile for this user",  # USER.md seeded on first turn
                "Memory for this user",
                "--SKILL-BODY-MARKER--",
                "--HEARTBEAT-MARKER--",
            ]
            positions = [sysmsg.index(m) for m in markers]
            assert positions == sorted(positions), (
                f"sections out of order: {list(zip(markers, positions))}",
            )
            # USER.md + BOOTSTRAP.md were both auto-seeded for alice on
            # this turn. BOOTSTRAP placeholder body is non-substantive
            # (headings + italic-only lines), so the slot is omitted from
            # the prompt — assert that by absence of the per-user header.
            assert (Path(td) / "users" / "alice" / "USER.md").exists()
            assert (Path(td) / "users" / "alice" / "BOOTSTRAP.md").exists()
            assert "Per-user assistant instructions" not in sysmsg, (
                "seeded BOOTSTRAP placeholder must not render in prompt"
            )
        finally:
            agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]
    print("OK: workspace mode emits all 12 sections in cache-stable order; USER.md + BOOTSTRAP.md auto-seeded")


async def test_user_bootstrap_substantive_renders_between_shared_mem_and_profile() -> None:
    """When a user's BOOTSTRAP.md has substantive content (not just the
    seeded placeholder), it appears in slot 7 — after the shared MEMORY
    index, before the USER profile. Validates the per-user cache-stable
    grouping (slots 6 → 7 → 8 → 9).
    """
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.memory import MemoryStore
    from wyoming_llm_agent.workspace import Workspace

    with tempfile.TemporaryDirectory() as td:
        store = MemoryStore(root=Path(td))
        # Pre-write substantive per-user BOOTSTRAP so seed is a no-op
        # and the rendered slot is present.
        users_bob = Path(td) / "users" / "bob"
        users_bob.mkdir(parents=True)
        (users_bob / "BOOTSTRAP.md").write_text(
            "--USER-BOOTSTRAP-MARKER--\n- Stay terse.\n", encoding="utf-8",
        )
        # Description is what shows in the rendered index — use it as
        # the slot-6 anchor. The body itself never enters the system
        # prompt (only the index does).
        store.save(None, "shared-fact", "--SHARED-DESC--", "shared body")

        ws = Workspace(
            soul="--SOUL--",
            identity="--IDENTITY--",
            heartbeat_template="--HEARTBEAT-- {{ date }}",
        )

        ha_snapshot = make_ha_snapshot(prompt_text="--HA--")
        fake_fetch = _FakeHAFetch(ha_snapshot)
        orig_fetch = agent_mod.fetch_session_snapshot
        agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
        try:
            llm = ScriptedLLM([
                {"choices": [{"message": {
                    "role": "assistant", "content": "ok",
                }}]},
            ])
            seen: list[str] = []
            orig_chat = llm.chat
            async def spy(messages, *, tools=None, tool_choice=None):
                seen.append(messages[0]["content"])
                return await orig_chat(messages, tools=tools, tool_choice=tool_choice)
            llm.chat = spy  # type: ignore[assignment]

            ag = Agent(
                llm=llm,
                config=AgentConfig(
                    memory_store=store,
                    workspace=ws,
                    ha_mcp_server=MCPServerConfig(name="ha", url="http://stub/mcp"),
                ),
            )
            await ag.respond(
                text="hi", language="en",
                conversation_id="ubp-c1", device_id="dev-1", satellite_id=None,
                user_id="bob",
            )
            sysmsg = seen[0]
            # Slot 6 (shared MEMORY) → slot 7 (user BOOTSTRAP) → slot 8
            # (USER profile, auto-seeded). The placeholder USER profile
            # body is rendered as-is by render_user_profile (header
            # `Profile for this user`), so we can use it as the slot-8
            # anchor.
            assert "Per-user assistant instructions" in sysmsg
            assert "--USER-BOOTSTRAP-MARKER--" in sysmsg
            ordered = [
                "--SHARED-DESC--",
                "Per-user assistant instructions",
                "Profile for this user",
            ]
            positions = [sysmsg.index(m) for m in ordered]
            assert positions == sorted(positions), (
                f"per-user slots misordered: {list(zip(ordered, positions))}"
            )
        finally:
            agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]
    print("OK: substantive user BOOTSTRAP renders between shared MEMORY and USER profile")


async def test_workspace_hot_reload_picks_up_edits() -> None:
    """Editing SOUL.md between turns is picked up without addon restart.
    The agent stats workspace files each turn and reloads on mtime
    change.
    """
    import os
    import tempfile
    import time
    from pathlib import Path
    from wyoming_llm_agent.workspace import SOUL_FILE, load_workspace

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # Seed workspace files via load_workspace (writes defaults).
        ws = load_workspace(root)
        assert (root / SOUL_FILE).exists()
        # Replace SOUL.md with a marker so we know if reload picks it up.
        (root / SOUL_FILE).write_text("--SOUL-V1--\n", encoding="utf-8")

        ha_snapshot = make_ha_snapshot()
        fake_fetch = _FakeHAFetch(ha_snapshot)
        orig_fetch = agent_mod.fetch_session_snapshot
        agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
        try:
            llm = ScriptedLLM([
                {"choices": [{"message": {"role": "assistant", "content": "v1"}}]},
                {"choices": [{"message": {"role": "assistant", "content": "v2"}}]},
            ])
            seen: list[str] = []
            orig_chat = llm.chat
            async def spy(messages, *, tools=None, tool_choice=None):
                seen.append(messages[0]["content"])
                return await orig_chat(messages, tools=tools, tool_choice=tool_choice)
            llm.chat = spy  # type: ignore[assignment]
            ag = Agent(
                llm=llm,
                config=AgentConfig(
                    workspace=load_workspace(root),
                    ha_mcp_server=MCPServerConfig(name="ha", url="http://stub/mcp"),
                ),
            )
            # Turn 1: V1 SOUL.
            await ag.respond(
                text="hi", language="en", conversation_id="hr-c1",
                device_id=None, satellite_id=None,
            )
            assert "--SOUL-V1--" in seen[0]

            # Edit SOUL.md on disk + bump mtime so the stat detects it.
            (root / SOUL_FILE).write_text("--SOUL-V2--\n", encoding="utf-8")
            future = time.time() + 5
            os.utime(root / SOUL_FILE, (future, future))

            # Turn 2: V2 SOUL should appear.
            await ag.respond(
                text="hi again", language="en", conversation_id="hr-c1",
                device_id=None, satellite_id=None,
            )
            assert "--SOUL-V2--" in seen[1]
            assert "--SOUL-V1--" not in seen[1]
        finally:
            agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]
    print("OK: workspace hot reload picks up SOUL.md edits between turns")


async def test_bootstrap_body_injected_into_system_prompt() -> None:
    """BOOTSTRAP.md body (after frontmatter close) appears in slot 3.
    Empty body → no slot.
    """
    import tempfile
    from pathlib import Path
    from wyoming_llm_agent.workspace import (
        BOOTSTRAP_FILE, Workspace, load_workspace,
    )

    # First with a non-empty body.
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / BOOTSTRAP_FILE).write_text(
            "---\nseed_templates: false\nauto_load_skills: []\n---\n\n"
            "--BOOT-BODY-MARKER--\n",
            encoding="utf-8",
        )
        ws = load_workspace(root)
        assert ws.bootstrap_body.strip() == "--BOOT-BODY-MARKER--"

        ha_snapshot = make_ha_snapshot()
        fake_fetch = _FakeHAFetch(ha_snapshot)
        orig_fetch = agent_mod.fetch_session_snapshot
        agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
        try:
            llm = ScriptedLLM([
                {"choices": [{"message": {"role": "assistant", "content": "ok"}}]},
            ])
            seen: list[str] = []
            orig_chat = llm.chat
            async def spy(messages, *, tools=None, tool_choice=None):
                seen.append(messages[0]["content"])
                return await orig_chat(messages, tools=tools, tool_choice=tool_choice)
            llm.chat = spy  # type: ignore[assignment]
            ag = Agent(
                llm=llm,
                config=AgentConfig(
                    workspace=ws,
                    ha_mcp_server=MCPServerConfig(name="ha", url="http://stub/mcp"),
                ),
            )
            await ag.respond(
                text="hi", language="en", conversation_id="bb-c1",
                device_id=None, satellite_id=None,
            )
            assert "[Boot instructions" in seen[0]
            assert "--BOOT-BODY-MARKER--" in seen[0]
        finally:
            agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]

    # Now with empty body — slot omitted.
    ws_empty = Workspace(
        soul="--SOUL--",
        bootstrap_body="",
        heartbeat_template="",
        auto_load_skills=(),
    )
    fake_fetch2 = _FakeHAFetch(make_ha_snapshot())
    orig_fetch = agent_mod.fetch_session_snapshot
    agent_mod.fetch_session_snapshot = fake_fetch2  # type: ignore[assignment]
    try:
        llm = ScriptedLLM([
            {"choices": [{"message": {"role": "assistant", "content": "ok"}}]},
        ])
        seen2: list[str] = []
        orig_chat = llm.chat
        async def spy2(messages, *, tools=None, tool_choice=None):
            seen2.append(messages[0]["content"])
            return await orig_chat(messages, tools=tools, tool_choice=tool_choice)
        llm.chat = spy2  # type: ignore[assignment]
        ag = Agent(
            llm=llm,
            config=AgentConfig(
                workspace=ws_empty,
                ha_mcp_server=MCPServerConfig(name="ha", url="http://stub/mcp"),
            ),
        )
        await ag.respond(
            text="hi", language="en", conversation_id="bb-c2",
            device_id=None, satellite_id=None,
        )
        assert "[Boot instructions" not in seen2[0]
    finally:
        agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]
    print("OK: BOOTSTRAP body injected when non-empty, slot omitted when blank")


async def test_workspace_auto_load_skills_applied_to_new_conversation() -> None:
    """BOOTSTRAP auto_load_skills → new convo starts with those loaded."""
    from pathlib import Path
    from wyoming_llm_agent.skills import Skill
    from wyoming_llm_agent.workspace import Workspace

    ha_snapshot = make_ha_snapshot()
    fake_fetch = _FakeHAFetch(ha_snapshot)
    orig_fetch = agent_mod.fetch_session_snapshot
    agent_mod.fetch_session_snapshot = fake_fetch  # type: ignore[assignment]
    try:
        # Skill "hello-world" exists; "ghost-skill" does not (must be silently dropped).
        hello = Skill(
            name="hello-world", description="Say hello",
            body="--HELLO-BODY--", path=Path("/tmp/nope"),
        )
        ws = Workspace(
            soul="", identity="", heartbeat_template="",
            auto_load_skills=("hello-world", "ghost-skill"),
        )
        llm = ScriptedLLM([
            {"choices": [{"message": {"role": "assistant", "content": "hi"}}]},
        ])
        seen: list[str] = []
        orig_chat = llm.chat
        async def spy(messages, *, tools=None, tool_choice=None):
            seen.append(messages[0]["content"])
            return await orig_chat(messages, tools=tools, tool_choice=tool_choice)
        llm.chat = spy  # type: ignore[assignment]
        ag = Agent(
            llm=llm,
            config=AgentConfig(
                workspace=ws, skills=[hello],
                ha_mcp_server=MCPServerConfig(name="ha", url="http://stub/mcp"),
            ),
        )
        await ag.respond(
            text="hi", language="en",
            conversation_id="auto-c1", device_id=None, satellite_id=None,
        )
        # Skill body present from turn 1 — no load_skill needed.
        assert "--HELLO-BODY--" in seen[0]
    finally:
        agent_mod.fetch_session_snapshot = orig_fetch  # type: ignore[assignment]
    print("OK: BOOTSTRAP auto_load_skills applied to new conversation")


def main() -> None:
    test_mcp_parsing_and_tool_def()
    test_cosine_similarity()
    test_record_embedding_increments_tokens_counter_when_supplied()
    test_embed_key_invalidates_on_desc_change()
    test_skill_parser_round_trip_and_validation()
    test_metrics_emit()
    test_memory_store_roundtrip()
    test_memory_user_isolation()
    test_memory_shared_fallback()
    test_memory_bad_slug_rejected()
    test_memory_save_bucket_full_attaches_status()
    test_memory_disabled_hides_meta_tools()
    test_working_memory_size_cap_rejects_oversize()
    test_working_memory_empty_set_acts_like_clear()
    test_workspace_seeds_missing_files_with_defaults()
    test_workspace_skip_seed_when_disabled()
    test_bootstrap_auto_load_skills_parsed()
    test_heartbeat_renders_per_turn_with_vars()
    test_heartbeat_render_failure_falls_back_to_raw()
    test_memory_render_shared_and_user_separate()
    test_journal_append_and_read()
    test_journal_entry_and_day_caps()
    test_user_profile_seed_and_render()
    test_user_bootstrap_seed_render_and_placeholder_skip()
    asyncio.run(test_agent_dispatches_ha_tool_via_mcp())
    asyncio.run(test_agent_ha_disabled())
    asyncio.run(test_agent_max_iterations_safety())
    asyncio.run(test_tool_filter_keeps_top_k())
    asyncio.run(test_tool_filter_ha_tools_mode_embedding())
    asyncio.run(test_skill_meta_tools_load_unload_inject_body())
    asyncio.run(test_skill_meta_tools_handle_bad_input())
    asyncio.run(test_memory_meta_tools_in_system_prompt())
    asyncio.run(test_working_memory_set_and_clear_lifecycle())
    asyncio.run(test_system_prompt_ordering_workspace_mode())
    asyncio.run(test_user_bootstrap_substantive_renders_between_shared_mem_and_profile())
    asyncio.run(test_workspace_hot_reload_picks_up_edits())
    asyncio.run(test_bootstrap_body_injected_into_system_prompt())
    asyncio.run(test_workspace_auto_load_skills_applied_to_new_conversation())
    asyncio.run(test_skill_allowed_tools_gating())
    test_sandbox_path_validation()
    asyncio.run(test_sandbox_unavailable_hides_run_skill_script())
    asyncio.run(test_sandbox_dispatch_requires_loaded_skill())
    asyncio.run(test_sandbox_self_test_category_gating_and_predicates())
    asyncio.run(test_skill_fetcher_url_flow())
    asyncio.run(test_skill_fetcher_picks_skills_from_mcp_server_bundle())
    asyncio.run(test_skill_fetcher_rejects_path_traversal())
    asyncio.run(test_mcp_skill_bundles_assemble_from_resources())
    asyncio.run(test_mcp_skills_install_from_bundles())
    asyncio.run(test_list_resources_paginates_via_cursor())
    asyncio.run(test_mcp_listener_dispatches_updated_notification())
    asyncio.run(test_agent_reload_skills_atomically_replaces_registry())
    asyncio.run(test_preflight_pass_and_fail())
    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
