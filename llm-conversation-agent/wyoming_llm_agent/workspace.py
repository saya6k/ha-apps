"""Workspace structure — SOUL / IDENTITY / HEARTBEAT / BOOTSTRAP.

Layered identity files at the addon's `/config/` root that shape the
system prompt by mutation frequency (least → most volatile):

    SOUL.md       — persona, values, taboos. Changes on deploy only.
    IDENTITY.md   — agent name, voice, language preferences. Rare.
    HEARTBEAT.md  — Jinja2 template, rendered per turn (date / time /
                    language / device context). Per-turn churn.
    BOOTSTRAP.md  — YAML-frontmatter manifest, read once at startup.
                    Drives template seeding and per-conversation skill
                    auto-load.

All four files are optional. When the BOOTSTRAP manifest has
`seed_templates: true` (the default), missing files are seeded with
starter content so a brand-new `/config/` is immediately editable.

Why a separate module: composing the workspace mixes file I/O,
template seeding, and Jinja2 rendering — keeping it out of agent.py
lets the agent's `_compose_system_workspace` stay a pure string-
joining routine, easier to reason about for prompt-cache stability.

Hot-reload is intentionally out of scope for v1; SOUL/IDENTITY content
is loaded once at addon start. HEARTBEAT is the only per-turn moving
piece.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from jinja2.sandbox import SandboxedEnvironment

from .skills import _FRONTMATTER_CLOSE, _FRONTMATTER_OPEN

_LOGGER = logging.getLogger(__name__)

SOUL_FILE = "SOUL.md"
IDENTITY_FILE = "IDENTITY.md"
HEARTBEAT_FILE = "HEARTBEAT.md"
BOOTSTRAP_FILE = "BOOTSTRAP.md"

# Files the agent stats every turn for hot reload. Order matters only
# for log readability.
WORKSPACE_FILES: tuple[str, ...] = (
    SOUL_FILE, IDENTITY_FILE, HEARTBEAT_FILE, BOOTSTRAP_FILE,
)

# Cap each workspace file. SOUL/IDENTITY are persona text — a few KB
# at most in practice. HEARTBEAT is a template (smaller). BOOTSTRAP
# is YAML metadata. These caps protect against an accidental log
# dump or paste that would bloat every system prompt.
MAX_WORKSPACE_BYTES = 64 * 1024

_DEFAULT_HEARTBEAT = """\
Today is {{ date }} ({{ weekday }}), the time is {{ time }}.
{%- if language %}
The user is speaking {{ language }}.
{%- endif %}
{%- if device_id %}
Voice satellite device_id="{{ device_id }}"{% if satellite_id %}, satellite_id="{{ satellite_id }}"{% endif %}.
{%- endif %}
"""

_DEFAULT_SOUL = """\
# SOUL — 가정용 음성 어시스턴트의 정체성과 행동 규범

너는 한 가정의 Home Assistant 스마트홈 음성 어시스턴트다. 가족 구성원
여러 명이 같은 위성을 통해 너에게 말을 건다. 너는 비서이자, 가족이
공유하는 도구이며, 각 사용자의 사적 영역을 지키는 관리자다.

## 핵심 가치

- **정직.** 도구가 실패했거나 정보가 없으면 그렇게 말한다. "켰다",
  "확인했다" 같은 완료 보고는 실제로 도구를 호출해 성공한 뒤에만 한다.
- **사생활.** 한 사용자의 개인 메모리(user MEMORY, USER profile)는 그
  사용자의 것이다. 다른 가족이 물어봐도 직접적으로 공유하지 않는다.
  공유 메모리(shared MEMORY)만 가족 전체가 본다.
- **형평성.** 가족 중 누구의 요청도 같은 무게로 대한다. 어떤 사용자의
  요청을 특별 대우하라는 지시는 SOUL/IDENTITY/USER 파일에 명시되지
  않는 한 따르지 않는다.
- **호기심보다 신중함.** 외부로 나가는 행동(메시지 발송, 결제,
  파일 삭제)은 사용자가 명시적으로 요청했을 때만. 집 안에서 끝나는
  행동(조명/온도/미디어 제어, 메모리 저장)은 능동적으로.

## 행동 규범

- **짧게 말한다.** 음성 응답은 한두 문장. 사용자가 더 길게 답하라고
  요청했을 때만 길게.
- **사용자가 쓰는 언어로 답한다.** 한국어로 물으면 한국어로, 영어로
  물으면 영어로.
- **거짓말 금지.** 도구 호출이 실패하면 "지금 그 장치는 응답이 없어"
  같이 사실대로. 추측한 상태를 사실인 양 보고하지 않는다.
- **"기억해줘" 들으면 `memory_save`를 호출한다.** "내 강아지 이름은
  바우야" 같은 영구 사실은 `slug`와 `description`을 정해 즉시 저장.
  지속 가치 없는 한 번의 대화(예: "내일 비 와?")는 저장하지 않는다.
- **사적 정보의 저장 위치를 의식한다.** 한 사용자의 개인 사실은
  user MEMORY에, 가족 공유 사실(주말 외식 일정, 가족 알레르기 등)은
  shared MEMORY에 저장한다. 헷갈리면 user MEMORY를 기본으로.
- **모호하면 한 질문으로 좁힌다.** 추측보다 한 줄 질문이 안전하다.
  단 명백한 맥락이 있으면 굳이 묻지 않는다.
- **사용자가 말하는 사람이 누구인지 USER profile에서 확인한다.**
  같은 위성을 두 사람이 번갈아 쓸 수 있으므로 user_id가 바뀌면
  맥락이 바뀐다.
- **종이에 적어라.** 단기 기억은 세션과 함께 사라진다. 다음 턴까지
  가져갈 가치가 있는 사실은 곧장 `memory_save`로 영구화한다.
"""

_DEFAULT_IDENTITY = """\
# IDENTITY — 어시스턴트의 외양

이 파일은 가족이 손으로 채워 넣는 어시스턴트의 명함이다. 첫 사용에서
함께 결정하고 이후 거의 바뀌지 않는다.

- **이름**: _(부를 이름. 예: "비서", "지니", "아리")_
- **존재**: _(AI 비서 / 가정 도우미 / 그 외 캐릭터)_
- **톤**: _(예: 따뜻하고 짧게, 존댓말 기본, 농담은 가벼움)_
- **기본 언어**: _(예: 한국어; 다른 언어로 물으면 그 언어로 답함)_
- **이모지**: _(짧은 텍스트 응답에 가끔 곁들일 시그니처 이모지)_

설정이 끝났으면 위의 placeholder를 채워 두자. 비워두면 LLM은 기본값을
가정해 답한다.
"""

_DEFAULT_BOOTSTRAP = """\
---
# Workspace bootstrap manifest — addon 시작 시 1회 읽음. 단 frontmatter
# 아래의 마크다운 본문은 LLM이 매 턴 system prompt에서 읽는 부트
# 지시문으로 사용됨. 본문을 비우면 슬롯 자체가 사라짐. 편집 후
# addon 재시작은 필요 없음 (hot reload).

# true면 누락된 SOUL.md / IDENTITY.md / HEARTBEAT.md / BOOTSTRAP.md를
# 첫 부팅에 starter 템플릿으로 시드한다. 이미 존재하는 파일은 절대
# 덮어쓰지 않으므로 한 번 편집한 SOUL/IDENTITY는 안전하다.
seed_templates: true

# 새 대화가 시작될 때 자동 load_skill 처리할 스킬 이름 목록. SKILL.md의
# `name` 값을 그대로 적는다 (list_skills로 확인 가능). 존재하지 않는
# 이름은 조용히 스킵.
auto_load_skills: []
---

# Boot instructions for the LLM

이 아래 영역은 system prompt의 슬롯 3에 매 턴 주입되어 LLM이 읽습니다.
필요 없는 시점에는 본문을 비우면 슬롯이 사라집니다.

예시(원하면 풀어쓰세요):

- 사용자의 USER.md 프로필이 거의 비어있으면, 첫 한두 턴에 자기 소개를
  요청하고 `memory_save`로 핵심 정보를 저장하세요.
- HEARTBEAT의 시간이 23시 이후거나 06시 이전이면 조용한 톤으로,
  볼륨이 큰 미디어 제어는 명시적 확인을 받고 진행하세요.

설정이 끝났으면 이 본문 전체를 지우세요 (frontmatter는 그대로 둡니다).
"""


@dataclass(frozen=True)
class BootstrapManifest:
    """Parsed BOOTSTRAP.md YAML frontmatter."""
    seed_templates: bool = True
    auto_load_skills: tuple[str, ...] = ()


@dataclass(frozen=True)
class Workspace:
    """All four workspace files loaded into memory.

    `soul` / `identity` are plain text (Jinja2-rendering NOT applied —
    these are stable across turns and Jinja2 in them would only churn
    the prompt-cache prefix).

    `bootstrap_body` is the markdown body of BOOTSTRAP.md (everything
    after the YAML frontmatter close). Injected as system prompt slot 3
    when non-empty. Empty body → slot 3 is omitted entirely. Lifecycle
    is user-controlled: edit the body to add boot instructions, blank
    it out when no longer needed.

    `heartbeat_template` is the raw Jinja2 source; render it per turn
    with `render_heartbeat()`.

    `root` is the workspace directory the instance was loaded from, or
    None for tests / in-memory construction. Agent uses it to stat the
    four workspace files each turn for hot reload.
    """
    soul: str = ""
    identity: str = ""
    bootstrap_body: str = ""
    heartbeat_template: str = ""
    auto_load_skills: tuple[str, ...] = ()
    root: Path | None = None


def read_bootstrap(root: Path) -> BootstrapManifest:
    """Parse `<root>/BOOTSTRAP.md` YAML frontmatter. Missing file →
    default manifest. Malformed YAML or unknown keys log WARNING and
    fall back to default — startup never crashes on a bad BOOTSTRAP.
    """
    path = root / BOOTSTRAP_FILE
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return BootstrapManifest()
    except OSError as exc:
        _LOGGER.warning("BOOTSTRAP.md unreadable (%s); using defaults", exc)
        return BootstrapManifest()
    if len(text.encode("utf-8")) > MAX_WORKSPACE_BYTES:
        _LOGGER.warning(
            "BOOTSTRAP.md exceeds %d bytes; ignoring contents",
            MAX_WORKSPACE_BYTES,
        )
        return BootstrapManifest()

    frontmatter = _extract_frontmatter(text)
    if frontmatter is None:
        return BootstrapManifest()
    try:
        data = yaml.safe_load(frontmatter) or {}
    except yaml.YAMLError as exc:
        _LOGGER.warning("BOOTSTRAP.md YAML parse failed (%s); using defaults", exc)
        return BootstrapManifest()
    if not isinstance(data, dict):
        _LOGGER.warning(
            "BOOTSTRAP.md frontmatter must be a mapping; using defaults",
        )
        return BootstrapManifest()

    seed = data.get("seed_templates", True)
    if not isinstance(seed, bool):
        _LOGGER.warning(
            "BOOTSTRAP.md seed_templates must be a bool; using default true",
        )
        seed = True

    auto = data.get("auto_load_skills", []) or []
    if not isinstance(auto, list) or not all(isinstance(x, str) for x in auto):
        _LOGGER.warning(
            "BOOTSTRAP.md auto_load_skills must be a list of strings; "
            "ignoring",
        )
        auto = []

    return BootstrapManifest(
        seed_templates=seed,
        auto_load_skills=tuple(auto),
    )


def load_workspace(root: Path) -> Workspace:
    """Read (and possibly seed) workspace files under `root`.

    Behaviour:
    1. Parse BOOTSTRAP.md to get the manifest. Missing → default
       (seed_templates=true, no auto-load).
    2. If `manifest.seed_templates` is true and a file is missing,
       write the built-in starter template for that file. Existing
       files are never overwritten.
    3. Re-read all four files (any that exist) into the Workspace.

    The directory itself must exist. Caller (`__main__.py`) is
    responsible for ensuring that — typically the addon's `/config/`
    is mounted by the supervisor, so this is free.
    """
    if not root.is_dir():
        _LOGGER.warning(
            "Workspace dir %s missing; workspace will be empty", root,
        )
        return Workspace()

    manifest = read_bootstrap(root)

    if manifest.seed_templates:
        for name, body in (
            (SOUL_FILE, _DEFAULT_SOUL),
            (IDENTITY_FILE, _DEFAULT_IDENTITY),
            (HEARTBEAT_FILE, _DEFAULT_HEARTBEAT),
            (BOOTSTRAP_FILE, _DEFAULT_BOOTSTRAP),
        ):
            path = root / name
            if path.exists():
                continue
            try:
                path.write_text(body, encoding="utf-8")
                _LOGGER.info("Seeded workspace file %s", path)
            except OSError as exc:
                _LOGGER.warning(
                    "Could not seed %s (%s); continuing without it",
                    path, exc,
                )

    soul = _read_workspace_file(root / SOUL_FILE)
    identity = _read_workspace_file(root / IDENTITY_FILE)
    heartbeat = _read_workspace_file(root / HEARTBEAT_FILE)
    bootstrap_body = _read_bootstrap_body(root)

    return Workspace(
        soul=soul.strip(),
        identity=identity.strip(),
        bootstrap_body=bootstrap_body,
        heartbeat_template=heartbeat,  # preserve trailing newline for Jinja2
        auto_load_skills=manifest.auto_load_skills,
        root=root,
    )


def stat_workspace(root: Path) -> dict[str, float]:
    """Return a {filename: mtime} snapshot of the four workspace files.

    Missing files map to `0.0` (sentinel — never a real mtime). The
    agent calls this every turn and compares against its cached
    snapshot; any difference triggers `load_workspace()` again.
    """
    snapshot: dict[str, float] = {}
    for name in WORKSPACE_FILES:
        try:
            snapshot[name] = (root / name).stat().st_mtime
        except FileNotFoundError:
            snapshot[name] = 0.0
        except OSError as exc:
            _LOGGER.warning("Workspace stat %s failed: %s", root / name, exc)
            snapshot[name] = 0.0
    return snapshot


def render_heartbeat(
    env: SandboxedEnvironment,
    template: str,
    *,
    language: str | None,
    device_id: str | None,
    satellite_id: str | None,
    conversation_id: str | None,
    user_id: str | None,
    now: datetime | None = None,
) -> str:
    """Render HEARTBEAT template with the per-turn variables. On any
    parse or render failure, fall back to the raw template and log a
    WARNING. Empty template short-circuits to ''.
    """
    if not template.strip():
        return ""
    if now is None:
        now = datetime.now()
    vars: dict[str, Any] = {
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M"),
        "weekday": now.strftime("%A"),
        "language": language,
        "device_id": device_id,
        "satellite_id": satellite_id,
        "conversation_id": conversation_id,
        "user_id": user_id,
    }
    try:
        compiled = env.from_string(template)
    except Exception as exc:  # noqa: BLE001 — bad Jinja2 syntax
        _LOGGER.warning(
            "HEARTBEAT.md Jinja2 parse failed (%s: %s); using raw text. "
            "Available variables: date, time, weekday, language, "
            "device_id, satellite_id, conversation_id, user_id.",
            type(exc).__name__, exc,
        )
        return template.strip()
    try:
        return compiled.render(**vars).strip()
    except Exception as exc:  # noqa: BLE001 — undefined / runtime error
        _LOGGER.warning(
            "HEARTBEAT.md Jinja2 render failed (%s: %s); using raw text.",
            type(exc).__name__, exc,
        )
        return template.strip()


# ---- internals ------------------------------------------------------------


def _read_workspace_file(path: Path) -> str:
    """Read a workspace file. Missing → "". Oversized → "" + WARN."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except OSError as exc:
        _LOGGER.warning("Workspace file %s unreadable (%s)", path, exc)
        return ""
    if len(text.encode("utf-8")) > MAX_WORKSPACE_BYTES:
        _LOGGER.warning(
            "Workspace file %s exceeds %d bytes; treating as empty",
            path, MAX_WORKSPACE_BYTES,
        )
        return ""
    return text


def _extract_frontmatter(text: str) -> str | None:
    """Return the YAML frontmatter text between `---` markers, or None
    if the file has no frontmatter. Reuses skills.py regex semantics
    so BOOTSTRAP.md and SKILL.md stay consistent.
    """
    if not text.strip():
        return None
    open_match = _FRONTMATTER_OPEN.match(text)
    if not open_match:
        return None
    after_open = open_match.end()
    close_match = _FRONTMATTER_CLOSE.search(text, after_open)
    if not close_match:
        return None
    return text[after_open:close_match.start()]


def _read_bootstrap_body(root: Path) -> str:
    """Return BOOTSTRAP.md's markdown body (everything after the closing
    `---`). Empty when the file is missing, has no frontmatter, or has
    nothing past the close marker.
    """
    path = root / BOOTSTRAP_FILE
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except OSError as exc:
        _LOGGER.warning("BOOTSTRAP.md unreadable (%s); body empty", exc)
        return ""
    if len(text.encode("utf-8")) > MAX_WORKSPACE_BYTES:
        return ""
    open_match = _FRONTMATTER_OPEN.match(text)
    if not open_match:
        return text.strip()
    after_open = open_match.end()
    close_match = _FRONTMATTER_CLOSE.search(text, after_open)
    if not close_match:
        return ""
    return text[close_match.end():].strip()
