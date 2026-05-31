#!/bin/sh
# Print the Zensical *source* config path the runtime should use.
#
# Resolution order:
#   1. /config/zensical.toml        — publish-ready config that travels
#                                     with your /config directory to
#                                     GitHub. Highest priority so the
#                                     add-on renders exactly what you
#                                     ship.
#   2. /addon_config/zensical.toml  — add-on-only override (good for
#                                     custom paths or settings you don't
#                                     want to publish).
#   3. /opt/zensical/zensical.toml  — bundled defaults.
#
# The resolved file is the *source*; effective-config.py rewrites it
# into /tmp/zensical-effective.toml with the container's hard-coded
# docs_dir / site_dir so sync.sh and nginx keep working regardless of
# what the source said.
if [ -f /config/zensical.toml ]; then
    echo /config/zensical.toml
elif [ -f /addon_config/zensical.toml ]; then
    echo /addon_config/zensical.toml
else
    echo /opt/zensical/zensical.toml
fi
