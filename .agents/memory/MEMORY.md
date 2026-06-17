# Memory index

- [nemotron-asr add-on](nemotron-asr-addon.md) — new ONNX/CPU Wyoming STT add-on replacing sherpa-onnx; scaffolded, validated, experimental/local-only
- [container runtime preference](container-runtime-preference.md) — use Docker Desktop on this Mac; podman + Apple container CLI both removed 2026-06-15 to free space
- [devcontainer HA boot](devcontainer-ha-boot.md) — boot HA via scripts/devcontainer-ha.sh; 3 gotchas (entrypoint idles, no manual dockerd, supervisor_run needs a TTY)
- [parakeet.cpp hotword patch](parakeet-hotword-patch.md) — hotwords vendored in nemo-asr-cpp/patches (ABI v5); GGUF lacks SPM scores → dual greedy variants per phrase; bare-'▁' boost hazard
- [wakewordlab add-on](wakewordlab-addon.md) — DELETED for poor quality; livekit-wakeword chosen as successor (oWW compat verification details inside)
- [livekit-wakeword add-on](livekit-wakeword-addon.md) — Wyoming wake-word add-on with OUR incremental bridge (80ms cadence, 10x less CPU than upstream API); serves oWW zoo + custom /share models; Korean training planned
- [voiceprint verification plan](voiceprint-verification-plan.md) — voiceprint add-on built: pass-through STT gate proxy, LiteRT CAM++ (no ggml SV runtime exists), smoke-tested; threshold needs real-voice validation
- [app terminology](app-terminology.md) — prefer "app" over "add-on"/"addon" in ha-apps prose/naming; keep literal addon identifiers (labels, linter action)
- [nemo-asr-cpp chunk-size](nemo-asr-cpp-chunk-size.md) — accuracy/speed dial via in-place GGUF att_context_right KV edit (verified); default 320ms, 4 presets {80,320,560,1120}ms, no engine refactor
- [deployment facts](deployment-facts.md) — repo is public; HA repo id `03f32180`; GHCR `{arch}-addon-<slug>` images private→need web-UI publish; voiceprint-model-v1 release published
- [release-please squash gotcha](release-please-squash-gotcha.md) — squash-merging multi-scope PRs drops release-please releases; use rebase-merge or a conventional PR title; revert+cherry-pick to recover
- [zeroconf default=None](zeroconf-default-none.md) — Wyoming --zeroconf must default to None, not a truthy string; truthy default imports wyoming.zeroconf → uninstalled zeroconf package → ModuleNotFoundError at boot
- [patch-path-prefix-consistency](patch-path-prefix-consistency.md) — git apply fails when .patch files mix a/b prefix styles in a single invocation; keep all patches consistent
- [nemo-asr-cpp .nemo source](nemo-asr-cpp-nemo-source.md) — .nemo → GGUF conversion evaluated 2026-06-18 and rejected; nemo_toolkit ~3 GB image bloat kills the value prop for HAOS targets
