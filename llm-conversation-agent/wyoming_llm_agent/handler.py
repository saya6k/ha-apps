"""Wyoming event handler: Describe → Info, Transcript → Handled/NotHandled.

HA's wyoming conversation integration only consumes single Handled /
NotHandled events for the conversation domain — HandledStart /
HandledChunk / HandledStop and `supports_handled_streaming` are not
wired up anywhere in HA core (verified against dev branch as of
2026-05). So we always emit one terminal event after the LLM finishes.
"""
from __future__ import annotations

import argparse
import logging
from importlib.metadata import PackageNotFoundError, version

from wyoming.asr import Transcript
from wyoming.event import Event
from wyoming.handle import Handled, NotHandled
from wyoming.info import Attribution, Describe, HandleModel, HandleProgram, Info
from wyoming.server import AsyncEventHandler

from . import __version__
from .agent import Agent

_LOGGER = logging.getLogger(__name__)

_AGENT_NAME = "LLM Conversation Agent"
_AGENT_DESCRIPTION = "LLM-backed conversation agent for Home Assistant"
_ATTRIBUTION = Attribution(
    name="ha-llm-conversation-agent",
    url="https://github.com/saya6k/ha-llm-conversation-agent",
)


def _pkg_version() -> str:
    try:
        return version("ha-llm-conversation-agent")
    except PackageNotFoundError:
        return __version__


class EventHandler(AsyncEventHandler):
    def __init__(
        self,
        agent: Agent,
        cli_args: argparse.Namespace,
        languages: list[str],
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.agent = agent
        self.cli_args = cli_args
        self.languages = languages

    async def handle_event(self, event: Event) -> bool:
        try:
            return await self._handle_event(event)
        except Exception:
            _LOGGER.exception("Unexpected error handling event: %s", event)
            return False

    async def _handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self._info().event())
            return True

        if Transcript.is_type(event.type):
            transcript = Transcript.from_event(event)
            text = (transcript.text or "").strip()
            language = transcript.language

            context = transcript.context or {}
            conversation_id = context.get("conversation_id")
            device_id = context.get("device_id") or self.cli_args.device_id
            satellite_id = context.get("satellite_id") or self.cli_args.satellite_id
            # HA core does NOT populate context["user_id"] in the
            # Wyoming Transcript today — even on 2026.6.0 dev. See
            # notes/ha-version-limitations.md L6 for the upstream gap
            # and watch-list. Until that's fixed, this is always None
            # and the memory store routes every turn to the shared
            # bucket (per-user BOOTSTRAP / USER profile slots stay
            # silent). The wiring is ready; only the upstream send is
            # missing.
            user_id = context.get("user_id")

            _LOGGER.debug(
                "Transcript lang=%s device=%s satellite=%s convo=%s user=%s text=%r",
                language, device_id, satellite_id, conversation_id, user_id, text,
            )

            if not text:
                await self.write_event(
                    NotHandled(text="No command was given.", context=transcript.context).event()
                )
                return True

            result = await self.agent.respond(
                text=text, language=language, conversation_id=conversation_id,
                device_id=device_id, satellite_id=satellite_id,
                user_id=user_id,
            )
            response_cls = Handled if result.handled else NotHandled
            await self.write_event(
                response_cls(text=result.text, context=transcript.context).event()
            )
            return True

        return True

    def _info(self) -> Info:
        return Info(
            handle=[
                HandleProgram(
                    name=_AGENT_NAME,
                    description=_AGENT_DESCRIPTION,
                    attribution=_ATTRIBUTION,
                    installed=True,
                    version=_pkg_version(),
                    supports_home_control=True,
                    models=[
                        HandleModel(
                            name=_AGENT_NAME,
                            description=_AGENT_DESCRIPTION,
                            attribution=_ATTRIBUTION,
                            installed=True,
                            version=_pkg_version(),
                            languages=self.languages,
                        )
                    ],
                )
            ]
        )
