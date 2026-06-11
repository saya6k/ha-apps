# Home Assistant App: NeMo ASR (cpp)

Fast multilingual speech-to-text over Wyoming — NVIDIA Nemotron streaming ASR on
the ggml runtime (parakeet.cpp).

## Installation

1. **Settings** > **Apps** > **App Store**, add this repository.
2. Install **NeMo ASR (cpp)** and start it.

First boot compiles nothing on your device — the add-on image already contains
`libparakeet`. It downloads the chosen GGUF model into `/data/models`
(~720 MB for `q4_k`). Then confirm the Wyoming integration discovered it:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=wyoming)

## Options

| Option          | Default | Description |
| --------------- | ------- | ----------- |
| `language`      | Auto    | Fallback language (native-name dropdown) when the pipeline doesn't send one. `Auto` = model auto-detect. Per-request language always wins. |
| `quantization`  | q4_k    | GGUF weight precision: `q4_k` (smallest/fastest) → `f16` (best quality). Changing re-downloads the model. |
| `hotwords`      | []      | Phrases to bias recognition toward — one per item (room names, entity names, people). |
| `hotword_boost` | 2       | Advanced. Bias strength (logit bonus per token). Values above ~3 can destabilize decoding. |
| `hf_token`      | (empty) | HuggingFace token for gated/private repos. |
| `debug_logging` | false   | Verbose logging. |

## Hotwords

List phrases the model should prefer when the audio is ambiguous — names of
rooms, devices, or people it otherwise mishears. Biasing is best-effort: it
nudges the greedy decoder at near-ties, it cannot force words that weren't
spoken. Keep the boost at the default unless a hotword still loses; raising it
past ~3 trades accuracy everywhere else and can garble output.

## vs. the Nemotron ASR add-on

Same model, different runtime. This one (ggml) is faster on CPU and lighter on
RAM/disk. Run whichever fits — or both, on different ports.

## Performance

The model is resident (loaded once), so each command is pure compute. Expect
real-time on a modern x86 host and on a Raspberry Pi 5 at full clock; on a
low-power N100, ensure the CPU isn't clock-throttled. Each transcription logs:

```
Transcript (0.7s for 3.0s audio, RTF=0.23) [lang=ko]: '...'
```

`RTF` is wall time ÷ audio duration; < 1 means faster than real time. Drop
`quantization` to `q4_k` (default) for the lowest latency/RAM.

## Network

| Port    | Description                    |
| ------- | ------------------------------ |
| `10360` | Wyoming protocol endpoint      |

## Troubleshooting

If transcripts look wrong or latency is high, enable `debug_logging` and check
the boot log. The browser mic in the dashboard needs HTTPS/localhost (a `[object
Object]` error there is a browser secure-context issue, not this add-on).
