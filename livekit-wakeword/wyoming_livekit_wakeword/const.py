"""Constants and the known-model registry."""
from __future__ import annotations

from dataclasses import dataclass

SAMPLE_RATE = 16000
# Scoring cadence: one embedding per 80 ms of new audio (matches openWakeWord).
FRAME_SAMPLES = 1280
# One Google-speech-embedding input = 76 mel frames = exactly this many samples
# (hop 160, effective window 640: (12640 - 640) / 160 + 1 == 76).
EMB_BUFFER_SAMPLES = 12640
# Classifier input: the last 16 embeddings -> (1, 16, 96).
NUM_EMBEDDINGS = 16

# Seconds a model stays quiet after it fires (mirrors upstream's listener).
REFRACTORY_SECONDS = 2.0

DEFAULT_MODEL_DIR = "/data/models"
DEFAULT_CUSTOM_DIR = "/share/livekit-wakeword"

# Pinned upstream sources. livekit-wakeword distributes hey_livekit.onnx inside
# its repo (no registry/release asset); openWakeWord's zoo lives in its GitHub
# release. Both runtimes share the byte-identical frozen frontend, so oWW
# classifiers run unmodified here (verified, see AGENTS.md).
_LK_REF = "431c7e4376bd660180cf4a3adf1d95befc8eb57a"
_OWW_RELEASE = "https://github.com/dscripka/openWakeWord/releases/download/v0.5.1"


@dataclass(frozen=True)
class ModelSpec:
    url: str
    sha256: str
    phrase: str
    attribution_name: str
    attribution_url: str


KNOWN_MODELS: dict[str, ModelSpec] = {
    "hey_livekit": ModelSpec(
        url=(
            "https://raw.githubusercontent.com/livekit/livekit-wakeword/"
            f"{_LK_REF}/examples/ios_wakeword/WakewordDemo/Resources/hey_livekit.onnx"
        ),
        sha256="8bd634fb7acf1e52d06307fb8f460abf2c7a40e561fb4532fc56e087e0246f62",
        phrase="hey livekit",
        attribution_name="livekit-wakeword",
        attribution_url="https://github.com/livekit/livekit-wakeword",
    ),
    "alexa": ModelSpec(
        url=f"{_OWW_RELEASE}/alexa_v0.1.onnx",
        sha256="6ff566a01d12670e8d9e3c59da32651db1575d17272a601b7f8a39283dfbae3e",
        phrase="alexa",
        attribution_name="openWakeWord",
        attribution_url="https://github.com/dscripka/openWakeWord",
    ),
    "hey_jarvis": ModelSpec(
        url=f"{_OWW_RELEASE}/hey_jarvis_v0.1.onnx",
        sha256="94a13cfe60075b132f6a472e7e462e8123ee70861bc3fb58434a73712ee0d2cb",
        phrase="hey jarvis",
        attribution_name="openWakeWord",
        attribution_url="https://github.com/dscripka/openWakeWord",
    ),
    "hey_mycroft": ModelSpec(
        url=f"{_OWW_RELEASE}/hey_mycroft_v0.1.onnx",
        sha256="c2a311e8fa1338de89c31b3b46dc4dffd4af2f9a8d6ddead48893c2d301b1f18",
        phrase="hey mycroft",
        attribution_name="openWakeWord",
        attribution_url="https://github.com/dscripka/openWakeWord",
    ),
    "hey_rhasspy": ModelSpec(
        url=f"{_OWW_RELEASE}/hey_rhasspy_v0.1.onnx",
        sha256="5a9b3ed3be2910e35780e097905aa9f35a9c10038df47914cf2b3ec4d670f6ea",
        phrase="hey rhasspy",
        attribution_name="openWakeWord",
        attribution_url="https://github.com/dscripka/openWakeWord",
    ),
}
