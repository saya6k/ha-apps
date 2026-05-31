"""agentskills.io-format Skill loader.

A skill is a directory under `--skills-dir` (default `/config/skills/`)
containing a `SKILL.md` file with YAML frontmatter and a Markdown body.
We follow the [agentskills.io specification](https://agentskills.io/specification)
verbatim — no vendor metadata namespace, no proprietary extensions.

Frontmatter fields (per spec):

| Field           | Required | Notes                                                     |
| --------------- | -------- | --------------------------------------------------------- |
| `name`          | Yes      | 1-64 chars, lowercase + digits + hyphens, no leading/    |
|                 |          | trailing hyphen, no `--`. Must match the parent dir name. |
| `description`   | Yes      | 1-1024 chars.                                             |
| `license`       | No       | Free-form short string / file ref.                        |
| `compatibility` | No       | Free-form, max 500 chars.                                 |
| `metadata`      | No       | Arbitrary key-value mapping (we don't read it ourselves). |
| `allowed-tools` | No       | Space-separated string → list[str] (PR4 will gate tools  |
|                 |          | by this when the skill is activated).                     |

This module only parses + validates. LLM exposure (PR3) and tool
gating (PR4) are separate. The `scripts/`, `assets/`, `references/`
directories from the spec are not read here — `scripts/` execution
lives in the future PR-sandbox with bubblewrap isolation; if those
dirs exist we leave them on disk untouched.

Bad SKILL.md files log WARNING and are skipped — the addon never
crashes on a malformed skill.

Security:
* Symlinks under the skills root are rejected by default (path
  traversal vector — a malicious skill could point SKILL.md at
  `/etc/passwd`). Bundled skills inside the addon image would never
  use them; user-managed skills should also be plain dirs.
* Each skill's resolved path is verified to live inside the
  configured skills root.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

_LOGGER = logging.getLogger(__name__)

SKILL_FILE_NAME = "SKILL.md"
MAX_SKILL_MD_BYTES = 256 * 1024  # spec recommends <5k tokens; 256KB is a generous safety cap

# Per agentskills.io spec: 1-64 chars, lowercase alphanumeric + hyphens,
# no leading/trailing hyphen, no consecutive `--`.
_NAME_RE = re.compile(r"^(?:[a-z0-9]|[a-z0-9][a-z0-9-]*[a-z0-9])$")
_DOUBLE_HYPHEN = re.compile(r"--")

_FRONTMATTER_OPEN = re.compile(r"^---\s*\r?\n", re.MULTILINE)
# Frontmatter close marker on its own line: `---` or `...` (YAML doc end).
_FRONTMATTER_CLOSE = re.compile(r"^(?:---|\.\.\.)\s*\r?\n", re.MULTILINE)


class SkillParseError(ValueError):
    """Raised when a SKILL.md fails to parse or violates the spec."""


@dataclass
class Skill:
    """One agentskills.io-format Skill, parsed from <dir>/SKILL.md."""

    name: str
    description: str
    body: str
    path: Path  # Directory containing SKILL.md.
    license: str | None = None
    compatibility: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    allowed_tools: list[str] = field(default_factory=list)


def parse_skill_md(text: str, *, expected_name: str | None = None) -> tuple[dict, str]:
    """Split frontmatter + body and validate against agentskills.io spec.

    Returns `(frontmatter_dict, body)`. Raises `SkillParseError` on any
    spec violation. The dict is normalised — `allowed-tools` already
    parsed into list[str], unset optional fields not present.
    """
    if not text.strip():
        raise SkillParseError("SKILL.md is empty")

    open_match = _FRONTMATTER_OPEN.match(text)
    if not open_match:
        raise SkillParseError("SKILL.md must start with YAML frontmatter ('---')")
    after_open = open_match.end()

    close_match = _FRONTMATTER_CLOSE.search(text, after_open)
    if not close_match:
        raise SkillParseError("YAML frontmatter not closed with '---'")
    frontmatter_text = text[after_open:close_match.start()]
    body = text[close_match.end():].strip()

    try:
        raw = yaml.safe_load(frontmatter_text) or {}
    except yaml.YAMLError as exc:
        raise SkillParseError(f"YAML frontmatter failed to parse: {exc}") from exc

    if not isinstance(raw, dict):
        raise SkillParseError(
            f"YAML frontmatter must be a mapping, got {type(raw).__name__}"
        )

    # name
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise SkillParseError("`name` is required and must be a non-empty string")
    if len(name) > 64:
        raise SkillParseError(f"`name` exceeds 64 chars: {name!r} ({len(name)})")
    if not _NAME_RE.match(name):
        raise SkillParseError(
            f"`name` must be lowercase alphanumeric + hyphens, no leading/"
            f"trailing hyphen: {name!r}"
        )
    if _DOUBLE_HYPHEN.search(name):
        raise SkillParseError(f"`name` must not contain consecutive hyphens: {name!r}")
    if expected_name is not None and name != expected_name:
        raise SkillParseError(
            f"`name` ({name!r}) does not match parent directory ({expected_name!r})"
        )

    # description
    description = raw.get("description")
    if not isinstance(description, str) or not description.strip():
        raise SkillParseError("`description` is required and must be a non-empty string")
    if len(description) > 1024:
        raise SkillParseError(
            f"`description` exceeds 1024 chars ({len(description)})"
        )

    # license — free-form, optional
    license_str = raw.get("license")
    if license_str is not None and not isinstance(license_str, str):
        raise SkillParseError("`license` must be a string when present")

    # compatibility — optional, max 500
    compatibility = raw.get("compatibility")
    if compatibility is not None:
        if not isinstance(compatibility, str):
            raise SkillParseError("`compatibility` must be a string when present")
        if len(compatibility) > 500:
            raise SkillParseError(
                f"`compatibility` exceeds 500 chars ({len(compatibility)})"
            )

    # metadata — arbitrary mapping
    metadata = raw.get("metadata") or {}
    if not isinstance(metadata, dict):
        raise SkillParseError("`metadata` must be a mapping when present")

    # allowed-tools — space-separated string per spec
    allowed_raw = raw.get("allowed-tools")
    if allowed_raw is None:
        allowed_tools: list[str] = []
    elif isinstance(allowed_raw, str):
        allowed_tools = allowed_raw.split()
    elif isinstance(allowed_raw, list):
        # OpenClaw uses lists; tolerate it for cross-vendor portability.
        if not all(isinstance(t, str) for t in allowed_raw):
            raise SkillParseError("`allowed-tools` list must contain only strings")
        allowed_tools = list(allowed_raw)
    else:
        raise SkillParseError(
            "`allowed-tools` must be a space-separated string or a list of strings"
        )

    normalised = {
        "name": name,
        "description": description.strip(),
        "license": license_str,
        "compatibility": compatibility,
        "metadata": metadata,
        "allowed_tools": allowed_tools,
    }
    return normalised, body


def _read_skill_md(skill_dir: Path) -> Skill:
    """Read + parse the SKILL.md inside `skill_dir`. Raises SkillParseError."""
    md_path = skill_dir / SKILL_FILE_NAME
    if md_path.is_symlink():
        raise SkillParseError(f"{SKILL_FILE_NAME} is a symlink (rejected)")
    if not md_path.is_file():
        raise SkillParseError(f"{SKILL_FILE_NAME} missing in {skill_dir}")
    size = md_path.stat().st_size
    if size > MAX_SKILL_MD_BYTES:
        raise SkillParseError(
            f"{SKILL_FILE_NAME} exceeds {MAX_SKILL_MD_BYTES} bytes ({size})"
        )

    text = md_path.read_text(encoding="utf-8")
    front, body = parse_skill_md(text, expected_name=skill_dir.name)
    return Skill(
        name=front["name"],
        description=front["description"],
        body=body,
        path=skill_dir,
        license=front["license"],
        compatibility=front["compatibility"],
        metadata=front["metadata"],
        allowed_tools=front["allowed_tools"],
    )


def load_skills_dir(root: str | Path) -> list[Skill]:
    """Scan `root` for skill subdirectories and return parsed Skills.

    Each immediate subdirectory of `root` whose name is a valid skill
    `name` is a candidate. Symlinked subdirectories are rejected by
    default (path-traversal defense). Bad SKILL.md files log WARNING
    and are skipped — never abort the addon over a malformed skill.

    Returns a list sorted by skill name for stable ordering across
    runs (helps the upstream prompt cache when the skill list shows
    up in system prompts).
    """
    root_path = Path(root).expanduser()
    if not root_path.is_dir():
        _LOGGER.info(
            "Skills directory %s does not exist or is not a directory; "
            "no skills loaded.",
            root_path,
        )
        return []

    try:
        root_real = root_path.resolve(strict=True)
    except OSError as exc:
        _LOGGER.warning("Skills directory %s could not be resolved: %s", root_path, exc)
        return []

    skills: list[Skill] = []
    for entry in sorted(root_path.iterdir()):
        if entry.is_symlink():
            _LOGGER.warning(
                "Skipping symlinked skill entry %s (symlinks rejected — "
                "path-traversal defense). Move the real folder under %s.",
                entry, root_path,
            )
            continue
        if not entry.is_dir():
            continue
        try:
            entry_real = entry.resolve(strict=True)
        except OSError as exc:
            _LOGGER.warning("Skipping %s — could not resolve: %s", entry, exc)
            continue
        # Defense in depth: even non-symlink dirs shouldn't resolve outside root.
        try:
            entry_real.relative_to(root_real)
        except ValueError:
            _LOGGER.warning(
                "Skipping %s — resolved path %s is outside skills root %s",
                entry, entry_real, root_real,
            )
            continue
        try:
            skill = _read_skill_md(entry)
        except SkillParseError as exc:
            _LOGGER.warning("Skipping skill %s: %s", entry.name, exc)
            continue
        skills.append(skill)

    skills.sort(key=lambda s: s.name)
    return skills
