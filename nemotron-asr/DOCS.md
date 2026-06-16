# Home Assistant App: Nemotron ASR

Multilingual speech-to-text over the Wyoming protocol, powered by NVIDIA
Nemotron streaming ASR (ONNX, CPU).

## Installation

1. **Settings** > **Apps** > **App Store**, add this repository.
2. Install **Nemotron ASR** and start it.

First boot downloads the ONNX model (~1.4 GB) from Hugging Face into
`/data/models`. Then confirm the Wyoming integration discovered it:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=wyoming)

## Options

| Option          | Default | Description |
| --------------- | ------- | ----------- |
| `language`      | Auto    | Fallback language (native-name dropdown) when the pipeline doesn't send one. `Auto` = model auto-detect. Per-request language always wins. |
| `num_threads`   | 0       | ONNX Runtime intra-op threads. 0 = all cores. |
| `model_repo`    | `nub235/nemotron-3.5-asr-streaming-onnx` | HuggingFace repo id of the ONNX export. |
| `hotwords`      | (none)  | Phrases to bias toward (room/entity/person names), one per item. |
| `hotword_boost` | 2.0     | Advanced. Strength of the hotword bias. |
| `hf_token`      | (empty) | HuggingFace token for gated/private repos. |
| `debug_logging` | false   | Verbose logging for troubleshooting. |

## Performance

This is a 0.6B INT4 model running on CPU; the **encoder dominates** runtime and
is very **clock-sensitive**. On a modern x86 desktop expect RTF well under 1. On
an Intel N100 the result depends almost entirely on whether the CPU is allowed
to clock up:

| N100 state                         | rough RTF |
| ---------------------------------- | --------- |
| Turbo on / governor=performance    | ~0.5–1.0  |
| Turbo off / pinned at 800 MHz base | **5–8** (unusable) |

If your RTF is in the 5–8 range, the host is throttling — **not** a model
problem. At boot the add-on logs CPU diagnostics so you can see it:

```
CPU ISA: avx2, avx_vnni
CPU diagnostics (cur / scaling_max / cpuinfo_max, governor):
  cpu0: 800 MHz / 800 MHz / 3400 MHz, governor=powersave
WARNING ... Intel turbo is DISABLED (intel_pstate/no_turbo=1) ...
```

If `cur` sits at base clock under load, fix it at the host level: enable turbo
in BIOS, set the CPU governor to `performance`, and check cooling. The add-on
can't override host throttling. Also set `num_threads` to your physical core
count (4 on N100) if auto-detection looks wrong in the boot log.

Each transcription logs:

```
Transcript (1.20s for 3.50s audio, RTF=0.34) [lang=ko]: '안녕하세요 ...'
```

## Languages

The model supports 40+ locales via a language prompt. Common pipeline
languages are advertised to Home Assistant; the actual locale is chosen from
the per-request language (or the `language` fallback option).

## Network

| Port    | Description                  |
| ------- | ---------------------------- |
| `10350` | Wyoming protocol endpoint    |

## Streaming

Transcription is incremental: partial text is emitted while you speak (Wyoming
`TranscriptChunk`) and a final transcript is sent at end-of-speech. Because most
decoding happens *during* speech, the delay after you stop talking is small even
on slower CPUs.

## Troubleshooting

Validated end-to-end in English + Korean, including on a Raspberry Pi 5. If
transcripts look wrong or latency is high, enable `debug_logging` and check the
boot log for clock throttling (Performance section) before opening an issue.

## License

The Nemotron ASR model (downloaded at first boot) is © NVIDIA Corporation and
is licensed under the [NVIDIA Open Model License](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/).
This add-on software is Apache-2.0.
