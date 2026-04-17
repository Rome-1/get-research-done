from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMAND = REPO_ROOT / "src/grd/commands/plan-phase.md"
PLANNER = REPO_ROOT / "src/grd/agents/grd-planner.md"


def test_plan_phase_command_does_not_expose_context7_tools() -> None:
    command = COMMAND.read_text(encoding="utf-8")

    assert "mcp__context7__*" not in command
    assert "Context7" not in command


def test_planner_prompt_uses_runtime_neutral_library_doc_guidance() -> None:
    planner = PLANNER.read_text(encoding="utf-8")

    assert "mcp__context7__*" not in planner
    assert "Context7" not in planner
    assert "Library Documentation Checks" in planner
    assert (
        "For Level 1-2 discovery on software libraries, verify API signatures, behavior, and version-sensitive features "
        "against authoritative documentation available in the current environment or project references."
        in planner
    )
    assert "do not hardcode any specific documentation connector into the planner prompt." in planner


def test_planner_prompt_trims_redundant_role_language() -> None:
    planner = PLANNER.read_text(encoding="utf-8")

    assert "Your job: Produce PLAN.md files that executors can carry out directly." in planner
    assert "Plans are prompts, not documents that become prompts." not in planner
