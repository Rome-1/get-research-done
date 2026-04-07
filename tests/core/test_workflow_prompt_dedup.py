"""Regression checks for planner workflow prompt deduplication."""

from __future__ import annotations

from pathlib import Path

from gpd.adapters.install_utils import expand_at_includes

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / "src/gpd/specs/workflows"
TEMPLATES_DIR = REPO_ROOT / "src/gpd/specs/templates"


def _read(name: str) -> str:
    return (WORKFLOWS_DIR / name).read_text(encoding="utf-8")


def _expand(name: str) -> str:
    return expand_at_includes(_read(name), REPO_ROOT / "src/gpd", "/runtime/")


def test_planner_workflows_expand_the_shared_planner_template_once_per_route() -> None:
    plan_phase_raw = _read("plan-phase.md")
    quick_raw = _read("quick.md")
    verify_work_raw = _read("verify-work.md")

    plan_phase = _expand("plan-phase.md")
    quick = _expand("quick.md")
    verify_work = _expand("verify-work.md")
    planner_template = (TEMPLATES_DIR / "planner-subagent-prompt.md").read_text(encoding="utf-8")

    for raw_text in (plan_phase_raw, quick_raw, verify_work_raw):
        assert "templates/planner-subagent-prompt.md" in raw_text
        assert "templates/phase-prompt.md" in raw_text
        assert "# Planner Subagent Prompt Template" not in raw_text

    assert planner_template.count("## Standard Planning Template") == 1
    assert planner_template.count("## Revision Template") == 1
    assert planner_template.count("@{GPD_INSTALL_DIR}/templates/plan-contract-schema.md") == 2

    assert "# Planner Subagent Prompt Template" in plan_phase
    assert plan_phase.count("# Planner Subagent Prompt Template") == 2
    assert "## Standard Planning Template" in plan_phase
    assert "## Revision Template" in plan_phase

    assert "project_contract_gate.authoritative" in planner_template


def test_planner_workflows_do_not_embed_the_removed_long_policy_blocks() -> None:
    plan_phase = _read("plan-phase.md")
    verify_work = _read("verify-work.md")

    for legacy_phrase in (
        "Each plan has a complete contract block (claims, deliverables, acceptance tests, forbidden proxies, uncertainty markers, and `references[]` whenever grounding is not already explicit elsewhere in the contract)",
        "Non-scoping plans keep `claims[]`, `deliverables[]`, `acceptance_tests[]`, and `forbidden_proxies[]` non-empty.",
        "Include `references[]` only when the plan relies on external grounding",
        "Keep the full canonical frontmatter, including `wave`, `depends_on`, `files_modified`, `interactive`, `conventions`, and `contract`.",
        "If the downstream fix plan will need specialized tooling or any other machine-checkable hard validation requirement, surface it in PLAN frontmatter `tool_requirements` before drafting task prose.",
        "If the revised fix plan still needs specialized tooling or any other machine-checkable hard validation requirement, keep it in PLAN frontmatter `tool_requirements` before rewriting task prose.",
        ):
        assert legacy_phrase not in plan_phase
        assert legacy_phrase not in verify_work


def test_planner_workflows_keep_tangent_policy_single_sourced() -> None:
    plan_phase = _read("plan-phase.md")

    assert plan_phase.count("Required 4-way tangent decision model:") == 1
    assert plan_phase.count("Branch as alternative hypothesis") == 1
