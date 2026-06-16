---
name: app-preflight
description: Runs an app's pre-PR sanity checks in this Home Assistant app monorepo — Python parse, yamllint, shellcheck, and (on request) docker build + a Wyoming `describe` smoke. Use before committing or opening a PR for any app under a subproject directory.
---

# App preflight checks

Run the checks an app must pass before a PR. Each subproject's `AGENTS.md` has a
**"Sanity checks before PR"** section — that is authoritative; this skill runs
the common baseline and defers to it for per-app extras.

## Steps
1. Decide which app(s) to check: the argument, else the subproject dirs with
   changes (`git status --porcelain | grep -oE '^.. [a-z-]+/' | sort -u`).
2. `cd` into the app and **read its `AGENTS.md` "Sanity checks before PR"** — run
   exactly those. The baseline every app shares:
   - **Python** (if it has a `wyoming_*`/package dir):
     `python3 -c "import ast,glob;[ast.parse(open(f).read()) for f in glob.glob('<pkg>/*.py')]"`
   - **YAML:** `yamllint config.yaml translations/*.yaml`
   - **Shell / s6:** `shellcheck -x rootfs/etc/s6-overlay/s6-rc.d/*/run` (and any `finish`)
   - **Schema drift** where the app mirrors a `list(...)` schema in a `const`
     (e.g. nemo's `SCHEMA_MODELS`): confirm they match.
3. Only when asked (slow): `docker build .` from the app dir.
4. Only when a service is running locally: Wyoming smoke —
   `echo '{"type":"describe"}' | nc -w 1 localhost <port> | grep -qi <slug>`
   (port + grep term are in the app's `AGENTS.md`).
5. Repo-wide invariants to spot-check: LF line endings (no CRLF), no
   `version.txt`, `config.yaml` only at the subproject root.

## IMPORTANT
- Report pass/fail per check with the actual output; do not claim a check passed
  if it was skipped (e.g. docker build, smoke).
- Do not "fix" unrelated findings here — just run and report. Fixes are a
  separate step.

## Output format
- One line per check: `OK` / `FAIL` (+ first error) / `SKIPPED` (+ why).
- End with an overall verdict: ready / not ready for PR.
