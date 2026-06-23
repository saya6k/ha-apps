# Changelog

## [4.1.11](https://github.com/saya6k/ha-apps/compare/wardrowbe-v4.1.10...wardrowbe-v4.1.11) (2026-06-23)


### Bug Fixes

* **wardrowbe:** use s6 fix-attrs.d to chown postgres data dir before init ([#445](https://github.com/saya6k/ha-apps/issues/445)) ([00a4f55](https://github.com/saya6k/ha-apps/commit/00a4f555de6089f073f005a576b62815de16fa8b))

## [4.1.10](https://github.com/saya6k/ha-apps/compare/wardrowbe-v4.1.9...wardrowbe-v4.1.10) (2026-06-23)


### Bug Fixes

* **wardrowbe:** stat /data/postgres parent instead of /data/postgres/data ([6996266](https://github.com/saya6k/ha-apps/commit/6996266262929bc62f13bd676af8aedb1e3e9a7a))
* **wardrowbe:** stat /data/postgres parent instead of /data/postgres/data ([#442](https://github.com/saya6k/ha-apps/issues/442)) ([981b15d](https://github.com/saya6k/ha-apps/commit/981b15d699c3c9bfbbdb29c932507df2b55ceb5a))

## [4.1.9](https://github.com/saya6k/ha-apps/compare/wardrowbe-v4.1.8...wardrowbe-v4.1.9) (2026-06-23)


### Bug Fixes

* **wardrowbe:** use numeric uid/gid in switch-user; execvp for PATH search ([2b9ee44](https://github.com/saya6k/ha-apps/commit/2b9ee44a5021e0637652bf362857266f053361d8))
* **wardrowbe:** use numeric uid/gid in switch-user; execvp for PATH search ([#438](https://github.com/saya6k/ha-apps/issues/438)) ([715159e](https://github.com/saya6k/ha-apps/commit/715159e48c929b1bf6e85cbaf333303f036c5b99))

## [4.1.8](https://github.com/saya6k/ha-apps/compare/wardrowbe-v4.1.7...wardrowbe-v4.1.8) (2026-06-23)


### Bug Fixes

* **wardrowbe:** replace s6-setuidgid with custom switch-user binary ([e73f9b9](https://github.com/saya6k/ha-apps/commit/e73f9b9a551a161ff9cf3504277fbd54b9f68b0d))
* **wardrowbe:** replace s6-setuidgid with custom switch-user binary ([#435](https://github.com/saya6k/ha-apps/issues/435)) ([3dbbc76](https://github.com/saya6k/ha-apps/commit/3dbbc7610ad99f2dccca7f497c4926ea6f8e217f))

## [4.1.7](https://github.com/saya6k/ha-apps/compare/wardrowbe-v4.1.6...wardrowbe-v4.1.7) (2026-06-23)


### Bug Fixes

* **wardrowbe:** pass through getpwnam to real /etc/passwd in fakeeuid shim ([a5ae543](https://github.com/saya6k/ha-apps/commit/a5ae5435ad5f7a138f7050888c1571a38e29525b))
* **wardrowbe:** pass through getpwnam to real /etc/passwd in fakeeuid shim ([#432](https://github.com/saya6k/ha-apps/issues/432)) ([0be1003](https://github.com/saya6k/ha-apps/commit/0be1003b2ab5cfd1e8349c6ab40dfdc76dd3c506))

## [4.1.6](https://github.com/saya6k/ha-apps/compare/wardrowbe-v4.1.5...wardrowbe-v4.1.6) (2026-06-23)


### Bug Fixes

* **wardrowbe:** handle postgres-owned cluster on production instances ([27f406a](https://github.com/saya6k/ha-apps/commit/27f406ab1ca4e54e62f745c54b9e936a0eab77db))
* **wardrowbe:** handle postgres-owned cluster on production instances ([#429](https://github.com/saya6k/ha-apps/issues/429)) ([e2307db](https://github.com/saya6k/ha-apps/commit/e2307db07886c565ad8511aeaa993ee5326a9d5f))

## [4.1.5](https://github.com/saya6k/ha-apps/compare/wardrowbe-v4.1.4...wardrowbe-v4.1.5) (2026-06-23)


### Bug Fixes

* **wardrowbe:** rmdir stale /data/postgres/data before initdb ([91824f0](https://github.com/saya6k/ha-apps/commit/91824f0bb4ebed7dcb3165f8fb736717448e6831))
* **wardrowbe:** rmdir stale /data/postgres/data before initdb ([#423](https://github.com/saya6k/ha-apps/issues/423)) ([6b150a0](https://github.com/saya6k/ha-apps/commit/6b150a02522aaeaec898e902860a1e44343e21cb))

## [4.1.4](https://github.com/saya6k/ha-apps/compare/wardrowbe-v4.1.3...wardrowbe-v4.1.4) (2026-06-23)


### Bug Fixes

* **wardrowbe:** add getpwuid shim; chmod /var/lib/postgresql 755 at build ([#417](https://github.com/saya6k/ha-apps/issues/417)) ([dfba4dc](https://github.com/saya6k/ha-apps/commit/dfba4dc32d9fa4870ea21c5ea332351d26bed468))
* **wardrowbe:** drop s6-setuidgid from psql calls; create nginx log dir ([#419](https://github.com/saya6k/ha-apps/issues/419)) ([f7b7a3a](https://github.com/saya6k/ha-apps/commit/f7b7a3a9db6dd16860f3cc72b5e39cf617e7efd6))
* **wardrowbe:** HA container capability fixes — full stack boot ([b691847](https://github.com/saya6k/ha-apps/commit/b6918474aedfcea59ea4a7a5e197ee4f649c4e6a))
* **wardrowbe:** run initdb directly into /data/postgres/data ([#418](https://github.com/saya6k/ha-apps/issues/418)) ([5afb55e](https://github.com/saya6k/ha-apps/commit/5afb55e121f8f263b431125c4a8d544c0f4b6b3a))
* **wardrowbe:** run postgres as root via LD_PRELOAD shim; fix nginx caps ([#414](https://github.com/saya6k/ha-apps/issues/414)) ([2416e22](https://github.com/saya6k/ha-apps/commit/2416e222ca72fc9fa9d93ff06476c79a56fbcc89))
* **wardrowbe:** wait for backend before starting nginx ([#420](https://github.com/saya6k/ha-apps/issues/420)) ([601a19d](https://github.com/saya6k/ha-apps/commit/601a19d09c95f038b31f47b0fb0779b88ebcdc82))

## [4.1.3](https://github.com/saya6k/ha-apps/compare/wardrowbe-v4.1.2...wardrowbe-v4.1.3) (2026-06-23)


### Bug Fixes

* **wardrowbe:** remove runtime chown calls; use s6-setuidgid for postgres dirs ([28b50ee](https://github.com/saya6k/ha-apps/commit/28b50ee63a53dccfd4aff191e9c7dc1b1631a788))

## [4.1.2](https://github.com/saya6k/ha-apps/compare/wardrowbe-v4.1.1...wardrowbe-v4.1.2) (2026-06-23)


### Bug Fixes

* **repo:** replace {,**} with explicit dir+glob rules in all AppArmor profiles ([6903c13](https://github.com/saya6k/ha-apps/commit/6903c1329a95f5833114dd3aabdc9849fbf8e7b8))

## [4.1.1](https://github.com/saya6k/ha-apps/compare/wardrowbe-v4.1.0...wardrowbe-v4.1.1) (2026-06-23)


### Bug Fixes

* **wardrowbe:** allow AppArmor write access to /var/lib/postgresql ([733efb5](https://github.com/saya6k/ha-apps/commit/733efb53e44e0762f3db271ee1344a0541e1a48b))

## [4.1.0](https://github.com/saya6k/ha-apps/compare/wardrowbe-v4.0.1...wardrowbe-v4.1.0) (2026-06-23)


### Features

* **wardrowbe:** add AppArmor profile ([03cf2c5](https://github.com/saya6k/ha-apps/commit/03cf2c546a6353297bd00b0a5d7ea6e34dc83a09))


### Performance

* **wardrowbe:** tune PostgreSQL for low-IOPS storage (SD card, eMMC) ([07945fc](https://github.com/saya6k/ha-apps/commit/07945fc4b5d438a930a8e2f51e11f1f93410ecbc))




## [4.0.1](https://github.com/saya6k/ha-apps/compare/wardrowbe-v4.0.0...wardrowbe-v4.0.1) (2026-06-22)


### Bug Fixes

* **wardrowbe:** split compound import and suppress E402 on conditional import ([d313737](https://github.com/saya6k/ha-apps/commit/d3137373412ab75e04a066dacf887661ac310c2d))


### Documentation

* **wardrowbe:** reorder README shields — Show add-on below for-the-badge badges ([150aad3](https://github.com/saya6k/ha-apps/commit/150aad374c28e4a509052c95b67782dd39931ca2))


### Build System

* **wardrowbe:** move venv to builder, strip Python .so extensions ([#357](https://github.com/saya6k/ha-apps/issues/357)) ([c386655](https://github.com/saya6k/ha-apps/commit/c3866555a8fc5f102db6f6ee423aa12d51016331))


### CI

* **repo:** tighten markdownlint scope and disable style-only rules ([9fe6f97](https://github.com/saya6k/ha-apps/commit/9fe6f97b9fee3e1c010f2ee534b36ea8de2a74fe))

## [4.0.0](https://github.com/saya6k/ha-apps/compare/wardrowbe-v3.0.0...wardrowbe-v4.0.0) (2026-06-18)


### ⚠ BREAKING CHANGES

* **wardrowbe:** clothing photos move from /config/photos to /data/photos. Existing photos are migrated automatically on first start; the addon_config photos dir is no longer used.

### Features

* **wardrowbe:** move clothing photos to /data/photos ([34c50e7](https://github.com/saya6k/ha-apps/commit/34c50e7c2bd63171fd700267b0d61e16294b9b36))


### Bug Fixes

* **wardrowbe:** add HEALTHCHECK to restore health-based auto-restart ([cdbbd7f](https://github.com/saya6k/ha-apps/commit/cdbbd7f1a76521732530a5806805b0572f2c4044))


### Documentation

* **wardrowbe:** add Show add-on badge to README ([e0e2a38](https://github.com/saya6k/ha-apps/commit/e0e2a38faa38a1f9fdfe43e6754aeeda5a80221b))


### Build System

* **wardrowbe:** build add-on locally, drop GHCR image reference ([f7cf363](https://github.com/saya6k/ha-apps/commit/f7cf363b0b0163df4ee09fd0827821ff99caa218))
* **wardrowbe:** migrate off build.yaml, pin base image, bump upstream ([560218f](https://github.com/saya6k/ha-apps/commit/560218f23144833cf571ce45706edd69780322a3))
* **wardrowbe:** remove npm rebuild sharp from frontend build ([91fb4a5](https://github.com/saya6k/ha-apps/commit/91fb4a5f5d3dcfab2aab871c3c1a1376a229d23e))
* **wardrowbe:** remove npm, py3-virtualenv, debug layer, pip upgrade ([e9ce8ae](https://github.com/saya6k/ha-apps/commit/e9ce8aee06b2cdaa7281965543963f3716af9ca7))

## [3.0.0](https://github.com/saya6k/ha-apps/compare/wardrowbe-v2.0.2...wardrowbe-v3.0.0) (2026-06-18)


### ⚠ BREAKING CHANGES

* **wardrowbe:** clothing photos move from /config/photos to /data/photos. Existing photos are migrated automatically on first start; the addon_config photos dir is no longer used.

### Features

* **wardrowbe:** move clothing photos to /data/photos ([34c50e7](https://github.com/saya6k/ha-apps/commit/34c50e7c2bd63171fd700267b0d61e16294b9b36))


### Bug Fixes

* **wardrowbe:** add HEALTHCHECK to restore health-based auto-restart ([cdbbd7f](https://github.com/saya6k/ha-apps/commit/cdbbd7f1a76521732530a5806805b0572f2c4044))


### Documentation

* **wardrowbe:** add Show add-on badge to README ([e0e2a38](https://github.com/saya6k/ha-apps/commit/e0e2a38faa38a1f9fdfe43e6754aeeda5a80221b))


### Build System

* **wardrowbe:** build add-on locally, drop GHCR image reference ([f7cf363](https://github.com/saya6k/ha-apps/commit/f7cf363b0b0163df4ee09fd0827821ff99caa218))
* **wardrowbe:** migrate off build.yaml, pin base image, bump upstream ([560218f](https://github.com/saya6k/ha-apps/commit/560218f23144833cf571ce45706edd69780322a3))
* **wardrowbe:** remove npm rebuild sharp from frontend build ([91fb4a5](https://github.com/saya6k/ha-apps/commit/91fb4a5f5d3dcfab2aab871c3c1a1376a229d23e))
* **wardrowbe:** remove npm, py3-virtualenv, debug layer, pip upgrade ([e9ce8ae](https://github.com/saya6k/ha-apps/commit/e9ce8aee06b2cdaa7281965543963f3716af9ca7))

## [2.0.2](https://github.com/saya6k/ha-apps/compare/wardrowbe-v2.0.1...wardrowbe-v2.0.2) (2026-06-18)


### Documentation

* **wardrowbe:** add Show add-on badge to README ([e0e2a38](https://github.com/saya6k/ha-apps/commit/e0e2a38faa38a1f9fdfe43e6754aeeda5a80221b))
* **zensical:** add Show add-on badge to README ([57ccc5c](https://github.com/saya6k/ha-apps/commit/57ccc5c3f992cedb2f76b78cc5dac01b2054746c))


### Build System

* **wardrowbe:** remove npm rebuild sharp from frontend build ([91fb4a5](https://github.com/saya6k/ha-apps/commit/91fb4a5f5d3dcfab2aab871c3c1a1376a229d23e))
* **wardrowbe:** remove npm, py3-virtualenv, debug layer, pip upgrade ([e9ce8ae](https://github.com/saya6k/ha-apps/commit/e9ce8aee06b2cdaa7281965543963f3716af9ca7))

## [2.0.1](https://github.com/saya6k/ha-apps/compare/wardrowbe-v2.0.0...wardrowbe-v2.0.1) (2026-06-18)


### Build System

* **wardrowbe:** build add-on locally, drop GHCR image reference ([f7cf363](https://github.com/saya6k/ha-apps/commit/f7cf363b0b0163df4ee09fd0827821ff99caa218))

## [2.0.0](https://github.com/saya6k/ha-apps/compare/wardrowbe-v1.4.2...wardrowbe-v2.0.0) (2026-06-15)


### ⚠ BREAKING CHANGES

* **wardrowbe:** clothing photos move from /config/photos to /data/photos. Existing photos are migrated automatically on first start; the addon_config photos dir is no longer used.

### Features

* **wardrowbe:** move clothing photos to /data/photos ([34c50e7](https://github.com/saya6k/ha-apps/commit/34c50e7c2bd63171fd700267b0d61e16294b9b36))

## [1.4.2](https://github.com/saya6k/ha-apps/compare/wardrowbe-v1.4.1...wardrowbe-v1.4.2) (2026-06-15)


### Bug Fixes

* **wardrowbe:** add HEALTHCHECK to restore health-based auto-restart ([cdbbd7f](https://github.com/saya6k/ha-apps/commit/cdbbd7f1a76521732530a5806805b0572f2c4044))

## [1.4.1](https://github.com/saya6k/ha-apps/compare/wardrowbe-v1.4.0...wardrowbe-v1.4.1) (2026-06-15)


### Build System

* **wardrowbe:** migrate off build.yaml, pin base image, bump upstream ([560218f](https://github.com/saya6k/ha-apps/commit/560218f23144833cf571ce45706edd69780322a3))

## [1.4.0] — 2026-05-25

### Removed (breaking)
- **MCP server extracted to a separate repo**:
  [`saya6k/mcp-wardrowbe`](https://github.com/saya6k/mcp-wardrowbe),
  now distributed as a standalone Python package (`pip install wardrowbe-mcp`).
  The add-on no longer bundles it — one fewer process inside the container,
  no auto-bound `8080/tcp` port, no auto-generated `/config/.mcp_api_key`,
  smaller image. If you used MCP, install the standalone package and point
  it at this add-on's backend (or any other Wardrowbe instance).
- **Removed `options:` / `schema:` keys** (will be ignored if still
  present in user configs): `mcp_enabled`, `mcp_api_key`, `mcp_auth_mode`,
  `mcp_external_id`, `mcp_oidc_refresh_token`.
- **Removed `8080/tcp` from `ports:` / `ports_description`**.
- Deleted `mcp_server/` package, `rootfs/etc/s6-overlay/s6-rc.d/mcp/`
  service, and all `MCP_*` env wiring in `00-init.sh`.

### Migration
1. Note your current `mcp_oidc_refresh_token` (if OIDC) — you'll reuse it.
2. Update the add-on. The MCP-related options disappear from the UI.
3. On any host that can reach this add-on, install the standalone:
   `pip install wardrowbe-mcp` (or `uv tool install wardrowbe-mcp`).
4. Run it pointing at the add-on:
   `wardrowbe-mcp --wardrowbe-url http://<ha-host>:8099 --auth oidc ...`.
5. Update your MCP client config — the URL is no longer `:8080` on the
   HA host; it's wherever you ran the standalone process.

Rationale: `notes/extraction.md` in the new repo.

## [1.3.1] — 2026-05-25

### Fixed
- **Skill bundle now actually ships in the wheel.** 1.3.0 used a
  `wardrowbe_mcp/skill -> ../skill` symlink pointing OUTSIDE the
  package; setuptools doesn't follow those when building wheels, so
  `register_skill_resources()` saw an empty directory and logged
  `Skill bundle directory missing at .../wardrowbe_mcp/skill;
  MCP resources not registered`. The MCP server still served tools,
  but `resources/list` returned `[]`. Moved the canonical bundle
  *into* the package at `mcp_server/wardrowbe_mcp/skill/` (real
  directory now); `.claude/skills/wardrowbe-skill` symlink updated
  to point at the new location.
- **Broaden `package-data` glob** to `skill/**/*` so future skills
  shipping `scripts/`, `assets/`, or non-`.md` files also land in
  the wheel.

## [1.3.0] — 2026-05-25

### Added
- **Expose `mcp_server/skill/` as MCP resources** so compatible clients
  auto-install the wardrowbe-skill bundle without a separate package
  URL. Each file under the skill directory is registered as
  `skill://wardrowbe-skill/<relpath>` (e.g.
  `skill://wardrowbe-skill/SKILL.md`,
  `skill://wardrowbe-skill/examples/morning-outfit.md`). The receiving
  client (e.g. `ha-llm-conversation-agent` ≥ 1.11.0) calls
  `resources/list` + `resources/read` once at startup and writes the
  bundle into its skills directory.
- **Canonical skill location**: `mcp_server/wardrowbe_mcp/skill/`
  (inside the package so setuptools includes it via `package-data`).
  `.claude/skills/wardrowbe-skill` symlinks here for Claude Code users.

### Internal
- `mcp_server/pyproject.toml`: bumped to 0.2.0, added
  `[tool.setuptools.package-data]` for the skill bundle.

## [1.2.1] — 2026-05-25

### Fixed
- **MCP server now binds container port `8080`** instead of `3000`.
  Wardrowbe's Next.js frontend already listens on `3000`, so the MCP
  server lost the race and every external request hit the frontend's
  404 page instead. Switched to `8080` (HTTP-alt standard; same as
  `saya6k/mcp-grocy-api`). If you'd manually mapped host port 3000 to
  the addon's old MCP port, re-map to `8080/tcp` in the addon's
  Network pane and update your MCP client config URL accordingly.
- **`aiohttp.ClientSession()` `RuntimeError: no running event loop`** at
  MCP startup. The session was constructed eagerly before uvicorn
  started its event loop; aiohttp ≥ 3.10 rejects that. Restructured
  `__main__.py` to own the loop via `asyncio.run(_serve(args))` and
  create the session inside the running loop with `async with`.

### Internal docs
- `notes/mcp-server-design.md` updated with both gotchas
  ("Why not port 3000", "Why asyncio.run instead of uvicorn.run") so
  the next bump doesn't re-introduce either.

## [1.2.0] — 2026-05-25

### Changed
- **Wardrobe photos moved from `/media/wardrowbe/` to `/config/photos/`.**
  `/media/` is shared HA-wide via the media browser, which is the wrong
  default for personal clothing photos. `/config/` is per-addon and
  private; the subdir name reflects content (`photos`) rather than
  re-stating the addon name. One-shot migration in `00-init.sh` copies
  from `/media/wardrowbe/` (1.0–1.1.x), `/data/wardrobe/` (≤ 0.x), or
  `/config/wardrobe/` (a brief 1.2.0 dev iteration) on first boot, then
  clears the legacy directory.

### Compatibility
- All `options:` / `schema:` keys unchanged.
- Snapshot size trade-off: photos now sit inside `addon_config`, so
  every HA add-on snapshot includes them. See DOCS "Data & Storage".

## [1.1.0] — 2026-05-25

### Added
- **MCP server** (`mcp_server/`) — exposes the wardrowbe API as MCP tools
  over SSE (`/sse`) and Streamable HTTP (`/mcp`) on container port 8080.
  Tools ported one-for-one from `hacs-wardrowbe/llm_api/` plus three new
  read-only helpers (`list_items`, `get_item`, `get_outfit`). Bearer-token
  auth via auto-generated `mcp_api_key` (persisted to `/config/.mcp_api_key`).
  Backend auth supports both dev_login sync and OIDC refresh_token (mirrors
  hacs-wardrowbe's `WardrowbeOAuth2Implementation`).
- **Skill bundle** (`mcp_server/skill/`) — vendor-neutral
  [agentskills.io](https://agentskills.io)-compatible skill for Claude
  Code / Desktop / any MCP-aware host, with `SKILL.md`, `README.md`, and
  three worked-example workflows under `examples/`. Auto-discoverable via
  the `.claude/skills/wardrowbe-skill` symlink.
- New addon options: `mcp_enabled`, `mcp_api_key`, `mcp_auth_mode`
  (`dev`|`oidc`), `mcp_external_id`, `mcp_oidc_refresh_token`.

### Changed
- Container port 8080 declared in `ports:` but **not bound to the host by
  default** (`null`). Map it explicitly in the addon UI's Network section
  if you want to reach the MCP server from outside the HA host.

### Compatibility
- All previous `options:` / `schema:` keys unchanged. Adding the
  `mcp_*` keys is additive.

## [1.0.7] — 2026-05-25

### Added
- Daily `pg_dump` scheduler written to `/share/wardrowbe/backups/`. Upstream
  wardrowbe has no backup feature, so the packaging layer now ships one.
- New options: `backup_enabled` (default `true`), `backup_retention_days`
  (default 7, 0 disables pruning), `backup_hour` (default 3, container TZ).

### Fixed
- `/share/wardrowbe/backups/` was previously created empty with no producer.
  Docs incorrectly claimed an "in-app DB export" wrote there.

## [1.0.6] — 2026-05-25

### Changed
- PostgreSQL data now lives at `/data/postgres/data/` with
  `backup_exclude: ["postgres/**", "redis/**"]` so HA add-on snapshots stay
  small even with large wardrobes.

### Added
- `AGENTS.md` + `CLAUDE.md` (symlink) — dev/agent guidance, matching the
  layout used by `ha-supertonic` / `ha-rethink` / `ha-playwright`.
- `translations/{en,ko}.yaml` — option labels/descriptions for the HA add-on
  UI in English and Korean.
- `.github/workflows/{ci,deploy,lock,stale,release}.yaml` — thin callers to
  the `hassio-addons/workflows` reusable workflows + tag-driven GitHub
  release.
- `.gitignore` + `notes/` directory convention for local-only scratch docs.

### Compatibility
- All `options:` / `schema:` keys unchanged. Existing user configs continue
  to work without edits.

## [1.0.5] — 2026-05-01

### Changed
- Default wardrowbe version updated to v1.2.5

## [1.0.4] — 2026-04-18

### Changed
- Default wardrowbe version updated to v1.2.4

## [1.0.3] — 2026-03-31

### Fixed
- Persistent database in `/config/` for migration

## [1.0.2] — 2026-03-31

### Changed
- Default wardrowbe version updated to v1.2.3

## [1.0.1] — 2026-03-21

### Added
- `oidc_mobile_client_id` config option for mobile app OIDC (public client, PKCE)
- Mobile app setup instructions in DOCS.md

### Changed
- Default wardrowbe version updated to v1.2.2

### Fixed
- Worker auto-detects `WorkerSettings` location (v1.2.2 moved it from `tagging.py` to `worker.py`)

## [1.0.0] — 2026-03-21

### Added
- Upstream wardrowbe v1.2.2 support (auto-detects v1.2.1 as well)
- `dev_login` toggle in addon config — switch between dev login and OIDC
- `external_url` option for OIDC callback configuration
- OIDC authentication with auto-detection (auto-disables dev login when OIDC is set)
- `AUTH_TRUST_HEADER` enabled for HA ingress compatibility
- Persistent secrets in `/config/` (addon_config mount) for migration
- Wardrobe photos stored in `/media/wardrowbe/` (visible in HA Media Browser)
- DB backup directory at `/share/wardrowbe/backups/`
- Auto-migration from old `/data/wardrobe/` storage layout
- CHANGELOG.md and DOCS.md

### Fixed
- Next.js Image Optimization 400 errors — disabled `/_next/image` proxy, images served directly from backend
- Next.js `compress: false` injected at build time so nginx `sub_filter` works on all response types
- `BACKEND_URL` set at build time so Next.js rewrites are baked correctly for `127.0.0.1:8000`
- `NEXTAUTH_URL` properly set to external URL when configured, internal URL otherwise
- JWT `decryption operation failed` after restart — secrets now persisted in addon_config
- Worker `ModuleNotFoundError` — auto-detects `WorkerSettings` in both `worker.py` (v1.2.2+) and `tagging.py` (v1.2.1)
- PYTHONPATH and PATH set in Dockerfile ENV and s6 container environment
- PostgreSQL role/database creation uses Unix socket (trust auth) instead of TCP (md5)
- nginx `sub_filter` for HA ingress path rewriting (CSS, JS, HTML, API paths, page routes)
- Client-side ingress script injected via `sub_filter` for dynamic fetch/XHR/history rewriting
- nginx allows private network ranges for external reverse proxy access

### Architecture
- Single-container s6-overlay v3: PostgreSQL, Redis, FastAPI backend, arq worker, Next.js frontend, nginx
- Source cloned from GitHub at build time (`WARDROWBE_VERSION` ARG) — no bundled code
- Multi-stage Dockerfile: source clone → frontend build → backend wheels → final HA base image
- Backend wheels built on HA base image to match Python version

## [0.3.0] — 2026-03-19

### Added
- Storage layout: addon_config for secrets, media for photos, share for backups, data for DBs
- `dev_login` config option
- `external_url` config option
- OIDC support with external domain

## [0.2.0] — 2026-03-18

### Added
- Initial working addon with wardrowbe v1.2.1
- s6-overlay service management (postgres, redis, backend, worker, frontend, nginx)
- HA ingress support with nginx reverse proxy
- Dev login mode for ingress access
- AI configuration (Ollama / OpenAI)

### Known Issues
- Next.js Image Optimization not working (fixed in 1.0.0)
- Secrets regenerated on restart (fixed in 0.3.0)
