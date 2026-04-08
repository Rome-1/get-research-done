"""Focused regressions for the Phase 11 coordinator-routing outliers."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / "src" / "gpd" / "specs" / "workflows"


def _read(name: str) -> str:
    return (WORKFLOWS_DIR / name).read_text(encoding="utf-8")


def test_debug_workflow_routes_on_typed_status_and_file_backed_diagnosis() -> None:
    workflow = _read("debug.md")

    assert "gpd_return.status: completed" in workflow
    assert "gpd_return.status: checkpoint" in workflow
    assert "gpd_return.status: blocked" in workflow
    assert "GPD/debug/{slug}.md" in workflow
    assert "session_status: diagnosed" in workflow
    assert "session file" in workflow
    assert "Do not route on heading markers in the returned text" in workflow
    assert "spawn a fresh continuation run" in workflow
    assert "## ROOT CAUSE FOUND" not in workflow
    assert "## INVESTIGATION INCONCLUSIVE" not in workflow


def test_new_project_and_new_milestone_route_roadmaps_on_typed_status() -> None:
    new_project = _read("new-project.md")
    new_milestone = _read("new-milestone.md")

    for workflow in (new_project, new_milestone):
        assert "gpd_return.status: completed" in workflow
        assert "gpd_return.status: blocked" in workflow
        assert "but `GPD/ROADMAP.md` or `GPD/STATE.md` is missing" in workflow
        assert "Do not trust the runtime handoff status by itself." in workflow
        assert "## ROADMAP CREATED" not in workflow
        assert "## ROADMAP BLOCKED" not in workflow


def test_parameter_sweep_balanced_mode_is_not_unconditionally_paused() -> None:
    workflow = _read("parameter-sweep.md")

    assert "autonomy=supervised" in workflow
    assert "autonomy=balanced" in workflow
    assert "only then pause for user approval" in workflow
    assert "If `autonomy=supervised`, show this plan and ask for confirmation before generating plans." in workflow
    assert "Proceed? (y/n)" not in workflow
