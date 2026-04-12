"""Tests for grd.core.lean.daemon — request dispatch + socket lifecycle.

The ``handle_request`` tests run in-process and are fast. The
``serve()`` lifecycle tests spin up an in-process thread and exercise the
real Unix-socket protocol against a stub Lean binary.
"""

from __future__ import annotations

import json
import os
import socket
import stat
import threading
import time
from pathlib import Path

import pytest

from grd.core.lean import daemon as lean_daemon
from grd.core.lean.env import pid_file_path, socket_path
from grd.core.lean.protocol import LeanCheckResult


def _stub_lean(bin_dir: Path, *, stdout: str = "", stderr: str = "", exit_code: int = 0) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    lean = bin_dir / "lean"
    lean.write_text(
        f"#!/bin/bash\ncat <<'__OUT__'\n{stdout}\n__OUT__\ncat <<'__ERR__' 1>&2\n{stderr}\n__ERR__\nexit {exit_code}\n",
        encoding="utf-8",
    )
    lean.chmod(lean.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return lean


class TestHandleRequest:
    def test_malformed_json_returns_invalid_request(self) -> None:
        result = lean_daemon.handle_request("{ not valid")
        assert result.ok is False
        assert result.error == "invalid_request"
        assert "Malformed JSON" in (result.error_detail or "")
        assert result.backend == "daemon"

    def test_unknown_op_rejected(self) -> None:
        result = lean_daemon.handle_request(json.dumps({"op": "delete_everything"}))
        assert result.ok is False
        assert result.error == "invalid_request"

    def test_check_without_code_is_invalid(self) -> None:
        result = lean_daemon.handle_request(json.dumps({"op": "check"}))
        assert result.ok is False
        assert result.error == "invalid_request"
        assert "'check' requires 'code'" in (result.error_detail or "")

    def test_typecheck_file_without_path_is_invalid(self) -> None:
        result = lean_daemon.handle_request(json.dumps({"op": "typecheck_file"}))
        assert result.ok is False
        assert result.error == "invalid_request"
        assert "'typecheck_file' requires 'path'" in (result.error_detail or "")

    def test_ping_responds_ok(self) -> None:
        result = lean_daemon.handle_request(json.dumps({"op": "ping"}))
        assert result.ok is True
        assert result.error is None
        assert result.backend == "daemon"

    def test_shutdown_responds_ok(self) -> None:
        result = lean_daemon.handle_request(json.dumps({"op": "shutdown"}))
        assert result.ok is True
        assert result.backend == "daemon"


class TestServeLifecycle:
    """Run a real daemon in a background thread + probe it via the socket."""

    def _start_thread(
        self,
        project_root: Path,
        *,
        idle_timeout_s: float = 2.0,
    ) -> tuple[lean_daemon.LeanDaemon, threading.Thread]:
        daemon = lean_daemon.LeanDaemon(
            project_root=project_root,
            idle_timeout_s=idle_timeout_s,
            read_timeout_s=2.0,
        )
        thread = threading.Thread(target=daemon.run, daemon=True)
        thread.start()
        # Wait for a live listening socket. Poll by attempting a connection —
        # just checking for a file at the path is insufficient because a
        # prior stale *file* (non-socket) can exist before the daemon binds.
        sock = socket_path(project_root)
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if sock.exists():
                probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                probe.settimeout(0.2)
                try:
                    probe.connect(str(sock))
                    probe.close()
                    return daemon, thread
                except OSError:
                    probe.close()
            time.sleep(0.02)
        raise AssertionError("daemon never produced a live listening socket")

    def _send(
        self,
        project_root: Path,
        payload: dict,
        *,
        timeout: float = 3.0,
    ) -> LeanCheckResult:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect(str(socket_path(project_root)))
        try:
            s.sendall((json.dumps(payload) + "\n").encode("utf-8"))
            buf = bytearray()
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf.extend(chunk)
                if b"\n" in buf:
                    break
            line = buf.split(b"\n", 1)[0].decode("utf-8")
            return LeanCheckResult.model_validate_json(line)
        finally:
            s.close()

    def test_ping_over_socket(self, tmp_path: Path) -> None:
        (tmp_path / ".grd").mkdir()
        daemon, thread = self._start_thread(tmp_path, idle_timeout_s=3.0)
        try:
            assert pid_file_path(tmp_path).exists()
            result = self._send(tmp_path, {"op": "ping"})
            assert result.ok is True
            assert result.backend == "daemon"
        finally:
            daemon.stop()
            thread.join(timeout=5)

    def test_check_routes_through_stub_lean(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / ".grd").mkdir()
        _stub_lean(tmp_path / "bin", exit_code=0)
        monkeypatch.setenv("PATH", str(tmp_path / "bin") + os.pathsep + os.environ["PATH"])

        daemon, thread = self._start_thread(tmp_path, idle_timeout_s=3.0)
        try:
            result = self._send(
                tmp_path,
                {"op": "check", "code": "theorem t : 1 = 1 := rfl"},
                timeout=10.0,
            )
            # Stub lean exits 0 with no diagnostics ⇒ ok=True.
            assert result.ok is True
            assert result.backend == "daemon"
        finally:
            daemon.stop()
            thread.join(timeout=5)

    def test_shutdown_op_exits_daemon(self, tmp_path: Path) -> None:
        (tmp_path / ".grd").mkdir()
        daemon, thread = self._start_thread(tmp_path, idle_timeout_s=30.0)
        sock = socket_path(tmp_path)
        try:
            result = self._send(tmp_path, {"op": "shutdown"})
            assert result.ok is True
            # Thread should exit quickly after shutdown.
            thread.join(timeout=5)
            assert not thread.is_alive()
            # Socket + pid file cleaned up on exit.
            assert not sock.exists()
            assert not pid_file_path(tmp_path).exists()
        finally:
            # In case the thread is still alive for some reason, stop it.
            daemon.stop()
            thread.join(timeout=5)

    def test_idle_timeout_triggers_shutdown(self, tmp_path: Path) -> None:
        (tmp_path / ".grd").mkdir()
        # Very short idle — daemon should exit on its own without any requests.
        daemon, thread = self._start_thread(tmp_path, idle_timeout_s=0.5)
        try:
            thread.join(timeout=5)
            assert not thread.is_alive(), "daemon did not exit on idle timeout"
            assert not socket_path(tmp_path).exists()
        finally:
            daemon.stop()
            thread.join(timeout=2)

    def test_stale_socket_file_is_replaced(self, tmp_path: Path) -> None:
        """A prior crashed daemon left a socket behind — we must reclaim it."""
        (tmp_path / ".grd").mkdir()
        sock = socket_path(tmp_path)
        # Leave a regular file (not a socket) at the path.
        sock.write_text("stale", encoding="utf-8")
        daemon, thread = self._start_thread(tmp_path, idle_timeout_s=1.0)
        try:
            result = self._send(tmp_path, {"op": "ping"})
            assert result.ok is True
        finally:
            daemon.stop()
            thread.join(timeout=5)
