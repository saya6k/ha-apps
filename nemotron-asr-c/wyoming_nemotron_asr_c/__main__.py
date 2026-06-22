"""Entry point: download .nemo, convert to .bin, load model, serve Wyoming."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
from functools import partial

from wyoming.info import AsrModel, AsrProgram, Attribution, Info
from wyoming.server import AsyncServer, AsyncTcpServer

from . import __version__
from .const import (
    CHUNK_CHOICES,
    DEFAULT_CHUNK_SIZE,
    FE_WEIGHTS,
    HOTWORD_BOOST_DEFAULT,
    LANGUAGES,
    LIB_DIR,
    MODELS_DIR,
    PORT,
    QUANTS,
)
from .engine import NemoCEngine
from .handler import NemoCHandler
from .models import cleanup_old_models, ensure_bin, extract_tokenizer

_LOGGER = logging.getLogger(__name__)


def _build_info(model_repo: str) -> Info:
    """Build the Wyoming Info response for this add-on."""
    return Info(
        asr=[
            AsrProgram(
                name="Nemotron ASR (C)",
                description=(
                    "NVIDIA Nemotron streaming ASR on pure C "
                    "(nemotron-asr-streaming.c), .nemo -> .bin at boot"
                ),
                attribution=Attribution(
                    name="NVIDIA",
                    url="https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b",
                ),
                installed=True,
                version=__version__,
                supports_transcript_streaming=True,
                models=[
                    AsrModel(
                        name=model_repo,
                        languages=list(LANGUAGES),
                        attribution=Attribution(
                            name="NVIDIA",
                            url="https://huggingface.co/nvidia/nemotron-3.5-asr-streaming-0.6b",
                        ),
                        installed=True,
                        description=None,
                        version=None,
                    )
                ],
            )
        ],
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nemotron ASR (C) Wyoming server")
    parser.add_argument(
        "--uri", default=f"tcp://0.0.0.0:{PORT}",
        help="Wyoming server URI",
    )
    parser.add_argument(
        "--lib-dir", default=LIB_DIR,
        help="Directory containing libnemotron_asr.so",
    )
    parser.add_argument(
        "--model", default="nvidia/nemotron-3.5-asr-streaming-0.6b",
        help="HuggingFace repo ID containing the .nemo model file",
    )
    parser.add_argument(
        "--model-dir", default=MODELS_DIR,
        help="Directory for downloaded models and converted .bin files",
    )
    parser.add_argument(
        "--quantization", default="q8p",
        choices=list(QUANTS.keys()),
        help="Weight quantization for the converted .bin",
    )
    parser.add_argument(
        "--chunk-size", default=DEFAULT_CHUNK_SIZE,
        choices=list(CHUNK_CHOICES.keys()),
        help="Streaming encoder lookahead (accuracy vs speed)",
    )
    parser.add_argument(
        "--language", default=None,
        help="Fallback language when the client doesn't specify one",
    )
    parser.add_argument(
        "--hf-token", default="",
        help="HuggingFace access token for gated/private repos",
    )
    parser.add_argument(
        "--zeroconf", default=None,
        help="Zeroconf service name (omit to disable)",
    )
    parser.add_argument(
        "--hotwords", default="",
        help="Newline-separated hotword phrases for contextual biasing",
    )
    parser.add_argument(
        "--hotword-boost", type=float, default=HOTWORD_BOOST_DEFAULT,
        help=f"Logit bonus per hotword token during greedy decode (default: {HOTWORD_BOOST_DEFAULT})",
    )
    parser.add_argument(
        "--speech-enhancement", action="store_true",
        help="Enable the FastEnhancer denoise pre-filter on input audio",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Validate quantization.
    quant_spec = QUANTS[args.quantization]
    if not quant_spec.implemented:
        _LOGGER.error(
            "Quantization %s (%s) is not yet implemented. C kernels are needed.",
            args.quantization, quant_spec.label,
        )
        raise SystemExit(1)

    # Resolve chunk size.
    att_right = CHUNK_CHOICES.get(args.chunk_size)
    if att_right is None:
        _LOGGER.warning(
            "Unrecognized chunk_size '%s'; falling back to %s",
            args.chunk_size, DEFAULT_CHUNK_SIZE,
        )
        att_right = CHUNK_CHOICES[DEFAULT_CHUNK_SIZE]

    # 1. Download + convert (before cleanup — keep old model as fallback).
    _LOGGER.info(
        "Model: %s (quant=%s, chunk=%s)",
        args.model, args.quantization, args.chunk_size,
    )
    token = args.hf_token or os.environ.get("HF_TOKEN") or None
    bin_path = ensure_bin(args.model, args.quantization, args.model_dir, token)
    _LOGGER.info("Model .bin ready: %s", bin_path)

    # Extract SentencePiece tokenizer for hotword biasing.
    from pathlib import Path
    slug = args.model.replace("/", "_")
    tok_path = extract_tokenizer(
        Path(args.model_dir) / slug / f"{slug}.nemo",
        Path(args.model_dir) / slug,
    )

    # 2. Load C engine (before cleanup — verify new model works first).
    _LOGGER.info("Loading C engine from %s ...", bin_path)
    engine = NemoCEngine(
        args.lib_dir, str(bin_path),
        att_right=att_right,
        tokenizer_path=str(tok_path) if tok_path else None,
    )
    try:
        # Set hotwords if configured.  Accepts both a newline-separated
        # string (from jq join in the s6 run script) and a JSON array.
        hotwords_raw = args.hotwords.strip()
        if hotwords_raw.startswith("["):
            import json
            try:
                hotwords = json.loads(hotwords_raw)
            except json.JSONDecodeError:
                hotwords = [w.strip() for w in hotwords_raw.split("\n") if w.strip()]
        else:
            hotwords = [w.strip() for w in hotwords_raw.split("\n") if w.strip()]
        if hotwords:
            engine.set_hotwords(hotwords, args.hotword_boost)

        # Set thread count.
        cpu_count = os.cpu_count() or 4
        engine.set_threads(min(cpu_count, 16))

        # 3. Warmup (fault weights in from disk).
        _LOGGER.info("Warming up ...")
        engine.warmup(args.language)

        # 4. New model fully verified — safe to remove old ones.
        cleanup_old_models(args.model_dir, args.model)

        # 4b. Optional speech-enhancement pre-filter.
        enhancer = None
        if args.speech_enhancement:
            from .enhancer import FastEnhancer
            _LOGGER.info("Speech enhancement enabled — loading FastEnhancer ...")
            enhancer = FastEnhancer(args.lib_dir, FE_WEIGHTS)

        # 5. Build Wyoming Info.
        wyoming_info = _build_info(args.model)

        # 6. Start TCP server.
        server = AsyncServer.from_uri(args.uri)
        _LOGGER.info("Starting server on %s", args.uri)

        # 7. Optional Zeroconf registration.
        if args.zeroconf:
            if not isinstance(server, AsyncTcpServer):
                raise ValueError("Zeroconf requires a tcp:// URI")
            from wyoming.zeroconf import HomeAssistantZeroconf
            tcp_server: AsyncTcpServer = server
            hass_zc = HomeAssistantZeroconf(
                name=args.zeroconf, port=tcp_server.port, host=tcp_server.host
            )
            await hass_zc.register_server()
            _LOGGER.info("Zeroconf registered as %s", args.zeroconf)

        # 8. Run server.
        server_task = asyncio.create_task(
            server.run(partial(NemoCHandler, wyoming_info, args, engine, enhancer))
        )

        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, server_task.cancel)
        loop.add_signal_handler(signal.SIGTERM, server_task.cancel)
        try:
            await server_task
        except asyncio.CancelledError:
            _LOGGER.info("Server stopped")
    finally:
        engine.close()


def _main_sync() -> None:
    try:
        asyncio.run(main())
    except Exception:
        _LOGGER.exception("Fatal error during bootstrap")
        raise SystemExit(1)


if __name__ == "__main__":
    _main_sync()
