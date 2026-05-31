"""Persistent MCP listener — receive resource notifications, dispatch refreshes.

Tool dispatch keeps using ephemeral sessions (the existing invariant — one
session per call, simple, robust to half-closed sockets). This module adds
a parallel persistent session per MCP server whose sole job is to:

1. Subscribe to URIs we care about (tracked SKILL.md URIs)
2. Receive `notifications/resources/updated` for those URIs
3. Receive `notifications/resources/list_changed` for the whole server
4. Dispatch a callback that re-fetches + re-installs affected bundles
5. Reconnect on disconnect with bounded backoff; re-subscribe after reconnect

One asyncio task per server. Lifecycle: `start_all` at boot, `stop_all` at
shutdown. Crashes inside the listener never propagate to the agent's main
loop — worst case is "no live updates; restart picks up changes."
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import suppress
from dataclasses import dataclass, field

from mcp import ClientSession, types
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.session import RequestResponder

from .mcp_client import MCPServerConfig, _make_factory

_LOGGER = logging.getLogger(__name__)

# Reconnect backoff: 1s, 2s, 4s, 8s, 16s, 30s (cap)
_BACKOFF_INITIAL = 1.0
_BACKOFF_MAX = 30.0


# Callback signatures.
OnResourceUpdated = Callable[[MCPServerConfig, str], Awaitable[None]]
OnListChanged = Callable[[MCPServerConfig], Awaitable[None]]


@dataclass
class _ServerListener:
    server: MCPServerConfig
    on_updated: OnResourceUpdated
    on_list_changed: OnListChanged
    tracked_uris: set[str] = field(default_factory=set)
    _task: asyncio.Task | None = None
    _stop: asyncio.Event = field(default_factory=asyncio.Event)
    _resub_signal: asyncio.Event = field(default_factory=asyncio.Event)

    def add_tracked(self, uris: list[str]) -> None:
        """Add URIs to subscribe to. Subscribed on next connect or immediately
        if a session is currently open (deferred — keeps this method sync)."""
        before = len(self.tracked_uris)
        self.tracked_uris.update(uris)
        if len(self.tracked_uris) > before:
            self._resub_signal.set()

    async def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(
            self._run(), name=f"mcp-listener-{self.server.name}",
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError, Exception):
                await self._task
            self._task = None

    async def _run(self) -> None:
        backoff = _BACKOFF_INITIAL
        while not self._stop.is_set():
            try:
                await self._session_loop()
                backoff = _BACKOFF_INITIAL  # successful close, reset
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning(
                    "MCP listener %s disconnected (%s: %s); reconnect in %.1fs",
                    self.server.name, type(exc).__name__, exc, backoff,
                )
            if self._stop.is_set():
                return
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=backoff)
                return  # stop signalled during backoff
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, _BACKOFF_MAX)

    async def _session_loop(self) -> None:
        """Open a session, subscribe to all tracked URIs, hold the connection
        open while processing notifications via the message handler. Returns
        cleanly when stop is signalled; raises on any session error."""
        factory = _make_factory(self.server.verify_ssl)
        if self.server.transport == "sse":
            opener = sse_client(
                self.server.url, headers=self.server.headers or None,
                httpx_client_factory=factory,
            )
            async with opener as (read_stream, write_stream):
                await self._inner(read_stream, write_stream)
        else:
            opener = streamablehttp_client(
                self.server.url, headers=self.server.headers or None,
                httpx_client_factory=factory,
            )
            async with opener as (read_stream, write_stream, _):
                await self._inner(read_stream, write_stream)

    async def _inner(self, read_stream, write_stream) -> None:
        async with ClientSession(
            read_stream, write_stream,
            message_handler=self._on_message,
        ) as session:
            await session.initialize()
            subscribed: set[str] = set()
            while not self._stop.is_set():
                # Subscribe to any tracked URIs we haven't subscribed to yet.
                pending = self.tracked_uris - subscribed
                for uri in pending:
                    try:
                        await session.subscribe_resource(uri)
                        subscribed.add(uri)
                    except Exception as exc:  # noqa: BLE001
                        _LOGGER.debug(
                            "MCP listener %s: subscribe %s failed (%s: %s); "
                            "server may not support subscribe — notifications "
                            "still arrive via list_changed if advertised",
                            self.server.name, uri, type(exc).__name__, exc,
                        )
                        subscribed.add(uri)  # don't retry every loop
                # Wait for either resub signal or stop.
                done_event = asyncio.Event()
                async def _wait_either():
                    s_task = asyncio.create_task(self._stop.wait())
                    r_task = asyncio.create_task(self._resub_signal.wait())
                    try:
                        await asyncio.wait(
                            {s_task, r_task},
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                    finally:
                        for t in (s_task, r_task):
                            if not t.done():
                                t.cancel()
                                with suppress(asyncio.CancelledError):
                                    await t
                    done_event.set()
                await _wait_either()
                self._resub_signal.clear()

    async def _on_message(
        self,
        message: RequestResponder[types.ServerRequest, types.ClientResult]
                 | types.ServerNotification | Exception,
    ) -> None:
        if isinstance(message, Exception):
            _LOGGER.debug(
                "MCP listener %s: stream exception %r", self.server.name, message,
            )
            return
        if not isinstance(message, types.ServerNotification):
            # Server-initiated requests (sampling, list_roots, elicit) —
            # T1 doesn't implement these; respond default via SDK.
            return
        root = message.root
        if isinstance(root, types.ResourceUpdatedNotification):
            uri = str(root.params.uri)
            _LOGGER.info(
                "MCP %s: resource updated %s — triggering re-install",
                self.server.name, uri,
            )
            try:
                await self.on_updated(self.server, uri)
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    "on_updated handler failed for %s %s",
                    self.server.name, uri,
                )
        elif isinstance(root, types.ResourceListChangedNotification):
            _LOGGER.info(
                "MCP %s: resource list changed — re-discovering bundles",
                self.server.name,
            )
            try:
                await self.on_list_changed(self.server)
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    "on_list_changed handler failed for %s", self.server.name,
                )
        # Other notifications (progress, logging, tools/prompts list_changed)
        # are not handled in T1 — silently ignored. Add handlers in T2.


class MCPListenerRegistry:
    """Coordinates per-server listeners with a single pair of callbacks."""

    def __init__(
        self,
        on_resource_updated: OnResourceUpdated,
        on_list_changed: OnListChanged,
    ) -> None:
        self._on_updated = on_resource_updated
        self._on_list_changed = on_list_changed
        self._by_name: dict[str, _ServerListener] = {}

    async def start_all(self, servers: list[MCPServerConfig]) -> None:
        for server in servers:
            listener = _ServerListener(
                server=server,
                on_updated=self._on_updated,
                on_list_changed=self._on_list_changed,
            )
            self._by_name[server.name] = listener
            await listener.start()

    def track(self, server_name: str, uris: list[str]) -> None:
        listener = self._by_name.get(server_name)
        if listener is None:
            return
        listener.add_tracked(uris)

    async def stop_all(self) -> None:
        await asyncio.gather(
            *(l.stop() for l in self._by_name.values()), return_exceptions=True,
        )
        self._by_name.clear()
