# Browser

Browser control for Assist conversation agents, supplied over MCP (Model
Context Protocol). The agent can open pages, click, fill in forms, read the
page, take screenshots and upload files, in a Chromium browser that runs
inside the app. When a site needs a person — a login, a captcha, a second
factor — you do that step yourself in the app's panel, in the same browser.

## How it works

- **Chromium** runs in the app with a virtual display. Its profile is kept in
  the app's data, so logins survive restarts and are part of backups.
- **[Playwright MCP](https://github.com/microsoft/playwright-mcp)** drives
  Chromium and provides the `browser_*` tools.
- **A gate** in front of Playwright MCP serves streamable HTTP at `/mcp` on
  port 8099. Home Assistant opens a new MCP session for every tool call; the
  gate keeps one session to Playwright MCP, so the current tab, an open file
  chooser and the element references from a snapshot carry over from one
  call to the next.
- **The panel** in the sidebar shows the browser's screen and lets you use
  it (see [Logging in to sites](#logging-in-to-sites)).

## Connect to Home Assistant

1. Start the app. The log should show `[gate] playwright-mcp session ready`
   and `Announced MCP endpoint to Home Assistant.`
2. Go to **Settings → Devices & services**. A discovered **Model Context
   Protocol** entry appears; add it. (Discovery needs Home Assistant 2026.10
   or newer.)
3. Enable the new tools for your Assist conversation agent.

If nothing is discovered, add the **Model Context Protocol** integration by
hand. The app's log prints the URL to use when the announcement fails; it
has the form `http://<app hostname>:8099/mcp`.

No port mapping is needed. Map port 8099 only for an MCP client outside the
Home Assistant host. The endpoint has **no authentication**: anyone who can
reach a mapped port can drive the browser and its logged-in sites, so map
it only on a network you trust.

Home Assistant stops waiting for a tool after **30 seconds**. Page loads time
out after 20 s and other actions after 5 s, so a slow step fails with a
message instead of hanging. While a call runs, the gate sends a progress
message every 2 s so that clients with a short read timeout keep listening.

## Tools

All 25 tools of Playwright MCP are offered:

| Group | Tools |
|---|---|
| Navigate | `browser_navigate`, `browser_navigate_back`, `browser_tabs`, `browser_close`, `browser_resize` |
| Read the page | `browser_snapshot`, `browser_find`, `browser_take_screenshot`, `browser_console_messages`, `browser_network_requests`, `browser_network_request` |
| Act on the page | `browser_click`, `browser_type`, `browser_fill_form`, `browser_select_option`, `browser_press_key`, `browser_hover`, `browser_drag`, `browser_drop`, `browser_handle_dialog`, `browser_wait_for`, `browser_emulate_media` |
| Files | `browser_file_upload` |
| Run code in the page | `browser_evaluate`, `browser_run_code_unsafe` |

What the gate changes, so results stay usable by a voice assistant:

- **Snapshots** default to a depth of 6 when the agent does not ask for one.
  A full page can be hundreds of thousands of characters.
- **Results** longer than 12,000 characters are cut, with a note telling the
  agent to ask for a smaller depth or one part of the page.
- **Screenshots** are saved as files and never returned as images: Home
  Assistant passes tool results to the model as text, so an image would
  arrive as a very long base64 string.
- **Background tabs** do not render. Before clicking, typing, uploading or
  taking a screenshot, the gate brings the agent's tab to the front.
- If Playwright MCP stops, the next call returns `browser_restarted` and the
  agent starts again from `browser_navigate`. It never silently continues in
  a fresh browser.

## Logging in to sites

Open **Browser** from the sidebar (admins only). The panel shows the
browser's screen live:

1. Ask the agent to open the site, or click the screen and use the browser
   yourself.
2. Log in. Click the screen to type into the page.
3. For Korean text, or a long password, type it into the box at the top and
   press **Copy to browser**, then click the field in the page and press
   **Ctrl+V**. Typing Korean straight into the screen does not work: the
   virtual display has no Korean input method.
4. Ask the agent to continue. It uses the same browser and is now logged in.

Logins are kept in the browser profile in the app's data and survive app
restarts and updates. When the app stops, Chromium is closed cleanly so
that a login made just before is saved. If Chromium crashes, logins from
the last ~30 seconds can be lost.

**Reset profile** deletes all cookies and logins (it asks for a second
click). The agent and you share one browser: while the agent works, it
brings its own tab to the front, so do not use other tabs in the panel at
the same time.

The panel listens on port 8098 and accepts connections only from Home
Assistant's Ingress proxy.

## Files and /share

- Screenshots and other files the browser saves go to `/share/playwright/`.
  The tool result gives the path. A file name the agent asks for is kept,
  but always placed in that folder.
- `browser_file_upload` can upload any file under `/share`, for example a
  file the Code Interpreter app exported to `/share/code-interpreter/`.

## Using it with the other apps

The apps work on their own and also complement each other:

- **[CRW Web Tools](https://github.com/saya6k/ha-app-crw)** searches the web
  and reads a page quickly. Use it first; use this app when a page needs a
  login, clicks or JavaScript, or when you want a screenshot.
- **[Code Interpreter](https://github.com/saya6k/ha-app-code-interpreter)**
  can analyse a file downloaded with the browser, or produce a file that the
  browser then uploads to a web form. Files move through `/share`.

## Options

| Option | Default | Description |
|---|---|---|
| `allowed_origins` | empty | Origins the browser may load, e.g. `https://example.com`. Empty allows every site. A convenience filter, not a security boundary: it does not apply to redirects |
| `blocked_origins` | empty | Origins the browser must not load. Checked before `allowed_origins`; same caveat |
| `browser_language` | `en-US` | Chromium's language and the `Accept-Language` sent to sites, e.g. `ko-KR` |
| `font_languages` | empty | Download Noto Sans fonts for `ja`, `ko`, `zh-hans`, `zh-hant` at start (about 9–17 MB each, kept in the app's data). Without them, text in these scripts shows as empty boxes. Removing a language deletes its fonts |
| `outgoing_proxy` | empty | Proxy for all browser traffic, e.g. `http://10.0.0.2:3128` or `socks5://10.0.0.2:1080` |
| `viewport` | `1280x800` | Browser window size; screenshots of the visible area use it |

## Resources

The image is about 900 MB. With one page open the app uses roughly 800 MB
of memory (Chromium about 580 MB); more tabs and heavy pages use more. Ask
the agent to close tabs it no longer needs.

## Security

Read this before you log in to anything in this browser.

- **A web page can try to steer the agent.** Text on a page reaches the
  model, and a malicious page can try to make the agent act on your
  logged-in sites. Only log in to sites you are comfortable letting the
  agent use, keep `allowed_origins` short if you can, and watch the panel.
- **The browser can reach your network,** including Home Assistant itself
  and other devices on your LAN.
- **`browser_evaluate` and `browser_run_code_unsafe`** run code the model
  writes inside the page or against the browser.
- **Origin lists are not a security boundary.** They do not apply to
  redirects.
- The browser's remote-control port and the VNC server listen on the
  loopback interface only. The panel is reached only through Ingress, and the
  Supervisor token is not passed to the browser.
- The MCP endpoint has no authentication. It refuses requests that carry an
  `Origin` header, so web pages (including ones in this browser) cannot
  call it.

## Troubleshooting

- **`Timeout when calling tool`:** the step hit Home Assistant's 30 s
  limit. Ask for smaller steps, or check that the site loads at all.
- **`browser_restarted`:** the automation process restarted. The agent has
  to open the page again; logins are kept.
- **Text shows as empty boxes:** add the language to `font_languages` and
  restart the app.
- **The panel stays black or says "Disconnected":** press **Reconnect**. If
  it persists, check the app log for `[x11vnc]` or `[panel]` errors.
- **A login is gone:** Chromium may have crashed within ~30 s of the login;
  log in again in the panel.

## Licenses and trademarks

The app's source is at <https://github.com/saya6k/ha-app-playwright> under
the MIT license. The image bundles Chromium (BSD-3-Clause and others),
Playwright MCP and Playwright (Apache-2.0), noVNC (MPL-2.0), websockify
(LGPL-3.0), x11vnc (GPL-2.0) and Xvfb (MIT/X11). Fonts downloaded through
`font_languages` are Noto Sans CJK (SIL Open Font License 1.1).

"Playwright" is a trademark of Microsoft. This app is an independent
community project and is not affiliated with or endorsed by Microsoft.
