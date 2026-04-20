"""Tests for ``grd.core.lean.find_counterexample`` (ge-16j / P2-3)."""

from __future__ import annotations

import json
import stat
from collections.abc import Callable
from pathlib import Path

import pytest
from typer.testing import CliRunner

from grd.cli import app
from grd.core.lean import find_counterexample as fc_mod
from grd.core.lean.protocol import LeanCheckResult, LeanDiagnostic

runner = CliRunner()


# ─── Fake lean_check helpers ────────────────────────────────────────────────


def _ok_result() -> LeanCheckResult:
    return LeanCheckResult(ok=True, backend="subprocess", elapsed_ms=4)


def _fail_result(*, message: str = "tactic failed", severity: str = "error") -> LeanCheckResult:
    return LeanCheckResult(
        ok=False,
        backend="subprocess",
        elapsed_ms=6,
        diagnostics=[LeanDiagnostic(severity=severity, message=message)],
    )


def _make_check(
    *,
    ok_when: Callable[[str], bool] | None = None,
    plausible_counterexample: str | None = None,
    plausible_success: bool = False,
) -> Callable[..., LeanCheckResult]:
    """Build a stub for ``lean_check`` keyed on the composed source.

    ``ok_when(source) -> bool`` decides the accept/reject outcome for the
    non-plausible candidates. ``plausible_counterexample`` injects a
    Plausible-style error message into the diagnostics when the source
    uses ``by plausible``; ``plausible_success=True`` instead reports
    ``ok=True`` (the statement was proved, so no counterexample).
    """

    def _impl(*, code: str, **_kwargs) -> LeanCheckResult:
        if ":= by plausible" in code:
            if plausible_success:
                return _ok_result()
            if plausible_counterexample is not None:
                return _fail_result(message=plausible_counterexample)
            return _fail_result(message="tactic 'plausible' failed")
        if ok_when is not None and ok_when(code):
            return _ok_result()
        return _fail_result()

    return _impl


# ─── Proposition extraction ─────────────────────────────────────────────────


def test_extract_proposition_strips_theorem_header() -> None:
    assert fc_mod._extract_proposition("theorem foo : P ∧ Q") == "P ∧ Q"


def test_extract_proposition_strips_assignment_tail() -> None:
    assert fc_mod._extract_proposition("theorem foo : P := by sorry") == "P"


def test_extract_proposition_returns_bare_prop() -> None:
    assert fc_mod._extract_proposition("1 + 1 = 3") == "1 + 1 = 3"


def test_extract_proposition_rejects_empty() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        fc_mod._extract_proposition("   ")


# ─── Source composition ────────────────────────────────────────────────────


def test_compose_decide_negation_wraps_with_not() -> None:
    src = fc_mod._compose_decide_negation("1 + 1 = 3")
    assert "example : ¬(1 + 1 = 3) := by decide" in src


def test_compose_decide_negation_prepends_imports() -> None:
    src = fc_mod._compose_decide_negation("1 = 2", imports=["Mathlib.Tactic"])
    assert src.startswith("import Mathlib.Tactic\n")


def test_compose_plausible_attempt_uses_plausible_tactic() -> None:
    src = fc_mod._compose_plausible_attempt("∀ n : Nat, n < 10")
    assert ":= by plausible" in src
    assert "example : ∀ n : Nat, n < 10" in src


def test_compose_witness_negation_splices_binder() -> None:
    src = fc_mod._compose_witness_negation("∀ n : Nat, n * n ≠ 4", "2", "decide")
    assert ":= by decide" in src
    # Witness spliced through beta-redex form for robustness.
    assert "(fun n =>" in src and " n * n ≠ 4) 2" in src


def test_compose_witness_negation_supports_named_assignment() -> None:
    src = fc_mod._compose_witness_negation("∀ n : Nat, n < 10", "n := 42", "decide")
    assert " n < 10) 42" in src
    # Only the RHS of ':=' is spliced — the name prefix is dropped.
    assert "n := 42" not in src


def test_compose_witness_negation_falls_back_when_no_binder() -> None:
    src = fc_mod._compose_witness_negation("P x", "4", "decide")
    assert "¬(P x 4) := by decide" in src


# ─── Plausible counterexample extraction ────────────────────────────────────


def test_extract_plausible_counterexample_matches_found_pattern() -> None:
    res = LeanCheckResult(
        ok=False,
        backend="subprocess",
        diagnostics=[
            LeanDiagnostic(
                severity="error",
                message="Counterexample found: n = 7, m = 0\n(shrunk 4 times)",
            )
        ],
    )
    assert fc_mod._extract_plausible_counterexample(res) == ("Counterexample found: n = 7, m = 0")


def test_extract_plausible_counterexample_returns_none_without_signal() -> None:
    res = LeanCheckResult(
        ok=False,
        backend="subprocess",
        diagnostics=[LeanDiagnostic(severity="error", message="type mismatch")],
    )
    assert fc_mod._extract_plausible_counterexample(res) is None


# ─── Core orchestrator ──────────────────────────────────────────────────────


def test_find_counterexample_confirms_decide_refutation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        fc_mod,
        "lean_check",
        _make_check(ok_when=lambda src: "¬(1 + 1 = 3) := by decide" in src),
    )

    result = fc_mod.find_counterexample(
        "1 + 1 = 3",
        project_root=tmp_path,
        methods=["decide"],
    )
    assert result.ok is True
    [ce] = result.counterexamples
    assert ce.method == "decide"
    assert ce.ok is True
    assert ce.rank == 0
    assert "decide" in ce.snippet


def test_find_counterexample_decide_rejection_means_no_counterexample(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``decide`` failing to accept ``¬P`` is *not* a counterexample."""
    monkeypatch.setattr(fc_mod, "lean_check", _make_check(ok_when=lambda _src: False))
    result = fc_mod.find_counterexample("1 + 1 = 2", project_root=tmp_path, methods=["decide"])
    assert result.ok is False
    assert result.counterexamples == []
    assert len(result.rejected) == 1
    assert result.rejected[0].method == "decide"


def test_find_counterexample_plausible_reports_witness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        fc_mod,
        "lean_check",
        _make_check(
            ok_when=lambda _src: False,
            plausible_counterexample="Counterexample found: n = 3",
        ),
    )

    result = fc_mod.find_counterexample(
        "∀ n : Nat, n < 2",
        project_root=tmp_path,
        methods=["plausible"],
    )
    assert result.ok is True
    [ce] = result.counterexamples
    assert ce.method == "plausible"
    assert ce.plausible_message == "Counterexample found: n = 3"
    assert "Counterexample found: n = 3" in ce.snippet


def test_find_counterexample_plausible_proves_statement_is_not_a_counterexample(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        fc_mod,
        "lean_check",
        _make_check(plausible_success=True),
    )
    result = fc_mod.find_counterexample(
        "∀ n : Nat, n = n",
        project_root=tmp_path,
        methods=["plausible"],
    )
    assert result.ok is False
    assert len(result.rejected) == 1
    assert "statement appears true" in (result.rejected[0].error_summary or "")


def test_find_counterexample_plausible_silent_failure_is_rejection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Plausible can fail without a ``found a counterexample`` line — that's a rejection."""
    monkeypatch.setattr(
        fc_mod,
        "lean_check",
        _make_check(
            ok_when=lambda _src: False,
            plausible_counterexample=None,  # generic tactic failure
        ),
    )
    result = fc_mod.find_counterexample(
        "∀ n : Nat, n < 2",
        project_root=tmp_path,
        methods=["plausible"],
    )
    assert result.ok is False
    [rej] = result.rejected
    assert rej.method == "plausible"
    assert rej.ok is False


def test_find_counterexample_llm_witness_confirmed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Accept the refutation only when witness 3 is spliced.
    def _ok(src: str) -> bool:
        return "n < 2) 3" in src and ":= by decide" in src

    monkeypatch.setattr(fc_mod, "lean_check", _make_check(ok_when=_ok))

    class _ScriptedLLM:
        def complete(self, **_kwargs) -> str:
            return "3\n1\n"

    result = fc_mod.find_counterexample(
        "∀ n : Nat, n < 2",
        project_root=tmp_path,
        methods=["llm"],
        with_llm=True,
        llm=_ScriptedLLM(),  # type: ignore[arg-type]
    )
    assert result.ok is True
    [ce] = result.counterexamples
    assert ce.method == "llm"
    assert ce.witness == "3"
    assert ce.via_llm is True
    assert "witness 3" in ce.snippet


def test_find_counterexample_llm_without_backend_is_silent(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(fc_mod, "lean_check", _make_check(ok_when=lambda _: False))
    result = fc_mod.find_counterexample(
        "∀ n : Nat, True",
        project_root=tmp_path,
        methods=["llm"],
        with_llm=True,
        llm=None,
    )
    assert result.ok is False
    # No LLM witnesses produced, no candidates checked.
    assert result.counterexamples == []
    assert result.rejected == []


def test_find_counterexample_llm_failure_degrades_silently(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A broken LLM must not kill the search — built-in methods still run."""
    monkeypatch.setattr(
        fc_mod,
        "lean_check",
        _make_check(ok_when=lambda src: "¬(1 = 2) := by decide" in src),
    )

    class _Broken:
        def complete(self, **_kwargs) -> str:
            raise RuntimeError("network down")

    result = fc_mod.find_counterexample(
        "1 = 2",
        project_root=tmp_path,
        methods=["decide"],
        with_llm=True,
        llm=_Broken(),  # type: ignore[arg-type]
    )
    assert result.ok is True
    assert len(result.counterexamples) == 1


def test_find_counterexample_ranks_decide_before_plausible(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        fc_mod,
        "lean_check",
        _make_check(
            ok_when=lambda src: "¬(P) := by decide" in src,
            plausible_counterexample="Counterexample found: trivial",
        ),
    )
    result = fc_mod.find_counterexample("P", project_root=tmp_path, methods=["plausible", "decide"])
    assert result.ok is True
    methods_ranked = [c.method for c in result.counterexamples]
    assert methods_ranked == ["decide", "plausible"]
    assert [c.rank for c in result.counterexamples] == [0, 1]


def test_find_counterexample_rejects_unknown_method(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown counterexample method"):
        fc_mod.find_counterexample("P", project_root=tmp_path, methods=["made-up"])


def test_find_counterexample_budget_caps_candidates(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(fc_mod, "lean_check", _make_check(ok_when=lambda _: False))

    class _EchoLLM:
        def complete(self, **_kwargs) -> str:
            return "1\n2\n3\n4\n5\n"

    result = fc_mod.find_counterexample(
        "∀ n : Nat, True",
        project_root=tmp_path,
        methods=["decide", "plausible", "llm"],
        with_llm=True,
        llm=_EchoLLM(),  # type: ignore[arg-type]
        budget=2,
    )
    # Only two candidates total (decide + plausible); LLM witnesses truncated.
    assert len(result.counterexamples) + len(result.rejected) == 2
    assert result.budget == 2


def test_find_counterexample_rejects_nonpositive_budget(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=">= 1"):
        fc_mod.find_counterexample("P", project_root=tmp_path, methods=["decide"], budget=0)


def test_find_counterexample_emits_event_per_candidate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(fc_mod, "lean_check", _make_check(ok_when=lambda _: False))

    received: list[str] = []

    def _emit(event) -> None:
        received.append(event.tactic)

    fc_mod.find_counterexample(
        "∀ n : Nat, P n",
        project_root=tmp_path,
        methods=["decide", "plausible"],
        on_event=_emit,
    )
    assert set(received) == {"decide", "plausible"}


def test_find_counterexample_llm_event_label_includes_witness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(fc_mod, "lean_check", _make_check(ok_when=lambda _: False))

    class _LLM:
        def complete(self, **_kwargs) -> str:
            return "42\n"

    labels: list[str] = []
    fc_mod.find_counterexample(
        "∀ n : Nat, P n",
        project_root=tmp_path,
        methods=["llm"],
        with_llm=True,
        llm=_LLM(),  # type: ignore[arg-type]
        on_event=lambda ev: labels.append(ev.tactic),
    )
    assert labels == ["llm:42"]


def test_find_counterexample_with_llm_implicitly_enables_llm_method(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``with_llm=True`` adds ``llm`` to the method list when omitted."""
    monkeypatch.setattr(fc_mod, "lean_check", _make_check(ok_when=lambda _: False))

    class _LLM:
        def complete(self, **_kwargs) -> str:
            return "0\n"

    result = fc_mod.find_counterexample(
        "∀ n, P n",
        project_root=tmp_path,
        methods=["decide"],
        with_llm=True,
        llm=_LLM(),  # type: ignore[arg-type]
    )
    assert "llm" in result.methods


def test_find_counterexample_empty_candidate_pool_returns_ok_false(
    tmp_path: Path,
) -> None:
    # Empty methods list (after dedup of nothing) = zero candidates.
    result = fc_mod.find_counterexample("P", project_root=tmp_path, methods=[], with_llm=False)
    assert result.ok is False
    assert result.total_elapsed_ms == 0


# ─── LLM parsing ────────────────────────────────────────────────────────────


def test_propose_llm_witnesses_strips_bullets_and_dedups() -> None:
    class _LLM:
        def complete(self, **_kwargs) -> str:
            return "1. 7\n- 7\n* 3\n```\n\n0 1\n"

    witnesses = fc_mod._propose_llm_witnesses(
        statement="∀ n, P n",
        llm=_LLM(),
        limit=10,  # type: ignore[arg-type]
    )
    assert witnesses == ["7", "3", "0 1"]


def test_propose_llm_witnesses_respects_limit() -> None:
    class _LLM:
        def complete(self, **_kwargs) -> str:
            return "1\n2\n3\n4\n5\n"

    witnesses = fc_mod._propose_llm_witnesses(
        statement="P",
        llm=_LLM(),
        limit=2,  # type: ignore[arg-type]
    )
    assert witnesses == ["1", "2"]


def test_propose_llm_witnesses_swallows_errors() -> None:
    class _Broken:
        def complete(self, **_kwargs) -> str:
            raise RuntimeError("boom")

    assert (
        fc_mod._propose_llm_witnesses(
            statement="P",
            llm=_Broken(),
            limit=3,  # type: ignore[arg-type]
        )
        == []
    )


# ─── CLI wiring ─────────────────────────────────────────────────────────────


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


def test_cli_find_counterexample_confirms_when_decide_accepts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
            "find-counterexample",
            "1 + 1 = 3",
            "--no-daemon",
            "--no-spawn",
            "--method",
            "decide",
        ],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is True
    assert parsed["statement"] == "1 + 1 = 3"
    assert parsed["methods"] == ["decide"]
    assert len(parsed["counterexamples"]) == 1
    assert parsed["counterexamples"][0]["method"] == "decide"
    assert parsed["counterexamples"][0]["rank"] == 0


def test_cli_find_counterexample_exit_1_when_nothing_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
            "find-counterexample",
            "1 + 1 = 2",
            "--no-daemon",
            "--no-spawn",
            "--method",
            "decide",
        ],
    )
    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is False
    assert parsed["counterexamples"] == []


def test_cli_find_counterexample_list_methods(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "find-counterexample",
            "--list-methods",
        ],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed["methods"] == list(fc_mod.DEFAULT_METHODS)
    assert parsed["available"] == ["decide", "plausible", "llm"]


def test_cli_find_counterexample_requires_statement(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "find-counterexample",
        ],
    )
    assert result.exit_code == 2


def test_cli_find_counterexample_rejects_unknown_method(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
            "find-counterexample",
            "P",
            "--no-daemon",
            "--no-spawn",
            "--method",
            "bogus",
        ],
    )
    assert result.exit_code == 2


def test_cli_find_counterexample_budget_caps_pool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
            "find-counterexample",
            "P",
            "--no-daemon",
            "--no-spawn",
            "--budget",
            "1",
        ],
    )
    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    total = len(parsed["counterexamples"]) + len(parsed["rejected"])
    assert total == 1
    assert parsed["budget"] == 1
