# Changelog

## [0.5.2](https://github.com/saya6k/ha-app-codemirror/releases/tag/v0.5.2)

## What's Changed

## Bug Fixes

* fix: support musl renameat2 and speed up folder ZIP uploads (#1) @saya6k

**Full Changelog**: https://github.com/saya6k/ha-app-codemirror/compare/v0.5.1...v0.5.2

## [0.5.1](https://github.com/saya6k/ha-app-codemirror/releases/tag/v0.5.1)

First release through the ha-apps catalog. The image is now built on the Home Assistant base image with an s6-overlay service and published to `ghcr.io/saya6k/app-codemirror`.

- Replace legacy Supervisor map types with `local_apps` and `all_app_configs`
  to eliminate deprecation warnings while preserving mount paths and permissions.

### Earlier versions

#### 0.5.0

- Complete `mdi:` icon names in YAML/JSON with actual SVG glyphs in suggestions
  and hover previews, using a locally bundled, on-demand MDI catalog.
- Add individual reload actions for automations, scripts, groups and Core YAML
  configuration, plus a Material Design Icons link in the Home Assistant menu.
- Render unsaved Jinja templates using live Home Assistant states, with a selection
  or whole-document result panel and hover previews for standalone expressions.
- Show template errors inline; keep results inert and discard responses after edits
  or navigation. Korean controls and mobile preview are supported.
#### 0.4.1

- Load expanded directories on demand, with 500-entry pages, instead of scanning
  all mounted directory trees before showing files.
- Restore the last document independently of directory and entity API requests.
- Show readable directory errors with a retry button; slow or unavailable mounts
  no longer delay other roots. Directory requests time out after 15 seconds.

#### 0.4.0

- Added Automatic, Korean and English UI language choices, including CodeMirror
  search/replace phrases, with browser-local persistence.
- Added document tabs that retain drafts, cursor/selection, scroll and undo state;
  dirty tab close confirmation and protections apply to inactive tabs too.
- Use the unmodified official CodeMirror logo for icon.png/logo.png, with the
  upstream SVG and MIT license retained and a reproducible rasterization script.
- Folder picker and folder drop uploads now compress to ZIP in the browser and
  extract into staging on the server before exclusive publication.
- Archive validation rejects traversal, links, duplicate/conflicting paths,
  encrypted/unsupported ZIPs and excessive expansion. Existing folders are kept.


#### 0.3.0

- Replaced workspace/folder selectors with a single tree containing all enabled roots.
- Removed the action toolbar; file operations use context menus and HA controls use
  the header menu, also available on mobile.
- Added recursive rename/delete/cut/copy/paste with root permissions, no-clobber
  publishing, unsaved-document guards, keyboard shortcuts and mobile menu access.
- Creation, upload and paste follow the selected directory or selected file parent.
- Entity suggestions display Home Assistant state_translated values through a fixed
  Core template API request, falling back to raw states when unavailable.

#### 0.2.1

- Explicitly copy frontend sources in Docker builds so incomplete app copies fail
  at the source-copy step rather than with TypeScript TS18003.
- Include a local-app packaging script that preserves frontend/src and hidden
  build files while excluding dependencies and browser-test artifacts.

#### 0.2.0

- Top toolbar for safe file/directory creation in the selected workspace and folder.
- Manual YAML validation, checked YAML reload and confirmed Core restart through
  Home Assistant and Supervisor APIs; unsaved edits block lifecycle actions.
- Entity dropdown with ID substring/friendly-name search, keyboard selection,
  refresh and visible connection errors.
- Added `hassio_api` with the `homeassistant` role for Core restart.
- Documented why the supported Supervisor proxy is retained and how its internal
  Core connection automatically uses Unix sockets on supported installations.
- Tests cover creation boundaries, API permissions/errors, action sequencing,
  dirty documents and real-browser entity completion.

#### 0.1.0

- Based on conf-edit-ha 1.6.3, retaining its CodeMirror editor and HA integration.
- Markdown language support and sanitized live preview.
- Default mounts for local apps, media, all app configs, SSL and share, with
  independent opt-in access options enforced by the API.
- Folder-aware drag-and-drop and picker uploads, including binary files.
- No-clobber uploads, upload limits, atomic saves/backups and link-safe paths.
- Ingress-only production access, request-origin defense and browser security headers.
- Workspace persistence, unsaved-change guards and accessible file controls.

