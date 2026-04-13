"""Stage 6: decision gate.

Pure function from ``(similarity, cluster_consensus)`` to one of:

- ``AUTO_ACCEPT``: similarity ≥ auto_accept_similarity — the Lean statement
  faithfully represents the claim.
- ``CLUSTER_CONSENSUS``: similarity in the ambiguous band — accept only if a
  symbolic-equivalence cluster has ≥2 candidates agreeing (MVP: we treat this
  as "needs review by default" because we don't yet implement real clustering
  — ge-48t defers that to Phase 4+ per the bead).
- ``ESCALATE``: similarity < escalate_below_similarity — file a ``bd new -l
  human`` bead with the specific ambiguity surfaced.

Kept in its own module so the thresholds are testable without wiring an LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from grd.core.lean.autoformalize.config import AutoformalizeConfig

__all__ = [
    "DecisionOutcome",
    "FaithfulnessDecision",
    "decide_faithfulness",
]


DecisionOutcome = Literal["auto_accept", "cluster_consensus", "escalate"]


@dataclass(frozen=True)
class FaithfulnessDecision:
    """Outcome of the decision gate for one candidate."""

    outcome: DecisionOutcome
    similarity: float
    reason: str
    requires_cluster_consensus: bool = False


def decide_faithfulness(
    *,
    similarity: float,
    config: AutoformalizeConfig,
    cluster_size: int = 1,
) -> FaithfulnessDecision:
    """Apply §8.2 thresholds to produce a verdict for this candidate.

    ``cluster_size`` counts how many compiled candidates back-translate to
    similar English (typically recomputed via ``jaccard_similarity`` over
    pairs of back-translations). In the MVP, ``cluster_size >= 2`` upgrades
    an ambiguous-band candidate to ``AUTO_ACCEPT``; without that we mark it
    as needing human review.
    """
    if similarity >= config.auto_accept_similarity:
        return FaithfulnessDecision(
            outcome="auto_accept",
            similarity=similarity,
            reason=(f"similarity {similarity:.3f} >= auto-accept threshold {config.auto_accept_similarity:.2f}"),
        )
    if similarity < config.escalate_below_similarity:
        return FaithfulnessDecision(
            outcome="escalate",
            similarity=similarity,
            reason=(
                f"similarity {similarity:.3f} < escalate threshold "
                f"{config.escalate_below_similarity:.2f} — back-translation diverges from claim"
            ),
        )
    # Ambiguous band: require cluster consensus.
    if cluster_size >= 2:
        return FaithfulnessDecision(
            outcome="auto_accept",
            similarity=similarity,
            reason=(
                f"similarity {similarity:.3f} in ambiguous band; cluster consensus "
                f"of {cluster_size} candidates upgraded to auto-accept"
            ),
            requires_cluster_consensus=True,
        )
    return FaithfulnessDecision(
        outcome="cluster_consensus",
        similarity=similarity,
        reason=(
            f"similarity {similarity:.3f} in ambiguous band "
            f"[{config.escalate_below_similarity:.2f}, {config.auto_accept_similarity:.2f}); "
            "no cluster consensus — needs human review"
        ),
        requires_cluster_consensus=True,
    )
