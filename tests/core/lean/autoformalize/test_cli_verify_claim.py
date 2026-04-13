"""CLI-level tests for ``grd lean verify-claim``.

Uses ``--no-llm`` so we don't need an Anthropic key; monkeypatches the
underlying ``verify_claim`` for the success path so we control the result.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from grd.cli import app
from grd.core.lean.autoformalize.pipeline import VerifyClaimResult

runner = CliRunner()


def test_help_mentions_verify_claim() -> None:
    result = runner.invoke(app, ["lean", "--help"])
    assert result.exit_code == 0
    assert "verify-claim" in result.stdout


def test_verify_claim_help_covers_flags() -> None:
    result = runner.invoke(app, ["lean", "verify-claim", "--help"])
    assert result.exit_code == 0
    for flag in ("--phase", "--physics", "--no-physics", "--import", "--timeout", "--no-daemon", "--no-llm"):
        assert flag in result.stdout


def test_auto_accept_exits_zero_with_expected_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".grd").mkdir()

    stub_result = VerifyClaimResult(
        claim="pi is irrational",
        outcome="auto_accept",
        chosen_source="theorem foo : True := trivial",
        chosen_back_translation="pi is irrational",
        chosen_similarity=0.95,
        candidates=[],
        blueprint=None,
        index_source="",
        escalation=None,
        notes=[],
    )

    captured: dict[str, object] = {}

    def _fake_verify(**kwargs: object) -> VerifyClaimResult:
        captured.update(kwargs)
        return stub_result

    monkeypatch.setattr(
        "grd.core.lean.autoformalize.verify_claim",
        _fake_verify,
    )

    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "verify-claim",
            "pi is irrational",
            "--no-llm",
        ],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed["outcome"] == "auto_accept"
    assert parsed["chosen_source"] == "theorem foo : True := trivial"
    assert parsed["chosen_similarity"] == 0.95
    # Verify the CLI threaded the claim through to the pipeline.
    assert captured["claim"] == "pi is irrational"


def test_low_confidence_exits_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".grd").mkdir()

    stub_result = VerifyClaimResult(
        claim="x",
        outcome="escalate",
        chosen_source=None,
        chosen_back_translation=None,
        chosen_similarity=0.2,
        candidates=[],
        blueprint=None,
        index_source="",
        escalation=None,
        notes=["no candidate compiled within repair budget"],
    )

    monkeypatch.setattr(
        "grd.core.lean.autoformalize.verify_claim",
        lambda **_kw: stub_result,
    )

    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "verify-claim",
            "x",
            "--no-llm",
        ],
    )
    # Non-auto-accept outcomes must exit 1 so CI gates treat them as failure.
    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    assert parsed["outcome"] == "escalate"


def test_physics_and_no_physics_are_mutually_exclusive(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "lean",
            "verify-claim",
            "x",
            "--physics",
            "--no-physics",
            "--no-llm",
        ],
    )
    assert result.exit_code != 0


def test_physics_override_propagates_to_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".grd").mkdir()

    captured: dict[str, object] = {}

    def _fake_verify(**kwargs: object) -> VerifyClaimResult:
        captured.update(kwargs)
        return VerifyClaimResult(
            claim="x",
            outcome="auto_accept",
            chosen_source="t",
            chosen_back_translation="x",
            chosen_similarity=1.0,
            candidates=[],
            blueprint=None,
            index_source="",
            escalation=None,
            notes=[],
        )

    monkeypatch.setattr(
        "grd.core.lean.autoformalize.verify_claim",
        _fake_verify,
    )

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "lean",
            "verify-claim",
            "x",
            "--physics",
            "--no-llm",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert captured["physics_override"] is True
