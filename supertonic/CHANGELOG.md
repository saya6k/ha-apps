# Changelog

## [2.6.0](https://github.com/saya6k/ha-apps/compare/supertonic-v2.5.0...supertonic-v2.6.0) (2026-06-23)


### Features

* **supertonic:** add AppArmor profile ([84fe2b3](https://github.com/saya6k/ha-apps/commit/84fe2b36ae0de1b1b8140da3bd988c3aad305b7b))



## [2.5.0](https://github.com/saya6k/ha-apps/compare/supertonic-v2.4.1...supertonic-v2.5.0) (2026-06-22)


### Features

* **supertonic:** NeMo WFST TN — ordinal/currency/date/time/unit support ([57a45cb](https://github.com/saya6k/ha-apps/commit/57a45cb3d999e6ee4cd028e59ec0b041b5634095))


### Bug Fixes

* **supertonic:** add Cython build dep for pynini source build on aarch64 ([a07fc48](https://github.com/saya6k/ha-apps/commit/a07fc48c1ae4f5f8b17378dc3fa67e39a6506dbb))
* **supertonic:** install setuptools before pynini source build on aarch64 ([86cef16](https://github.com/saya6k/ha-apps/commit/86cef163d6bf97344346cf3326e1d0804a082acc))
* **supertonic:** restrict pynini+NeMo-TN to amd64; aarch64 uses rbnf fallback ([2225a5b](https://github.com/saya6k/ha-apps/commit/2225a5b81dbbaddabfc38bd6082c8b365534d466))
* **supertonic:** suppress ruff F821/E402 on intentional import patterns ([2ee10e1](https://github.com/saya6k/ha-apps/commit/2ee10e1fde6c26563cac1f87cc749e33f7bf7ce7))
* **supertonic:** upgrade pynini to 2.1.7 for aarch64 source build compatibility ([fdfcfa6](https://github.com/saya6k/ha-apps/commit/fdfcfa666b623a7261ca49877c2dea0bd639f312))


### Documentation

* **supertonic:** reorder README shields — Show add-on below for-the-badge badges ([231a0a3](https://github.com/saya6k/ha-apps/commit/231a0a3cd025ef9671af6d76f8e07541ec4bf3b5))


### Build System

* **supertonic:** strip .so debug symbols in builder stage ([#358](https://github.com/saya6k/ha-apps/issues/358)) ([aa479c7](https://github.com/saya6k/ha-apps/commit/aa479c70ea9b76e0997244c0b25fdcca1bbc7b45))


### CI

* **repo:** tighten markdownlint scope and disable style-only rules ([9fe6f97](https://github.com/saya6k/ha-apps/commit/9fe6f97b9fee3e1c010f2ee534b36ea8de2a74fe))

## [2.4.1](https://github.com/saya6k/ha-apps/compare/supertonic-v2.4.0...supertonic-v2.4.1) (2026-06-19)


### Bug Fixes

* **repo:** add apparmor: true to all add-ons, remove custom profiles ([6ccfe5d](https://github.com/saya6k/ha-apps/commit/6ccfe5d4b5daf805d66b7dbcdc1c71ab95e106e1))
* **repo:** add apparmor: true to all add-ons, remove custom profiles ([a8b8a61](https://github.com/saya6k/ha-apps/commit/a8b8a6163024fa611e2b661b90f37093640419fa))
* **repo:** remove redundant apparmor: true (linter default) ([423ac7f](https://github.com/saya6k/ha-apps/commit/423ac7ff0c4fbde79abdec4e86a08f5c91f6fe1f))


### Build System

* **supertonic:** upgrade wyoming 1.7.2 → 1.9.0 ([#237](https://github.com/saya6k/ha-apps/issues/237)) ([a704b8d](https://github.com/saya6k/ha-apps/commit/a704b8d586a5dffa53d60f855ccf8ff78bf13703))

## [2.4.0](https://github.com/saya6k/ha-apps/compare/supertonic-v2.3.1...supertonic-v2.4.0) (2026-06-18)


### Features

* **supertonic:** add custom AppArmor profile ([30d2bcd](https://github.com/saya6k/ha-apps/commit/30d2bcd4a0763c4f4b94b27d9ae0fa566c2c85d5))
* **supertonic:** add language-aware number normalizer ([3bb7f5b](https://github.com/saya6k/ha-apps/commit/3bb7f5b11bfae8209fbd014200e1e8682bf6ebfc))
* **supertonic:** add text_normalization app option (hidden, default on) ([9a5e153](https://github.com/saya6k/ha-apps/commit/9a5e1530ac0c3369ebcb0ad41c9a5ee4233af4d9))
* **supertonic:** take TTS language from the pipeline per request ([7f06db1](https://github.com/saya6k/ha-apps/commit/7f06db17d385328fdd4c6017fa080db45710dc1a))
* **supertonic:** wire number normalization into the synth path ([4b8da88](https://github.com/saya6k/ha-apps/commit/4b8da886c885d0af2e3a5f12cfc0ba987fd518ac))


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))
* **supertonic:** clear executable-stack flag on MNN x86_64 .so ([0fafddf](https://github.com/saya6k/ha-apps/commit/0fafddfe9cbb76e9df8e42314d8bfa665d977c47))


### Documentation

* **supertonic:** add Show add-on badge to README ([84470bf](https://github.com/saya6k/ha-apps/commit/84470bf3c204fbb0adb2e491f44af4a7037132cf))
* **supertonic:** clarify number-normalization boundary matches Piper 2 ([d8c70b8](https://github.com/saya6k/ha-apps/commit/d8c70b875a5e9e41a5b1cfacf215bd0f4bef303a))
* **supertonic:** document text_normalization option ([8e7b130](https://github.com/saya6k/ha-apps/commit/8e7b13011bc67064c4d50eaacb0c91a894f6beb0))


### Build System

* **supertonic:** --no-compile pip install in builder stage ([c08322d](https://github.com/saya6k/ha-apps/commit/c08322d95d984cdde0c228d07a6cad600e86c7c6))
* **supertonic:** build add-on locally, drop GHCR image reference ([424e282](https://github.com/saya6k/ha-apps/commit/424e2826d53715e1ec68f8923753d1a5ced19279))
* **supertonic:** clean apt cache in builder stage ([5d7dd53](https://github.com/saya6k/ha-apps/commit/5d7dd53c8a37efe3ba5d0a47f43ee97df136da03))
* **supertonic:** multi-stage image and inline base, drop retired build.yaml ([f27c0e3](https://github.com/saya6k/ha-apps/commit/f27c0e372d0968989ed8ee6579a09534c264afe3))
* **supertonic:** reference prebuilt public GHCR image ([c24ed8c](https://github.com/saya6k/ha-apps/commit/c24ed8c6c9a948227ae860f538d81f15d252dc47))
* **supertonic:** swap orphan num2words for unicode-rbnf ([3686f09](https://github.com/saya6k/ha-apps/commit/3686f0983c0e61cbef2a18b4b34bd834c5d8fdcf))
* **supertonic:** switch base image to Debian trixie, unpin numpy ([e81b444](https://github.com/saya6k/ha-apps/commit/e81b444b925ebf59696d933b2498a41816a44f80))
* **supertonic:** upgrade wyoming 1.7.2 → 1.9.0 ([#237](https://github.com/saya6k/ha-apps/issues/237)) ([a704b8d](https://github.com/saya6k/ha-apps/commit/a704b8d586a5dffa53d60f855ccf8ff78bf13703))

## [2.3.1](https://github.com/saya6k/ha-apps/compare/supertonic-v2.3.0...supertonic-v2.3.1) (2026-06-18)


### Build System

* **supertonic:** --no-compile pip install in builder stage ([c08322d](https://github.com/saya6k/ha-apps/commit/c08322d95d984cdde0c228d07a6cad600e86c7c6))
* **supertonic:** clean apt cache in builder stage ([5d7dd53](https://github.com/saya6k/ha-apps/commit/5d7dd53c8a37efe3ba5d0a47f43ee97df136da03))
* **wardrowbe:** remove npm rebuild sharp from frontend build ([91fb4a5](https://github.com/saya6k/ha-apps/commit/91fb4a5f5d3dcfab2aab871c3c1a1376a229d23e))

## [2.3.0](https://github.com/saya6k/ha-apps/compare/supertonic-v2.2.2...supertonic-v2.3.0) (2026-06-18)


### Features

* **supertonic:** add custom AppArmor profile ([30d2bcd](https://github.com/saya6k/ha-apps/commit/30d2bcd4a0763c4f4b94b27d9ae0fa566c2c85d5))


### Documentation

* **supertonic:** add Show add-on badge to README ([84470bf](https://github.com/saya6k/ha-apps/commit/84470bf3c204fbb0adb2e491f44af4a7037132cf))

## [2.2.2](https://github.com/saya6k/ha-apps/compare/supertonic-v2.2.1...supertonic-v2.2.2) (2026-06-18)


### Build System

* **supertonic:** build add-on locally, drop GHCR image reference ([424e282](https://github.com/saya6k/ha-apps/commit/424e2826d53715e1ec68f8923753d1a5ced19279))

## [2.2.1](https://github.com/saya6k/ha-apps/compare/supertonic-v2.2.0...supertonic-v2.2.1) (2026-06-17)


### Bug Fixes

* **repo:** use 3-way finish template across all apps, add to scaffold ([b1a4d01](https://github.com/saya6k/ha-apps/commit/b1a4d011fdadfc7451faa57904da81c31591ddfb))

## [2.2.0](https://github.com/saya6k/ha-apps/compare/supertonic-v2.1.1...supertonic-v2.2.0) (2026-06-16)


### Features

* **supertonic:** add language-aware number normalizer ([3bb7f5b](https://github.com/saya6k/ha-apps/commit/3bb7f5b11bfae8209fbd014200e1e8682bf6ebfc))
* **supertonic:** add text_normalization app option (hidden, default on) ([9a5e153](https://github.com/saya6k/ha-apps/commit/9a5e1530ac0c3369ebcb0ad41c9a5ee4233af4d9))
* **supertonic:** wire number normalization into the synth path ([4b8da88](https://github.com/saya6k/ha-apps/commit/4b8da886c885d0af2e3a5f12cfc0ba987fd518ac))


### Documentation

* **supertonic:** clarify number-normalization boundary matches Piper 2 ([d8c70b8](https://github.com/saya6k/ha-apps/commit/d8c70b875a5e9e41a5b1cfacf215bd0f4bef303a))
* **supertonic:** document text_normalization option ([8e7b130](https://github.com/saya6k/ha-apps/commit/8e7b13011bc67064c4d50eaacb0c91a894f6beb0))


### Build System

* **supertonic:** swap orphan num2words for unicode-rbnf ([3686f09](https://github.com/saya6k/ha-apps/commit/3686f0983c0e61cbef2a18b4b34bd834c5d8fdcf))

## [Unreleased]

### Features

* Number-to-words normalization before synthesis — integers and decimals are
  expanded to spoken words using CLDR RBNF spellout (e.g. `23` → `twenty-three`,
  `3.5` → `three point five`, `이십삼개` in Korean). Covers all 31 supported
  languages. On by default; disable via `text_normalization: false` in the
  advanced options if a specific language produces unexpected output.

## [2.1.1](https://github.com/saya6k/ha-apps/compare/supertonic-v2.1.0...supertonic-v2.1.1) (2026-06-15)


### Build System

* **supertonic:** reference prebuilt public GHCR image ([c24ed8c](https://github.com/saya6k/ha-apps/commit/c24ed8c6c9a948227ae860f538d81f15d252dc47))

## [2.1.0](https://github.com/saya6k/ha-apps/compare/supertonic-v2.0.1...supertonic-v2.1.0) (2026-06-15)


### Features

* **supertonic:** take TTS language from the pipeline per request ([7f06db1](https://github.com/saya6k/ha-apps/commit/7f06db17d385328fdd4c6017fa080db45710dc1a))

## [2.0.1](https://github.com/saya6k/ha-apps/compare/supertonic-v2.0.0...supertonic-v2.0.1) (2026-06-15)


### Bug Fixes

* **supertonic:** clear executable-stack flag on MNN x86_64 .so ([0fafddf](https://github.com/saya6k/ha-apps/commit/0fafddfe9cbb76e9df8e42314d8bfa665d977c47))


### Build System

* **supertonic:** multi-stage image and inline base, drop retired build.yaml ([f27c0e3](https://github.com/saya6k/ha-apps/commit/f27c0e372d0968989ed8ee6579a09534c264afe3))
* **supertonic:** switch base image to Debian trixie, unpin numpy ([e81b444](https://github.com/saya6k/ha-apps/commit/e81b444b925ebf59696d933b2498a41816a44f80))

## 2.0.0

- **Inference backend: ONNX Runtime / OpenVINO → MNN** (via
  [`supertonic-mnn`](https://github.com/vra/supertonic-mnn)). Removes
  ~400 MB of runtime deps (`onnxruntime-openvino`, `intel-opencl-icd`,
  etc.), drops the `/dev/dri` device + `video:` group, and deletes the
  ORT provider-intercept monkey-patching.
- **New options**: `precision` (`auto` by default — picks int8/fp16/fp32
  from `/proc/cpuinfo`), `model_version` (`v3`), `mnn_memory` (`normal`).
- **Removed options (breaking)**: `provider`, `crop_silence`.
- **Schema change**: `language` is now native names (`한국어`, `日本語`,
  `Deutsch`, …) ordered by ISO 639-1 code — same convention OS language
  pickers use. The engine still accepts ISO codes and English names
  via `resolve_language()`. Existing configs with `language: ko` or
  `language: Korean` need to be changed to `language: 한국어` in the
  add-on UI / YAML editor.
- **Logging**: CPU diagnostics (governor + freqs) on boot; per-request
  `TTFT: x.xxs`.
- **Cache path**: `/data/.cache/supertonic3` → `/data/.cache/supertonic-mnn`.
  First boot re-downloads the (smaller) MNN model.
- `translations/ko.yaml` added.
- **Brand assets**: `icon.png` and `logo.png` replaced with the
  MIT-licensed `logo_square.png` / `logo_wide.png` from
  [`supertone-inc/supertonic-py`](https://github.com/supertone-inc/supertonic-py/tree/main/docs/assets/images).
  Attribution recorded in the new `NOTICE` file.
- **CI/CD via [`hassio-addons/workflows`](https://github.com/hassio-addons/workflows)**:
  - `ci.yaml` — PR validation (yamllint, shellcheck, hadolint,
    `frenck/action-addon-linter`)
  - `deploy.yaml` — push to `main` or published release builds amd64 +
    aarch64 images and pushes to GHCR at `ghcr.io/saya6k/{arch}-addon-supertonic`
  - `release.yaml` — `v*` tags create a GitHub Release with the matching
    CHANGELOG section as the body
  - `lock.yaml` / `stale.yaml` — issue / PR housekeeping
  The `image:` line in `config.yaml` is staged but kept commented out
  until the first GHCR publish — uncomment it once `deploy.yaml` has
  successfully pushed amd64 + aarch64 tags so users get prebuilt
  images instead of a long local build.
- **HA terminology**: user-visible docs (README / DOCS / AGENTS, option
  descriptions) updated from "add-on" to "app" to match HA's current
  terminology. Schema keys (`addon_config:rw`), the GHCR image name
  pattern (`{arch}-addon-supertonic`), and references to upstream orgs
  (`hassio-addons`) keep their legacy spelling — those are identifiers,
  not display strings.
- **Add-on renamed** to drop the model-version suffix now that v2 and v3
  are both supported:
  - `slug`: `supertonic_3` → `supertonic`
  - `name`: `Supertonic 3` → `Supertonic`
  - Python package: `wyoming_supertonic_3` → `wyoming_supertonic`
  - Console entry point: `wyoming-supertonic-3` → `wyoming-supertonic`
  - Wyoming `TtsProgram.name`: `Supertonic 3` → `Supertonic`
  - Repository directory: `ha-supertonic-3-tts` → `ha-supertonic`
  Slug change means this 2.0.0 release is a fresh add-on as far as HA
  is concerned — config from `supertonic_3` does not carry over and the
  model cache will be re-downloaded.
  Note: the Python package name `wyoming_supertonic` matches the PyPI
  package by mitrokun (which 1.x used as upstream bridge). They are
  unrelated codebases; we do not publish to PyPI, and the image installs
  this package locally via `pip install --no-deps /usr/src/app`.

## 1.4.1

- **Fix**: the OV allowlist that 1.2.3 introduced was never actually
  effective. The `ort.InferenceSession.__init__` intercept correctly
  forwarded our OV tuple list to `vector_estimator.onnx`, but for the
  three other models (`duration_predictor`, `text_encoder`, `vocoder`)
  it only *logged* "OV bypassed" — it never overrode the providers,
  so supertonic's loader (which we'd patched to advertise OV in
  `DEFAULT_ONNX_PROVIDERS`) ended up passing OV to those sessions
  anyway. They then hit the OV CPU plugin's attention-Reshape
  dynamic-shape bug at the first warm-up:
  `[CPU] Reshape ... input data (1,2,N) conflicts with the reshape
  pattern (1,2,head_dim,N')`.
  - The intercept's else branch now forcibly sets
    `providers=["CPUExecutionProvider"]` for any non-allowlisted
    `supertonic3 *.onnx`, regardless of what the loader was going
    to pass.
  - The `_patch_loader_log_truth()` helper that rebound
    `supertonic.loader.DEFAULT_ONNX_PROVIDERS` to `["OV", "CPU"]`
    is gone. That patch was the source of the OV leak — its only
    purpose was to make the loader's `Using ONNX providers: ...`
    log line read "OV+CPU", but it also caused supertonic to actually
    pass OV to every session. The intercept now logs explicitly
    per model (`OV provider applied to ...` /
    `Forced plain CPU EP for ...`) so the truth lives in our logs
    instead.

## 1.4.0

- **Rewritten Wyoming bridge.** The add-on no longer depends on
  `mitrokun/wyoming_supertonic`. The Wyoming protocol server is now our
  own package, `wyoming_supertonic_3`, shipped from this repo and
  installed via local `pip install /usr/src/app` during image build. The
  `supertonic` PyPI library is still used for the actual model loading
  and synthesis — we did not reinvent that piece.
- The six runtime monkey-patches that used to live in
  `rootfs/usr/local/bin/supertonic-launcher` are now plain module-level
  code:
  - OMP/BLAS thread pinning runs inside `engine.configure_thread_envs()`
    before `supertonic` is imported.
  - `SUPERTONIC_INTER_OP_THREADS=1` and the intra-op count are exported
    from the same helper.
  - The OpenVINO `ort.InferenceSession.__init__` intercept lives in
    `engine._install_provider_intercept()` (still narrowed to the
    `vector_estimator.onnx` allowlist; see 1.3.0 below for why).
  - Warm-up runs via `engine.warmup(voices, shapes)` with several
    `(lang, text)` pairs, not just a single English `Hello.` — this
    primes OV's dynamic-shape cache for realistic Korean / longer
    sequences too.
  - Error propagation is normal `try`/`except` inside the handler
    (re-raised as Wyoming `Error` events) — no more upstream catch
    swallowing.
  - The `TtsProgram.name` literal is `Supertonic 3` directly in our
    `_build_info()` instead of being rewritten after the fact.
- The launcher script (`rootfs/usr/local/bin/supertonic-launcher`) and
  its `rootfs/usr/local/bin/` directory are deleted. The s6 `run`
  script now `exec`s `python3 -m wyoming_supertonic_3` directly.
- `build.yaml`: the `WYOMING_SUPERTONIC_REF` build-arg is gone, since
  the upstream bridge is no longer fetched.
- TTFT improvement: `AudioStart` is emitted before synthesis begins (was
  after, in the old launcher), so a client can prepare its audio
  pipeline while the model is still running. The actual first-byte
  latency is unchanged but the protocol event signalling arrives a beat
  sooner.

## 1.3.0

- **Rename**: the add-on now identifies itself as **Supertonic 3**
  end-to-end so the model version is visible everywhere users see it.
  - `slug`: `supertonic` → `supertonic_3`. **Existing installs must
    uninstall the old add-on and install this one fresh** — HA
    treats a new slug as an entirely separate add-on, so its
    configuration and `/data` volume do not carry over. The model
    cache will be re-downloaded on first start of the renamed
    add-on.
  - `name`: `Supertonic` → `Supertonic 3`.
  - Wyoming `TtsProgram.name`: a launcher-side monkey-patch
    rewrites the upstream value (`Supertonic`) to `Supertonic 3`
    before the `Info` event is built, so HA's voice picker shows
    the version too.
- **Fix**: when any OpenVINO provider was selected, the
  duration_predictor model crashed on multilingual inputs (specifically
  Korean text after an English warm-up) with the OV CPU-plugin
  exception
  `[CPU] Reshape ... input data (1,2,N) conflicts with the reshape
  pattern (1,2,head_dim,N')` — a dynamic-shape caching bug in the OV
  CPU plugin's attention Reshape handling that we cannot work around
  upstream.
  - The fix narrows the `ort.InferenceSession.__init__` provider
    intercept to apply OpenVINO only to `vector_estimator.onnx`. The
    other three supertonic3 models (`duration_predictor`,
    `text_encoder`, `vocoder`) are small and called once per sentence,
    so leaving them on plain CPU EP costs almost nothing — but
    vector_estimator alone is the 257 MB transformer called `steps`
    (~3) times per chunk, so OV's speedup is still applied where it
    matters.
  - The startup log line now reports the allowlist explicitly
    (`OV applied only to vector_estimator.onnx; others stay on plain
    CPU EP`).

## 1.2.2

- **Fix**: 1.2.1 finally shipped the OpenVINO build correctly
  (`version=1.23.0`, OV EP in `get_available_providers()`), but the
  monkey-patch that was supposed to steer supertonic at the OV provider
  didn't actually take effect — the loader's log kept saying `Using ONNX
  providers: ['CPUExecutionProvider']`. Two bugs piled on top of each
  other:
  - We mutated `supertonic.config.DEFAULT_ONNX_PROVIDERS`, but
    `supertonic/loader.py:18` does `from .config import
    DEFAULT_ONNX_PROVIDERS` — that's an *import-time snapshot* into
    loader's namespace. Mutating `config` doesn't reach `loader`.
  - Even if we patched loader's binding instead, `loader.py:249` filters
    the list with `[p for p in providers if p in available_providers]`
    where `available_providers` is a list of *strings*. Our
    `(name, options)` tuple form is never `in` a list of strings, so
    the filter silently dropped the OpenVINO entry — meaning we'd
    never have been able to pass `device_type=GPU` etc. through the
    constant patch anyway.
- Replace with two cooperating patches: (1) module-level monkey-patch
  on `ort.InferenceSession.__init__` that swaps `providers=` to our
  full tuple list (with embedded provider_options) when the model path
  matches `*supertonic3*.onnx`; (2) `supertonic.loader.DEFAULT_ONNX_PROVIDERS`
  rebound to a string-only list so the loader's "Using ONNX providers"
  log line is truthful.
- Document the two bugs in `AGENTS.md` so the next reader doesn't redo
  the wrong fix.

## 1.2.1

- **Fix**: 1.2.0 shipped with the `onnxruntime-openvino` wheel installed but
  the actual files in `site-packages/onnxruntime/` were plain ORT 1.26.0,
  because `pip install supertonic` (later in the Dockerfile) pulled in the
  latest plain `onnxruntime` as a transitive dep and silently overwrote the
  OV files. pip doesn't know the two distributions provide the same import
  name, so it didn't flag the conflict. The launcher detected the missing
  EP and correctly fell back to CPU, but OpenVINO never actually ran.
- Reorder Dockerfile so the ORT install happens **last** (after supertonic
  + wyoming-supertonic), with an explicit `pip uninstall onnxruntime`
  preceding the swap. The OV (or pinned plain) build is now the final
  writer to `onnxruntime/` and stays put.
- Add a build-time sanity check on amd64: `python3 -c "assert
  'OpenVINOExecutionProvider' in onnxruntime.get_available_providers()"`.
  If the swap ever silently breaks again, the build fails instead of
  shipping a defective image.

## 1.2.0

- **OpenVINO Execution Provider** (opt-in). New `provider` option:
  `cpu` (default, current behavior), `openvino_cpu`, `openvino_gpu`,
  `openvino_auto`. On Intel x86 hosts with an iGPU (N100/N305 UHD,
  12th-gen+ Core, etc.), `openvino_gpu` is the most likely path to
  RTF < 1 — community benchmarks on similar hardware suggest 1.5–4×
  over the ORT CPU EP for transformer/conv workloads. **Default stays
  `cpu`**; flip to one of the OV options after measuring on your host.
- amd64 image swaps `onnxruntime==1.23.1` → `onnxruntime-openvino==1.23.0`
  (same ORT 1.23.x line, bundles OpenVINO 2025.3 + CPU/GPU/NPU plugins +
  OneTBB). Adds `ocl-icd-libopencl1` and `intel-opencl-icd` from Debian
  Bookworm main for the iGPU runtime. Net image size delta: **+290 MB**.
- aarch64 image is unchanged — no `onnxruntime-openvino` wheel exists
  for that arch. The launcher silently falls back to CPU if the user
  picks an `openvino_*` provider on aarch64.
- iGPU device pass-through declared in `config.yaml`:
  `devices: ['/dev/dri/renderD128']` and `video: true` (Frigate-style).
  The supervisor silently no-ops the device on hosts that don't have it,
  so this is safe to declare unconditionally.
- Compiled OpenVINO blobs cached at `/data/.cache/ov/` so the first-load
  compile (10–30 s on iGPU) only happens once per model. Cache is keyed
  on driver version, so apt-upgrading `intel-opencl-icd` invalidates it
  automatically.
- Provider override in the launcher patches
  `supertonic.config.DEFAULT_ONNX_PROVIDERS` rather than the more
  fragile `InferenceSession.__init__` interception path that was used
  for the failed INT8 experiment.
- Always include `CPUExecutionProvider` as the tail of the providers
  list so a runtime OV failure (device unreachable, op unsupported) is
  auto-recovered by ORT instead of crashing the load.

## 1.1.3

- **Revert INT8 quantization** introduced in 1.1.0–1.1.2. On the test
  hardware (Intel N100, 4 cores) `quantize_dynamic` with `MatMul`+`Gemm`
  op types produced **slower** synthesis, not faster: RTF went from 3.50
  (FP32 baseline) to 4.90 with no audible quality benefit. Root cause:
  the attention Q×K / attn×V MatMuls have non-constant B and got
  auto-skipped, while the small projection MatMuls that *were* quantized
  paid `QuantizeLinear`/`DequantizeLinear` overhead per call without
  enough INT8 amortization at hidden dim ~512–1024. File size barely
  changed (244.7 → 230.7 MB), confirming most weight tonnage stayed FP32.
- Remove `quantize` option from the schema; `onnx` package from the
  Dockerfile; the `onnxruntime.InferenceSession` monkey-patch from the
  launcher.
- Launcher cleans up `/data/.cache/supertonic3.int8/` on startup so users
  recover the ~330 MB of orphaned INT8 cache from the failed iterations.
- Keep the `inter_op_threads=1` override — small but free win, and the
  rationale (supertonic hard-codes `ORT_SEQUENTIAL`) is unaffected.
- Document the experiment in `AGENTS.md` so the next person who looks at
  perf doesn't repeat the same three iterations.

## 1.1.2

- **Fix crash loop**: 1.1.1 successfully built INT8 graphs but ORT 1.23 CPU EP
  could not dispatch the resulting `ConvInteger` nodes against the
  `vector_estimator`'s Conv1d layouts (`NOT_IMPLEMENTED: Could not find an
  implementation for ConvInteger(10) ...`), and the broken model stayed
  cached on disk so every restart hit the same crash.
- Restrict `quantize_dynamic` to `op_types_to_quantize=["MatMul", "Gemm"]`.
  Conv layers stay FP32 (the typical ORT-CPU recipe — `ConvInteger` has
  spotty kernel coverage). Smaller speedup than full quantization but the
  model actually loads.
- Add a recipe identifier (`matmul`) to cache file names
  (`vector_estimator.matmul.int8.onnx`). Old caches from 1.1.1 are
  auto-cleaned at startup, so users hit by the crash loop recover on the
  next boot without manual `/data/.cache/supertonic3.int8/` deletion.
- Add in-process recovery: if an INT8 session ever fails to construct, the
  cache is poisoned (sentinel + delete) and the launcher retries with the
  FP32 path in the same process — no more bounce loop.

## 1.1.1

- **Fix**: 1.1.0 silently fell back to FP32 because `onnxruntime.quantization`
  imports `onnx` (the schema/protobuf library, separate from `onnxruntime`),
  which wasn't installed in the image. The fallback path worked as designed
  — `INT8 substitution skipped: No module named 'onnx'` — but the perf
  improvement never landed. Add `onnx>=1.16,<2.0` to the Dockerfile.

## 1.1.0

- **INT8 dynamic quantization** of the two heavy ONNX models
  (`vector_estimator`, `vocoder`). On AVX-VNNI CPUs (Intel Alder Lake-N,
  12th-gen+ Core, modern AMD Ryzen) this roughly halves synthesis time:
  RTF on N100 (4 cores, `steps=3`) measured down from ≈3.5 to ≈1.5–1.8.
  Implementation is a launcher-side `onnxruntime.InferenceSession` patch
  that lazily quantizes on first start and caches results to
  `/data/.cache/supertonic3.int8/`. Toggleable via the new `quantize`
  option (default `true`). Failure mode is silent fallback to FP32 with
  a `<name>.failed` sentinel in the cache dir.
- **Force `SUPERTONIC_INTER_OP_THREADS=1`**. Upstream `wyoming_supertonic`
  sets it to `threads // 2`, but `supertonic/loader.py` hard-codes
  `execution_mode=ORT_SEQUENTIAL` — so any `inter_op > 1` only spawns
  unused threads competing with the intra-op pool. Small win (~5–10%)
  but free.
- Updated performance table in `DOCS.md` with FP32 vs INT8 RTF columns.

## 1.0.0

- Initial release
- Wraps [wyoming_supertonic](https://github.com/mitrokun/wyoming_supertonic)
  (commit `c40c2c7`) around [Supertonic](https://github.com/supertone-inc/supertonic) V3 (`supertonic==1.2.0`)
- Wyoming protocol on port `10209`
- Streaming synthesis enabled by default
- Auto-discovery via the Home Assistant Wyoming integration
- Built-in voices `M1`–`M5`, `F1`–`F5` across 31 supported languages
- Persistent Hugging Face model cache in `/data/hf_cache`
- Warms up all 10 voices at container startup so the first user request is
  instant (no ONNX cold-start, no per-voice lazy-load)
- Replaces upstream's silent `_synthesize_text` exception swallowing — synth
  errors now propagate to a Wyoming `Error` event so Home Assistant fails
  fast instead of waiting for its TTS timeout
- Sets `HOME=/data` so the supertonic library's hard-coded
  `~/.cache/supertonic3` path lands on the persistent add-on volume
  (`SUPERTONIC_CACHE_DIR` is bypassed when the library is given a model name,
  which `TTS()` always does)
- Pins `onnxruntime==1.23.1` (the version Supertone tested against).
- Disables nested parallelism: sets `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=
  MKL_NUM_THREADS=BLIS_NUM_THREADS=NUMEXPR_NUM_THREADS=1` before any imports
  so ONNX Runtime's thread pool is the only multi-threading layer. Without
  this, OMP and BLAS each spawn their own pools and compete with ORT for
  cores, producing ~12–16 contending threads on a 4-core N100.
- Removes the previous `OMP_PROC_BIND=FALSE` Dockerfile env: `false` is the
  libgomp default anyway, and explicitly setting it encouraged thread
  migration and cache misses on small-core hosts.
- Default `steps` lowered from `5` to `3` so CPU-only hosts get usable
  latency out of the box. Bench data on Intel N100 (4 cores): `steps=5`
  gave RTF ≈ 5; `steps=3` gives ≈ 40 % faster synth at a small quality cost.
  Raise to `5` if your hardware has headroom.
- Configurable warm-up: `warmup_voices` list option (default `["M1"]`)
  controls which voices are pre-loaded at startup. Reduces typical boot time
  from ~150 s (all 10 voices) to ~15–20 s (single voice).
- Adds startup diagnostics: `os.cpu_count`, `sched_getaffinity`, ONNX Runtime
  version and available providers, and per-request RTF (synth-time /
  audio-duration). Makes it possible to tell threading issues from CPU caps
  from real model cost.
