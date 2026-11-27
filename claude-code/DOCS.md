# Claude Code app — Documentation

Runs Anthropic's [Claude Code][claude-code] CLI in a browser terminal
(ttyd + tmux) inside the Home Assistant **ingress** side panel. The CLI is
baked into the image; the login and every Claude Code setting persist
across restarts and updates.

## Where things live

| Path in the app | On the host | Contents |
| --------------- | ----------- | -------- |
| `/homeassistant` | HA config folder (Samba `config` share) | Always mounted; also linked at `/config` when `config_access` is on |
| `/addon_config` | `/addon_configs/<repo>_claude-code/` | `CLAUDE_CONFIG_DIR`: `.claude.json`, `.credentials.json`, `settings.json`, `CLAUDE.md`, sessions; `ssh/` (see [SSH](#ssh)) |
| `/data/home` | private | `HOME`: shell history, `~/.gitconfig`, `~/.ssh`, `gh` login. Claude starts here unless `config_access` is on |

`CLAUDE_CONFIG_DIR=/addon_config` moves both `~/.claude/` **and**
`~/.claude.json` into the app config folder, so you can edit them with the
File editor, Samba, or Studio Code Server. Restart the app (or the Claude
session) after hand-editing `.claude.json`: a running Claude rewrites it.

On every start the app creates any of `.claude.json`, `.credentials.json`
and `settings.json` that are missing from `/addon_config` (see below; the
rest start as empty JSON objects). Claude Code itself adds its own state to
`.claude.json` as you use it. Existing files are never overwritten; delete
one to get the default back.

The app's own Home Assistant instructions (paths, `hab`, `ha`, the restart
guard) are written to `/etc/claude-code/CLAUDE.md` on every start, so they
follow the options; Claude Code loads them alongside your own
`/addon_config/CLAUDE.md`. An unedited `CLAUDE.md` seeded by an earlier
version of the app is removed once, so the two cannot contradict.

### Home Assistant MCP server

The default `.claude.json` registers Home Assistant's built-in MCP server
for every session (user scope), reached through the Supervisor proxy:

```json
{
  "mcpServers": {
    "ha": {
      "type": "http",
      "url": "http://supervisor/core/api/mcp",
      "headers": { "Authorization": "Bearer ${SUPERVISOR_TOKEN}" }
    }
  }
}
```

It needs the **Model Context Protocol Server** integration in Home
Assistant (Settings → Devices & services → Add integration); without it
`/mcp` shows `ha` as failed. Claude sees only the entities exposed to
Assist. `${SUPERVISOR_TOKEN}` is filled in at runtime — the token is never
written to disk. To drop it, run `claude mcp remove -s user ha`.

Common edits:

- `settings.json` — permissions, env vars, hooks ([settings docs][settings])
- `CLAUDE.md` — instructions applied to every session
- `.claude.json` → `mcpServers` — user-scoped MCP servers

## Login

Pick one:

1. **`/login` in the terminal.** When Claude prints the authorization
   link, a Home Assistant notification titled *Claude Code login* appears
   with a clickable copy of it, so you don't have to copy the long URL out
   of the terminal. Authorize, then paste the code back into the terminal.
   The session is saved in `/addon_config/.credentials.json`.
2. **`claude_code_oauth_token` option.** Run `claude setup-token` on any
   machine with a browser and paste the token into the app configuration.

## Configuration

| Option | Type | Default | Notes |
| ------ | ---- | ------- | ----- |
| `claude_code_oauth_token` | password | unset | Optional long-lived token; overrides the saved `/login` session. |
| `claude_code_version` | version | unset | Unset: latest release on every start. `2.1.300`: pin that version. |
| `config_access` | bool | `false` | Links the HA config folder at `/config` and starts Claude there, for editing YAML directly. Off: Claude starts in `HOME` and is told to use `hab` and the API instead (see below). |
| `enable_remote_control` | bool | `false` | Runs `claude --remote-control 'Home Assistant'` so the session can also be driven from the Claude app / claude.ai/code. The session starts at app boot, without opening the panel. Requires a `/login` session — a `claude setup-token` token cannot establish Remote Control. |
| `packages` | list | `[]` | Alpine packages installed on every start, e.g. `nodejs` + `npm` (for `npx`) or `uv` (for `uvx`). See [Extra tools for MCP servers](#extra-tools-for-mcp-servers). |
| `init_commands` | list | `[]` | Shell commands run in order on every start, after `packages` and before Claude starts. |
| `experimental_code_mode` | bool | unset (off) | Sets `CLAUDE_CODE_EXPERIMENTAL_CODE_MODE=1` for Claude Code's experimental Code Mode. A `"0"` in `settings.json`'s `env` still turns it off. Claude Code does not support Code Mode with Remote Control, so it has no effect while `enable_remote_control` is on (a warning is logged at startup). |
| `restart_guard` | bool | `true` | Runs `ha core check` before Claude restarts Home Assistant and blocks the restart on an invalid config (a `PreToolUse` hook in `settings.json`). |
| `statusline` | bool | `true` | Show the [claudebar][claudebar] statusline under the prompt (usage limits, context, cost). |
| `statusline_theme` / `statusline_style` | list | `tokyo-night` / `powerline` | The Nerd Font glyphs are bundled (see below), so every style works in any browser. |
| `statusline_segments` | list | claudebar's defaults | Order matters. `rate-limits` = 5-hour and weekly subscription usage. |
| `statusline_warn` / `statusline_crit` | % | `50` / `80` | Bar colour thresholds. |
| `statusline_weekly_show_at` | % | `75` | Show the weekly limit from this usage; `0` = always. |

## Home Assistant config folder

By default Claude does not work on the configuration files. It manages
Home Assistant through [`hab`][hab] and the APIs, the same way the UI
does, and starts in its home folder. Turn on `config_access` to link the
folder at `/config` and start Claude there instead, for YAML packages,
`configuration.yaml`, custom components and so on.

The folder stays mounted at `/homeassistant` either way: an app's mounts
are fixed and cannot follow an option. With `config_access` off, the
app's instructions tell Claude not to edit it, which steers Claude but
does not lock the folder away.

## Command-line tools

All of these are installed in the image:

- **`hab`** ([Home Assistant Builder][hab], Apache-2.0) — entities,
  devices, areas, automations, scripts, dashboards, helpers and more,
  through the HA API. Already authenticated with the app's
  `$SUPERVISOR_TOKEN`. Pinned to the image version; its update check is
  off.
- **`ha`** — the Home Assistant CLI, already authenticated, for
  `ha core check`, `ha core logs`, `ha apps restart …` and the like.
- **`gh`** — the GitHub CLI. Run `gh auth login` once in the terminal;
  the login is kept in `HOME`.
- **`git`** and **`ssh`** — see [SSH](#ssh) for keys.

### Extra tools for MCP servers

Many MCP servers are started with `npx` or `uvx`, which the image does
not include. List what they need in `packages` (Alpine package names,
installed with `apk add`) and any further setup in `init_commands`:

```yaml
packages:
  - nodejs
  - npm
  - uv
init_commands:
  - npm install -g @modelcontextprotocol/server-filesystem
```

The container is recreated on every start, so both run again each time,
after the rest of the setup (including the Claude Code install) and before
Claude starts; commands run with `bash -c` in `HOME`, each limited to 10
minutes. If a package cannot be installed or a command exits non-zero or
times out, the app stops with the error in its log. `npm install -g` goes
into the container, so it is redone on each start. Caches under
`HOME/.cache` (such as `uvx`'s) are left out of backups.

## SSH

Put SSH files into the `ssh` folder of the app config folder
(`/addon_configs/<repo>_claude-code/ssh/` over Samba or the File editor),
for example a private key `id_ed25519`, a `config` and a `known_hosts`.
On every start they are copied into `~/.ssh` with owner-only permissions,
replacing files of the same name, so git over SSH works without fixing
permissions by hand. Files only in `~/.ssh` (such as a key made with
`ssh-keygen` in the terminal) are kept. Restart the app after changing the
folder.

Claude runs commands without a terminal, so it cannot answer ssh's
first-connection host key prompt: add the host to `known_hosts` (for
example `ssh-keyscan github.com >> known_hosts`), or set
`StrictHostKeyChecking accept-new` for it in `config`.

## Restart guard

With `restart_guard` on, the app adds a `PreToolUse` hook for Bash to
`settings.json`. Before a command that restarts or rebuilds Home Assistant
(`ha core restart`, `hab system restart`, `curl …/core/restart`, the
`homeassistant.restart` service) it runs `ha core check`; if the check fails, the command is
blocked and the errors go back to Claude to fix first. It matches the
command text, so it prevents mistakes rather than enforcing a policy.
Turning the option off removes only this hook.

## Statusline

The app writes claudebar's `config.toml` from the options on every start
(edits made with `claudebar config` do not survive a restart) and adds
`"statusLine": {"type": "command", "command": "claudebar render"}` to
`/addon_config/settings.json`. If that file already has a different
`statusLine`, it is left alone; turning `statusline` off removes only
claudebar's entry. The 5-hour and weekly bars appear once Claude Code
reports them, which it does for Claude subscription logins.

## Font

The terminal page ships the [Symbols Nerd Font][nerd-fonts] (MIT), served
by the app itself, so powerline and Nerd Font glyphs (claudebar's
`powerline` style, git branch icons, …) render in any browser without
installing a font. Normal text uses your system's monospace font.

## Updates

On every start the app installs the latest Claude Code release from the npm
registry (only downloading when the version changed), or the version set in
`claude_code_version`. Builds are cached in `/data/claude-code/` and left
out of backups. If the download fails — offline, unknown version, checksum
mismatch, or a build that will not run — the last working build is used,
then the copy bundled in the image. Claude Code's own auto-updater is off.

To switch without restarting, run `claude-select [VERSION]` in the terminal
and start a new Claude session.

## Security

- Only Home Assistant ingress can reach the terminal: nginx admits the
  Supervisor (`172.30.32.2`) and loopback, ttyd listens on loopback only.
  No host port is published. The panel is admin-only.
- A custom AppArmor profile (`apparmor.txt`) confines the container: file
  access inside it stays broad so Claude can work, but extra capabilities,
  mounts, raw sockets and tracing other processes are denied.
- The terminal is a root shell with read/write access to your HA config
  (at `/homeassistant`, whatever `config_access` is set to),
  the Home Assistant REST API, and the Supervisor API with the `manager`
  role (`$SUPERVISOR_TOKEN`): it can check the config, restart Home
  Assistant, and read or control other apps. The Docker API is not
  available.
- `/addon_config/.credentials.json` holds your Claude login. The app
  config folder is visible over Samba and to apps that map
  `all_app_configs`; treat it, and the keys in its `ssh` folder, like
  password files.

## Copy and paste

- **Drag** to select: tmux copies the selection and the page puts it on
  the clipboard (a small "Copied" note appears). Claude Code's own "c to
  copy" works the same way. The mouse wheel scrolls the history.
- **Shift+drag** (macOS: **Option+drag**) makes a plain browser selection
  instead; copy it with Ctrl+C / Cmd+C.
- On Home Assistant over plain HTTP, browsers restrict clipboard access;
  the page falls back to a legacy copy, and if the browser still refuses,
  the note says so — use Shift/Option+drag then.

[claude-code]: https://docs.claude.com/en/docs/claude-code/overview
[settings]: https://docs.claude.com/en/docs/claude-code/settings
[claudebar]: https://github.com/micschr0/claudebar
[nerd-fonts]: https://github.com/ryanoasis/nerd-fonts
[hab]: https://github.com/balloob/home-assistant-build-cli
