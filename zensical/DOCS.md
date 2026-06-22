# Zensical add-on — Documentation

This add-on renders Markdown from your Home Assistant `/config/` directory
as a [Zensical][zensical] site, served through the Home Assistant
**ingress** side panel.

> **Heads-up — Zensical is in alpha (0.0.x).** Zensical is the Material
> for MkDocs team's successor SSG. It ships a `zensical.toml`
> configuration format and its own Material-like theme, but both are
> still being stabilised. Some Material-era theme knobs (e.g. `primary` /
> `accent` colour aliases, `material/*` icon names) may render
> differently or be ignored until Zensical hits a stable release.

## Source layout

```text
/config/docs/
├── index.md      ← landing page
├── any.md        ← becomes a page in the sidebar
└── nested/
    └── page.md   ← becomes a section + page in the sidebar
```

**Index resolution:** `/config/docs/index.md` is the landing page. If
it's missing, a small placeholder is rendered instead. `/config/README.md`
is not read by the add-on — write a real `index.md` if you want a
landing page in both your HA docs site and on GitHub.

**Seeding:** if `/config/docs/` is missing on first start, a small
starter set (including `index.md` and `getting-started.md`) is copied
in. Existing files are never overwritten.

## How it stays up to date

1. `inotifywait` watches `/config/docs/` and the add-on config dir
   (`/addon_config/`) recursively for any change (create / modify /
   delete / move).
2. Events within a 1-second window are collapsed into a single rebuild.
3. `zensical build` regenerates the static site into the working directory.
4. `nginx` serves the new files. Refresh the browser to see them.

The watcher only looks at the paths above — other files under `/config/`
(automations, configuration.yaml, log files) are ignored, so editing
those won't trigger a rebuild.

## Configuration

### Add-on options

| Option | Type | Default | Notes |
| ------ | ---- | ------- | ----- |
| `log_level` | enum | `info` | One of `trace`, `debug`, `info`, `notice`, `warning`, `error`, `fatal`. Sets bashio's threshold for the add-on's own log lines (file events, build status, sync errors). The Zensical CLI has no `--verbose` / `--quiet` flags, so its build output is not affected by this option. |

The remaining customisation is done through files inside the add-on's
own config directory, which the Supervisor exposes at:

```text
/addon_configs/<repo-prefix>_zensical/
```

on the host (the exact prefix depends on how you installed the add-on)
and at `/addon_config/` inside the container.

### Override the renderer config

On first start the add-on writes a publish-ready example to
`/config/zensical.example.toml`. The intent is for this same file to
work two ways:

- **Inside the add-on:** rename to `/config/zensical.toml` and the
  watcher picks it up on the next save.
- **On GitHub Pages (or any `zensical build` outside the container):**
  push `/config/` to a repo and a workflow can run
  `zensical build -f /config/zensical.toml` directly — the example
  uses relative paths (`docs_dir = "docs"`, `site_dir = "_site"`) so
  it doesn't need editing.

**Resolution order (highest priority first):**

1. `/config/zensical.toml` — your publish-ready config. Travels with
   your /config repo to GitHub.
2. `/addon_config/zensical.toml` — add-on-only override. Useful when
   you want settings that should not be published.
3. `/opt/zensical/zensical.toml` — bundled defaults.

The resolved file's `docs_dir` and `site_dir` are **always rewritten
at runtime** to `/var/lib/zensical/docs` and `/var/lib/zensical/site`
so the sync layer and nginx keep working. Everything else from your
file — `site_name`, `theme`, `markdown_extensions`, etc. — passes
through verbatim. That means a value like `site_dir = "_site"` in
your published config is honoured by external builds (GitHub Pages)
but ignored inside the add-on.

### Publishing your /config to GitHub

A minimal recipe:

1. Rename `/config/zensical.example.toml` to `/config/zensical.toml`,
   adjust `site_name`, theme features, palette to taste.
2. Make sure there's a `/config/docs/index.md` — that's the landing
   page both inside the add-on and for a `zensical build` running on
   GitHub Pages.
3. Add a `.gitignore` containing at least `_site/` (or whatever your
   `site_dir` is).
4. `git init`, push, and add a GitHub Actions workflow that runs
   `pip install zensical pymdown-extensions && zensical build` and
   deploys the `_site/` directory to GitHub Pages.

### Theme overrides

Create `/addon_config/overrides/` and add template partial overrides
there. Then in your custom config, point the theme at it:

```toml
[project.theme]
custom_dir = "/addon_config/overrides"
```

Note: Zensical's template engine is MiniJinja (similar to Jinja2 but
not identical) — Material for MkDocs partials may need small tweaks.
See the [Zensical customization docs](https://zensical.org/docs/customization/).

## What is rendered

Pymdown extensions enabled out of the box:

- Admonitions (`!!! note`, `!!! warning`, …) + collapsible details
- Code highlighting with copy button
- Tabbed content blocks (`=== "Tab"`)
- Task lists (`- [x]`), definition lists, footnotes, abbreviations
- Mermaid diagrams (fenced as ```` ```mermaid ````)
- Emoji shortcodes via Twemoji

The Material theme provides instant page loading, sidebar navigation,
client-side search, and an automatic light / dark palette toggle.

## Security

- The add-on serves only through Home Assistant ingress
  (`ingress: true`, `ingress_port: 8099`). No port is exposed on the
  host network.
- `nginx` allow-lists the Supervisor ingress IP (`172.30.32.2`) and
  denies everything else, so even from inside the container network the
  site cannot be reached by other add-ons.
- The renderer has read/write access to `/config/`. Files under
  `/config/docs/` are mirrored verbatim into the site output, so do
  **not** place secrets under that path.

## Troubleshooting

| Symptom | Likely cause |
| ------- | ------------ |
| "Build failed" placeholder page | `zensical build` errored — check add-on logs for the YAML / Markdown error. |
| Changes don't show up | Hard-refresh the browser (`Cmd/Ctrl + Shift + R`). Material caches aggressively. |
| 404 on a nested page | Make sure the file ends in `.md` and lives under `/config/docs/`. Files outside that path are ignored. |
| Add-on logs spamming "sync failed" | Check `/config/docs/` permissions — the add-on needs read access. |

## Acknowledgements

Inspired by [XavierBerger/mkdocs][xb-mkdocs] (HA add-on packaging
pattern for a Material-style renderer) and [wendevlin/homedocs][wd-homedocs]
(file watcher → automatic rebuild). The renderer itself is
[Zensical][zensical] by the Material for MkDocs team.

[zensical]: https://zensical.org/
[xb-mkdocs]: https://github.com/XavierBerger/home-assistant-addons/tree/main/mkdocs
[wd-homedocs]: https://github.com/wendevlin/homeassistant-addons/tree/main/homedocs
