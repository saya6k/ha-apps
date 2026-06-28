# Repository agent instructions

> `CLAUDE.md` and `GEMINI.md` are local symlinks to this file (gitignored) — edit `AGENTS.md`.
> Per-app guidance lives in each subproject's own `AGENTS.md`. **Read it first when working in a subproject.**

HA add-on catalog repo. Shared git history, issue tracker, and release pipeline. Apps with their own `ha-app-*` repo keep only metadata here (`config.yaml`, `icon.png`, `logo.png`, `translations/`, `DOCS.md`, `README.md`); source, Dockerfile, and CI live in the per-app repo. Apps without a dedicated repo still carry full source here. Subproject names use the bare slug (no `ha-` prefix); keep `ha-` in GitHub URLs, package names, Wyoming Info strings, and CHANGELOG cross-references.

## Apps

| App | What it is |
|---|---|
| `livekit-wakeword/` ([ha-app-livekit-wakeword](https://github.com/saya6k/ha-app-livekit-wakeword)) | Wyoming wake word — livekit-wakeword runtime + our incremental oWW-compatible bridge. Serves oWW zoo + custom `/share` models. Metadata only — source and CI live in ha-app-livekit-wakeword. |
| `nemotron-asr-c/` ([ha-app-nemotron-asr-c](https://github.com/saya6k/ha-app-nemotron-asr-c)) | Wyoming STT — Nemotron 0.6B on pure C (nemotron-asr-streaming.c). Boot-time .nemo conversion, true-streaming (stateful mel→encoder→rnnt cascade), hotword biasing. Metadata only. |
| `nemo-asr-cpp/` ([ha-app-nemo-asr-cpp](https://github.com/saya6k/ha-app-nemo-asr-cpp)) | Wyoming STT — Nemotron 0.6B on ggml/parakeet.cpp (GGUF). Fast/light CPU sibling; ctypes over a flat C API. Metadata only. |
| `supertonic/` ([ha-app-supertonic](https://github.com/saya6k/ha-app-supertonic)) | Wyoming TTS — supertonic-mnn. Python bridge with auto-precision detection. Metadata only. |
| `voiceprint/` ([ha-app-voiceprint](https://github.com/saya6k/ha-app-voiceprint)) | Speaker-verifying Wyoming STT proxy. Pass-through gate for enrolled voices. CAM++ embeddings on LiteRT. Metadata only. |
| `wardrowbe/` ([ha-app-wardrowbe](https://github.com/saya6k/ha-app-wardrowbe)) | Anyesh/wardrowbe: Postgres + Redis + FastAPI + arq + Next.js + nginx + daily backup in one s6-overlay v3 container. Metadata only — source and CI live in ha-app-wardrowbe. |
| `zensical/` ([ha-app-zensical](https://github.com/saya6k/ha-app-zensical)) | Renders `/config/docs/` as a Zensical site via the HA ingress panel. Stateless renderer + inotify watcher. Metadata only. |
| `otelcol/` ([ha-app-otelcol](https://github.com/saya6k/ha-app-otelcol)) | OpenTelemetry Collector — otelcol-contrib + Python HA-API bridge. Collects logs, metrics, and traces from HA Core, Supervisor, and add-ons; exports via OTLP. `stage: experimental`. Metadata only. |

## AI tooling (`.agents/`)

```
.agents/
├── skills/     ← reusable abilities (Skill — "어떻게 잘 할까?") · .claude/skills symlinks here
├── workflows/  ← task procedures (Workflow — "무슨 순서로 할까?") · .claude/commands symlinks here
├── agents/     ← Claude Code agent definitions · .claude/agents symlinks here
└── memory/     ← cross-conversation context notes (gitignored)
```

| | Skill | Workflow |
|---|---|---|
| 의미 | 능력 | 절차 |
| 질문 | "어떻게 잘 할까?" | "무슨 순서로 할까?" |
| 재사용 범위 | 매우 넓음 | 특정 작업 |
| 호출 방식 | 필요 시 참조 | 작업 시작 시 실행 |

**`skills/`** — reusable abilities, referenced when needed:

| 파일 | 역할 |
|---|---|
| `app-preflight` | PR 전 Python parse · yamllint · shellcheck 실행법 |
| `conventional-commit` | release-please용 커밋 메시지 작성법 |

**`workflows/`** — task procedures, opened at the start of a task:

| 파일 | 역할 |
|---|---|
| `new-app-scaffold.md` | 새 앱 추가 절차 (파일 생성 → `.github/` 등록) |
| `app-dev-pr.md` | 브랜치 생성 → preflight → `dev`에 통합 |
| `app-promote-to-main.md` | 승인된 `dev → main` 승격 → 릴리즈 검증 → 로컬 sync |

**Typical flow:**
- New app: `new-app-scaffold` → implement → `app-preflight` → `conventional-commit` → `app-dev-pr`
- Existing change: implement → `app-preflight` → `conventional-commit` → `app-dev-pr`
- Promotion: (user approval) → `app-promote-to-main`

**`memory/`** carries context that isn't in the code — boot gotchas, decisions, verified workarounds. Memory can go stale; always verify against current files.

## Commits (enforced — release-please depends on this)

```
<type>(<scope>): <subject>
```

**Scopes:** `livekit-wakeword` · `nemotron-asr-c` · `nemo-asr-cpp` · `otelcol` · `supertonic` · `voiceprint` · `wardrowbe` · `zensical` · `repo`

**Types:** `feat` (minor) · `fix`/`perf`/`revert` (patch) · `docs`/`refactor`/`build`/`ci` (patch, in CHANGELOG) · `chore`/`test`/`style` (no release) · `type!` / `BREAKING CHANGE:` footer (major)

Wrong or missing scope = release-please silently drops the change. Multi-app commits must be split by scope. See `.agents/skills/conventional-commit/SKILL.md`.

## Releases

ha-apps is the **catalog** — it stores only metadata. Versioning and images are driven by ha-app-* repos.

**Per-app release flow (in the ha-app-* repo):**
1. Merge changes to `main` → release-drafter updates the draft.
2. **Publish the draft** → `build.yml` pushes `ghcr.io/saya6k/app-<slug>:{ver}` to GHCR.
3. `build.yml` dispatches to ha-apps → `sync-app-version.yml` opens
   `chore(<slug>): release <ver>` PR to `dev`, bumping `config.yaml` + prepending
   release notes to `CHANGELOG.md`.
4. Merge sync PR → promote `dev → main` as usual.

**ha-apps-only changes (CI, docs, metadata fixes):**
Land on `dev` via PR → promote. `packages: {}` in release-please config — no
automatic release PRs are generated for ha-apps itself.

Never squash-merge a multi-scope PR — squash collapses all scopes to the title's
scope. Use rebase-merge or split into one PR per scope.
See [[release-please-squash-gotcha]].

## Invariants

- **No top-level build commands.** `pyproject.toml` / `Dockerfile` live in subprojects; run from there.
- **LF line endings everywhere** (`.gitattributes`). CRLF breaks bashio and s6 silently.
- **`config.yaml` at subproject root only.** Supervisor scans every `config.*` it finds.
- **Never `--no-verify` / `--no-gpg-sign`.** Fix hook failures at the root cause.
- **Lint config is at the root** (`.hadolint.yaml`, `.markdownlint.yaml`, `.shellcheckrc`). Don't duplicate in subprojects.
- **Stage gating:** stable = no `stage:` key, committed. Experimental = `stage: experimental`, committed. To promote: remove the key. (Registrations in release-please / labels / labeler / issue templates are done at scaffold time for both stages; no rework at promotion.)
- **`.github/labels.yml` is SoT for labels.** Hand edits on GitHub are wiped on the next sync.
- **Doc taxonomy:** `CHANGELOG.md` = what changed · `AGENTS.md` = current shape · `DOCS.md` = user knobs · `README.md` = one-paragraph blurb. Never link to `.agents/` from shipped docs.
