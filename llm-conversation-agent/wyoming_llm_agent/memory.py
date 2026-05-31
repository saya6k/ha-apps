"""Per-user persistent memory store backing the `memory_*` meta-tools.

Layout under `--memory-dir` (default `/config/memory/`):

    memory/
    ├── shared/
    │   ├── MEMORY.md           # index, one entry per line: `- <slug>: <desc>`
    │   └── <slug>.md           # plain-markdown body (no frontmatter)
    └── users/
        └── <safe_user_id>/
            ├── MEMORY.md
            └── <slug>.md

Identity: HA's voice satellite delivers `Transcript.context["user_id"]`
starting in HA 2026.6.0 (PR #170433). When absent or unsafe, this
module falls back to the `shared` bucket so the addon stays useful on
older HA. `shared` is a reserved bucket name — a user_id literally
equal to `shared` is treated as unknown.

The index file is regenerated from the in-memory dict on every save
or delete. Hand-edits to MEMORY.md survive only if they match the
`- <slug>: <description>` line format; anything else is dropped on the
next write. Body files may be hand-edited freely — `memory_save`
overwrites them.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Same shape as agentskills.io skill names: lowercase letters, digits,
# and internal hyphens. 1-64 chars. Single-char names are allowed.
_SLUG_RE = re.compile(r"^(?:[a-z0-9]|[a-z0-9][a-z0-9-]{0,62}[a-z0-9])$")
# Per-user bucket segment. UUID4 hex (HA's actual user_id format) is
# 32 lowercase hex chars; we accept any lowercase alphanumeric +
# `_` / `-`, up to 64 chars, to stay forward-compatible with whatever
# HA decides to put there. Anything else routes to `shared`.
_USER_ID_RE = re.compile(r"^[a-z0-9_-]{1,64}$")

# One body file's hard cap. Tight enough that a single memory entry
# stays focused — if it doesn't fit in ~4 KB (~1.5 k tokens) the LLM
# is probably journaling instead of remembering. Forces consolidation:
# the model has to decide what is actually worth keeping. Mirrors the
# discipline NousResearch baked into Hermes (2200-char memory cap).
MAX_MEMORY_BYTES = 4 * 1024
# Whole-bucket cap, summed across every saved entry. Generous enough
# for ~8 well-edited memories; tight enough that the catalog stays
# scannable in the system prompt and the LLM is nudged to prune
# rather than accumulate. When this is exceeded, `memory_save` is
# rejected with a directive to consolidate first.
MAX_BUCKET_MEMORY_BYTES = 32 * 1024
MAX_DESCRIPTION_CHARS = 200
# USER.md is a free-form per-user profile, hand-edited by the household
# member — NOT written by the LLM. Bigger cap than a single memory
# because it absorbs timezone, preferences, household role, etc. Read-
# time safety net, not a budget the LLM has to manage.
MAX_USER_PROFILE_BYTES = 16 * 1024
# Per-user BOOTSTRAP.md — onboarding/behavior nudges scoped to one
# household member. Smaller cap than USER.md because it's meant to be
# short instructions, not a profile dump.
MAX_USER_BOOTSTRAP_BYTES = 8 * 1024

_INDEX_FILE_NAME = "MEMORY.md"
_BODY_SUFFIX = ".md"
_SHARED_BUCKET = "shared"
_USER_PROFILE_FILE = "USER.md"
_USER_BOOTSTRAP_FILE = "BOOTSTRAP.md"
_JOURNAL_DIR_NAME = "journal"

# Daily journal caps. Per-entry small so individual notes stay focused;
# per-day big enough that a chatty day doesn't get truncated.
MAX_JOURNAL_ENTRY_BYTES = 4 * 1024
MAX_JOURNAL_DAY_BYTES = 64 * 1024
# YYYY-MM-DD only. Reject anything else (path safety + format invariant).
_JOURNAL_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_DEFAULT_USER_PROFILE = """\
# USER.md — 사용자 프로필

이 파일은 LLM이 매 턴 읽는 사용자 정보입니다. 가정 구성원의 한 명을 가리킵니다.
직접 편집하세요. 어시스턴트가 새로운 정보를 알게 되면 `memory_save`로 별도 메모리에
저장하지만, 아래 핵심 항목은 사람이 손으로 채워 두는 것을 권장합니다.

- **이름**: _(부를 이름)_
- **호칭**: _(아빠 / 엄마 / 누나 / 형 / 본인 등 가족 내 호칭)_
- **시간대**: _(예: Asia/Seoul)_
- **언어**: _(주로 사용하는 언어)_
- **알레르기 / 음식 제약**: _(없으면 "없음")_
- **관심사 / 진행 중 프로젝트**: _(예: 학교, 회사, 취미)_
- **선호**: _(어시스턴트가 알아두면 좋은 취향. 예: 짧은 답변 선호, 존댓말 등)_

## 메모

_(시간이 지나며 이 사용자에 대해 알게 된 것들. 어시스턴트가 직접 채우거나 사용자가
손으로 적습니다.)_
"""

# Seeded as a blank placeholder so household members have a file ready
# to fill in. Empty body → slot omitted from the system prompt, so
# leaving the placeholder unchanged costs zero tokens.
_DEFAULT_USER_BOOTSTRAP = """\
# BOOTSTRAP.md — 이 사용자에게 적용할 어시스턴트 행동 지침

_(이 파일은 비어 있어도 됩니다. 채워두면 매 턴 시스템 프롬프트에 들어가서_
_어시스턴트가 이 사용자와 대화할 때만 적용할 지침이 됩니다. 전역 BOOTSTRAP은_
_`/config/BOOTSTRAP.md` 에 있고, 그 후에 이 파일이 적용됩니다.)_

_예시:_
_- "이 사용자는 어린이입니다. 짧고 쉬운 말로 답하세요."_
_- "이 사용자에게는 22시 이후 큰 소리 미디어를 재생하기 전에 확인하세요."_
_- "이 사용자는 영어로 답하는 것을 선호합니다."_
"""

_INDEX_LINE_RE = re.compile(
    r"^- (?P<slug>(?:[a-z0-9]|[a-z0-9][a-z0-9-]{0,62}[a-z0-9])): (?P<desc>.*)$"
)


def _strip_bootstrap_placeholder(body: str) -> str:
    """Return the substantive portion of a per-user BOOTSTRAP body.

    Drops markdown headings (`#`-prefixed), italic-only commentary
    lines (`_..._`), and blank lines — leaving only real instructions
    the user added. When the input is the seeded placeholder verbatim,
    the result is empty, and `render_user_bootstrap` skips the slot.
    Strictly heuristic — false positives just mean we render a slot
    that was actually placeholder, which is harmless (just tokens).
    """
    kept: list[str] = []
    for raw in body.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("_") and stripped.endswith("_"):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


class MemoryError(Exception):
    """Raised when a memory operation is rejected (bad slug, oversized
    body, path-traversal attempt, OS error). Dispatch layer converts
    this into `{"ok": False, "error": ...}` for the LLM.
    """


class MemoryBucketFullError(MemoryError):
    """Subclass raised specifically when `save` is rejected because the
    bucket-total cap would be exceeded. The dispatch layer catches this
    and attaches a `status` payload (entry list + sizes) to the tool
    result so the LLM can pick what to delete without a round trip.
    """


@dataclass
class MemoryStore:
    """Filesystem-backed per-user memory. One instance per addon process.

    Methods are sync because the data sizes are tiny (KB) and the I/O
    sits inside the same event loop's tool-dispatch turn — running them
    sync avoids spawning a thread pool for every save.
    """

    root: Path

    # ---- public API -------------------------------------------------------

    def list(self, user_id: str | None) -> list[tuple[str, str]]:
        """Return [(slug, description), …] sorted by slug. Empty if
        the index is missing or unreadable.
        """
        entries = self._read_index(self._bucket_dir(user_id, create=False))
        return sorted(entries.items())

    def read(self, user_id: str | None, slug: str) -> str | None:
        """Return the body text for `slug`, or None if it doesn't exist."""
        self._validate_slug(slug)
        bucket = self._bucket_dir(user_id, create=False)
        body_path = self._resolve_inside(bucket, f"{slug}{_BODY_SUFFIX}")
        try:
            return body_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise MemoryError(f"read failed: {exc}") from exc

    def save(
        self,
        user_id: str | None,
        slug: str,
        description: str,
        body: str,
    ) -> None:
        """Write body + update index. Atomic per-file (tmp → rename).
        Overwrites any existing entry with the same slug.
        """
        self._validate_slug(slug)
        if not isinstance(description, str) or not description.strip():
            raise MemoryError("description must be a non-empty string")
        if len(description) > MAX_DESCRIPTION_CHARS:
            raise MemoryError(
                f"description must be ≤{MAX_DESCRIPTION_CHARS} chars",
            )
        if "\n" in description or "\r" in description:
            raise MemoryError("description must be a single line")
        if not isinstance(body, str):
            raise MemoryError("body must be a string")
        body_bytes = body.encode("utf-8")
        if len(body_bytes) > MAX_MEMORY_BYTES:
            raise MemoryError(
                f"body exceeds {MAX_MEMORY_BYTES}-byte per-entry limit "
                f"(got {len(body_bytes)}). Consolidate this memory — "
                f"keep only the essentials, or split it across two "
                f"focused slugs.",
            )

        bucket = self._bucket_dir(user_id, create=True)
        # Bucket-total safety: reject if adding this entry would push
        # the user's total saved bytes past MAX_BUCKET_MEMORY_BYTES.
        # Matches the Hermes "memory at X/Y chars" pattern — forces the
        # model to delete or consolidate before adding noise.
        existing_total = self._bucket_total_bytes(bucket, exclude_slug=slug)
        projected_total = existing_total + len(body_bytes)
        if projected_total > MAX_BUCKET_MEMORY_BYTES:
            raise MemoryBucketFullError(
                f"Memory bucket at "
                f"{existing_total:,}/{MAX_BUCKET_MEMORY_BYTES:,} bytes. "
                f"Adding this entry ({len(body_bytes)} bytes) would push "
                f"it to {projected_total:,}. Current entries (largest "
                f"first) are in the `status` field of this result — call "
                f"`memory_delete` on what's stale or `memory_save` over an "
                f"existing slug to consolidate first.",
            )

        body_path = self._resolve_inside(bucket, f"{slug}{_BODY_SUFFIX}")
        self._atomic_write(body_path, body)

        entries = self._read_index(bucket)
        entries[slug] = description.strip()
        self._write_index(bucket, entries)
        _LOGGER.debug(
            "memory_save ok user=%s slug=%s %d bytes (bucket %d/%d)",
            self._bucket_label(user_id), slug, len(body_bytes),
            projected_total, MAX_BUCKET_MEMORY_BYTES,
        )

    def delete(self, user_id: str | None, slug: str) -> bool:
        """Remove body file + index entry. Returns True if anything was
        actually removed (either the file or the index entry).
        """
        self._validate_slug(slug)
        bucket = self._bucket_dir(user_id, create=False)
        if not bucket.is_dir():
            return False
        removed_file = False
        body_path = self._resolve_inside(bucket, f"{slug}{_BODY_SUFFIX}")
        try:
            body_path.unlink()
            removed_file = True
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise MemoryError(f"delete failed: {exc}") from exc

        entries = self._read_index(bucket)
        removed_entry = entries.pop(slug, None) is not None
        if removed_entry:
            self._write_index(bucket, entries)
        if removed_file or removed_entry:
            _LOGGER.debug(
                "memory_delete ok user=%s slug=%s",
                self._bucket_label(user_id), slug,
            )
        return removed_file or removed_entry

    def status(self, user_id: str | None) -> dict[str, Any]:
        """Return current usage of the user's (or shared) memory bucket
        so the LLM can decide whether to consolidate before adding more.

        Shape:
            {
              "bucket": "shared" | "users/<id>",
              "entry_count": int,
              "total_bytes": int,
              "per_entry_limit_bytes": MAX_MEMORY_BYTES,
              "bucket_limit_bytes": MAX_BUCKET_MEMORY_BYTES,
              "usage_pct": int (0–100, clamped),
              "entries": [{"slug": str, "bytes": int}, ...]  # sorted desc
            }

        Empty bucket → entry_count=0, total_bytes=0, entries=[]. Safe to
        call before any memory has been saved.
        """
        bucket = self._bucket_dir(user_id, create=False)
        entries: list[dict[str, Any]] = []
        total = 0
        if bucket.is_dir():
            for body_path in sorted(bucket.glob(f"*{_BODY_SUFFIX}")):
                if body_path.name == _INDEX_FILE_NAME:
                    continue
                if body_path.name in {_USER_PROFILE_FILE, _USER_BOOTSTRAP_FILE}:
                    continue
                try:
                    size = body_path.stat().st_size
                except OSError:
                    continue
                slug = body_path.stem
                entries.append({"slug": slug, "bytes": size})
                total += size
        entries.sort(key=lambda e: e["bytes"], reverse=True)
        usage_pct = min(100, int(total * 100 / MAX_BUCKET_MEMORY_BYTES)) \
            if MAX_BUCKET_MEMORY_BYTES else 0
        return {
            "bucket": self._bucket_label(user_id),
            "entry_count": len(entries),
            "total_bytes": total,
            "per_entry_limit_bytes": MAX_MEMORY_BYTES,
            "bucket_limit_bytes": MAX_BUCKET_MEMORY_BYTES,
            "usage_pct": usage_pct,
            "entries": entries,
        }

    def _bucket_total_bytes(
        self, bucket: Path, *, exclude_slug: str | None = None,
    ) -> int:
        """Sum bytes of all `<slug>.md` bodies in `bucket`, optionally
        excluding one slug (so re-saving an existing slug doesn't double-
        count its old + new size during the projected-total check in
        `save`). Skips USER.md / BOOTSTRAP.md / MEMORY.md.
        """
        if not bucket.is_dir():
            return 0
        total = 0
        excluded = (
            f"{exclude_slug}{_BODY_SUFFIX}" if exclude_slug else None
        )
        for body_path in bucket.glob(f"*{_BODY_SUFFIX}"):
            if body_path.name == _INDEX_FILE_NAME:
                continue
            if body_path.name in {_USER_PROFILE_FILE, _USER_BOOTSTRAP_FILE}:
                continue
            if excluded and body_path.name == excluded:
                continue
            try:
                total += body_path.stat().st_size
            except OSError:
                continue
        return total

    def render_index(self, user_id: str | None) -> str:
        """System-prompt block for one bucket (legacy / non-workspace).

        Picks user or shared based on `user_id`; the workspace mode in
        R3 calls `render_shared_index` + `render_user_index` separately
        instead, so both buckets appear simultaneously.
        """
        entries = self._read_index(self._bucket_dir(user_id, create=False))
        if not entries:
            return ""
        bucket_kind = (
            "this user"
            if self._safe_user_segment(user_id) is not None
            else "everyone (shared — voice satellite did not deliver a user id)"
        )
        header = (
            f"You have persistent memory for {bucket_kind}. Active entries — "
            f"call memory_read(slug) to load the body, memory_save(slug, "
            f"description, body) to add/update, memory_delete(slug) to remove:"
        )
        return self._format_block(header, entries)

    def render_shared_index(self) -> str:
        """Household-wide bucket. Always rendered (regardless of
        whether HA delivered a user_id). Empty bucket → ''.
        """
        entries = self._read_index(
            self._bucket_dir(_SHARED_BUCKET, create=False),
        )
        if not entries:
            return ""
        header = (
            "Household-wide memory (visible to every user). "
            "Call memory_read(slug) to load a body. memory_save / "
            "memory_delete here would affect everyone — only use for "
            "shared facts the user explicitly says are not private:"
        )
        return self._format_block(header, entries)

    def render_user_index(self, user_id: str | None) -> str:
        """Per-user bucket. Returns '' when `user_id` is unsafe / missing
        (caller should rely on the shared block only in that case).
        """
        if self._safe_user_segment(user_id) is None:
            return ""
        entries = self._read_index(self._bucket_dir(user_id, create=False))
        if not entries:
            return ""
        header = (
            "Memory for this user (private). Call memory_read(slug) to "
            "load a body, memory_save(slug, description, body) to "
            "add/update, memory_delete(slug) to forget:"
        )
        return self._format_block(header, entries)

    @staticmethod
    def _format_block(header: str, entries: dict[str, str]) -> str:
        lines = [header]
        for slug in sorted(entries):
            lines.append(f"- {slug}: {entries[slug]}")
        return "\n".join(lines)

    # ---- per-user USER.md profile ----------------------------------------

    def ensure_user_profile_seeded(self, user_id: str | None) -> bool:
        """Idempotent seed of the per-user USER.md template.

        Called once per turn from the agent when `user_id` is a safe
        segment. Creates the bucket dir if missing and writes the
        starter template only if the file does not already exist.
        Returns True iff a file was actually written. Unsafe / shared
        user_id is a no-op (the shared bucket has no profile).
        """
        if self._safe_user_segment(user_id) is None:
            return False
        bucket = self._bucket_dir(user_id, create=True)
        path = bucket / _USER_PROFILE_FILE
        if path.exists():
            return False
        try:
            self._atomic_write(path, _DEFAULT_USER_PROFILE)
        except MemoryError as exc:
            _LOGGER.warning(
                "USER.md seed failed for %s: %s",
                self._bucket_label(user_id), exc,
            )
            return False
        _LOGGER.info(
            "Seeded USER.md template for user %s",
            self._bucket_label(user_id),
        )
        return True

    def read_user_profile(self, user_id: str | None) -> str | None:
        """Return the per-user USER.md body, or None if absent / unsafe."""
        if self._safe_user_segment(user_id) is None:
            return None
        bucket = self._bucket_dir(user_id, create=False)
        path = bucket / _USER_PROFILE_FILE
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            _LOGGER.warning("USER.md %s unreadable (%s)", path, exc)
            return None
        if len(text.encode("utf-8")) > MAX_USER_PROFILE_BYTES:
            _LOGGER.warning(
                "USER.md %s exceeds %d bytes; treating as empty",
                path, MAX_USER_PROFILE_BYTES,
            )
            return None
        return text

    def render_user_profile(self, user_id: str | None) -> str:
        """System-prompt block for this user's profile. Empty when the
        file is absent or the user_id is unsafe — caller skips the
        section entirely so brand-new users don't bloat the prompt.
        """
        body = self.read_user_profile(user_id)
        if not body or not body.strip():
            return ""
        header = (
            "Profile for this user (household member). Treat as ground "
            "truth about who you are talking to:"
        )
        return f"{header}\n{body.strip()}"

    # ---- per-user BOOTSTRAP.md (onboarding/behavior nudges) -------------

    def ensure_user_bootstrap_seeded(self, user_id: str | None) -> bool:
        """Idempotent seed of the per-user BOOTSTRAP.md placeholder.

        Mirrors `ensure_user_profile_seeded`: seeds only on first
        encounter of a safe `user_id`, never overwrites. The seeded
        body is blank-with-comments so `render_user_bootstrap` skips
        the slot until the user adds real instructions.
        """
        if self._safe_user_segment(user_id) is None:
            return False
        bucket = self._bucket_dir(user_id, create=True)
        path = bucket / _USER_BOOTSTRAP_FILE
        if path.exists():
            return False
        try:
            self._atomic_write(path, _DEFAULT_USER_BOOTSTRAP)
        except MemoryError as exc:
            _LOGGER.warning(
                "user BOOTSTRAP.md seed failed for %s: %s",
                self._bucket_label(user_id), exc,
            )
            return False
        _LOGGER.info(
            "Seeded BOOTSTRAP.md placeholder for user %s",
            self._bucket_label(user_id),
        )
        return True

    def read_user_bootstrap(self, user_id: str | None) -> str | None:
        """Return the per-user BOOTSTRAP.md body, or None if absent /
        unsafe / oversize. Stripped of HTML/markdown comments? No —
        kept verbatim; the LLM is the consumer, not a renderer.
        """
        if self._safe_user_segment(user_id) is None:
            return None
        bucket = self._bucket_dir(user_id, create=False)
        path = bucket / _USER_BOOTSTRAP_FILE
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            _LOGGER.warning(
                "user BOOTSTRAP.md %s unreadable (%s)", path, exc,
            )
            return None
        if len(text.encode("utf-8")) > MAX_USER_BOOTSTRAP_BYTES:
            _LOGGER.warning(
                "user BOOTSTRAP.md %s exceeds %d bytes; treating as empty",
                path, MAX_USER_BOOTSTRAP_BYTES,
            )
            return None
        return text

    def render_user_bootstrap(self, user_id: str | None) -> str:
        """System-prompt block for this user's BOOTSTRAP body.

        Returns "" when the file is absent, the user_id is unsafe, or
        the body is empty / only the seeded placeholder commentary —
        so newly seeded users don't bloat the prompt until the
        household member actually fills the file in. Detection of
        "still placeholder" is conservative: we strip leading `_`,
        whitespace, and `#`-prefixed headings, and skip if nothing
        substantive remains.
        """
        body = self.read_user_bootstrap(user_id)
        if not body:
            return ""
        substantive = _strip_bootstrap_placeholder(body)
        if not substantive:
            return ""
        header = (
            "Per-user assistant instructions (applies only while talking "
            "to this user; supplements the global BOOTSTRAP):"
        )
        return f"{header}\n{substantive}"

    # ---- per-user daily journal -----------------------------------------

    def journal_append(
        self,
        user_id: str | None,
        text: str,
        *,
        now: datetime | None = None,
    ) -> tuple[str, int]:
        """Append a timestamped paragraph to today's journal file.

        Returns `(date, bytes_after)`. Raises `MemoryError` for unsafe
        user_id, oversize entry, or when adding the entry would push
        the day file past `MAX_JOURNAL_DAY_BYTES`.
        """
        if self._safe_user_segment(user_id) is None:
            raise MemoryError(
                "journal requires a safe user_id (no shared journal)",
            )
        if not isinstance(text, str) or not text.strip():
            raise MemoryError("journal entry must be a non-empty string")
        body = text.strip()
        body_bytes = body.encode("utf-8")
        if len(body_bytes) > MAX_JOURNAL_ENTRY_BYTES:
            raise MemoryError(
                f"entry exceeds {MAX_JOURNAL_ENTRY_BYTES} bytes "
                f"(got {len(body_bytes)})",
            )

        if now is None:
            now = datetime.now()
        date = now.strftime("%Y-%m-%d")
        time = now.strftime("%H:%M")

        path = self._journal_path(user_id, date, create=True)
        existing = ""
        try:
            existing = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise MemoryError(f"journal read failed: {exc}") from exc

        # `## HH:MM\n<body>\n\n` — markdown-friendly + parseable later.
        appended = f"## {time}\n{body}\n\n"
        new_content = existing + appended
        if len(new_content.encode("utf-8")) > MAX_JOURNAL_DAY_BYTES:
            raise MemoryError(
                f"day file would exceed {MAX_JOURNAL_DAY_BYTES} bytes; "
                f"clean up older entries in {path}",
            )
        self._atomic_write(path, new_content)
        _LOGGER.debug(
            "journal_append user=%s date=%s +%d bytes (total=%d)",
            self._bucket_label(user_id), date,
            len(appended.encode("utf-8")),
            len(new_content.encode("utf-8")),
        )
        return date, len(new_content.encode("utf-8"))

    def read_journal_day(
        self, user_id: str | None, date: str | None = None,
        *, now: datetime | None = None,
    ) -> tuple[str, str | None]:
        """Return `(resolved_date, body | None)`. `body` is None when
        the file does not exist for that date. Unsafe user_id → raises.
        """
        if self._safe_user_segment(user_id) is None:
            raise MemoryError(
                "journal requires a safe user_id (no shared journal)",
            )
        if date is None:
            if now is None:
                now = datetime.now()
            date = now.strftime("%Y-%m-%d")
        if not _JOURNAL_DATE_RE.match(date):
            raise MemoryError(
                f"date must be YYYY-MM-DD; got {date!r}",
            )
        path = self._journal_path(user_id, date, create=False)
        try:
            return date, path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return date, None
        except OSError as exc:
            raise MemoryError(f"journal read failed: {exc}") from exc

    # ---- internals --------------------------------------------------------

    def _journal_path(
        self, user_id: str | None, date: str, *, create: bool,
    ) -> Path:
        if not _JOURNAL_DATE_RE.match(date):
            raise MemoryError(f"invalid journal date {date!r}")
        bucket = self._bucket_dir(user_id, create=create)
        journal_dir = bucket / _JOURNAL_DIR_NAME
        if create:
            try:
                journal_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise MemoryError(
                    f"journal mkdir failed: {exc}",
                ) from exc
        candidate = journal_dir / f"{date}{_BODY_SUFFIX}"
        # Defense in depth (same pattern as _resolve_inside).
        journal_real = journal_dir.resolve()
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        try:
            resolved.relative_to(journal_real)
        except ValueError as exc:
            raise MemoryError(
                f"path escape attempt: {candidate} -> {resolved}",
            ) from exc
        return candidate

    def _bucket_dir(self, user_id: str | None, *, create: bool) -> Path:
        seg = self._safe_user_segment(user_id)
        if seg is None:
            bucket = self.root / _SHARED_BUCKET
        else:
            bucket = self.root / "users" / seg
        if create:
            try:
                bucket.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise MemoryError(f"bucket mkdir failed: {exc}") from exc
        return bucket

    @staticmethod
    def _safe_user_segment(user_id: str | None) -> str | None:
        """Return a path-safe segment for `user_id`, or None to use shared."""
        if not isinstance(user_id, str):
            return None
        if user_id == _SHARED_BUCKET:
            return None
        if not _USER_ID_RE.match(user_id):
            return None
        return user_id

    @staticmethod
    def _bucket_label(user_id: str | None) -> str:
        seg = MemoryStore._safe_user_segment(user_id)
        return seg if seg is not None else _SHARED_BUCKET

    @staticmethod
    def _validate_slug(slug: str) -> None:
        if not isinstance(slug, str) or not _SLUG_RE.match(slug):
            raise MemoryError(
                f"invalid slug {slug!r}: must match "
                f"[a-z0-9][a-z0-9-]*[a-z0-9], 1-64 chars",
            )

    @staticmethod
    def _resolve_inside(bucket: Path, name: str) -> Path:
        """Final path must live inside `bucket` after resolution. Slug
        regex already forbids `/` and `..`, but resolve+relative_to is
        defense in depth in case the regex changes. Always resolves
        both sides so symlinks in ancestors (e.g. macOS `/var` →
        `/private/var`) don't cause false escape alarms.
        """
        candidate = (bucket / name)
        bucket_real = bucket.resolve()
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        try:
            resolved.relative_to(bucket_real)
        except ValueError as exc:
            raise MemoryError(
                f"path escape attempt: {candidate} -> {resolved}",
            ) from exc
        return candidate

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, path)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise MemoryError(f"write failed: {exc}") from exc

    def _read_index(self, bucket: Path) -> dict[str, str]:
        index_path = bucket / _INDEX_FILE_NAME
        try:
            text = index_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}
        except OSError as exc:
            _LOGGER.warning(
                "memory index %s unreadable (%s); treating as empty",
                index_path, exc,
            )
            return {}
        entries: dict[str, str] = {}
        for line in text.splitlines():
            m = _INDEX_LINE_RE.match(line)
            if m:
                entries[m.group("slug")] = m.group("desc").strip()
        return entries

    def _write_index(self, bucket: Path, entries: dict[str, str]) -> None:
        index_path = bucket / _INDEX_FILE_NAME
        if not entries:
            # Empty index → remove the file so the directory is clean.
            try:
                index_path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                raise MemoryError(f"index unlink failed: {exc}") from exc
            return
        lines = [f"- {slug}: {entries[slug]}" for slug in sorted(entries)]
        self._atomic_write(index_path, "\n".join(lines) + "\n")
