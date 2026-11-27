# Changelog

## [0.10.0](https://github.com/saya6k/ha-app-code-interpreter/releases/tag/v0.10.0)

## What's Changed

## ⚠️ Breaking changes

* feat!: the MCP endpoint answers only Home Assistant (discovery token) (#20) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-code-interpreter/compare/v0.9.0...v0.10.0

## [0.9.0](https://github.com/saya6k/ha-app-code-interpreter/releases/tag/v0.9.0)

## What's Changed

## New Features

* feat: plugins — MCP servers Home Assistant reaches, per-server access (#19) @saya6k
* feat: ask for a skill with hassio.app_stdin; skills carry a uses manifest (#18) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-code-interpreter/compare/v0.8.0...v0.9.0

## [0.8.0](https://github.com/saya6k/ha-app-code-interpreter/releases/tag/v0.8.0)

## What's Changed

## New Features

* feat: GetLiveContext results carry the entities parsed (#17) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-code-interpreter/compare/v0.7.0...v0.8.0

## [0.7.0](https://github.com/saya6k/ha-app-code-interpreter/releases/tag/v0.7.0)

## What's Changed

## New Features

* feat: skills proposed from finished sessions by an AI Task, approved by an admin (#16) @saya6k

## Bug Fixes

* fix: one logo for light and dark themes; drop dark_logo.png (#15) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-code-interpreter/compare/v0.6.0...v0.7.0

## [0.6.0](https://github.com/saya6k/ha-app-code-interpreter/releases/tag/v0.6.0)

## What's Changed

## New Features

* feat: continue the latest session; one HA connection per run (#14) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-code-interpreter/compare/v0.5.0...v0.6.0

## [0.5.0](https://github.com/saya6k/ha-app-code-interpreter/releases/tag/v0.5.0)

## What's Changed

## ⚠️ Breaking changes

* feat!: one run_code tool for scripts; docs and identity for Code Mode (#12) @saya6k
* feat!: run_code runs JavaScript in a Node REPL (#8) @saya6k

## New Features

* feat: ha.admin.hab() for administrators, with Claude Code's dontAsk rules (#13) @saya6k
* feat: ha.* in REPL cells through Home Assistant's MCP Server (#11) @saya6k
* feat: share.list, share.import and share.export from REPL cells (#10) @saya6k
* feat: $, file, write, sleep and log globals in the REPL (#9) @saya6k

## Maintenance

* chore: run local docker through socktainer, not linux-test (#7) @saya6k
* chore: drop the experimental stage from the app config (#5) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-code-interpreter/compare/v0.4.0...v0.5.0

## [0.4.0](https://github.com/saya6k/ha-app-code-interpreter/releases/tag/v0.4.0)

## What's Changed

## New Features

* feat: add pypdf and pdfplumber; drop package test suites from the sandbox (#4) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-code-interpreter/compare/v0.3.0...v0.4.0

## [0.3.0](https://github.com/saya6k/ha-app-code-interpreter/releases/tag/v0.3.0)

## What's Changed

## New Features

* `network_allowlist: ["*"]` allows any public host on port 443 (`"*:port"` for others). IP literals and non-public addresses stay refused, so Home Assistant and the LAN remain unreachable. (#3)

## Bug Fixes

* fix: harden sandbox restarts, REPL errors and audit accuracy; allow "*" egress (#3) @saya6k
  * A REPL restart survives a cancelled call, and the session and its files are kept.
  * `run_command` reports fork/thread limits instead of killing the REPL.
  * `/share` import/export and audit hashing no longer block other sessions.
  * Audit log: violations are classified accurately, and failed upstream connects are no longer shown as allowed.
  * The startup self-check fails closed instead of stopping the app.

**Full Changelog**: https://github.com/saya6k/ha-app-code-interpreter/compare/v0.2.0...v0.3.0

## [0.2.0](https://github.com/saya6k/ha-app-code-interpreter/releases/tag/v0.2.0)

## What's Changed

## New Features

* feat: Ingress panel for live sessions and the audit log (#2) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-code-interpreter/compare/v0.1.0...v0.2.0

## [0.1.0](https://github.com/saya6k/ha-app-code-interpreter/releases/tag/v0.1.0)

## What's Changed

First stable release of **Code Interpreter**: stateful Python for Assist conversation agents over MCP. Each session runs in a bubblewrap sandbox inside the app, and the app runs with protection mode on.

## New Features

* feat: Code Interpreter app with bubblewrap sandboxes (#1) @saya6k

See [DOCS](https://github.com/saya6k/ha-app-code-interpreter/blob/main/code-interpreter/DOCS.md) for tools, limits, network access and the security model.

**Full Changelog**: https://github.com/saya6k/ha-app-code-interpreter/commits/v0.1.0

