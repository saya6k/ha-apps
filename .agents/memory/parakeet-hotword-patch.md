---
name: parakeet-hotword-patch
description: "Hotword biasing ships as a vendored patch in nemo-asr-cpp (patches/0001, ABI v5); GGUF lacks SPM scores so the bridge registers two greedy segmentation variants per phrase"
metadata: 
  node_type: memory
  type: project
  originSessionId: 88d78d9d-5fd8-4d2d-bd99-664dec394d7e
---

As of 2026-06-12, hotword biasing for `nemo-asr-cpp` is **vendored in the
add-on repo** as `nemo-asr-cpp/patches/0001-rnnt-hotword-biasing.patch`
(109 lines vs upstream mudler/parakeet.cpp @ e270af7, C ABI 4→5), applied by
the Dockerfile with `git apply` after checkout. Upstream-PR-shaped: when
upstream ships the feature, delete the patch + apply step, bump PARAKEET_REF.
Working copies of the patched checkout live in /tmp/parakeet.cpp and
/tmp/parakeet-clean (volatile; the repo patch file is the durable artifact).

Hard-won tokenization findings (apply to nemotron-asr-c's Python hotwords too):
- The GGUF embeds vocab pieces (`parakeet.tokenizer.pieces`, logit index
  order) but **no SentencePiece scores**, so exact unigram segmentation can't
  be reproduced; greedy longest-match diverges ('▁일' vs SPM's '▁'+'일') and a
  diverged sequence silently biases nothing. Fix: register up to two greedy
  variants per phrase (marker + marker-less) — `tokenizer.encode_variants`.
- Drop a leading bare `▁` (id 2) token: boosting it as a phrase start every
  step makes boost ≥ ~4 catastrophic (repetition loops). Boost 2.0 default is
  validated: multi-hotword KO fixes with no EN regression.

Upstream divergence (reviewed 2026-06-13, pin stays at e270af7 / #20): upstream
added 3 commits we deliberately skip — #26 CUDA graphs (irrelevant, our build is
GGML_NATIVE=OFF CPU), #22 prebuilt-binary CI (irrelevant, we compile from source),
and **#24 `503d7ec` "ABI v5" (EOU vs EOB distinction)** which **collides head-on
with our patch**: upstream's #24 also bumps PARAKEET_CAPI_ABI_VERSION 4→5 and
heavily edits the exact two files our patch touches (`include/parakeet_capi.h`
+61/-8, `src/parakeet_capi.cpp` +96/-23), so a REF bump makes our `git apply`
fail. Decision: keep current pin — none of the 3 commits add a feature we use
(EOU/EOB is a turn-taking signal HA's Wyoming pipeline handles at pipeline level).
**When we do want EOU/EOB:** bump PARAKEET_REF→b8012f11, change our patch's ABI
bump to **5→6** (upstream now owns 5), rebase the hotword hunks onto the new
context (`git apply --reject`). Upstream still has no hotword PR/issue, so the
patch can't be dropped yet.

Related: [[nemotron-asr-c-addon]]
