---
name: release-please-squash-gotcha
description: ha-apps — squash-merging a multi-scope PR breaks release-please; use rebase-merge or a conventional PR title
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 8683c7a5-4b03-47bb-8f3e-87ef1fda371e
---

In ha-apps, **squash-merging a PR that bundles several `type(scope):` commits
silently breaks release-please.** GitHub's squash replaces all commit headers
with the PR *title* as the single subject; release-please parses only the
commit header for `type(scope):`, so a non-conventional PR title (e.g.
"Public-repo deployment: …") makes it skip every package — no release PRs.

**Why:** release-please (release-type `simple`, manifest monorepo) needs both
(a) files changed under the package's path AND (b) a conventional *type* in the
header to bump. Squash keeps the paths but loses the headers (they survive only
as body bullets, which it ignores).

**How to apply:** for any multi-app PR, merge with **Rebase and merge** so each
scoped commit lands individually on main. If you must squash, make the **PR
title** a valid Conventional Commit. Recovery when it already happened: revert
the squash commit, then cherry-pick the original conventional commits back onto
main (net-zero tree change) and push — release-please then re-parses them.

See [[deployment-facts]].
