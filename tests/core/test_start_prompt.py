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
        "Give a first-run chooser for people who may not know GPD yet.",
        "GPD project` (a folder where GPD already saved its own project files, notes, and state)",
        "research map` (GPD's summary of an existing research folder before full project setup)",
        "In GPD terms, \\`map-research\\` means inspect an existing folder before planning.",
        "In GPD terms, \\`new-project\\` creates the project scaffolding GPD will use later.",
        "Reply with the number or the option name.",
        "This folder already has saved GPD work (`GPD project`)",
        "This folder already has GPD's folder summary (`research map`)",
        "This folder already has research files, but GPD is not set up here yet",
        "This folder looks new or mostly empty",
        "I will show the safest next steps first and the broader options second.",
        "Recommended next steps:",
        "Keep the numbered list short.",
        "Other useful options, only if one of these is what you need:",
        "Resume this project (recommended)",
        "Suggest the next best step",
        "Review the project status first",
        "Do one small bounded task",
        "Explain one concept",
        "Show all commands",
        "Map this folder first (recommended)",
        "Start a brand-new GPD project anyway",
        "Take a guided tour first",
        "Fast start (recommended)",
        "Full guided setup",
        "Turn this into a full GPD project",
        "Reopen a different GPD project",
        "broader capability overview",
        "planning phases, verifying work, writing papers, and handling tangents",
        "This is the in-runtime continue command for an existing GPD project.",
        "This is a normal-terminal recovery command, not an in-runtime slash command.",
        "/gpd:resume-work",
        "/gpd:progress",
        "/gpd:quick",
        "/gpd:tour",
        "/gpd:map-research",
        "/gpd:new-project --minimal",
        "/gpd:new-project",
        "/gpd:explain",
        "/gpd:help --all",
        "If the researcher chooses `Resume this project (recommended)` or `Continue where I left off`:",
        "If the researcher chooses `Map this folder first (recommended)` or `Refresh the research map`:",
        "Follow the installed `/gpd:new-project --minimal` command contract directly",
        "Follow the installed `/gpd:new-project` command contract directly",
        "Follow the installed `/gpd:help --all` command contract directly",
        "Use \\`gpd resume --recent\\` in your normal terminal to find the project first.",
        "Then open that project folder in the runtime and run \\`/gpd:resume-work\\`.",
        "In GPD terms, \\`resume-work\\` is the in-runtime continue command after you find the right project.",
        "Do not silently create project files from `/gpd:start` itself.",
        "Do not silently switch the user into a different project folder.",
        "When in doubt between a fresh folder and an existing research folder, prefer `map-research` as the safer recommendation.",
        "keep the official GPD terms visible in plain-English form",
    ):
        assert fragment in workflow

    assert "Read `{GPD_INSTALL_DIR}/workflows/new-project.md` with the file-read tool." not in workflow
    assert "Read `{GPD_INSTALL_DIR}/workflows/help.md` with the file-read tool." not in workflow
    assert "Read `{GPD_INSTALL_DIR}/workflows/tour.md` with the file-read tool." not in workflow
