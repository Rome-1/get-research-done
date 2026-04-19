"""Autoformalization pipeline for GRD (ge-48t).

Implements the 6-stage pipeline from research/formal-proof-integration/AUTOFORMALIZATION.md
§8 as the retrieval/LLM harness that powers ``grd lean verify-claim`` and the
APOLLO-style repair loop used by ``grd lean prove``.

Layering (each module importable on its own):

    config.py       — FaithfulnessConfig loaded from ``.grd/lean-env.json``
                      (thresholds, budget, candidate count, model ID).
    llm.py          — LLMBackend protocol + MockLLM (tests) + anthropic adapter.
                      Also defines prompt-composition helpers.
    index.py        — NameIndex: Suffix Array Check over Mathlib4 + PhysLean
                      identifier snapshots. No Mathlib install required — reads
                      newline-delimited name files from the project's .grd dir.
    blueprint.py    — Stage 1: build the grounded Blueprint context for a claim
                      (phase text, conventions, physics flag).
    candidates.py   — Stage 3: DRAFT-SKETCH-PROVE candidate generation via the
                      configured LLM backend. N candidates returned verbatim.
    repair.py       — Stage 4: APOLLO-style compile-repair loop. Classifies
                      errors against §7 catalog and feeds them back to the LLM.
    faithfulness.py — Stage 5: back-translate to English + similarity gate.
                      Ships a deterministic token-Jaccard fallback so tests
                      (and CI without sentence-transformers) still work.
    decision.py     — Stage 6: pure threshold function. Returns AUTO_ACCEPT /
                      CLUSTER_CONSENSUS / ESCALATE.
    escalate.py     — Shell out to ``bd create -l human`` when the decision gate
                      demands human review. Captures the specific ambiguity.
    pipeline.py     — verify_claim(...) orchestrator. Threads 1→6 and returns a
                      VerifyClaimResult ready for CLI/JSON emission.

The pipeline never *requires* a real Claude API key or a real Mathlib snapshot
to import — every external dependency is pluggable and lazily loaded, so unit
tests monkeypatch the narrow seams and CI passes without network.
"""

from __future__ import annotations

from grd.core.lean.autoformalize.config import (
    DEFAULT_AUTO_ACCEPT_SIMILARITY,
    DEFAULT_ESCALATE_BELOW_SIMILARITY,
    DEFAULT_NUM_CANDIDATES,
    DEFAULT_REPAIR_BUDGET,
    AutoformalizeConfig,
    load_autoformalize_config,
)
from grd.core.lean.autoformalize.decision import (
    DecisionOutcome,
    FaithfulnessDecision,
    decide_faithfulness,
)
from grd.core.lean.autoformalize.faithfulness import (
    FaithfulnessReport,
    SemanticDiff,
    compute_semantic_diff,
    jaccard_similarity,
)
from grd.core.lean.autoformalize.index import NameIndex, load_default_index
from grd.core.lean.autoformalize.llm import (
    ErrorKind,
    LLMBackend,
    MockLLM,
    classify_compile_error,
)
from grd.core.lean.autoformalize.pipeline import (
    CandidateResult,
    VerifyClaimResult,
    verify_claim,
)

__all__ = [
    "DEFAULT_AUTO_ACCEPT_SIMILARITY",
    "DEFAULT_ESCALATE_BELOW_SIMILARITY",
    "DEFAULT_NUM_CANDIDATES",
    "DEFAULT_REPAIR_BUDGET",
    "AutoformalizeConfig",
    "CandidateResult",
    "DecisionOutcome",
    "ErrorKind",
    "FaithfulnessDecision",
    "FaithfulnessReport",
    "LLMBackend",
    "MockLLM",
    "NameIndex",
    "SemanticDiff",
    "VerifyClaimResult",
    "compute_semantic_diff",
    "classify_compile_error",
    "decide_faithfulness",
    "jaccard_similarity",
    "load_autoformalize_config",
    "load_default_index",
    "verify_claim",
]
