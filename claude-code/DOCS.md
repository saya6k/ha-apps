# Claude Code app — Documentation

Runs Anthropic's [Claude Code][claude-code] CLI in a browser terminal
(ttyd + tmux) inside the Home Assistant **ingress** side panel. The CLI is
baked into the image; the login and every Claude Code setting persist
across restarts and updates.

## Where things live

| Path in the app | On the host | Contents |
| --------------- | ----------- | -------- |
| `/config` | HA config folder (Samba `config` share) | Working directory Claude starts in |
| `/addon_config` | `/addon_configs/<repo>_claude-code/` | `CLAUDE_CONFIG_DIR`: `.claude.json`, `.credentials.json`, `settings.json`, `CLAUDE.md`, sessions |
| `/data/home` | private | `HOME`: shell history, `~/.gitconfig`, `~/.ssh` |

`CLAUDE_CONFIG_DIR=/addon_config` moves both `~/.claude/` **and**
`~/.claude.json` into the app config folder, so you can edit them with the
File editor, Samba, or Studio Code Server. Restart the app (or the Claude
session) after hand-editing `.claude.json`: a running Claude rewrites it.

On every start the app creates any of `.claude.json`, `.credentials.json`,
`settings.json` and `CLAUDE.md` that are missing from `/addon_config`
(see below; the rest start as empty JSON objects or a three-line Home
Assistant `CLAUDE.md`). Claude Code itself adds its own state to
`.claude.json` as you use it. Existing files are never overwritten; delete
one to get the default back.

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
| `claude_code_oauth_token` | password | empty | Optional long-lived token; overrides the saved `/login` session. |
| `claude_code_version` | version | unset | Unset: latest release on every start. `2.1.300`: pin that version. |
| `enable_remote_control` | bool | `false` | Runs `claude --remote-control 'Home Assistant'` so the session can also be driven from the Claude app / claude.ai/code. The session starts at app boot, without opening the panel. Requires a `/login` session — a `claude setup-token` token cannot establish Remote Control. |
| `experimental_code_mode` | bool | `false` | Sets `CLAUDE_CODE_EXPERIMENTAL_CODE_MODE=1` for Claude Code's experimental Code Mode. A `"0"` in `settings.json`'s `env` still turns it off. |
| `statusline` | bool | `true` | Show the [claudebar][claudebar] statusline under the prompt (usage limits, context, cost). |
| `statusline_theme` / `statusline_style` | list | `tokyo-night` / `unicode` | `powerline`, `lean` and `rounded` need a Nerd Font in the browser. |
| `statusline_segments` | list | claudebar's defaults | Order matters. `rate-limits` = 5-hour and weekly subscription usage. |
| `statusline_warn` / `statusline_crit` | % | `50` / `80` | Bar colour thresholds. |
| `statusline_weekly_show_at` | % | `75` | Show the weekly limit from this usage; `0` = always. |

## Statusline

The app writes claudebar's `config.toml` from the options on every start
(edits made with `claudebar config` do not survive a restart) and adds
`"statusLine": {"type": "command", "command": "claudebar render"}` to
`/addon_config/settings.json`. If that file already has a different
`statusLine`, it is left alone; turning `statusline` off removes only
claudebar's entry. The 5-hour and weekly bars appear once Claude Code
reports them, which it does for Claude subscription logins.

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
- The terminal is a root shell with read/write access to your HA config,
  the Home Assistant REST API, and the Supervisor API with the `manager`
  role (`$SUPERVISOR_TOKEN`): it can check the config, restart Home
  Assistant, and read or control other apps. The Docker API is not
  available.
- `/addon_config/.credentials.json` holds your Claude login. The app
  config folder is visible over Samba and to apps that map
  `all_app_configs`; treat it like a password file.

## Copy and paste

tmux mouse mode is on (the wheel scrolls history). Hold **Shift** (macOS:
**Option**) while dragging to select text for the browser clipboard.

[claude-code]: https://docs.claude.com/en/docs/claude-code/overview
[settings]: https://docs.claude.com/en/docs/claude-code/settings
[claudebar]: https://github.com/micschr0/claudebar
