"""Tests for grd.core.lean.env — toolchain detection + env file management."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from grd.core.lean import env as lean_env


@pytest.fixture
def isolated_project(tmp_path: Path) -> Path:
    (tmp_path / ".grd").mkdir()
    return tmp_path


def test_env_file_path_lives_under_dot_grd(isolated_project: Path) -> None:
    path = lean_env.env_file_path(isolated_project)
    assert path == isolated_project / ".grd" / "lean-env.json"


def test_socket_path_and_pid_path_are_siblings_of_env_file(isolated_project: Path) -> None:
    env_p = lean_env.env_file_path(isolated_project)
    sock_p = lean_env.socket_path(isolated_project)
    pid_p = lean_env.pid_file_path(isolated_project)
    assert env_p.parent == sock_p.parent == pid_p.parent


def test_load_env_returns_empty_for_missing_file(isolated_project: Path) -> None:
    assert lean_env.load_env(isolated_project) == {}


def test_load_env_returns_empty_for_malformed_json(isolated_project: Path) -> None:
    # Corrupted bootstrap state must never crash subsequent operations —
    # the bootstrap skill will detect the staleness and rewrite.
    env_path = lean_env.env_file_path(isolated_project)
    env_path.write_text("{ this is not JSON", encoding="utf-8")
    assert lean_env.load_env(isolated_project) == {}


def test_save_env_is_atomic_and_creates_parent(tmp_path: Path) -> None:
    # No .grd directory pre-created: save_env must create it.
    lean_env.save_env(tmp_path, {"stage_elan": True, "stage_toolchain": "leanprover/lean4:4.13.0"})
    path = lean_env.env_file_path(tmp_path)
    assert path.is_file()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == {"stage_elan": True, "stage_toolchain": "leanprover/lean4:4.13.0"}


def test_save_env_no_tmp_sibling_left_behind(isolated_project: Path) -> None:
    lean_env.save_env(isolated_project, {"a": 1})
    siblings = list(lean_env.env_file_path(isolated_project).parent.iterdir())
    # Only the one authoritative env file — no *.tmp leftover.
    assert [p.name for p in siblings] == ["lean-env.json"]


def test_detect_toolchain_reports_missing_when_path_is_empty() -> None:
    info = lean_env.detect_toolchain(env={"PATH": "/this/path/does/not/exist"})
    assert info.lean_found is False
    assert info.lean_path is None
    assert info.elan_path is None
    assert info.lake_path is None


def test_detect_toolchain_finds_stub_binary(tmp_path: Path) -> None:
    """When a fake lean binary is on PATH, detection must find it."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_lean = bin_dir / "lean"
    fake_lean.write_text(
        "#!/bin/bash\necho 'Lean (version 4.0.0-fake, commit abc, Release)'\n",
        encoding="utf-8",
    )
    fake_lean.chmod(fake_lean.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    info = lean_env.detect_toolchain(env={"PATH": str(bin_dir)})
    assert info.lean_found is True
    assert info.lean_path == str(fake_lean)
    assert info.lean_version is not None
    assert "Lean" in info.lean_version


def test_compute_env_status_when_no_daemon_running(isolated_project: Path) -> None:
    status = lean_env.compute_env_status(isolated_project)
    assert status.daemon_running is False
    assert status.daemon_pid is None
    assert status.env_file_exists is False
    assert status.socket_path == str(lean_env.socket_path(isolated_project))


def test_compute_env_status_reports_stale_pid_as_not_running(isolated_project: Path) -> None:
    # Write a PID file pointing at an impossible PID; socket does not exist.
    pid_file = lean_env.pid_file_path(isolated_project)
    pid_file.write_text("2147483647", encoding="utf-8")
    status = lean_env.compute_env_status(isolated_project)
    assert status.daemon_running is False


def test_pantograph_available_returns_bool() -> None:
    # We don't mandate Pantograph be installed in CI — just that the probe
    # returns a plain bool without raising.
    result = lean_env.pantograph_available()
    assert isinstance(result, bool)
