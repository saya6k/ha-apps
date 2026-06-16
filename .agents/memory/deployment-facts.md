---
name: deployment-facts
description: "ha-apps public-repo deployment facts — HA repo identifier, GHCR image naming/visibility, voiceprint model release"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8683c7a5-4b03-47bb-8f3e-87ef1fda371e
---

The ha-apps repo (github.com/saya6k/ha-apps) is now **public**. Key deployment facts:

- **HA add-on repo identifier: `03f32180`.** When installed from this repo, an
  add-on's network hostname is `03f32180-<slug>` (hyphen) and its addon_config
  dir is `/addon_configs/03f32180_<slug>` (underscore) — replacing the
  `local-`/`local_` prefix used for locally-built add-ons. voiceprint defaults
  its `upstream_uri` to `tcp://03f32180-nemo-asr-cpp:10360`.
- **Prebuilt images:** each published add-on's `config.yaml` has
  `image: ghcr.io/saya6k/{arch}-addon-<slug>`, built per release tag by
  `.github/workflows/build.yml`. The images exist but are **private by
  default** — GHCR package visibility must be flipped to Public via the web UI
  (https://github.com/users/saya6k/packages → each package → settings); there
  is no REST API for this and `gh` needs `write:packages` scope to even list.
- **voiceprint model release `voiceprint-model-v1` now exists** (published
  2026-06-15) with `campplus_zh_en_fp16.tflite` attached — fixes the first-run
  404 in `models.ensure_model`. See [[voiceprint-verification-plan]].
