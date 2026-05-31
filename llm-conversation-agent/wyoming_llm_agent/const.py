"""Defaults and constants."""
from __future__ import annotations

DEFAULT_URI = "tcp://0.0.0.0:10500"
DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_REQUEST_TIMEOUT = 60.0
DEFAULT_MAX_TOOL_ITERATIONS = 8
DEFAULT_HISTORY_TURNS = 6

# HA mcp_server tool filtering mode.
#   "always"    — HA tools always pass the filter (current default; preserves
#                 prompt-cache stability since `tools:` array stays constant).
#   "embedding" — HA tools also go through top-K embedding similarity. Trades
#                 prefix cache hits for fewer tokens per request — meaningful
#                 with large HA setups (50+ exposed entities) but breaks
#                 vLLM/OpenAI prompt caching when the top-K shifts per turn.
HA_TOOLS_MODE_ALWAYS = "always"
HA_TOOLS_MODE_EMBEDDING = "embedding"
HA_TOOLS_MODES = (HA_TOOLS_MODE_ALWAYS, HA_TOOLS_MODE_EMBEDDING)
DEFAULT_HA_TOOLS_MODE = HA_TOOLS_MODE_ALWAYS

# Meta-tool names. The agent always exposes these (bypass the embedding
# filter) so the LLM can drive skill activation per agentskills.io's
# progressive disclosure pattern. Names use simple snake_case so they
# survive `_safe_name` and read naturally in tool-call logs.
META_TOOL_LIST_SKILLS = "list_skills"
META_TOOL_LOAD_SKILL = "load_skill"
META_TOOL_UNLOAD_SKILL = "unload_skill"
META_TOOL_RUN_SKILL_SCRIPT = "run_skill_script"
# Per-user persistent memory meta-tools. Same bypass mechanics as the
# skill meta-tools — listing them in META_TOOL_NAMES is enough; the
# filter's always-in path and the gating "never hide meta tools" rule
# both key off this frozenset.
META_TOOL_MEMORY_SAVE = "memory_save"
META_TOOL_MEMORY_READ = "memory_read"
META_TOOL_MEMORY_DELETE = "memory_delete"
META_TOOL_MEMORY_STATUS = "memory_status"
# Working memory (R3 slot 9). In-memory per-conversation scratchpad —
# dies when the conversation evicts or `working_memory_clear` is called.
# Distinct from `memory_*` (persistent, on-disk).
META_TOOL_WORKING_MEMORY_SET = "working_memory_set"
META_TOOL_WORKING_MEMORY_CLEAR = "working_memory_clear"
# Daily journal — per-user only (no shared journal). Lazy-loaded
# (not auto-injected into the system prompt); LLM calls
# load_journal_day(date) when context demands.
META_TOOL_JOURNAL_APPEND = "journal_append"
META_TOOL_LOAD_JOURNAL_DAY = "load_journal_day"
META_TOOL_NAMES: frozenset[str] = frozenset({
    META_TOOL_LIST_SKILLS,
    META_TOOL_LOAD_SKILL,
    META_TOOL_UNLOAD_SKILL,
    META_TOOL_RUN_SKILL_SCRIPT,
    META_TOOL_MEMORY_SAVE,
    META_TOOL_MEMORY_READ,
    META_TOOL_MEMORY_DELETE,
    META_TOOL_MEMORY_STATUS,
    META_TOOL_WORKING_MEMORY_SET,
    META_TOOL_WORKING_MEMORY_CLEAR,
    META_TOOL_JOURNAL_APPEND,
    META_TOOL_LOAD_JOURNAL_DAY,
})

# Languages we advertise in HandleProgram. LLMs are multilingual so we
# default to a broad set; the option `languages` can override.
DEFAULT_LANGUAGES: list[str] = [
    "en", "ko", "ja", "zh", "es", "fr", "de", "it", "pt", "ru",
    "nl", "pl", "tr", "ar", "hi", "vi", "id", "th", "sv", "cs",
]

# Domains we generate per-domain tools for. Anything else is read-only
# (visible via get_state) until a per-domain tool exists.
CONTROL_DOMAINS_ON_OFF: frozenset[str] = frozenset({
    "light", "switch", "fan", "input_boolean", "automation", "script",
    "media_player", "climate", "humidifier", "siren",
})
DOMAIN_LIGHT = "light"
DOMAIN_CLIMATE = "climate"
DOMAIN_COVER = "cover"
DOMAIN_MEDIA_PLAYER = "media_player"
DOMAIN_LOCK = "lock"
DOMAIN_SCENE = "scene"

# Per-conversation history is keyed by HA's conversation_id (or by
# device_id when that's missing). Drop entries older than this so a
# long-running addon doesn't slowly leak memory.
CONVERSATION_TTL_SECONDS = 30 * 60
