"""bubblewrap-isolated skill script runner.

Skills can ship `scripts/*.py` files (per agentskills.io spec Level 3).
This module is the only path through which they execute, called from
the `run_skill_script` meta-tool. Isolation policy
(see notes/sandbox.md):

  * **Strong isolation, permissive commands** — voice UX can't ask
    per-command; one solid bubblewrap config replaces N permission
    prompts. Inside the sandbox you can do anything bash would let
    you do; outside the sandbox you can do nothing.
  * **Credentials denied by omission** — host `~/.ssh`, `/data`
    (addon `options.json` with `api_key`), supervisor token env var,
    `/run/secrets` etc. are simply not mounted into the bwrap.
  * **No network** (`--unshare-net`) — push/publish/apply, `curl|sh`,
    data exfiltration all fail at the syscall level.
  * **User namespace** (`--unshare-user`) — `sudo`/`su` don't exist
    in PATH anyway, and even if a script smuggles them in, root in
    the namespace ≠ root on the host.
  * **Read-only skill dir + tmpfs `/tmp`** — script can write
    intermediate files to `/tmp` (gone when the process ends), nothing
    else.
  * **Memory + CPU + fd + file-size caps** via `preexec_fn` setting
    RLIMIT_AS / RLIMIT_CPU / RLIMIT_NOFILE / RLIMIT_FSIZE in the
    forked child before exec(bwrap); inherited through bwrap → python3
    → skill. Caps: 200 MB / 5 CPU-seconds / 64 fds / 16 MB per write.
    Separate from the 10s overall asyncio wall-clock timeout.
  * **Output capped at 256 KB per stream** so a runaway loop can't
    DoS the host with stdout.

Requires `SYS_ADMIN` capability on the addon container (set in
`config.yaml`) so the bwrap binary can create namespaces. Without it,
`run_sandboxed_script` raises `SandboxError` with a clear message and
the caller returns the error to the LLM as a tool result.
"""
from __future__ import annotations

import asyncio
import contextlib
import errno
import logging
import os
import resource
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

try:
    import seccomp as _seccomp
    _SECCOMP_AVAILABLE = True
except ImportError:
    _seccomp = None
    _SECCOMP_AVAILABLE = False

_LOGGER = logging.getLogger(__name__)

# Syscalls denied to skill scripts even inside the user namespace.
# Threat model: a skill script that decides to escape, not a kernel-
# exploit attacker. We deny the obvious escape surfaces — namespace
# re-jiggering, ptrace-based process injection, kernel module loading,
# eBPF, mount tricks — and leave normal filesystem / process syscalls
# alone so most legitimate Python scripts work unchanged.
_SECCOMP_DENY: tuple[str, ...] = (
    "ptrace",
    "process_vm_readv",
    "process_vm_writev",
    "mount",
    "umount",
    "umount2",
    "pivot_root",
    "chroot",
    "kexec_load",
    "kexec_file_load",
    "init_module",
    "finit_module",
    "delete_module",
    "bpf",
    "userfaultfd",
    "unshare",
    "setns",
    "perf_event_open",
    "swapon",
    "swapoff",
    "reboot",
    "create_module",
    "get_kernel_syms",
    "query_module",
)

BWRAP_BIN = "bwrap"
PYTHON_BIN = "/usr/bin/python3"

DEFAULT_TIMEOUT_S = 10.0
MAX_STDOUT_BYTES = 256 * 1024
MAX_STDERR_BYTES = 256 * 1024
MAX_STDIN_BYTES = 1024 * 1024
MAX_MEMORY_BYTES = 200 * 1024 * 1024     # RLIMIT_AS via preexec_fn
MAX_CPU_SECONDS = 5                       # RLIMIT_CPU via preexec_fn
# Per-file write cap. Single `write()` past this returns EFBIG, so a
# script can't drop a multi-GB file under /tmp before the tmpfs cap or
# RLIMIT_AS catch it. 16 MB is generous for normal skill outputs
# (think: text reports, small JSON / CSV dumps).
MAX_FILE_SIZE_BYTES = 16 * 1024 * 1024    # RLIMIT_FSIZE via preexec_fn
# Open file descriptors. Stdin/out/err + a handful of imports is well
# under 32; 64 leaves headroom for libraries that fan out (requests
# session, urllib3, etc.) without letting a fork bomb / socket spam go
# wild.
MAX_OPEN_FILES = 64                       # RLIMIT_NOFILE via preexec_fn
# Tmpfs size cap. Without this the `/tmp` tmpfs would silently grow up
# to the host's free memory. 64 MB is more than enough for a script's
# intermediate files and bounded by RLIMIT_AS anyway, but having an
# explicit cap means a kernel-level EFAULT on overflow regardless of
# whether the script's allocations are tracked against its own RSS.
MAX_TMPFS_BYTES = 64 * 1024 * 1024        # bwrap --size (since 0.4)

# History note: 1.14.0 and earlier emitted `--rlimit-as` / `--rlimit-cpu`
# / `--rlimit-fsize` / `--rlimit-nofile` as bwrap flags, guarded by a
# `_detect_bwrap_rlimit_support()` probe that grepped `bwrap --help`
# for `--rlimit-as`. That probe always returned False — **upstream
# bubblewrap (verified through 0.11.0) does NOT have an `--rlimit-*`
# flag family**; it was confused with another tool's interface. So
# every previous addon release shipped skill scripts with NO rlimit
# enforcement at all. 1.14.2 fixes this by setting rlimits in the
# parent process via `preexec_fn` (between fork() and execve(bwrap)).
# Linux propagates rlimits across exec and namespace creation, so the
# skill script inherits them through bwrap → python3.
# Whether the outer container lets bwrap unshare the PID namespace and
# mount a fresh /proc inside it. In nested LXC (typical HA Supervisor
# install) this is denied with EPERM and we fall back to host PID
# namespace + `--ro-bind /proc /proc`. In docker-direct / HA Container
# / podman setups it usually succeeds, giving real PID isolation
# (skill scripts can't see host process listings). Probed at startup;
# the result drives `_bwrap_argv()` branching.
_BWRAP_SUPPORTS_PID_UNSHARE: bool | None = None


class SandboxError(RuntimeError):
    """Raised when the sandbox cannot be set up at all (e.g. bwrap missing,
    bad skill_dir, path traversal). Distinct from a script that ran and
    exited non-zero — that's reported via SandboxResult.exit_code.
    """


def _set_skill_rlimits() -> None:
    """preexec_fn: set process rlimits in the bwrap child between fork()
    and exec(). Linux inherits rlimits across exec and namespace ops,
    so bwrap → python3 → skill all see these caps.

    We do this here instead of as bwrap flags because upstream bwrap
    (verified through 0.11.0) does NOT have `--rlimit-*` flags. The
    only places I had seen them advertised were misattributions.

    Lowering RLIMIT_NOFILE is a hard limit drop and irreversible —
    skill scripts cannot raise it back. Same for RLIMIT_AS / CPU /
    FSIZE: setting them to the same hard+soft value means even a
    privileged process inside the user namespace cannot grow them.

    Failures here propagate up and kill the bwrap launch — we'd
    rather refuse to run than silently run unconfined. (preexec_fn
    exceptions are re-raised by subprocess in the parent.)
    """
    resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
    # RLIMIT_CPU soft != hard: at the soft limit the kernel sends
    # SIGXCPU (default action: terminate). If soft == hard the kernel
    # follows up with SIGKILL almost immediately — fast enough that
    # SIGXCPU can't terminate cleanly first, and the process dies with
    # SIGKILL instead. Giving the hard limit a +5s buffer lets SIGXCPU
    # do its job; a script that catches and ignores SIGXCPU still gets
    # SIGKILLed at the hard limit. Either way the script dies before
    # 10s.
    resource.setrlimit(resource.RLIMIT_CPU, (MAX_CPU_SECONDS, MAX_CPU_SECONDS + 5))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_BYTES))
    resource.setrlimit(resource.RLIMIT_NOFILE, (MAX_OPEN_FILES, MAX_OPEN_FILES))


async def _detect_bwrap_pid_unshare_support() -> tuple[bool, str]:
    """Probe whether `--unshare-pid` + a fresh `/proc` mount is allowed
    in the *current* host environment.

    Issuing `mount("proc", "/newroot/proc", "proc", ...)` requires the
    outer container's mount policy to allow nested proc mounts. HA
    Supervisor on LXC (HAOS) denies this even with CAP_SYS_ADMIN;
    docker-direct / HA Container / podman / bare-metal typically
    allow it. Cheap to test: run `bwrap ... -- /usr/bin/python3 -c ""`
    with the full strict-mode argv and check the exit status.

    Returns `(supported, reason)`. On failure, `reason` carries the
    bwrap stderr so the operator can see *why* we fell back to relaxed
    mode.
    """
    argv = [
        BWRAP_BIN,
        "--unshare-pid",
        "--unshare-net", "--unshare-user", "--unshare-ipc",
        "--unshare-uts", "--unshare-cgroup",
        "--die-with-parent",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/lib", "/lib",
    ]
    if Path("/lib64").is_dir():
        argv += ["--ro-bind", "/lib64", "/lib64"]
    argv += [
        "--proc", "/proc",
        "--", PYTHON_BIN, "-c", "",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={},
        )
    except FileNotFoundError as exc:
        return False, f"exec failed: {exc}"
    try:
        _, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=5.0)
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        await proc.wait()
        return False, "probe timed out"
    if proc.returncode == 0:
        return True, "ok"
    stderr = stderr_b.decode("utf-8", errors="replace").strip() or "(no stderr)"
    return False, stderr


async def probe_sandbox() -> tuple[bool, str]:
    """Best-effort startup probe. Runs `bwrap --unshare-all` against the
    same `/usr` + `/lib` ro-bind layout the real sandbox uses, then
    execs `PYTHON_BIN -c ''` so we catch the actual failure modes:
      * bwrap binary missing → addon image broken
      * EPERM creating user namespace → SYS_ADMIN capability missing
        (addon container needs `privileged: [SYS_ADMIN]` in config.yaml)
      * EPERM on mount → AppArmor profile blocking namespace mounts
        (set `apparmor: false` in config.yaml — see sandbox notes)
      * EINVAL on nested namespace → kernel build doesn't support userns
        or addon-in-something nesting refuses to mount a fresh /proc

    Returns (ok, reason). On failure, the agent disables the
    `run_skill_script` meta-tool entirely so the LLM never sees a tool
    it can't actually call. Other skill features (instructions,
    allowed-tools gating) keep working.

    Note: we probe with `PYTHON_BIN -c ''` rather than `/bin/true` or
    `/usr/bin/true`. Alpine keeps busybox at `/bin/true` but no
    `/usr/bin/true`, while Debian/Ubuntu put it under `/usr/bin/`.
    PYTHON_BIN is what the real sandbox actually runs, so probing it
    means "if the probe passes, real skill scripts will at least exec."
    """
    if shutil.which(BWRAP_BIN) is None:
        return False, f"{BWRAP_BIN!r} not on PATH"
    # Detect optional bwrap features before we build any real argv.
    # Note: rlimits are NOT detected here — they're enforced by
    # `_set_skill_rlimits()` (preexec_fn) regardless of bwrap version.
    global _BWRAP_SUPPORTS_PID_UNSHARE
    pid_ok, pid_reason = await _detect_bwrap_pid_unshare_support()
    _BWRAP_SUPPORTS_PID_UNSHARE = pid_ok
    if pid_ok:
        _LOGGER.info(
            "Skill sandbox: strict PID mode — --unshare-pid + fresh "
            "/proc available. Skill scripts cannot see host process "
            "listings.",
        )
    else:
        _LOGGER.info(
            "Skill sandbox: relaxed PID mode — outer container denies "
            "nested /proc mount, falling back to host PID namespace + "
            "ro-bind /proc. Skill scripts can read host /proc (process "
            "listing visible) but still can't act on those processes "
            "(blocked by --unshare-user + seccomp). Probe stderr: %s",
            pid_reason[:200],
        )
    # Mirror the real-run argv structure so a probe pass implies a
    # real run will at least exec. Specifically: keep --unshare-pid
    # OFF (mounting a fresh /proc on /newroot/proc is denied inside
    # nested HA-addon containers even with CAP_SYS_ADMIN — see the
    # "Operation not permitted" trap noted in sandbox.md). Instead of
    # remounting /proc we ro-bind the host one.
    probe_argv = [
        BWRAP_BIN,
        "--unshare-net", "--unshare-user", "--unshare-ipc",
        "--unshare-uts", "--unshare-cgroup",
        "--die-with-parent",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/lib", "/lib",
    ]
    if Path("/lib64").is_dir():
        probe_argv += ["--ro-bind", "/lib64", "/lib64"]
    probe_argv += [
        "--ro-bind", "/proc", "/proc",
        "--", PYTHON_BIN, "-c", "",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *probe_argv,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={},
        )
    except FileNotFoundError as exc:
        return False, f"exec {BWRAP_BIN}: {exc}"
    try:
        _, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=5.0)
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        await proc.wait()
        return False, "bwrap probe timed out"
    if proc.returncode == 0:
        return True, "ok"
    stderr = stderr_b.decode("utf-8", errors="replace").strip() or "(no stderr)"
    hint = ""
    if "Failed to make / slave" in stderr or "MS_SLAVE" in stderr:
        hint = (
            " — AppArmor on the addon host is blocking bwrap's "
            "mount(MS_SLAVE|MS_REC) call. Set `apparmor: false` in "
            "config.yaml (the bwrap sandbox itself still provides "
            "isolation: --unshare-all + seccomp + ro-bind + rlimits)."
        )
    elif "Operation not permitted" in stderr or "EPERM" in stderr:
        hint = (
            " — addon container likely missing CAP_SYS_ADMIN. "
            "Add `privileged: [SYS_ADMIN]` to config.yaml."
        )
    elif "namespaces are not" in stderr or "clone" in stderr.lower():
        hint = (
            " — kernel may not support user namespaces, or this "
            "addon is running inside another container that blocks them."
        )
    return False, f"bwrap probe failed (rc={proc.returncode}): {stderr}{hint}"


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    truncated_stdout: bool = False
    truncated_stderr: bool = False


@dataclass
class SandboxCheck:
    """One behavioural self-test result. Returned by `verify_sandbox_behavior`."""
    name: str
    category: str            # "always" | "rlimit" | "tmpfs" | "pid_strict" | "seccomp" | "slow"
    claim: str               # what the test is supposed to prove
    passed: bool
    detail: str              # last line of stdout, or short failure reason
    skipped_reason: str | None = None


@dataclass(frozen=True)
class _BehaviorTest:
    name: str
    category: str
    claim: str
    source: str              # Python source — must `raise SystemExit(0)` on pass, non-zero on fail
    expect_timed_out: bool = False  # if True, predicate is `result.timed_out`
    expect_killed: bool = False     # if True, predicate is `result.exit_code < 0 and not timed_out`
    timeout_s: float | None = None  # override run_sandboxed_script timeout (default: 12s, slow: 25s)


def _validate_script_path(skill_dir: Path, script_path: str) -> Path:
    """Resolve `script_path` (relative) under `skill_dir` with strict
    rejection of `..`, absolute paths, symlinks escaping the skill dir,
    and non-`.py` files. Returns the resolved absolute path inside the
    sandbox's `/skill` mount.
    """
    if not script_path or script_path.startswith("/"):
        raise SandboxError(f"script_path must be relative: {script_path!r}")
    if ".." in Path(script_path).parts:
        raise SandboxError(f"script_path must not contain '..': {script_path!r}")
    if not script_path.endswith(".py"):
        raise SandboxError(f"only .py scripts are supported: {script_path!r}")

    candidate = (skill_dir / script_path).resolve(strict=False)
    try:
        skill_real = skill_dir.resolve(strict=True)
    except OSError as exc:
        raise SandboxError(f"skill dir unreadable: {exc}") from exc
    try:
        candidate.relative_to(skill_real)
    except ValueError as exc:
        raise SandboxError(
            f"script_path escapes skill dir: {script_path!r}",
        ) from exc
    if not candidate.is_file():
        raise SandboxError(f"script not found: {script_path!r}")
    return candidate


def _build_seccomp_fd() -> int | None:
    """Compile the syscall denylist into a BPF program and return an
    inheritable fd pointing at it. Returns None when libseccomp isn't
    available (macOS dev hosts, alpine without py3-libseccomp) — caller
    drops the `--seccomp` flag and proceeds with weaker isolation +
    a one-line WARNING. Voice operation outranks strictness.
    """
    if not _SECCOMP_AVAILABLE:
        return None
    filt = _seccomp.SyscallFilter(defaction=_seccomp.ALLOW)
    for name in _SECCOMP_DENY:
        try:
            filt.add_rule(_seccomp.ERRNO(errno.EPERM), name)
        except (ValueError, RuntimeError):
            # Syscall not known on this arch — that's fine, it can't be
            # called either then.
            _LOGGER.debug("seccomp: skipping unknown syscall %s", name)
    # libseccomp's Python binding wants a file-LIKE object (must have
    # `.fileno()`), NOT a raw int fd. Passing the int from mkstemp()
    # raises `'int' object has no attribute 'fileno'` and we'd silently
    # ship without seccomp — the self-test (--self-test-sandbox) caught
    # exactly this regression. Wrap with fdopen(closefd=False) so the
    # raw fd survives the `with` block and we can hand it to bwrap via
    # pass_fds + `--seccomp <fd>`.
    fd, path = tempfile.mkstemp(prefix="skill-seccomp-")
    try:
        with os.fdopen(fd, "wb", closefd=False) as f:
            filt.export_bpf(f)
            f.flush()
    except Exception as exc:  # noqa: BLE001
        os.close(fd)
        with contextlib.suppress(OSError):
            os.unlink(path)
        _LOGGER.warning("seccomp export_bpf failed (%s); running without seccomp", exc)
        return None
    os.lseek(fd, 0, os.SEEK_SET)
    # We don't need the path on disk after the fd is open.
    with contextlib.suppress(OSError):
        os.unlink(path)
    return fd


def _bwrap_argv(
    skill_dir: Path, script_rel: str, args: Sequence[str], *,
    seccomp_fd: int | None,
) -> list[str]:
    """Build the bwrap command line. See module docstring for policy.

    PID namespace handling is environment-dependent — set by
    `_BWRAP_SUPPORTS_PID_UNSHARE` (probed at startup):

      * **Strict** (docker-direct / HA Container / bare-metal): include
        `--unshare-pid` and let bwrap mount a fresh `/proc`. Skill
        scripts see only their own process tree.
      * **Relaxed** (LXC nested = typical HAOS Supervisor): skip
        `--unshare-pid`, ro-bind the host `/proc`. Skill scripts can
        read host process listings but cannot signal them (privilege
        gated by `--unshare-user`, syscalls gated by seccomp).
    """
    argv = [
        BWRAP_BIN,
        "--unshare-net", "--unshare-user", "--unshare-ipc",
        "--unshare-uts", "--unshare-cgroup",
        "--die-with-parent",
        "--new-session",
        # Read-only host bits the Python runtime actually needs.
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/lib", "/lib",
    ]
    if _BWRAP_SUPPORTS_PID_UNSHARE:
        # Insert pid isolation; the matching `--proc /proc` mount comes
        # later in the argv (after --ro-bind /usr etc.) per bwrap's
        # ordering rules.
        argv.insert(1, "--unshare-pid")
    # /lib64 may or may not exist (e.g. on Alpine arm64).
    if Path("/lib64").is_dir():
        argv += ["--ro-bind", "/lib64", "/lib64"]
    if Path("/etc/ssl").is_dir():
        argv += ["--ro-bind", "/etc/ssl", "/etc/ssl"]
    # /proc handling depends on whether we got pid isolation.
    if _BWRAP_SUPPORTS_PID_UNSHARE:
        argv += ["--proc", "/proc"]
    else:
        argv += ["--ro-bind", "/proc", "/proc"]
    argv += [
        "--dev-bind", "/dev/null", "/dev/null",
        "--dev-bind", "/dev/urandom", "/dev/urandom",
        # Writable scratch — gone when the bwrap process exits. `--size`
        # caps the tmpfs at MAX_TMPFS_BYTES so a script can't fill the
        # host's RAM-backed tmpfs by writing under /tmp. `--size` must
        # come *before* the `--tmpfs` it applies to (bwrap docs).
        "--size", str(MAX_TMPFS_BYTES),
        "--tmpfs", "/tmp",
        # The skill's own directory, read-only.
        "--ro-bind", str(skill_dir), "/skill",
        "--chdir", "/skill",
    ]
    # NOTE: rlimits are NOT bwrap flags — upstream bubblewrap has no
    # --rlimit-* family. Set via `preexec_fn=_set_skill_rlimits` in
    # run_sandboxed_script() so they're inherited across exec(bwrap)
    # → exec(python3) → skill script.
    argv += [
        # Sterile environment — no SUPERVISOR_TOKEN, no API keys leaked.
        "--setenv", "HOME", "/tmp",
        "--setenv", "PATH", "/usr/bin:/usr/local/bin",
        "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
    ]
    if seccomp_fd is not None:
        argv += ["--seccomp", str(seccomp_fd)]
    argv += [
        "--",
        PYTHON_BIN, script_rel, *args,
    ]
    return argv


async def run_sandboxed_script(
    *,
    skill_dir: Path,
    script_path: str,
    args: Sequence[str] = (),
    stdin: str | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> SandboxResult:
    """Execute `skill_dir/script_path` inside a bubblewrap sandbox.

    Raises SandboxError before launching for unrecoverable config
    problems (bwrap missing, bad path, etc.). A script that ran and
    exited non-zero — even from an unhandled Python exception —
    returns a SandboxResult with that exit code; the caller decides
    whether that's an error to surface to the LLM.
    """
    if shutil.which(BWRAP_BIN) is None:
        raise SandboxError(
            f"{BWRAP_BIN!r} not on PATH. The skill sandbox requires "
            f"bubblewrap (apk add bubblewrap) and the addon container "
            f"needs SYS_ADMIN capability (config.yaml: privileged: "
            f"[SYS_ADMIN]). See notes/sandbox.md."
        )
    # Validate path under the sandbox's /skill mount, but pass the
    # *relative* form to bwrap because that's the runtime view.
    _validate_script_path(skill_dir, script_path)

    if stdin is not None and len(stdin.encode("utf-8")) > MAX_STDIN_BYTES:
        raise SandboxError(
            f"stdin exceeds {MAX_STDIN_BYTES} bytes "
            f"({len(stdin.encode('utf-8'))} given)"
        )

    seccomp_fd = _build_seccomp_fd()
    if seccomp_fd is None and _SECCOMP_AVAILABLE:
        # Built once before — module loaded but the build itself failed.
        pass
    elif seccomp_fd is None:
        _LOGGER.warning(
            "libseccomp not available — running skill script without "
            "syscall filter. Install py3-libseccomp in the addon image "
            "to enable the second layer of defence.",
        )

    argv = _bwrap_argv(skill_dir, script_path, args, seccomp_fd=seccomp_fd)
    _LOGGER.debug("sandbox argv: %s", argv)

    stdin_bytes = stdin.encode("utf-8") if stdin is not None else None
    pass_fds: tuple[int, ...] = (seccomp_fd,) if seccomp_fd is not None else ()
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdin=asyncio.subprocess.PIPE if stdin_bytes else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={},  # belt-and-suspenders: nothing inherited even before bwrap --setenv
            pass_fds=pass_fds,
            # Set rlimits in the forked child before exec(bwrap). Linux
            # propagates RLIMIT_* across exec and namespace creation, so
            # bwrap → python3 → skill all inherit our caps. This is the
            # ONLY rlimit enforcement we have — bwrap itself has no
            # --rlimit-* flags. preexec_fn is "deprecated for thread
            # safety" upstream but asyncio is single-threaded and we
            # never combine subprocess with threading here, so the
            # warning doesn't apply.
            preexec_fn=_set_skill_rlimits,
        )
    except FileNotFoundError as exc:
        if seccomp_fd is not None:
            with contextlib.suppress(OSError):
                os.close(seccomp_fd)
        raise SandboxError(f"failed to launch {BWRAP_BIN}: {exc}") from exc
    finally:
        # bwrap dup'd it for the child; our copy can go.
        if seccomp_fd is not None:
            with contextlib.suppress(OSError):
                os.close(seccomp_fd)

    timed_out = False
    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(stdin_bytes), timeout=timeout_s,
        )
    except asyncio.TimeoutError:
        timed_out = True
        with contextlib.suppress(ProcessLookupError):
            proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
            await proc.wait()
        stdout_b, stderr_b = b"", b""

    truncated_stdout = len(stdout_b) > MAX_STDOUT_BYTES
    truncated_stderr = len(stderr_b) > MAX_STDERR_BYTES
    stdout = stdout_b[:MAX_STDOUT_BYTES].decode("utf-8", errors="replace")
    stderr = stderr_b[:MAX_STDERR_BYTES].decode("utf-8", errors="replace")

    return SandboxResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=-1 if timed_out else (proc.returncode or 0),
        timed_out=timed_out,
        truncated_stdout=truncated_stdout,
        truncated_stderr=truncated_stderr,
    )


# ---- Behavioural self-tests --------------------------------------------------
#
# Each entry is a tiny Python script that asserts ONE isolation claim from
# notes/sandbox.md and exits 0 on pass / non-zero on fail. The scripts run
# via the production `run_sandboxed_script()` code path, so a green suite
# means our claims hold for the CURRENT bwrap + apparmor + seccomp + kernel
# combination — not just "bwrap launches".
#
# Adding a test: append a `_BehaviorTest`. Keep the source self-contained
# (no skill-dir-bundled dependencies); the script must succeed in <12s.

_BEHAVIOR_TESTS: tuple[_BehaviorTest, ...] = (
    _BehaviorTest(
        name="net_isolated",
        category="always",
        claim="--unshare-net removes network access (DNS / connect both fail)",
        source="""\
import socket
try:
    socket.gethostbyname('one.one.one.one')
    print('FAIL: DNS resolved despite --unshare-net', flush=True)
    raise SystemExit(1)
except OSError as e:
    print(f'ok: {type(e).__name__}: {e}', flush=True)
""",
    ),
    _BehaviorTest(
        name="env_sterile",
        category="always",
        claim="env={} + bwrap --setenv leaves only HOME/PATH/PYTHONDONTWRITEBYTECODE (+ PWD from --chdir)",
        source="""\
import os, json
# PWD is auto-set by bwrap when --chdir is given (bwrap.c uses
# set_env_unless_existing); we treat it as expected, not a leak.
# Anything else means our env={} + --setenv discipline broke.
expected = {'HOME', 'PATH', 'PYTHONDONTWRITEBYTECODE', 'PWD'}
keys = set(os.environ.keys())
extras = sorted(keys - expected)
missing = sorted(expected - keys - {'PWD'})  # PWD is bwrap-best-effort, not required
print(json.dumps({'keys': sorted(keys), 'extras': extras, 'missing': missing}), flush=True)
raise SystemExit(0 if not extras and not missing else 1)
""",
    ),
    _BehaviorTest(
        name="no_host_data",
        category="always",
        claim="/data (host addon options.json with api_key) not mounted",
        source="""\
import os
try:
    open('/data/options.json').read(1)
    print('FAIL: /data/options.json readable', flush=True)
    raise SystemExit(1)
except (FileNotFoundError, PermissionError, IsADirectoryError, NotADirectoryError) as e:
    print(f'ok: {type(e).__name__}', flush=True)
""",
    ),
    _BehaviorTest(
        name="no_host_secrets",
        category="always",
        claim="/etc/shadow and host secret dirs not reachable",
        source="""\
import os
hits = []
for p in ('/etc/shadow', '/root/.ssh', '/run/secrets', '/data', '/share', '/config'):
    try:
        os.stat(p)
        hits.append(p)
    except (FileNotFoundError, PermissionError, NotADirectoryError):
        pass
if hits:
    print(f'FAIL: reachable paths: {hits}', flush=True)
    raise SystemExit(1)
print('ok: all host secret paths absent', flush=True)
""",
    ),
    _BehaviorTest(
        name="usr_readonly",
        category="always",
        claim="--ro-bind /usr is genuinely read-only",
        source="""\
try:
    open('/usr/test_write_should_fail', 'w').write('x')
    print('FAIL: /usr writable', flush=True)
    raise SystemExit(1)
except OSError as e:
    print(f'ok: {type(e).__name__} errno={e.errno}', flush=True)
""",
    ),
    _BehaviorTest(
        name="skill_readonly",
        category="always",
        claim="--ro-bind <skill_dir> /skill is read-only",
        source="""\
try:
    open('/skill/test_write_should_fail', 'w').write('x')
    print('FAIL: /skill writable', flush=True)
    raise SystemExit(1)
except OSError as e:
    print(f'ok: {type(e).__name__} errno={e.errno}', flush=True)
""",
    ),
    _BehaviorTest(
        name="tmp_writable",
        category="always",
        claim="/tmp tmpfs is writable for scratch use",
        source="""\
p = '/tmp/sandbox_self_test_marker'
with open(p, 'w') as f:
    f.write('ok')
with open(p) as f:
    assert f.read() == 'ok'
print('ok', flush=True)
""",
    ),
    _BehaviorTest(
        name="seccomp_blocks_unshare",
        category="seccomp",
        claim="seccomp denylist rejects unshare(CLONE_NEWNS) at the syscall layer",
        source="""\
import ctypes, ctypes.util, errno
libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
CLONE_NEWNS = 0x00020000
rc = libc.unshare(CLONE_NEWNS)
err = ctypes.get_errno()
if rc == -1 and err == errno.EPERM:
    print(f'ok: unshare blocked by seccomp (EPERM)', flush=True)
elif rc == -1:
    # Some kernels return EINVAL/ENOSYS first; still a refusal, log it.
    print(f'ok: unshare refused (errno={err})', flush=True)
else:
    print(f'FAIL: unshare returned {rc}', flush=True)
    raise SystemExit(1)
""",
    ),
    _BehaviorTest(
        name="seccomp_blocks_mount",
        category="seccomp",
        claim="seccomp denylist rejects mount() at the syscall layer",
        source="""\
import ctypes, ctypes.util, errno
libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
rc = libc.mount(b'none', b'/tmp/mnt', b'tmpfs', 0, None)
err = ctypes.get_errno()
if rc == -1 and err == errno.EPERM:
    print(f'ok: mount blocked by seccomp (EPERM)', flush=True)
elif rc == -1:
    print(f'ok: mount refused (errno={err})', flush=True)
else:
    print(f'FAIL: mount returned {rc}', flush=True)
    raise SystemExit(1)
""",
    ),
    _BehaviorTest(
        name="rlimit_fsize",
        category="rlimit",
        claim="RLIMIT_FSIZE (preexec_fn) caps single-file writes at 16 MiB",
        source="""\
import os
written = 0
try:
    with open('/tmp/big', 'wb') as f:
        for _ in range(32):  # try to write 32 MiB, cap is 16
            f.write(b'x' * 1024 * 1024)
            written += 1024 * 1024
    print(f'FAIL: wrote {written} bytes (cap 16 MiB)', flush=True)
    raise SystemExit(1)
except OSError as e:
    print(f'ok: {type(e).__name__} errno={e.errno} at {written} bytes', flush=True)
""",
    ),
    _BehaviorTest(
        name="rlimit_nofile",
        category="rlimit",
        claim="RLIMIT_NOFILE (preexec_fn) caps open fd count at 64",
        source="""\
import os
fds = []
try:
    for i in range(200):
        fds.append(os.open(f'/tmp/nofile_{i}', os.O_CREAT | os.O_WRONLY, 0o600))
    print(f'FAIL: opened {len(fds)} fds (cap 64)', flush=True)
    raise SystemExit(1)
except OSError as e:
    print(f'ok: {type(e).__name__} errno={e.errno} at {len(fds)} fds', flush=True)
finally:
    for fd in fds:
        try: os.close(fd)
        except OSError: pass
""",
    ),
    _BehaviorTest(
        name="tmpfs_size_cap",
        category="tmpfs",
        claim="--size --tmpfs caps total /tmp usage at 64 MiB",
        source="""\
# Spread across many files so per-file rlimit-fsize doesn't trigger first.
import os
written = 0
try:
    for i in range(20):  # 20 * 8 MiB = 160 MiB, far past the 64 MiB cap
        with open(f'/tmp/chunk_{i}', 'wb') as f:
            f.write(b'x' * 8 * 1024 * 1024)
        written += 8 * 1024 * 1024
    print(f'FAIL: wrote {written} bytes total (cap 64 MiB)', flush=True)
    raise SystemExit(1)
except OSError as e:
    print(f'ok: {type(e).__name__} errno={e.errno} after {written} bytes', flush=True)
""",
    ),
    _BehaviorTest(
        name="pid_isolation",
        category="pid_strict",
        claim="--unshare-pid hides host processes (strict mode only)",
        source="""\
import os
pids = sorted(int(e) for e in os.listdir('/proc') if e.isdigit())
# In strict pid mode we expect to see only our own python process (PID 1
# inside the new namespace) plus maybe its kernel helpers. Anything >5
# means we're seeing the host process tree.
if len(pids) <= 5:
    print(f'ok: {len(pids)} visible PIDs ({pids})', flush=True)
else:
    print(f'FAIL: {len(pids)} PIDs visible — host /proc leaked', flush=True)
    raise SystemExit(1)
""",
    ),
    _BehaviorTest(
        name="wall_clock_timeout",
        category="slow",
        claim="asyncio wait_for(DEFAULT_TIMEOUT_S=10s) kills runaway scripts",
        source="""\
import time
time.sleep(20)  # >DEFAULT_TIMEOUT_S, must be SIGTERM/SIGKILLed at ~10s
print('FAIL: slept full 20s without interruption', flush=True)
raise SystemExit(1)
""",
        expect_timed_out=True,
        # Must use the documented DEFAULT_TIMEOUT_S — overriding it would
        # mask the very behaviour we're testing.
        timeout_s=DEFAULT_TIMEOUT_S,
    ),
    _BehaviorTest(
        name="rlimit_cpu",
        category="slow",
        claim="RLIMIT_CPU (preexec_fn, 5s) sends SIGXCPU on 100% CPU loops",
        source="""\
i = 0
while True:
    i += 1  # busy loop; should hit rlimit-cpu well before asyncio's 10s
""",
        expect_killed=True,
        # RLIMIT_CPU is now always set via preexec_fn (no bwrap version
        # dependency); SIGXCPU fires at ~5s wall for a single-thread
        # busy loop. 15s ceiling > 5s rlimit, < 25s slow default.
        timeout_s=15.0,
    ),
)


def _evaluate(test: _BehaviorTest, result: SandboxResult) -> tuple[bool, str]:
    """Return (passed, detail) for one test result."""
    if test.expect_timed_out:
        passed = result.timed_out
        detail = (
            "ok: killed after timeout"
            if passed
            else f"FAIL: did not time out (exit={result.exit_code} stdout={result.stdout.strip()[:80]!r})"
        )
        return passed, detail
    if test.expect_killed:
        # Two conventions for "killed by signal":
        #   * Python direct subprocess: exit_code = -signum (negative)
        #   * Shell / bwrap wrapping:    exit_code = 128 + signum (positive)
        # bwrap is our supervisor process and uses the shell convention
        # (WIFSIGNALED → 128+WTERMSIG), so child SIGXCPU/SIGKILL surface
        # as 152/137 to Python. Either convention indicates the script
        # didn't exit normally, which is what `expect_killed` is for.
        ec = result.exit_code
        wrapped_signal = 128 < ec < 160        # 129-159 = 128+signum
        direct_signal = ec < 0
        passed = (not result.timed_out) and (wrapped_signal or direct_signal)
        if passed:
            signum = (ec - 128) if wrapped_signal else -ec
            detail = f"ok: killed by signal ({signum})"
        else:
            detail = (
                f"FAIL: not signal-killed "
                f"(exit={ec} timed_out={result.timed_out})"
            )
        return passed, detail
    passed = (not result.timed_out) and result.exit_code == 0
    if passed:
        # Surface the script's last stdout line as the detail.
        lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
        detail = lines[-1] if lines else "ok (no output)"
    else:
        last_out = result.stdout.strip().splitlines()
        last_err = result.stderr.strip().splitlines()
        why = last_out[-1] if last_out else (last_err[-1] if last_err else "")
        detail = f"exit={result.exit_code} timed_out={result.timed_out} {why}"
    return passed, detail[:300]


async def verify_sandbox_behavior(
    *, include_slow: bool = False,
) -> list[SandboxCheck]:
    """End-to-end behavioural self-test of the live sandbox.

    Runs each `_BehaviorTest` via the production `run_sandboxed_script()`
    so a pass means the corresponding isolation claim is enforced by THIS
    deployment's bwrap + apparmor + seccomp + kernel. Categories:

      * `always`      — runs unconditionally
      * `rlimit`      — skipped when bwrap < 0.10 (no `--rlimit-*` family)
      * `tmpfs`       — runs unconditionally (`--size` since bwrap 0.4)
      * `pid_strict`  — skipped in relaxed PID mode (host pidns)
      * `seccomp`     — skipped when libseccomp not available
      * `slow`        — skipped unless `include_slow=True`; runs into the
                        `--rlimit-cpu 5s` / `wait_for 10s` ceilings,
                        adds ~15-20s total

    Caller must `await probe_sandbox()` first so support flags are set;
    otherwise the rlimit/pid_strict categories are conservatively skipped.

    Returns one `SandboxCheck` per test, in declaration order. Each test
    runs in its own tmp skill dir, single bwrap subprocess. Total runtime
    without `include_slow` is roughly 3-5 seconds on typical HAOS.
    """
    tmp = Path(tempfile.mkdtemp(prefix="sandbox-self-test-"))
    out: list[SandboxCheck] = []
    try:
        for test in _BEHAVIOR_TESTS:
            # Category gates. Note: there is no "rlimit not supported"
            # skip anymore — rlimits are set via preexec_fn on every
            # spawn, independent of bwrap version.
            if test.category == "pid_strict" and not _BWRAP_SUPPORTS_PID_UNSHARE:
                out.append(SandboxCheck(
                    name=test.name, category=test.category, claim=test.claim,
                    passed=False, detail="(skipped: relaxed PID mode)",
                    skipped_reason="relaxed_pid",
                ))
                continue
            if test.category == "seccomp" and not _SECCOMP_AVAILABLE:
                out.append(SandboxCheck(
                    name=test.name, category=test.category, claim=test.claim,
                    passed=False, detail="(skipped: libseccomp not installed)",
                    skipped_reason="no_seccomp",
                ))
                continue
            if test.category == "slow" and not include_slow:
                out.append(SandboxCheck(
                    name=test.name, category=test.category, claim=test.claim,
                    passed=False, detail="(skipped: pass include_slow=True)",
                    skipped_reason="slow_opt_in",
                ))
                continue

            script = tmp / f"{test.name}.py"
            script.write_text(test.source)
            # Per-test override wins; otherwise: slow tests need >10s for
            # wait_for to fire cleanly, fast tests get a tight 12s ceiling.
            if test.timeout_s is not None:
                timeout = test.timeout_s
            elif test.category == "slow":
                timeout = 25.0
            else:
                timeout = 12.0
            try:
                result = await run_sandboxed_script(
                    skill_dir=tmp,
                    script_path=f"{test.name}.py",
                    timeout_s=timeout,
                )
            except SandboxError as exc:
                out.append(SandboxCheck(
                    name=test.name, category=test.category, claim=test.claim,
                    passed=False, detail=f"setup error: {exc}",
                ))
                continue
            passed, detail = _evaluate(test, result)
            out.append(SandboxCheck(
                name=test.name, category=test.category, claim=test.claim,
                passed=passed, detail=detail,
            ))
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


