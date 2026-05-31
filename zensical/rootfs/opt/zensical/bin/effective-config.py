#!/usr/bin/env python3
"""Render an "effective" Zensical config for the add-on runtime.

The user can hand us a `zensical.toml` whose `docs_dir` / `site_dir` are
relative paths suitable for a GitHub Pages workflow (e.g. `docs_dir = "docs"`,
`site_dir = "_site"`). The add-on runtime, however, needs those paths to
point at the fixed locations:

    docs_dir → /var/lib/zensical/docs   (sync.sh mirrors /config here)
    site_dir → /var/lib/zensical/site   (nginx serves this)

Zensical 0.0.43 panics on absolute paths in `docs_dir`/`site_dir`
("invariant: Id(Format(Path(RootDir)))"); it requires relative paths
resolved against the config file's own directory (upstream issue #68).
So this script writes the effective TOML *into* /var/lib/zensical/ with
`docs_dir = "docs"` and `site_dir = "site"`, which resolve to the
intended absolute locations.

Everything else from the source — site_name, theme, palette,
markdown_extensions — passes through verbatim.

Usage:  effective-config.py SRC DST
"""
from __future__ import annotations

import sys
import tomllib

import tomli_w

DOCS_DIR = "docs"
SITE_DIR = "site"


def main(src: str, dst: str) -> None:
    with open(src, "rb") as f:
        data = tomllib.load(f)
    # Zensical accepts both flat configs and [project]-wrapped configs;
    # normalise to wrapped so our overrides land in the right place.
    if "project" not in data:
        data = {"project": data}
    data["project"]["docs_dir"] = DOCS_DIR
    data["project"]["site_dir"] = SITE_DIR
    with open(dst, "wb") as f:
        tomli_w.dump(data, f)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: effective-config.py SRC DST", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
