"""Regression tests for complete-milestone prompt wiring."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_complete_milestone_command_uses_supported_version_placeholders_and_preloads_dependencies() -> None:
    command = _read("src/grd/commands/complete-milestone.md")

    assert "{{version}}" not in command
    assert "{version}" in command
    assert "Mark research milestone {version} complete" in command
    assert "GRD/v{version}-MILESTONE-AUDIT.md" in command
    assert "GRD/milestones/v{version}-ROADMAP.md" in command
    assert "GRD/milestones/v{version}-REQUIREMENTS.md" in command
    assert "chore: archive v{version} research milestone" in command
    assert "@{GRD_INSTALL_DIR}/workflows/complete-milestone.md" in command
    assert "@{GRD_INSTALL_DIR}/templates/milestone.md" in command
    assert "@{GRD_INSTALL_DIR}/templates/milestone-archive.md" in command


def test_complete_milestone_workflow_required_reading_uses_portable_runtime_paths() -> None:
    workflow = _read("src/grd/specs/workflows/complete-milestone.md")

    assert "1. `@{GRD_INSTALL_DIR}/templates/milestone.md`" in workflow
    assert "2. `@{GRD_INSTALL_DIR}/templates/milestone-archive.md`" in workflow
    assert "3. `GRD/ROADMAP.md`" in workflow
    assert "4. `GRD/REQUIREMENTS.md`" in workflow
    assert "5. `GRD/PROJECT.md`" in workflow
    assert "templates/milestone.md" not in workflow.replace("@{GRD_INSTALL_DIR}/templates/milestone.md", "")
    assert "templates/milestone-archive.md" not in workflow.replace("@{GRD_INSTALL_DIR}/templates/milestone-archive.md", "")


def test_complete_milestone_workflow_references_portable_archive_template() -> None:
    workflow = _read("src/grd/specs/workflows/complete-milestone.md")

    assert "@{GRD_INSTALL_DIR}/templates/milestone-archive.md" in workflow
    assert "ROADMAP archive** uses `templates/milestone-archive.md`" not in workflow
