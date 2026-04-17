"""Prompt-visibility regressions for the review agents."""

from __future__ import annotations

from pathlib import Path

from grd.adapters.install_utils import expand_at_includes
from grd.mcp.paper.models import (
    ClaimIndex,
    ClaimRecord,
    ClaimType,
    ReviewConfidence,
    ReviewIssueSeverity,
    ReviewIssueStatus,
    ReviewRecommendation,
    ReviewStageKind,
    ReviewSupportStatus,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / "src/grd/agents"
REFERENCES_DIR = REPO_ROOT / "src/grd/specs/references"


def _read(agent_name: str) -> str:
    return (AGENTS_DIR / agent_name).read_text(encoding="utf-8")


def _expanded(agent_name: str) -> str:
    return expand_at_includes(_read(agent_name), SPEC_ROOT, "/runtime/")


def _enum_line(field_name: str, enum_type: type[object]) -> str:
    values = " | ".join(member.value for member in enum_type)
    return f"{field_name}: {values}"


def _assert_shared_contract_pointer(text: str, contract_fragment: str) -> None:
    assert "references/publication/peer-review-panel.md" in text
    assert contract_fragment in text
    assert "Do not restate that schema here." in text
    assert "Required schema for" not in text
    assert "closed schema; do not invent extra keys" not in text


def test_review_reader_prompt_surfaces_full_claim_index_schema() -> None:
    review_reader = (AGENTS_DIR / "grd-review-reader.md").read_text(encoding="utf-8")
    claims_schema = _between(
        review_reader,
        "full `ClaimIndex` and `StageReviewReport` contracts",
    )
    assert "Stage 1 must also emit `GRD/review/CLAIMS{round_suffix}.json`." in review_reader
    assert "Capture theorem kind, explicit hypotheses, and free target parameters for theorem-like claims." in review_reader
    assert "Keep `proof_audits` empty in this stage." in review_reader
    assert "Focus `findings` on overclaiming, missing promised deliverables, and claim-structure blockers." in review_reader

    expanded = _expanded("grd-review-reader.md")
    assert "Peer Review Panel Protocol" not in expanded
    assert "Stage 1 `CLAIMS{round_suffix}.json` must follow this compact `ClaimIndex` shape:" not in expanded
    assert "StageReviewReport`, nested `ReviewFinding`, and nested `ProofAuditRecord` entries use a closed schema" not in expanded


def test_review_reader_prompt_surfaces_full_stage_review_schema() -> None:
    review_reader = (AGENTS_DIR / "grd-review-reader.md").read_text(encoding="utf-8")
    stage_schema = _between(
        review_reader,
        "Required schema for `STAGE-reader{round_suffix}.json` (`StageReviewReport`, mirroring the staged-review contract):",
        "</artifact_format>",
    )

    _assert_stage_review_contract_visible(stage_schema, ReviewStageKind.reader.value)
    assert "not the final referee decision" in stage_schema
    assert "STAGE-reader.json" not in stage_schema
    assert "round-specific variant when instructed" not in stage_schema


def test_peer_review_panel_reference_surfaces_stage1_claim_index_schema() -> None:
    panel = (REFERENCES_DIR / "publication" / "peer-review-panel.md").read_text(encoding="utf-8")
    claims_schema = _between(
        panel,
        "Stage 1 `CLAIMS{round_suffix}.json` must follow this compact `ClaimIndex` shape:",
        "The final adjudicator JSON artifacts must follow these canonical schemas:",
    )

    _assert_schema_tokens_visible(claims_schema)
    assert "closed schema" in claims_schema
    assert "do not invent extra keys" in claims_schema
    assert "required `ClaimIndex` metadata" in claims_schema
    assert "lowercase 64-hex digest" in claims_schema
    assert "Stage 1 `CLAIMS.json` must follow this compact `ClaimIndex` shape:" not in panel


def test_expanded_review_reader_prompt_keeps_claim_index_metadata_visible() -> None:
    expanded = expand_at_includes(
        (AGENTS_DIR / "grd-review-reader.md").read_text(encoding="utf-8"),
        REPO_ROOT / "src/grd/specs",
        "/runtime/",
    )

    assert "Peer Review Panel Protocol" in expanded
    assert '"manuscript_path": "paper/main.tex"' in expanded
    assert '"manuscript_sha256": "<sha256>"' in expanded
    assert '"supporting_artifacts": ["paper/figures/main-result.pdf"]' in expanded


def test_review_literature_prompt_surfaces_full_stage_review_schema() -> None:
    literature = (AGENTS_DIR / "grd-review-literature.md").read_text(encoding="utf-8")
    stage_schema = _between(
        literature,
        "Required schema for `STAGE-literature{round_suffix}.json` (`StageReviewReport`, mirroring the staged-review contract):",
        "Required finding coverage:",
    )

    _assert_stage_review_contract_visible(stage_schema, ReviewStageKind.literature.value)
    assert ".grd/review/STAGE-literature{round_suffix}.json" in literature
    assert "STAGE-literature.json" not in literature


def test_stage_review_agents_surface_compact_stage_review_schema() -> None:
    for agent_name, marker, stage_kind in (
        (
            "grd-review-math.md",
            "Required schema for `STAGE-math{round_suffix}.json` (`StageReviewReport`, mirroring the staged-review contract):",
            "math",
        ),
        (
            "grd-review-physics.md",
            "Required schema for `STAGE-physics{round_suffix}.json` (`StageReviewReport`, mirroring the staged-review contract):",
            "physics",
        ),
        (
            "grd-review-significance.md",
            "Required schema for `STAGE-interestingness{round_suffix}.json` (`StageReviewReport`, mirroring the staged-review contract):",
            "interestingness",
        ),
    ):
        expanded = expand_at_includes(
            (AGENTS_DIR / agent_name).read_text(encoding="utf-8"),
            REPO_ROOT / "src/grd/specs",
            "/runtime/",
        )
        schema = _between(expanded, marker, "Required finding coverage:")
        _assert_stage_review_contract_visible(schema, stage_kind)
        assert "do not collapse them to prose or scalars" in schema
        assert "{round_suffix}.json" in expanded
        assert "round-specific variant" not in expanded
