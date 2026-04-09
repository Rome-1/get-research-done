"""Routing regressions for the `plan-phase` checker seam."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PHASE = REPO_ROOT / "src/gpd/specs/workflows/plan-phase.md"


def test_plan_phase_separates_planner_checkpoint_handling_from_checker_revision() -> None:
    source = PLAN_PHASE.read_text(encoding="utf-8")

    assert "## 9b. Handle Planner Checkpoint" in source
    assert "spawn a fresh `gpd-planner` continuation handoff" in source
    assert "Do not route planner checkpoints into the checker revision loop." in source
    assert "Only after the planner returns `completed` should the workflow advance to checker review." in source
    assert "Present to user, get response, spawn continuation (step 12)" not in source


def test_plan_phase_routes_checker_statuses_through_structured_fields() -> None:
    source = PLAN_PHASE.read_text(encoding="utf-8")

    assert "`gpd_return.status: completed`" in source
    assert "`gpd_return.status: checkpoint`" in source
    assert "`gpd_return.status: blocked`" in source
    assert "`gpd_return.status: failed`" in source
    assert "Record approved plans from the structured `approved_plans` list only." in source
    assert "Record blocked plans from the structured `blocked_plans` list only." in source
    assert "Approved Plans (ready for execution)" not in source
    assert 'Approved Plans" table' not in source
    assert "plan-ID reconciliation" in source


def test_plan_phase_fails_closed_on_plan_id_mismatch_before_accepting_checker_success() -> None:
    source = PLAN_PHASE.read_text(encoding="utf-8")

    assert "`approved_plans` names only readable `*-PLAN.md` artifacts" in source
    assert "`blocked_plans` is empty" in source
    assert "every approved plan file still exists and matches the approved plan IDs" in source
    assert "Reject the return if any listed plan ID does not map to a readable `*-PLAN.md` file" in source
    assert "send the checker output back through the revision loop as a fail-closed mismatch" in source
