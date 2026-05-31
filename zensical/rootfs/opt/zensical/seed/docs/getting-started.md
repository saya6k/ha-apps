# Getting started

This add-on serves Markdown from your Home Assistant `/config/docs/`
directory as a static site, rendered with
[Zensical](https://zensical.org/).

## Source mapping

| Page | File |
| ---- | ---- |
| Landing page (`index.md`) | `/config/docs/index.md` |
| All other pages           | every `.md` file under `/config/docs/` |

Sub-directories under `/config/docs/` become sections in the sidebar.

## Live reload

The add-on watches `/config/docs/` for changes. When you save a file,
the site rebuilds within ~1 second. Refresh your browser to see the
update.

## Markdown features

Pymdown extensions are enabled out of the box.

!!! tip "Admonitions"
    Use `!!! note`, `!!! warning`, `!!! tip`, `!!! danger` and similar
    keywords to highlight blocks like this one.

```yaml
# Code blocks get syntax highlighting and a copy button.
automation:
  - alias: Welcome home
    trigger:
      platform: state
      entity_id: person.you
      to: home
    action:
      service: light.turn_on
      target:
        entity_id: light.entryway
```

=== "Tab one"
    Content inside the first tab.

=== "Tab two"
    Content inside the second tab.

- [x] Install the add-on
- [x] Open this page via the side panel
- [ ] Edit `/config/docs/index.md`
- [ ] Add a new page under `/config/docs/`

## Removing this sample

This file (`getting-started.md`) was copied into `/config/docs/` on first
start. Delete or replace it whenever you're ready — the site will rebuild
automatically.
