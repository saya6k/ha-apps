"""Constants for the voiceprint proxy."""

SAMPLE_RATE = 16000

# CAM++ zh_en advanced (3D-Speaker, Apache 2.0), converted to a fixed-shape
# TFLite graph: input (1, 80, 500) fbank, output (1, 192) embedding.
# 500 frames = 5.0 s; shorter audio is repeat-padded, longer is cropped.
# Regeneration recipe lives in .agents/runtime-experiment (gitignored).
NUM_FRAMES = 500
NUM_MELS = 80
EMBEDDING_DIM = 192
MODEL_SHA256 = "c245a86cc093d165692929602a10fb42ff4ba4352bd9d5b04907a94b422d30d6"

# Edge-trim: frames quieter than max RMS * this factor are silence.
TRIM_RMS_FACTOR = 0.1

# The 14 MB TFLite model is not vendored in the image — it is fetched once into
# the persistent /data volume on first run and verified against MODEL_SHA256.
# Hosted as a pinned GitHub release asset (version-independent tag so an app
# release doesn't require re-uploading it). Keep the tag/filename in sync with
# the actual uploaded asset.
MODEL_FILENAME = "campplus_zh_en_fp16.tflite"
MODEL_DIR = "/data"
MODEL_URL = (
    "https://github.com/saya6k/ha-apps/releases/download/"
    "voiceprint-model-v1/campplus_zh_en_fp16.tflite"
)
DEFAULT_ENROLL_DIR = "/share/voiceprint"

# Fixed location for `capture: true` dumps (a "_" dir → not enrolled as a
# speaker). Keep in sync with the run script's mkdir path.
CAPTURE_DIR = "/share/voiceprint/_captures"
