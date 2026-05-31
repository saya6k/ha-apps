"""OpenAI-compatible /embeddings client + cosine helpers.

Used by the agent to rank tools by similarity to the user transcript so
the LLM only receives the top-K most relevant ones per turn. Crosses
the 50-tool degradation cliff cleanly even with a heavy MCP setup.

Same retry-on-dead-pool pattern as `llm.LLMClient`: keepalive
connections half-closed during a network blip get one transparent retry
on a fresh socket.

Backend assumptions:
* OpenAI-shape `POST /embeddings` with `{model, input}` returning
  `{data: [{embedding: [float, ...]}, ...]}`.
* Both `base_url` and `api_key` may be inherited from the chat config
  (most users) or set independently (vLLM hybrid setups where chat and
  embedding live on different ports/hosts).
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import httpx

from .metrics import record_embedding

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
class EmbeddingConfig:
    base_url: str
    api_key: str
    model: str
    request_timeout: float = 30.0
    verify_ssl: bool = True
    extra_headers: dict[str, str] = field(default_factory=dict)

    @property
    def headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        h.update(self.extra_headers)
        return h


class EmbeddingClient:
    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config
        timeout = httpx.Timeout(
            connect=10.0, write=30.0,
            read=config.request_timeout, pool=10.0,
        )
        self._client = httpx.AsyncClient(
            timeout=timeout, follow_redirects=True, verify=config.verify_ssl,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of strings; preserves input order."""
        if not texts:
            return []
        body = {"model": self.config.model, "input": texts}
        url = f"{self.config.base_url.rstrip('/')}/embeddings"

        last_exc: BaseException | None = None
        for attempt in (1, 2):
            try:
                r = await self._client.post(url, headers=self.config.headers, json=body)
                break
            except _RETRYABLE as exc:
                last_exc = exc
                _LOGGER.warning(
                    "Embedding POST attempt %d/2 failed (%s); retrying",
                    attempt, type(exc).__name__,
                )
        else:
            assert last_exc is not None
            record_embedding(ok=False)
            raise last_exc

        if r.status_code != 200:
            record_embedding(ok=False)
            raise httpx.HTTPStatusError(
                f"Embedding upstream {r.status_code}: {r.text[:500]}",
                request=r.request, response=r,
            )
        data = r.json()
        items = data.get("data") or []
        # Capture usage.total_tokens when upstream provides it. OpenAI
        # always returns this; some vLLM builds omit usage from
        # /embeddings responses, in which case we record the call but
        # not the tokens (counter stays at 0 for that model — distinct
        # from "absent" which would mean the metric was never seen).
        usage = data.get("usage") if isinstance(data, dict) else None
        total_tokens = 0
        if isinstance(usage, dict):
            total_tokens = int(usage.get("total_tokens") or 0)
        record_embedding(ok=True, model=self.config.model, tokens=total_tokens)
        return [list(item.get("embedding") or []) for item in items]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Standard cosine, defensive against zero-vectors / length mismatch."""
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for i in range(n):
        av = a[i]
        bv = b[i]
        dot += av * bv
        norm_a += av * av
        norm_b += bv * bv
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))
