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
| `f32` | Float32 — no quantization, bit-exact, largest |
| `bf16` | BFloat16 linear weights — ~half size |
| `w8a16` | Int8 weights + fp16 compute (planned) |
| `q8p` | W8A8 packed int8 — default, fastest |
| `q4p` | 4-bit packed (planned) |

### `chunk_size` (list)

Streaming encoder lookahead. Larger = more accurate, slightly more compute.

| Value | att_right | Latency |
|---|---|---|
| `80ms` | 0 | Lowest latency |
| `160ms` | 1 | — |
| `320ms` | 3 | Default |
| `560ms` | 6 | — |
| `1120ms` | 13 | Most accurate |

### `hotwords`

Phrases to bias recognition toward. One per item. Best-effort greedy biasing.

### `hotword_boost`

Strength of hotword bias (logit bonus per token). Default 2.0. Range 0–10.

### `hf_token`

Optional HuggingFace access token for gated/private model repos.

### `debug_logging`

Enable verbose logging for troubleshooting.
