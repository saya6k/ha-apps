# Spec: RNN-T Hotword Boost for nemotron-asr-c

## Objective

nemotron-3.5-asr-streaming 모델의 RNN-T greedy decoder에 **hotword (contextual) biasing**을 구현한다. 사용자가 등록한 키워드/문구 목록이 음성 인식 결과에 더 잘 잡히도록, decoder의 logit에 boost를 더해 해당 토큰이 선택될 확률을 높인다.

**User:** Home Assistant에서 "Hey Jarvis" 같은 특정 웨이크워드 이후의 음성을 더 정확히 인식하고 싶은 사용자. 스마트홈 기기 이름, 지역명, 전문 용어 등 모델이 잘못 인식하기 쉬운 고유명사를 정확히 잡는 것이 목표.

**Success criteria:**
- Wyoming `Transcribe` 이벤트로 hotword list가 전달되면, 해당 phrase들이 인식 결과에 더 잘 포착된다
- hotword가 없을 때는 기존과 bit-identical한 결과를 낸다 (no regression)
- boost는 near-tie 상황만 뒤집는 best-effort 방식 — 없는 단어를 만들어내지 않는다

## Tech Stack

- **C runtime:** kdrkdrkdr/nemotron-asr-streaming.c @ `4fde8b47` (pinned, with vendored patches)
- **Tokenizer:** SentencePiece (`tokenizer.model` extracted from `.nemo` at boot)
- **Python bridge:** ctypes over `libnemotron_asr.so`
- **Protocol:** Wyoming (Transcribe event carries per-utterance hotwords)

## Commands

```bash
# Build (from nemotron-asr-c/)
docker build .

# Lint
python3 -c "import ast,glob;[ast.parse(open(f).read()) for f in glob.glob('wyoming_nemo_asr_c/*.py')]"
yamllint config.yaml translations/*.yaml
shellcheck rootfs/etc/s6-overlay/s6-rc.d/nemotron-asr-c/run

# Smoke test
echo '{"type":"describe"}' | nc -w 1 localhost 10370 | grep -qi nemo

# End-to-end with hotwords
echo '{"type":"transcribe","data":{"language":"ko","hotwords":["홈어시스턴트","거실"]}}' | nc -w 1 localhost 10370
# ... followed by AudioStart / AudioChunk / AudioStop
```

## Project Structure

```
nemotron-asr-c/
  patches/
    0001-shared-lib.patch          # existing: PIC + .so build
    0002-set-att-right.patch       # existing: nemo_set_att_right/get
    0003-rnnt-hotword-biasing.patch  # NEW: hotword bias in RNN-T decoder
  tools/
    convert_nemo.py                # modified: also extract tokenizer.model
  wyoming_nemo_asr_c/
    __main__.py    # + --hotwords/--hotword-boost CLI args
    engine.py      # + nemo_set_hotwords ctypes binding + vocab access
    handler.py     # + extract hotwords from Transcribe event
    models.py      # maybe: tokenizer extraction during conversion
    const.py       # + HOTWORD_BOOST_DEFAULT
  config.yaml      # + hotwords, hotword_boost options
  Dockerfile       # + sentencepiece pip package
```

## Architecture

```
config.yaml / CLI args
  hotwords: "거실,주방,홈어시스턴트"
  hotword_boost: 2.0
       │
       ▼
  __main__.py: tokenize each phrase via SentencePiece
       │
       ▼
  engine.py: NemoCEngine.set_hotwords(phrases, boost)
       │
       ▼
  libnemotron_asr.so → nemo_set_hotwords(ctx, ids, lens, n, boost)
       │
       ▼
  nemo_ctx_t {
    + hotword_ids (int32_t*)      // concatenated token-id sequences
    + hotword_lens (int*)         // phrase lengths
    + hotword_n (int)             // number of phrases
    + hotword_boost (float)       // logit bonus
  }
       │
       ▼
  nemo_rnnt_stream_accept()     ← global hotwords applied here
    nemo_rnnt_stream_t {
      + hot_active pairs          // carried across frames
    }
       │
       ▼
  joint_argmax() 대신 hotword-aware argmax:
    for each token in vocab:
      logit += boost if token starts/continues a hotword
    → argmax
       │
       ▼
  advance hot_active matches on emitted tokens
```

### Key design decisions

- **Hotwords stored in `nemo_ctx_t` (global), active matches in `nemo_rnnt_stream_t` (per-stream).** Hotword definitions are set once; each stream tracks its own partial match progress independently. This is safe because `ASR_LOCK` serializes stream access.
- **Tokenizer runs in Python, not C.** The SentencePiece model is loaded once at boot; Python tokenizes phrases → passes int32 token IDs to C. This avoids pulling SentencePiece into the C build and reuses the tokenizer already present in the `.nemo`.

## Code Style

C 패치는 upstream 스타일을 그대로 따른다. Python bridge는 기존 `engine.py`/`handler.py`와 동일한 패턴을 사용한다.

### C layer (nemotron_asr.h + nemotron_asr_decoder.c modifications)

```c
// In nemo_ctx_t (nemotron_asr.h) — global, set once at boot:
//   + int32_t *hw_ids;       // concatenated token-id sequences (malloc'd)
//   + int *hw_lens;           // length of each phrase
//   + int hw_n;               // number of phrases (0 → no biasing)
//   + float hw_boost;         // logit bonus

// New public API (nemotron_asr.h):
// void nemo_set_hotwords(nemo_ctx_t *ctx, const int32_t *ids,
//                         const int *lens, int n, float boost);

// In nemo_rnnt_stream_t (nemotron_asr_decoder.c) — per-stream, tracks progress:
struct nemo_rnnt_stream_t {
    // ... existing fields (h, c, enc_proj, pred_out, pred_proj, text) ...
    // Active hotword partial matches: (phrase_idx, matched_prefix_len) pairs.
    // Carried across encoder frames alongside the RNN-T state.
    int hw_active_cap;
    int hw_active_len;
    int *hw_active_pairs;   // flat: [p0, len0, p1, len1, ...]
};
```

### C layer (nemotron_asr.c — nemo_set_hotwords implementation)

```c
void nemo_set_hotwords(nemo_ctx_t *ctx, const int32_t *ids,
                       const int *lens, int n, float boost) {
    if (!ctx) return;
    free(ctx->hw_ids);
    free(ctx->hw_lens);
    ctx->hw_ids = NULL;
    ctx->hw_lens = NULL;
    ctx->hw_n = 0;
    ctx->hw_boost = 0.0f;
    if (ids && lens && n > 0 && boost != 0.0f) {
        int total = 0;
        for (int i = 0; i < n; i++) total += lens[i];
        ctx->hw_ids = (int32_t *)malloc((size_t)total * sizeof(int32_t));
        ctx->hw_lens = (int *)malloc((size_t)n * sizeof(int));
        if (ctx->hw_ids && ctx->hw_lens) {
            memcpy(ctx->hw_ids, ids, (size_t)total * sizeof(int32_t));
            memcpy(ctx->hw_lens, lens, (size_t)n * sizeof(int));
            ctx->hw_n = n;
            ctx->hw_boost = boost;
        }
    }
}
```

### Python layer (engine.py additions)

```python
# New method on NemoCEngine:
def set_hotwords(self, phrases: list[str], boost: float) -> None:
    """Tokenize phrases and pass token IDs to the C runtime."""
    ids_flat = []
    lens = []
    for phrase in phrases:
        tokens = self._sp.EncodeAsIds(phrase)
        ids_flat.extend(tokens)
        lens.append(len(tokens))
    # Pass to C (applied to the shared ctx; per-stream hotwords TBD)
    ...

# New method on NemoCStream (per-utterance):
def set_hotwords(self, phrases: list[list[int]], boost: float) -> None:
    """Set hotword token-id sequences for this stream."""
    ...
```

## Data Flow

```
1. Boot:
   convert_nemo.py extracts tokenizer.model from .nemo → /data/models/<slug>/tokenizer.model
2. Engine init:
   NemoCEngine loads tokenizer.model via sentencepiece
   Reads hotwords/hotword_boost from CLI args → tokenizes → calls nemo_set_hotwords()
   (Global setting, applied to every stream — matches nemotron-asr pattern)
3. Per utterance:
   NemoCStream created → inherits global hotword state from engine
   (Future: Wyoming Transcribe event may carry per-utterance hotwords via context dict)
4. Each accept_audio() → _feed_encoder() → nemo_encoder_forward_chunks()
   → nemo_rnnt_stream_accept() applies boost during greedy decode
5. stream.finalize() / stream.text() returns text with hotword-boosted recognition
```

### Why global, not per-utterance?

nemotron-asr uses global hotwords (set at boot). The Wyoming `Transcribe` event has a
`context: dict` field that could carry hotwords per-utterance, but no standard
convention exists yet. Starting with global hotwords keeps the initial implementation
simple and matches the existing nemotron-asr pattern. Per-utterance override can be a
follow-up when the Wyoming protocol standardizes the hotword context key.

## Testing Strategy

### Unit tests
- **Python:** tokenizer extraction from `.nemo`, `set_hotwords` parameter validation
- **C:** hotword matching logic (unit-testable if we extract the decode loop)

### Integration tests
- **Hotword effect:** feed known audio with/without hotwords; verify hotword phrase appears more often with boost
- **No regression:** feed audio with empty hotword list; verify output is bit-identical to pre-patch
- **Multi-phrase:** verify multiple hotwords don't interfere with each other

### Manual verification
- Docker build + smoke test
- Wyoming client sends a `Transcribe` event with hotwords, then audio, then checks transcript

## Options (config.yaml additions)

```yaml
options:
  # ... existing ...
  hotwords: ''
  hotword_boost: 2.0
schema:
  # ... existing ...
  hotwords: str?           # newline-separated list, optional
  hotword_boost: float?    # logit bonus, default 2.0 if hotwords are set
```

Per-utterance hotwords from `Transcribe` event override the config option (if both present, the event's list wins — same as `language` override pattern).

## Boundaries

- **Always:**
  - Apply boost in greedy decode loop only (not beam search — no beam exists anyway)
  - Track partial matches across encoder frames (carry in stream state)
  - Tokenize via SentencePiece (use the model's own tokenizer)
  - Strip language tags from output regardless of hotword state
  - Test that empty/no hotwords produces bit-identical output

- **Ask first:**
  - Changing the boost application strategy (e.g., decaying boost over time, context-window limits)
  - Adding beam search or other decode strategies
  - Changing the tokenizer or vocabulary handling
  - Per-stream vs global ctx hotword state design change

- **Never:**
  - Hardcode vocabulary — always read from model
  - Modify upstream nemotron_asr.h directly — always use patches
  - Change the `.bin` format — hotword data stays in stream state, not in the model file
  - Skip the SentencePiece tokenization and use simple string matching

## Open Questions

1. **Per-stream vs global hotwords?** → **Resolved: Global (ctx-level) for now**, matching nemotron-asr's `--hotwords` CLI pattern. Hotwords are set once at boot and applied to every stream. Per-stream hotwords (from Wyoming Transcribe event's `context` dict) is a follow-up when the protocol supports it.

2. **Tokenizer model location.** The SentencePiece `tokenizer.model` is inside the `.nemo` archive. `convert_nemo.py` uses PyTorch to read the checkpoint. → **Resolved: Extract to `data/<model>/tokenizer.model`** during `convert_nemo.py` execution. The Python bridge loads it at engine init.

3. **Default boost value?** → **Resolved: 2.0**, matching nemotron-asr's default. User-visible in config.yaml.

4. **C hotword storage location.** → **Resolved: `nemo_ctx_t`** (global, set once). If per-stream hotwords are needed later, we can add a `nemo_rnnt_stream_set_hotwords()` then. For now, storing in `nemo_ctx_t` is simpler and sufficient.

## Risks

- **Tokenizer dependency:** SentencePiece Python package must be installed in the runtime container. It's lightweight and already implicitly available (torch depends on it in some environments), but we must add it explicitly to `Dockerfile`.
- **Concurrent stream safety:** The ctypes/ASR_LOCK serialize access, so per-stream hotword state won't race. But if we put hotwords on the shared `nemo_ctx_t`, two streams could overwrite each other's hotwords. → Use per-stream storage.
- **Tokenizer mismatch:** The extracted `tokenizer.model` must match the model's vocabulary exactly. Since both come from the same `.nemo`, this is guaranteed.
