---
name: nemo-asr-cpp-chunk-size
description: Plan + verified mechanism for adding a chunk-size (accuracy/speed) dial to the nemo-asr-cpp add-on via a GGUF KV edit
metadata: 
  node_type: memory
  type: project
  originSessionId: 1136ae39-745d-4f72-9141-14c373fa49fa
---

Adding a `chunk_size` (accuracy↔speed) option to **nemo-asr-cpp** (decided 2026-06-15; user chose this add-on over nemotron-asr because it needs no engine refactor).

**Mechanism (verified by parakeet.cpp source @ pinned REF e270af7 + live GGUF metadata):**
- The cache-aware operating point is the scalar GGUF KV `parakeet.encoder.att_context_right` (with `att_context_style=chunked_limited`). `model_loader.cpp:143` reads the scalar; `relpos_attention.cpp` builds the chunked-limited mask from it; `conformer.cpp` uses it in the **offline** encoder path too (parity.md 5a: offline limited-context WER 0). So our buffered `transcribe_pcm_lang` honors it.
- `att_context_presets` KV is **informational only** — not read by the C++ loader.
- `PARAKEET_ATT_CONTEXT` env var is NOT the dial — it forces symmetric [W,W] local attention (long-audio OOM guard), different mechanism.

**Approach (b), confirmed cheapest:** edit ONE INT32 KV in-place (same byte width, no file rewrite, no re-quant, no GPU, no re-download). Patch the downloaded GGUF's `att_context_right` at add-on boot per the option. Add-on already depends on the `gguf` python lib ([[parakeet-hotword-patch]]).

**Live `mudler/parakeet-cpp-gguf` nemotron-3.5 q4_k metadata:** `att_context_style=chunked_limited`, `att_context_left=56`, **`att_context_right=3` (current default = [56,3] = 320ms, NOT 560ms)**, `att_context_presets=[56,3,56,0,56,6,56,13]`.

**Trained presets = 4 only:** right ∈ {0,3,6,13} = 80/320/560/1120 ms. **No 160ms** ([56,1] absent — don't expose it, untrained). chunk = att_right+1; ms = chunk×80.

**Plan:** config.yaml `chunk_size` dropdown (4 modes, default 320ms = current behavior) + const.py label→att_right map + models.py KV in-place patch helper + __main__ wiring + translations + DOCS/AGENTS notes. No engine/model changes. Status: verified, not yet implemented.
