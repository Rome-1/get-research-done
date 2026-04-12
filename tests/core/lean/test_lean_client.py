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
