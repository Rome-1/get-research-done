"""Unix-socket daemon for the Lean backend.

The daemon listens on ``<project>/.grd/lean-repl.sock``. Each connection
receives exactly one JSON-line request and sends back one JSON-line response,
then closes. We deliberately do *not* multiplex multiple requests per
connection — it keeps the client side trivial and, since Lean invocations
are relatively expensive, the per-connection overhead is negligible.

Wire format (newline-terminated JSON objects)::

    → {"op": "check", "code": "theorem t : 1 + 1 = 2 := by norm_num",
       "imports": [], "timeout_s": 30.0}
    ← {"ok": true, "diagnostics": [...], "elapsed_ms": 124, ...}

    → {"op": "ping"}
    ← {"ok": true, "elapsed_ms": 0, "backend": "daemon"}

    → {"op": "shutdown"}
    ← {"ok": true, "elapsed_ms": 0, "backend": "daemon"}   (then exits)

Current backend: every ``check`` / ``typecheck_file`` request dispatches to
the one-shot subprocess runner in ``backend.py``. This means the daemon
today provides the socket protocol, lifecycle, and idle shutdown — not
actual REPL reuse. Pantograph-backed REPL reuse lands in a follow-up bead;
clients and the wire protocol will not change.
"""

from __future__ import annotations

import json
import logging
import os
import selectors
import signal
import socket
import sys
import threading
import time
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from grd.core.lean import backend as lean_backend
from grd.core.lean.env import pid_file_path, socket_path
from grd.core.lean.protocol import LeanCheckRequest, LeanCheckResult

__all__ = [
    "DEFAULT_IDLE_TIMEOUT_S",
    "DEFAULT_READ_TIMEOUT_S",
    "LeanDaemon",
    "handle_request",
    "serve",
]


DEFAULT_IDLE_TIMEOUT_S = 10 * 60
"""Seconds with no connections before the daemon shuts itself down."""

DEFAULT_READ_TIMEOUT_S = 60.0
"""Seconds to wait for a client to finish sending its JSON line."""

_MAX_REQUEST_BYTES = 4 * 1024 * 1024
"""Hard cap on request size to avoid unbounded buffering."""

logger = logging.getLogger("grd.lean.daemon")


def handle_request(raw: str) -> LeanCheckResult:
    """Parse a wire-format JSON line and dispatch to the appropriate handler."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        return LeanCheckResult(
            ok=False,
            error="invalid_request",
            error_detail=f"Malformed JSON: {exc.msg} (line {exc.lineno}, col {exc.colno})",
            backend="daemon",
        )

    try:
        req = LeanCheckRequest.model_validate(parsed)
    except PydanticValidationError as exc:
        return LeanCheckResult(
            ok=False,
            error="invalid_request",
            error_detail=f"Schema validation failed: {exc.errors(include_url=False)!r}",
            backend="daemon",
        )

    if req.op == "ping":
        return LeanCheckResult(ok=True, backend="daemon")
    if req.op == "shutdown":
        return LeanCheckResult(ok=True, backend="daemon")

    if req.op == "check":
        if req.code is None:
            return LeanCheckResult(
                ok=False,
                error="invalid_request",
                error_detail="'check' requires 'code'.",
                backend="daemon",
            )
        result = lean_backend.run_check(
            code=req.code,
            imports=list(req.imports),
            timeout_s=req.timeout_s,
        )
    elif req.op == "typecheck_file":
        if req.path is None:
            return LeanCheckResult(
                ok=False,
                error="invalid_request",
                error_detail="'typecheck_file' requires 'path'.",
                backend="daemon",
            )
        result = lean_backend.run_check(
            path=req.path,
            timeout_s=req.timeout_s,
        )
    else:  # pragma: no cover — guarded by the Literal union on req.op
        return LeanCheckResult(
            ok=False,
            error="invalid_request",
            error_detail=f"Unknown op: {req.op}",
            backend="daemon",
        )

    # Preserve the result while re-tagging the backend as 'daemon' so callers
    # can tell the request went through the socket rather than a direct call.
    return result.model_copy(update={"backend": "daemon"})


def _read_json_line(conn: socket.socket, timeout_s: float) -> str | None:
    """Read bytes until newline, up to ``_MAX_REQUEST_BYTES``.

    Returns the decoded string without the trailing newline. Returns ``None``
    on EOF before any data, timeout, or oversize input. The daemon treats
    ``None`` as "client went away" and just closes the connection.
    """
    conn.settimeout(timeout_s)
    buf = bytearray()
    while True:
        try:
            chunk = conn.recv(4096)
        except TimeoutError:
            return None
        except OSError:
            return None
        if not chunk:
            break
        buf.extend(chunk)
        if b"\n" in chunk:
            newline = buf.index(b"\n")
            buf = buf[:newline]
            break
        if len(buf) > _MAX_REQUEST_BYTES:
            return None
    if not buf:
        return None
    try:
        return buf.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _bind_socket(sock_path: Path) -> socket.socket:
    """Create a listening Unix-stream socket at ``sock_path``.

    Removes any stale socket file first (handles uncleanly-exited prior
    daemons). Sets permissions to 0o600 so only the owning user can connect.
    """
    if sock_path.exists():
        try:
            sock_path.unlink()
        except OSError:
            pass
    sock_path.parent.mkdir(parents=True, exist_ok=True)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.setblocking(False)
    srv.bind(str(sock_path))
    os.chmod(sock_path, 0o600)
    srv.listen(8)
    return srv


class LeanDaemon:
    """State container for a running daemon instance.

    Split out from ``serve()`` so tests can drive the accept loop directly
    without the signal-handling and daemonization glue.
    """

    def __init__(
        self,
        *,
        project_root: Path,
        idle_timeout_s: float = DEFAULT_IDLE_TIMEOUT_S,
        read_timeout_s: float = DEFAULT_READ_TIMEOUT_S,
    ) -> None:
        self.project_root = Path(project_root)
        self.idle_timeout_s = idle_timeout_s
        self.read_timeout_s = read_timeout_s
        self.sock_path = socket_path(self.project_root)
        self.pid_path = pid_file_path(self.project_root)
        self._stop = threading.Event()
        self._last_activity = time.monotonic()

    def stop(self) -> None:
        self._stop.set()

    def _write_pid(self) -> None:
        self.pid_path.parent.mkdir(parents=True, exist_ok=True)
        self.pid_path.write_text(str(os.getpid()), encoding="utf-8")

    def _remove_pid(self) -> None:
        try:
            self.pid_path.unlink(missing_ok=True)
        except OSError:
            pass

    def _remove_socket(self) -> None:
        try:
            self.sock_path.unlink(missing_ok=True)
        except OSError:
            pass

    def _serve_one(self, conn: socket.socket) -> bool:
        """Handle a single client connection. Returns True if we should shut down."""
        try:
            raw = _read_json_line(conn, self.read_timeout_s)
            if raw is None:
                return False
            result = handle_request(raw)
            # Determine shutdown *before* sending the response so the client
            # always gets an ack for the shutdown request.
            shutdown_requested = False
            try:
                parsed = json.loads(raw)
                shutdown_requested = isinstance(parsed, dict) and parsed.get("op") == "shutdown"
            except json.JSONDecodeError:
                pass
            payload = (result.model_dump_json() + "\n").encode("utf-8")
            try:
                conn.sendall(payload)
            except OSError:
                pass
            return shutdown_requested
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def run(self) -> None:
        """Blocking accept loop. Returns when stopped or idle timeout fires."""
        srv = _bind_socket(self.sock_path)
        self._write_pid()
        sel = selectors.DefaultSelector()
        sel.register(srv, selectors.EVENT_READ)
        logger.info("grd-lean daemon listening on %s (pid=%s)", self.sock_path, os.getpid())
        try:
            while not self._stop.is_set():
                idle = time.monotonic() - self._last_activity
                remaining = self.idle_timeout_s - idle
                if remaining <= 0:
                    logger.info("grd-lean daemon idle for %.0fs; exiting", idle)
                    break
                events = sel.select(timeout=min(remaining, 5.0))
                if not events:
                    continue
                for key, _mask in events:
                    if key.fileobj is not srv:
                        continue
                    try:
                        conn, _addr = srv.accept()
                    except BlockingIOError:
                        continue
                    conn.setblocking(True)
                    self._last_activity = time.monotonic()
                    shutdown = self._serve_one(conn)
                    if shutdown:
                        logger.info("grd-lean daemon received shutdown op; exiting")
                        return
        finally:
            sel.close()
            try:
                srv.close()
            except OSError:
                pass
            self._remove_socket()
            self._remove_pid()


def serve(
    project_root: Path,
    *,
    idle_timeout_s: float = DEFAULT_IDLE_TIMEOUT_S,
    read_timeout_s: float = DEFAULT_READ_TIMEOUT_S,
) -> None:
    """Blocking entry point — run the daemon until idle or signalled."""
    daemon = LeanDaemon(
        project_root=project_root,
        idle_timeout_s=idle_timeout_s,
        read_timeout_s=read_timeout_s,
    )

    def _handle_signal(_signum: int, _frame: object) -> None:
        daemon.stop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, _handle_signal)
        except (ValueError, OSError):
            # Signal module not available in this thread (e.g. tests).
            pass

    daemon.run()


def _detach_and_serve(
    project_root: Path,
    *,
    idle_timeout_s: float,
    read_timeout_s: float,
    log_path: Path | None,
) -> None:  # pragma: no cover — exercised via integration tests
    """Detach from the controlling terminal and start serving.

    Used when the CLI is invoked with ``serve-repl --detach``.
    """
    # First fork — parent returns to caller.
    if os.fork() > 0:
        return
    # Child — become session leader, then fork again to fully detach.
    os.setsid()
    if os.fork() > 0:
        os._exit(0)
    # Grandchild: redirect std streams.
    os.chdir(str(project_root))
    sys.stdin.close()
    log = open(str(log_path) if log_path else os.devnull, "a", buffering=1)
    os.dup2(log.fileno(), sys.stdout.fileno())
    os.dup2(log.fileno(), sys.stderr.fileno())
    try:
        serve(
            project_root,
            idle_timeout_s=idle_timeout_s,
            read_timeout_s=read_timeout_s,
        )
    except Exception:  # pragma: no cover — defensive
        logger.exception("grd-lean daemon crashed")
    finally:
        os._exit(0)
