from __future__ import annotations

from pathlib import Path

from gpd.registry import get_command, list_commands


REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = REPO_ROOT / "src" / "gpd" / "commands"
WORKFLOWS_DIR = REPO_ROOT / "src" / "gpd" / "specs" / "workflows"


def test_start_command_is_registered_and_projectless() -> None:
    assert "start" in list_commands()
    command = get_command("gpd:start")
    assert command.name == "gpd:start"
    assert command.context_mode == "projectless"


def test_start_command_references_workflow() -> None:
    command_prompt = (COMMANDS_DIR / "start.md").read_text(encoding="utf-8")
    assert "@{GPD_INSTALL_DIR}/workflows/start.md" in command_prompt


def test_start_workflow_routes_to_existing_entrypoints() -> None:
    workflow = (WORKFLOWS_DIR / "start.md").read_text(encoding="utf-8")

    for fragment in (
        "existing GPD project",
        "existing research folder",
        "fresh or mostly empty folder",
        "/gpd:resume-work",
        "/gpd:progress",
        "/gpd:quick",
        "/gpd:map-research",
        "/gpd:new-project --minimal",
        "/gpd:new-project",
        "/gpd:explain",
        "/gpd:help",
        "not a parallel onboarding state machine",
    ):
        assert fragment in workflow
