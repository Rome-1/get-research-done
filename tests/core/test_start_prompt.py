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
        "research map but not a full project yet",
        "existing research folder",
        "fresh or mostly empty folder",
        "/gpd:resume-work",
        "/gpd:progress",
        "/gpd:quick",
        "/gpd:tour",
        "/gpd:map-research",
        "/gpd:new-project --minimal",
        "/gpd:new-project",
        "/gpd:explain",
        "/gpd:help --all",
        "Follow the installed `/gpd:new-project --minimal` command contract directly",
        "Follow the installed `/gpd:new-project` command contract directly",
        "Follow the installed `/gpd:help --all` command contract directly",
        "Show full command reference",
        "Use \\`gpd resume --recent\\` in your normal terminal to find the project first.",
        "Then open that project folder in the runtime and run \\`/gpd:resume-work\\`.",
        "not a parallel onboarding state machine",
    ):
        assert fragment in workflow

    assert "Read `{GPD_INSTALL_DIR}/workflows/new-project.md` with the file-read tool." not in workflow
    assert "Read `{GPD_INSTALL_DIR}/workflows/help.md` with the file-read tool." not in workflow
    assert "Read `{GPD_INSTALL_DIR}/workflows/tour.md` with the file-read tool." not in workflow
