# Code Interpreter

A sandboxed code runner for Assist conversation agents, supplied over MCP
(Model Context Protocol). The agent writes one JavaScript script per call:
it can read and control Home Assistant, filter the results in code, run
Python for analysis and charts, and exchange files with you through
`/share`. Variables persist between calls of a session.

## How it works

- **One tool, a whole script:** instead of one tool call per step, the agent
  sends a script to `run_code`. The script calls Home Assistant, the shell
  and files through globals, and returns only what the agent needs. Fewer
  round trips, and large data (all entity states, a CSV) stays in the
  sandbox instead of the conversation.
- **MCP server:** streamable HTTP at `/mcp` on port 8099. Home Assistant's
  **Model Context Protocol** integration connects to it, and the app
  announces itself through Supervisor discovery.
- **One sandbox per session:** each session runs in its own
  [bubblewrap](https://github.com/containers/bubblewrap) sandbox inside the
  app container. A JavaScript (Node 26) REPL keeps the session's variables
  until the session ends.
- **Python for analysis:** the sandbox has Python with numpy, pandas, scipy,
  statsmodels, scikit-learn, sympy, networkx, matplotlib (Korean labels work
  out of the box), seaborn, openpyxl, xlsxwriter, pyarrow, pillow, lxml,
  beautifulsoup4, python-docx, fpdf2, pypdf, pdfplumber, pyyaml and
  tabulate. Scripts run it with `` $`python3 …` ``.
- **Home Assistant through its MCP Server:** the app, not the sandbox, calls
  Home Assistant, and only with what the person in the conversation may use
  (see [Home Assistant access](#home-assistant-access)).
- **Sessions end on their own:** a session is closed after
  `idle_timeout_minutes` without a call, and its variables and files are
  discarded.

The app runs with **protection mode on**. It needs no Docker access and no
extra privileges.

## Connect to Home Assistant

1. Start the app. The log should show `sandbox self-check ok`, a `[hamcp]`
   line with the Home Assistant tools it found, and
   `Announced MCP endpoint to Home Assistant.`
2. Go to **Settings → Devices & services**. A discovered **Model Context
   Protocol** entry appears; add it. (Discovery needs Home Assistant
   2026.10 or newer.)
3. For `ha.*` in scripts, add the **Model Context Protocol Server**
   integration too (it is what the app calls). Without it, scripts still run
   but `ha.*` answers `HaUnavailable`.
4. Enable the new tools for your Assist conversation agent. The agent can
   already control devices through this app, so you can leave its own
   **Assist** API off; with both on, it sees the same Home Assistant tools
   twice.

If nothing is discovered, add the **Model Context Protocol** integration by
hand. The app's log prints the URL to use when the announcement fails; it
has the form `http://<app hostname>:8099/mcp`. Added by hand, Home
Assistant does not tell the app who is speaking, so `ha.admin` is never
available that way.

No port mapping is needed. Map port 8099 only for an MCP client outside the
Home Assistant host.

## Tools

| Tool | What it does |
|---|---|
| `run_code` | Run a JavaScript script in the session's sandbox. Returns `result` (the last expression), `logs` (console output; error output marked `[stderr]`), `error` and `message` if it threw, `new_files` under `/sandbox`, and `kernel_restarted` |
| `list_sessions` / `close_session` | See and end your own sessions |

Top-level `await` works, and `const`, `let`, `function` and `class` declared
at the top level stay defined for later calls. A call without `session_id`
continues the speaker's latest open session (the result says
`resumed: true`), so variables carry over between turns even when the agent
does not pass the id back; `reset: true` starts clean. Calls with no user (a
voice satellite, a client outside Home Assistant) always start a new
session. When a session has expired, a call with its `session_id` returns
`session_not_found`; the agent never silently continues in a fresh one.

### In a script

| Global | What it does |
|---|---|
| `ha.tools()` | The Home Assistant tools this person may use |
| `ha.<domain>.<tool>(args)` | Call one, e.g. `ha.intent.HassTurnOff({name: "Kitchen light"})`; `ha.call("light__HassLightSet", args)` takes the full name. `ha.homeassistant.GetLiveContext()` returns Home Assistant's text as `result` and the same entities parsed as `entities` (`names`, `domain`, `state`, `areas`, `attributes`), so scripts filter objects instead of matching text |
| `ha.admin` | Administrators only: read-only Home Assistant tools (see below) |
| `ha.admin.hab(argv, {stdin})` | Administrators only: the Home Assistant Builder CLI, for example `["automation", "get", "night"]`; changes need `hab_allow` (see [Editing with hab](#editing-with-hab)) |
| `` $`cmd ${x}` `` | Run `sh -c` in `/sandbox`; values are quoted. `.text()`, `.lines()`, `.json()`, `.nothrow()`, `.timeout(ms)`; a failing command throws `ShellError` |
| `file(p)`, `write(p, s)` | Read (`.text()`, `.json()`, `.lines()`, `.exists()`) and write files; relative paths are under `/sandbox` |
| `share.list(dir)`, `share.import(path, dest)`, `share.export(path)` | Home Assistant's `/share` (see [Files and /share](#files-and-share)) |
| `plugins.<server>.<tool>(args)` | MCP servers Home Assistant connects to, if the app allows this person any (see [Plugins](#plugins)); `plugins.tools()` lists them, `plugins.call(name, args)` takes a full name. Undefined otherwise |
| `skills.list()`, `skills.<name>(args)` | The speaker's saved skills (see [Skills](#skills)); only approved ones run |
| `sleep(ms)`, `log(...)`, `require(name)` | Waiting, logging, Node's built-in modules |

There is no npm: only Node's built-ins and the preinstalled Python packages
are available. There is no `/proc` (`process.memoryUsage()` and `psutil`
do not work), and a script can start at most one worker thread.

### Time limit per call

Home Assistant ends every tool call after **30 seconds**. `run_code`
defaults to `timeout_s: 25`, so a long script is interrupted by the app
first and its variables are kept. A loop that runs after an `await` cannot
be interrupted; the REPL is then restarted, which loses the variables but
keeps the files. Work that needs more than about 25 seconds (a large
download, long model training) cannot finish in one call through Home
Assistant: ask the agent to split it into steps.

## Home Assistant access

Scripts call Home Assistant's **Model Context Protocol Server** integration
through the app. The app's Supervisor token stays in the app; the sandbox
only asks the app to make a call.

| Who is speaking | `ha.*` | `ha.admin` |
|---|---|---|
| An administrator | Assist API: the entities exposed to Assist, like the Assist conversation agent | The **read-only** tools of the Home Assistant API: logs, history and statistics, automation traces, configuration (automations, scripts, scenes, areas, devices, config entries), repairs, templates |
| Anyone else, or no user (a voice satellite, a client outside Home Assistant) | Assist API | Not defined |

- Who is speaking comes from Home Assistant: it tells servers found through
  Supervisor discovery which user the conversation belongs to. An
  administrator is an active user in the Administrators group; system users
  (Supervisor, other apps) never count, so a command relayed by another app
  is treated as non-admin.
- `ha.admin` cannot change anything: `call_action`, configuration changes,
  repairs and energy settings are left out. Templates and history are not
  limited to exposed entities, and logs can contain secrets: whatever a
  script reads can reach the conversation agent (and, for a cloud agent, its
  provider).
- What the Assist API may do follows your Home Assistant settings: exposed
  entities, and the MCP Server integration's own **read-only** option.
- A script may make **50** Home Assistant calls per run. A `run_code` that
  arrives while the same user's Home Assistant call is still running (a
  script or tool that asks the conversation agent again) is refused as
  `nested_call`.
- Sessions belong to the person who started them: another user's
  `session_id` is `session_not_found`.
- Home Assistant does not pass on which satellite heard a command, so
  "turn off the light here" cannot be resolved; name the room or device.

### Editing with hab

`ha.admin.hab()` runs [Home Assistant Builder](https://github.com/balloob/home-assistant-build-cli)
(`hab`) in the app for administrators. It can read and edit automations,
scripts, scenes, dashboards, helpers, to-do lists and more, which the
Home Assistant API above cannot.

Its permissions work like Claude Code's Code Mode in `dontAsk` mode, made for
runs that nobody can approve while they happen:

- Every `hab` call is checked on its own. Commands `hab` marks as reading
  run. Commands that change something run only if a rule in `hab_allow`
  matches; by default the list is empty, so nothing is changed.
- A rule is the command as typed, with `*` for any rest:
  `automation update *`, `script create *`, `dashboard *`. A rule in
  `hab_deny` wins over `hab_allow`.
- Some commands no rule can allow: accounts and users, apps, backups,
  updates, the host, network, ESPHome, integrations, running actions
  directly (`action call`, `automation run`, `script run`,
  `scene activate`, `event fire`) and `assist` (it would call the agent
  again).
- `-f`/`--file`, `--url`, `--config` and token flags are refused: data goes
  in with `-d` or `{stdin}`.
- Every call is audited as `ha.hab` with its arguments; refusals as
  `policy.violation`.

```yaml
hab_allow:
  - automation create *
  - automation update *
  - script update *
hab_deny:
  - automation update alarm_*
```

An allowed automation or script can later run any action when it triggers:
allowing `automation update *` lets the agent decide what your automations
do. Allow only what you want the agent to change, and read the `ha.hab`
entries in the audit log.

A script can do in one call what took the agent many: turning off every
light in a loop, for example. That is the point, but it also means a
misunderstood request, or instructions planted in a device's name, acts on
everything exposed at once. Expose to Assist only what the agent should
control.

## Skills

With `skill_workflow` on, the app learns reusable functions from finished
sessions:

1. When a known user's session ends (idle, closed or replaced), the app
   takes the code that ran without errors and did real work, at most the
   last 8 runs, and sends it to an **AI Task** entity
   (`skill_ai_task_entity`, or Home Assistant's preferred one) with the
   user's existing skills.
2. The AI Task decides whether one task is worth keeping and rewrites it as a
   general function with parameters, for example `turn_off_lights_except({
   except: "거실" })`.
3. The proposal is stored **pending** for that user only, and Home Assistant
   shows a notification that a skill waits for approval (only the user and
   the skill's name: every user sees notifications). An administrator reads the code in the
   panel's **Skills** section and approves or rejects it; that clears the
   notification. A new proposal for an existing skill waits beside the
   approved version until it is approved.
4. Scripts see their user's skills with `skills.list()` and run approved
   ones as `skills.<name>(args)`, with the same permissions as any other
   code.

### Asking for a skill

An administrator can also ask for a skill directly, from an automation, a
script or **Developer tools → Actions**:

```yaml
action: hassio.app_stdin
data:
  app: <this app's slug, e.g. 03f32180_code-interpreter>
  input:
    type: skill.request
    user: Bob            # name, username or user id of the skill's owner
    request: Turn off every light except the living room's
```

The AI Task writes the skill from the request, using only the Home Assistant
tools that user can call, and it is stored pending like any other proposal.
The action returns nothing; the outcome is in the audit log
(`skill.requested`, then `skill.proposed` or `skill.review`). A name that
matches no user or several users is refused: use the username then. Requests
are ignored while `skill_workflow` is off.

### What a skill uses

Each proposal lists what it calls (`uses`): Home Assistant tools, plugin
tools, and hab commands for administrators. The panel shows the list, and warns about calls
in the code that the list leaves out, or that go through a variable and
cannot be read. The list helps you review; it is **not** a permission. An
approved skill always runs with the rights of the person whose script runs
it, no more.

Calls with no user never propose skills. Nothing is sent while
`skill_workflow` is off (the default). The AI Task reads code that came from
conversations, and requests that anyone could have written, so it can be
misled like any model; that is why nothing runs before an administrator
approves it. Requests, proposals, reviews, approvals and uses are in the
audit log (`skill.*`).

## Plugins

Home Assistant's **Model Context Protocol** integration connects to other MCP
servers (a memory store, a web service, …), and Home Assistant's MCP Server
offers each one's tools to the app. List the ones scripts may use in
`plugins`:

```yaml
plugins:
  - name: Memory          # the integration entry's title in Settings → Devices & services
    access: all           # all = every Home Assistant user, admin = administrators only
```

Scripts then call `plugins.memory.search({query: "…"})` (the tool
`memory__search`); for a server name that is not a JavaScript name, write
`plugins["multi-service-mcp"].find_places(args)`. `plugins.tools()`
lists the tools the speaker may use; with none, `plugins` is undefined.

- The app calls the servers through Home Assistant, so their credentials
  stay in Home Assistant and the sandbox needs no network.
- Calls with no user (a voice satellite, a client outside Home Assistant)
  never get plugins. `access: admin` plugins are checked on every call.
- A plugin's tools run with no Home Assistant user behind them: the server
  sees the same caller for everyone. Only list servers whose tools every
  allowed person may use, including tools that write (`memory__save`).
- Plugin answers go back to the model; a server that returns text written
  by others can carry instructions. Every call is in the audit log
  (`plugin.call`) and counts toward the 50 calls per run.
- An entry that is not loaded, whose title matches several entries, or that
  is this app itself is left out with a warning in the log. The log's
  `[plugins]` line at startup shows which are available.

## Files and /share

Each session has a private `/sandbox` (256 MB) and `/tmp` (64 MB). Both live
in memory and are gone when the session ends; nothing is written to the Home
Assistant data disk.

- To give the agent a file, put it in `/share` (for example with the Samba
  or File editor app). A script can look for it with `share.list()` and
  copy it in with `share.import()`. `share.list()` shows file names in
  `/share` to the agent (and, for a cloud agent, its provider).
- `share.export(path)` copies a file to `export_dir/<session>/` (default
  `/share/code-interpreter`). Name clashes get `-1`, `-2` suffixes; nothing
  is overwritten.
- Paths outside `/share`, symlink escapes and files over `max_file_mb` are
  refused.

## Network

By default the sandbox has **no network at all**: no internet, no Home
Assistant, no LAN, no DNS. (`ha.*` works regardless: the app makes those
calls.)

To let code reach specific hosts (for example to `pip install` a missing
package), list them in `network_allowlist`:

```yaml
network_allowlist:
  - pypi.org
  - "*.pythonhosted.org"
```

Entries are `host` or `host:port` (port 443 if omitted); `*.domain` matches
subdomains only. Traffic goes through an HTTPS proxy in the app that allows
only the listed hosts, and only when they resolve to public addresses.
Plain HTTP, IP addresses and everything else are refused. Invalid entries
are ignored with an error in the log. `fetch()` in scripts and Python both
use the proxy.

To allow the whole internet, use `"*"` (quoted, any host on port 443; add
`"*:8080"` and so on for other ports):

```yaml
network_allowlist:
  - "*"
```

Even then, only public addresses are reachable: Home Assistant, your LAN and
IP addresses stay refused, and every connection is in the audit log. Code in
the sandbox comes from the conversation, so `"*"` also lets it send what it
reads (`/share` imports, Home Assistant state) to any server; prefer listing
hosts.

## Options

| Option | Default | Description |
|---|---|---|
| `idle_timeout_minutes` | `20` | Close a session after this many minutes without a call |
| `max_sessions` | `3` | Sessions at once; the least recently used idle session is closed to make room |
| `memory_limit_mb` | `2048` | Address-space limit per sandbox process (`RLIMIT_AS`, minimum 1024). This counts reserved memory, so real use is lower |
| `network_allowlist` | empty | Hosts the sandbox may reach over HTTPS (see above); `"*"` = any public host. Empty = no network |
| `max_file_mb` | `20` | Largest file for `share.import` and `share.export` |
| `export_dir` | `/share/code-interpreter` | Where `share.export` puts files; must be under `/share` |
| `audit_retention_days` | `30` | Days of audit log to keep |
| `hab_allow` | empty | `hab` commands that may change Home Assistant (see [Editing with hab](#editing-with-hab)) |
| `hab_deny` | empty | `hab` commands refused even if `hab_allow` matches |
| `skill_workflow` | `false` | Propose skills from finished sessions through an AI Task (see [Skills](#skills)) |
| `skill_ai_task_entity` | empty | AI Task entity for the review; empty = Home Assistant's preferred one |
| `plugins` | empty | MCP servers scripts may call, each with `access: all` or `admin` (see [Plugins](#plugins)) |

## Security model

The sandbox is meant to contain code an LLM writes. It is **not** a virtual
machine: sandboxes share the host kernel.

Inside a sandbox, code:

- runs as an unprivileged user with no capabilities, in its own user, PID,
  network, IPC and mount namespaces;
- sees a read-only system and only its own `/sandbox` and `/tmp`, with no
  `/proc`;
- cannot see the app's files, `/share`, `/config`, the Supervisor token or
  other sessions; `/share` and Home Assistant are reached only through calls
  the app checks;
- is filtered by seccomp (no nested namespaces, no `bpf`, `ptrace`,
  `keyctl`, `io_uring`, …) and runs under the app's AppArmor profile;
- has limits on memory (`memory_limit_mb`), processes, open files and file
  size. Math libraries use 2 threads, and sandboxes run at a lower CPU
  priority. Under memory pressure the kernel ends sandboxes before the app.

If the sandbox cannot be set up as described, the app refuses to run code
(fail closed) and logs why at startup.

## Sessions & audit panel

Opening the app from the sidebar (**Code Interpreter**, admins only) shows a
panel served through Home Assistant Ingress:

- **Live sessions** of every user, with their idle expiry and the current
  settings. **Close** ends a session at once; who closed it is written to the
  audit log as `ui.close_session`.
- **Audit log** by day: one row per session with its code runs, Home
  Assistant calls, file transfers, network connections (allowed / denied),
  errors and policy violations. Click a session for its event timeline,
  including the code that ran. `#day=YYYYMMDD&session=<id>` links straight
  to a session.

The panel listens on port 8098 and accepts requests only from Home
Assistant's Ingress proxy.

## Audit log

Every session, code run, Home Assistant call (`ha.call`, with the tool and
its arguments), file transfer, network connection and refused action is
recorded in `/data/audit/audit-YYYYMMDD.jsonl` (kept for
`audit_retention_days`, included in backups). The log keeps the code that
ran but never its output or a Home Assistant result, only their size. Each
record also shows as a one-line `[audit]` summary in the app log.

## Troubleshooting

- **`sandbox self-check FAILED` in the log:** the host does not allow the
  sandbox (for example a kernel without user namespaces). `run_code`
  returns `sandbox_unavailable` until this is fixed; the log line says why.
- **`HaUnavailable` from `ha.*`:** add the **Model Context Protocol
  Server** integration; the message says what failed.
- **`ha.admin` is undefined for an administrator:** the Model Context
  Protocol integration was added by hand instead of from discovery, or the
  user is not in the Administrators group.
- **`NotAllowed` from `ha.admin.hab()`:** the command changes Home
  Assistant and no `hab_allow` rule matches it, or it is one no rule can
  allow; the message says which.
- **`nested_call`:** a Home Assistant tool called by a script asked the
  conversation agent again. Avoid exposing such scripts to Assist.
- **`Timeout when calling tool`:** the call ran into Home Assistant's 30 s
  limit. Ask for shorter steps.
- **`KernelDied`:** the REPL process ended (out of memory, a native crash).
  Its last error output is at the end of `logs`. Variables are lost and
  files are kept.
- **`MemoryError` in Python, or `RangeError` / `Fatal process out of
  memory` in JavaScript:** raise `memory_limit_mb`.
- **A Python package is missing:** add `pypi.org` and `*.pythonhosted.org`
  to `network_allowlist` and let the agent run `pip install` (keep each
  install under 25 s).

## Licenses

The app's source is at
<https://github.com/saya6k/ha-app-code-interpreter> under the MIT license.
The sandbox bundles bubblewrap (LGPL-2.0-or-later), Node.js (MIT, with its
bundled components under their own licenses; see `/opt/node/LICENSE` in the
sandbox), acorn (MIT) and the Python packages listed above under their own
open-source licenses. The app includes Home Assistant Builder (`hab`), whose
README states the Apache 2.0 license. The icon and logo were made for this app.
