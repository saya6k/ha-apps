# CodeMirror

![Supports aarch64 Architecture][aarch64-shield] ![Supports amd64 Architecture][amd64-shield]

CodeMirror 6 editor for Home Assistant, served through the Ingress side panel.
Edits YAML, JSON, Python, shell and Markdown with live Markdown preview, entity
and `mdi:` icon completion, Jinja template rendering, configuration checks,
backups, document tabs and folder-aware drag-and-drop uploads. Only `/config`
is accessible by default; each additional workspace is enabled with its
`allow_*` option.

Based on [roman-pinchuk/conf-edit-ha](https://github.com/roman-pinchuk/conf-edit-ha).
Official CodeMirror branding is preserved with its source and license.

## ⚠️ THIS IS A BETA VERSION

This build comes from the beta channel — a pre-release (rc) of this app.

- It may not work at all.
- It might stop working or change without notice.
- It could have a negative impact on your system.

If you want the stable release: <https://github.com/saya6k/ha-apps>

See **[DOCS.md](DOCS.md)** for configuration and usage.

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
