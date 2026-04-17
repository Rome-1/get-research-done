"""Seam regressions for the `literature-review` workflow vertical."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = REPO_ROOT / "src" / "grd" / "commands"
WORKFLOWS_DIR = REPO_ROOT / "src" / "grd" / "specs" / "workflows"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_literature_review_command_stays_thin_and_leaves_routing_to_the_workflow() -> None:
    command = _read(COMMANDS_DIR / "literature-review.md")

    assert "Follow `@{GRD_INSTALL_DIR}/workflows/literature-review.md` exactly." in command
    assert "The workflow owns staged loading, scope fixing, artifact gating, and citation verification." in command
    assert "grd-literature-reviewer" not in command
    assert "grd-bibliographer" not in command
    assert "grd commit" not in command


def test_literature_review_workflow_requires_reviewer_and_bibliographer_spawn_contracts() -> None:
    workflow = _read(WORKFLOWS_DIR / "literature-review.md")

    assert 'subagent_type="grd-literature-reviewer"' in workflow
    assert 'subagent_type="grd-bibliographer"' in workflow
    assert workflow.count("<spawn_contract>") >= 2
    assert "shared_state_policy: return_only" in workflow
    assert "GRD/literature/{slug}-REVIEW.md" in workflow
    assert "GRD/literature/{slug}-CITATION-SOURCES.json" in workflow
    assert "GRD/literature/{slug}-CITATION-AUDIT.md" in workflow
    assert "grd_return.files_written" in workflow
    assert "fresh continuation handoff" in workflow
    assert "checkpoint_response" in workflow
    assert "Do not trust the runtime handoff status by itself." in workflow
    assert "Proceed without citation audit." not in workflow


def test_literature_review_workflow_removes_legacy_commit_ownership_and_keeps_completion_fail_closed() -> None:
    workflow = _read(WORKFLOWS_DIR / "literature-review.md")

    assert "grd commit" not in workflow
    assert "Return to orchestrator through the typed child-return contract." in workflow
    assert "Route on `grd_return.status` and the artifact gate" in workflow
    assert "If the review is incomplete or blocked, use `grd_return.status: blocked` or `failed`" in workflow
    assert "spawn a fresh continuation run after the response" in workflow
