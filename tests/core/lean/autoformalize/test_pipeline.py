"""End-to-end tests for ``grd.core.lean.autoformalize.pipeline.verify_claim``.

All external seams are stubbed: the LLM is a ``MockLLM``, ``lean_check`` is a
callable, and the escalation function is a capturing stub. These tests pin
the orchestration across the three terminal outcomes (auto_accept, escalate,
cluster_consensus) so refactors to the inner stages can't silently change the
pipeline's contract.
"""

from __future__ import annotations

from pathlib import Path

from grd.core.lean.autoformalize.config import AutoformalizeConfig
from grd.core.lean.autoformalize.escalate import BeadEscalationResult
from grd.core.lean.autoformalize.index import NameIndex
from grd.core.lean.autoformalize.llm import MockLLM
from grd.core.lean.autoformalize.pipeline import verify_claim
from grd.core.lean.protocol import LeanCheckResult, LeanDiagnostic


def _ok() -> LeanCheckResult:
    return LeanCheckResult(ok=True, backend="subprocess", elapsed_ms=3, diagnostics=[])


def _fail(msg: str = "type mismatch") -> LeanCheckResult:
    return LeanCheckResult(
        ok=False,
        backend="subprocess",
        elapsed_ms=1,
        diagnostics=[LeanDiagnostic(severity="error", message=msg)],
    )


class _StubCheck:
    def __init__(self, results: list[LeanCheckResult]) -> None:
        self._results = list(results)
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs: object) -> LeanCheckResult:
        self.calls.append(kwargs)
        if not self._results:
            # Fall through — if the pipeline compiles more than we scripted,
            # return a generic failure so we notice.
            return _fail("script exhausted")
        return self._results.pop(0)


class _EscalateSpy:
    def __init__(self, bead_id: str | None = "ge-test") -> None:
        self.calls: list[dict[str, object]] = []
        self._bead_id = bead_id

    def __call__(self, **kwargs: object) -> BeadEscalationResult:
        self.calls.append(kwargs)
        return BeadEscalationResult(attempted=True, bead_id=self._bead_id, title=kwargs.get("title", ""))


def _candidate_and_backtranslation(claim: str) -> list[str]:
    """One candidate source + its back-translation, repeated per candidate."""
    return [
        f"```lean\ntheorem foo : True := trivial  -- for: {claim}\n```",
        claim,  # back-translation returns claim verbatim → similarity 1.0
    ]


def test_auto_accept_path_picks_top_candidate(tmp_path: Path) -> None:
    """Happy path: candidate compiles, back-translation matches, similarity ≥ 0.85."""
    claim = "pi is irrational"
    cfg = AutoformalizeConfig(num_candidates=1, repair_budget=0)
    llm = MockLLM(responses=_candidate_and_backtranslation(claim))
    check = _StubCheck([_ok()])
    escalate = _EscalateSpy()

    result = verify_claim(
        claim=claim,
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
        lean_check=check,
        escalate_fn=escalate,
    )

    assert result.outcome == "auto_accept"
    assert result.chosen_source is not None
    assert "theorem foo" in result.chosen_source
    assert result.chosen_similarity == 1.0
    assert result.escalation is None
    assert escalate.calls == []  # no bead filed on auto-accept
    assert len(result.candidates) == 1
    assert result.candidates[0].decision is not None
    assert result.candidates[0].decision.outcome == "auto_accept"


def test_no_candidate_compiles_escalates(tmp_path: Path) -> None:
    cfg = AutoformalizeConfig(num_candidates=2, repair_budget=0)
    # Two candidates, no back-translations (won't be reached).
    llm = MockLLM(
        responses=[
            "```lean\nbad1\n```",
            "```lean\nbad2\n```",
        ]
    )
    check = _StubCheck([_fail(), _fail()])
    escalate = _EscalateSpy(bead_id="ge-failbead")

    result = verify_claim(
        claim="some claim",
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
        lean_check=check,
        escalate_fn=escalate,
    )

    assert result.outcome == "escalate"
    assert result.chosen_source is None
    assert result.chosen_similarity is None
    assert result.escalation is not None
    assert result.escalation.bead_id == "ge-failbead"
    assert len(escalate.calls) == 1
    assert "no candidate compiled" in escalate.calls[0]["title"]
    assert "no candidate compiled within repair budget" in result.notes


def test_low_similarity_routes_to_escalate(tmp_path: Path) -> None:
    """Compiles cleanly but back-translation has no overlap → similarity 0.0 → escalate."""
    claim = "pi is irrational"
    cfg = AutoformalizeConfig(num_candidates=1, repair_budget=0)
    llm = MockLLM(
        responses=[
            "```lean\ntheorem foo : True := trivial\n```",
            "completely unrelated goldbach statement",  # 0 token overlap
        ]
    )
    check = _StubCheck([_ok()])
    escalate = _EscalateSpy(bead_id="ge-lowbead")

    result = verify_claim(
        claim=claim,
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
        lean_check=check,
        escalate_fn=escalate,
    )

    assert result.outcome == "escalate"
    assert result.chosen_source is None
    assert result.chosen_similarity == 0.0
    assert result.escalation is not None
    assert result.escalation.bead_id == "ge-lowbead"
    assert "escalate" in escalate.calls[0]["title"]


def test_ambiguous_band_without_cluster_requests_human_review(tmp_path: Path) -> None:
    """Similarity in [0.70, 0.85) with no cluster consensus → cluster_consensus outcome."""
    claim = "every even number is the sum of two primes"
    cfg = AutoformalizeConfig(num_candidates=1, repair_budget=0)
    # Content tokens (after stopword strip):
    #   claim → {every, even, number, sum, two, primes}          (6)
    #   trans → {every, even, number, sum, two, primes, plus, more} (8)
    # Intersection 6, union 8 → Jaccard 0.75 — in the ambiguous band.
    llm = MockLLM(
        responses=[
            "```lean\ntheorem foo : True := trivial\n```",
            "every even number sum two primes plus more",
        ]
    )
    check = _StubCheck([_ok()])
    escalate = _EscalateSpy(bead_id="ge-clusterbead")

    result = verify_claim(
        claim=claim,
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
        lean_check=check,
        escalate_fn=escalate,
    )

    assert result.outcome == "cluster_consensus"
    assert result.chosen_source is None
    assert result.chosen_similarity is not None
    assert 0.70 <= result.chosen_similarity < 0.85
    assert result.escalation is not None
    assert "cluster consensus" in escalate.calls[0]["title"]


def test_cluster_consensus_upgrades_two_agreeing_candidates_to_accept(tmp_path: Path) -> None:
    """Two candidates land in the ambiguous band but back-translate to paraphrases."""
    claim = "every even number is the sum of two primes"
    cfg = AutoformalizeConfig(num_candidates=2, repair_budget=0)
    # Both back-translations score ~0.75 vs the claim (in band) AND jaccard
    # ≥ 0.6 against each other, so the cluster size reaches 2 and the winner
    # upgrades to auto_accept.
    llm = MockLLM(
        responses=[
            # candidate 1 source
            "```lean\ntheorem foo : True := trivial\n```",
            # candidate 2 source
            "```lean\ntheorem bar : True := trivial\n```",
            # candidate 1 back-translation: sim vs claim = 6/8 = 0.75
            "every even number sum two primes plus more",
            # candidate 2 back-translation: also in band, paraphrases candidate 1
            "every even number sum two primes plus extra",
        ]
    )
    check = _StubCheck([_ok(), _ok()])
    escalate = _EscalateSpy()

    result = verify_claim(
        claim=claim,
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
        lean_check=check,
        escalate_fn=escalate,
    )

    assert result.outcome == "auto_accept"
    assert result.chosen_source is not None
    # Auto-accept via cluster consensus — no escalation filed.
    assert escalate.calls == []
    # The winning decision should record that cluster consensus was required.
    winner = next(c for c in result.candidates if c.decision and c.decision.outcome == "auto_accept")
    assert winner.decision is not None
    assert winner.decision.requires_cluster_consensus is True


def test_escalate_unfiled_when_bd_missing(tmp_path: Path) -> None:
    """bd missing from PATH must surface as ``escalate_unfiled`` with a
    top-level warning so the human sees the silent-failure (UX-STUDY.md §P0-8
    / ge-1hr). ``escalation_attempted`` and ``escalation_error`` are promoted
    to the top-level result so ``--raw`` JSON consumers don't have to dig
    into the nested ``escalation`` object.
    """
    cfg = AutoformalizeConfig(num_candidates=1, repair_budget=0)
    llm = MockLLM(responses=["```lean\nbad1\n```"])
    check = _StubCheck([_fail()])

    def _escalate_bd_missing(**kwargs: object) -> BeadEscalationResult:
        return BeadEscalationResult(
            attempted=False,
            bead_id=None,
            error="bd CLI not found on PATH",
            title=str(kwargs.get("title", "")),
        )

    result = verify_claim(
        claim="some claim",
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
        lean_check=check,
        escalate_fn=_escalate_bd_missing,
    )

    assert result.outcome == "escalate_unfiled"
    assert result.chosen_source is None
    assert result.warning is not None
    assert "ESCALATION NOT FILED" in result.warning
    # The warning should direct the user to the install + manual-filing path.
    assert "bd create" in result.warning
    assert result.escalation_attempted is False
    assert result.escalation_error == "bd CLI not found on PATH"
    # The nested escalation block is still preserved for the manual-filing body.
    assert result.escalation is not None
    assert result.escalation.bead_id is None


def test_escalate_unfiled_when_bd_runs_but_errors(tmp_path: Path) -> None:
    """bd present but failing mid-run is a different failure mode than bd
    missing — the warning text should explain that bd ran but returned no
    bead id, and the outcome is still promoted to ``escalate_unfiled``.
    """
    cfg = AutoformalizeConfig(num_candidates=1, repair_budget=0)
    llm = MockLLM(responses=["```lean\nbad1\n```"])
    check = _StubCheck([_fail()])

    def _escalate_bd_broken(**kwargs: object) -> BeadEscalationResult:
        return BeadEscalationResult(
            attempted=True,
            bead_id=None,
            error="bd create exited 2: dolt down",
            title=str(kwargs.get("title", "")),
        )

    result = verify_claim(
        claim="some claim",
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
        lean_check=check,
        escalate_fn=_escalate_bd_broken,
    )

    assert result.outcome == "escalate_unfiled"
    assert result.warning is not None
    assert "bd ran but did not return a bead id" in result.warning
    assert "dolt down" in result.warning
    assert result.escalation_attempted is True
    assert result.escalation_error == "bd create exited 2: dolt down"


def test_escalate_filed_stays_escalate(tmp_path: Path) -> None:
    """When bd filed a bead the outcome stays ``escalate`` — no warning."""
    cfg = AutoformalizeConfig(num_candidates=1, repair_budget=0)
    llm = MockLLM(responses=["```lean\nbad\n```"])
    check = _StubCheck([_fail()])
    escalate = _EscalateSpy(bead_id="ge-filed")

    result = verify_claim(
        claim="some claim",
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
        lean_check=check,
        escalate_fn=escalate,
    )

    assert result.outcome == "escalate"
    assert result.warning is None
    assert result.escalation_attempted is True
    assert result.escalation_error is None


def test_auto_accept_exposes_chosen_goals(tmp_path: Path) -> None:
    """chosen_goals comes from the winning candidate's repair outcome (ge-2zu)."""
    claim = "one equals one"
    cfg = AutoformalizeConfig(num_candidates=1, repair_budget=0)
    llm = MockLLM(responses=_candidate_and_backtranslation(claim))
    # Compile returns ok with goals_after=[] (all goals closed).
    ok_with_goals = LeanCheckResult(ok=True, backend="subprocess", elapsed_ms=3, diagnostics=[], goals_after=[])
    check = _StubCheck([ok_with_goals])
    escalate = _EscalateSpy()

    result = verify_claim(
        claim=claim,
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
        lean_check=check,
        escalate_fn=escalate,
    )

    assert result.outcome == "auto_accept"
    assert result.chosen_goals == []


def test_chosen_goals_none_when_no_compile(tmp_path: Path) -> None:
    """When no candidate compiles, chosen_goals is None."""
    cfg = AutoformalizeConfig(num_candidates=1, repair_budget=0)
    llm = MockLLM(responses=["```lean\nbad\n```"])
    check = _StubCheck([_fail()])
    escalate = _EscalateSpy(bead_id="ge-test")

    result = verify_claim(
        claim="some claim",
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
        lean_check=check,
        escalate_fn=escalate,
    )

    assert result.outcome == "escalate"
    assert result.chosen_goals is None


def test_notes_flag_empty_index(tmp_path: Path) -> None:
    """An empty NameIndex should surface a note explaining DDR is disabled."""
    cfg = AutoformalizeConfig(num_candidates=1, repair_budget=0)
    llm = MockLLM(responses=_candidate_and_backtranslation("x"))
    check = _StubCheck([_ok()])

    result = verify_claim(
        claim="x",
        project_root=tmp_path,
        llm=llm,
        config=cfg,
        index=NameIndex.empty(),
        lean_check=check,
        escalate_fn=_EscalateSpy(),
    )
    assert any("name index is empty" in note for note in result.notes)
