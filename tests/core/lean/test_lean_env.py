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


def _stub_binary(bin_dir: Path, name: str, *, banner: str = "") -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / name
    body = f"#!/bin/bash\necho '{banner}'\n" if banner else "#!/bin/bash\nexit 0\n"
    script.write_text(body, encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return script


def test_compute_env_status_ready_false_when_nothing_installed(
    isolated_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PATH", "/this/path/does/not/exist")
    status = lean_env.compute_env_status(isolated_project)
    assert status.ready is False
    # Every core component should appear. pantograph availability is environment-
    # dependent in CI, so we only assert that the three binary names are present.
    for name in ("elan", "lean", "lake"):
        assert name in status.blocked_by


def test_compute_env_status_ready_true_when_all_core_components_present(
    isolated_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bin_dir = isolated_project / "bin"
    _stub_binary(bin_dir, "lean", banner="Lean (version 4.0.0-fake)")
    _stub_binary(bin_dir, "elan", banner="elan 3.0.0")
    _stub_binary(bin_dir, "lake", banner="Lake 5.0.0")
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setattr(lean_env, "pantograph_available", lambda: True)

    status = lean_env.compute_env_status(isolated_project)
    assert status.blocked_by == []
    assert status.ready is True


def test_compute_env_status_blocks_on_pantograph_only(
    isolated_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bin_dir = isolated_project / "bin"
    _stub_binary(bin_dir, "lean", banner="Lean (version 4.0.0-fake)")
    _stub_binary(bin_dir, "elan", banner="elan 3.0.0")
    _stub_binary(bin_dir, "lake", banner="Lake 5.0.0")
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setattr(lean_env, "pantograph_available", lambda: False)

    status = lean_env.compute_env_status(isolated_project)
    assert status.ready is False
    assert status.blocked_by == ["pantograph"]


def test_compute_env_status_ignores_mathlib_cache_when_not_opted_in(
    isolated_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Core components all present, user has not opted into mathlib-cache —
    # the cache must NOT appear in blocked_by because it's opt-in only.
    bin_dir = isolated_project / "bin"
    _stub_binary(bin_dir, "lean", banner="Lean (version 4.0.0-fake)")
    _stub_binary(bin_dir, "elan", banner="elan 3.0.0")
    _stub_binary(bin_dir, "lake", banner="Lake 5.0.0")
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setattr(lean_env, "pantograph_available", lambda: True)
    lean_env.save_env(
        isolated_project,
        {
            "options": {"with_mathlib_cache": False},
            "stages": [],
        },
    )

    status = lean_env.compute_env_status(isolated_project)
    assert status.ready is True
    assert "mathlib-cache" not in status.blocked_by


def test_compute_env_status_blocks_on_mathlib_cache_when_opted_in_but_missing(
    isolated_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # User opted in (`with_mathlib_cache=True`) but the stage record is
    # absent → cache download hasn't completed yet → block.
    bin_dir = isolated_project / "bin"
    _stub_binary(bin_dir, "lean", banner="Lean (version 4.0.0-fake)")
    _stub_binary(bin_dir, "elan", banner="elan 3.0.0")
    _stub_binary(bin_dir, "lake", banner="Lake 5.0.0")
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setattr(lean_env, "pantograph_available", lambda: True)
    lean_env.save_env(
        isolated_project,
        {
            "options": {"with_mathlib_cache": True},
            "stages": [],
        },
    )

    status = lean_env.compute_env_status(isolated_project)
    assert status.ready is False
    assert status.blocked_by == ["mathlib-cache"]


def test_compute_env_status_clears_mathlib_block_when_stage_ok(
    isolated_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bin_dir = isolated_project / "bin"
    _stub_binary(bin_dir, "lean", banner="Lean (version 4.0.0-fake)")
    _stub_binary(bin_dir, "elan", banner="elan 3.0.0")
    _stub_binary(bin_dir, "lake", banner="Lake 5.0.0")
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setattr(lean_env, "pantograph_available", lambda: True)
    lean_env.save_env(
        isolated_project,
        {
            "options": {"with_mathlib_cache": True},
            "stages": [
                {"name": "mathlib_cache", "status": "ok", "detail": "downloaded"},
            ],
        },
    )

    status = lean_env.compute_env_status(isolated_project)
    assert status.ready is True
    assert status.blocked_by == []


def test_compute_env_status_daemon_state_does_not_affect_ready(
    isolated_project: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A stopped daemon must not block readiness — the client auto-spawns.
    bin_dir = isolated_project / "bin"
    _stub_binary(bin_dir, "lean", banner="Lean (version 4.0.0-fake)")
    _stub_binary(bin_dir, "elan", banner="elan 3.0.0")
    _stub_binary(bin_dir, "lake", banner="Lake 5.0.0")
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setattr(lean_env, "pantograph_available", lambda: True)

    status = lean_env.compute_env_status(isolated_project)
    assert status.daemon_running is False
    assert status.ready is True
