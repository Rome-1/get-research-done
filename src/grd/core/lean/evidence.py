"""Bridge from Lean type-check results to GRD ``VerificationEvidence`` records.

Phase 1.5 of the formal-proof integration: once ``grd lean check`` returns a
``LeanCheckResult``, callers need a principled mapping to the structured
evidence the rest of GRD already understands so it can live alongside other
verification records inside ``intermediate_results[*].verification_records``
in ``.grd/state.json``.

This module is deliberately tiny and side-effect-free — the actual state
mutation stays in ``grd.core.results.result_verify``. Keeping the mapping
isolated means the verifier/agent layer (grd-prover, ge-d8s) and the
autoformalization pipeline (ge-48t) can reuse it without coupling to the
state-persistence layer.
"""

from __future__ import annotations

from datetime import UTC, datetime

from grd.contracts import VerificationEvidence
from grd.core.lean.protocol import LeanCheckResult

__all__ = [
    "LEAN_VERIFIER",
    "LEAN_METHOD_TYPECHECK",
    "lean_result_to_evidence",
]


LEAN_VERIFIER = "grd-lean"
"""Canonical verifier string for evidence produced by the Lean backend."""

LEAN_METHOD_TYPECHECK = "lean4_typecheck"
"""Method tag for evidence produced by ``grd lean check`` type-checking."""


def lean_result_to_evidence(
    result: LeanCheckResult,
    *,
    verifier: str = LEAN_VERIFIER,
    method: str = LEAN_METHOD_TYPECHECK,
    evidence_path: str | None = None,
    notes: str | None = None,
    claim_id: str | None = None,
    deliverable_id: str | None = None,
    acceptance_test_id: str | None = None,
    verified_at: str | None = None,
) -> VerificationEvidence:
    """Translate a Lean check outcome into a ``VerificationEvidence`` record.

    Confidence is derived from what Lean actually said, not just the process
    exit code: a clean elaboration maps to ``high``; a compile that emitted
    warnings drops to ``medium``; anything Lean rejected — whether an
    elaboration error or an orchestration failure like ``lean_not_found`` —
    maps to ``unreliable`` so the record can't be mistaken for a passing
    proof downstream.
    """
    if result.ok:
        any_warning = any(d.severity == "warning" for d in result.diagnostics)
        confidence: str = "medium" if any_warning else "high"
    else:
        confidence = "unreliable"

    detail_bits = [f"backend={result.backend}", f"ok={result.ok}"]
    if result.error is not None:
        detail_bits.append(f"error={result.error}")
    if result.diagnostics:
        detail_bits.append(f"diagnostics={len(result.diagnostics)}")
    default_notes = "; ".join(detail_bits)

    return VerificationEvidence(
        verified_at=verified_at or datetime.now(UTC).isoformat(),
        verifier=verifier,
        method=method,
        confidence=confidence,  # type: ignore[arg-type]
        evidence_path=evidence_path,
        notes=notes or default_notes,
        claim_id=claim_id,
        deliverable_id=deliverable_id,
        acceptance_test_id=acceptance_test_id,
    )
