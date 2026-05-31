#!/usr/bin/env bash
# Mirror /config/docs/ into the Zensical working docs_dir.
# Called by init-zensical once at startup, then by zensical-watcher on every
# inotify event burst.
set -euo pipefail

SRC_DOCS=/config/docs
DEST=/var/lib/zensical/docs

mkdir -p "$DEST"

# Mirror /config/docs/* (and recursively) into DEST. --delete drops files
# the user removed; permissions don't matter on rendered output so -a is fine.
if [ -d "$SRC_DOCS" ]; then
    rsync -a --delete "$SRC_DOCS/" "$DEST/"
else
    # User deleted /config/docs entirely — wipe DEST so stale pages disappear.
    find "$DEST" -mindepth 1 -delete
fi

# If the user hasn't supplied a landing page, drop a placeholder so
# zensical doesn't fail on a missing index.
if [ ! -f "$DEST/index.md" ]; then
    printf '# Home Assistant Documentation\n\nCreate `/config/docs/index.md` to replace this page.\n' \
        > "$DEST/index.md"
fi
