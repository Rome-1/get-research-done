from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / "src/grd/specs/workflows"
COMMANDS_DIR = REPO_ROOT / "src/grd/commands"
PUBLICATION_BOOTSTRAP_PREFLIGHT_INCLUDE = (
    "@{GRD_INSTALL_DIR}/references/publication/publication-bootstrap-preflight.md"
)
PUBLICATION_RESPONSE_WRITER_HANDOFF_INCLUDE = (
    "@{GRD_INSTALL_DIR}/references/publication/publication-response-writer-handoff.md"
)
PUBLICATION_ROUND_ARTIFACTS_INCLUDE = (
    "@{GRD_INSTALL_DIR}/references/publication/publication-review-round-artifacts.md"
)
PUBLICATION_REVIEW_RELIABILITY_INCLUDE = "@{GRD_INSTALL_DIR}/references/publication/peer-review-reliability.md"


def _workflow_text(name: str) -> str:
    return (WORKFLOWS_DIR / name).read_text(encoding="utf-8")


def _command_text(name: str) -> str:
    return (COMMANDS_DIR / name).read_text(encoding="utf-8")


def test_write_paper_workflow_runs_centralized_review_preflight() -> None:
    workflow = _workflow_text("write-paper.md")
    shared_preflight = (
        REPO_ROOT / "src/grd/specs/templates/paper/publication-manuscript-root-preflight.md"
    ).read_text(encoding="utf-8")

    assert "grd validate review-preflight write-paper --strict" in workflow
    assert "Run the centralized review preflight before continuing:" in workflow
    assert "Do not satisfy that gate with legacy `.grd/paper/` publication artifacts" in workflow
    assert "Strict review for that resume path uses `${PAPER_DIR}/ARTIFACT-MANIFEST.json`" in workflow
    assert "missing manuscript" not in workflow
    assert 'PAPER_DIR="$DIR"' in workflow
    assert 'PAPER_DIR="paper"' in workflow
    assert '${PAPER_DIR}/{topic_specific_stem}.tex' in workflow


def test_respond_to_referees_workflow_runs_centralized_review_preflight() -> None:
    workflow = _workflow_text("respond-to-referees.md")
    shared_preflight = (
        REPO_ROOT / "src/grd/specs/templates/paper/publication-manuscript-root-preflight.md"
    ).read_text(encoding="utf-8")

    assert 'grd validate review-preflight respond-to-referees "$ARGUMENTS" --strict' in workflow
    assert "grd validate review-preflight respond-to-referees --strict" in workflow
    assert "missing referee report source when provided as a path" in workflow
    assert "Any spawned agent that needs user input must return `status: checkpoint` and stop" in workflow
    assert "Do not ask the child agent to wait inside the same run" in workflow
    assert "Apply the shared publication bootstrap preflight exactly:" in workflow
    assert PUBLICATION_BOOTSTRAP_PREFLIGHT_INCLUDE in workflow
    assert PUBLICATION_RESPONSE_WRITER_HANDOFF_INCLUDE in workflow
    assert "bibliography_audit_clean" in shared_preflight
    assert "reproducibility_ready" in shared_preflight
    assert "Treat those files as complete only if the expected mirrored artifacts exist on disk" in workflow
    assert "${PAPER_DIR}/response-letter.tex" in workflow
    assert "${PAPER_DIR}/{section}.tex" in workflow


def test_arxiv_submission_workflow_runs_centralized_review_preflight() -> None:
    workflow = _workflow_text("arxiv-submission.md")
    shared_preflight = (
        REPO_ROOT / "src/grd/specs/templates/paper/publication-manuscript-root-preflight.md"
    ).read_text(encoding="utf-8")

    assert 'grd validate review-preflight arxiv-submission "$ARGUMENTS" --strict' in workflow
    assert "grd validate review-preflight arxiv-submission --strict" in workflow
    assert "Strict preflight also requires `ARTIFACT-MANIFEST.json` and `BIBLIOGRAPHY-AUDIT.json` beside the resolved manuscript entry point." in workflow
    assert "not from legacy `.grd/paper/` copies or some other manuscript directory" in workflow
    assert "strict preflight treats the latest round-specific pair as authoritative submission-gate input" in workflow
    assert "latest recommendation is `accept` or `minor_revision` with no unresolved blocking issues" in workflow
    assert "The same resolved manuscript root is also the strict preflight source of truth for `ARTIFACT-MANIFEST.json`, `BIBLIOGRAPHY-AUDIT.json`, and the compiled PDF." in workflow
    assert "If `$ARGUMENTS` specifies a `.tex` file, set `resolved_main_tex` to that file" in workflow
    assert "canonical manuscript `.tex` entrypoint under that directory" in workflow
    assert 'MAIN_SOURCE="${resolved_main_tex}"' in workflow


def test_peer_review_workflow_runs_centralized_review_preflight_with_explicit_arguments() -> None:
    workflow = _workflow_text("peer-review.md")

    assert 'grd validate review-preflight peer-review "$ARGUMENTS" --strict' in workflow
    assert "grd validate review-preflight peer-review --strict" not in workflow


def test_verify_work_workflow_runs_centralized_review_preflight() -> None:
    workflow = _workflow_text("verify-work.md")

    assert 'grd validate review-preflight verify-work "${PHASE_ARG}" --strict' in workflow
    assert "grd validate review-preflight verify-work --strict" in workflow
