"""CLI-level tests for ``grd lean stub-claim``.

Uses ``--no-llm`` so we don't need an Anthropic key; monkeypatches the
underlying ``stub_claim`` for the success path so we control the result.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from grd.cli import app
from grd.core.lean.autoformalize.stub import StubClaimResult

runner = CliRunner()


def test_help_mentions_stub_claim() -> None:
    result = runner.invoke(app, ["lean", "--help"])
    assert result.exit_code == 0
    assert "stub-claim" in result.stdout


def test_stub_claim_help_covers_flags() -> None:
    result = runner.invoke(app, ["lean", "stub-claim", "--help"])
    assert result.exit_code == 0
    for flag in ("--physics", "--no-physics", "--import", "--no-llm"):
        assert flag in result.stdout


def test_stub_claim_no_llm_exits_zero_with_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".grd").mkdir()

    stub_result = StubClaimResult(
        claim="pi is irrational",
        skeleton="theorem pi_irrational : Irrational Real.pi := sorry",
        retrieval_hits=["Real.pi", "Irrational"],
        suggested_imports=["Mathlib.Data.Real.Pi"],
        next_steps=["Typecheck: grd lean check"],
        index_source="test",
        notes=[],
    )

    captured: dict[str, object] = {}

    def _fake_stub(**kwargs: object) -> StubClaimResult:
        captured.update(kwargs)
        return stub_result

    monkeypatch.setattr(
        "grd.core.lean.autoformalize.stub_claim",
        _fake_stub,
    )

    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "stub-claim",
            "pi is irrational",
            "--no-llm",
        ],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed["claim"] == "pi is irrational"
    assert "sorry" in parsed["skeleton"]
    assert parsed["retrieval_hits"] == ["Real.pi", "Irrational"]
    assert parsed["suggested_imports"] == ["Mathlib.Data.Real.Pi"]
    assert captured["claim"] == "pi is irrational"


def test_stub_claim_physics_and_no_physics_conflict(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "lean",
            "stub-claim",
            "x",
            "--physics",
            "--no-physics",
            "--no-llm",
        ],
    )
    assert result.exit_code == 2


def test_stub_claim_no_llm_dry_run_produces_placeholder(tmp_path: Path) -> None:
    """--no-llm must produce a recognizable placeholder skeleton."""
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "stub-claim",
            "every prime is greater than one",
            "--no-llm",
        ],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert "sorry" in parsed["skeleton"]
    assert "stub_claim_placeholder" in parsed["skeleton"]


def test_stub_claim_human_output_shows_skeleton(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-raw mode must surface the skeleton in the terminal output."""
    (tmp_path / ".grd").mkdir()

    stub_result = StubClaimResult(
        claim="x",
        skeleton="theorem foo : True := sorry",
        retrieval_hits=["Real.pi"],
        suggested_imports=["Mathlib.Tactic"],
        next_steps=["Try grd lean check"],
        index_source="",
        notes=[],
    )
    monkeypatch.setattr("grd.core.lean.autoformalize.stub_claim", lambda **_kw: stub_result)

    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "lean", "stub-claim", "x", "--no-llm"],
    )
    assert result.exit_code == 0
    # CliRunner merges stderr into stdout — human output goes to err_console.
    assert "theorem foo" in result.output
    assert "Real.pi" in result.output
    assert "Mathlib.Tactic" in result.output
