from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = REPO_ROOT / "src/grd/commands"
WORKFLOWS_DIR = REPO_ROOT / "src/grd/specs/workflows"


def test_peer_review_surfaces_canonical_phase_summary_artifacts() -> None:
    workflow_text = (WORKFLOWS_DIR / "peer-review.md").read_text(encoding="utf-8")

    assert ".grd/phases/*/*SUMMARY.md" in workflow_text


def test_regression_check_searches_canonical_phase_summary_artifacts() -> None:
    workflow_text = (WORKFLOWS_DIR / "regression-check.md").read_text(encoding="utf-8")

    assert '-name "*SUMMARY.md"' in workflow_text


def test_verify_work_searches_canonical_phase_summary_artifacts() -> None:
    workflow_text = (WORKFLOWS_DIR / "verify-work.md").read_text(encoding="utf-8")

    assert 'ls "$phase_dir"/*SUMMARY.md 2>/dev/null' in workflow_text
    assert "ls .grd/phases/*/*SUMMARY.md 2>/dev/null | sort" in workflow_text


def test_verify_work_searches_canonical_phase_verification_artifacts() -> None:
    workflow_text = (WORKFLOWS_DIR / "verify-work.md").read_text(encoding="utf-8")

    assert "rg -l '^session_status: (validating|diagnosed)$' .grd/phases/*/*-VERIFICATION.md 2>/dev/null | sort | head -5" in workflow_text
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

    assert "roadmap-plus-disk union" in complete_milestone
    assert "Standalone `PLAN.md` / `SUMMARY.md` artifacts" in complete_milestone
    assert "for SUMMARY in .grd/phases/${PHASE_DIR}/*SUMMARY.md; do" in validate_conventions
    assert "ls .grd/phases/*/*SUMMARY.md 2>/dev/null" in graph
    assert "cat .grd/phases/*/*SUMMARY.md" in write_paper
    assert 'cat "$PHASE_DIR"/*SUMMARY.md 2>/dev/null' in write_paper
    assert 'VALIDATED=$(ls .grd/phases/*/*SUMMARY.md 2>/dev/null | xargs grep -El "approach_validated: true|comparison_verdicts:|contract_results:" 2>/dev/null | head -1)' in plan_phase


def test_transition_workflow_surfaces_standalone_phase_artifact_support() -> None:
    workflow_text = (WORKFLOWS_DIR / "transition.md").read_text(encoding="utf-8")

    assert 'ls "${PHASE_DIR}"/PLAN.md "${PHASE_DIR}"/*-PLAN.md 2>/dev/null | sort' in workflow_text
    assert 'ls "${PHASE_DIR}"/SUMMARY.md "${PHASE_DIR}"/*-SUMMARY.md 2>/dev/null | sort' in workflow_text
    assert 'cat ${PHASE_DIR}/SUMMARY.md ${PHASE_DIR}/*-SUMMARY.md 2>/dev/null' in workflow_text
    assert 'cat ${PHASE_DIR}/CONTEXT.md ${PHASE_DIR}/*-CONTEXT.md 2>/dev/null' in workflow_text
    assert "standalone and numbered PLAN files" in workflow_text
    assert "standalone and numbered SUMMARY files" in workflow_text
    assert "Counting standalone `PLAN.md` / `SUMMARY.md` alongside numbered `*-PLAN.md` / `*-SUMMARY.md` artifacts" in workflow_text


def test_progress_workflow_counts_standalone_and_numbered_phase_pairs() -> None:
    workflow_text = (WORKFLOWS_DIR / "progress.md").read_text(encoding="utf-8")

    assert ".grd/phases/[current-phase-dir]/PLAN.md" in workflow_text
    assert ".grd/phases/[current-phase-dir]/*-PLAN.md" in workflow_text
    assert ".grd/phases/[current-phase-dir]/SUMMARY.md" in workflow_text
    assert ".grd/phases/[current-phase-dir]/*-SUMMARY.md" in workflow_text
    assert 'for plan in .grd/phases/[current-phase-dir]/PLAN.md .grd/phases/[current-phase-dir]/*-PLAN.md; do' in workflow_text
    assert 'SUMMARY="$(dirname "$plan")/SUMMARY.md"' in workflow_text


def test_command_surfaces_list_standalone_and_numbered_phase_artifacts() -> None:
    progress = (COMMANDS_DIR / "progress.md").read_text(encoding="utf-8")
    regression_check = (COMMANDS_DIR / "regression-check.md").read_text(encoding="utf-8")
    show_phase = (COMMANDS_DIR / "show-phase.md").read_text(encoding="utf-8")
    audit = (COMMANDS_DIR / "audit-milestone.md").read_text(encoding="utf-8")
    write_paper = (COMMANDS_DIR / "write-paper.md").read_text(encoding="utf-8")

    assert ".grd/phases/[current-phase-dir]/PLAN.md" in progress
    assert ".grd/phases/[current-phase-dir]/*-PLAN.md" in progress
    assert ".grd/phases/[current-phase-dir]/SUMMARY.md" in progress
    assert ".grd/phases/[current-phase-dir]/*-SUMMARY.md" in progress
    assert "standalone `PLAN.md` and numbered `*-PLAN.md`" in show_phase
    assert "`SUMMARY.md` / `*-SUMMARY.md` artifact" in show_phase
    assert "find_files: .grd/phases/*/*SUMMARY.md" in audit
    assert "completed summary frontmatter (`SUMMARY.md` and `*-SUMMARY.md`)" in regression_check
    assert "ls .grd/phases/*/*SUMMARY.md 2>/dev/null" in write_paper


def test_respond_to_referees_prefers_canonical_markdown_report_path() -> None:
    workflow_text = (WORKFLOWS_DIR / "respond-to-referees.md").read_text(encoding="utf-8")

    assert "Use `.grd/REFEREE-REPORT{round_suffix}.md` as the canonical issue-ID source" in workflow_text
    assert "use canonical `.grd/REFEREE-REPORT{round_suffix}.md` only" in workflow_text
    assert "`.grd/paper/REFEREE_RESPONSE{round_suffix}.md`" in workflow_text
    assert "`.grd/AUTHOR-RESPONSE{round_suffix}.md`" in workflow_text
    assert "Read the completed `.grd/AUTHOR-RESPONSE{round_suffix}.md` and `.grd/paper/REFEREE_RESPONSE{round_suffix}.md`" in workflow_text
    assert "`.grd/paper/referee-report-*.md` or `paper/referee-reports/*.md`" not in workflow_text
