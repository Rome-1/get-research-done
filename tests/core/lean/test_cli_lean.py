"""Tests for the ``grd lean`` CLI surface."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
from typer.testing import CliRunner

from grd.cli import app

runner = CliRunner()


def _stub_lean(bin_dir: Path, *, exit_code: int = 0) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    lean = bin_dir / "lean"
    lean.write_text(
        f"#!/bin/bash\nexit {exit_code}\n",
        encoding="utf-8",
    )
    lean.chmod(lean.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return lean


def test_help_lists_lean_subcommands() -> None:
    result = runner.invoke(app, ["lean", "--help"])
    assert result.exit_code == 0
    for cmd in ("check", "typecheck-file", "env", "serve-repl", "stop-repl", "ping", "bootstrap"):
        assert cmd in result.stdout


def test_env_command_raw_emits_valid_json(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(app, ["--raw", "--cwd", str(tmp_path), "lean", "env"])
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert "lean_found" in parsed
    assert "daemon_running" in parsed
    assert parsed["env_file"].endswith("/.grd/lean-env.json")


def test_check_with_missing_lean_exits_nonzero_and_emits_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".grd").mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "check",
            "theorem t : 1 = 1 := rfl",
            "--no-daemon",
        ],
    )
    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is False
    assert parsed["error"] == "lean_not_found"


def test_check_with_stub_lean_exits_zero_no_daemon(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".grd").mkdir()
    _stub_lean(tmp_path / "bin")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "check",
            "theorem t : 1 = 1 := rfl",
            "--no-daemon",
        ],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is True
    assert parsed["backend"] == "subprocess"


def test_check_rejects_both_inline_code_and_file(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    lean_file = tmp_path / "x.lean"
    lean_file.write_text("theorem t : 1 = 1 := rfl\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "lean",
            "check",
            "inline code",
            "--file",
            str(lean_file),
        ],
    )
    assert result.exit_code != 0


def test_typecheck_file_nonexistent_errors(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "lean",
            "typecheck-file",
            str(tmp_path / "nope.lean"),
        ],
    )
    assert result.exit_code != 0


def test_ping_when_no_daemon_exits_nonzero(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(app, ["--raw", "--cwd", str(tmp_path), "lean", "ping"])
    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is False
    assert parsed["alive"] is False


def test_stop_repl_is_noop_when_no_daemon(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(app, ["--raw", "--cwd", str(tmp_path), "lean", "stop-repl"])
    assert result.exit_code == 0, result.stdout


def test_bootstrap_dry_run_emits_structured_report(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(app, ["--raw", "--cwd", str(tmp_path), "lean", "bootstrap", "--dry-run"])
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert "stages" in parsed
    assert parsed["ok"] is True
    stage_names = [s["name"] for s in parsed["stages"]]
    assert "elan" in stage_names
    assert "toolchain" in stage_names
    assert "pantograph" in stage_names


def test_bootstrap_uninstall_dry_run(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(
        app,
        ["--raw", "--cwd", str(tmp_path), "lean", "bootstrap", "--uninstall", "--dry-run"],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed["dry_run"] is True
    assert isinstance(parsed["paths"], list)
