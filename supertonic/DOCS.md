# Home Assistant App: Supertonic

Lightweight multilingual TTS over the Wyoming protocol, powered by MNN.

## Installation

1. **Settings** > **Apps** > **App Store**, add this repository.
2. Install **Supertonic** and start it.

First boot downloads the MNN model from Hugging Face (~80 MB int8 /
~150 MB fp16 / ~300 MB fp32) into `/data/.cache/supertonic-mnn`. The
Wyoming integration auto-discovers the app; confirm here:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=wyoming)

Ten voices ship in the model: `M1`–`M5`, `F1`–`F5`. Voice is picked
per-request by the Wyoming client.

## Options

There is **no language option** — Supertonic speaks whatever language your
Voice pipeline is set to (sent per request, like an STT engine). `model_version`
`v3` covers all 31 languages.

| Option          | Default | Description |
| --------------- | ------- | ----------- |
| `speed`         | 1.0     | 0.5–2.0 speed multiplier. |
| `steps`         | 4       | Denoising steps. 2–3 fastest, 4 balanced, 6+ slightly smoother. |
| `model_version` | v3      | `v3` = all 31 languages; `v2` = en/ko/es/pt/fr only. |
| `warmup_voices` | `[M1]`  | Voices pre-loaded at startup so their first request is instant. |

### Advanced (optional, leave unset for sane defaults)

These options exist in the schema but are blank by default. Leave them
empty and the values listed below are used. Only set them if you have
a specific reason to override.

| Option          | Default when unset | Override |
| --------------- | ------------------ | -------- |
| `threads`       | auto (`os.cpu_count()`) | Positive integer to pin MNN thread pool size. |
| `precision`     | `auto`            | `fp16` / `fp32` / `int8` to force a precision (default `auto` picks from `/proc/cpuinfo`). |
| `mnn_memory`    | `normal`          | `low` (RAM-tight) / `high` (RAM-for-speed). |
| `no_streaming`  | `false`           | `true` to disable sentence-by-sentence streaming. |
| `debug_logging` | `false`           | `true` to enable DEBUG logs. |

## Performance

The boot log prints per-core CPU diagnostics:

```
CPU diagnostics (cur / scaling_max / cpuinfo_max, governor):
  cpu0: 800 MHz / 800 MHz / 3400 MHz, governor=powersave
```

Under load, `cur` should rise toward `scaling_max`. If it stays at base
clock, your host is throttling (BIOS turbo off, `powersave` governor,
or thermal). The app can't fix host-level throttling — but the
diagnostic tells you where to look.

Rough RTF expectations (steps=4):

| Host                         | precision | RTF |
| ---------------------------- | --------- | --- |
| Modern x86 desktop / M-series| int8/fp16 | 0.05–0.15 |
| Intel N100 (Turbo on)        | int8      | 0.3–0.6 |
| Intel N100 (Turbo off, 6 W)  | int8      | ~2 |
| Raspberry Pi 5 (cooled)      | int8      | 0.7–1.0 |
| Raspberry Pi 4               | fp32      | ≥ 3 |

Each request logs `RTF` (CPU time ÷ audio duration) and `TTFT`
(request → first audio chunk).

## Network

| Port    | Description                |
| ------- | -------------------------- |
| `10209` | Wyoming protocol endpoint  |

## Support

[Open an issue on GitHub](https://github.com/saya6k/ha-app-supertonic-v3/issues).
