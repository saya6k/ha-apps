# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository. `CLAUDE.md` is a symlink to `AGENTS.md` — edit the
target, not the symlink.

## What this directory is

A Home Assistant **add-on repository monorepo** holding five add-ons in
sibling directories. A single `repository.yaml` at the root advertises
all five to HA's store. Per-add-on tooling (CI, release tagging, labels,
issue forms) lives at the **root** `.github/` — the per-subproject
`.github/` directories have been removed because GitHub Actions only
reads workflows from the repo root.

Each add-on still has its own version, Dockerfile, CHANGELOG, and deep
`AGENTS.md` — but they share one git history, one issue tracker, and
one release pipeline.

**When working on a task, `cd` into the relevant subproject and read that
project's `AGENTS.md` first — it carries the real invariants, build commands,
and "don'ts". The notes below are only for cross-cutting orientation.**

Subdirectory names use the bare add-on slug (`llm-conversation-agent`, not
`ha-llm-conversation-agent`). The `ha-` prefix is still part of each
add-on's GitHub project name and brand — don't strip it from URLs,
package names, Wyoming Info strings, or CHANGELOG cross-references.

| Subproject | What it is |
|---|---|
| [`llm-conversation-agent/`](llm-conversation-agent/AGENTS.md) | Wyoming conversation agent backed by any OpenAI-compatible LLM; delegates entity exposure to HA's `mcp_server`. Python + s6. Has a skill sandbox (bubblewrap + seccomp + rlimits + custom AppArmor). |
| [`rethink/`](rethink/AGENTS.md) | Packages [`anszom/rethink`](https://github.com/anszom/rethink) so LG ThinQ appliances talk to HA over MQTT instead of LG's cloud. Node upstream, packaged shell. |
| [`supertonic/`](supertonic/AGENTS.md) | Wyoming TTS service running [`supertonic-mnn`](https://github.com/vra/supertonic-mnn). Python bridge with auto-precision detection. |
| [`wardrowbe/`](wardrowbe/AGENTS.md) | Packages [`Anyesh/wardrowbe`](https://github.com/Anyesh/wardrowbe). Seven processes (Postgres, Redis, FastAPI, arq worker, Next.js, nginx, daily backup) in one s6-overlay v3 container. |
| [`zensical/`](zensical/AGENTS.md) | Renders `/config/docs/` as a [Zensical](https://zensical.org/) site served through the HA ingress side panel. Stateless renderer + inotify watcher. |

## Conventions shared across every subproject

These hold everywhere — if a subproject's `AGENTS.md` disagrees, the
subproject wins.

- **Each subproject's `AGENTS.md` is symlinked as `CLAUDE.md`.** Edit
  `AGENTS.md`; the symlink follows. Same convention at this top level.
- **Doc taxonomy is fixed:** `CHANGELOG.md` = *what* changed (HA renders it
  in the add-on UI), `AGENTS.md` = *current* shape (this file), `DOCS.md` =
  user-visible knobs (HA renders it as the Documentation tab), `README.md` =
  one-paragraph blurb, `notes/` = *why* / decision logs (gitignored in every
  subproject — never link to `notes/` from any shipped doc).
- **CI lives at the root only.** `.github/workflows/ci.yml` uses
  `dorny/paths-filter` to detect which add-on changed and fans out a
  matrix per add-on running the **official** Home Assistant add-on
  linter (`frenck/action-addon-linter@v2`) plus yamllint, hadolint, and
  shellcheck — same checks the `hassio-addons/workflows/app-ci.yaml`
  reusable workflow runs, but called directly so we can pass `path:
  ./<addon>` (the reusable wrapper doesn't accept a subdir input).
  Pattern follows `alexbelgium/hassio-addons`. Image build/publish to
  GHCR is currently out of band; that's a future task and will likely
  call `home-assistant/builder/actions/build-image` per (add-on × arch).
- **HA app packaging:** every subproject has `config.yaml` (+ `build.yaml`
  where needed) + `Dockerfile` + `rootfs/etc/s6-overlay/s6-rc.d/*` for
  service supervision + `translations/{en,ko}.yaml` for option UI strings.
  Adding a new s6 script means adding it to the `chmod +x` block in the
  `Dockerfile` — s6 silently ignores non-executable scripts.
- **`config.yaml` lives at the subproject root only.** The supervisor's repo
  scanner reads every `config.*` it finds; templates / examples must use a
  different filename (e.g. `example_config.yaml`).
- **Never `--no-verify` / `--no-gpg-sign` on git commits.** If a hook fails,
  fix the root cause.
- **Lint config is centralized.** `.hadolint.yaml`, `.markdownlint.yaml`,
  `.shellcheckrc` at the root are read by both CI and local runs. Don't
  duplicate ignore lists inside subprojects.
- **Line endings are LF everywhere** via `.gitattributes`. Shell scripts,
  s6 `run`/`finish`, and all text files MUST be LF — Windows-checked-out
  CRLF breaks bashio and s6 silently.
- **External-facing docs:** `CONTRIBUTING.md` carries the Conventional
  Commits rules for outside contributors; `SECURITY.md` carries the
  vuln-report channel and per-add-on attack surface; `CODE_OF_CONDUCT.md`
  is Contributor Covenant 2.1 boilerplate. Update `CONTRIBUTING.md` in
  lockstep with any change to the "Allowed types/scopes" tables here.

## Commit and release rules (enforced — release-please depends on this)

Releases are driven by [release-please](https://github.com/googleapis/release-please).
It parses each commit on `main` and groups changes into per-add-on
release PRs (one open PR per add-on under `chore(<addon>): release <ver>`).
Merging that PR tags `<addon>-v<ver>`, bumps `version:` in the add-on's
`config.yaml` (plus `pyproject.toml`/`version.txt` where applicable),
and writes a section into the add-on's `CHANGELOG.md`.

This only works if every commit follows **Conventional Commits with the
add-on slug as the scope**:

```
<type>(<scope>): <subject>

[optional body]

[optional footer — e.g. BREAKING CHANGE: <description>]
```

### Allowed types

| Type | Effect on release |
|---|---|
| `feat` | minor bump, "Features" section in CHANGELOG |
| `fix` | patch bump, "Bug Fixes" section |
| `perf` | patch bump, "Performance" section |
| `revert` | patch bump, "Reverts" section |
| `docs` / `refactor` / `build` / `ci` | patch bump, listed in CHANGELOG |
| `chore` / `test` / `style` | no release, hidden from CHANGELOG |
| `<type>!` or `BREAKING CHANGE:` footer | major bump |

### Allowed scopes

One of: `llm-conversation-agent`, `rethink`, `supertonic`, `wardrowbe`,
`zensical`, or `repo` (for `.github/`, root docs, `repository.yaml`).
Any other scope = release-please cannot route the commit to an add-on
and the change will not appear in any CHANGELOG.

If one commit truly spans multiple add-ons, **split it**. Cross-cutting
"repo" changes go under `repo`.

### Examples

```
feat(supertonic): add Korean voice F5
fix(llm-conversation-agent): retry half-closed MCP keepalive sockets
docs(zensical): document use_directory_urls=false constraint
ci(repo): bump dorny/paths-filter to v3
chore(supertonic)!: drop ORT/OpenVINO stack

BREAKING CHANGE: removes the `provider` option; users on 1.x must reconfigure.
```

### How a release ships

1. Land Conventional-Commit PRs on `main`.
2. The `Release` workflow runs and release-please opens (or updates) a
   `chore(<addon>): release <ver>` PR per affected add-on.
3. Review the PR — the diff is the auto-bumped `config.yaml` /
   `CHANGELOG.md` / `version.txt` (and `pyproject.toml` for
   `llm-conversation-agent` / `supertonic`).
4. Merge. release-please tags `<addon>-v<ver>` and creates a GitHub
   Release whose body is the new CHANGELOG section.
5. Image build/publish to GHCR is **not yet automated in monorepo
   mode** — run it manually until that workflow is added.

### Configuration files (do not rename)

- `.github/release-please-config.json` — package list, releaser type
  (`simple`), `extra-files` mappings for `config.yaml` / `pyproject.toml`.
- `.github/.release-please-manifest.json` — authoritative current
  version per add-on. release-please rewrites it on every release.
- `<addon>/version.txt` — seeded for the `simple` releaser. Don't
  delete; release-please bumps it alongside `config.yaml`.

### Label and PR automation

- `.github/labels.yml` is the source of truth; `Sync labels` workflow
  pushes it to GitHub on change. **Adding/renaming labels by hand on
  GitHub will be wiped on the next sync.**
- `.github/labeler.yml` auto-applies `addon:<slug>` labels by changed
  path on every PR.
- Issue forms (`.github/ISSUE_TEMPLATE/{bug,feature}.yml`) require
  selecting an add-on from a dropdown and pre-apply
  `type:fix|feat` + `needs:triage`.

## Working in this directory

- **No top-level commands.** `pyproject.toml` / `requirements.txt` /
  `Dockerfile` live in subprojects; run them from there.
- **Each subproject's `AGENTS.md` lists its own sanity-check incantation**
  (yamllint, shellcheck, `docker build .`, smoke tests, etc.). Run those
  before opening a PR against that subproject. The root CI workflow runs
  the cross-cutting linters; it does not replace per-add-on smoke tests.
- Only `supertonic/` currently has its own `.git` checkout here. The
  other four are working copies without local git state — treat that as
  ambient state, not something to "fix".
