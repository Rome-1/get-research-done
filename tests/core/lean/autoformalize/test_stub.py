"""Tests for ``grd.core.lean.autoformalize.stub`` — stub-claim core logic.

Covers skeleton generation, index search, import extraction, and next-steps
composition. All LLM calls are stubbed via MockLLM.
"""

from __future__ import annotations

from pathlib import Path

from grd.core.lean.autoformalize.config import AutoformalizeConfig
from grd.core.lean.autoformalize.index import NameIndex
from grd.core.lean.autoformalize.llm import MockLLM
from grd.core.lean.autoformalize.stub import (
    StubClaimResult,
    search_index,
    stub_claim,
)


def _make_index(*names: str) -> NameIndex:
    return NameIndex.from_iterable(list(names), source="test")


# ─── search_index ─────────────────────────────────────────────────────────


def test_search_empty_index_returns_empty() -> None:
    assert search_index("pi is irrational", NameIndex.empty()) == []


def test_search_finds_matching_names() -> None:
    idx = _make_index("Nat.Prime", "Real.pi", "Irrational", "Complex.exp", "Finset.sum")
    hits = search_index("pi is irrational", idx)
    # "pi" matches Real.pi, "irrational" matches Irrational
    assert "Real.pi" in hits
    assert "Irrational" in hits


def test_search_ranks_by_overlap_score() -> None:
    idx = _make_index("Nat.Prime.irrational", "Real.pi", "Irrational")
    hits = search_index("pi is irrational", idx)
    # "Nat.Prime.irrational" matches "irrational" (1 token)
    # "Real.pi" matches "pi" (1 token)
    # "Irrational" matches "irrational" (1 token)
    # All score 1, so sorted alphabetically
    assert len(hits) == 3


def test_search_respects_max_results() -> None:
    names = [f"Foo.bar{i}" for i in range(30)]
    # Add "bar" as a common token
    idx = _make_index(*names)
    hits = search_index("bar baz", idx, max_results=5)
    assert len(hits) <= 5


def test_search_stopwords_excluded() -> None:
    idx = _make_index("The.Great", "Is.True", "Of.Something")
    # "the", "is", "of" are stopwords — should not match
    hits = search_index("the cat is on the mat", idx)
    assert hits == []


# ─── stub_claim ───────────────────────────────────────────────────────────


def test_stub_claim_returns_skeleton(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    llm = MockLLM(responses=[
        "```lean\nimport Mathlib.Data.Nat.Prime\n\ntheorem every_prime_gt_one (p : Nat) (hp : Nat.Prime p) : p > 1 := sorry\n```"
    ])
    cfg = AutoformalizeConfig(num_candidates=1)

    result = stub_claim(
        claim="every prime number is greater than 1",
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
    )

    assert isinstance(result, StubClaimResult)
    assert result.claim == "every prime number is greater than 1"
    assert "sorry" in result.skeleton
    assert "theorem" in result.skeleton


def test_stub_claim_extracts_imports(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    llm = MockLLM(responses=[
        "```lean\nimport Mathlib.Data.Nat.Prime\nimport Mathlib.Tactic\n\ntheorem foo : True := sorry\n```"
    ])
    cfg = AutoformalizeConfig(num_candidates=1)

    result = stub_claim(
        claim="x",
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
    )

    assert "Mathlib.Data.Nat.Prime" in result.suggested_imports
    assert "Mathlib.Tactic" in result.suggested_imports


def test_stub_claim_retrieval_hits_from_index(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    idx = _make_index("Nat.Prime", "Nat.Prime.eq_one_or_self_of_dvd", "Real.pi")
    llm = MockLLM(responses=["```lean\ntheorem foo : True := sorry\n```"])
    cfg = AutoformalizeConfig(num_candidates=1)

    result = stub_claim(
        claim="every prime is odd or equal to 2",
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=idx,
    )

    # "prime" matches Nat.Prime and Nat.Prime.eq_one_or_self_of_dvd
    assert any("Prime" in h for h in result.retrieval_hits)


def test_stub_claim_includes_next_steps(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    llm = MockLLM(responses=["```lean\ntheorem foo : True := sorry\n```"])
    cfg = AutoformalizeConfig(num_candidates=1)

    result = stub_claim(
        claim="x",
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
    )

    assert len(result.next_steps) >= 3
    assert any("grd lean check" in s for s in result.next_steps)
    assert any("grd lean prove" in s for s in result.next_steps)
    assert any("grd lean verify-claim" in s for s in result.next_steps)


def test_stub_claim_user_imports_appended(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    llm = MockLLM(responses=["```lean\ntheorem foo : True := sorry\n```"])
    cfg = AutoformalizeConfig(num_candidates=1)

    result = stub_claim(
        claim="x",
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
        imports=["MyProject.Custom"],
    )

    assert "MyProject.Custom" in result.suggested_imports


def test_stub_claim_notes_empty_index(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    llm = MockLLM(responses=["```lean\ntheorem foo : True := sorry\n```"])
    cfg = AutoformalizeConfig(num_candidates=1)

    result = stub_claim(
        claim="x",
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
    )

    assert any("name index is empty" in n for n in result.notes)
