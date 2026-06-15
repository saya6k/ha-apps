# AGENTS.md

Guidance for AI coding agents working on this repository. Detailed history
lives in `CHANGELOG.md` — read that for the *why* behind older decisions.

## What this repo is

A single Home Assistant **app** (the new HA term for what used to be
called an "add-on") running Supertonic as a Wyoming TTS service. The
whole repo *is* the app. As of **2.0.0** the engine is
[`supertonic-mnn`](https://github.com/vra/supertonic-mnn) (MNN). The 1.x
ORT/OpenVINO stack is gone — see CHANGELOG before reintroducing any of it.

## Git / repo tracking

Part of the `ha-apps` monorepo — one git repo at the root, no per-app
`.git` checkouts. Tracking is **stage-gated** by the root `.gitignore`:
only `stage: stable` add-ons are committed; experimental ones are
gitignored and stay local-only. Promote one by setting `stage: stable`
in `config.yaml`, deleting its line from the root `.gitignore`, then
`git add` it.

**This add-on:** tracked (`stage: stable`).

## Layout

```
config.yaml / Dockerfile                app packaging (base image is pinned
                                        in the Dockerfile FROM — build.yaml
                                        is retired since Supervisor 2026.04.0)
pyproject.toml                          our bridge package metadata
wyoming_supertonic/
  __main__.py    argparse + server
  handler.py     Wyoming events, TTFT log
  engine.py      SupertonicTTS wrapper, MNN config patch, CPU diag, auto-precision
  const.py       voices, language name↔code, defaults
rootfs/etc/s6-overlay/s6-rc.d/          supertonic (longrun) + discovery (oneshot)
translations/en.yaml + ko.yaml          option UI strings
CHANGELOG.md / DOCS.md / README.md      user-facing docs (HA renders the first two)
```

Follow the [Piper app](https://github.com/home-assistant/addons/tree/master/piper) (still in the legacy `addons` repo URL) for s6 / discovery / healthcheck conventions; deviate only with reason. We also delegate CI / build to [`hassio-addons/workflows`](https://github.com/hassio-addons/workflows) reusable workflows — `.github/workflows/{ci,deploy,lock,stale}.yaml` are thin callers; do not duplicate their logic locally.

## Documentation layout

| File | Role | Length target |
| ---- | ---- | ------------- |
| `README.md`        | One-paragraph blurb. Keep tiny. | ~15 lines |
| `DOCS.md`          | User-facing options + perf table. HA renders it as the "Documentation" tab. | ≤ ~80 lines |
| `AGENTS.md`        | This file — agent/dev guidance for the *current* code. Symlinked as `CLAUDE.md`. | ~100 lines |
| `CHANGELOG.md`     | Per-version headline. HA renders this in the app UI. Keep each version 5–15 lines. | — |
| `.agents/`           | Local dev decision logs / postmortems / *why* behind changes. **Gitignored** — never link to `.agents/` from the shipped docs (README/DOCS/AGENTS/CHANGELOG); the link would dangle for end users. | free-form |
| `translations/<lang>.yaml` | Option UI labels/descriptions. | — |

Rule of thumb when writing docs: **CHANGELOG = *what* changed**, **AGENTS = *current state* of the code**, **DOCS = *user-visible knobs***, **`.agents/` = *why* / decision log**. If a paragraph fits "we considered X and rejected it because Y", it belongs in `.agents/`, not in any shipped file.

## Engine integration

`engine.py` does four non-obvious things on top of `supertonic_mnn`:

1. **Thread env pinning** — `OMP_NUM_THREADS=1` etc. set at module import,
   before numpy/MNN load. Stops libgomp's per-core pool fighting MNN's.
2. **MNN config patching** — `_patch_mnn_config()` rewrites
   `config.json` after `ensure_models()` to inject `threads` and
   `mnn_memory` (the library reads them off disk; no Python override).
3. **Auto precision** — `_detect_best_precision()` reads `/proc/cpuinfo`
   and picks `int8` (AVX-VNNI / NEON SDOT), `fp16` (FEAT_FP16-only ARM),
   or `fp32` (fallback). Decision is logged.
4. **CPU diagnostics** — `log_cpu_diagnostics()` dumps per-core
   governor + freqs at boot so users see throttling without grepping sysfs.

Warm-up = one short utterance per voice (no multi-shape sweep — MNN doesn't
need it). `handler.py` logs `TTFT` once per client request (first chunk only).

## Options → CLI

| App option      | CLI flag           | Notes |
| --------------- | ------------------ | ----- |
| `speed`/`steps` | `--speed`/`--steps`| floats / ints |
| `threads`       | `--threads`        | patched into `config.json` |
| `precision`     | `--precision`      | `auto`\|`fp16`\|`fp32`\|`int8` |
| `model_version` | `--version`        | `v2`\|`v3` (overrides argparse default `--version` behaviour) |
| `mnn_memory`    | `--mnn-memory`     | `low`\|`normal`\|`high` |
| `warmup_voices` | `--warmup-voices`  | comma-joined from YAML array by `run` script |
| `no_streaming`/`debug_logging` | `--no-streaming`/`--debug` | flags |

Voice (`M1`–`F5`) **and language** are **not** app options — both come
per-request from the Wyoming client. The HA pipeline's TTS language rides in
`Synthesize.voice.language`; `handler.py` normalises it (`en-US` → `en`,
names → ISO via `resolve_language`) and falls back to `DEFAULT_LANGUAGE`
only when the client sends none. `__main__._build_info` advertises all
`LANGUAGES` on every voice so HA knows what's offered.

## Pins & cache

- `Dockerfile` installs `supertonic-mnn` from a pinned git SHA
  (`SUPERTONIC_MNN_REF`). PyPI's 0.1.3 lacks `version=`/`lang=` kwargs we
  need; switch to `pip install supertonic-mnn>=0.2.0` once upstream
  publishes (and drop the apt install/purge of `git`).
- Models cache under `/data/.cache/supertonic-mnn` because the s6 `run`
  script exports `HOME=/data`. `backup_exclude: [".cache/**"]`.
- Bump version in all three on release: `config.yaml`, `pyproject.toml`,
  `wyoming_supertonic/__init__.py`.

## Local development

The host Python (Mac, Linux dev box) is **not** what runs in production.
The Debian-based HA base image ships its own `python3`. For quick
syntax / import checks during dev, use a project-local venv managed
with [`uv`](https://github.com/astral-sh/uv) — fast, and its global
hardlinked wheel cache deduplicates across multiple addon repos
sharing the same deps.

```bash
# one-time
uv venv .venv --python 3.12
uv pip install 'wyoming>=1.5,<2' 'sentence-stream>=1.0.4' 'numpy'
# note: `supertonic-mnn` is NOT installed locally — it isn't on PyPI
# and the Dockerfile pulls it from a pinned git SHA. Local venv is for
# import / syntax / handler.py edits only; engine.py end-to-end testing
# requires the Docker image.

# day-to-day
.venv/bin/python -c "from wyoming_supertonic import const, handler; print('OK')"
```

`.venv/` is gitignored.

For full engine testing, build the image (`docker build .`) — that's
the only way to exercise the MNN runtime + voice models against the
exact Python the addon ships with.

## Sanity checks before PR

YAML lint, `shellcheck` the s6 scripts, `python3 -c "import ast; ast.parse(...)"`
each `*.py`, build for one arch, smoke-test `echo '{"type":"describe"}' | nc -w 1 localhost 10209`
returns `"Supertonic"`.

## Don'ts

- Don't reintroduce ORT/OpenVINO without a written reason — 2.0.0 removed
  ~400 MB and a lot of monkey-patching for a reason.
- Don't add backwards-compat shims for removed options (`provider`,
  `crop_silence`, `language`).
- Don't re-add a `language` add-on option — language is per-request from the
  pipeline (`Synthesize.voice.language`); a fixed option only drifts from the
  pipeline's choice.
- Don't pre-download models in the Dockerfile; HF cache works fine.
- Don't add `armv7`/`armhf`/`i386` without confirming MNN wheels exist.
- Don't forget the `chmod +x` block in `Dockerfile` when adding a new s6 script.
- `icon.png` / `logo.png` are MIT-licensed assets copied from
  `supertone-inc/supertonic-py`. If you swap them, update `NOTICE`
  in lockstep so the attribution stays accurate.
