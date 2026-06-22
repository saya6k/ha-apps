"""Entry point: python -m wyoming_supertonic ..."""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
from functools import partial
from typing import List

from . import __version__
from .const import (
    DEFAULT_PORT,
    LANGUAGES,
    MNN_CACHE_DIR,
    VOICES,
)

_LOGGER = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="wyoming_supertonic")
    parser.add_argument(
        "--uri",
        default=f"tcp://0.0.0.0:{DEFAULT_PORT}",
        help="unix:// or tcp:// URI to listen on",
    )
    parser.add_argument(
        "--zeroconf",
        nargs="?",
        const="supertonic",
        default=None,
        help="Enable mDNS discovery with optional name (default: supertonic)",
    )
    parser.add_argument(
        "--precision",
        default="auto",
        choices=["auto", "fp16", "fp32", "int8"],
        help="MNN model precision ('auto' picks best for the host CPU)",
    )
    parser.add_argument(
        "--version",
        default="v3",
        choices=["v2", "v3"],
        help="Supertonic model version (v3 = 31 languages, v2 = 5)",
    )
    parser.add_argument(
        "--model-dir",
        default=MNN_CACHE_DIR,
        help="Directory to store/load MNN models",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=int(os.environ.get("SUPERTONIC_THREADS", 0)),
        help="MNN intra-op threads. 0 (default) = auto (os.cpu_count()).",
    )
    parser.add_argument(
        "--mnn-memory",
        default="normal",
        choices=["low", "normal", "high"],
        help="MNN memory mode (higher trades RAM for speed)",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=3,
        help="Denoising steps (flow-matching iterations)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Speech speed multiplier",
    )
    parser.add_argument(
        "--warmup-voices",
        default="M1",
        help=(
            "Comma-separated voice IDs to pre-warm (e.g. 'M1,F1'). "
            "Empty string disables warm-up."
        ),
    )
    parser.add_argument(
        "--samples-per-chunk",
        type=int,
        default=1024,
        help="AudioChunk size in samples",
    )
    parser.add_argument(
        "--auto-punctuation",
        default=".?!。？！．؟",
        help="Auto-append a punctuation character when missing",
    )
    parser.add_argument(
        "--no-text-normalization",
        action="store_true",
        help="Disable number-to-words normalization before synthesis",
    )
    parser.add_argument(
        "--no-streaming",
        action="store_true",
        help="Disable Wyoming streaming protocol input events",
    )
    parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="Skip the warm-up sweep",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Verbose logging",
    )
    parser.add_argument(
        "--app-version",
        action="version",
        version=__version__,
    )
    return parser.parse_args()


def _build_info(version: str) -> "Info":  # noqa: F821
    from wyoming.info import Attribution, Info, TtsProgram, TtsVoice

    voices = [
        TtsVoice(
            name=voice,
            description=f"Supertonic voice {voice}",
            attribution=Attribution(
                name="Supertone",
                url="https://huggingface.co/yunfengwang/supertonic-tts-mnn",
            ),
            installed=True,
            version=None,
            languages=list(LANGUAGES),
            speakers=None,
        )
        for voice in VOICES
    ]
    return Info(
        tts=[
            TtsProgram(
                name="Supertonic",
                description="Supertonic (MNN) — lightweight multilingual TTS",
                attribution=Attribution(
                    name="Supertone",
                    url="https://huggingface.co/yunfengwang/supertonic-tts-mnn",
                ),
                installed=True,
                version=version,
                voices=voices,
                supports_synthesize_streaming=True,
            )
        ],
    )


def _parse_warmup_voices(spec: str) -> List[str]:
    return [v.strip() for v in spec.split(",") if v.strip()]


async def main() -> None:
    args = _parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
        datefmt="%H:%M:%S",
    )

    from .engine import SupertonicEngine
    from .handler import SupertonicEventHandler
    from .normalize import TextNormalizer

    resolved_threads = args.threads if args.threads > 0 else (os.cpu_count() or 4)
    _LOGGER.info(
        "Booting wyoming_supertonic %s "
        "(precision=%s, version=%s, steps=%d, threads=%d, memory=%s)",
        __version__,
        args.precision,
        args.version,
        args.steps,
        resolved_threads,
        args.mnn_memory,
    )

    engine = SupertonicEngine(
        precision=args.precision,
        version=args.version,
        steps=args.steps,
        speed=args.speed,
        threads=resolved_threads,
        memory_mode=args.mnn_memory,
        model_dir=args.model_dir,
    )

    if not args.no_warmup:
        warmup_voices = _parse_warmup_voices(args.warmup_voices)
        if warmup_voices:
            engine.warmup(warmup_voices)
        else:
            _LOGGER.info("Warm-up disabled by empty --warmup-voices")

    # One shared normalizer so its per-language RBNF engine cache survives
    # across client connections.
    normalizer = TextNormalizer()
    if args.no_text_normalization:
        _LOGGER.info("Number normalization disabled")

    wyoming_info = _build_info(__version__)

    from wyoming.server import AsyncServer, AsyncTcpServer

    server = AsyncServer.from_uri(args.uri)

    if args.zeroconf:
        if not isinstance(server, AsyncTcpServer):
            raise ValueError("Zeroconf requires a tcp:// uri")
        try:
            from wyoming.zeroconf import HomeAssistantZeroconf

            tcp_server: AsyncTcpServer = server
            hass_zc = HomeAssistantZeroconf(
                name=args.zeroconf, port=tcp_server.port, host=tcp_server.host
            )
            await hass_zc.register_server()
            _LOGGER.info("Zeroconf discovery registered (name=%s)", args.zeroconf)
        except ImportError:
            _LOGGER.warning("Zeroconf requested but wyoming[zeroconf] is not installed")

    _LOGGER.info("Ready (uri=%s)", args.uri)

    server_task = asyncio.create_task(
        server.run(
            partial(SupertonicEventHandler, wyoming_info, args, engine, normalizer)
        )
    )

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, server_task.cancel)
    loop.add_signal_handler(signal.SIGTERM, server_task.cancel)

    try:
        await server_task
    except asyncio.CancelledError:
        _LOGGER.info("Server stopped")


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        pass
