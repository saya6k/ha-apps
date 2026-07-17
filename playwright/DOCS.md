# Playwright Browser

Safe browser automation for Assist conversation agents over MCP.
Playwright drives a headless Chromium behind a domain allowlist; secret
values are injected bridge-side from 1Password or Bitwarden and **never
enter the conversation**. A live session viewer in the sidebar shows what
the browser is doing at all times.

> **Heads up: this is a big add-on (~1.7 GB installed).** It bundles a
> full Chromium browser. Expect a long first install, especially on
> SD-card based boards (Raspberry Pi class).

## Connecting Home Assistant

1. Install and start the add-on. Set at least `allowed_domains` — with
   the default empty list every navigation is rejected.
2. In Home Assistant, add the **Model Context Protocol** integration
   (Settings → Devices & services → Add integration → MCP).
3. Enter the endpoint URL:

   ```text
   http://03f32180-playwright:8099/mcp
   ```

4. Pick the integration's tools in your conversation agent (e.g.
   "Assist" pipeline with an LLM that supports tools).

Works side by side with the **CRW Web Tools** add-on — the recommended
setup registers both MCP servers: crw for read-only search/scraping,
playwright for interactive missions (logins, forms, clicks).

## Security model

- **Domain allowlist** — `browser_goto` only accepts `https://` URLs on
  the domains you list (subdomains included). The final URL after every
  redirect *and after every click* is re-checked; leaving the allowlist
  closes the session. An empty list (the default) rejects everything.
- **Secrets never pass through the LLM** — the agent only ever sees
  secret *names* (via the `secret_names` tool) and sends placeholders
  like `{{secret:op://Vault/Item/password}}` in `browser_fill` /
  `browser_type`. The bridge resolves the placeholder at injection time;
  tool results, logs, and error messages are scrubbed of the value and
  any page echo of it. There is no tool that returns a secret value.
- **Minimal surface** — one exposed endpoint (`:8099`, not published to
  the host by default; Home Assistant reaches it over the internal
  network). JavaScript evaluation and screenshots are disabled unless
  you opt into `advanced_tools`.
- **Session viewer** — the sidebar panel (admin-only, behind Home
  Assistant's ingress authentication) streams a live view of the
  browser, the current URL, a timeline of tool calls (arguments as the
  agent sent them — placeholders, not values), and an **End session**
  button that kills the browser instantly. Password fields appear
  masked, exactly as the browser renders them.

## Secret providers

| Provider | Token | Reference format |
|---|---|---|
| `local` | – (reads `local_secrets`) | `<site>/id`, `<site>/pw` |
| `1password` | Service Account token (`onepassword_token`) | `op://<vault>/<item>/<field>` |
| `bitwarden` | Secrets Manager machine account token (`bitwarden_access_token`) | secret UUID |

> ⚠️ **`local` is for testing only.** Entries in `local_secrets` are
> stored in plain text in the add-on configuration. The values are still
> never shown to the conversation agent — it only sees the `<site>/id` /
> `<site>/pw` references — but real credentials belong in 1Password or
> Bitwarden. The default entry matches the public login demo at
> `the-internet.herokuapp.com` so you can try user story 1 end to end
> out of the box.

- 1Password: `secret_names` lists `op://vault/item` references — append
  the field (`/username`, `/password`, …) in the placeholder.
- Bitwarden: set `bitwarden_server_url` for self-hosted instances.
  `secret_names` additionally needs `bitwarden_organization_id`
  (resolving by UUID works without it). Personal vaults and Vaultwarden
  are not supported — Secrets Manager only.

## Options

| Option | Default | Notes |
|---|---|---|
| `advanced_tools` | `false` | Adds `browser_evaluate` (arbitrary JS) and `browser_screenshot` |
| `allowed_domains` | `[the-internet.herokuapp.com]` | **Required for any use.** HTTPS-only, subdomains included; the default entry is the public demo site |
| `bitwarden_access_token` | – | Secrets Manager machine token |
| `bitwarden_organization_id` | – | Only needed for `secret_names` listing |
| `bitwarden_server_url` | `https://vault.bitwarden.com` | Self-hosted supported |
| `local_secrets` | demo entry | ⚠️ Testing only — plain-text site/id/pw entries for the `local` provider |
| `onepassword_token` | – | Service Account token |
| `persist_session` | `false` | Keep cookies/storage between sessions (inside `/data` only) |
| `secret_provider` | `local` | Where placeholders resolve; `local` is testing-only |
| `session_idle_timeout` | `300` | Seconds before an idle browser session closes |

## Release checklist (HA end-to-end)

Manual verification on a real Home Assistant instance before/after each
release — mirrors SPEC success criteria 3 and 4:

1. Register the MCP integration and ask the assistant to log into an
   allowlisted site using `{{secret:...}}` credentials and read some
   account data back.
2. Confirm the answer contains the data but **the conversation log and
   the add-on log contain no secret value** (search both for the value).
3. Ask for a site outside the allowlist — the agent must report the
   denial and have no way around it.
4. While the agent works, open the sidebar panel: live frames and the
   tool timeline update; **End session** cuts the browser off
   immediately.

## Troubleshooting

- **Every `browser_goto` is denied** — `allowed_domains` is empty or the
  site is `http://`. Add the domain; only HTTPS is supported.
- **`secret_names` is missing** — `secret_provider` is `none`, or (for
  listing with Bitwarden) `bitwarden_organization_id` is unset.
- **Viewer shows "no session"** — sessions close after
  `session_idle_timeout` seconds of inactivity, when the agent calls
  `browser_close`, or when navigation leaves the allowlist.
- **Slow first response** — the browser session starts lazily on the
  first `browser_goto` after idle; Chromium startup takes a few seconds.
