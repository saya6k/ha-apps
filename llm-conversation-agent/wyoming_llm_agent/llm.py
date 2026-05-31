"""OpenAI-compatible chat completions client.

Same retry-on-dead-pool pattern as the old bridge: httpx may hand out a
keepalive connection the upstream half-closed during a network blip;
the first request after recovery fails until a fresh socket is opened.
One application-level retry covers it.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from time import monotonic
from typing import Any

import httpx

from .metrics import record_chat

_LOGGER = logging.getLogger(__name__)

_RETRYABLE: tuple[type[BaseException], ...] = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.RemoteProtocolError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.PoolTimeout,
)


@dataclass
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    request_timeout: float = 60.0
    verify_ssl: bool = True
    extra_headers: dict[str, str] = field(default_factory=dict)

    @property
    def headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        h.update(self.extra_headers)
        return h


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        timeout = httpx.Timeout(
            connect=10.0,
            write=30.0,
            read=config.request_timeout,
            pool=10.0,
        )
        self._client = httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, verify=config.verify_ssl,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict | None = None,
        read_timeout: float | None = None,
    ) -> dict[str, Any]:
        """Send one chat completion request. Returns the parsed JSON.

        `read_timeout` overrides the client's default read timeout for this
        one call — useful when the caller knows a request is cold-start
        sensitive (model loading on the upstream).
        """
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
        }
        if tools:
            body["tools"] = tools
            if tool_choice is not None:
                body["tool_choice"] = tool_choice

        url = f"{self.config.base_url.rstrip('/')}/chat/completions"

        post_kwargs: dict[str, Any] = {"headers": self.config.headers, "json": body}
        if read_timeout is not None:
            post_kwargs["timeout"] = httpx.Timeout(
                connect=10.0, write=30.0, read=read_timeout, pool=10.0,
            )

        last_exc: BaseException | None = None
        t0 = monotonic()
        for attempt in (1, 2):
            try:
                r = await self._client.post(url, **post_kwargs)
                break
            except _RETRYABLE as exc:
                last_exc = exc
                _LOGGER.warning(
                    "LLM POST attempt %d/2 failed (%s); retrying",
                    attempt, type(exc).__name__,
                )
        else:
            assert last_exc is not None
            record_chat(self.config.model, ok=False,
                        duration_s=monotonic() - t0, usage=None)
            raise last_exc

        if r.status_code != 200:
            record_chat(self.config.model, ok=False,
                        duration_s=monotonic() - t0, usage=None)
            raise httpx.HTTPStatusError(
                f"LLM upstream {r.status_code}: {r.text[:500]}",
                request=r.request,
                response=r,
            )
        parsed = r.json()
        record_chat(self.config.model, ok=True,
                    duration_s=monotonic() - t0,
                    usage=parsed.get("usage"))
        return parsed
