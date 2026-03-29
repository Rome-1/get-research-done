from __future__ import annotations

from pathlib import Path

from gpd.registry import get_command, list_commands

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = REPO_ROOT / "src" / "gpd" / "commands"
WORKFLOWS_DIR = REPO_ROOT / "src" / "gpd" / "specs" / "workflows"


def test_tour_command_is_registered_and_projectless() -> None:
    assert "tour" in list_commands()
    command = get_command("gpd:tour")
    assert command.name == "gpd:tour"
    assert command.context_mode == "projectless"


def test_tour_command_references_workflow() -> None:
    command_prompt = (COMMANDS_DIR / "tour.md").read_text(encoding="utf-8")
    assert "@{GPD_INSTALL_DIR}/workflows/tour.md" in command_prompt


def test_tour_workflow_introduces_a_safe_beginner_walkthrough() -> None:
    workflow = (WORKFLOWS_DIR / "tour.md").read_text(encoding="utf-8")

    for fragment in (
        "beginner-friendly guided tour",
        "does not change your files",
        "/gpd:start",
        "/gpd:new-project --minimal",
        "/gpd:map-research",
        "/gpd:resume-work",
        "/gpd:suggest-next",
        "/gpd:progress",
        "/gpd:explain",
        "/gpd:quick",
        "/gpd:help",
        "does not create project artifacts",
        "tour` does not execute those",
        "inspect the folder for you",
        "Do not ask the user to pick a branch and do not continue into another workflow",
    ):
        assert fragment in workflow
