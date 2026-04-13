"""Top-level orchestrator for the 6-stage autoformalization pipeline.

``verify_claim(...)`` is the single entry point that:

1. reads the grounded Blueprint context from state.json + conventions,
2. loads the Mathlib4 / PhysLean name index,
3. generates N candidate Lean statements via the LLM,
4. runs each through an APOLLO-style compile-repair loop,
5. for each compiled candidate, back-translates and scores similarity,
6. applies the decision gate; on ESCALATE / CLUSTER_CONSENSUS (no cluster),
   files a ``bd new -l human`` bead with the specific ambiguity.

The orchestrator is deliberately imperative: the interesting work lives in
the stage modules, and this file just threads them together so the
per-candidate story is easy to trace in the emitted JSON.

The pipeline NEVER hard-fails on transport issues (bd missing, index absent,
lean not installed). It records the degradation in the result so the caller
can choose to treat it as a blocker. "Report what happened" beats "raise
ValueError" for a long-running batch over a phase with 50 claims.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from grd.core.lean.autoformalize.blueprint import BlueprintContext, extract_blueprint_context
from grd.core.lean.autoformalize.candidates import Candidate, generate_candidates
from grd.core.lean.autoformalize.config import AutoformalizeConfig, load_autoformalize_config
from grd.core.lean.autoformalize.decision import FaithfulnessDecision, decide_faithfulness
from grd.core.lean.autoformalize.escalate import BeadEscalationResult, escalate_to_human
from grd.core.lean.autoformalize.faithfulness import (
    FaithfulnessReport,
    assess_faithfulness,
    jaccard_similarity,
)
from grd.core.lean.autoformalize.index import NameIndex, load_default_index
from grd.core.lean.autoformalize.repair import (
    LeanCheckFn,
    RepairOutcome,
    repair_candidate,
)

if TYPE_CHECKING:
    from grd.core.lean.autoformalize.llm import LLMBackend

__all__ = [
    "CandidateResult",
    "VerifyClaimResult",
    "verify_claim",
]


@dataclass(frozen=True)
class CandidateResult:
    """Full per-candidate trace: generation → repair → faithfulness → decision."""

    index: int
    candidate: Candidate
    repair: RepairOutcome
    faithfulness: FaithfulnessReport | None = None
    decision: FaithfulnessDecision | None = None


@dataclass(frozen=True)
class VerifyClaimResult:
    """Final pipeline output for one informal claim.

    ``outcome`` mirrors the winning candidate's decision (or ``"escalate"`` if
    no candidate compiled). ``chosen_source`` is the Lean code the user should
    accept; it's ``None`` when we bailed to human review. The ``candidates``
    list carries every attempt for debugging — even the ones that failed — so
    the CLI JSON is rich enough for a second pass without rerunning.
    """

    claim: str
    outcome: str
    chosen_source: str | None
    chosen_back_translation: str | None
    chosen_similarity: float | None
    candidates: list[CandidateResult] = field(default_factory=list)
    blueprint: BlueprintContext | None = None
    index_source: str = ""
    escalation: BeadEscalationResult | None = None
    notes: list[str] = field(default_factory=list)


def verify_claim(
    *,
    claim: str,
    project_root: Path,
    llm: LLMBackend,
    config: AutoformalizeConfig | None = None,
    index: NameIndex | None = None,
    phase: str | None = None,
    physics_override: bool | None = None,
    imports: list[str] | None = None,
    lean_check: LeanCheckFn | None = None,
    escalate_fn: Callable[..., BeadEscalationResult] | None = None,
    use_daemon: bool = True,
    timeout_s: float = 30.0,
) -> VerifyClaimResult:
    """Run stages 1→6 for one informal claim and return the verdict.

    ``config`` / ``index`` are resolvable from ``project_root`` — callers pass
    them in only when they already built one (batch runs, tests, etc.).
    ``lean_check`` and ``escalate_fn`` are seams for tests — production callers
    leave them at ``None`` and get the real lean client / ``bd create`` shell-out.
    """
    cfg = config or load_autoformalize_config(project_root)
    idx = index or load_default_index(project_root, cfg)
    blueprint = extract_blueprint_context(
        claim=claim,
        project_root=project_root,
        phase=phase,
        physics_override=physics_override,
    )
    notes: list[str] = []
    if idx.size == 0:
        notes.append(
            "name index is empty — DDR hallucination check is disabled; "
            "drop a newline-delimited identifier snapshot into "
            ".grd/mathlib4-names.txt to enable grounded retrieval"
        )

    candidates = generate_candidates(
        blueprint=blueprint,
        index=idx,
        llm=llm,
        config=cfg,
    )

    candidate_results: list[CandidateResult] = []
    compiled: list[CandidateResult] = []

    for cand in candidates:
        repair = repair_candidate(
            candidate=cand,
            blueprint=blueprint,
            index=idx,
            llm=llm,
            project_root=project_root,
            repair_budget=cfg.repair_budget,
            timeout_s=timeout_s,
            imports=imports,
            use_daemon=use_daemon,
            lean_check=lean_check,
        )
        result = CandidateResult(index=cand.index, candidate=cand, repair=repair)
        candidate_results.append(result)
        if repair.ok:
            compiled.append(result)

    if not compiled:
        esc = _escalate_no_compile(
            claim=claim,
            candidates=candidate_results,
            project_root=project_root,
            escalate_fn=escalate_fn,
        )
        return VerifyClaimResult(
            claim=claim,
            outcome="escalate",
            chosen_source=None,
            chosen_back_translation=None,
            chosen_similarity=None,
            candidates=candidate_results,
            blueprint=blueprint,
            index_source=idx.source,
            escalation=esc,
            notes=notes + ["no candidate compiled within repair budget"],
        )

    # Score every compiled candidate so we have a cluster to reason over.
    scored: list[CandidateResult] = []
    for r in compiled:
        fr = assess_faithfulness(
            claim=claim,
            lean_source=r.repair.final_source,
            llm=llm,
        )
        # decision.cluster_size is updated below once we know the cluster; for
        # now we store a single-candidate decision so the trace is complete.
        provisional = decide_faithfulness(similarity=fr.similarity, config=cfg, cluster_size=1)
        scored.append(
            CandidateResult(
                index=r.index, candidate=r.candidate, repair=r.repair, faithfulness=fr, decision=provisional
            )
        )

    # Pick the top-scoring compiled candidate; compute cluster consensus over
    # back-translations using the same Jaccard primitive so the MVP is
    # symbolic-equiv-cluster-shaped without requiring a true cluster algorithm.
    scored.sort(key=lambda r: r.faithfulness.similarity if r.faithfulness else 0.0, reverse=True)
    winner = scored[0]
    assert winner.faithfulness is not None  # compiled path always produces one

    cluster_size = _cluster_consensus_size(winner, scored, config=cfg)
    decision = decide_faithfulness(
        similarity=winner.faithfulness.similarity,
        config=cfg,
        cluster_size=cluster_size,
    )
    winner = CandidateResult(
        index=winner.index,
        candidate=winner.candidate,
        repair=winner.repair,
        faithfulness=winner.faithfulness,
        decision=decision,
    )
    # Re-insert the re-decided winner in-place so the emitted candidates list
    # reflects the final verdict, not the provisional one.
    scored[0] = winner

    # Merge the scored list back into the full candidate_results for emission:
    # compiled candidates get faithfulness/decision; failed ones keep their
    # empty slots.
    by_index = {r.index: r for r in scored}
    merged: list[CandidateResult] = []
    for r in candidate_results:
        merged.append(by_index.get(r.index, r))

    escalation: BeadEscalationResult | None = None
    if decision.outcome != "auto_accept":
        escalation = _escalate_low_confidence(
            claim=claim,
            winner=winner,
            decision=decision,
            project_root=project_root,
            escalate_fn=escalate_fn,
        )

    chosen_source = winner.repair.final_source if decision.outcome == "auto_accept" else None

    return VerifyClaimResult(
        claim=claim,
        outcome=decision.outcome,
        chosen_source=chosen_source,
        chosen_back_translation=winner.faithfulness.back_translation,
        chosen_similarity=winner.faithfulness.similarity,
        candidates=merged,
        blueprint=blueprint,
        index_source=idx.source,
        escalation=escalation,
        notes=notes,
    )


def _cluster_consensus_size(
    winner: CandidateResult,
    scored: list[CandidateResult],
    *,
    config: AutoformalizeConfig,
    threshold: float = 0.6,
) -> int:
    """Count compiled candidates whose back-translations paraphrase the winner.

    We use Jaccard similarity on the back-translations themselves — two
    candidates that paraphrase to similar English are treated as semantically
    equivalent for the MVP. This is a stand-in for the symbolic-equivalence
    clustering in §8.2 pro pipeline and is explicitly listed as deferred in
    the bead. ``threshold`` defaults to 0.6: generous enough to cluster
    genuine paraphrases, strict enough to reject different theorems that
    happen to share stopwords.
    """
    if winner.faithfulness is None:
        return 1
    cluster = 1
    winner_back = winner.faithfulness.back_translation
    for other in scored:
        if other.index == winner.index or other.faithfulness is None:
            continue
        if jaccard_similarity(winner_back, other.faithfulness.back_translation) >= threshold:
            cluster += 1
    # Clamp by the active ambiguous band so the decision layer behaves
    # predictably — a cluster of 3 doesn't escalate just because the top
    # similarity was already above auto_accept.
    _ = config  # reserved for future per-project overrides
    return cluster


def _escalate_no_compile(
    *,
    claim: str,
    candidates: list[CandidateResult],
    project_root: Path,
    escalate_fn: Callable[..., BeadEscalationResult] | None,
) -> BeadEscalationResult:
    fn = escalate_fn or escalate_to_human
    last_reasons = "; ".join(c.repair.reason for c in candidates if c.repair.reason)
    title = "autoformalize: no candidate compiled — human review needed"
    body = (
        f"Informal claim:\n{claim}\n\n"
        f"All {len(candidates)} candidates failed to compile within the repair budget.\n"
        f"Last per-candidate reasons: {last_reasons or '(none)'}\n\n"
        "Filed automatically by grd lean verify-claim (ge-48t)."
    )
    return fn(title=title, body=body, project_root=project_root)


def _escalate_low_confidence(
    *,
    claim: str,
    winner: CandidateResult,
    decision: FaithfulnessDecision,
    project_root: Path,
    escalate_fn: Callable[..., BeadEscalationResult] | None,
) -> BeadEscalationResult:
    fn = escalate_fn or escalate_to_human
    assert winner.faithfulness is not None
    title = f"autoformalize: {decision.outcome.replace('_', ' ')} — human review needed"
    body = (
        f"Informal claim:\n{claim}\n\n"
        f"Top Lean candidate:\n```lean\n{winner.repair.final_source.strip()}\n```\n\n"
        f"Back-translation:\n{winner.faithfulness.back_translation}\n\n"
        f"Similarity: {winner.faithfulness.similarity:.3f} ({winner.faithfulness.backend})\n"
        f"Reason: {decision.reason}\n\n"
        "Filed automatically by grd lean verify-claim (ge-48t)."
    )
    return fn(title=title, body=body, project_root=project_root)
