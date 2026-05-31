"""Tiny asyncio HTTP server that serves `GET /metrics` only.

We don't pull in aiohttp / starlette / fastapi just for this — image
size matters. A bare `asyncio.start_server` with one-line HTTP/1.0
parsing is enough: no keep-alive, no pipelining, no streaming, scraped
at most once a few seconds. Prometheus is a tolerant client.
"""
from __future__ import annotations

import asyncio
import logging

from .metrics import render_latest

_LOGGER = logging.getLogger(__name__)

_NOT_FOUND = (
    b"HTTP/1.0 404 Not Found\r\n"
    b"Content-Length: 0\r\n"
    b"Connection: close\r\n\r\n"
)


async def serve_metrics(host: str, port: int) -> asyncio.AbstractServer:
    """Start the /metrics HTTP server. Returns the server handle."""
    server = await asyncio.start_server(_handle, host, port)
    _LOGGER.info("Prometheus /metrics listening on http://%s:%d/metrics", host, port)
    return server


async def _handle(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
) -> None:
    try:
        # We need only the request line + a couple of headers; cap to 4 KB.
        try:
            raw = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError):
            return
        request_line = raw.split(b"\r\n", 1)[0].decode("latin-1", errors="replace")
        parts = request_line.split(" ", 2)
        if len(parts) < 2:
            return
        method, path = parts[0], parts[1]

        if method != "GET" or not (path == "/metrics" or path.startswith("/metrics?")):
            writer.write(_NOT_FOUND)
            await writer.drain()
            return

        body, content_type = render_latest()
        head = (
            f"HTTP/1.0 200 OK\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("latin-1")
        writer.write(head + body)
        await writer.drain()
    except Exception:  # noqa: BLE001 — never let one scrape crash the server
        _LOGGER.exception("metrics HTTP handler failed")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:  # noqa: BLE001
            pass
