# Home Assistant Add-on: LiveKit WakeWord

On-device wake word detection over the Wyoming protocol, on the
[livekit-wakeword](https://github.com/livekit/livekit-wakeword) runtime.
Streaming inference costs ~4 ms per 80 ms frame on a modern x86 core
(openWakeWord-class CPU use) — fine for Raspberry Pi 4/5, HA Green, N100.

## Installation

Install and start the add-on, then add the discovered **Wyoming** service in
**Settings → Devices & Services**. Pick the wake word in your voice
assistant pipeline (**Settings → Voice assistants**).

Built-in models download on first start (~300 KB each, checksum-verified)
into the add-on data volume; first start needs internet access.

## Options

| Option | Default | Description |
| ------ | ------- | ----------- |
| `models` | `[hey_jarvis]` | Built-in models to load. All loaded models listen simultaneously. |
| `threshold` | `0.5` | Activation probability required to trigger (0–1). |
| `trigger_level` | `1` | Consecutive 80 ms frames at/above threshold required to fire. Raise to 2–3 against brief false positives. |
| `debug_logging` | `false` | Verbose logs, including per-frame scores. |

## Built-in models

| Model | Phrase | Source |
| ----- | ------ | ------ |
| `hey_livekit` | "hey livekit" | livekit-wakeword (Apache 2.0) |
| `alexa` | "alexa" | openWakeWord (Apache 2.0) |
| `hey_jarvis` | "hey jarvis" | openWakeWord (Apache 2.0) |
| `hey_mycroft` | "hey mycroft" | openWakeWord (Apache 2.0) |
| `hey_rhasspy` | "hey rhasspy" | openWakeWord (Apache 2.0) |

openWakeWord models run here unmodified because both projects share the same
frozen audio frontend (mel spectrogram + Google speech embedding).

## Custom models

Place `.onnx` wake word classifiers in `/share/livekit-wakeword` — every file
there is loaded automatically, named after its filename. Both classifier
formats work:

- models trained with the
  [livekit-wakeword training pipeline](https://github.com/livekit/livekit-wakeword#training-a-custom-wake-word)
  (any head, including the higher-accuracy `conv_attention`; 30+ languages
  via VoxCPM2 synthetic data), and
- openWakeWord `.onnx` classifiers.

The expected ONNX input is the shared `(1, 16, 96)` embedding matrix.

## Tuning

- With `debug_logging` on, every 80 ms frame logs `model=score` — watch real
  scores before changing `threshold`.
- After a detection the stream has a 2-second cooldown.
