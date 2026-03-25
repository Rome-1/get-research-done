from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / "src/gpd/specs/workflows"


def test_peer_review_surfaces_canonical_phase_summary_artifacts() -> None:
    workflow_text = (WORKFLOWS_DIR / "peer-review.md").read_text(encoding="utf-8")

    assert "GPD/phases/*/*SUMMARY.md" in workflow_text


def test_regression_check_searches_canonical_phase_summary_artifacts() -> None:
    workflow_text = (WORKFLOWS_DIR / "regression-check.md").read_text(encoding="utf-8")

    assert '-name "*SUMMARY.md"' in workflow_text


def test_verify_work_searches_canonical_phase_summary_artifacts() -> None:
    workflow_text = (WORKFLOWS_DIR / "verify-work.md").read_text(encoding="utf-8")

    assert 'ls "$phase_dir"/*SUMMARY.md 2>/dev/null' in workflow_text
    assert "ls GPD/phases/*/*SUMMARY.md 2>/dev/null | sort" in workflow_text


def test_verify_work_searches_canonical_phase_verification_artifacts() -> None:
    workflow_text = (WORKFLOWS_DIR / "verify-work.md").read_text(encoding="utf-8")

    assert "rg -l '^session_status: (validating|diagnosed)$' GPD/phases/*/*-VERIFICATION.md 2>/dev/null | sort | head -5" in workflow_text
    assert 'ls "$phase_dir"/*-VERIFICATION.md 2>/dev/null | head -1' in workflow_text


def test_execute_plan_searches_standalone_and_numbered_phase_artifacts() -> None:
    workflow_text = (WORKFLOWS_DIR / "execute-plan.md").read_text(encoding="utf-8")

    assert 'ls "${phase_dir}"/PLAN.md "${phase_dir}"/*-PLAN.md 2>/dev/null | sort' in workflow_text
    assert 'ls "${phase_dir}"/SUMMARY.md "${phase_dir}"/*-SUMMARY.md 2>/dev/null | sort' in workflow_text
    assert "Canonical standalone pairing is `PLAN.md` <-> `SUMMARY.md`" in workflow_text


def test_show_phase_and_verify_phase_surface_standalone_summary_semantics() -> None:
    show_phase = (WORKFLOWS_DIR / "show-phase.md").read_text(encoding="utf-8")
    verify_phase = (WORKFLOWS_DIR / "verify-phase.md").read_text(encoding="utf-8")

    assert "`PLAN.md` and `*-PLAN.md`" in show_phase
    assert "`SUMMARY.md` and `*-SUMMARY.md`" in show_phase
    assert 'for plan in "$phase_dir"/PLAN.md "$phase_dir"/*-PLAN.md; do' in verify_phase
    assert 'PREV_SUMMARY=$(ls "$PREV_PHASE_DIR"/SUMMARY.md "$PREV_PHASE_DIR"/*-SUMMARY.md 2>/dev/null | tail -1)' in verify_phase
    assert 'CURR_SUMMARY=$(ls "$phase_dir"/SUMMARY.md "$phase_dir"/*-SUMMARY.md 2>/dev/null | tail -1)' in verify_phase


def test_summary_driven_workflows_search_canonical_summary_artifacts() -> None:
    complete_milestone = (WORKFLOWS_DIR / "complete-milestone.md").read_text(encoding="utf-8")
    validate_conventions = (WORKFLOWS_DIR / "validate-conventions.md").read_text(encoding="utf-8")
    graph = (WORKFLOWS_DIR / "graph.md").read_text(encoding="utf-8")
    write_paper = (WORKFLOWS_DIR / "write-paper.md").read_text(encoding="utf-8")
    plan_phase = (WORKFLOWS_DIR / "plan-phase.md").read_text(encoding="utf-8")

    assert "for summary in GPD/phases/*/*SUMMARY.md; do" in complete_milestone
    assert "cat GPD/phases/*/*SUMMARY.md" in complete_milestone
    assert "for SUMMARY in GPD/phases/${PHASE_DIR}/*SUMMARY.md; do" in validate_conventions
    assert "ls GPD/phases/*/*SUMMARY.md 2>/dev/null" in graph
    assert "cat GPD/phases/*/*SUMMARY.md" in write_paper
    assert 'cat "$PHASE_DIR"/*SUMMARY.md 2>/dev/null' in write_paper
    assert 'VALIDATED=$(ls GPD/phases/*/*SUMMARY.md 2>/dev/null | xargs grep -El "approach_validated: true|comparison_verdicts:|contract_results:" 2>/dev/null | head -1)' in plan_phase


def test_respond_to_referees_prefers_canonical_markdown_report_path() -> None:
    workflow_text = (WORKFLOWS_DIR / "respond-to-referees.md").read_text(encoding="utf-8")

    assert "Use `GPD/REFEREE-REPORT{round_suffix}.md` as the canonical issue-ID source" in workflow_text
    assert "prefer canonical `GPD/REFEREE-REPORT{round_suffix}.md`" in workflow_text
    assert "`GPD/paper/referee-report-*.md` or `paper/referee-reports/*.md`" in workflow_text
