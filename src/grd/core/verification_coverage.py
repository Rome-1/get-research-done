"""Formal proof coverage computations over state.json verification records.

Checks 5.20 (universal.formal_statement) and 5.21 (universal.formal_proof) are
recorded on intermediate results as VerificationEvidence entries. This module
aggregates those entries into claim-level coverage metrics for surfacing in
`/grd:progress` and the verification MCP tool.
"""

from __future__ import annotations

from collections.abc import Iterable

__all__ = [
    "FORMAL_STATEMENT_METHODS",
    "FORMAL_PROOF_METHODS",
    "collect_verification_records_from_state",
    "formal_proof_coverage_from_records",
    "formal_proof_coverage_from_state",
]


FORMAL_STATEMENT_METHODS: frozenset[str] = frozenset(
    {"5.20", "universal.formal_statement", "formal_statement"}
)
FORMAL_PROOF_METHODS: frozenset[str] = frozenset(
    {"5.21", "universal.formal_proof", "formal_proof"}
)


def _record_subject(record: dict) -> str | None:
    """Return the stable identity of what a record is evidence for.

    Prefers claim_id, then deliverable_id, then acceptance_test_id. Returns
    None when none of these are bound (an unbound formal record).
    """
    for key in ("claim_id", "deliverable_id", "acceptance_test_id"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def collect_verification_records_from_state(state: object) -> list[dict]:
    """Flatten verification_records from intermediate_results in a state dict."""
    if not isinstance(state, dict):
        return []
    results = state.get("intermediate_results")
    if not isinstance(results, list):
        return []
    flat: list[dict] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        records = item.get("verification_records")
        if not isinstance(records, list):
            continue
        for record in records:
            if isinstance(record, dict):
                flat.append(record)
    return flat


def formal_proof_coverage_from_records(
    verification_records: Iterable[object],
    *,
    total_claims: int | None = None,
) -> dict:
    """Compute formal-proof coverage metrics from a flat list of records.

    Args:
        verification_records: Iterable of VerificationEvidence-shaped dicts.
            Non-dict entries and malformed records are skipped defensively.
        total_claims: Optional denominator for blueprint completion. When
            provided and positive, blueprint_completion_percent = proofs /
            total_claims. Otherwise the denominator is the number of claims
            that have entered the formal track (any formal_statement record).

    Returns:
        A dict with counts, the blueprint completion percent, and per-bucket
        claim IDs. A record bearing check 5.21 implies a formal statement
        exists for the same claim, so the statement count always includes
        claims with proofs.
    """
    claims_with_statement: set[str] = set()
    claims_with_proof: set[str] = set()
    unbound_statements = 0
    unbound_proofs = 0

    for record in verification_records:
        if not isinstance(record, dict):
            continue
        method = record.get("method")
        if not isinstance(method, str):
            continue
        method_norm = method.strip()
        if not method_norm:
            continue
        is_statement = method_norm in FORMAL_STATEMENT_METHODS
        is_proof = method_norm in FORMAL_PROOF_METHODS
        if not (is_statement or is_proof):
            continue
        subject = _record_subject(record)
        if subject is None:
            if is_proof:
                unbound_proofs += 1
            if is_statement:
                unbound_statements += 1
            continue
        if is_proof:
            claims_with_proof.add(subject)
            claims_with_statement.add(subject)
        if is_statement:
            claims_with_statement.add(subject)

    claims_with_formal_statement = len(claims_with_statement)
    claims_with_formal_proof = len(claims_with_proof)

    if total_claims is not None and total_claims > 0:
        denom = total_claims
    else:
        denom = claims_with_formal_statement

    blueprint_completion_percent = (
        round(claims_with_formal_proof / denom * 100, 1) if denom > 0 else 0.0
    )

    statement_only = sorted(claims_with_statement - claims_with_proof)

    return {
        "total_claims": total_claims,
        "claims_with_formal_statement": claims_with_formal_statement,
        "claims_with_formal_proof": claims_with_formal_proof,
        "claims_with_statement_only": len(statement_only),
        "blueprint_completion_percent": blueprint_completion_percent,
        "unbound_formal_statements": unbound_statements,
        "unbound_formal_proofs": unbound_proofs,
        "claim_ids": {
            "formal_statement": sorted(claims_with_statement),
            "formal_proof": sorted(claims_with_proof),
            "statement_only": statement_only,
        },
    }


def formal_proof_coverage_from_state(
    state: object, *, total_claims: int | None = None
) -> dict:
    """Compute formal-proof coverage metrics from a state dict."""
    records = collect_verification_records_from_state(state)
    return formal_proof_coverage_from_records(records, total_claims=total_claims)
