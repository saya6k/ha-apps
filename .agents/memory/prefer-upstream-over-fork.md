---
name: prefer-upstream-over-fork
description: User prefers tracking upstream over maintaining custom C++ patches/forks
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 2242e1f6-2a09-479a-89f7-311f6187a041
---

For the `nemo-asr-cpp` add-on (packages upstream `mudler/parakeet.cpp`), the user
prefers to **track upstream cleanly and NOT maintain a custom C++ patch/fork**.

We went through a full cycle: scoped → implemented hotword biasing as a vendored
C++ patch (`patches/0001-hotword-biasing.patch`) over pinned upstream → it built
and a single hotword worked, but multiple hotwords flooded (greedy biasing is
structurally flood-prone; robust biasing needs beam search, which no fast-CPU
NeMo ggml impl has). The user then said to **remove the entire self-implemented
hotword feature** and wait until mudler adds biasing upstream, then adopt it.

**Why:** maintaining a fork/patch is a burden the user doesn't want; speculative
self-implementations that aren't upstream should be removed, not carried.

**How to apply:** when a wanted feature isn't in the upstream a subproject
packages, prefer (a) waiting for / requesting it upstream, or (b) using a
sibling that already has it — over forking/patching. Don't build a vendored
patch unless the user explicitly accepts the maintenance. If a self-implemented
workaround is later rejected, remove it fully (don't leave it half-in).
Tangent: when the user answers with a number ("1번"), the options were ambiguous
across messages — confirm which option before acting. See [[nemo-asr-cpp-addon]].
