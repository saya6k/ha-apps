# AGENTS.md

Guidance for AI coding agents working on this repository. Detailed history
lives in `CHANGELOG.md` — read it for the *why* behind older decisions.

## What this repo is

A single Home Assistant **add-on** that renders Markdown from
`/config/docs/` as a [Zensical](https://zensical.org/) site, served
through the HA ingress side panel. `/config/docs/index.md` is the
landing page; every other `.md` under `/config/docs/` becomes a page.

The whole repo *is* the add-on. License is MIT.

### Why Zensical, not mkdocs-material

The user explicitly chose Zensical on **2026-05-26** despite the alpha
status. Reasons that informed the call:

1. The PyPI ownership change on 2026-03-09 + the MkDocs 2.0 rewrite
   leave the mkdocs ecosystem unsuitable as a long-term base — its
   replacement has no plugin or theme migration path.
2. Material for MkDocs 9.7.x enters maintenance-only status in
   2026-11. Building on it would have been a six-month dead end.
3. Zensical reads its native `zensical.toml`, which the user can edit
   with the same mental model as `mkdocs.yml` (same keys —
   `site_name`, `theme.features`, `theme.palette`,
   `markdown_extensions.*`). The user-facing UX is preserved without
   inheriting the mkdocs.yml YAML quirks (anchors, `!!python/name:`
   tags, INHERIT).

Internal directories were renamed to `zensical` on the same day
(`/var/lib/zensical/`, `/opt/zensical/`, s6 services `init-zensical`
and `zensical-watcher`). The bundled config is `zensical.toml`. The
add-on was never shipped with `mkdocs.yml` support, so the codepath was
removed in the same migration — `resolve-config.sh` only knows about
`zensical.toml`.

## Git / repo tracking

Part of the `ha-apps` monorepo — one git repo at the root, no per-app
`.git` checkouts. Tracking is **stage-gated** by the root `.gitignore`:
only `stage: stable` add-ons are committed; experimental ones are
gitignored and stay local-only. Promote one by setting `stage: stable`
in `config.yaml`, deleting its line from the root `.gitignore`, then
`git add` it.

**This add-on:** tracked (`stage: stable` — promoted from experimental
2026-06-03).

## Layout

```
config.yaml / Dockerfile                     add-on packaging (base+labels in Dockerfile; build.yaml removed — deprecated)
requirements.txt                             zensical + pymdown stack pins
rootfs/etc/nginx/http.d/default.conf         nginx server block (ingress-only)
rootfs/etc/s6-overlay/s6-rc.d/               init-zensical + zensical-watcher + nginx
rootfs/opt/zensical/zensical.toml             bundled defaults (used when neither override exists)
rootfs/opt/zensical/bin/sync.sh               mirror /config/docs → /var/lib/zensical/docs
rootfs/opt/zensical/bin/resolve-config.sh     pick /config/zensical.toml > /addon_config/zensical.toml > bundled
rootfs/opt/zensical/bin/effective-config.py   rewrite docs_dir/site_dir to container paths
rootfs/opt/zensical/seed/                     files copied into /config/ on first run (incl. zensical.example.toml)
CHANGELOG.md / DOCS.md / README.md           user-facing docs (HA renders the first two)
```

## Map / mount layout

```yaml
map:
  - type: homeassistant_config   # HA's /config dir → /config in container
    read_only: false
    path: /config
  - type: addon_config           # add-on's own config dir → /addon_config
    read_only: false
    path: /addon_config
```

The default mount path for `addon_config` would be `/config`, which
collides with `homeassistant_config`. We override both explicitly. The
plain `config:` shortform is the legacy alias and is avoided.

References we deliberately learn from:

- [XavierBerger/mkdocs](https://github.com/XavierBerger/home-assistant-addons/tree/main/mkdocs)
  — Material-renderer packaging on the HA Alpine base, `use_directory_urls: false`
  for ingress-prefix-safe links, nginx allow-listed to the Supervisor proxy IP.
  (We use Zensical, not mkdocs-material, but the packaging pattern is the same.)
- [wendevlin/homedocs](https://github.com/wendevlin/homeassistant-addons/tree/main/homedocs)
  — file watcher → rebuild on change (chokidar there; `inotifywait` here).

Do not duplicate the s6 supervision / Dockerfile patterns of `ha-rethink`
or `ha-wardrowbe` blindly; copy only what fits a stateless renderer.

## Documentation layout

| File | Role | Length target |
| ---- | ---- | ------------- |
| `README.md`        | One-paragraph blurb. Keep tiny. | ~15 lines |
| `DOCS.md`          | User-facing layout + troubleshooting. HA renders it as the "Documentation" tab. | ≤ ~100 lines |
| `AGENTS.md`        | This file — agent/dev guidance for the *current* code. Symlinked as `CLAUDE.md`. | ~100 lines |
| `CHANGELOG.md`     | Per-version headline. HA renders this in the add-on UI. 5–15 lines per version. | — |
| `.agents/`           | Local dev decision logs / postmortems. **Gitignored** — never link from shipped docs. | free-form |

**CHANGELOG = what changed**, **AGENTS = current state**,
**DOCS = user-visible behaviour**, **`.agents/` = why**.

## How the services chain together

```
init-zensical (oneshot)
  ├─ seed /config/docs/ if missing
  ├─ /opt/zensical/bin/sync.sh   mirror to /var/lib/zensical/docs/
  └─ zensical build --clean      first site into /var/lib/zensical/site/
        │
        ├──► zensical-watcher (longrun)
        │      inotifywait /config/docs + /addon_config → debounce 1s → sync.sh + zensical build
        │
        └──► nginx (longrun)
               serves /var/lib/zensical/site/ on ingress_port 8099
```

`init-zensical` is the dependency of both longruns; nothing else has to
wait on the watcher (nginx serves whatever is in `site/`, even if the
last rebuild failed).

## Customisation via `/addon_config/`

The runtime renderer config is selected by `resolve-config.sh`:

```text
/config/zensical.toml        → use it (publish-ready, travels to GitHub).
/addon_config/zensical.toml  → use it (add-on-only override).
otherwise                    → /opt/zensical/zensical.toml (bundled).
```

`init-zensical` seeds `/config/zensical.example.toml` on the **first run
only**, tracked by a marker at `/data/.zensical-example-seeded`. After
that it's never recreated — so a user who doesn't want it can delete it
and it stays gone (it previously reappeared on every start). We never
seed `/config/zensical.toml` itself — the existence of that file is the
user's signal that they want to take ownership.

The watcher re-resolves on every rebuild, so creating, renaming, or
deleting an override file takes effect on the next event burst
without a service restart.

### The effective-config rewrite step

The resolved source config is **never passed to `zensical build`
directly**. Instead `effective-config.py` reads it, force-overrides
`project.docs_dir = "docs"` and `project.site_dir = "site"`, and
writes the result to `/var/lib/zensical/zensical.toml`. That file is
what we hand to Zensical, and the relative `docs`/`site` resolve
against its parent directory to `/var/lib/zensical/{docs,site}`.

Zensical 0.0.43 panics on **absolute** `docs_dir`/`site_dir` with
`invariant: Id(Format(Path(RootDir)))` (upstream issue #68). The
relative-paths-plus-co-located-config trick is the only way to point
Zensical at fixed container paths until that ships.

Why: the whole point of the `/config/zensical.toml` priority is to
let the same file work for both this add-on *and* a `zensical build`
outside the container (e.g. GitHub Pages). The user writes
`docs_dir = "docs"` and `site_dir = "_site"`; those resolve correctly
when building from the /config repo root. Inside the add-on, those
relative paths would point at the wrong places — so we overwrite
them. Everything else from the source (site_name, theme, palette,
markdown_extensions) passes through unmodified.

`effective-config.py` uses `tomllib` (stdlib, Python ≥3.11) to read
and `tomli_w` (pure-Python PyPI dep, ~30 KB) to write. The "wrap or
strip `[project]`" normalisation matches Zensical's own
`parse_zensical_config` behaviour.

## Index resolution

```text
/config/docs/index.md  exists  → use it as the landing page.
otherwise                      → sync.sh writes a placeholder explaining the layout.
```

Decided 2026-05-27: `/config/README.md` is no longer touched by the
add-on. The earlier "copy README → docs/index.md" fallback was
removed because README links like `[Hardware](./docs/hardware.md)`
make sense at the /config root (where README lives) but break the
moment the file is re-rooted inside docs_dir — rewriting links during
the copy is a path-substitution rabbit hole, and asking users to keep
two link-flavours in their README is worse. A single
`/config/docs/index.md` is the only source of truth now.

## Ingress / link generation

`use_directory_urls = false` in `zensical.toml` is **load-bearing**.
With it, Zensical generates `*.html` link targets that browsers
resolve relative to the current URL. HA's ingress proxy strips the `/api/hassio_ingress/<token>/`
prefix when forwarding, so the add-on always sees URLs at `/`, while the
browser keeps the prefix when following links. Switching to
`use_directory_urls: true` will break navigation under ingress — don't.

nginx is allow-listed to `172.30.32.2` (Supervisor ingress IP) **and**
`127.0.0.1`. The loopback entry is load-bearing: the Dockerfile
`HEALTHCHECK` runs `curl http://127.0.0.1:8099/index.html` from inside
the container, and without that allow line every probe 403s, the
container goes `unhealthy` after `retries × interval` (≈ 90s), and
Supervisor restarts it in a loop. The ingress port (8099) is not
exposed to the host network.

## Don'ts

- Don't add a `/livereload` WebSocket layer for true browser auto-refresh.
  `zensical serve` (like mkdocs serve) uses absolute-pathed WS URLs that
  don't survive HA's ingress prefix. Rebuild-on-save + manual refresh is
  the documented behaviour; users have ~1s feedback and that's good enough.
- Don't reintroduce a `README.md → docs/index.md` copy step. We
  removed it on 2026-05-27 because link paths (`./docs/...`) only
  resolve from the /config root, not from inside docs_dir, and
  rewriting them during the copy is a fragile substitution game. The
  landing page is `/config/docs/index.md`, full stop.
- Don't seed `/config/zensical.toml` (or `/addon_config/zensical.toml`)
  on first start — only the `.example.toml` neighbour in `/config/`.
  The presence of `zensical.toml` is how we detect that the user wants
  to override defaults; seeding it would force every user into
  "custom" mode and make the bundled defaults unreachable.
- Don't revert the example seed to unconditional re-creation. It's
  one-shot, guarded by `/data/.zensical-example-seeded`, so deleting the
  example doesn't resurrect it on the next start.
- Don't drop the `effective-config.py` rewrite step. Without it,
  user-written `docs_dir = "docs"` in `/config/zensical.toml` would
  resolve against the wrong root (the source file's directory rather
  than `/var/lib/zensical/`), so Zensical would build from the
  unsynced copy. Equivalent breakage for `site_dir` (nginx serves
  the wrong directory). And — Zensical 0.0.43 still panics on
  absolute paths, so we can't sidestep this by hard-coding either.
- Don't re-introduce `mkdocs.yml` support in `resolve-config.sh`.
  Decided 2026-05-26: the add-on is Zensical-native; we never shipped
  a YAML codepath publicly, so dropping it cleanly was free. Adding it
  back means maintaining a YAML parser shim, the `material.extensions`
  remap, and two parallel "how to override" sections in DOCS.md — not
  worth it.
- Don't reintroduce `mkdocs` or `mkdocs-material` as runtime
  dependencies. The migration to Zensical (2026-05-26) was deliberate;
  see **Why Zensical** above. Mixing the two stacks would resurrect
  the same EoL / 2.0-rewrite trap we just stepped out of.
- Don't bump `zensical` blindly. Every 0.0.x release is allowed to
  break compat. Test the build + watcher + ingress path locally
  before lifting the pin.
- Don't expose port 8099 (or any port) outside ingress. The site has no
  auth.
- Don't watch `/config/` recursively. HA writes to that directory
  constantly (state files, `home-assistant.log`, …) and would trigger
  rebuilds on every state change.
- Don't switch `docs_dir` to `/config/docs` directly. The two-step
  mirror (sync → build) keeps `/config/docs/` clean — no `site/`
  artefacts dropped next to user files, and `rsync --delete` doesn't
  risk wiping anything the user put in /config/docs/ by accident.

## Pins & build

- `requirements.txt` pins `zensical==0.0.43` (exact) and
  `pymdown-extensions==10.21.3`. Zensical is alpha (0.0.x) — treat
  every patch bump as potentially breaking and verify locally before
  merging. We are explicitly *not* tracking mkdocs or mkdocs-material;
  that subtree was removed on 2026-05-26.
- **musllinux wheels** for `amd64` (`musllinux_1_2_x86_64`) and
  `aarch64` (`musllinux_1_2_aarch64`) are published on PyPI, so install
  on the Alpine HA base is fast and does not need a Rust toolchain. If
  Zensical ever stops shipping these wheels, we have to install Rust at
  build time — the image cost roughly doubles.
- **Python ≥3.10** required by Zensical. The base is pinned to Alpine
  `3.21` (`python3` 3.12.x) — bumped from 3.19 on 2026-06-03 because the
  multi-arch `base:3.19` tag doesn't exist and `build.yaml` (which carried
  the old per-arch 3.19 pin) is deprecated. Wheel-safe: the zensical wheel
  is `cp310-abi3` and pymdown is pure-Python, so neither cares about the
  3.11→3.12 change (verified by a local build). Confirm again on any
  further base bump.
- `HEALTHCHECK` probes the ingress port; nginx returning 200 on
  `/index.html` proves both init and serve worked.
- `image:` line in `config.yaml` is staged-commented; uncomment once
  `deploy.yaml` has actually published amd64 + aarch64 tags to GHCR so
  users get prebuilt images instead of a long local build.

## Zensical-specific gotchas

- **Emoji backend.** `material.extensions.emoji.twemoji` no longer
  exists in this image (the `mkdocs-material` package was removed).
  Use `zensical.extensions.emoji.{twemoji,to_svg}` instead. The bundled
  `zensical.toml` is already set up this way (Zensical defaults already
  use the zensical backends — no override needed unless we ever
  introduce a custom emoji index). Reject any PR that hard-codes
  `material.*` extension paths.
- **Icon set.** Zensical ships Lucide icons (`lucide/sun`,
  `lucide/moon`, …). `material/brightness-7` and other Material Design
  Icon names from the Material for MkDocs era won't resolve.
- **`--clean` semantics.** `zensical build --clean` clears the
  incremental build cache (NOT the output dir). `init-zensical` uses
  `--clean` to start cold; `zensical-watcher` omits `--clean` so warm
  rebuilds can reuse the cache for ms-scale builds. Reversing this
  costs build latency for no benefit.
- **No `--verbose` / `--quiet`.** Unlike mkdocs, the Zensical CLI has
  no verbosity flags. The `log_level` option therefore controls only
  bashio output, not the renderer.
- **Strict mode is unsupported.** `zensical serve --strict` prints a
  warning and ignores the flag (per CLI source as of 0.0.43). Don't
  rely on it for validation.
- The base (Alpine `3.21`) + image labels now live in the `Dockerfile`
  via `ARG BUILD_FROM=ghcr.io/home-assistant/base:3.21`; `build.yaml` was
  removed (Supervisor flags it as deprecated). The migrated labels were
  also corrected — the old `build.yaml` still carried stale MkDocs-era
  title/description/source.
- `HEALTHCHECK` probes the ingress port; nginx returning 200 on
  `/index.html` proves both init and serve worked.
- `image:` line in `config.yaml` is staged-commented; uncomment once
  `deploy.yaml` has actually published amd64 + aarch64 tags to GHCR so
  users get prebuilt images instead of a long local build.
