---
name: app-terminology
description: "In the ha-apps repo, prefer the term \"app\" over \"add-on\"/\"addon\" in prose and naming"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 734b84d4-cba6-457e-a10d-37bf29e45dc8
---

In the `ha-apps` monorepo the user prefers **"app"** over "add-on"/"addon" in
prose, doc headings, and skill/file naming (e.g. skills `app-preflight`,
`new-app-scaffold`; "Home Assistant app monorepo").

**Why:** the repo is named `ha-apps` and the user's own docs already say "HA app
packaging"; they asked to standardize on "app".

**How to apply:** use "app" when referring to the subprojects/the HA-app concept
in anything we write. KEEP literal identifiers that contain "addon" unchanged —
they are fixed strings, not prose: the `addon:<slug>` GitHub labels
(`labels.yml`/`labeler.yml`), the `frenck/action-addon-linter` action, HA base
image names, and any HA-defined config keys. Don't rename `repository.yaml` or
HA store concepts. Related: [[nemo-asr-cpp-addon]] and the repo SoT lives in
`.github/copilot-instructions.md`.
