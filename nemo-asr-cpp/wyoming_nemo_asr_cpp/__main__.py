"""Entry point: python -m wyoming_nemo_asr_cpp ...

Downloads the chosen GGUF quant, loads it once into a resident parakeet.cpp
context, warms up, then serves the Wyoming ASR protocol.
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
    DEFAULT_CHUNK,
    DEFAULT_MODEL,
    DEFAULT_PORT,
    GGUF_REPO,
    LANGUAGES,
    LIB_DIR,
    MODEL_DIR,
    ModelSpec,
    resolve_chunk,
    resolve_model,
)

_LOGGER = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="wyoming_nemo_asr_cpp")
    parser.add_argument("--uri", default=f"tcp://0.0.0.0:{DEFAULT_PORT}")
    parser.add_argument("--lib-dir", default=LIB_DIR)
    parser.add_argument("--model-dir", default=MODEL_DIR)
    parser.add_argument("--gguf-repo", default=GGUF_REPO)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--quantization", default="q4_k")
    parser.add_argument(
        "--chunk-size",
        default=DEFAULT_CHUNK,
        help="Streaming operating point (accuracy<->speed): larger = more "
        "lookahead/accuracy, more compute. Patched into the GGUF att_context_right.",
    )
    parser.add_argument("--language", default=None)
    parser.add_argument(
        "--hotwords",
        default="",
        help="Newline-separated phrases to bias recognition toward.",
    )
    parser.add_argument(
        "--hotword-boost",
        type=float,
        default=2.0,
        help="Logit bonus per hotword token during greedy decode.",
    )
    parser.add_argument("--hf-token", default=os.environ.get("HF_TOKEN", ""))
    parser.add_argument("--zeroconf", nargs="?", const="nemo-asr-cpp", default=None)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--app-version", action="version", version=__version__)
    return parser.parse_args()


def _build_info(model_label: str, spec: ModelSpec) -> "Info":  # noqa: F821
    from wyoming.info import AsrModel, AsrProgram, Attribution, Info

    attr = Attribution(
        name="parakeet.cpp (ggml) / NVIDIA NeMo ASR",
        url="https://github.com/mudler/parakeet.cpp",
    )
    # English-only Parakeet models ignore the language prompt; advertise en only.
    langs = list(LANGUAGES) if spec.multilingual else ["en"]
    return Info(
        asr=[
            AsrProgram(
                name="NeMo ASR (cpp)",
                description="NVIDIA NeMo ASR on ggml (parakeet.cpp)",
                attribution=attr,
                installed=True,
                version=__version__,
                supports_transcript_streaming=False,
                models=[
                    AsrModel(
                        name=spec.basename,
                        description=model_label,
                        attribution=attr,
                        installed=True,
                        version=None,
                        languages=langs,
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
    spec = resolve_model(args.model)
    _LOGGER.info(
        "Booting wyoming_nemo_asr_cpp %s (model=%s, quant=%s, chunk=%s)",
        __version__, args.model, args.quantization, args.chunk_size,
    )

    from .engine import ParakeetASR

    try:
        gguf = models.ensure_gguf(
            spec.basename, args.quantization, args.model_dir,
            repo=args.gguf_repo, token=args.hf_token,
        )
        # Apply the chunk-size dial by editing the GGUF's att_context_right KV in
        # place (no re-download). No-ops safely on non-streaming models.
        att_right = resolve_chunk(args.chunk_size)
        models.set_att_context_right(gguf, att_right)
        hotwords = [w.strip() for w in args.hotwords.split("\n") if w.strip()]
        if hotwords and not spec.hotwords:
            _LOGGER.warning(
                "Model '%s' has no hotword-biasing decoder; ignoring %d hotword(s). "
                "Use a Nemotron / RNN-T model for hotword support.",
                args.model, len(hotwords),
            )
            hotwords = []
        engine = ParakeetASR(
            args.lib_dir, gguf,
            hotwords=hotwords, hotword_boost=args.hotword_boost,
        )
        engine.warmup(args.language)
    except Exception as err:  # noqa: BLE001 - any setup failure -> graceful stop
        _LOGGER.error("Model setup failed: %s", err)
        _LOGGER.error(
            "Check the quant name, hf_token, disk space, and that libparakeet.so "
            "+ ggml libs are in --lib-dir. Shutting down."
        )
        if args.debug:
            _LOGGER.exception("Full traceback (debug):")
        raise SystemExit(1)

    wyoming_info = _build_info(args.model, spec)

    from wyoming.server import AsyncServer, AsyncTcpServer

    server = AsyncServer.from_uri(args.uri)
    if args.zeroconf:
        if not isinstance(server, AsyncTcpServer):
            raise ValueError("Zeroconf requires a tcp:// uri")
        try:
            from wyoming.zeroconf import HomeAssistantZeroconf

            tcp: AsyncTcpServer = server
            await HomeAssistantZeroconf(
                name=args.zeroconf, port=tcp.port, host=tcp.host
            ).register_server()
        except ImportError:
            _LOGGER.warning("Zeroconf requested but wyoming[zeroconf] not installed")

    _LOGGER.info("Ready (uri=%s)", args.uri)

    from .handler import ParakeetEventHandler

    server_task = asyncio.create_task(
        server.run(partial(ParakeetEventHandler, wyoming_info, args, engine))
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
