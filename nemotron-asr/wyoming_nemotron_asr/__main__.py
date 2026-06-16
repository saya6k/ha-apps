"""Entry point: python -m wyoming_nemotron_asr ...

Builds the ONNX engine once at boot (download + session load), then serves the
Wyoming ASR protocol. A setup failure exits non-zero so s6's finish halts the
container with a clear one-line error instead of crash-looping.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
from functools import partial

from . import __version__
from . import models
from .const import (
    DEFAULT_MODEL_REPO,
    DEFAULT_PORT,
    LANGUAGES,
    MODEL_BASE_DIR,
)

_LOGGER = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="wyoming_nemotron_asr")
    parser.add_argument("--uri", default=f"tcp://0.0.0.0:{DEFAULT_PORT}")
    parser.add_argument("--model-repo", default=DEFAULT_MODEL_REPO)
    parser.add_argument("--model-dir", default=MODEL_BASE_DIR)
    parser.add_argument(
        "--language",
        default=None,
        help="Fallback language when the client doesn't specify one (e.g. 'ko').",
    )
    parser.add_argument(
        "--num-threads",
        type=int,
        default=int(os.environ.get("NEMOTRON_THREADS", "0")) or (os.cpu_count() or 4),
    )
    parser.add_argument("--hf-token", default=os.environ.get("HF_TOKEN", ""))
    parser.add_argument(
        "--hotwords",
        default="",
        help="Newline-separated phrases to bias toward (e.g. room/entity names).",
    )
    parser.add_argument(
        "--hotword-boost",
        type=float,
        default=2.0,
        help="Logit bonus per hotword token during greedy decode.",
    )
    parser.add_argument(
        "--no-transcript-streaming",
        action="store_true",
        help="Send only the final Transcript (no TranscriptChunk streaming). Use "
        "for older HA pipelines that error on transcript streaming.",
    )
    parser.add_argument(
        "--zeroconf", nargs="?", const="nemotron-asr", default=None
    )
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--app-version", action="version", version=__version__)
    return parser.parse_args()


def _build_info(streaming: bool) -> "Info":
    from wyoming.info import AsrModel, AsrProgram, Attribution, Info

    attr = Attribution(
        name="NVIDIA Nemotron ASR (ONNX)",
        url="https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b",
    )
    return Info(
        asr=[
            AsrProgram(
                name="Nemotron ASR",
                description="NVIDIA Nemotron streaming ASR (0.6B, ONNX, CPU)",
                attribution=attr,
                installed=True,
                version=__version__,
                supports_transcript_streaming=streaming,
                models=[
                    AsrModel(
                        name="nemotron-3.5-asr-streaming-0.6b",
                        description="Multilingual streaming Conformer-Transducer",
                        attribution=attr,
                        installed=True,
                        version=None,
                        languages=list(LANGUAGES),
                    )
                ],
            )
        ],
    )


async def main() -> None:
    args = _parse_args()
    args.hf_token = (args.hf_token or "").strip()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
        datefmt="%H:%M:%S",
    )
    _LOGGER.info(
        "Booting wyoming_nemotron_asr %s (repo=%s, threads=%d, lang=%s)",
        __version__, args.model_repo, args.num_threads, args.language,
    )

    from . import diag

    diag.log_cpu_diagnostics()

    from .engine import NemotronASR

    try:
        model_dir = models.ensure_model(
            args.model_repo, args.model_dir, token=args.hf_token
        )
        hotwords = [w.strip() for w in args.hotwords.split("\n") if w.strip()]
        engine = NemotronASR(
            model_dir,
            num_threads=args.num_threads,
            hotwords=hotwords,
            hotword_boost=args.hotword_boost,
        )
    except Exception as err:  # noqa: BLE001 - any setup failure -> graceful stop
        _LOGGER.error("Model setup failed: %s", err)
        _LOGGER.error(
            "Check the model repo id, hf_token (for gated repos), disk space "
            "(~1.4 GB), and network connectivity. Shutting down."
        )
        if args.debug:
            _LOGGER.exception("Full traceback (debug):")
        raise SystemExit(1)

    engine.warmup(args.language)

    wyoming_info = _build_info(streaming=not args.no_transcript_streaming)

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
        except ImportError:
            _LOGGER.warning("Zeroconf requested but wyoming[zeroconf] not installed")

    _LOGGER.info("Ready (uri=%s)", args.uri)

    from .handler import NemotronEventHandler

    server_task = asyncio.create_task(
        server.run(partial(NemotronEventHandler, wyoming_info, args, engine))
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
