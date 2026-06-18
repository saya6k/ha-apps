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
- **Local build (no prebuilt images, since 2026-06-18).** Add-ons have **no
  `image:` key** — HA builds each from its Dockerfile on the host. CI
  build-tests the Dockerfile (`.github/workflows/ci.yml` `build-image` job, all
  configured arches, `push: false`); nothing is published to GHCR and the old
  `build.yml` publish workflow was deleted. The `03f32180-<slug>` hostname is
  **unaffected** — repo-installed add-ons keep the repo identifier whether built
  locally or pulled, so voiceprint's `tcp://03f32180-nemo-asr-cpp:10360` default
  still holds.
- **voiceprint model release `voiceprint-model-v1` now exists** (published
  2026-06-15) with `campplus_zh_en_fp16.tflite` attached — fixes the first-run
  404 in `models.ensure_model`. See [[voiceprint-verification-plan]].
