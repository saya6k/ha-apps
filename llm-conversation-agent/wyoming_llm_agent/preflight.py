"""Startup probe that verifies the upstream LLM accepts tool definitions.

This catches the most common misconfiguration in real-world deployments:
the user picks a model that doesn't support OpenAI function calling
(many Gemma / Mistral / "uncensored" fine-tunes, or older Ollama
endpoints). Without tools the agent silently produces text-only
replies that HA can't act on — symptoms look like "the LLM understands
me but never turns anything on."

The probe never blocks startup. It just logs a loud ERROR/WARNING that
the user (or a future maintainer reading addon logs) will see.
"""
from __future__ import annotations

import logging

import httpx

from .llm import LLMClient

_LOGGER = logging.getLogger(__name__)

# Preflight is a cold-start probe — local Ollama / vLLM / etc. often load
# the model on the first request, which can take much longer than steady
# state. Be generous so the common "model is loading" case doesn't trip
# our timeout. Steady-state requests still use the user's request_timeout.
_PREFLIGHT_READ_TIMEOUT_FLOOR = 180.0

_PROBE_TOOL = {
    "type": "function",
    "function": {
        "name": "preflight_ping",
        "description": (
            "Reply by calling this function with the answer 'pong'. "
            "This is a startup self-test for the conversation agent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {"type": "string", "enum": ["pong"]},
            },
            "required": ["answer"],
            "additionalProperties": False,
        },
    },
}

_PROBE_MESSAGES = [
    {
        "role": "system",
        "content": (
            "You are a tool-calling assistant. When asked to call a function, "
            "respond ONLY with the tool call — no surrounding text."
        ),
    },
    {
        "role": "user",
        "content": (
            "Call the preflight_ping function with answer='pong'. "
            "Do not reply with plain text — use the tool."
        ),
    },
]


async def check_function_calling(llm: LLMClient) -> None:
    """One-shot probe. Logs and returns; never raises."""
    base_url = llm.config.base_url
    model = llm.config.model
    timeout = max(llm.config.request_timeout, _PREFLIGHT_READ_TIMEOUT_FLOOR)
    try:
        response = await llm.chat(
            _PROBE_MESSAGES, tools=[_PROBE_TOOL], read_timeout=timeout,
        )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        body = ""
        if exc.response is not None:
            body = exc.response.text[:300]
        _LOGGER.error(
            "Preflight: upstream %s rejected the tools-bearing probe (HTTP %s). "
            "If this is a 400 about an unknown 'tools' or 'tool_choice' field, "
            "your upstream does NOT support OpenAI function calling and this "
            "agent will not be able to control Home Assistant. Body: %s",
            base_url, status, body,
        )
        return
    except (httpx.ReadTimeout, httpx.PoolTimeout) as exc:
        _LOGGER.warning(
            "Preflight: upstream %s accepted the probe but did not reply within "
            "%.0fs. This is usually the model loading into memory on the first "
            "request (Ollama / vLLM / local backends do lazy load). If your real "
            "user queries also time out, raise `request_timeout` or pre-warm the "
            "model. Original error: %s",
            base_url, timeout, exc,
        )
        return
    except httpx.ConnectError as exc:
        _LOGGER.error(
            "Preflight: could not connect to upstream %s (%s). "
            "Verify base_url is reachable from inside the addon container.",
            base_url, exc,
        )
        return
    except Exception as exc:  # noqa: BLE001 — diagnostics only
        _LOGGER.error(
            "Preflight: unexpected error talking to upstream %s (%s: %s). "
            "The agent will start anyway; the first real request will retry.",
            base_url, type(exc).__name__, exc,
        )
        return

    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    tool_calls = message.get("tool_calls") or []

    if tool_calls:
        names = [(c.get("function") or {}).get("name") for c in tool_calls]
        _LOGGER.info(
            "Preflight OK: model %s returned tool_calls (%s) — function calling works.",
            model, ", ".join(n for n in names if n) or "unnamed",
        )
        return

    # Accepted the request but didn't call the tool. Most likely the model
    # can't, or the upstream silently dropped `tools`. Either way: the
    # agent will be useless for home control.
    content_preview = (message.get("content") or "")[:300]
    _LOGGER.error(
        "Preflight FAILED: model %s on %s accepted the request but did NOT "
        "return tool_calls when explicitly asked to. The agent requires "
        "function-calling-capable models. Common causes:\n"
        "  * The model isn't trained for tools (many Gemma/Mistral fine-tunes,\n"
        "    'uncensored' variants, very small local models).\n"
        "  * The upstream proxy strips the `tools` field before forwarding.\n"
        "  * Ollama < 0.4 doesn't fully implement OpenAI tools.\n"
        "Home control via this agent will silently fail until you switch to "
        "a model with proven function-calling support. Probe response content: %r",
        model, base_url, content_preview,
    )
