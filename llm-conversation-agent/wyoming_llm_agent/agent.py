"""Agent loop: Transcript → fetch HA tools+prompt + cached MCP/custom →
LLM → dispatch tool calls → loop → reply.

The agent owns no HA-specific code. The Home Assistant side is
delegated to HA's built-in `mcp_server` integration (Streamable HTTP).
Each turn we fetch a fresh `tools/list` + `prompts/get("Assist")` from
HA — so newly exposed entities and updated state appear without
restarting the addon. Static external MCP servers (memory, vector
search, etc.) keep using the discovery-at-startup cache.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

from .const import (
    CONVERSATION_TTL_SECONDS,
    DEFAULT_HA_TOOLS_MODE,
    DEFAULT_HISTORY_TURNS,
    DEFAULT_MAX_TOOL_ITERATIONS,
    HA_TOOLS_MODE_EMBEDDING,
    META_TOOL_LIST_SKILLS,
    META_TOOL_LOAD_SKILL,
    META_TOOL_MEMORY_DELETE,
    META_TOOL_MEMORY_READ,
    META_TOOL_MEMORY_SAVE,
    META_TOOL_MEMORY_STATUS,
    META_TOOL_JOURNAL_APPEND,
    META_TOOL_LOAD_JOURNAL_DAY,
    META_TOOL_NAMES,
    META_TOOL_RUN_SKILL_SCRIPT,
    META_TOOL_UNLOAD_SKILL,
    META_TOOL_WORKING_MEMORY_CLEAR,
    META_TOOL_WORKING_MEMORY_SET,
)
from .sandbox import SandboxError, run_sandboxed_script
from .embedding import EmbeddingClient, cosine_similarity
from .llm import LLMClient
from .mcp_client import (
    MCPServerConfig,
    MCPToolRef,
    build_mcp_tools,
    dispatch_mcp_tool,
    fetch_session_snapshot,
)
from .memory import (
    MemoryBucketFullError,
    MemoryError as MemoryStoreError,
    MemoryStore,
)
from .metrics import (
    record_tool_call,
    record_turn,
    set_active_conversations,
    set_loaded_skills,
)
from .skills import Skill
from .workspace import (
    Workspace,
    load_workspace,
    render_heartbeat,
    stat_workspace,
)

_LOGGER = logging.getLogger(__name__)

# HA's mcp_server exposes one prompt named after its LLM API ("Assist").
HA_PROMPT_NAME = "Assist"

# Hard cap on the per-conversation working-memory buffer (R3 slot 9).
# Working memory is in-context, so every byte goes through the LLM
# every turn until cleared — keep it tight.
MAX_WORKING_MEMORY_BYTES = 8 * 1024


def _embed_key(name: str, description: str) -> str:
    """Embedding-cache key. Description hash → automatic invalidation when
    an entity is renamed/redescribed in HA; no manual cache reload needed.
    16 hex chars (64 bits) makes collisions vanishingly unlikely.
    """
    h = hashlib.sha256((description or "").encode("utf-8")).hexdigest()[:16]
    return f"{name}:{h}"


@dataclass
class AgentConfig:
    max_tool_iterations: int = DEFAULT_MAX_TOOL_ITERATIONS
    history_turns: int = DEFAULT_HISTORY_TURNS
    # Static MCP server tools, discovered once at startup.
    mcp_tools: list[MCPToolRef] = field(default_factory=list)
    # HA mcp_server config — fetched per turn so HA state stays fresh.
    # None disables HA delegation entirely (e.g. running outside an addon).
    ha_mcp_server: MCPServerConfig | None = None
    tool_filter_top_k: int = 0
    # How HA mcp_server tools interact with the embedding filter.
    # See const.HA_TOOLS_MODE_* for semantics.
    ha_tools_mode: str = DEFAULT_HA_TOOLS_MODE
    # agentskills.io-format Skills loaded at startup. PR2 only registers
    # them; PR3 will expose list_skills/load_skill meta-tools so the LLM
    # can pull SKILL.md instructions + allowed-tools on demand.
    skills: list[Skill] = field(default_factory=list)
    # Per-user persistent memory store. None disables the memory meta-
    # tools entirely (LLM never sees memory_save/read/delete and the
    # MEMORY.md index is not injected into the system prompt).
    memory_store: MemoryStore | None = None
    # Workspace (SOUL/IDENTITY/HEARTBEAT/USER + auto-load list).
    # Always present. When `/config/` is unmounted or all files are
    # absent, the instance has empty strings — the agent then just
    # skips the corresponding system-prompt slots.
    workspace: Workspace = field(default_factory=Workspace)
    # Verify TLS certs on outbound HTTP. MCP servers carry their own verify
    # setting (passed through the httpx_client_factory at session-open time).
    verify_ssl: bool = True


@dataclass
class _Conversation:
    messages: list[dict[str, Any]] = field(default_factory=list)
    last_used: float = field(default_factory=time.monotonic)
    # Skill names activated for this conversation. Their SKILL.md bodies
    # are appended to the system message every turn until unload_skill
    # is called or the conversation is evicted. Per agentskills.io
    # progressive disclosure: metadata always visible, body lazy.
    loaded_skills: set[str] = field(default_factory=set)
    # Working memory (R3 slot 9). In-context per-conversation scratchpad
    # the LLM curates via `working_memory_set` / `working_memory_clear`.
    # Persists across turns of the same conversation; dies on eviction.
    working_memory: str = ""


@dataclass
class AgentResult:
    handled: bool
    text: str


@dataclass
class _SystemContext:
    """Turn-stable inputs to `_compose_system`. Passed into the LLM loop
    so we can rebuild `messages[0]` after a meta-tool call mutates
    `convo.loaded_skills` — the very next round-trip in the same user
    turn then sees the loaded skill's body.

    `user_id` selects the per-user memory bucket. None routes to the
    `shared` bucket — used on HA <2026.6.0 where the Transcript context
    does not yet deliver user_id.
    """
    ha_prompt: str | None
    language: str | None
    device_id: str | None
    satellite_id: str | None
    conversation_id: str | None
    user_id: str | None


@dataclass
class _TurnContext:
    """Turn-stable inputs that the loop needs in order to rebuild the
    `tools:` array after a meta-tool call changes `convo.loaded_skills`.
    The previous turn's tool list becomes stale (PR4 gating exposes
    `allowed_tools` of the just-loaded skill and hides the rest), so the
    next round-trip re-runs `_filter_tools` with fresh gating sets.
    """
    ha_tools: list[dict[str, Any]]
    other_tools: list[dict[str, Any]]
    query: str
    system_ctx: _SystemContext


class Agent:
    def __init__(
        self,
        *,
        llm: LLMClient,
        config: AgentConfig,
        embedding_client: EmbeddingClient | None = None,
    ) -> None:
        self.llm = llm
        self.config = config
        self._embedding_client = embedding_client
        self._tool_embeddings: dict[str, list[float]] = {}
        # Jinja2 sandbox for HEARTBEAT.md rendering. SandboxedEnvironment
        # blocks attribute access on unsafe types so a malformed template
        # can't escape into the host. StrictUndefined surfaces typos
        # (`{{ devicd_id }}`) at render time so we fall through to the
        # raw text + WARNING instead of silently emitting empty strings.
        # trim/lstrip blocks make `{% if %}` formatting predictable.
        self._jinja_env = SandboxedEnvironment(
            autoescape=False,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # Dispatch lookup tables.
        self._mcp_by_name: dict[str, MCPToolRef] = {
            ref.openai_name: ref for ref in config.mcp_tools
        }
        # HA mcp_server's tool set is refreshed per turn; populated by
        # `_fetch_ha_snapshot()` before dispatch.
        self._ha_tools_by_name: dict[str, MCPToolRef] = {}
        # In-memory per-conversation history.
        self._conversations: dict[str, _Conversation] = {}
        # Skill registry by name (PR2: registered only; PR3 wires meta-tools).
        self._skills_by_name: dict[str, Skill] = {s.name: s for s in config.skills}
        set_loaded_skills(len(self._skills_by_name))
        # Per-user persistent memory. None → memory meta-tools hidden,
        # MEMORY.md index not injected.
        self._memory_store: MemoryStore | None = config.memory_store
        # Workspace (R3) — always present, may have empty fields when
        # /config/ files are absent. Drives SOUL/IDENTITY/HEARTBEAT and
        # auto-loaded skills.
        self._workspace: Workspace = config.workspace
        # Skill names every new conversation auto-loads. Resolved
        # against `_skills_by_name` at conversation-creation time, so
        # unknown names are silently skipped without erroring.
        self._auto_load_skills: frozenset[str] = frozenset(
            config.workspace.auto_load_skills,
        )
        # Workspace file mtimes for hot reload. Populated lazily on the
        # first `respond()` so tests that pass an in-memory Workspace
        # (root=None) don't trigger any I/O.
        self._workspace_mtimes: dict[str, float] = {}
        # Probe result set by __main__ before respond() ever runs. When
        # False, run_skill_script is hidden from _meta_tool_defs() — LLM
        # never sees a tool that can't actually execute. Other skill
        # features (instructions, allowed-tools gating) still work.
        self.sandbox_available: bool = False

    async def aclose(self) -> None:
        if self._embedding_client is not None:
            await self._embedding_client.aclose()

    def reload_skills(self, skills_dir: str | None = None) -> int:
        """Re-scan the skills directory and atomically replace the registry.

        Triggered by the MCP listener after a `resources/updated` or
        `resources/list_changed` from an external server. Active
        conversations keep their `loaded_skills` set; entries that now
        point at a removed skill are pruned. Returns the new skill count.
        """
        from .skills import load_skills_dir
        if skills_dir is None:
            # If reload is called without a dir, no-op — caller should pass
            # the same value used at startup.
            return len(self._skills_by_name)
        skills = load_skills_dir(skills_dir)
        new_registry = {s.name: s for s in skills}
        prev_names = set(self._skills_by_name)
        self._skills_by_name = new_registry
        set_loaded_skills(len(self._skills_by_name))
        # Prune stale loaded_skills entries in active conversations.
        removed = prev_names - set(new_registry)
        if removed:
            for convo in self._conversations.values():
                convo.loaded_skills -= removed
        _LOGGER.info(
            "Skill registry reloaded: %d skill(s) registered (added: %s, removed: %s)",
            len(self._skills_by_name),
            ", ".join(sorted(set(new_registry) - prev_names)) or "—",
            ", ".join(sorted(removed)) or "—",
        )
        return len(self._skills_by_name)

    async def warmup_embeddings(self) -> None:
        """Pre-embed every known tool's "<name>: <description>" string.

        External MCP tools come from startup config and never change at
        runtime. HA mcp_server tools are fetched per turn, but when
        `ha_tools_mode == "embedding"` we best-effort pre-warm them too
        so the first turn doesn't pay the embedding latency. If HA
        isn't reachable at startup (e.g. addon booted before HA), we
        log and fall through — `_filter_tools` will lazy-fill on demand.

        Cache keys include a description hash, so HA renaming or
        redescribing an entity invalidates cleanly without a manual reload.
        """
        if self._embedding_client is None or self.config.tool_filter_top_k <= 0:
            return

        # Static tools — always succeeds, no network beyond the embedding call.
        static_entries: list[tuple[str, str]] = []  # (cache_key, "name: desc")
        for ref in self.config.mcp_tools:
            key = _embed_key(ref.openai_name, ref.description)
            static_entries.append((key, f"{ref.openai_name}: {ref.description}"))

        if static_entries:
            try:
                vectors = await self._embedding_client.embed(
                    [text for _, text in static_entries],
                )
                for (key, _), vec in zip(static_entries, vectors):
                    self._tool_embeddings[key] = vec
                _LOGGER.info(
                    "Embedded %d static tool description(s) for top-K=%d filtering.",
                    len(static_entries), self.config.tool_filter_top_k,
                )
            except Exception as exc:  # noqa: BLE001
                _LOGGER.error(
                    "Static tool embedding warmup failed (%s: %s); "
                    "top-K filtering will fall back to include-all this run.",
                    type(exc).__name__, exc,
                )

        # HA tool pre-warm — only when caller enabled embedding mode for them.
        # Best-effort: missing HA on startup falls through to lazy-fill.
        if (
            self.config.ha_tools_mode == HA_TOOLS_MODE_EMBEDDING
            and self.config.ha_mcp_server is not None
        ):
            await self._prewarm_ha_embeddings()

    async def _prewarm_ha_embeddings(self) -> None:
        """One-shot HA mcp_server fetch + embed. Failures are non-fatal."""
        try:
            ha_snapshot = await fetch_session_snapshot(
                self.config.ha_mcp_server, prompt_name=None,
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.info(
                "HA mcp_server pre-warm skipped (%s: %s); "
                "embedding cache will lazy-fill on the first turn.",
                type(exc).__name__, exc,
            )
            return
        if not ha_snapshot.tools:
            _LOGGER.info(
                "HA mcp_server returned no tools at pre-warm; "
                "embedding cache will lazy-fill once entities are exposed.",
            )
            return
        try:
            texts = [
                f"{ref.openai_name}: {ref.description}"
                for ref in ha_snapshot.tools
            ]
            vectors = await self._embedding_client.embed(texts)
            for ref, vec in zip(ha_snapshot.tools, vectors):
                key = _embed_key(ref.openai_name, ref.description)
                self._tool_embeddings[key] = vec
            _LOGGER.info(
                "Pre-warmed %d HA mcp_server tool embedding(s) "
                "(ha_tools_mode=embedding).",
                len(ha_snapshot.tools),
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning(
                "HA tool embedding batch failed (%s: %s); "
                "will lazy-fill per turn.",
                type(exc).__name__, exc,
            )

    async def respond(
        self,
        *,
        text: str,
        language: str | None,
        conversation_id: str | None,
        device_id: str | None,
        satellite_id: str | None,
        user_id: str | None = None,
    ) -> AgentResult:
        """Run one turn — accumulate the full reply before returning."""
        turn_start = monotonic()
        # 1. Fetch a fresh HA mcp_server snapshot (tools + prompt).
        ha_snapshot = await self._fetch_ha_snapshot()
        self._ha_tools_by_name = {ref.openai_name: ref for ref in ha_snapshot.tools}

        # 1a. Hot reload — pick up edits to SOUL/IDENTITY/HEARTBEAT/
        # BOOTSTRAP without an addon restart.
        self._maybe_reload_workspace()

        # 2. Compose the message list. SystemContext captures everything
        # the system message depends on so the loop can rebuild it after
        # a meta-tool mutates `convo.loaded_skills` or the memory index.
        convo_key = conversation_id or device_id or satellite_id or "default"
        convo = self._get_conversation(convo_key)
        system_ctx = _SystemContext(
            ha_prompt=ha_snapshot.prompt_text,
            language=language,
            device_id=device_id,
            satellite_id=satellite_id,
            conversation_id=conversation_id,
            user_id=user_id,
        )
        system_msg = self._compose_system_from_ctx(system_ctx, convo)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_msg},
            *convo.messages,
            {"role": "user", "content": text},
        ]

        # 3. Build the tool list. HA mcp_server tools come fresh; everything
        # else comes from startup caches. Meta tools (list_skills /
        # load_skill / unload_skill) join `other_tools` and bypass the
        # embedding filter because they're always-on and tiny.
        ha_tools = build_mcp_tools(ha_snapshot.tools)
        mcp_tool_defs = build_mcp_tools(self.config.mcp_tools)
        meta_tools = self._meta_tool_defs()
        other_tools = mcp_tool_defs + meta_tools
        _LOGGER.debug(
            "Tool registry for this turn: %d HA mcp_server (%s), "
            "%d external MCP (%s), %d meta (%s)",
            len(ha_tools), ", ".join(t["function"]["name"] for t in ha_tools),
            len(mcp_tool_defs), ", ".join(t["function"]["name"] for t in mcp_tool_defs),
            len(meta_tools), ", ".join(t["function"]["name"] for t in meta_tools),
        )
        turn_ctx = _TurnContext(
            ha_tools=ha_tools, other_tools=other_tools,
            query=text, system_ctx=system_ctx,
        )
        tools = await self._recompute_tools(turn_ctx, convo)

        # 4. LLM loop.
        final_text, completed = await self._run_loop_blocking(
            messages, tools, convo=convo, turn_ctx=turn_ctx,
        )

        if not completed:
            _LOGGER.warning(
                "Agent hit max_tool_iterations=%d without a final reply",
                self.config.max_tool_iterations,
            )
            final_text = (
                "I'm having trouble completing that — too many tool calls in a row. "
                "Try rephrasing the request."
            )

        if completed:
            convo.messages.append({"role": "user", "content": text})
            if final_text:
                convo.messages.append({"role": "assistant", "content": final_text})
            self._trim_history(convo)
        self._evict_stale()
        set_active_conversations(len(self._conversations))

        handled = completed and bool(final_text)
        record_turn(language, handled=handled, duration_s=monotonic() - turn_start)
        return AgentResult(
            handled=handled,
            text=final_text or "I couldn't generate a reply.",
        )

    # ---- internals --------------------------------------------------------

    def _maybe_reload_workspace(self) -> bool:
        """Stat the 4 workspace files; if any mtime changed since the
        last check, re-call `load_workspace()` and replace the cached
        Workspace + auto_load_skills. Returns True iff a reload happened.

        No-op when the Workspace was constructed without a root (tests
        / in-memory use). Failures during reload are logged and leave
        the previous Workspace in place — the addon never falls into
        an empty-workspace state because of a transient stat error.
        """
        root = self._workspace.root
        if root is None:
            return False
        try:
            mtimes = stat_workspace(root)
        except Exception as exc:  # noqa: BLE001 — never crash on stat
            _LOGGER.warning("Workspace stat failed (%s); skipping reload", exc)
            return False
        if mtimes == self._workspace_mtimes:
            return False
        # First-turn population vs. real change is distinguishable by
        # the empty cache; either way we (re-)load.
        first_check = not self._workspace_mtimes
        self._workspace_mtimes = mtimes
        if first_check:
            return False
        try:
            new_ws = load_workspace(root)
        except Exception as exc:  # noqa: BLE001 — never crash on reload
            _LOGGER.warning(
                "Workspace reload failed (%s); keeping previous content", exc,
            )
            return False
        self._workspace = new_ws
        self._auto_load_skills = frozenset(new_ws.auto_load_skills)
        _LOGGER.info(
            "Workspace hot-reloaded: SOUL=%d, IDENTITY=%d, "
            "BOOTSTRAP body=%d, HEARTBEAT=%d, auto_load_skills=%s",
            len(new_ws.soul), len(new_ws.identity),
            len(new_ws.bootstrap_body), len(new_ws.heartbeat_template),
            ", ".join(new_ws.auto_load_skills) or "—",
        )
        return True

    async def _fetch_ha_snapshot(self):
        """Open one MCP session to HA, return tools + prompt. Empty on failure
        — the LLM still gets external MCP / custom tools.
        """
        from .mcp_client import MCPSessionSnapshot
        if self.config.ha_mcp_server is None:
            return MCPSessionSnapshot(tools=[], prompt_text=None)
        return await fetch_session_snapshot(
            self.config.ha_mcp_server, prompt_name=HA_PROMPT_NAME,
        )

    def _compose_system(
        self,
        ha_prompt: str | None,
        *,
        language: str | None,
        device_id: str | None,
        satellite_id: str | None,
        conversation_id: str | None,
        loaded_skills: set[str] | None = None,
        user_id: str | None = None,
        working_memory: str = "",
    ) -> str:
        """R3 12-section system prompt, ordered by mutation frequency
        (lowest → highest) so the upstream prompt cache hits as much
        prefix as possible. Per-user sections are grouped together at
        the tail of the shared-content prefix so cross-user cache
        sharing maxes out through the Skill catalog + shared MEMORY:

            [1]  SOUL              cache-stable until deploy
            [2]  IDENTITY          rare (reconfig)
            [3]  BOOTSTRAP body    LLM boot instructions; user-edited
            [4]  HA api_prompt     entity add/remove only
            [5]  Skill catalog     skill reload only
            [6]  shared MEMORY     any household member saves shared
            [7]  user BOOTSTRAP    per-user behavior nudges; rare edit
            [8]  USER profile      manual edit of this user's USER.md
            [9]  user MEMORY       this user saves
            [10] Active skill body conversation load_skill
            [11] Working memory    per-conversation scratchpad
            [12] HEARTBEAT         per turn (date/time/language/device)

        Slot 3 is emitted only when `Workspace.bootstrap_body` is
        non-empty; the user blanks the body when boot instructions are
        no longer needed. Slot 7 is omitted when the user's
        BOOTSTRAP.md is missing, unsafe, or still the seeded
        placeholder. Slot 11 is similarly skipped when the convo's
        `working_memory` buffer is empty.
        """
        ws = self._workspace
        parts: list[str] = []

        # Seed-on-first-encounter: when the user_id is known and safe,
        # make sure their USER.md profile + BOOTSTRAP.md placeholder
        # both exist so a fresh household member has editable files
        # from turn 1. Idempotent.
        if self._memory_store is not None:
            try:
                self._memory_store.ensure_user_profile_seeded(user_id)
            except MemoryStoreError as exc:
                _LOGGER.warning("USER.md seed failed: %s", exc)
            try:
                self._memory_store.ensure_user_bootstrap_seeded(user_id)
            except MemoryStoreError as exc:
                _LOGGER.warning("user BOOTSTRAP.md seed failed: %s", exc)

        # [1] SOUL
        if ws.soul:
            parts.append(ws.soul)
        # [2] IDENTITY
        if ws.identity:
            parts.append(ws.identity)
        # [3] BOOTSTRAP body (boot instructions for the LLM; blanked by
        # the user when no longer needed)
        if ws.bootstrap_body:
            parts.append(
                "[Boot instructions — follow these and ask the user to "
                "clear this section once they no longer apply]\n"
                + ws.bootstrap_body,
            )
        # [4] HA api_prompt
        if ha_prompt:
            parts.append(ha_prompt)
        # [5] Skill catalog
        if self._skills_by_name:
            lines = [
                "Available skills (call load_skill to activate when relevant):",
            ]
            for skill in sorted(self._skills_by_name.values(),
                                key=lambda s: s.name):
                lines.append(f"- {skill.name}: {skill.description}")
            parts.append("\n".join(lines))
        # [6] shared MEMORY index
        if self._memory_store is not None:
            try:
                shared_block = self._memory_store.render_shared_index()
            except MemoryStoreError as exc:
                _LOGGER.warning("memory render_shared_index failed: %s", exc)
                shared_block = ""
            if shared_block:
                parts.append(shared_block)
            # [7] Per-user BOOTSTRAP (behavior nudges scoped to this
            # user; placed before USER profile because edits to it are
            # even rarer than the profile)
            try:
                user_bootstrap = self._memory_store.render_user_bootstrap(user_id)
            except MemoryStoreError as exc:
                _LOGGER.warning(
                    "memory render_user_bootstrap failed: %s", exc,
                )
                user_bootstrap = ""
            if user_bootstrap:
                parts.append(user_bootstrap)
            # [8] USER profile (per-user free-form profile)
            try:
                user_profile = self._memory_store.render_user_profile(user_id)
            except MemoryStoreError as exc:
                _LOGGER.warning("memory render_user_profile failed: %s", exc)
                user_profile = ""
            if user_profile:
                parts.append(user_profile)
            # [9] user MEMORY index
            try:
                user_block = self._memory_store.render_user_index(user_id)
            except MemoryStoreError as exc:
                _LOGGER.warning("memory render_user_index failed: %s", exc)
                user_block = ""
            if user_block:
                parts.append(user_block)
        # [10] Active skill bodies
        if loaded_skills:
            for name in sorted(loaded_skills):
                skill = self._skills_by_name.get(name)
                if skill is None:
                    continue
                parts.append(f"[Active skill: {skill.name}]\n{skill.body}")
        # [11] Working memory (per-conversation scratchpad)
        if working_memory:
            parts.append(
                "[Working memory for this conversation]\n" + working_memory,
            )
        # [12] HEARTBEAT
        heartbeat = render_heartbeat(
            self._jinja_env, ws.heartbeat_template,
            language=language,
            device_id=device_id,
            satellite_id=satellite_id,
            conversation_id=conversation_id,
            user_id=user_id,
        )
        if heartbeat:
            parts.append(heartbeat)

        return "\n\n".join(parts)

    def _compute_skill_tool_gating(
        self, all_tool_names: list[str], loaded_skills: set[str],
    ) -> tuple[set[str], set[str]]:
        """Compute the (force_include, hidden) sets for this turn.

        * `force_include`: tool names matching any pattern in any LOADED
          skill's `allowed_tools`. These are guaranteed to appear in
          the per-turn `tools:` array regardless of embedding score.
        * `hidden`: tool names matching some registered skill's
          `allowed_tools` BUT no loaded skill's. These are "owned by
          an inactive skill" — kept out of the `tools:` array until the
          owning skill is loaded. Real lazy disclosure.

        Patterns are `fnmatch` (`*`, `?`, `[seq]`). Meta tools
        (`list_skills`, etc.) are never hidden, even if a pathological
        pattern matches them — they're the LLM's only way to activate
        skills in the first place.
        """
        if not self._skills_by_name:
            return set(), set()

        loaded_patterns: list[str] = []
        all_patterns: list[str] = []
        for skill in self._skills_by_name.values():
            patterns = skill.allowed_tools
            if not patterns:
                continue
            all_patterns.extend(patterns)
            if skill.name in loaded_skills:
                loaded_patterns.extend(patterns)

        if not all_patterns:
            return set(), set()

        force_include: set[str] = set()
        hidden: set[str] = set()
        for name in all_tool_names:
            if name in META_TOOL_NAMES:
                continue
            if any(fnmatch.fnmatchcase(name, p) for p in loaded_patterns):
                force_include.add(name)
            elif any(fnmatch.fnmatchcase(name, p) for p in all_patterns):
                hidden.add(name)
        return force_include, hidden

    async def _recompute_tools(
        self, turn_ctx: _TurnContext, convo: _Conversation,
    ) -> list[dict[str, Any]]:
        """Rebuild the per-turn tools array, applying skill gating against
        the current `convo.loaded_skills`. Called once per user turn,
        plus once after every meta-tool call that mutates loaded skills.
        """
        all_names = [
            t["function"]["name"]
            for t in turn_ctx.ha_tools + turn_ctx.other_tools
        ]
        force_include, hidden = self._compute_skill_tool_gating(
            all_names, convo.loaded_skills,
        )
        return await self._filter_tools(
            ha_tools=turn_ctx.ha_tools,
            other_tools=turn_ctx.other_tools,
            query=turn_ctx.query,
            skill_force_include=force_include,
            skill_hidden=hidden,
        )

    def _compose_system_from_ctx(
        self, ctx: _SystemContext, convo: _Conversation,
    ) -> str:
        """Convenience wrapper: rebuild system message from cached turn
        context + current `loaded_skills`. Used by `respond()` once at
        the start of the turn and by the loop after each meta-tool call.
        """
        return self._compose_system(
            ctx.ha_prompt,
            language=ctx.language,
            device_id=ctx.device_id,
            satellite_id=ctx.satellite_id,
            conversation_id=ctx.conversation_id,
            loaded_skills=convo.loaded_skills,
            user_id=ctx.user_id,
            working_memory=convo.working_memory,
        )

    def _meta_tool_defs(self) -> list[dict[str, Any]]:
        """OpenAI function-calling schemas for all meta tools.

        Always exposed (bypass the embedding filter via the always-in
        path in `_filter_tools`). Sections are gated so the LLM never
        sees a meta-tool that can't actually do anything:
        - Skill meta-tools require at least one registered skill.
        - `run_skill_script` additionally requires a working sandbox.
        - Memory meta-tools require a configured MemoryStore.
        - Working-memory meta-tools have no dependency — they live
          inside `_Conversation` so they always work.
        """
        defs: list[dict[str, Any]] = []
        if self._skills_by_name:
            defs.extend(self._skill_meta_tool_defs())
        if self._memory_store is not None:
            defs.extend(self._memory_meta_tool_defs())
        defs.extend(self._working_memory_meta_tool_defs())
        return defs

    def _skill_meta_tool_defs(self) -> list[dict[str, Any]]:
        defs: list[dict[str, Any]] = [
            {
                "type": "function",
                "function": {
                    "name": META_TOOL_LIST_SKILLS,
                    "description": (
                        "List all registered skills (name + description) and "
                        "which are currently loaded. The system prompt already "
                        "shows the same list — call this only if you need to "
                        "re-check the loaded state mid-turn."
                    ),
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": META_TOOL_LOAD_SKILL,
                    "description": (
                        "Activate a skill for this conversation. Its full "
                        "instructions are added to your context starting from "
                        "the next round-trip in this same user turn. Call when "
                        "the user's request matches a skill description."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Exact skill name from the available list.",
                            },
                        },
                        "required": ["name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": META_TOOL_UNLOAD_SKILL,
                    "description": (
                        "Deactivate a previously loaded skill. Its instructions "
                        "leave the context window from the next round-trip. "
                        "Use when switching task domains."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                        },
                        "required": ["name"],
                    },
                },
            },
        ]
        if not self.sandbox_available:
            return defs
        defs.append({
                "type": "function",
                "function": {
                    "name": META_TOOL_RUN_SKILL_SCRIPT,
                    "description": (
                        "Run a Python script bundled inside a LOADED skill's "
                        "directory. Returns stdout, stderr, exit_code, "
                        "timed_out. The script runs in a bubblewrap sandbox: "
                        "no network, no host filesystem access outside the "
                        "skill dir, no credentials, 10s timeout, 200MB memory. "
                        "Use only when the skill's SKILL.md says to run a "
                        "specific script."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "skill_name": {
                                "type": "string",
                                "description": "Name of a currently LOADED skill.",
                            },
                            "script_path": {
                                "type": "string",
                                "description": (
                                    "Path relative to the skill dir, e.g. "
                                    "'scripts/extract.py'. Must end in .py, "
                                    "no '..' segments."
                                ),
                            },
                            "args": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Command-line arguments to the script.",
                            },
                            "stdin": {
                                "type": "string",
                                "description": "Optional stdin text (max 1MB).",
                            },
                        },
                        "required": ["skill_name", "script_path"],
                    },
                },
            })
        return defs

    def _memory_meta_tool_defs(self) -> list[dict[str, Any]]:
        """Persistent-memory meta tools. Wired only when MemoryStore is
        configured. Per-call user_id comes from the Transcript context
        (`_SystemContext.user_id`); the LLM never names a user — it
        just sees "this user" (or shared, when HA hasn't delivered an
        id yet).
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": META_TOOL_MEMORY_SAVE,
                    "description": (
                        "Persist a fact about this user across conversations. "
                        "Overwrites any prior entry with the same slug. The "
                        "system prompt already shows existing slugs + their "
                        "one-line descriptions. Use when the user shares a "
                        "lasting preference, name, schedule, or context worth "
                        "remembering next time."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "slug": {
                                "type": "string",
                                "description": (
                                    "Stable identifier, lowercase + digits + "
                                    "hyphens, 1-64 chars (e.g. 'dog-name', "
                                    "'work-schedule')."
                                ),
                            },
                            "description": {
                                "type": "string",
                                "description": (
                                    "Single-line summary shown in the index. "
                                    "≤200 chars."
                                ),
                            },
                            "body": {
                                "type": "string",
                                "description": (
                                    "Full markdown content to remember. ≤32KB."
                                ),
                            },
                        },
                        "required": ["slug", "description", "body"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": META_TOOL_MEMORY_READ,
                    "description": (
                        "Load the full body of a persisted memory. The system "
                        "prompt only shows one-line descriptions; call this "
                        "when you need the details. Omit `slug` to receive "
                        "the index instead."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "slug": {
                                "type": "string",
                                "description": "Slug from the memory index.",
                            },
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": META_TOOL_MEMORY_DELETE,
                    "description": (
                        "Forget a persisted memory. Use when the user asks "
                        "to forget something or when a memory is now wrong."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "slug": {"type": "string"},
                        },
                        "required": ["slug"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": META_TOOL_MEMORY_STATUS,
                    "description": (
                        "Report current memory usage for this user's "
                        "bucket: total bytes, entry count, per-entry and "
                        "bucket byte limits, percent full, and a list of "
                        "entries by size. Call before memory_save when you "
                        "suspect the bucket is full, or when planning to "
                        "consolidate."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": META_TOOL_JOURNAL_APPEND,
                    "description": (
                        "Append a one-paragraph note to TODAY's journal "
                        "for this user. Use for ephemeral observations "
                        "worth keeping a few days — what happened, what "
                        "the user mentioned, decisions made. For "
                        "long-term facts use memory_save instead. "
                        "Per-user (no shared journal). Auto-prepends a "
                        "HH:MM timestamp. ≤4KB per entry, ≤64KB per day."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": (
                                    "Markdown paragraph. ≤4KB. Don't "
                                    "include your own timestamp — the "
                                    "tool adds one."
                                ),
                            },
                        },
                        "required": ["text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": META_TOOL_LOAD_JOURNAL_DAY,
                    "description": (
                        "Load all journal entries for a date for this "
                        "user. Use to recall what happened recently. "
                        "Omit `date` for today. Returns body=null when "
                        "the user has no entries for that day."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": (
                                    "YYYY-MM-DD (e.g. 2026-05-26). "
                                    "Omit for today."
                                ),
                            },
                        },
                    },
                },
            },
        ]

    def _working_memory_meta_tool_defs(self) -> list[dict[str, Any]]:
        """Conversation-scoped scratchpad. Always available — lives in
        `_Conversation.working_memory`, no external dependency.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": META_TOOL_WORKING_MEMORY_SET,
                    "description": (
                        "Write or overwrite the working-memory buffer "
                        "for THIS conversation. Use for ephemeral state "
                        "the model needs to keep in mind across the next "
                        "few turns — current task, partial plan, what "
                        "you just clarified with the user. This buffer "
                        "dies when the conversation evicts; for "
                        "long-term facts use `memory_save` instead. "
                        "Empty body acts like working_memory_clear."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": (
                                    "Markdown / plain text. ≤8KB. "
                                    "Whole buffer is replaced — append "
                                    "yourself if needed."
                                ),
                            },
                        },
                        "required": ["content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": META_TOOL_WORKING_MEMORY_CLEAR,
                    "description": (
                        "Empty the working-memory buffer for this "
                        "conversation. Call when the current task is "
                        "done or context fully changed."
                    ),
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    async def _filter_tools(
        self,
        *,
        ha_tools: list[dict[str, Any]],
        other_tools: list[dict[str, Any]],
        query: str,
        skill_force_include: set[str] | None = None,
        skill_hidden: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Rank tools by cosine similarity to the user transcript and keep
        the top-K. Bypassed when top-K is 0/disabled or when the total
        tool count is already at/under the cap.

        HA and other tools are passed separately because their cache
        strategies differ:
          * other_tools (custom HTTP + external MCP) — stable schemas,
            startup-warmed.
          * ha_tools — change per turn. With `ha_tools_mode=always`
            (default) they bypass scoring entirely, preserving upstream
            prompt-cache stability. With `ha_tools_mode=embedding` they
            join the scoring pool; cache misses are lazy-filled in one
            batch this turn. Lazy-fill failures degrade to include-all
            for the missing HA tools — never dropped.

        Skill gating (PR4):
          * `skill_hidden` — names that match some registered skill's
            `allowed_tools` but NO loaded skill's. Dropped from both
            sources before any other processing — real lazy disclosure
            (invisible until the owning skill is loaded).
          * `skill_force_include` — names matching a loaded skill's
            `allowed_tools`. Pulled into always_in so they pass
            regardless of embedding score. META_TOOL_NAMES are never
            hidden (caller-side guarantee in `_compute_skill_tool_gating`).
        """
        skill_force_include = skill_force_include or set()
        skill_hidden = skill_hidden or set()

        if skill_hidden:
            ha_tools = [
                t for t in ha_tools if t["function"]["name"] not in skill_hidden
            ]
            other_tools = [
                t for t in other_tools if t["function"]["name"] not in skill_hidden
            ]

        all_tools = ha_tools + other_tools
        if (
            self._embedding_client is None
            or self.config.tool_filter_top_k <= 0
            or len(all_tools) <= self.config.tool_filter_top_k
        ):
            return all_tools

        # Mode split: in "always" HA tools bypass the filter (default).
        if self.config.ha_tools_mode == HA_TOOLS_MODE_EMBEDDING:
            await self._ensure_ha_embeddings(ha_tools)
            scoring_tools = list(all_tools)
            always_in: list[dict[str, Any]] = []
        else:
            scoring_tools = list(other_tools)
            always_in = list(ha_tools)

        # Meta tools (skill_*, memory_*, working_memory_*) are tiny and
        # always-needed — pull them out of scoring entirely and append
        # at the tail. They do NOT count toward the top-K budget so
        # non-meta tools always get their full budget.
        meta_tail: list[dict[str, Any]] = [
            t for t in scoring_tools
            if t["function"]["name"] in META_TOOL_NAMES
        ]
        scoring_tools = [
            t for t in scoring_tools
            if t["function"]["name"] not in META_TOOL_NAMES
        ]

        # Loaded-skill tools always pass — pull them out of scoring_tools
        # into always_in so they survive the top-K cut.
        if skill_force_include:
            kept: list[dict[str, Any]] = []
            for t in scoring_tools:
                if t["function"]["name"] in skill_force_include:
                    always_in.append(t)
                else:
                    kept.append(t)
            scoring_tools = kept

        if not scoring_tools:
            return always_in + meta_tail

        try:
            query_vec = (await self._embedding_client.embed([query]))[0]
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning(
                "Embedding the user query failed (%s: %s); skipping tool filter.",
                type(exc).__name__, exc,
            )
            return always_in + scoring_tools + meta_tail

        scored: list[tuple[float, dict[str, Any]]] = []
        for tool in scoring_tools:
            name = tool["function"]["name"]
            desc = tool["function"].get("description", "") or ""
            vec = self._tool_embeddings.get(_embed_key(name, desc))
            if vec is None:
                # Lazy-fill failed earlier this turn (HA), or not in the
                # static cache (defensive). Include rather than drop.
                always_in.append(tool)
                continue
            scored.append((cosine_similarity(query_vec, vec), tool))

        scored.sort(key=lambda x: x[0], reverse=True)
        keep = self.config.tool_filter_top_k - len(always_in)
        top = always_in + [t for _, t in scored[: max(keep, 0)]] + meta_tail
        _LOGGER.debug(
            "Tool filter (ha_tools_mode=%s, hidden=%d, forced=%d, meta=%d): "
            "kept %d/%d (always-in: %d, scored top: %s)",
            self.config.ha_tools_mode, len(skill_hidden), len(skill_force_include),
            len(meta_tail), len(top), len(all_tools), len(always_in),
            ", ".join(f"{s:.2f}/{t['function']['name']}" for s, t in scored[:5]),
        )
        return top

    async def _ensure_ha_embeddings(
        self, ha_tools: list[dict[str, Any]],
    ) -> None:
        """Lazy-fill HA tool embeddings for any (name, desc_hash) not yet
        cached. One batch call per turn even if many entities were newly
        exposed. Failure leaves entries missing — caller falls them
        through to always-in (the include-all-on-failure policy).
        """
        if self._embedding_client is None:
            return
        missing: list[tuple[str, str]] = []  # (cache_key, "name: desc")
        for tool in ha_tools:
            name = tool["function"]["name"]
            desc = tool["function"].get("description", "") or ""
            key = _embed_key(name, desc)
            if key not in self._tool_embeddings:
                missing.append((key, f"{name}: {desc}"))
        if not missing:
            return
        try:
            vectors = await self._embedding_client.embed(
                [text for _, text in missing],
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning(
                "Lazy embed of %d HA tool(s) failed (%s: %s); "
                "those tools fall through to include-all for this turn.",
                len(missing), type(exc).__name__, exc,
            )
            return
        for (key, _), vec in zip(missing, vectors):
            self._tool_embeddings[key] = vec
        _LOGGER.debug("Lazy-embedded %d HA tool(s)", len(missing))

    async def _run_loop_blocking(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
        *, convo: _Conversation, turn_ctx: _TurnContext,
    ) -> tuple[str, bool]:
        final_text = ""
        for _ in range(self.config.max_tool_iterations):
            response = await self.llm.chat(messages, tools=tools or None)
            choice = (response.get("choices") or [{}])[0]
            message = choice.get("message") or {}
            tool_calls = message.get("tool_calls") or []
            messages.append({
                "role": "assistant",
                "content": message.get("content") or "",
                **({"tool_calls": tool_calls} if tool_calls else {}),
            })
            if not tool_calls:
                final_text = (message.get("content") or "").strip()
                return final_text, True
            tools_dirty = await self._dispatch_tool_calls(
                tool_calls, messages, convo=convo, system_ctx=turn_ctx.system_ctx,
            )
            if tools_dirty:
                tools = await self._recompute_tools(turn_ctx, convo)
        return final_text, False

    async def _dispatch_tool_calls(
        self, tool_calls: list[dict[str, Any]], messages: list[dict[str, Any]],
        *, convo: _Conversation, system_ctx: _SystemContext,
    ) -> bool:
        """Process the tool calls, append role=tool results to `messages`,
        and return True iff anything tool-affecting changed (loaded
        skills set OR memory index). On any change the system message
        is rebuilt in place and the caller re-runs gating + filtering.
        """
        skill_state_changed = False
        memory_index_changed = False
        working_memory_changed = False
        for call in tool_calls:
            fn = call.get("function") or {}
            name = fn.get("name") or ""
            raw_args = fn.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {}
            if name in META_TOOL_NAMES:
                tool_result = await self._dispatch_meta_tool(
                    name, args, convo, system_ctx,
                )
                if name in (META_TOOL_LOAD_SKILL, META_TOOL_UNLOAD_SKILL) \
                        and tool_result.get("ok"):
                    skill_state_changed = True
                if name in (META_TOOL_MEMORY_SAVE, META_TOOL_MEMORY_DELETE) \
                        and tool_result.get("ok"):
                    memory_index_changed = True
                if name in (META_TOOL_WORKING_MEMORY_SET,
                            META_TOOL_WORKING_MEMORY_CLEAR) \
                        and tool_result.get("ok"):
                    working_memory_changed = True
            else:
                tool_result = await self._dispatch(name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": call.get("id") or "",
                "name": name,
                "content": json.dumps(tool_result, ensure_ascii=False),
            })
        # In-place rebuild of system message so the very next round-trip
        # in this same user turn sees the (un)loaded skill body, the
        # refreshed memory index, or the new working-memory buffer.
        # Append-only at the tail of `_compose_system` → stable prefix
        # preserved for the upstream prompt cache.
        if skill_state_changed or memory_index_changed or working_memory_changed:
            messages[0]["content"] = self._compose_system_from_ctx(
                system_ctx, convo,
            )
        # Only skill-state changes invalidate the gating / tools array;
        # memory operations don't surface or hide tools.
        return skill_state_changed

    async def _dispatch_meta_tool(
        self, name: str, args: dict[str, Any], convo: _Conversation,
        system_ctx: _SystemContext,
    ) -> dict[str, Any]:
        """Route a meta-tool call (skill or memory). Memory tools key
        off `system_ctx.user_id` to pick the right bucket; the LLM
        never sees or names a user. `run_skill_script` does subprocess
        I/O; the others are pure in-process."""
        if name == META_TOOL_LIST_SKILLS:
            record_tool_call(name, "meta", ok=True)
            return {
                "ok": True,
                "available": [
                    {"name": s.name, "description": s.description}
                    for s in sorted(self._skills_by_name.values(),
                                    key=lambda s: s.name)
                ],
                "loaded": sorted(convo.loaded_skills),
            }
        if name == META_TOOL_LOAD_SKILL:
            skill_name = args.get("name") or ""
            if skill_name not in self._skills_by_name:
                record_tool_call(name, "meta", ok=False)
                return {
                    "ok": False,
                    "error": f"unknown skill {skill_name!r}",
                    "available": sorted(self._skills_by_name),
                }
            convo.loaded_skills.add(skill_name)
            record_tool_call(name, "meta", ok=True)
            return {"ok": True, "loaded": sorted(convo.loaded_skills)}
        if name == META_TOOL_UNLOAD_SKILL:
            skill_name = args.get("name") or ""
            if skill_name not in convo.loaded_skills:
                record_tool_call(name, "meta", ok=False)
                return {
                    "ok": False,
                    "error": f"skill {skill_name!r} not loaded",
                    "loaded": sorted(convo.loaded_skills),
                }
            convo.loaded_skills.discard(skill_name)
            record_tool_call(name, "meta", ok=True)
            return {"ok": True, "loaded": sorted(convo.loaded_skills)}
        if name == META_TOOL_RUN_SKILL_SCRIPT:
            skill_name = args.get("skill_name") or ""
            skill = self._skills_by_name.get(skill_name)
            if skill is None:
                record_tool_call(name, "sandbox", ok=False)
                return {"ok": False, "error": f"unknown skill {skill_name!r}"}
            # Require explicit load — the SKILL.md body must be in the
            # LLM's context so it understands what each script does.
            # Also: prevents the model from poking at script files of
            # a skill it hasn't activated.
            if skill_name not in convo.loaded_skills:
                record_tool_call(name, "sandbox", ok=False)
                return {
                    "ok": False,
                    "error": f"skill {skill_name!r} not loaded — call load_skill first",
                }
            script_path = args.get("script_path") or ""
            script_args = args.get("args") or []
            if not isinstance(script_args, list) \
                    or not all(isinstance(a, str) for a in script_args):
                record_tool_call(name, "sandbox", ok=False)
                return {"ok": False, "error": "args must be a list of strings"}
            stdin_text = args.get("stdin")
            if stdin_text is not None and not isinstance(stdin_text, str):
                record_tool_call(name, "sandbox", ok=False)
                return {"ok": False, "error": "stdin must be a string"}
            try:
                result = await run_sandboxed_script(
                    skill_dir=skill.path,
                    script_path=script_path,
                    args=script_args,
                    stdin=stdin_text,
                )
            except SandboxError as exc:
                record_tool_call(name, "sandbox", ok=False)
                return {"ok": False, "error": f"sandbox error: {exc}"}
            record_tool_call(name, "sandbox", ok=(result.exit_code == 0))
            return {
                "ok": result.exit_code == 0 and not result.timed_out,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "timed_out": result.timed_out,
                "truncated_stdout": result.truncated_stdout,
                "truncated_stderr": result.truncated_stderr,
            }
        if name in (META_TOOL_MEMORY_SAVE, META_TOOL_MEMORY_READ,
                    META_TOOL_MEMORY_DELETE, META_TOOL_MEMORY_STATUS,
                    META_TOOL_JOURNAL_APPEND, META_TOOL_LOAD_JOURNAL_DAY):
            return self._dispatch_memory_meta_tool(name, args, system_ctx)
        if name == META_TOOL_WORKING_MEMORY_SET:
            content = args.get("content", "")
            if not isinstance(content, str):
                record_tool_call(name, "meta", ok=False)
                return {"ok": False, "error": "content must be a string"}
            if len(content.encode("utf-8")) > MAX_WORKING_MEMORY_BYTES:
                record_tool_call(name, "meta", ok=False)
                return {
                    "ok": False,
                    "error": (
                        f"content exceeds {MAX_WORKING_MEMORY_BYTES} bytes"
                    ),
                }
            # Empty body == clear, so users don't have to pick between
            # set("") and clear().
            convo.working_memory = content.strip()
            record_tool_call(name, "meta", ok=True)
            return {"ok": True, "bytes": len(convo.working_memory.encode("utf-8"))}
        if name == META_TOOL_WORKING_MEMORY_CLEAR:
            convo.working_memory = ""
            record_tool_call(name, "meta", ok=True)
            return {"ok": True}
        # Shouldn't happen — META_TOOL_NAMES checked upstream.
        record_tool_call(name, "meta", ok=False)
        return {"ok": False, "error": f"unknown meta tool {name!r}"}

    def _dispatch_memory_meta_tool(
        self, name: str, args: dict[str, Any], system_ctx: _SystemContext,
    ) -> dict[str, Any]:
        store = self._memory_store
        if store is None:
            # Defensive — _meta_tool_defs already hides these when None,
            # so the LLM should never get here.
            record_tool_call(name, "meta", ok=False)
            return {"ok": False, "error": "memory disabled"}
        user_id = system_ctx.user_id
        if name == META_TOOL_MEMORY_SAVE:
            slug = args.get("slug") or ""
            description = args.get("description") or ""
            body = args.get("body")
            try:
                store.save(user_id, slug, description, body or "")
            except MemoryBucketFullError as exc:
                # Bucket-full: hand the LLM the entry list inline so it can
                # decide what to delete without a separate memory_status
                # round trip (R2 consolidation guardrail).
                record_tool_call(name, "meta", ok=False)
                result: dict[str, Any] = {"ok": False, "error": str(exc)}
                try:
                    result["status"] = store.status(user_id)
                except MemoryStoreError:
                    pass
                return result
            except MemoryStoreError as exc:
                record_tool_call(name, "meta", ok=False)
                return {"ok": False, "error": str(exc)}
            record_tool_call(name, "meta", ok=True)
            return {"ok": True, "slug": slug}
        if name == META_TOOL_MEMORY_READ:
            slug = args.get("slug")
            if not slug:
                record_tool_call(name, "meta", ok=True)
                return {
                    "ok": True,
                    "index": [
                        {"slug": s, "description": d}
                        for s, d in store.list(user_id)
                    ],
                }
            try:
                body = store.read(user_id, slug)
            except MemoryStoreError as exc:
                record_tool_call(name, "meta", ok=False)
                return {"ok": False, "error": str(exc)}
            if body is None:
                record_tool_call(name, "meta", ok=False)
                return {"ok": False, "error": f"no memory with slug {slug!r}"}
            record_tool_call(name, "meta", ok=True)
            return {"ok": True, "slug": slug, "body": body}
        if name == META_TOOL_MEMORY_DELETE:
            slug = args.get("slug") or ""
            try:
                removed = store.delete(user_id, slug)
            except MemoryStoreError as exc:
                record_tool_call(name, "meta", ok=False)
                return {"ok": False, "error": str(exc)}
            if not removed:
                record_tool_call(name, "meta", ok=False)
                return {"ok": False, "error": f"no memory with slug {slug!r}"}
            record_tool_call(name, "meta", ok=True)
            return {"ok": True, "slug": slug}
        if name == META_TOOL_MEMORY_STATUS:
            try:
                report = store.status(user_id)
            except MemoryStoreError as exc:
                record_tool_call(name, "meta", ok=False)
                return {"ok": False, "error": str(exc)}
            record_tool_call(name, "meta", ok=True)
            return {"ok": True, **report}
        if name == META_TOOL_JOURNAL_APPEND:
            text = args.get("text") or ""
            if not isinstance(text, str):
                record_tool_call(name, "meta", ok=False)
                return {"ok": False, "error": "text must be a string"}
            try:
                date, total_bytes = store.journal_append(user_id, text)
            except MemoryStoreError as exc:
                record_tool_call(name, "meta", ok=False)
                return {"ok": False, "error": str(exc)}
            record_tool_call(name, "meta", ok=True)
            return {"ok": True, "date": date, "day_bytes": total_bytes}
        if name == META_TOOL_LOAD_JOURNAL_DAY:
            date_arg = args.get("date")
            if date_arg is not None and not isinstance(date_arg, str):
                record_tool_call(name, "meta", ok=False)
                return {"ok": False, "error": "date must be a string"}
            try:
                date, body = store.read_journal_day(user_id, date_arg)
            except MemoryStoreError as exc:
                record_tool_call(name, "meta", ok=False)
                return {"ok": False, "error": str(exc)}
            record_tool_call(name, "meta", ok=True)
            return {"ok": True, "date": date, "body": body}
        record_tool_call(name, "meta", ok=False)
        return {"ok": False, "error": f"unknown memory meta tool {name!r}"}

    async def _dispatch(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Route a non-meta tool call. HA tools → HA mcp_server; otherwise
        external MCP or custom HTTP. Per-turn HA snapshot determines
        what counts as an HA tool.
        """
        if name in self._ha_tools_by_name:
            source = "ha"
            target = self._ha_tools_by_name[name]
            coro = dispatch_mcp_tool(target, args)
        elif name in self._mcp_by_name:
            source = "mcp"
            target = self._mcp_by_name[name]
            coro = dispatch_mcp_tool(target, args)
        else:
            record_tool_call(name, "unknown", ok=False)
            return {"ok": False, "error": f"unknown tool {name}"}

        try:
            result = await coro
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("Tool %s failed", name)
            record_tool_call(name, source, ok=False)
            return {"ok": False, "error": str(exc)}
        record_tool_call(name, source, ok=bool(result.get("ok", True)))
        return result

    def _get_conversation(self, key: str) -> _Conversation:
        convo = self._conversations.get(key)
        if convo is None:
            convo = _Conversation()
            if self._auto_load_skills:
                # Filter against the currently-registered skill names so
                # a BOOTSTRAP entry pointing at a deleted skill is just
                # silently dropped, not an error.
                convo.loaded_skills.update(
                    self._auto_load_skills & set(self._skills_by_name),
                )
            self._conversations[key] = convo
        convo.last_used = time.monotonic()
        return convo

    def _trim_history(self, convo: _Conversation) -> None:
        max_msgs = self.config.history_turns * 2
        if len(convo.messages) > max_msgs:
            convo.messages = convo.messages[-max_msgs:]

    def _evict_stale(self) -> None:
        now = time.monotonic()
        stale = [k for k, c in self._conversations.items()
                 if now - c.last_used > CONVERSATION_TTL_SECONDS]
        for k in stale:
            del self._conversations[k]
