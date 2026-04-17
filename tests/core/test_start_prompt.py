from __future__ import annotations

from pathlib import Path

from grd.adapters.install_utils import expand_at_includes
from grd.registry import get_command, list_commands
from tests.doc_surface_contracts import assert_start_workflow_router_contract

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = REPO_ROOT / "src" / "grd" / "commands"
WORKFLOWS_DIR = REPO_ROOT / "src" / "grd" / "specs" / "workflows"
SOURCE_ROOT = REPO_ROOT / "src" / "grd"
PATH_PREFIX = "/runtime/"


def test_start_command_is_registered_and_projectless() -> None:
    assert "start" in list_commands()
    command = get_command("grd:start")
    assert command.name == "grd:start"
    assert command.context_mode == "projectless"


def test_start_command_references_workflow() -> None:
    raw_command_prompt = (COMMANDS_DIR / "start.md").read_text(encoding="utf-8")
    command_prompt = expand_at_includes(raw_command_prompt, SOURCE_ROOT, PATH_PREFIX)

    assert "@{GRD_INSTALL_DIR}/workflows/start.md" in raw_command_prompt
    assert "@{GRD_INSTALL_DIR}/references/onboarding/beginner-command-taxonomy.md" in raw_command_prompt
    assert "grd resume" in command_prompt
    assert "grd resume --recent" in command_prompt
    assert "grd:resume-work" in command_prompt
    assert "grd:suggest-next" in command_prompt
    assert "advisory recent-project picker" in command_prompt
    assert "reloads canonical state in the reopened project" in command_prompt
    assert (
        command_prompt.index("`grd resume` remains the local read-only current-workspace recovery snapshot")
        < command_prompt.index("`grd resume --recent` remains the normal-terminal advisory recent-project picker")
        < command_prompt.index("`grd:suggest-next` is the fastest post-resume next command")
    )


def test_start_workflow_routes_to_existing_entrypoints() -> None:
    workflow = (WORKFLOWS_DIR / "start.md").read_text(encoding="utf-8")

    assert_start_workflow_router_contract(workflow)

    for fragment_options in (
        (
            "GRD project` (a folder where GRD already saved its own project files, notes, and state)",
            "GRD project` (a folder where GRD already saved its own project files, notes, and state",
        ),
        (
            "research map` (GRD's summary of an existing research folder before full project setup)",
            "research map` (GRD's summary of an existing research folder before full project setup",
        ),
        ("In GRD terms, \\`map-research\\` means inspect an existing folder before planning.",),
        ("In GRD terms, \\`new-project\\` creates the project scaffolding GRD will use later.",),
        ("This folder already has saved GRD work (`GRD project`)",),
        ("This folder already has GRD's folder summary (`research map`)",),
        ("This folder already has research files, but GRD is not set up here yet",),
        ("This folder looks new or mostly empty",),
        ("I will show the safest next steps first and the broader options second.",),
        ("Keep the numbered list short.",),
        ("Resume this project (recommended)",),
        ("Review the project status first",),
        ("Map this folder first (recommended)",),
        ("Start a brand-new GRD project anyway",),
        ("Fast start (recommended)",),
        ("Full guided setup",),
        ("Turn this into a full GRD project",),
        ("Reopen a different GRD project",),
        (
            "This is the in-runtime continue command for an existing GRD project.",
            "This is the in-runtime recovery command for the selected project.",
            "This is the in-runtime return path for the selected project.",
        ),
        (
            "If the researcher chooses `Resume this project (recommended)` or `Continue where I left off`:",
            "If the researcher chooses `Resume this project` or `Continue where I left off`:",
        ),
        (
            "If the researcher chooses `Map this folder first (recommended)` or `Refresh the research map`:",
            "If the researcher chooses `Map this folder first` or `Refresh the research map`:",
        ),
        (
            "Use \\`grd resume --recent\\` in your normal terminal to find the project first.",
            "Use \\`grd resume --recent\\` in your normal terminal first.",
            "Use \\`grd resume --recent\\` in your normal terminal to pick the project first.",
        ),
        (
            "The recent-project picker is advisory; choose the workspace there, then \\`grd:resume-work\\` reloads canonical state for that project.",
            "The recent-project picker is advisory",
        ),
        (
            "Then open that project folder in the runtime and run \\`grd:resume-work\\`.",
            "Then open the project folder in the runtime and run \\`grd:resume-work\\`.",
        ),
        (
            "In GRD terms, \\`resume-work\\` is the in-runtime continuation step once the recovery ladder has identified the right project.",
            "In GRD terms, \\`resume-work\\` is the in-runtime recovery step once the recovery ladder has identified the right project.",
            "In GRD terms, \\`resume-work\\` is the in-runtime command that continues a selected project.",
            "In GRD terms, \\`resume-work\\` is the in-runtime continuation step once the recovery ladder has identified the right project and reopened its workspace.",
        ),
        ("Do not silently create project files from `grd:start` itself.",),
        (
            "Do not silently switch the user into a different project folder.",
            "Do not silently switch to a different project folder.",
            "Do not silently switch projects.",
        ),
        (
            "When in doubt between a fresh folder and an existing research folder, prefer `map-research` as the safer recommendation.",
            "When in doubt between a fresh folder and an existing research folder, prefer `map-research`.",
        ),
        ("keep the official GRD terms visible in plain-English form",),
    ):
        assert any(fragment in workflow for fragment in fragment_options)

    assert "Read `{GRD_INSTALL_DIR}/workflows/new-project.md` with the file-read tool." not in workflow
    assert "Read `{GRD_INSTALL_DIR}/workflows/help.md` with the file-read tool." not in workflow
    assert "Read `{GRD_INSTALL_DIR}/workflows/tour.md` with the file-read tool." not in workflow
