"""Prompt regressions for agent taxonomy and execution routing."""

from __future__ import annotations

from pathlib import Path

from grd import registry

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / "src" / "grd" / "agents"


def _read_agent(name: str) -> str:
    return (AGENTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def test_executor_prompt_describes_default_writable_scoped_task_role() -> None:
    executor = _read_agent("grd-executor")

    assert "default writable implementation agent" in executor
    assert "Scoped-task mode" in executor
    assert "the prompt itself is the execution contract" in executor
    assert "route it to grd-paper-writer" in executor
    assert "route it to grd-notation-coordinator" in executor


def test_planner_debugger_and_explainer_route_work_to_specialized_agents() -> None:
    planner = _read_agent("grd-planner")
    debugger = _read_agent("grd-debugger")
    explainer = _read_agent("grd-explainer")

    assert "go to `grd-executor`" in planner
    assert "goes to `grd-paper-writer`" in planner
    assert "goes to `grd-notation-coordinator`" in planner

    assert "hand it to `grd-executor`" in debugger
    assert "hand it to `grd-paper-writer`" in debugger
    assert "hand it to `grd-notation-coordinator`" in debugger

    assert "not the default writable implementation agent" in explainer
    assert "route that work to `grd-executor`" in explainer
    assert "route it to `grd-paper-writer`" in explainer
    assert "route it to `grd-notation-coordinator`" in explainer


def test_public_worker_prompts_identify_writable_production_surface() -> None:
    executor = _read_agent("grd-executor")
    debugger = _read_agent("grd-debugger")
    paper_writer = _read_agent("grd-paper-writer")

    assert "Agent surface: public writable production agent." in executor
    assert "Agent surface: public writable production agent specialized for discrepancy investigation" in debugger
    assert "Agent surface: public writable production agent for manuscript sections" in paper_writer
    assert (
        "On demand only: shared protocols, verification core, physics subfields, agent infrastructure, and cross-project patterns."
        in debugger
    )
    assert "@{GRD_INSTALL_DIR}/references/shared/shared-protocols.md" not in debugger
    assert "@{GRD_INSTALL_DIR}/references/orchestration/agent-infrastructure.md" not in debugger


def test_internal_agents_explicitly_identify_internal_specialist_surface() -> None:
    for name in registry.list_agents():
        agent = registry.get_agent(name)
        if agent.surface != "internal":
            continue
        content = _read_agent(name)
        assert "Agent surface: internal specialist subagent." in content, name
        assert "Do not act as the default writable implementation agent" in content, name


def test_consistency_checker_stays_one_shot_and_does_not_claim_resolution_work() -> None:
    source = _read_agent("grd-consistency-checker")

    assert "This is a one-shot handoff: inspect once, write once, return once." in source
    assert "grd_return.status: checkpoint" in source
    assert "status: completed | checkpoint | blocked | failed" in source
    assert "Do not act as the default writable implementation agent." in source
    assert "Do not claim ownership of code fixes, commits, convention-authoring, or pattern-library updates." in source
    assert "Create it from the template" not in source
    assert "grd pattern add" not in source
