"""Tests for ``grd.core.lean.autoformalize.llm`` — prompt composition + error
classification + MockLLM semantics."""

from __future__ import annotations

import pytest

from grd.core.lean.autoformalize.llm import (
    LLMMessage,
    MockLLM,
    build_back_translation_messages,
    build_candidate_messages,
    build_repair_messages,
    classify_compile_error,
)
from grd.core.lean.protocol import LeanCheckResult, LeanDiagnostic

# ─── MockLLM ────────────────────────────────────────────────────────────────


def test_mock_llm_returns_queued_responses_in_order() -> None:
    llm = MockLLM(responses=["first", "second"])
    r1 = llm.complete(system="s", messages=[LLMMessage(role="user", content="x")])
    r2 = llm.complete(system="s", messages=[LLMMessage(role="user", content="y")])
    assert r1 == "first"
    assert r2 == "second"
    assert len(llm.calls) == 2
    assert llm.calls[0][0] == "s"


def test_mock_llm_raises_when_exhausted() -> None:
    llm = MockLLM(responses=["only"])
    llm.complete(system="s", messages=[])
    with pytest.raises(RuntimeError, match="no more scripted"):
        llm.complete(system="s", messages=[])


# ─── Prompt composition ────────────────────────────────────────────────────


def test_candidate_prompt_bakes_in_convention_lock() -> None:
    system, messages = build_candidate_messages(
        claim="every even natural is the sum of two primes",
        conventions={"metric_signature": "(+,-,-,-)"},
        index_sample=["Nat.Prime", "Real.pi"],
        index_total=2,
        physics=False,
    )
    body = messages[0].content
    assert "ACTIVE CONVENTION LOCK" in body
    assert "metric_signature" in body
    assert "(+,-,-,-)" in body
    assert "Nat.Prime" in body
    assert "Lean 4" in system


def test_candidate_prompt_physics_branch_mentions_physlean() -> None:
    system, _ = build_candidate_messages(
        claim="any",
        conventions=None,
        index_sample=[],
        index_total=0,
        physics=True,
    )
    assert "PhysLean" in system


def test_candidate_prompt_no_conventions_gracefully() -> None:
    _, messages = build_candidate_messages(
        claim="x",
        conventions=None,
        index_sample=[],
        index_total=0,
        physics=False,
    )
    body = messages[0].content
    assert "no active convention lock" in body
    assert "no Mathlib4" in body


def test_repair_prompt_includes_classified_error_and_diagnostics() -> None:
    result = LeanCheckResult(
        ok=False,
        backend="subprocess",
        elapsed_ms=5,
        diagnostics=[
            LeanDiagnostic(severity="error", line=3, column=10, message="unknown identifier 'IrratNum'"),
        ],
    )
    system, messages = build_repair_messages(
        claim="pi is irrational",
        previous_source="theorem foo : IrratNum 3 := sorry",
        lean_result=result,
        error_kind="hallucinated_identifier",
        conventions=None,
    )
    body = messages[0].content
    assert "ERROR CLASS: hallucinated_identifier" in body
    assert "unknown identifier" in body
    assert "```lean" in body
    assert "Lean 4" in system


def test_back_translation_prompt_is_minimal() -> None:
    system, messages = build_back_translation_messages(
        lean_source="theorem foo (n : Nat) : n = n := rfl",
    )
    body = messages[0].content
    assert "LEAN 4 STATEMENT" in body
    assert "one clear English sentence" in body
    assert "do not add" in system.lower()


# ─── Error classification ─────────────────────────────────────────────────


def _fail_with(messages: list[str]) -> LeanCheckResult:
    return LeanCheckResult(
        ok=False,
        backend="subprocess",
        elapsed_ms=1,
        diagnostics=[LeanDiagnostic(severity="error", message=m) for m in messages],
    )


def test_classify_detects_hallucinated_identifier() -> None:
    result = _fail_with(["unknown identifier 'IrratNum'"])
    assert classify_compile_error(result, "theorem foo : IrratNum 1 := sorry") == "hallucinated_identifier"


def test_classify_detects_lean3_syntax_from_source() -> None:
    # Even with a generic diagnostic, Lean-3 markers in the source are decisive.
    result = _fail_with(["unexpected token"])
    src = "theorem foo : P := begin\nintro\nend\n"
    assert classify_compile_error(result, src) == "lean3_syntax"


def test_classify_detects_typeclass_missing() -> None:
    result = _fail_with(["failed to synthesize instance\n  Monoid α"])
    assert classify_compile_error(result, "x") == "typeclass_missing"


def test_classify_detects_universe_mismatch() -> None:
    result = _fail_with(["universe level mismatch"])
    assert classify_compile_error(result, "x") == "universe"


def test_classify_detects_namespace() -> None:
    result = _fail_with(["unknown namespace Mathlib.Foo"])
    assert classify_compile_error(result, "x") == "namespace"


def test_classify_falls_through_to_elaboration() -> None:
    result = _fail_with(["type mismatch"])
    assert classify_compile_error(result, "x") == "elaboration"


def test_classify_without_diagnostics_uses_elaboration_for_orchestration_error() -> None:
    result = LeanCheckResult(
        ok=False,
        backend="subprocess",
        elapsed_ms=0,
        error="lean_not_found",
        diagnostics=[],
    )
    assert classify_compile_error(result, "x") == "elaboration"
