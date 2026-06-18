# Repository agent instructions

> `CLAUDE.md` and `GEMINI.md` are symlinks to this file — edit `AGENTS.md`.
> Per-app guidance lives in each subproject's own `AGENTS.md`. **Read it first when working in a subproject.**

HA add-on monorepo. Shared git history, issue tracker, and release pipeline. Each add-on has its own version, Dockerfile, and CHANGELOG. Subproject names use the bare slug (no `ha-` prefix); keep `ha-` in GitHub URLs, package names, Wyoming Info strings, and CHANGELOG cross-references.

## Apps

| App | What it is |
|---|---|
| [`livekit-wakeword/`](livekit-wakeword/AGENTS.md) | Wyoming wake word — livekit-wakeword runtime + our incremental oWW-compatible bridge. Serves oWW zoo + custom `/share` models. |
| [`nemotron-asr-c/`](nemotron-asr-c/AGENTS.md) | Wyoming STT — Nemotron 0.6B on pure C (nemotron-asr-streaming.c). Boot-time .nemo conversion, true-streaming (stateful mel→encoder→rnnt cascade), hotword biasing. |
| [`nemo-asr-cpp/`](nemo-asr-cpp/AGENTS.md) | Wyoming STT — Nemotron 0.6B on ggml/parakeet.cpp (GGUF). Fast/light CPU sibling; ctypes over a flat C API. |
| [`supertonic/`](supertonic/AGENTS.md) | Wyoming TTS — supertonic-mnn. Python bridge with auto-precision detection. |
| [`voiceprint/`](voiceprint/AGENTS.md) | Speaker-verifying Wyoming STT proxy. Pass-through gate for enrolled voices. CAM++ embeddings on LiteRT. |
| [`wardrowbe/`](wardrowbe/AGENTS.md) | Anyesh/wardrowbe: Postgres + Redis + FastAPI + arq + Next.js + nginx + daily backup in one s6-overlay v3 container. |
| [`zensical/`](zensical/AGENTS.md) | Renders `/config/docs/` as a Zensical site via the HA ingress panel. Stateless renderer + inotify watcher. |

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

**Scopes:** `livekit-wakeword` · `nemotron-asr-c` · `nemo-asr-cpp` · `supertonic` · `voiceprint` · `wardrowbe` · `zensical` · `repo`

**Types:** `feat` (minor) · `fix`/`perf`/`revert` (patch) · `docs`/`refactor`/`build`/`ci` (patch, in CHANGELOG) · `chore`/`test`/`style` (no release) · `type!` / `BREAKING CHANGE:` footer (major)

Wrong or missing scope = release-please silently drops the change. Multi-app commits must be split by scope. See `.agents/skills/conventional-commit/SKILL.md`.

## Releases

1. Land Conventional-Commit PRs on `main`.
2. release-please opens `chore(<addon>): release <ver>` PR — auto-bumps `config.yaml` / `CHANGELOG.md` (+ `pyproject.toml` where applicable).
3. Merge → tags `<addon>-v<ver>`. No image is published — HA builds each add-on locally from its Dockerfile; CI build-tests the Dockerfile (`.github/workflows/ci.yml`, `push: false`).

Never squash-merge a multi-scope PR — squash collapses all scopes to the title's scope; use rebase-merge or split into one PR per scope. Config: `.github/release-please-config.json` + `.github/.release-please-manifest.json`. No `version.txt`.

## Invariants

- **No top-level build commands.** `pyproject.toml` / `Dockerfile` live in subprojects; run from there.
- **LF line endings everywhere** (`.gitattributes`). CRLF breaks bashio and s6 silently.
- **`config.yaml` at subproject root only.** Supervisor scans every `config.*` it finds.
- **Never `--no-verify` / `--no-gpg-sign`.** Fix hook failures at the root cause.
- **Lint config is at the root** (`.hadolint.yaml`, `.markdownlint.yaml`, `.shellcheckrc`). Don't duplicate in subprojects.
- **Stage gating:** stable = no `stage:` key, committed. Experimental = `stage: experimental`, committed. To promote: remove the key. (Registrations in release-please / labels / labeler / issue templates are done at scaffold time for both stages; no rework at promotion.)
- **`.github/labels.yml` is SoT for labels.** Hand edits on GitHub are wiped on the next sync.
- **Doc taxonomy:** `CHANGELOG.md` = what changed · `AGENTS.md` = current shape · `DOCS.md` = user knobs · `README.md` = one-paragraph blurb. Never link to `.agents/` from shipped docs.
