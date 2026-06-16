# Contributing

This is a personal Home Assistant add-on monorepo. **Pull requests are
accepted only from repository collaborators.** If you are not a
collaborator, please don't open a PR — file an issue (bug report or
feature request) instead, and it will be triaged there. The rest of this
document is the workflow for collaborators.

Several independent add-ons live under sibling directories, sharing CI,
release automation, and labels at the root. Per-add-on engineering details
live in each subdirectory's `AGENTS.md`.

## Before you open a PR

1. **Pick the right add-on directory** and read its `AGENTS.md`. It carries
   the real invariants ("don't reintroduce X", "this constant is load-bearing
   because Y") — those are the most common review failures.
2. **One add-on per PR** when possible. Releases are scoped per add-on, and
   release-please routes commits by the scope in the title. A PR that touches
   two add-ons becomes two release PRs and is harder to revert.
3. **Run the per-add-on sanity checks** listed in that add-on's `AGENTS.md`
   (yamllint, shellcheck, `docker build .`, smoke test, etc.) **before**
   pushing. The root CI runs the cross-cutting lints, not the smoke tests.

## Commit and PR title format (enforced)

We use [Conventional Commits](https://www.conventionalcommits.org/) with the
add-on slug as the scope. **release-please reads this** — a wrong scope means
your change ends up in the wrong CHANGELOG or no CHANGELOG at all.

```
<type>(<scope>): <subject>
```

### Allowed types and their release effect

| Type | Release | CHANGELOG section |
|---|---|---|
| `feat` | minor bump | Features |
| `fix` | patch bump | Bug Fixes |
| `perf` | patch bump | Performance |
| `revert` | patch bump | Reverts |
| `docs` / `refactor` / `build` / `ci` | patch bump | Listed |
| `chore` / `test` / `style` | no release | Hidden |

Breaking changes: append `!` to the type (e.g. `feat(supertonic)!: …`) or
add a `BREAKING CHANGE:` footer. Either triggers a major bump.

### Allowed scopes

`livekit-wakeword` · `nemo-asr-cpp` · `nemotron-asr` · `supertonic` ·
`voiceprint` · `wardrowbe` · `zensical` · `repo` (for `.github/`,
root docs, `repository.yaml`).

Any other scope = release-please can't route the commit. If a change truly
spans add-ons, split the PR.

### Examples

```
feat(supertonic): add Korean voice F5
fix(nemotron-asr): handle empty transcript on short audio clips
docs(zensical): document use_directory_urls=false constraint
ci(repo): bump dorny/paths-filter to v3
chore(supertonic)!: drop ORT/OpenVINO stack

BREAKING CHANGE: removes the `provider` option; users on 1.x must reconfigure.
```

## Release flow (so you know what your PR triggers)

1. Your PR merges to `main` with a Conventional Commit title.
2. The `Release` workflow runs and release-please opens (or updates) a
   `chore(<addon>): release <ver>` PR per affected add-on.
3. A maintainer reviews the release PR — the diff is auto-bumped
   `config.yaml` / `CHANGELOG.md` (and `pyproject.toml`
   for `livekit-wakeword` / `nemo-asr-cpp` / `nemotron-asr` / `supertonic` /
   `voiceprint`).
4. Merging that PR tags `<addon>-v<ver>` and creates a GitHub Release.

Image build/publish to GHCR is currently manual — that's tracked as a
future task.

## Issues

Use the issue templates (Bug report / Feature request). Both require
selecting an add-on from the dropdown — that auto-applies the
`addon:<slug>` label and routes the issue. PRs are also auto-labelled by
changed paths.

## Licensing

The root `LICENSE` (MIT) covers the repo scaffolding. Some add-on
subdirectories carry their own licenses that override the root for that
directory's files — see `LICENSE` for the table. If your contribution
adds new third-party code or assets to a subdirectory, make sure the
license is compatible with that subdirectory's existing license.
