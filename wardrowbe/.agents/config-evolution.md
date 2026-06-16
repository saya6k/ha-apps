# config.yaml evolution policy

Rule: `options:` / `schema:` keys are a contract with every existing
user's saved addon configuration. Renaming or removing a key forces them
to reconfigure on next update — silent and surprising.

## What to do

- **Additions are free.** New keys land additively at the bottom of
  `options:` and the matching schema row. Provide a sensible default so
  no one *has* to set the new key.
- **Renames need a transition.** Land the new key as a new option,
  read both old and new in `00-init.sh` (preferring new), warn in the
  log when the old key is set, and remove the old key one release later.
  CHANGELOG entry calls out the deprecation window.
- **Removals need the same transition.** Default the obsolete key to the
  inert value, ignore it, warn in the log, remove a release later.

## Why we care this much

The wardrowbe addon's options surface is non-trivial (DB credentials,
auth knobs, AI endpoints, backup schedule…). A user with a working
config does *not* want a routine update to silently invalidate it.
We've already preserved compatibility once during the 1.0.5 → 1.0.6
PGDATA move and again during 1.0.7 → 1.1.0 MCP additions; both were
zero-touch additive changes. The 1.3.x MCP *removal* is the first
breaking change — see CHANGELOG for the migration path.

## What this rules out

- Reshuffling option key names "for cleanliness".
- Dropping a key in the same release it's deprecated.
- Tightening schema validation (e.g., narrowing a `str?` to `str` with a
  required default) without a transition.

## Related files

- `config.yaml` — the contract.
- `rootfs/etc/cont-init.d/00-init.sh` — every option read here.
- `translations/{en,ko}.yaml` — UI labels for each key.
- `CHANGELOG.md` — flag every option change under a **Compatibility**
  heading in the release entry.
