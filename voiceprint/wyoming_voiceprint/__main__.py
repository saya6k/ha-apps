"""Wyoming STT proxy with speaker verification."""
from __future__ import annotations

import argparse
import asyncio
import logging
from functools import partial

from wyoming.asr import Transcribe, Transcript
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.client import AsyncClient
from wyoming.info import AsrModel, AsrProgram, Attribution, Describe, Info
from wyoming.server import AsyncServer

from . import __version__, models
from .const import DEFAULT_ENROLL_DIR, MODEL_DIR
from .embedder import Embedder
from .enroll import load_voiceprints
from .handler import VoiceprintHandler

_LOGGER = logging.getLogger(__name__)

_ATTRIBUTION = Attribution(
    name="3D-Speaker (CAM++)",
    url="https://github.com/modelscope/3D-Speaker",
)


class InfoProvider:
    """Builds our Info, mirroring the downstream ASR's advertised languages.

    HA only offers an STT engine to a pipeline if the engine advertises the
    pipeline's language, so an empty list makes the proxy unselectable.
    Languages are re-queried from the downstream ASR on every Describe until a
    non-empty answer is cached (it may boot after us).
    """

    def __init__(self, upstream_uri: str, speakers: list[str]) -> None:
        self._upstream_uri = upstream_uri
        self._speakers = speakers
        self._cached: list[str] = []

    async def info(self) -> Info:
        if not self._cached:
            if await self.refresh() is None:
                _LOGGER.warning("Downstream ASR %s not reachable", self._upstream_uri)
            if not self._cached:
                _LOGGER.warning(
                    "Downstream ASR %s advertises no languages (or is "
                    "unreachable); this proxy stays unselectable until it does",
                    self._upstream_uri,
                )
        return self._build(self._cached)

    async def refresh(self) -> list[str] | None:
        """Query upstream languages; None when unreachable."""
        client = AsyncClient.from_uri(self._upstream_uri)
        try:
            await client.connect()
            try:
                await client.write_event(Describe().event())
                event = await asyncio.wait_for(client.read_event(), timeout=5)
            finally:
                await client.disconnect()
        except (OSError, asyncio.TimeoutError):
            return None
        if event is None:
            return None
        info = Info.from_event(event)
        languages = sorted(
            {lang for p in info.asr for m in p.models for lang in m.languages}
        )
        if languages:
            self._cached = languages
        return languages

    def _build(self, languages: list[str]) -> Info:
        return Info(
            asr=[
                AsrProgram(
                    name="Voiceprint",
                    attribution=_ATTRIBUTION,
                    installed=True,
                    description="Speaker-verifying STT proxy",
                    version=__version__,
                    models=[
                        AsrModel(
                            name="campplus_zh_en",
                            attribution=_ATTRIBUTION,
                            installed=True,
                            description=(
                                "Forwards to upstream STT; enrolled: "
                                + (", ".join(self._speakers) if self._speakers else "none")
                            ),
                            version="1.0.0",
                            languages=languages,
                        )
                    ],
                )
            ]
        )


async def _probe_upstream(uri: str) -> bool:
    """Stream a short silent utterance and wait for a transcript."""
    client = AsyncClient.from_uri(uri)
    try:
        await client.connect()
        try:
            await client.write_event(Transcribe().event())
            await client.write_event(
                AudioStart(rate=16000, width=2, channels=1).event()
            )
            await client.write_event(
                AudioChunk(
                    rate=16000, width=2, channels=1, audio=bytes(16000)  # 0.5 s
                ).event()
            )
            await client.write_event(AudioStop().event())
            while True:
                event = await asyncio.wait_for(client.read_event(), timeout=60)
                if event is None:
                    return False
                if Transcript.is_type(event.type):
                    return True
        finally:
            await client.disconnect()
    except (OSError, asyncio.TimeoutError):
        return False


async def _startup_check(info_provider: InfoProvider, uri: str) -> None:
    """Verify the upstream actually transcribes; retry until it comes up."""
    attempt = 0
    while True:
        attempt += 1
        languages = await info_provider.refresh()
        if languages is not None:
            _LOGGER.info(
                "Upstream %s is up (languages: %s)",
                uri, ", ".join(languages) if languages else "none advertised",
            )
            break
        if attempt == 1 or attempt % 12 == 0:
            _LOGGER.warning(
                "Upstream %s not reachable (attempt %d); retrying every 5 s",
                uri, attempt,
            )
        await asyncio.sleep(5)

    if await _probe_upstream(uri):
        _LOGGER.info("Upstream ASR verified: test utterance returned a transcript")
    else:
        _LOGGER.error(
            "Upstream %s accepted the connection but returned no transcript "
            "for a test utterance — check the upstream add-on's logs", uri,
        )


async def run(args: argparse.Namespace) -> None:
    model_path = args.model or models.ensure_model(MODEL_DIR)
    embedder = Embedder(model_path)
    voiceprints = load_voiceprints(args.enroll_dir, embedder)
    if not voiceprints:
        _LOGGER.warning(
            "No voiceprints in %s — passing all audio through unverified. "
            "Add WAVs under %s/<speaker>/ and restart.",
            args.enroll_dir, args.enroll_dir,
        )

    info_provider = InfoProvider(args.upstream_uri, sorted(voiceprints))
    # held in this scope (alive for the server's lifetime) so it isn't GC'd
    check_task = asyncio.create_task(_startup_check(info_provider, args.upstream_uri))  # noqa: F841

    server = AsyncServer.from_uri(args.uri)
    _LOGGER.info(
        "Ready: upstream=%s speakers=[%s] threshold=%.2f require_match=%s on %s",
        args.upstream_uri, ", ".join(sorted(voiceprints)),
        args.threshold, args.require_match, args.uri,
    )
    await server.run(
        partial(VoiceprintHandler, info_provider, args, embedder, voiceprints)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Wyoming STT proxy with speaker verification")
    parser.add_argument("--uri", default="tcp://0.0.0.0:10350")
    parser.add_argument(
        "--upstream-uri", required=True,
        help="Wyoming STT service to forward audio to, e.g. tcp://core-whisper:10300",
    )
    parser.add_argument(
        "--model", default=None,
        help="Path to a local .tflite model; if omitted, it is downloaded "
        "into /data on first run and cached there.",
    )
    parser.add_argument(
        "--enroll-dir", default=DEFAULT_ENROLL_DIR,
        help="Directory with <speaker>/*.wav enrollment clips",
    )
    parser.add_argument(
        "--capture", action="store_true",
        help="Save each received utterance as a 16 kHz WAV in the fixed "
        "CAPTURE_DIR (same audio path as live) for in-domain enrollment.",
    )
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--require-match", action=argparse.BooleanOptionalAction, default=True,
        help="Reject (empty transcript) when no enrolled speaker matches",
    )
    parser.add_argument(
        "--tag-speaker", action="store_true",
        help="Prefix transcripts with [speaker]",
    )
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
