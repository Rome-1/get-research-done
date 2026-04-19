"""Tests for ``grd.core.lean.try_prove`` — parallel hammer (ge-k8s / P2-1)."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
from typer.testing import CliRunner

from grd.cli import app
from grd.core.lean import try_prove as try_prove_mod
from grd.core.lean.protocol import LeanCheckResult, LeanDiagnostic

runner = CliRunner()


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _fake_check(*, ok_tactics: set[str]) -> object:
    """Stub for ``lean_client.check`` that passes when any ``ok_tactics`` member appears."""

    def _impl(*, code: str, **_kwargs: object) -> LeanCheckResult:
        for tac in ok_tactics:
            if f":= by {tac}" in code:
                return LeanCheckResult(ok=True, backend="subprocess", elapsed_ms=5)
        return LeanCheckResult(
            ok=False,
            backend="subprocess",
            elapsed_ms=7,
            diagnostics=[LeanDiagnostic(severity="error", message="tactic failed")],
        )

    return _impl


# ─── Core orchestrator ───────────────────────────────────────────────────────


def test_try_prove_returns_every_passing_candidate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        try_prove_mod, "lean_check", _fake_check(ok_tactics={"simp_all", "aesop"})
    )

    result = try_prove_mod.try_prove_statement("1 + 1 = 2", project_root=tmp_path)

    assert result.ok is True
    passing = {c.tactic for c in result.successes}
    assert passing == {"simp_all", "aesop"}
    # All default tactics were attempted; the two that didn't pass became failures.
    attempted = {c.tactic for c in result.successes} | {c.tactic for c in result.failures}
    assert set(try_prove_mod.DEFAULT_HAMMER_TACTICS).issubset(attempted)


def test_try_prove_ranks_builtin_order_before_elapsed_time(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`simp_all` appears before `aesop` in the ladder, so it must rank higher."""

    monkeypatch.setattr(
        try_prove_mod, "lean_check", _fake_check(ok_tactics={"simp_all", "aesop"})
    )

    result = try_prove_mod.try_prove_statement("P", project_root=tmp_path)
    ranked = [c.tactic for c in result.successes]
    assert ranked[0] == "simp_all"
    assert ranked[1] == "aesop"
    assert [c.rank for c in result.successes] == [0, 1]


def test_try_prove_all_failures_returns_ok_false(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(try_prove_mod, "lean_check", _fake_check(ok_tactics=set()))

    result = try_prove_mod.try_prove_statement(
        "False", project_root=tmp_path, tactics=["exact?", "aesop"]
    )
    assert result.ok is False
    assert result.successes == []
    assert [c.tactic for c in result.failures] == sorted(
        ["exact?", "aesop"], key=lambda t: t
    ) or True  # order is completion order; we only assert membership below
    assert {c.tactic for c in result.failures} == {"exact?", "aesop"}
    assert all(c.error_summary == "tactic failed" for c in result.failures)


def test_try_prove_snippet_is_raw_tactic_string(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(try_prove_mod, "lean_check", _fake_check(ok_tactics={"aesop"}))
    result = try_prove_mod.try_prove_statement(
        "theorem foo : P → P", project_root=tmp_path, tactics=["aesop"]
    )
    [cand] = result.successes
    assert cand.snippet == "by aesop"
    assert ":= by aesop" in cand.source
    assert "theorem foo : P → P" in cand.source


def test_try_prove_respects_max_candidates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(try_prove_mod, "lean_check", _fake_check(ok_tactics=set()))

    result = try_prove_mod.try_prove_statement(
        "P", project_root=tmp_path, max_candidates=2
    )
    # First two tactics from the default ladder, plus nothing from LLM.
    attempted = {c.tactic for c in result.failures}
    assert attempted == set(try_prove_mod.DEFAULT_HAMMER_TACTICS[:2])


def test_try_prove_rejects_nonpositive_max_candidates(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=">= 1"):
        try_prove_mod.try_prove_statement("P", project_root=tmp_path, max_candidates=0)


def test_try_prove_with_llm_adds_candidates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        try_prove_mod, "lean_check", _fake_check(ok_tactics={"norm_num"})
    )

    class _ScriptedLLM:
        def __init__(self, response: str) -> None:
            self.response = response
            self.calls: list[tuple[str, list, float]] = []

        def complete(self, *, system: str, messages: list, temperature: float = 0.7) -> str:
            self.calls.append((system, messages, temperature))
            return self.response

    # LLM proposes two tactics; only `norm_num` will actually kernel-check under the stub.
    llm = _ScriptedLLM("norm_num\nlinarith\n")

    result = try_prove_mod.try_prove_statement(
        "1 + 1 = 2",
        project_root=tmp_path,
        tactics=["exact?", "apply?"],  # none of these pass under the stub
        with_llm=True,
        llm=llm,  # type: ignore[arg-type]
    )
    assert result.with_llm is True
    assert result.ok is True
    [cand] = result.successes
    assert cand.tactic == "norm_num"
    assert cand.via_llm is True
    assert llm.calls, "LLM should have been asked for candidates"


def test_try_prove_llm_failure_degrades_silently(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An LLM that raises must not break the hammer — built-ins still run."""
    monkeypatch.setattr(try_prove_mod, "lean_check", _fake_check(ok_tactics={"aesop"}))

    class _BrokenLLM:
        def complete(self, **_kwargs: object) -> str:
            raise RuntimeError("network down")

    result = try_prove_mod.try_prove_statement(
        "P",
        project_root=tmp_path,
        with_llm=True,
        llm=_BrokenLLM(),  # type: ignore[arg-type]
    )
    assert result.ok is True
    assert {c.tactic for c in result.successes} == {"aesop"}


def test_try_prove_with_llm_without_backend_is_noop(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`with_llm=True` + `llm=None` runs built-ins only."""
    monkeypatch.setattr(try_prove_mod, "lean_check", _fake_check(ok_tactics=set()))
    result = try_prove_mod.try_prove_statement(
        "P", project_root=tmp_path, with_llm=True, llm=None
    )
    assert result.ok is False
    assert result.with_llm is True
    # No LLM candidates, only the default tactics.
    assert {c.tactic for c in result.failures} == set(try_prove_mod.DEFAULT_HAMMER_TACTICS)


def test_try_prove_deduplicates_tactics(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Duplicate tactics across built-ins and LLM collapse to one attempt."""
    monkeypatch.setattr(try_prove_mod, "lean_check", _fake_check(ok_tactics={"aesop"}))

    class _EchoLLM:
        def complete(self, **_kwargs: object) -> str:
            return "aesop\naesop\n"

    result = try_prove_mod.try_prove_statement(
        "P",
        project_root=tmp_path,
        tactics=["aesop"],
        with_llm=True,
        llm=_EchoLLM(),  # type: ignore[arg-type]
    )
    assert len(result.successes) == 1
    assert result.successes[0].tactic == "aesop"


def test_try_prove_populates_goal_before(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(try_prove_mod, "lean_check", _fake_check(ok_tactics={"aesop"}))
    result = try_prove_mod.try_prove_statement(
        "1 + 1 = 2", project_root=tmp_path, tactics=["aesop"]
    )
    assert result.successes[0].goal_before == "⊢ 1 + 1 = 2"


def test_try_prove_emits_events_for_each_candidate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(try_prove_mod, "lean_check", _fake_check(ok_tactics={"aesop"}))

    received: list[str] = []

    def _emit(event: object) -> None:
        received.append(event.tactic)

    try_prove_mod.try_prove_statement(
        "P",
        project_root=tmp_path,
        tactics=["exact?", "apply?", "aesop"],
        on_event=_emit,
    )
    assert set(received) == {"exact?", "apply?", "aesop"}


def test_try_prove_custom_tactics_override_defaults(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(try_prove_mod, "lean_check", _fake_check(ok_tactics={"myTac"}))

    result = try_prove_mod.try_prove_statement(
        "P", project_root=tmp_path, tactics=["myTac", "otherTac"]
    )
    assert {c.tactic for c in result.successes} == {"myTac"}
    # Default tactics were NOT attempted.
    all_attempted = {c.tactic for c in result.successes} | {c.tactic for c in result.failures}
    assert all_attempted == {"myTac", "otherTac"}


# ─── CLI wiring ──────────────────────────────────────────────────────────────


def _stub_lean_ok(bin_dir: Path) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "lean"
    script.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _stub_lean_fail(bin_dir: Path) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "lean"
    script.write_text("#!/bin/bash\nexit 1\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_cli_try_prove_emits_ranked_successes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
            "try-prove",
            "1 = 1",
            "--no-daemon",
            "--no-spawn",
            "--tactic",
            "aesop",
        ],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is True
    assert parsed["statement"] == "1 = 1"
    assert len(parsed["successes"]) == 1
    assert parsed["successes"][0]["tactic"] == "aesop"
    assert parsed["successes"][0]["snippet"] == "by aesop"
    assert parsed["successes"][0]["rank"] == 0


def test_cli_try_prove_exit_1_when_all_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".grd").mkdir()
    _stub_lean_fail(tmp_path / "bin")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))

    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "try-prove",
            "False",
            "--no-daemon",
            "--no-spawn",
            "--tactic",
            "exact?",
            "--tactic",
            "aesop",
        ],
    )
    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is False
    assert parsed["successes"] == []
    assert {c["tactic"] for c in parsed["failures"]} == {"exact?", "aesop"}


def test_cli_try_prove_list_tactics(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "try-prove",
            "--list-tactics",
        ],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed["tactics"] == list(try_prove_mod.DEFAULT_HAMMER_TACTICS)


def test_cli_try_prove_requires_statement_when_not_listing(
    tmp_path: Path,
) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "try-prove",
        ],
    )
    assert result.exit_code == 2


def test_cli_try_prove_max_candidates_caps_pool(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / ".grd").mkdir()
    _stub_lean_fail(tmp_path / "bin")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))

    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "try-prove",
            "P",
            "--no-daemon",
            "--no-spawn",
            "--max-candidates",
            "2",
        ],
    )
    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    attempted = {c["tactic"] for c in parsed["failures"]}
    assert attempted == set(try_prove_mod.DEFAULT_HAMMER_TACTICS[:2])
    assert parsed["max_candidates"] == 2


# ─── LLM prompt parsing ──────────────────────────────────────────────────────


def test_propose_llm_tactics_strips_bullets_and_by() -> None:
    class _LLM:
        def complete(self, **_kwargs: object) -> str:
            return (
                "1. simp\n"
                "- by linarith\n"
                "* exact Nat.succ_pos n\n"
                "```\n"
                "\n"
                "aesop\n"
            )

    tactics = try_prove_mod._propose_llm_tactics(
        statement="P", llm=_LLM(), limit=10  # type: ignore[arg-type]
    )
    assert tactics == ["simp", "linarith", "exact Nat.succ_pos n", "aesop"]


def test_propose_llm_tactics_respects_limit() -> None:
    class _LLM:
        def complete(self, **_kwargs: object) -> str:
            return "a\nb\nc\nd\ne\n"

    tactics = try_prove_mod._propose_llm_tactics(
        statement="P", llm=_LLM(), limit=3  # type: ignore[arg-type]
    )
    assert tactics == ["a", "b", "c"]


def test_propose_llm_tactics_swallows_errors() -> None:
    class _Broken:
        def complete(self, **_kwargs: object) -> str:
            raise RuntimeError("boom")

    tactics = try_prove_mod._propose_llm_tactics(
        statement="P", llm=_Broken(), limit=3  # type: ignore[arg-type]
    )
    assert tactics == []
