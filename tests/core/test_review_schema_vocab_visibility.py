"""Parity checks for review-related schema vocabularies."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, get_args, get_origin

from grd.contracts import (
    PROOF_AUDIT_COUNTEREXAMPLE_STATUS_VALUES,
    PROOF_AUDIT_QUANTIFIER_STATUS_VALUES,
    PROOF_AUDIT_SCOPE_STATUS_VALUES,
    ComparisonVerdict,
    ContractProofAudit,
    VerificationEvidence,
)
from grd.mcp.paper.models import (
    ProofAuditStatus,
    ReviewConfidence,
    ReviewIssueSeverity,
    ReviewIssueStatus,
    ReviewRecommendation,
    ReviewStageKind,
    ReviewSupportStatus,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_RESULTS_SCHEMA = REPO_ROOT / "src/grd/specs/templates/contract-results-schema.md"
PEER_REVIEW_PANEL = REPO_ROOT / "src/grd/specs/references/publication/peer-review-panel.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _literal_values(annotation: object) -> tuple[str, ...]:
    origin = get_origin(annotation)
    if origin is Literal:
        return tuple(arg for arg in get_args(annotation) if isinstance(arg, str))
    values: list[str] = []
    for arg in get_args(annotation):
        values.extend(_literal_values(arg))
    return tuple(values)


def _backticked_choice_line(field_name: str, values: tuple[str, ...]) -> str:
    return f"`{field_name}: {' | '.join(values)}`"


def _expect_backticked_choice_line(text: str, field_name: str, values: tuple[str, ...]) -> None:
    spaced = _backticked_choice_line(field_name, values)
    compact = f"`{field_name}: {'|'.join(values)}`"
    assert spaced in text or compact in text


def _expect_backticked_must_be_one_of_line(text: str, field_name: str, values: tuple[str, ...]) -> None:
    rendered_values = ", ".join(f"`{value}`" for value in values)
    assert f"`{field_name}` must be one of: {rendered_values}." in text


def test_contract_results_schema_surfaces_the_full_closed_proof_audit_vocab() -> None:
    text = _read(CONTRACT_RESULTS_SCHEMA)

    _expect_backticked_choice_line(
        text, "proof_audit.completeness", _literal_values(ContractProofAudit.model_fields["completeness"].annotation)
    )
    _expect_backticked_choice_line(text, "proof_audit.quantifier_status", PROOF_AUDIT_QUANTIFIER_STATUS_VALUES)
    _expect_backticked_choice_line(text, "proof_audit.scope_status", PROOF_AUDIT_SCOPE_STATUS_VALUES)
    _expect_backticked_choice_line(text, "proof_audit.counterexample_status", PROOF_AUDIT_COUNTEREXAMPLE_STATUS_VALUES)
    _expect_backticked_choice_line(
        text, "evidence[].confidence", _literal_values(VerificationEvidence.model_fields["confidence"].annotation)
    )
    _expect_backticked_choice_line(text, "subject_kind", _literal_values(ComparisonVerdict.model_fields["subject_kind"].annotation))
    _expect_backticked_choice_line(text, "subject_role", _literal_values(ComparisonVerdict.model_fields["subject_role"].annotation))
    _expect_backticked_choice_line(
        text, "comparison_kind", _literal_values(ComparisonVerdict.model_fields["comparison_kind"].annotation)
    )
    _expect_backticked_choice_line(text, "verdict", _literal_values(ComparisonVerdict.model_fields["verdict"].annotation))


def test_peer_review_panel_surfaces_the_full_closed_review_vocab() -> None:
    text = _read(PEER_REVIEW_PANEL)

    _expect_backticked_choice_line(text, "stage_kind", tuple(stage.value for stage in ReviewStageKind))
    _expect_backticked_choice_line(text, "findings[].severity", tuple(item.value for item in ReviewIssueSeverity))
    _expect_backticked_choice_line(text, "findings[].support_status", tuple(item.value for item in ReviewSupportStatus))
    _expect_backticked_choice_line(text, "confidence", tuple(item.value for item in ReviewConfidence))
    _expect_backticked_choice_line(text, "recommendation_ceiling", tuple(item.value for item in ReviewRecommendation))
    _expect_backticked_choice_line(text, "issues[].opened_by_stage", tuple(stage.value for stage in ReviewStageKind))
    _expect_backticked_choice_line(text, "issues[].status", tuple(item.value for item in ReviewIssueStatus))
    _expect_backticked_choice_line(text, "final_recommendation", tuple(item.value for item in ReviewRecommendation))
    _expect_backticked_choice_line(text, "final_confidence", tuple(item.value for item in ReviewConfidence))
    _expect_backticked_must_be_one_of_line(text, "proof_audits[].alignment_status", tuple(item.value for item in ProofAuditStatus))
