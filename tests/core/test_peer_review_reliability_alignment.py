from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / "src/grd/specs/workflows"
REFERENCES_DIR = REPO_ROOT / "src/grd/specs/references"


def test_peer_review_workflow_references_canonical_reliability_doc_and_round_suffixed_artifacts() -> None:
    workflow = (WORKFLOWS_DIR / "peer-review.md").read_text(encoding="utf-8")

    assert "@{GRD_INSTALL_DIR}/references/publication/peer-review-reliability.md" in workflow
    assert ".grd/review/CLAIMS{round_suffix}.json" in workflow
    assert ".grd/review/STAGE-reader{round_suffix}.json" in workflow
    assert ".grd/review/STAGE-literature{round_suffix}.json" in workflow
    assert ".grd/review/STAGE-math{round_suffix}.json" in workflow
    assert ".grd/review/STAGE-physics{round_suffix}.json" in workflow
    assert ".grd/review/STAGE-interestingness{round_suffix}.json" in workflow
    assert ".grd/review/REVIEW-LEDGER{round_suffix}.json" in workflow
    assert ".grd/review/REFEREE-DECISION{round_suffix}.json" in workflow
    assert ".grd/REFEREE-REPORT{round_suffix}.md" in workflow
    assert ".grd/REFEREE-REPORT{round_suffix}.tex" in workflow
    assert "grd validate review-ledger .grd/review/REVIEW-LEDGER{round_suffix}.json" in workflow
    assert (
        "grd validate referee-decision .grd/review/REFEREE-DECISION{round_suffix}.json --strict --ledger "
        ".grd/review/REVIEW-LEDGER{round_suffix}.json"
    ) in workflow
    assert ".grd/" not in workflow


def test_peer_review_reliability_reference_uses_canonical_grd_paths_only() -> None:
    reliability = (REFERENCES_DIR / "publication" / "peer-review-reliability.md").read_text(encoding="utf-8")

    assert "Peer Review Phase Reliability" in reliability
    assert ".grd/STATE.md" in reliability
    assert ".grd/ROADMAP.md" in reliability
    assert ".grd/phases/" in reliability
    assert ".grd/review/REVIEW-LEDGER{round_suffix}.json" in reliability
    assert ".grd/review/REFEREE-DECISION{round_suffix}.json" in reliability
    assert ".grd/REFEREE-REPORT{round_suffix}.md" in reliability
    assert ".grd/AUTHOR-RESPONSE{round_suffix}.md" in reliability
    assert "grd validate review-claim-index .grd/review/CLAIMS{round_suffix}.json" in reliability
    assert "grd validate review-stage-report .grd/review/STAGE-<stage_id>{round_suffix}.json" in reliability
    assert "grd validate review-ledger .grd/review/REVIEW-LEDGER{round_suffix}.json" in reliability
    assert (
        "grd validate referee-decision .grd/review/REFEREE-DECISION{round_suffix}.json --strict --ledger "
        ".grd/review/REVIEW-LEDGER{round_suffix}.json"
    ) in reliability
    assert "bibliography_audit_clean" in reliability
    assert "reproducibility_ready" in reliability
    assert "proof_audits[]" in reliability
    assert "theorem-bearing claims" in reliability
    assert "claim record itself" in reliability
    assert "theorem_assumptions" not in reliability
    assert "theorem_parameters" not in reliability
    assert "`CLAIMS.json`" not in reliability
    assert "`REFEREE-DECISION.json`" not in reliability
    assert "`REVIEW-LEDGER.json`" not in reliability
    assert ".grd/" not in reliability
