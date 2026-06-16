"""Dummy upstream Wyoming STT: answers every session with a fixed transcript."""
import asyncio

from wyoming.asr import Transcript
from wyoming.audio import AudioStop
from wyoming.event import Event
from wyoming.info import AsrModel, AsrProgram, Attribution, Describe, Info
from wyoming.server import AsyncEventHandler, AsyncServer

ATTR = Attribution(name="dummy", url="https://example.com")
INFO = Info(asr=[AsrProgram(
    name="dummy-stt", attribution=ATTR, installed=True, description="dummy",
    version="0", models=[AsrModel(
        name="dummy", attribution=ATTR, installed=True, description="dummy",
        version="0", languages=["en", "ko"])],
)])


class Handler(AsyncEventHandler):
    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(INFO.event())
            return True
        if AudioStop.is_type(event.type):
            await self.write_event(Transcript(text="hello from upstream").event())
            return False
        return True


async def main() -> None:
    server = AsyncServer.from_uri("tcp://127.0.0.1:10300")
    await server.run(Handler)


asyncio.run(main())
