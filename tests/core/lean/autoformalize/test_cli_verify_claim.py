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


def test_escalate_unfiled_raw_exposes_top_level_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ``--raw`` JSON must expose ``warning`` / ``escalation_attempted`` /
    ``escalation_error`` at the top level so automation doesn't have to dig
    through the nested escalation block (ge-1hr / UX-STUDY.md §P0-8).
    """
    (tmp_path / ".grd").mkdir()

    stub_result = VerifyClaimResult(
        claim="x",
        outcome="escalate_unfiled",
        chosen_source=None,
        chosen_back_translation=None,
        chosen_similarity=None,
        candidates=[],
        blueprint=None,
        index_source="",
        escalation=None,
        notes=[],
        warning="ESCALATION NOT FILED (bd CLI not available). Install the beads CLI...",
        escalation_attempted=False,
        escalation_error="bd CLI not available",
    )
    monkeypatch.setattr("grd.core.lean.autoformalize.verify_claim", lambda **_kw: stub_result)

    result = runner.invoke(
        app,
        ["--raw", "--cwd", str(tmp_path), "lean", "verify-claim", "x", "--no-llm"],
    )
    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    assert parsed["outcome"] == "escalate_unfiled"
    assert "ESCALATION NOT FILED" in parsed["warning"]
    assert parsed["escalation_attempted"] is False
    assert parsed["escalation_error"] == "bd CLI not available"


def test_escalate_unfiled_renders_warning_banner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-raw mode must surface a visible banner — a cold mathematician
    should never miss the fact that escalation silently failed.
    """
    (tmp_path / ".grd").mkdir()

    stub_result = VerifyClaimResult(
        claim="x",
        outcome="escalate_unfiled",
        chosen_source=None,
        chosen_back_translation=None,
        chosen_similarity=None,
        candidates=[],
        blueprint=None,
        index_source="",
        escalation=None,
        notes=[],
        warning="ESCALATION NOT FILED (bd CLI not available). Install the beads CLI...",
        escalation_attempted=False,
        escalation_error="bd CLI not available",
    )
    monkeypatch.setattr("grd.core.lean.autoformalize.verify_claim", lambda **_kw: stub_result)

    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "lean", "verify-claim", "x", "--no-llm"],
    )
    # CliRunner mixes stderr into stdout by default — which is what we want
    # here: the warning is emitted via err_console and must be visible to the
    # user skimming the terminal.
    assert result.exit_code == 1
    assert "ESCALATION NOT FILED" in result.stdout


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
    # ge-oc0: conflicting flags is a user input error → exit 2.
    assert result.exit_code == 2


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


def test_raw_json_includes_chosen_semantic_diff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ge-cla: ``--raw`` JSON must include the structured diff object."""
    from grd.core.lean.autoformalize.faithfulness import SemanticDiff

    (tmp_path / ".grd").mkdir()

    diff = SemanticDiff(
        similarity=0.71,
        changed_quantifiers=["forall", "exists"],
        changed_domains=[],
        missing_hypotheses=["bounded"],
        changed_convention_terms=[],
        only_in_claim=["forall", "bounded"],
        only_in_translation=["exists"],
    )
    stub_result = VerifyClaimResult(
        claim="x",
        outcome="escalate",
        chosen_source=None,
        chosen_back_translation=None,
        chosen_similarity=0.71,
        chosen_semantic_diff=diff,
        candidates=[],
        blueprint=None,
        index_source="",
        escalation=None,
        notes=[],
    )
    monkeypatch.setattr("grd.core.lean.autoformalize.verify_claim", lambda **_kw: stub_result)

    result = runner.invoke(
        app,
        ["--raw", "--cwd", str(tmp_path), "lean", "verify-claim", "x", "--no-llm"],
    )
    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    sd = parsed["chosen_semantic_diff"]
    assert sd["similarity"] == 0.71
    assert sd["changed_quantifiers"] == ["forall", "exists"]
    assert sd["missing_hypotheses"] == ["bounded"]
    assert sd["only_in_claim"] == ["forall", "bounded"]
    assert sd["only_in_translation"] == ["exists"]
