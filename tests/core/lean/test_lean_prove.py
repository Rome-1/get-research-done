"""Tests for ``grd.core.lean.prove`` — MVP tactic-search ladder (ge-8cn)."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
from typer.testing import CliRunner

from grd.cli import app
from grd.core.lean import prove as lean_prove
from grd.core.lean.protocol import LeanCheckResult, LeanDiagnostic

runner = CliRunner()


# ─── Source composition ──────────────────────────────────────────────────────


def test_compose_attempt_source_wraps_bare_proposition_as_example() -> None:
    src = lean_prove.compose_attempt_source("1 + 1 = 2", "norm_num")
    assert "example : 1 + 1 = 2 := by norm_num" in src


def test_compose_attempt_source_accepts_keyword_header() -> None:
    src = lean_prove.compose_attempt_source("theorem foo : 1 + 1 = 2", "norm_num")
    assert "theorem foo : 1 + 1 = 2 := by norm_num" in src


def test_compose_attempt_source_rewrites_existing_definition_tail() -> None:
    """Full definitions (e.g. with `sorry`) get the ':=' tail replaced."""
    src = lean_prove.compose_attempt_source("theorem foo : 1 + 1 = 2 := sorry", "rfl")
    assert "theorem foo : 1 + 1 = 2 := by rfl" in src
    assert "sorry" not in src


def test_compose_attempt_source_prepends_imports() -> None:
    src = lean_prove.compose_attempt_source(
        "1 + 1 = 2",
        "norm_num",
        imports=["Mathlib.Tactic", "Mathlib.Data.Nat.Basic"],
    )
    assert src.startswith("import Mathlib.Tactic\nimport Mathlib.Data.Nat.Basic\n")
    assert "example : 1 + 1 = 2 := by norm_num" in src


def test_compose_attempt_source_rejects_empty_statement() -> None:
    with pytest.raises(ValueError, match="empty"):
        lean_prove.compose_attempt_source("   ", "rfl")


# ─── Tactic-search core ──────────────────────────────────────────────────────


def _fake_check(*, ok_on: str | None) -> callable:
    """Return a stub for ``lean_client.check`` that passes only on *ok_on*."""

    def _impl(*, code: str, **_kwargs) -> LeanCheckResult:
        if ok_on and f":= by {ok_on}" in code:
            return LeanCheckResult(ok=True, backend="subprocess", elapsed_ms=5)
        return LeanCheckResult(
            ok=False,
            backend="subprocess",
            elapsed_ms=7,
            diagnostics=[LeanDiagnostic(severity="error", message="tactic failed")],
        )

    return _impl


def test_prove_statement_returns_first_passing_tactic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With the default ladder, the first tactic that type-checks wins."""
    monkeypatch.setattr(lean_prove, "lean_check", _fake_check(ok_on="norm_num"))

    result = lean_prove.prove_statement("1 + 1 = 2", project_root=tmp_path)
    assert result.ok is True
    assert result.proof is not None
    assert ":= by norm_num" in result.proof

    # Only the tactics tried up to and including norm_num appear.
    tactics_run = [a.tactic for a in result.attempts]
    assert tactics_run == ["rfl", "decide", "norm_num"]
    assert result.attempts[-1].ok is True
    assert result.attempts[-1].error_summary is None
    assert result.attempts[0].error_summary == "tactic failed"


def test_prove_statement_reports_failure_with_every_attempt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(lean_prove, "lean_check", _fake_check(ok_on=None))

    result = lean_prove.prove_statement(
        "1 + 1 = 3",
        project_root=tmp_path,
        tactics=["rfl", "norm_num", "ring"],
    )
    assert result.ok is False
    assert result.proof is None
    assert [a.tactic for a in result.attempts] == ["rfl", "norm_num", "ring"]
    assert all(a.ok is False for a in result.attempts)
    assert result.total_elapsed_ms == sum(a.elapsed_ms for a in result.attempts)


def test_prove_statement_respects_max_attempts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(lean_prove, "lean_check", _fake_check(ok_on=None))

    result = lean_prove.prove_statement(
        "False",
        project_root=tmp_path,
        max_attempts=2,
    )
    assert [a.tactic for a in result.attempts] == ["rfl", "decide"]
    assert result.ok is False


def test_prove_statement_rejects_nonpositive_max_attempts(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=">= 1"):
        lean_prove.prove_statement("p", project_root=tmp_path, max_attempts=0)


def test_prove_statement_surfaces_orchestration_error_summary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _lean_missing(**_kwargs) -> LeanCheckResult:
        return LeanCheckResult(
            ok=False,
            backend="subprocess",
            error="lean_not_found",
            error_detail="PATH had no lean binary",
            elapsed_ms=1,
        )

    monkeypatch.setattr(lean_prove, "lean_check", _lean_missing)
    result = lean_prove.prove_statement("P", project_root=tmp_path, tactics=["rfl"])
    assert result.ok is False
    summary = result.attempts[0].error_summary or ""
    assert "lean_not_found" in summary


# ─── CLI wiring ──────────────────────────────────────────────────────────────


def _stub_lean_ok(bin_dir: Path) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "lean"
    script.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_cli_prove_emits_structured_json_on_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".grd").mkdir()
    _stub_lean_ok(tmp_path / "bin")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))

    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "prove",
            "1 = 1",
            "--no-daemon",
            "--max-attempts",
            "1",
        ],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is True
    assert parsed["statement"] == "1 = 1"
    assert len(parsed["attempts"]) == 1
    assert parsed["attempts"][0]["tactic"] == "rfl"
    assert parsed["proof"].rstrip().endswith(":= by rfl")


def test_cli_prove_exit_1_when_no_tactic_closes_goal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".grd").mkdir()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "lean"
    script.write_text("#!/bin/bash\nexit 1\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    monkeypatch.setenv("PATH", str(bin_dir))

    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "prove",
            "False",
            "--no-daemon",
            "--tactic",
            "rfl",
            "--tactic",
            "decide",
        ],
    )
    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is False
    assert [a["tactic"] for a in parsed["attempts"]] == ["rfl", "decide"]
