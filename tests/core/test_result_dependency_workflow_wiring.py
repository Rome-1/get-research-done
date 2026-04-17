"""Focused regressions for dependency-aware canonical result reuse guidance."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPARE_EXPERIMENT = REPO_ROOT / "src/grd/specs/workflows/compare-experiment.md"
ERROR_PROPAGATION = REPO_ROOT / "src/grd/specs/workflows/error-propagation.md"
EXPLAIN_WORKFLOW = REPO_ROOT / "src/grd/specs/workflows/explain.md"
EXPLAIN_COMMAND = REPO_ROOT / "src/grd/commands/explain.md"
LIMITING_CASES = REPO_ROOT / "src/grd/specs/workflows/limiting-cases.md"
NUMERICAL_CONVERGENCE = REPO_ROOT / "src/grd/specs/workflows/numerical-convergence.md"
SENSITIVITY_ANALYSIS = REPO_ROOT / "src/grd/specs/workflows/sensitivity-analysis.md"
AGENT_INFRASTRUCTURE = REPO_ROOT / "src/grd/specs/references/orchestration/agent-infrastructure.md"


def test_compare_experiment_workflow_distinguishes_flat_search_from_reverse_trace() -> None:
    text = COMPARE_EXPERIMENT.read_text(encoding="utf-8")

    assert 'grd result search --depends-on "{upstream_result_id}"' in text
    assert 'grd result downstream "{upstream_result_id}"' in text
    assert "flat list of all downstream dependents" in text
    assert "reverse dependency tree separated into direct and transitive dependents" in text
    assert 'grd result show "{result_id}"' in text
    assert 'grd result deps "{result_id}"' in text


def test_error_propagation_workflow_prefers_result_deps_before_manual_tree_rebuild() -> None:
    text = ERROR_PROPAGATION.read_text(encoding="utf-8")

    assert 'use `grd result show "{result_id}"` for the direct stored-result view' in text
    assert 'before `grd result deps "{result_id}"` to recover the recorded dependency tree' in text
    assert 'run `grd result show "{result_id}"` first' in text
    assert 'then run `grd result deps "{result_id}"`' in text


def test_explain_surfaces_result_deps_for_upstream_context() -> None:
    workflow_text = EXPLAIN_WORKFLOW.read_text(encoding="utf-8")
    command_text = EXPLAIN_COMMAND.read_text(encoding="utf-8")

    assert 'grd result show "{result_id}"' in workflow_text
    assert 'grd result deps "{result_id}"' in workflow_text
    assert 'grd result downstream "{result_id}"' in workflow_text
    assert 'grd result show "{result_id}"' in command_text
    assert 'grd result deps "{result_id}"' in command_text
    assert 'grd result downstream "{result_id}"' in command_text


def test_lookup_first_validation_workflows_surface_result_show_after_search() -> None:
    numerical_text = NUMERICAL_CONVERGENCE.read_text(encoding="utf-8")
    limiting_text = LIMITING_CASES.read_text(encoding="utf-8")

    assert "grd result search" in numerical_text
    assert 'grd result show "{result_id}"' in numerical_text
    assert "grd result search" in limiting_text
    assert 'grd result show "{result_id}"' in limiting_text


def test_sensitivity_analysis_prompts_for_result_deps_after_canonical_lookup() -> None:
    text = SENSITIVITY_ANALYSIS.read_text(encoding="utf-8")

    assert 'grd result search' in text
    assert 'grd result show "{result_id}"' in text
    assert 'grd result deps "{result_id}"' in text


def test_agent_infrastructure_separates_phase_and_result_dependency_commands() -> None:
    text = AGENT_INFRASTRUCTURE.read_text(encoding="utf-8")

    assert 'grd query deps <identifier>' in text
    assert 'Trace a specific phase/frontmatter dependency across phases' in text
    assert 'grd result show <identifier>' in text
    assert 'Inspect one canonical result directly' in text
    assert text.count('grd result show <identifier>') >= 2
    assert 'grd result deps <identifier>' in text
    assert 'Trace dependencies for a canonical result identifier' in text
    assert 'grd result downstream <identifier>' in text
    assert 'Trace downstream dependents with direct/transitive separation' in text
