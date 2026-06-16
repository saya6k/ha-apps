"""Wyoming wake word server — livekit-wakeword runtime."""
from __future__ import annotations

import argparse
import asyncio
import logging
from functools import partial

from wyoming.info import Attribution, Info, WakeModel, WakeProgram
from wyoming.server import AsyncServer

from . import __version__
from .const import DEFAULT_CUSTOM_DIR, DEFAULT_MODEL_DIR
from .engine import Engine
from .handler import WakeWordHandler
from .models import ResolvedModel, resolve_models

_LOGGER = logging.getLogger(__name__)


def _build_info(models: list[ResolvedModel]) -> Info:
    return Info(
        wake=[
            WakeProgram(
                name="livekit-wakeword",
                attribution=Attribution(
                    name="livekit-wakeword",
                    url="https://github.com/livekit/livekit-wakeword",
                ),
                installed=True,
                description="On-device wake word detection (livekit-wakeword runtime)",
                version=__version__,
                models=[
                    WakeModel(
                        name=m.name,
                        attribution=Attribution(
                            name=m.attribution_name, url=m.attribution_url
                        ),
                        installed=True,
                        description=f"Wake word: {m.phrase}",
                        version="1.0.0",
                        languages=["en"],
                        phrase=m.phrase,
                    )
                    for m in models
                ],
            )
        ]
    )


async def run(args: argparse.Namespace) -> None:
    models = resolve_models(args.models, args.model_dir, args.custom_model_dir)
    if not models:
        raise RuntimeError("No wake word models could be loaded")

    engine = Engine(models)
    engine.warmup()

    server = AsyncServer.from_uri(args.uri)
    _LOGGER.info(
        "Ready: %d model(s) [%s], threshold=%.2f, trigger_level=%d, listening on %s",
        len(models), ", ".join(m.name for m in models),
        args.threshold, args.trigger_level, args.uri,
    )
    await server.run(partial(WakeWordHandler, _build_info(models), args, engine))


def main() -> None:
    parser = argparse.ArgumentParser(description="Wyoming wake word server — livekit-wakeword")
    parser.add_argument("--uri", default="tcp://0.0.0.0:10400")
    parser.add_argument(
        "--models", nargs="+", default=["hey_jarvis"],
        help="Built-in model names to load (downloaded on first start)",
    )
    parser.add_argument("--model-dir", default=DEFAULT_MODEL_DIR)
    parser.add_argument(
        "--custom-model-dir", default=DEFAULT_CUSTOM_DIR,
        help="Every *.onnx here is loaded as an additional wake word model",
    )
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--trigger-level", type=int, default=1,
        help="Consecutive frames at/above threshold required to fire",
    )
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
