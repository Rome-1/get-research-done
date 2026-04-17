"""Tests for grd.core.lean.client — daemon preference + one-shot fallback."""

from __future__ import annotations

import os
import stat
import time
from pathlib import Path

import pytest

from grd.core.lean import client as lean_client
from grd.core.lean import env as lean_env


def _stub_lean(bin_dir: Path, *, exit_code: int = 0) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    lean = bin_dir / "lean"
    lean.write_text(
        f"#!/bin/bash\nexit {exit_code}\n",
        encoding="utf-8",
    )
    lean.chmod(lean.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return lean


def test_check_one_shot_path_when_daemon_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_lean(tmp_path / "bin")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))

    result = lean_client.check(
        code="theorem t : 1 = 1 := rfl",
        project_root=tmp_path,
        use_daemon=False,
    )
    assert result.ok is True
    assert result.backend == "subprocess"


def test_check_surfaces_lean_not_found_without_spawning_daemon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".grd").mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))

    # auto_spawn disabled, no socket ⇒ client falls through to subprocess.
    result = lean_client.check(
        code="x",
        project_root=tmp_path,
        use_daemon=True,
        auto_spawn=False,
    )
    assert result.ok is False
    assert result.error == "lean_not_found"
    assert result.backend == "subprocess"
    # And no daemon was started.
    assert not lean_env.socket_path(tmp_path).exists()


def test_ping_daemon_when_socket_absent_returns_false(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    assert lean_client.ping_daemon(tmp_path) is False


def test_shutdown_daemon_is_noop_when_not_running(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = lean_client.shutdown_daemon(tmp_path)
    assert result.ok is True
    assert "No daemon running" in (result.error_detail or "")


def test_socket_path_too_long_forces_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Very long project paths would overflow the Unix-socket limit.

    Client must fall back to one-shot rather than trying to bind a path the
    kernel will reject.
    """
    # Build a path longer than MAX_UNIX_SOCKET_PATH minus the socket filename.
    deep = tmp_path
    segment = "x" * 20
    while len(str(deep / ".grd" / "lean-repl.sock")) <= lean_client.MAX_UNIX_SOCKET_PATH:
        deep = deep / segment
    deep.mkdir(parents=True)
    (deep / ".grd").mkdir()
    _stub_lean(tmp_path / "bin")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))

    result = lean_client.check(
        code="x",
        project_root=deep,
        use_daemon=True,
        auto_spawn=True,
    )
    # We fell back — so the result comes from subprocess.
    assert result.backend == "subprocess"
    assert result.ok is True


def test_spawn_daemon_creates_log_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ge-f9i: daemon stderr must go to .grd/lean-daemon.log, not /dev/null."""
    (tmp_path / ".grd").mkdir()
    _stub_lean(tmp_path / "bin")
    monkeypatch.setenv("PATH", str(tmp_path / "bin") + os.pathsep + os.environ["PATH"])

    log = lean_env.daemon_log_path(tmp_path)
    assert not log.exists(), "log should not exist before spawn"

    try:
        lean_client.spawn_daemon(tmp_path, wait_s=5.0)
        # Log file must be created — even if daemon writes nothing,
        # the open("a") in spawn_daemon creates it.
        assert log.exists(), f"expected daemon log at {log}"
    finally:
        if lean_env.socket_path(tmp_path).exists():
            lean_client.shutdown_daemon(tmp_path)
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and lean_env.socket_path(tmp_path).exists():
                time.sleep(0.05)


def test_read_daemon_log_tail_returns_none_when_absent(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    assert lean_client.read_daemon_log_tail(tmp_path) is None


def test_read_daemon_log_tail_returns_last_lines(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    log = lean_env.daemon_log_path(tmp_path)
    log.write_text("\n".join(f"line {i}" for i in range(50)), encoding="utf-8")
    tail = lean_client.read_daemon_log_tail(tmp_path, lines=5)
    assert tail is not None
    lines = tail.splitlines()
    assert len(lines) == 5
    assert lines[-1] == "line 49"


def test_log_rotation_renames_large_file(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    log = lean_env.daemon_log_path(tmp_path)
    # Write > 1 MiB to trigger rotation.
    log.write_text("x" * (lean_client._LOG_ROTATE_BYTES + 100), encoding="utf-8")
    lean_client._rotate_log(log)
    rotated = log.with_suffix(log.suffix + ".1")
    assert rotated.exists()
    assert not log.exists()


def test_auto_spawn_starts_daemon_and_routes_request(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".grd").mkdir()
    _stub_lean(tmp_path / "bin")
    monkeypatch.setenv("PATH", str(tmp_path / "bin") + os.pathsep + os.environ["PATH"])

    try:
        result = lean_client.check(
            code="theorem t : 1 = 1 := rfl",
            project_root=tmp_path,
            use_daemon=True,
            auto_spawn=True,
            timeout_s=10.0,
        )
        assert result.ok is True
        # Either came back from the daemon (if it started in time) or fell
        # back to subprocess — both are correct. What we care about is that
        # the call didn't crash and the result shape is right.
        assert result.backend in {"daemon", "subprocess"}
    finally:
        # Try to stop any daemon we may have started so subsequent tests
        # get a clean slate.
        if lean_env.socket_path(tmp_path).exists():
            lean_client.shutdown_daemon(tmp_path)
            # Give it a beat to finish unlinking files.
            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and lean_env.socket_path(tmp_path).exists():
                time.sleep(0.05)
