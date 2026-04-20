"""High-level client for the Lean backend.

The CLI calls these functions. They implement the policy:

1. If a daemon is already running on the project's socket, send the request
   and return the result.
2. Otherwise, if ``use_daemon`` is allowed, try to auto-spawn the daemon
   and then retry once. If spawn fails (e.g. lean missing), fall through.
3. Otherwise, run the one-shot subprocess backend directly.

``use_daemon=False`` forces the direct path — useful for debugging and
tests, and required when the socket path would exceed the OS limit on
Unix-domain sockets (108 bytes on Linux, 104 on macOS).
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from grd.core.lean import backend as lean_backend
from grd.core.lean.env import daemon_log_path, socket_path
from grd.core.lean.protocol import LeanCheckRequest, LeanCheckResult

__all__ = [
    "check",
    "check_file",
    "ping_daemon",
    "read_daemon_log_tail",
    "shutdown_daemon",
    "spawn_daemon",
    "MAX_UNIX_SOCKET_PATH",
]


MAX_UNIX_SOCKET_PATH = 104
"""Conservative upper bound on Unix-domain socket path length.

Linux permits 108, macOS 104. We use the smaller so code works on both
without conditional branches. Callers whose sockets exceed this should
fall back to the one-shot backend (``use_daemon=False``) or set
``GRD_LEAN_SOCKET`` to a shorter path (e.g. under ``/tmp``).
"""


def _socket_usable(project_root: Path) -> bool:
    sock = socket_path(project_root)
    return len(str(sock)) <= MAX_UNIX_SOCKET_PATH


def _send_request(sock_path: Path, req: LeanCheckRequest, *, timeout_s: float) -> LeanCheckResult:
    """Open a client-side socket, send one JSON line, read the response line."""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(max(timeout_s + 5.0, 5.0))
    try:
        s.connect(str(sock_path))
    except (FileNotFoundError, ConnectionRefusedError, OSError) as exc:
        try:
            s.close()
        except OSError:
            pass
        return LeanCheckResult(
            ok=False,
            error="daemon_unavailable",
            error_detail=f"Cannot connect to daemon at {sock_path}: {exc}",
        )

    try:
        payload = (req.model_dump_json() + "\n").encode("utf-8")
        s.sendall(payload)
        # Read until newline.
        buf = bytearray()
        while True:
            try:
                chunk = s.recv(8192)
            except TimeoutError:
                return LeanCheckResult(
                    ok=False,
                    error="timeout",
                    error_detail="Daemon did not respond before timeout",
                )
            if not chunk:
                break
            buf.extend(chunk)
            if b"\n" in buf:
                newline = buf.index(b"\n")
                buf = buf[: newline + 1]
                break
        if not buf:
            return LeanCheckResult(
                ok=False,
                error="daemon_unavailable",
                error_detail="Daemon closed connection before replying",
            )
        line = buf.rstrip(b"\n").decode("utf-8", errors="replace")
        try:
            return LeanCheckResult.model_validate_json(line)
        except Exception as exc:  # pragma: no cover — defensive
            return LeanCheckResult(
                ok=False,
                error="internal_error",
                error_detail=f"Malformed daemon response: {exc}",
            )
    finally:
        try:
            s.close()
        except OSError:
            pass


_LOG_ROTATE_BYTES = 1 * 1024 * 1024  # 1 MiB


def _rotate_log(log: Path) -> None:
    """Rotate the daemon log if it exceeds ``_LOG_ROTATE_BYTES``.

    Simple single-generation rotation: ``lean-daemon.log`` →
    ``lean-daemon.log.1``. Old ``.1`` is overwritten silently.
    """
    try:
        if log.exists() and log.stat().st_size > _LOG_ROTATE_BYTES:
            rotated = log.with_suffix(log.suffix + ".1")
            log.rename(rotated)
    except OSError:
        pass


def spawn_daemon(
    project_root: Path,
    *,
    idle_timeout_s: float | None = None,
    python_exe: str | None = None,
    wait_s: float = 5.0,
) -> bool:
    """Attempt to start the daemon in a detached subprocess.

    Returns True iff the daemon answers a real ``ping`` within ``wait_s``
    seconds. Socket-existence alone is insufficient — a daemon that crashes
    during startup will create the socket briefly then exit, leaving a stale
    file (ge-f9i / P1-5). Stderr is captured to the project-local
    ``.grd/lean-daemon.log`` so that startup failures produce a readable
    log rather than vanishing into ``/dev/null``.
    """
    if not _socket_usable(project_root):
        return False

    py = python_exe or sys.executable
    args = [py, "-m", "grd.core.lean.daemon_entrypoint", "--project-root", str(project_root)]
    if idle_timeout_s is not None:
        args += ["--idle-timeout", str(idle_timeout_s)]

    env = os.environ.copy()
    # Ensure the grd package is importable in the child.
    env.setdefault("PYTHONUNBUFFERED", "1")

    log = daemon_log_path(project_root)
    log.parent.mkdir(parents=True, exist_ok=True)
    _rotate_log(log)

    try:
        log_fd = open(log, "a", buffering=1)  # noqa: SIM115
    except OSError:
        log_fd = None  # type: ignore[assignment]

    try:
        subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=log_fd or subprocess.DEVNULL,
            stderr=log_fd or subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
    except OSError:
        if log_fd:
            log_fd.close()
        return False

    # The parent doesn't write to the log — only the child does via its
    # inherited fd. Close our copy so we don't hold the file open.
    if log_fd:
        log_fd.close()

    # Wait for the daemon to actually respond to a ping, not just create
    # the socket file. A crash-on-startup daemon creates the socket during
    # _bind_socket() then exits — polling only for the file would report
    # "started" when the process is already dead.
    sock = socket_path(project_root)
    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        if sock.exists():
            if ping_daemon(project_root, timeout_s=1.0):
                return True
        time.sleep(0.1)
    # One last attempt at the deadline boundary.
    return ping_daemon(project_root, timeout_s=1.0)


def ping_daemon(project_root: Path, *, timeout_s: float = 2.0) -> bool:
    """Return True iff the daemon answers a ping within ``timeout_s``."""
    sock = socket_path(project_root)
    if not sock.exists():
        return False
    result = _send_request(sock, LeanCheckRequest(op="ping"), timeout_s=timeout_s)
    return result.ok and result.error is None


def shutdown_daemon(project_root: Path, *, timeout_s: float = 5.0) -> LeanCheckResult:
    """Ask the daemon to exit. Safe to call when no daemon is running."""
    sock = socket_path(project_root)
    if not sock.exists():
        return LeanCheckResult(
            ok=True,
            error=None,
            error_detail="No daemon running.",
            backend="daemon",
        )
    return _send_request(sock, LeanCheckRequest(op="shutdown"), timeout_s=timeout_s)


def read_daemon_log_tail(project_root: Path, lines: int = 20) -> str | None:
    """Return the last ``lines`` of the daemon log, or ``None`` if absent/empty.

    Used by the CLI to surface startup failures inline (ge-f9i / P1-5):
    when the daemon doesn't come up, printing the log tail saves the user
    from hunting for the file manually.
    """
    log = daemon_log_path(project_root)
    if not log.exists():
        return None
    try:
        text = log.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not text.strip():
        return None
    tail = text.rstrip("\n").rsplit("\n", lines)
    # rsplit with maxsplit=lines returns at most lines+1 parts; take everything
    # after the first split boundary.
    if len(tail) > lines:
        tail = tail[1:]
    return "\n".join(tail)


# Track the most recent spawn failure per-process so the CLI can surface it.
_last_spawn_failed: dict[str, bool] = {}


def _run_with_daemon(
    project_root: Path,
    req: LeanCheckRequest,
    *,
    auto_spawn: bool,
) -> LeanCheckResult | None:
    """Try to execute ``req`` via the daemon. Return None to signal fallback."""
    if not _socket_usable(project_root):
        return None
    sock = socket_path(project_root)
    key = str(project_root)
    if not sock.exists() or not ping_daemon(project_root, timeout_s=1.0):
        if not auto_spawn:
            return None
        if not spawn_daemon(project_root):
            _last_spawn_failed[key] = True
            return None
    _last_spawn_failed.pop(key, None)
    result = _send_request(sock, req, timeout_s=req.timeout_s)
    if result.error == "daemon_unavailable":
        return None
    return result


def check(
    *,
    code: str,
    project_root: Path | None = None,
    imports: list[str] | None = None,
    timeout_s: float = 30.0,
    use_daemon: bool | None = True,
    auto_spawn: bool = True,
    max_heartbeats: int | None = None,
) -> LeanCheckResult:
    """Type-check inline Lean 4 source.

    ``use_daemon``:
        * ``True`` (default) — prefer the daemon, fall back to one-shot.
        * ``False`` — always use the one-shot backend.
        * ``None`` — same as False; never spawn or contact the daemon.

    ``auto_spawn`` only matters when ``use_daemon`` is True: if the socket is
    missing, should we try to launch the daemon? Off-by-default callers (e.g.
    tests) can disable this to keep the run hermetic.

    ``max_heartbeats`` overrides Lean's ``maxHeartbeats`` option for this
    elaboration (``None`` keeps the toolchain default). Used by the
    heartbeat auto-retry layer.
    """
    imports = imports or []
    if use_daemon and project_root is not None:
        req = LeanCheckRequest(
            op="check",
            code=code,
            imports=list(imports),
            timeout_s=timeout_s,
            max_heartbeats=max_heartbeats,
        )
        maybe = _run_with_daemon(project_root, req, auto_spawn=auto_spawn)
        if maybe is not None:
            return maybe

    return lean_backend.run_check(
        code=code,
        imports=list(imports),
        timeout_s=timeout_s,
        max_heartbeats=max_heartbeats,
    )


def check_file(
    *,
    path: Path,
    project_root: Path | None = None,
    timeout_s: float = 30.0,
    use_daemon: bool | None = True,
    auto_spawn: bool = True,
    max_heartbeats: int | None = None,
) -> LeanCheckResult:
    """Type-check a ``.lean`` file by absolute path."""
    abs_path = str(Path(path).resolve())
    if use_daemon and project_root is not None:
        req = LeanCheckRequest(
            op="typecheck_file",
            path=abs_path,
            timeout_s=timeout_s,
            max_heartbeats=max_heartbeats,
        )
        maybe = _run_with_daemon(project_root, req, auto_spawn=auto_spawn)
        if maybe is not None:
            return maybe

    return lean_backend.run_check(
        path=abs_path,
        timeout_s=timeout_s,
        max_heartbeats=max_heartbeats,
    )
