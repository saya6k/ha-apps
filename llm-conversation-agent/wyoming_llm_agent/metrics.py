"""Prometheus metrics for the agent.

Exposed on a separate HTTP port (default 9099) so the Wyoming TCP socket
on 10500 stays uncluttered. All metrics use the `llm_agent_` prefix to
make scraping configs and Grafana dashboards self-evident.

We intentionally do NOT compute cost ($) here — prices vary per model
and provider, and conversion belongs in the user's Prometheus recording
rules or Grafana panels, not in the addon.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from time import monotonic

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

_LOGGER = logging.getLogger(__name__)

# ----- Metric definitions ---------------------------------------------------

requests_total = Counter(
    "llm_agent_requests_total",
    "Total LLM chat-completion requests made.",
    ["model", "outcome"],  # outcome: success | error
)

prompt_tokens_total = Counter(
    "llm_agent_prompt_tokens_total",
    "Cumulative prompt tokens billed by upstream LLM.",
    ["model"],
)

cached_prompt_tokens_total = Counter(
    "llm_agent_cached_prompt_tokens_total",
    "Cumulative cached prompt tokens reported by upstream "
    "(OpenAI: usage.prompt_tokens_details.cached_tokens; vLLM APC: same shape). "
    "0 when upstream doesn't report or doesn't cache. "
    "Cache hit rate = cached / prompt — compute in Prometheus / Grafana.",
    ["model"],
)

completion_tokens_total = Counter(
    "llm_agent_completion_tokens_total",
    "Cumulative completion tokens billed by upstream LLM.",
    ["model"],
)

request_duration_seconds = Histogram(
    "llm_agent_request_duration_seconds",
    "Wall-clock duration of one LLM chat-completion call.",
    ["model"],
    # A few buckets that span "fast cloud" (~0.5s) through "cold local
    # GPU" (~30s) without going wild.
    buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0, 120.0),
)

tool_calls_total = Counter(
    "llm_agent_tool_calls_total",
    "Tool calls dispatched by the agent.",
    ["tool_name", "source", "outcome"],  # source: ha|mcp|http; outcome: success|error
)

mcp_session_duration_seconds = Histogram(
    "llm_agent_mcp_session_duration_seconds",
    "Round-trip time for one MCP session (open + list_tools / call_tool + close).",
    ["server"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0),
)

embedding_calls_total = Counter(
    "llm_agent_embedding_calls_total",
    "Embedding requests made (tool warmup + per-turn query embedding).",
    ["outcome"],
)

embedding_tokens_total = Counter(
    "llm_agent_embedding_tokens_total",
    "Cumulative embedding tokens billed by upstream (OpenAI /embeddings: "
    "usage.total_tokens). Used for cost accounting alongside chat tokens; "
    "embedding cost is typically <1% of chat cost so this rarely dominates "
    "the bill, but tracking it lets dashboards report a single accurate $/h.",
    ["model"],
)

turns_total = Counter(
    "llm_agent_turns_total",
    "User transcripts processed.",
    ["language", "handled"],  # handled: true|false
)

turn_duration_seconds = Histogram(
    "llm_agent_turn_duration_seconds",
    "Wall-clock duration of one user turn (Transcript → Handled).",
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
)

active_conversations = Gauge(
    "llm_agent_active_conversations",
    "Distinct in-memory conversations the agent is tracking.",
)

loaded_skills = Gauge(
    "llm_agent_loaded_skills",
    "agentskills.io-format Skills successfully parsed at startup.",
)


# ----- Recording helpers ----------------------------------------------------


def record_chat(model: str, *, ok: bool, duration_s: float, usage: dict | None) -> None:
    """Record one upstream LLM chat-completion outcome."""
    outcome = "success" if ok else "error"
    requests_total.labels(model=model, outcome=outcome).inc()
    request_duration_seconds.labels(model=model).observe(duration_s)
    if ok and isinstance(usage, dict):
        pt = int(usage.get("prompt_tokens") or 0)
        ct = int(usage.get("completion_tokens") or 0)
        if pt:
            prompt_tokens_total.labels(model=model).inc(pt)
        if ct:
            completion_tokens_total.labels(model=model).inc(ct)
        # Cache hit telemetry. OpenAI and vLLM (APC) both put the count at
        # usage.prompt_tokens_details.cached_tokens. Always-emit even when
        # zero so dashboards can distinguish "unsupported" (counter absent)
        # from "supported but 0 hits" (counter present at 0).
        details = usage.get("prompt_tokens_details")
        if isinstance(details, dict):
            cached = int(details.get("cached_tokens") or 0)
            cached_prompt_tokens_total.labels(model=model).inc(cached)


def record_tool_call(tool_name: str, source: str, *, ok: bool) -> None:
    tool_calls_total.labels(
        tool_name=tool_name, source=source,
        outcome="success" if ok else "error",
    ).inc()


def record_embedding(*, ok: bool, model: str | None = None, tokens: int = 0) -> None:
    """Record one /embeddings outcome.

    `tokens` is the upstream-reported usage.total_tokens (0 when the
    response didn't include usage, e.g. some vLLM builds, or when the
    call failed). `model` is needed to label `embedding_tokens_total`;
    callers should pass `EmbeddingConfig.model`. Both are optional so
    older call sites (and the failure path) keep working without a
    model label — they just don't contribute to the tokens counter.
    """
    embedding_calls_total.labels(outcome="success" if ok else "error").inc()
    if ok and tokens > 0 and model:
        embedding_tokens_total.labels(model=model).inc(tokens)


def record_turn(language: str | None, *, handled: bool, duration_s: float) -> None:
    turns_total.labels(
        language=language or "unknown",
        handled="true" if handled else "false",
    ).inc()
    turn_duration_seconds.observe(duration_s)


def set_active_conversations(n: int) -> None:
    active_conversations.set(n)


def set_loaded_skills(n: int) -> None:
    loaded_skills.set(n)


@asynccontextmanager
async def time_mcp_session(server_name: str):
    """Context manager for timing one MCP session round-trip."""
    t0 = monotonic()
    try:
        yield
    finally:
        mcp_session_duration_seconds.labels(server=server_name).observe(
            monotonic() - t0,
        )


# ----- HTTP exposition ------------------------------------------------------


def render_latest() -> tuple[bytes, str]:
    """Return (body, content_type) for a /metrics HTTP response."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
