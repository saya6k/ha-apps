# Code Interpreter

Stateful Python code execution for Assist conversation agents, supplied over
MCP (Model Context Protocol). The agent can run code, keep variables between
calls, work with files, and hand results (tables, plots) back to you through
`/share`.

## How it works

- **MCP server:** streamable HTTP at `/mcp` on port 8099. Home Assistant's
  **Model Context Protocol** integration connects to it, and the app
  announces itself through Supervisor discovery.
- **One sandbox per session:** each session runs in its own
  [bubblewrap](https://github.com/containers/bubblewrap) sandbox inside the
  app container. A Python REPL keeps the session's variables until the
  session ends.
- **Preinstalled analysis stack:** numpy, pandas, scipy, statsmodels,
  scikit-learn, sympy, networkx, matplotlib (Korean labels work out of the
  box), seaborn, openpyxl, xlsxwriter, pyarrow, pillow, lxml, beautifulsoup4,
  python-docx, fpdf2, pyyaml and tabulate.
- **Sessions end on their own:** a session is closed after
  `idle_timeout_minutes` without a call, and its variables and files are
  discarded.

The app runs with **protection mode on**. It needs no Docker access and no
extra privileges.

## Connect to Home Assistant

1. Start the app. The log should show `sandbox self-check ok` and
   `Announced MCP endpoint to Home Assistant.`
2. Go to **Settings → Devices & services**. A discovered **Model Context
   Protocol** entry appears; add it. (Discovery needs Home Assistant
   2026.10 or newer.)
3. Enable the new tools for your Assist conversation agent.

If nothing is discovered, add the **Model Context Protocol** integration by
hand. The app's log prints the URL to use when the announcement fails; it
has the form `http://<app hostname>:8099/mcp`.

No port mapping is needed. Map port 8099 only for an MCP client outside the
Home Assistant host.

## Tools

| Tool | What it does |
|---|---|
| `run_code` | Run Python. Variables persist across calls with the same `session_id`. Returns stdout, stderr, the last expression's value, and `new_files` |
| `run_command` | Run a shell command (`sh -c`) in the same sandbox and files |
| `list_files` / `read_file` / `write_file` | Work with files under `/sandbox` |
| `import_from_share` | Copy a file from `/share` into the session |
| `export_to_share` | Copy a session file to `/share/code-interpreter/<session>/` |
| `list_sessions` / `close_session` | See and end sessions |

When a session has expired, a call with its `session_id` returns
`session_not_found`; the agent then starts a new session. It never silently
continues in a fresh one.

### Time limit per call

Home Assistant ends every tool call after **30 seconds**. The tools default
to `timeout_s: 25`, so a long cell is interrupted by the app first and its
variables are kept. Work that needs more than about 25 seconds in one call
(large `pip install`, long model training) cannot finish through Home
Assistant. Ask the agent to split it into shorter steps.

## Files and /share

Each session has a private `/sandbox` (256 MB) and `/tmp` (64 MB). Both live
in memory and are gone when the session ends; nothing is written to the Home
Assistant data disk.

- To give the agent a file, put it in `/share` (for example with the Samba
  or File editor app) and ask it to import that file.
- Exported files land in `export_dir/<session>/` (default
  `/share/code-interpreter`). Name clashes get `-1`, `-2` suffixes; nothing
  is overwritten.
- Paths outside `/share` and `/sandbox`, symlink escapes and files over
  `max_file_mb` are refused.

## Network

By default the sandbox has **no network at all**: no internet, no Home
Assistant, no LAN, no DNS.

To let code reach specific hosts (for example to `pip install` packages),
list them in `network_allowlist`:

```yaml
network_allowlist:
  - pypi.org
  - "*.pythonhosted.org"
```

Entries are `host` or `host:port` (port 443 if omitted); `*.domain` matches
subdomains only. Traffic goes through an HTTPS proxy in the app that allows
only the listed hosts, and only when they resolve to public addresses.
Plain HTTP, IP addresses and everything else are refused. Invalid entries
are ignored with an error in the log.

## Options

| Option | Default | Description |
|---|---|---|
| `idle_timeout_minutes` | `20` | Close a session after this many minutes without a call |
| `max_sessions` | `3` | Sessions at once; the least recently used idle session is closed to make room |
| `memory_limit_mb` | `2048` | Address-space limit per sandbox (`RLIMIT_AS`, minimum 768). This counts reserved memory, so real use is lower. Allocations beyond it raise `MemoryError` |
| `network_allowlist` | empty | Hosts the sandbox may reach over HTTPS (see above). Empty = no network |
| `max_file_mb` | `20` | Largest file for import, export and `write_file` |
| `export_dir` | `/share/code-interpreter` | Where exported files go; must be under `/share` |
| `audit_retention_days` | `30` | Days of audit log to keep |

## Security model

The sandbox is meant to contain code an LLM writes. It is **not** a virtual
machine: sandboxes share the host kernel.

Inside a sandbox, code:

- runs as an unprivileged user with no capabilities, in its own user, PID,
  network, IPC and mount namespaces;
- sees a read-only system and only its own `/sandbox` and `/tmp`, with no
  `/proc` (tools such as `psutil` do not work);
- cannot see the app's files, `/share`, `/config`, the Supervisor token or
  other sessions;
- is filtered by seccomp (no nested namespaces, no `bpf`, `ptrace`,
  `keyctl`, `io_uring`, …) and runs under the app's AppArmor profile;
- has limits on memory (`memory_limit_mb`), processes, open files and file
  size. Math libraries use 2 threads, and sandboxes run at a lower CPU
  priority. Under memory pressure the kernel ends sandboxes before the app.

If the sandbox cannot be set up as described, the app refuses to run code
(fail closed) and logs why at startup.

## Audit log

Every session, code run, command, file transfer, network connection and
refused action is recorded in `/data/audit/audit-YYYYMMDD.jsonl` (kept for
`audit_retention_days`, included in backups). The log keeps the code and
commands that ran but never their output, only its size. Each record also
shows as a one-line `[audit]` summary in the app log.

## Troubleshooting

- **`sandbox self-check FAILED` in the log:** the host does not allow the
  sandbox (for example a kernel without user namespaces). Tools return
  `sandbox_unavailable` until this is fixed; the log line says why.
- **`Timeout when calling tool`:** the call ran into Home Assistant's 30 s
  limit. Ask for shorter steps.
- **`KernelDied`:** the Python process ended below Python (out of memory,
  a native library crash). Its last error output is in `stderr`. Variables
  are lost and files are kept.
- **`MemoryError` on import:** raise `memory_limit_mb`.
- **A package is missing:** add `pypi.org` and `*.pythonhosted.org` to
  `network_allowlist` and let the agent `pip install` it (keep each install
  under 25 s).

## Licenses and trademarks

The app's source is at
<https://github.com/saya6k/ha-app-code-interpreter> under the MIT license.
The sandbox bundles
bubblewrap (LGPL-2.0-or-later) and the Python packages listed above under
their own open-source licenses.

The icon is the Python logo symbol as published on python.org, and the logo
sets it beside the words "Code Interpreter"; the symbol is not altered.
"Python" and the Python logos are trademarks or registered trademarks of the
Python Software Foundation. This app is an independent community project
and is not affiliated with or endorsed by the PSF.
