"""Fetch skills from URLs into /config/skills/ at addon startup.

Config option `skill_urls: list[str]` accepts:
- GitHub repo URLs (`https://github.com/user/repo`, optional `@ref` suffix)
- Direct archive URLs ending in `.tar.gz` / `.tgz` / `.zip` / `.tar`

Each URL is resolved to (archive_url, identifier). The identifier is
either the GitHub commit SHA, the archive's ETag / Last-Modified header,
or `sha256(content)` as a last resort. We persist last-installed
identifiers in `/data/skill_install_state.json` and skip URLs whose
upstream hasn't changed — avoiding repeated downloads and protecting
user-side edits to skill folders that the upstream hasn't touched.

When upstream HAS changed, we extract the archive and copy every
SKILL.md-containing directory into `/config/skills/<frontmatter_name>/`
(overwriting). Path-traversal entries and symlinks pointing outside the
extraction root are rejected before extraction.

Failures (network, parse, etc.) for one URL never block others or the
addon — log WARNING and continue.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import shutil
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass, field
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from .mcp_client import MCPServerConfig, MCPSkillBundle, fetch_skill_bundles
from .skills import SkillParseError, parse_skill_md

_LOGGER = logging.getLogger(__name__)

_MAX_ARCHIVE_BYTES = 100 * 1024 * 1024  # 100 MiB hard cap per URL
_HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)

_GITHUB_RE = re.compile(
    r"^https://github\.com/([^/\s]+)/([^/\s@]+?)(?:\.git)?(?:@(\S+))?/?$"
)
_ARCHIVE_SUFFIXES = (".tar.gz", ".tgz", ".tar", ".zip")


@dataclass
class _State:
    by_url: dict[str, dict[str, Any]] = field(default_factory=dict)


def _load_state(path: Path) -> _State:
    if not path.exists():
        return _State()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _State(by_url=data.get("by_url", {}))
    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning(
            "Skill install state at %s unreadable (%s); starting fresh",
            path, exc,
        )
        return _State()


def _save_state(path: Path, state: _State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"by_url": state.by_url}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


async def fetch_skill_urls(
    urls: list[str],
    target_dir: Path,
    state_path: Path,
    *,
    verify_ssl: bool = True,
    client: httpx.AsyncClient | None = None,
) -> list[str]:
    """Fetch each URL, install skills under target_dir, persist state.

    Returns the list of slugs installed or refreshed this run (empty if
    nothing changed upstream). Pass `client` to inject a test double; in
    production we manage the AsyncClient lifecycle here.
    """
    if not urls:
        return []
    target_dir.mkdir(parents=True, exist_ok=True)
    state = _load_state(state_path)
    installed_now: list[str] = []
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(
            timeout=_HTTP_TIMEOUT, verify=verify_ssl, follow_redirects=True,
        )
    try:
        for url in urls:
            try:
                slugs = await _fetch_one(client, url, target_dir, state)
                installed_now.extend(slugs)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning(
                    "Skill URL %s failed (%s: %s); continuing",
                    url, type(exc).__name__, exc,
                )
    finally:
        if own_client:
            await client.aclose()
    _save_state(state_path, state)
    return installed_now


async def _fetch_one(
    client: httpx.AsyncClient, url: str, target_dir: Path, state: _State,
) -> list[str]:
    archive_url, current_id, source_label = await _resolve(client, url)
    prev = state.by_url.get(url, {})
    if current_id and prev.get("id") == current_id:
        _LOGGER.debug(
            "Skill URL %s unchanged (%s); skipping",
            url, str(current_id)[:16],
        )
        return []

    _LOGGER.info("Fetching skill URL %s (%s)", url, source_label)
    archive = await _download(client, archive_url)
    if not current_id:
        # No upstream identifier (direct archive URL without ETag) —
        # fall back to sha256 of the downloaded bytes.
        current_id = hashlib.sha256(archive).hexdigest()
        if prev.get("id") == current_id:
            _LOGGER.debug(
                "Skill URL %s contents identical to last install; skipping",
                url,
            )
            return []

    slugs = _extract_and_install(archive, url, target_dir)
    if not slugs:
        _LOGGER.warning(
            "Skill URL %s contained no installable SKILL.md; "
            "nothing copied to %s",
            url, target_dir,
        )
        return []
    state.by_url[url] = {
        "id": current_id,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "slugs": slugs,
    }
    _LOGGER.info(
        "Installed %d skill(s) from %s: %s",
        len(slugs), url, ", ".join(slugs),
    )
    return slugs


async def _resolve(
    client: httpx.AsyncClient, url: str,
) -> tuple[str, str | None, str]:
    """Return (archive_url, current_id_or_None, human_label).

    GitHub repo URL → API call returns latest commit SHA → cheap skip.
    Direct archive URL → HEAD for ETag / Last-Modified; if absent, defer
    to post-download sha256.
    """
    m = _GITHUB_RE.match(url)
    if m:
        owner, repo, ref = m.group(1), m.group(2), m.group(3)
        headers = {"Accept": "application/vnd.github+json"}
        if not ref:
            r = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers=headers,
            )
            r.raise_for_status()
            ref = r.json().get("default_branch") or "main"
        r = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/commits/{ref}",
            headers=headers,
        )
        r.raise_for_status()
        sha = r.json()["sha"]
        archive_url = f"https://github.com/{owner}/{repo}/archive/{sha}.tar.gz"
        return archive_url, sha, f"github @ {sha[:8]}"

    lower = url.lower().split("?", 1)[0].split("#", 1)[0]
    if not any(lower.endswith(suf) for suf in _ARCHIVE_SUFFIXES):
        raise ValueError(
            "Unsupported URL: must be a GitHub repo URL "
            "(https://github.com/user/repo[@ref]) or end in "
            f"{', '.join(_ARCHIVE_SUFFIXES)} — got {url!r}"
        )
    try:
        r = await client.head(url)
        if r.status_code < 400:
            etag = r.headers.get("etag") or r.headers.get("last-modified")
            if etag:
                return url, etag.strip('"'), f"etag {etag[:30]}"
    except Exception:  # noqa: BLE001 — fallback path is safe
        pass
    return url, None, "no etag (will hash contents)"


async def _download(client: httpx.AsyncClient, archive_url: str) -> bytes:
    r = await client.get(archive_url)
    r.raise_for_status()
    content = r.content
    if len(content) > _MAX_ARCHIVE_BYTES:
        raise ValueError(
            f"Archive at {archive_url} is {len(content):,} bytes; "
            f"max allowed is {_MAX_ARCHIVE_BYTES:,}"
        )
    return content


def _extract_and_install(
    archive: bytes, source_url: str, target_dir: Path,
) -> list[str]:
    with tempfile.TemporaryDirectory(prefix="skill-fetch-") as tmp:
        tmp_path = Path(tmp)
        if _looks_like_zip(archive):
            with zipfile.ZipFile(io.BytesIO(archive)) as zf:
                _safe_extract_zip(zf, tmp_path)
        else:
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:*") as tf:
                _safe_extract_tar(tf, tmp_path)
        return _install_skills_from_tree(tmp_path, source_url, target_dir)


def _looks_like_zip(archive: bytes) -> bool:
    return archive[:4] == b"PK\x03\x04"


def _safe_extract_tar(tf: tarfile.TarFile, root: Path) -> None:
    """Reject path-traversal entries and escaping symlinks before extracting."""
    root_resolved = root.resolve()
    for member in tf.getmembers():
        member_path = (root / member.name).resolve()
        if root_resolved not in member_path.parents and member_path != root_resolved:
            raise ValueError(
                f"Refusing to extract path-traversal entry: {member.name!r}"
            )
        if member.issym() or member.islnk():
            link_target = (member_path.parent / member.linkname).resolve()
            if root_resolved not in link_target.parents and link_target != root_resolved:
                raise ValueError(
                    f"Refusing to extract symlink {member.name!r} -> "
                    f"{member.linkname!r} (escapes archive root)"
                )
    tf.extractall(root)


def _safe_extract_zip(zf: zipfile.ZipFile, root: Path) -> None:
    root_resolved = root.resolve()
    for name in zf.namelist():
        member_path = (root / name).resolve()
        if root_resolved not in member_path.parents and member_path != root_resolved:
            raise ValueError(
                f"Refusing to extract path-traversal entry: {name!r}"
            )
    zf.extractall(root)


def collect_installed_uris(
    server_name: str, state_path: Path,
) -> list[str]:
    """Return SKILL.md URIs previously installed from `server_name`.

    Used by the MCP listener at startup to re-subscribe after a
    reconnect. State key format `mcp://<server>#<skill>` stores no URI
    directly, but the URI is recoverable as the listener tracks them
    when fetch_mcp_skills runs.
    """
    # We don't currently persist the original URI in state (only the
    # skill name + hash). The listener registers URIs in-process from
    # fetch_mcp_skills's return value instead. This helper is a stub
    # so callers signal intent; future state file extension can backfill.
    return []


async def fetch_mcp_skills(
    servers: list[MCPServerConfig],
    target_dir: Path,
    state_path: Path,
    *,
    on_install: Callable[[str, list[str]], None] | None = None,
) -> list[str]:
    """For each MCP server, install any SKILL.md it serves as resources.

    Convention (this addon's, not agentskills.io's): a server exposes a
    skill by registering one resource whose URI ends in `/SKILL.md`
    (text/markdown) plus zero or more sibling resources sharing the
    same URI prefix. We install each bundle under
    `target_dir/<frontmatter_name>/` with sibling paths preserved.

    State key format: `mcp://<server>#<skill-name>`. Stored alongside
    skill_urls entries in the same state file. Per-server / per-skill
    failures are logged WARNING and skipped — never block other servers
    or the addon.
    """
    if not servers:
        return []
    target_dir.mkdir(parents=True, exist_ok=True)
    state = _load_state(state_path)
    installed_now: list[str] = []
    for server in servers:
        try:
            bundles = await fetch_skill_bundles(server)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning(
                "MCP server %s: skill fetch failed (%s: %s); continuing",
                server.name, type(exc).__name__, exc,
            )
            continue
        per_server_uris: list[str] = []
        for bundle in bundles:
            per_server_uris.append(bundle.skill_md_uri)
            try:
                slug = _install_mcp_bundle(bundle, target_dir, state)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning(
                    "MCP server %s: skill at %s install failed (%s: %s); skipping",
                    server.name, bundle.skill_md_uri,
                    type(exc).__name__, exc,
                )
                continue
            if slug:
                installed_now.append(slug)
        if on_install is not None and per_server_uris:
            try:
                on_install(server.name, per_server_uris)
            except Exception:  # noqa: BLE001
                _LOGGER.exception(
                    "on_install callback failed for %s", server.name,
                )
    _save_state(state_path, state)
    return installed_now


def _install_mcp_bundle(
    bundle: MCPSkillBundle, target_dir: Path, state: _State,
) -> str | None:
    """Validate, hash-check, then write a single MCP-served skill.

    Returns the installed slug, or None if unchanged (skipped).
    """
    try:
        meta, _body = parse_skill_md(bundle.skill_md_text)
    except SkillParseError as exc:
        _LOGGER.warning(
            "MCP server %s: SKILL.md at %s failed to parse (%s); skipping",
            bundle.server_name, bundle.skill_md_uri, exc,
        )
        return None
    name = meta.get("name")
    if not name:
        return None

    h = hashlib.sha256()
    h.update(bundle.skill_md_text.encode("utf-8"))
    for rel in sorted(bundle.siblings):
        h.update(b"\x00")
        h.update(rel.encode("utf-8"))
        h.update(b"\x00")
        h.update(bundle.siblings[rel])
    current_id = h.hexdigest()

    state_key = f"mcp://{bundle.server_name}#{name}"
    prev = state.by_url.get(state_key, {})
    if prev.get("id") == current_id:
        _LOGGER.debug(
            "MCP skill %s on %s unchanged; skipping",
            name, bundle.server_name,
        )
        return None

    dest = target_dir / name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    (dest / "SKILL.md").write_text(bundle.skill_md_text, encoding="utf-8")
    for rel, content in bundle.siblings.items():
        rel_clean = rel.lstrip("/")
        out = dest / rel_clean
        try:
            out.relative_to(dest)
        except ValueError:
            _LOGGER.warning(
                "MCP server %s: rejecting sibling path %r (escapes skill dir)",
                bundle.server_name, rel,
            )
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(content)
    state.by_url[state_key] = {
        "id": current_id,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "slugs": [name],
    }
    _LOGGER.info(
        "Installed MCP-served skill %r from server %s (%d sibling file(s))",
        name, bundle.server_name, len(bundle.siblings),
    )
    return name


def _install_skills_from_tree(
    tree_root: Path, source_url: str, target_dir: Path,
) -> list[str]:
    """Find every SKILL.md in the extracted tree, copy each containing
    directory into target_dir/<frontmatter_name>/. Overwrites existing
    installs — caller has already determined the upstream changed.
    """
    installed: list[str] = []
    seen: set[str] = set()
    for skill_md in sorted(tree_root.rglob("SKILL.md")):
        if skill_md.is_symlink():
            _LOGGER.warning(
                "Skipping symlinked SKILL.md from %s: %s",
                source_url, skill_md.relative_to(tree_root),
            )
            continue
        try:
            meta, _body = parse_skill_md(skill_md.read_text(encoding="utf-8"))
        except SkillParseError as exc:
            _LOGGER.warning(
                "SKILL.md at %s (from %s) failed to parse (%s); skipping",
                skill_md.relative_to(tree_root), source_url, exc,
            )
            continue
        name = meta.get("name")
        if not name:
            continue
        if name in seen:
            _LOGGER.warning(
                "Duplicate skill name %r in %s; using first occurrence",
                name, source_url,
            )
            continue
        seen.add(name)
        dest = target_dir / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(skill_md.parent, dest, symlinks=False)
        installed.append(name)
    return installed
