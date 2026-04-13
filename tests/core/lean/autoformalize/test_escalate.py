"""Tests for ``grd.core.lean.autoformalize.escalate``.

Covers the ``bd CLI missing`` graceful-degradation path, JSON parsing of
``bd create`` output, and dry-run (command captured but not executed).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from grd.core.lean.autoformalize import escalate as escalate_module
from grd.core.lean.autoformalize.escalate import escalate_to_human


def test_missing_bd_returns_unattempted_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(escalate_module.shutil, "which", lambda _bin: None)
    result = escalate_to_human(title="t", body="b", project_root=tmp_path)
    assert result.attempted is False
    assert result.bead_id is None
    assert result.error is not None
    assert "bd CLI not found" in result.error


def test_dry_run_skips_subprocess(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(escalate_module.shutil, "which", lambda _bin: "/fake/bd")

    def _boom(*_a: object, **_kw: object) -> None:
        raise AssertionError("subprocess.run must not be called in dry_run")

    monkeypatch.setattr(escalate_module.subprocess, "run", _boom)
    result = escalate_to_human(
        title="review needed",
        body="body",
        project_root=tmp_path,
        dry_run=True,
    )
    assert result.attempted is False
    assert result.bead_id is None
    # Command tuple should encode the full intended invocation.
    assert "/fake/bd" in result.command
    assert "-l" in result.command
    assert "human" in result.command
    assert "--title" in result.command


class _CompletedProcess:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_parses_bead_id_from_json_object(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(escalate_module.shutil, "which", lambda _bin: "/fake/bd")
    monkeypatch.setattr(
        escalate_module.subprocess,
        "run",
        lambda *_a, **_kw: _CompletedProcess(0, stdout='{"id":"ge-xyz"}'),
    )
    result = escalate_to_human(title="t", body="b", project_root=tmp_path)
    assert result.attempted is True
    assert result.bead_id == "ge-xyz"
    assert result.error is None


def test_parses_bead_id_from_json_list(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(escalate_module.shutil, "which", lambda _bin: "/fake/bd")
    monkeypatch.setattr(
        escalate_module.subprocess,
        "run",
        lambda *_a, **_kw: _CompletedProcess(0, stdout='[{"id":"ge-abc"}]'),
    )
    result = escalate_to_human(title="t", body="b", project_root=tmp_path)
    assert result.bead_id == "ge-abc"


def test_falls_back_to_first_token_when_json_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When ``bd`` prints a confirmation line like 'ge-xxx: created', pick the id."""
    monkeypatch.setattr(escalate_module.shutil, "which", lambda _bin: "/fake/bd")
    monkeypatch.setattr(
        escalate_module.subprocess,
        "run",
        lambda *_a, **_kw: _CompletedProcess(0, stdout="ge-001 created\n"),
    )
    result = escalate_to_human(title="t", body="b", project_root=tmp_path)
    assert result.bead_id == "ge-001"


def test_nonzero_exit_records_stderr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(escalate_module.shutil, "which", lambda _bin: "/fake/bd")
    monkeypatch.setattr(
        escalate_module.subprocess,
        "run",
        lambda *_a, **_kw: _CompletedProcess(2, stdout="", stderr="dolt down"),
    )
    result = escalate_to_human(title="t", body="b", project_root=tmp_path)
    assert result.attempted is True
    assert result.bead_id is None
    assert result.error is not None
    assert "dolt down" in result.error


def test_subprocess_timeout_reports_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(escalate_module.shutil, "which", lambda _bin: "/fake/bd")

    def _timeout(*_a: object, **_kw: object) -> None:
        raise subprocess.TimeoutExpired(cmd="bd", timeout=30.0)

    monkeypatch.setattr(escalate_module.subprocess, "run", _timeout)
    result = escalate_to_human(title="t", body="b", project_root=tmp_path)
    assert result.attempted is True
    assert result.bead_id is None
    assert result.error is not None
    assert "bd create failed" in result.error
