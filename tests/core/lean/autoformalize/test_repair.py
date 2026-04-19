"""Tests for ``grd.core.lean.autoformalize.repair``.

Exercises the APOLLO-style compile-repair loop with a fake ``lean_check`` and
a scripted ``MockLLM``. The goal is to pin behavior at the boundaries:
happy-path, budget exhaustion, DDR short-circuit, and the "repair fixes the
error" transition.
"""

from __future__ import annotations

from pathlib import Path

from grd.core.lean.autoformalize.blueprint import BlueprintContext
from grd.core.lean.autoformalize.candidates import Candidate
from grd.core.lean.autoformalize.index import NameIndex
from grd.core.lean.autoformalize.llm import MockLLM
from grd.core.lean.autoformalize.repair import repair_candidate
from grd.core.lean.protocol import LeanCheckResult, LeanDiagnostic


def _bp(claim: str = "x") -> BlueprintContext:
    return BlueprintContext(claim=claim, conventions={}, physics=False)


def _ok() -> LeanCheckResult:
    return LeanCheckResult(ok=True, backend="subprocess", elapsed_ms=7, diagnostics=[])


def _fail(msg: str) -> LeanCheckResult:
    return LeanCheckResult(
        ok=False,
        backend="subprocess",
        elapsed_ms=4,
        diagnostics=[LeanDiagnostic(severity="error", message=msg)],
    )


class _ScriptedCheck:
    """Replays a list of LeanCheckResult values in order — one per compile."""

    def __init__(self, results: list[LeanCheckResult]) -> None:
        self._results = list(results)
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> LeanCheckResult:
        self.calls.append(kwargs)
        if not self._results:
            raise AssertionError("lean_check called more times than scripted")
        return self._results.pop(0)


def test_first_compile_ok_returns_without_repair(tmp_path: Path) -> None:
    candidate = Candidate(index=0, source="theorem foo : True := trivial", raw="", temperature=0.3)
    check = _ScriptedCheck([_ok()])
    llm = MockLLM(responses=[])

    outcome = repair_candidate(
        candidate=candidate,
        blueprint=_bp(),
        index=NameIndex.empty(),
        llm=llm,
        project_root=tmp_path,
        repair_budget=5,
        lean_check=check,
    )

    assert outcome.ok is True
    assert outcome.final_source == candidate.source
    assert len(outcome.steps) == 1
    assert outcome.steps[0].repair_applied is False
    assert outcome.total_elapsed_ms == 7
    assert len(check.calls) == 1
    # LLM never consulted on first-try success.
    assert llm.calls == []


def test_repair_loop_fixes_then_compiles(tmp_path: Path) -> None:
    candidate = Candidate(index=0, source="theorem foo : IrratPi := sorry", raw="", temperature=0.3)
    # First compile fails; repair returns a fresh source wrapped in a fence;
    # second compile succeeds.
    check = _ScriptedCheck([_fail("unknown identifier 'IrratPi'"), _ok()])
    llm = MockLLM(responses=["```lean\ntheorem foo : True := trivial\n```"])

    outcome = repair_candidate(
        candidate=candidate,
        blueprint=_bp("pi is irrational"),
        index=NameIndex.empty(),
        llm=llm,
        project_root=tmp_path,
        repair_budget=3,
        lean_check=check,
    )

    assert outcome.ok is True
    assert outcome.final_source == "theorem foo : True := trivial"
    assert len(outcome.steps) == 2
    assert outcome.steps[0].repair_applied is False
    assert outcome.steps[0].error_kind == "hallucinated_identifier"
    assert outcome.steps[1].repair_applied is True
    assert outcome.steps[1].ok is True
    assert len(llm.calls) == 1


def test_budget_exhausted_reports_final_error(tmp_path: Path) -> None:
    candidate = Candidate(index=0, source="bad lean", raw="", temperature=0.3)
    check = _ScriptedCheck([_fail("type mismatch"), _fail("type mismatch")])
    # Two compiles permitted (budget=1 + initial). Repair once, still fails.
    llm = MockLLM(responses=["still bad lean"])

    outcome = repair_candidate(
        candidate=candidate,
        blueprint=_bp(),
        index=NameIndex.empty(),
        llm=llm,
        project_root=tmp_path,
        repair_budget=1,
        lean_check=check,
    )

    assert outcome.ok is False
    assert "budget exhausted" in outcome.reason
    assert "elaboration" in outcome.reason  # type mismatch → elaboration
    assert len(outcome.steps) == 2


def test_budget_zero_compiles_once_only(tmp_path: Path) -> None:
    """A ``repair_budget`` of 0 means "compile once, don't LLM-repair at all"."""
    candidate = Candidate(index=0, source="bad", raw="", temperature=0.3)
    check = _ScriptedCheck([_fail("type mismatch")])
    llm = MockLLM(responses=[])

    outcome = repair_candidate(
        candidate=candidate,
        blueprint=_bp(),
        index=NameIndex.empty(),
        llm=llm,
        project_root=tmp_path,
        repair_budget=0,
        lean_check=check,
    )

    assert outcome.ok is False
    assert len(outcome.steps) == 1
    assert llm.calls == []  # no repair requested


def test_ddr_shortcircuit_skips_lean_on_unknown_identifier(tmp_path: Path) -> None:
    """If the NameIndex flags an identifier as unknown, we never call Lean."""
    candidate = Candidate(index=0, source="theorem foo : IrratPi := sorry", raw="", temperature=0.3)
    check = _ScriptedCheck([_ok()])  # will raise if called
    idx = NameIndex.from_iterable(["Nat.Prime"])  # IrratPi is NOT in the index
    llm = MockLLM(
        responses=["```lean\ntheorem foo : True := trivial\n```", "```lean\ntheorem foo : True := trivial\n```"]
    )

    outcome = repair_candidate(
        candidate=candidate,
        blueprint=_bp(),
        index=idx,
        llm=llm,
        project_root=tmp_path,
        repair_budget=2,
        lean_check=check,
    )

    # After repair, the replacement has no unknown identifiers; the next
    # iteration falls through to Lean, which succeeds.
    assert outcome.ok is True
    # Lean was called once (on the repaired source).
    assert len(check.calls) == 1
    # The first iteration was a DDR rejection — repair_applied=False because
    # it's iteration 0 (the pristine candidate).
    assert outcome.steps[0].error_kind == "hallucinated_identifier"
    assert outcome.steps[0].elapsed_ms == 0
    assert outcome.steps[0].unknown_identifiers == ["IrratPi"]


def test_ddr_shortcircuit_exhausts_budget_without_compiling(tmp_path: Path) -> None:
    """Every LLM repair keeps emitting unknown identifiers → no Lean call ever."""
    candidate = Candidate(index=0, source="theorem a : IrratPi := sorry", raw="", temperature=0.3)
    check = _ScriptedCheck([])  # never called
    idx = NameIndex.from_iterable(["Nat.Prime"])
    llm = MockLLM(
        responses=[
            "```lean\ntheorem a : IrratPi := sorry\n```",  # still unknown
            "```lean\ntheorem a : IrratPi := sorry\n```",  # still unknown
        ]
    )

    outcome = repair_candidate(
        candidate=candidate,
        blueprint=_bp(),
        index=idx,
        llm=llm,
        project_root=tmp_path,
        repair_budget=2,
        lean_check=check,
    )

    assert outcome.ok is False
    assert "hallucinated identifiers" in outcome.reason
    assert "IrratPi" in outcome.reason
    assert check.calls == []
    assert len(outcome.steps) == 3  # initial + 2 repairs, all DDR-rejected


def test_repair_extracts_lean_from_fenced_response(tmp_path: Path) -> None:
    """The LLM response is wrapped in narrative + fence; we must extract the fence body."""
    candidate = Candidate(index=0, source="bad", raw="", temperature=0.3)
    check = _ScriptedCheck([_fail("universe level mismatch"), _ok()])
    llm = MockLLM(
        responses=[
            "Here's my fix:\n\n```lean\ntheorem bar : True := trivial\n```\n\nLet me know.",
        ]
    )

    outcome = repair_candidate(
        candidate=candidate,
        blueprint=_bp(),
        index=NameIndex.empty(),
        llm=llm,
        project_root=tmp_path,
        repair_budget=2,
        lean_check=check,
    )

    assert outcome.ok is True
    assert outcome.final_source == "theorem bar : True := trivial"
    # Verify the second Lean invocation got the fence body, not the narrative.
    assert check.calls[1]["code"] == "theorem bar : True := trivial"


def test_success_populates_goals_after(tmp_path: Path) -> None:
    """On compile success, goals_after comes from the LeanCheckResult (ge-2zu)."""
    candidate = Candidate(index=0, source="theorem foo : True := trivial", raw="", temperature=0.3)
    ok_with_goals = LeanCheckResult(ok=True, backend="subprocess", elapsed_ms=5, diagnostics=[], goals_after=[])
    check = _ScriptedCheck([ok_with_goals])
    llm = MockLLM(responses=[])

    outcome = repair_candidate(
        candidate=candidate,
        blueprint=_bp(),
        index=NameIndex.empty(),
        llm=llm,
        project_root=tmp_path,
        repair_budget=0,
        lean_check=check,
    )

    assert outcome.ok is True
    assert outcome.goals_after == []


def test_failure_populates_goals_after(tmp_path: Path) -> None:
    """On compile failure with unsolved goals, goals_after carries them (ge-2zu)."""
    candidate = Candidate(index=0, source="theorem foo : False := by rfl", raw="", temperature=0.3)
    fail_with_goals = LeanCheckResult(
        ok=False,
        backend="subprocess",
        elapsed_ms=4,
        diagnostics=[LeanDiagnostic(severity="error", message="type mismatch")],
        goals_after=["⊢ False"],
    )
    check = _ScriptedCheck([fail_with_goals])
    llm = MockLLM(responses=[])

    outcome = repair_candidate(
        candidate=candidate,
        blueprint=_bp(),
        index=NameIndex.empty(),
        llm=llm,
        project_root=tmp_path,
        repair_budget=0,
        lean_check=check,
    )

    assert outcome.ok is False
    assert outcome.goals_after == ["⊢ False"]


def test_repair_propagates_imports_and_timeout(tmp_path: Path) -> None:
    candidate = Candidate(index=0, source="theorem foo : True := trivial", raw="", temperature=0.3)
    check = _ScriptedCheck([_ok()])
    llm = MockLLM(responses=[])

    repair_candidate(
        candidate=candidate,
        blueprint=_bp(),
        index=NameIndex.empty(),
        llm=llm,
        project_root=tmp_path,
        repair_budget=0,
        timeout_s=42.0,
        imports=["Mathlib"],
        use_daemon=False,
        lean_check=check,
    )

    assert check.calls[0]["imports"] == ["Mathlib"]
    assert check.calls[0]["timeout_s"] == 42.0
    assert check.calls[0]["use_daemon"] is False


def test_preamble_prepended_to_compile_source(tmp_path: Path) -> None:
    """When a preamble is provided, it is prepended to the source sent to Lean
    but NOT included in the final_source or shown to the repair LLM (ge-j8k)."""
    preamble = "namespace Blueprint.Conventions\ninstance : MetricSignature := ⟨SignChoice.mostlyMinus⟩\nend Blueprint.Conventions"
    candidate = Candidate(index=0, source="theorem foo : True := trivial", raw="", temperature=0.3)
    check = _ScriptedCheck([_ok()])
    llm = MockLLM(responses=[])

    outcome = repair_candidate(
        candidate=candidate,
        blueprint=_bp(),
        index=NameIndex.empty(),
        llm=llm,
        project_root=tmp_path,
        repair_budget=0,
        lean_check=check,
        preamble=preamble,
    )

    assert outcome.ok is True
    # The source sent to Lean must include the preamble.
    compiled_code = check.calls[0]["code"]
    assert compiled_code.startswith(preamble)
    assert "theorem foo : True := trivial" in compiled_code
    # But final_source must NOT include the preamble — callers get the raw source.
    assert outcome.final_source == "theorem foo : True := trivial"
    assert "Blueprint.Conventions" not in outcome.final_source


def test_preamble_not_sent_to_repair_llm(tmp_path: Path) -> None:
    """On compile failure, the repair LLM receives only the candidate source,
    not the preamble — otherwise it would strip the preamble during repair and
    break subsequent compiles (ge-j8k)."""
    preamble = "namespace Blueprint.Conventions\nend Blueprint.Conventions"
    candidate = Candidate(index=0, source="bad lean code", raw="", temperature=0.3)
    check = _ScriptedCheck([_fail("type mismatch"), _ok()])
    llm = MockLLM(responses=["```lean\ntheorem foo : True := trivial\n```"])

    outcome = repair_candidate(
        candidate=candidate,
        blueprint=_bp(),
        index=NameIndex.empty(),
        llm=llm,
        project_root=tmp_path,
        repair_budget=1,
        lean_check=check,
        preamble=preamble,
    )

    assert outcome.ok is True
    # Both compile calls should include the preamble.
    assert preamble in check.calls[0]["code"]
    assert preamble in check.calls[1]["code"]
    # The LLM call messages should NOT contain the preamble.
    # calls is list of (system, messages, temperature) tuples.
    assert len(llm.calls) == 1
    system, messages, _ = llm.calls[0]
    assert "Blueprint.Conventions" not in system
    for msg in messages:
        if isinstance(msg, dict) and "content" in msg:
            assert "Blueprint.Conventions" not in msg["content"]


def test_preamble_none_compiles_source_directly(tmp_path: Path) -> None:
    """When preamble is None, the raw source goes to Lean unmodified."""
    candidate = Candidate(index=0, source="theorem foo : True := trivial", raw="", temperature=0.3)
    check = _ScriptedCheck([_ok()])
    llm = MockLLM(responses=[])

    repair_candidate(
        candidate=candidate,
        blueprint=_bp(),
        index=NameIndex.empty(),
        llm=llm,
        project_root=tmp_path,
        repair_budget=0,
        lean_check=check,
        preamble=None,
    )

    assert check.calls[0]["code"] == "theorem foo : True := trivial"
