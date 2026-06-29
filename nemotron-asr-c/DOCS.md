# Configuration

## Options

### `model` (string)

HuggingFace repository ID containing the `.nemo` model file. Any
Nemotron-architecture `.nemo` — including fine-tuned variants — is supported.
Default: `nvidia/nemotron-3.5-asr-streaming-0.6b`.

### `quantization` (list)

Weight precision of the converted `.bin` runtime file.

| Value | Description |
|---|---|
| `f32` | Float32 — no quantization, bit-exact reference, largest |
| `q8p` | W8A8 packed int8 — default, fastest |

### `chunk_size` (list)

Streaming encoder lookahead. Larger = more accurate, slightly more compute.

| Value | att_right | Latency |
|---|---|---|
| `80ms` | 0 | Lowest latency |
| `160ms` | 1 | — |
| `320ms` | 3 | Default |
| `560ms` | 6 | — |
| `1120ms` | 13 | Most accurate |

### `hf_token`

Optional HuggingFace access token for gated/private model repos.

### `speech_enhancement` (bool)

Run a lightweight [FastEnhancer](https://github.com/kdrkdrkdr/fastenhancer.c.wasm)
denoise filter on incoming 16 kHz audio before transcription. Can improve
accuracy in noisy rooms, but may slightly degrade already-clean audio. Default:
`false`.

### `log_level`

Log verbosity, using Home Assistant log level names. One of `trace`, `debug`,
`info`, `notice`, `warning`, `error`, `fatal`. Use `debug` (or `trace`) for
troubleshooting. Default: `info`.
