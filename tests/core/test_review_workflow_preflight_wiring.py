from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / "src/grd/specs/workflows"


def _workflow_text(name: str) -> str:
    return (WORKFLOWS_DIR / name).read_text(encoding="utf-8")


def test_write_paper_workflow_runs_centralized_review_preflight() -> None:
    workflow = _workflow_text("write-paper.md")

    assert "grd validate review-preflight write-paper --strict" in workflow
    assert "Run the centralized review preflight before continuing:" in workflow


def test_respond_to_referees_workflow_runs_centralized_review_preflight() -> None:
    workflow = _workflow_text("respond-to-referees.md")

    assert 'grd validate review-preflight respond-to-referees "$ARGUMENTS" --strict' in workflow
    assert "grd validate review-preflight respond-to-referees --strict" in workflow


def test_arxiv_submission_workflow_runs_centralized_review_preflight() -> None:
    workflow = _workflow_text("arxiv-submission.md")

    assert 'grd validate review-preflight arxiv-submission "$ARGUMENTS" --strict' in workflow
    assert "grd validate review-preflight arxiv-submission --strict" in workflow


def test_verify_work_workflow_runs_centralized_review_preflight() -> None:
    workflow = _workflow_text("verify-work.md")

    assert 'grd validate review-preflight verify-work "${PHASE_ARG}" --strict' in workflow
    assert "grd validate review-preflight verify-work --strict" in workflow
