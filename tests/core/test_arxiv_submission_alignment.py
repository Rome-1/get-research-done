"""Regression checks for arxiv submission prompt/workflow alignment."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = REPO_ROOT / "src/gpd/commands"
WORKFLOWS_DIR = REPO_ROOT / "src/gpd/specs/workflows"


def test_arxiv_submission_command_declares_manuscript_root_gates_without_first_match_discovery() -> None:
    command = (COMMANDS_DIR / "arxiv-submission.md").read_text(encoding="utf-8")

    assert "manuscript-root artifact manifest" in command
    assert "manuscript-root bibliography audit" in command
    assert "Follow `@{GPD_INSTALL_DIR}/workflows/arxiv-submission.md` exactly." in command
    assert "artifact_manifest" in command
    assert "bibliography_audit" in command
    assert "bibliography_audit_clean" in command
    assert "Paper target: $ARGUMENTS (optional; when omitted, the workflow resolves the manuscript root)." in command
    assert "@{GPD_INSTALL_DIR}/templates/paper/publication-manuscript-root-preflight.md" not in command
    assert "@{GPD_INSTALL_DIR}/references/publication/publication-review-round-artifacts.md" not in command
    assert "@{GPD_INSTALL_DIR}/references/publication/publication-response-artifacts.md" not in command


def test_arxiv_submission_workflow_resolves_manifest_based_manuscript_root_without_globbing() -> None:
    workflow = (WORKFLOWS_DIR / "arxiv-submission.md").read_text(encoding="utf-8")

    assert (
        "Apply the shared manuscript-root preflight, peer-review reliability, and round-artifact contract exactly:" in workflow
        or "Apply the shared manuscript-root artifact gates, peer-review reliability, and round-artifact contract exactly:" in workflow
    )
    assert "@{GPD_INSTALL_DIR}/templates/paper/publication-manuscript-root-preflight.md" in workflow
    assert "@{GPD_INSTALL_DIR}/references/publication/publication-review-round-artifacts.md" in workflow
    assert "@{GPD_INSTALL_DIR}/references/publication/publication-response-artifacts.md" not in workflow
    assert "ARTIFACT-MANIFEST.json" in workflow
    assert "BIBLIOGRAPHY-AUDIT.json" in workflow
    assert "bibliography_audit_clean" in workflow
    assert "gpd paper-build" in workflow
    assert "STOP and require an explicit manuscript path or a repaired manuscript-root state" in workflow
    assert "Do not fall back to `find` or arbitrary wildcard matching outside the documented default roots." in workflow
    assert 'ls "${DIR}"/*.tex' not in workflow
