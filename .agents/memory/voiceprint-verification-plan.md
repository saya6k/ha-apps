---
name: voiceprint-verification-plan
description: "voiceprint add-on BUILT 2026-06-12 — our own Wyoming pass-through STT gate proxy (LiteRT CAM++ speaker verification), experimental/gitignored, smoke-tested venv+docker; ASR-stage placement decision record inside"
metadata: 
  node_type: memory
  type: project
  originSessionId: 88d78d9d-5fd8-4d2d-bd99-664dec394d7e
---

User wants voiceprint enrollment in the HA voice pipeline (2026-06-12).
Reviewed [jxlarrea/wyoming-voice-match](https://github.com/jxlarrea/wyoming-voice-match)
(MIT, v1.9.1 Mar 2026, active): a Wyoming **ASR proxy** (HA → proxy :10350 →
real STT :10300) using SpeechBrain ECAPA-TDNN. Buffers post-wake audio,
verifies speaker at 5 s (early/parallel), extracts only enrolled-speaker
regions, forwards cleaned audio; rejection = empty `Transcript`. Enrollment =
30+ × 5 s WAVs per speaker → embedding via a script. CPU verify 200–500 ms,
~500 MB RAM; has Dockerfile.cpu.

**Decision: verification belongs at the ASR stage, not wake-word stage.**
Why: (1) wake-stage audio is only the wake phrase — "빅스비" < 1 s, and
text-independent ECAPA degrades sharply under ~2–3 s, while the command
utterance (2–5 s) is exactly the right material; (2) in HA Assist the wake
service never sees command audio (HA switches to STT after Detection), so a
wake-stage check can never get more audio; (3) failure UX — wake-stage false
reject is dead silence, ASR-stage reject gives pipeline feedback + the proxy
logs rejected clips for threshold tuning; (4) speaker **extraction** (TV/
background removal from transcripts) and TAG_SPEAKER per-speaker automations
only possible with command audio. Text-dependent SV on the wake phrase (Siri
style) would be the only good wake-stage approach — disproportionate effort.

**Built (user chose our own bridge + separate proxy):** `voiceprint/` add-on
in ha-apps (stage experimental → root-.gitignored, like
[[livekit-wakeword-addon]]). Differs from wyoming-voice-match on purpose:
**pass-through gate**, not buffer-then-forward — chunks stream to the
upstream STT unchanged, verification runs in an executor between AudioStop
and the upstream Transcript (added latency ≈ 0 for streaming STT like
nemo-asr-cpp); mismatch ⇒ empty Transcript. Runtime is **LiteRT, not
onnxruntime** (user pushed for lighter): our own TFLite fp16 conversion of
3D-Speaker CAM++ zh_en advanced — fidelity cos 0.999997 vs ONNX, payload
43 MB vs 93 MB; **no ggml speaker-embedding runtime exists** (checked).
Conversion is non-mechanical; recipe in
`voiceprint/notes/runtime-experiment/RECIPE.md`, decision record + model
contract in `voiceprint/AGENTS.md`. Enrollment = `/share/voiceprint/<name>/
*.wav`, recomputed each boot. Smoke-tested end-to-end (venv + docker s6,
say-voice fixtures): pass/reject/pass-through/tag_speaker all verified;
results in `voiceprint/notes/smoke/SMOKE_RESULTS.md`. Caveat: 0.5 default
threshold needs validation with real voices on the actual satellite mic.
Speaker **extraction** (TV-overlap region cut) is a designed-but-unbuilt
phase 2 — needs buffering, inherently ~0.3–1 s tail latency.
