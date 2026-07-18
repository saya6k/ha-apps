# Playwright Browser

Safe browser automation for Assist conversation agents over MCP.
Playwright drives a headless Chromium behind a domain allowlist; secret
values are injected bridge-side from 1Password or Bitwarden and **never
enter the conversation**. A live session viewer in the sidebar shows what
the browser is doing at all times.

> **Heads up: this is a big add-on (~1.9 GB installed).** It bundles a
> full Chromium browser and the Bitwarden CLI. Expect a long first
> install, especially on SD-card based boards (Raspberry Pi class).

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

The agent-facing contract is provider-agnostic: `secret_names` returns
opaque references, and the agent copies one into a `{{secret:...}}`
placeholder. Login items expose the same canonical fields everywhere —
`/username`, `/password`, and `/totp` where the backend supports it —
so switching providers never changes how conversations work.

| `secret_provider` | Backend | Credentials | Reference format |
|---|---|---|---|
| `local` | add-on config (testing only) | – (reads `local_secrets`) | `<site>/username`, `<site>/password` (also `/id`, `/pw`) |
| `1password` | 1Password cloud | Service Account token (`onepassword_token`) | `op://<vault>/<item>/<field>` |
| `1password-connect` | self-hosted 1Password Connect | `onepassword_connect_host` + `onepassword_connect_token` | `op://<vault>/<item>/<field>` |
| `bitwarden` | Bitwarden Secrets Manager (cloud or self-hosted) | machine account token (`bitwarden_access_token`) | secret UUID |
| `bitwarden-vault` | **personal vault** — bitwarden.com, self-hosted, **Vaultwarden** | personal API key (`bitwarden_client_id` + `bitwarden_client_secret`) + `bitwarden_master_password` | `<item>/username\|password\|totp\|uri\|custom:<field>` |

> ⚠️ **`local` is for testing only.** Entries in `local_secrets` are
> stored in plain text in the add-on configuration. The values are still
> never shown to the conversation agent, but real credentials belong in
> 1Password or Bitwarden. The default entry matches the public login
> demo at `the-internet.herokuapp.com`.

### Bitwarden personal vault / Vaultwarden (`bitwarden-vault`)

- Uses the official Bitwarden CLI bundled in the image. Its state
  (an encrypted vault copy and auth tokens) lives **only in tmpfs
  (memory)** — nothing is ever written to disk; the session key stays in
  process memory and is masked from all output.
- Get your personal API key from the web vault: **Settings → Security →
  Keys → View API key** (`client_id` is `user.xxxxxxxx…`).
- **SSO organizations:** interactive SSO login is not possible for a
  headless add-on and is not needed — personal API keys work for SSO
  accounts too, and unlocking always uses your master password.
- **HTTPS is required.** The Bitwarden CLI refuses plain-http server
  URLs. If your Vaultwarden uses a self-signed or private-CA
  certificate, paste the PEM into `bitwarden_ca_cert`.
- `<item>/totp` resolves the item's current TOTP code — two-factor
  logins can be automated end to end.

### Passkeys (WebAuthn) and Sign in with Apple

With `passkeys: true` and the `bitwarden-vault` provider, passkeys
stored in your vault are injected into an **in-memory virtual
authenticator** when a browser session starts. Sites that ask for a
passkey get an answer automatically — no new tools, the normal
goto/click flow just works.

- The add-on is a passkey **client only**: it can sign in with existing
  vault passkeys but can never create, modify, or export one. Keys are
  never written to disk.
- **Sign in with Apple:** works when your Apple ID has a passkey (add
  one from an Apple device first, stored in Bitwarden). Add
  `appleid.apple.com` to `allowed_domains` — the sign-in popup is
  allowlist-checked like every page. The password + trusted-device 2FA
  flow can **not** be automated headlessly.
- Other providers (1Password, Secrets Manager, local) cannot supply
  passkey key material — `passkeys` has no effect with them.
- **Limitation:** sites that open a browser "account picker" without
  identifying the account first (an empty-allowCredentials /
  discoverable-only flow) don't work in headless Chromium. Sites that
  ask for your username/email first — including Apple — send an explicit
  credential list and work fine.

## Options

| Option | Default | Notes |
|---|---|---|
| `advanced_tools` | `false` | Adds `browser_evaluate` (arbitrary JS) and `browser_screenshot` |
| `allowed_domains` | `[the-internet.herokuapp.com]` | **Required for any use.** HTTPS-only, subdomains included; the default entry is the public demo site |
| `bitwarden_access_token` | – | Secrets Manager machine token (`bitwarden` provider) |
| `bitwarden_ca_cert` | – | PEM cert to trust for self-signed/private-CA HTTPS (`bitwarden-vault`) |
| `bitwarden_client_id` | – | Personal API key client_id (`bitwarden-vault`) |
| `bitwarden_client_secret` | – | Personal API key client_secret (`bitwarden-vault`) |
| `bitwarden_master_password` | – | Vault unlock password (`bitwarden-vault`) — memory only, masked everywhere |
| `bitwarden_organization_id` | – | Only needed for `secret_names` listing (`bitwarden`) |
| `bitwarden_server_url` | `https://vault.bitwarden.com` | Shared by both Bitwarden providers; https only |
| `local_secrets` | demo entry | ⚠️ Testing only — plain-text site/id/pw entries for the `local` provider |
| `onepassword_connect_host` | – | Self-hosted Connect server URL (`1password-connect`) |
| `onepassword_connect_token` | – | Connect access token (`1password-connect`) |
| `onepassword_token` | – | Service Account token (`1password`) |
| `passkeys` | `false` | Sign in with vault passkeys (`bitwarden-vault` only) |
| `persist_session` | `false` | Keep cookies/storage between sessions (inside `/data` only) |
| `secret_provider` | `local` | Where placeholders resolve; `local` is testing-only |
| `session_idle_timeout` | `300` | Seconds before an idle browser session closes |

All secret-bearing options can instead be supplied as environment
variables (`ONEPASSWORD_TOKEN`, `OP_CONNECT_HOST`, `OP_CONNECT_TOKEN`,
`BITWARDEN_ACCESS_TOKEN`, `BW_CLIENTID`, `BW_CLIENTSECRET`,
`BW_MASTERPASSWORD`, …) when running the image outside Home Assistant —
**environment variables always win over options**, so credentials never
have to live in a file.

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
  listing with Bitwarden Secrets Manager) `bitwarden_organization_id`
  is unset.
- **`bitwarden-vault` fails to start** — the server URL must be
  `https://` (the Bitwarden CLI refuses http). Self-signed cert? Put the
  PEM in `bitwarden_ca_cert`. Also check all three of client_id,
  client_secret, and master password are set.
- **Passkey login does nothing** — `passkeys: true` requires the
  `bitwarden-vault` provider, and the passkey's site (rpId) must be in
  `allowed_domains` (for Apple: `appleid.apple.com`).
- **Viewer shows "no session"** — sessions close after
  `session_idle_timeout` seconds of inactivity, when the agent calls
  `browser_close`, or when navigation leaves the allowlist.
- **Slow first response** — the browser session starts lazily on the
  first `browser_goto` after idle; Chromium startup takes a few seconds.
