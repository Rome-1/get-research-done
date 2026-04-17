from __future__ import annotations

from pathlib import Path

from grd.adapters.install_utils import expand_at_includes
from grd.registry import get_command, list_commands
from tests.doc_surface_contracts import assert_tour_command_surface_contract

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = REPO_ROOT / "src" / "grd" / "commands"
WORKFLOWS_DIR = REPO_ROOT / "src" / "grd" / "specs" / "workflows"
SOURCE_ROOT = REPO_ROOT / "src" / "grd"
PATH_PREFIX = "/runtime/"


def test_tour_command_is_registered_and_projectless() -> None:
    assert "tour" in list_commands()
    command = get_command("grd:tour")
    assert command.name == "grd:tour"
    assert command.context_mode == "projectless"
    assert command.allowed_tools == ["file_read"]


def test_tour_command_references_workflow() -> None:
    raw_command_prompt = (COMMANDS_DIR / "tour.md").read_text(encoding="utf-8")
    command_prompt = expand_at_includes(raw_command_prompt, SOURCE_ROOT, PATH_PREFIX)

    assert "@{GRD_INSTALL_DIR}/workflows/tour.md" in raw_command_prompt
    assert "@{GRD_INSTALL_DIR}/references/onboarding/beginner-command-taxonomy.md" in raw_command_prompt
    assert "grd:set-tier-models" in command_prompt
    assert "grd:settings" in command_prompt


def test_tour_workflow_introduces_a_safe_beginner_walkthrough() -> None:
    workflow = (WORKFLOWS_DIR / "tour.md").read_text(encoding="utf-8")
    assert_tour_command_surface_contract(workflow)
    table_entries = workflow[
        workflow.index("Include these entries:") : workflow.index("Keep this table runtime-facing only.")
    ]
    assert "- `grd resume`" not in table_entries
    assert "Keep this table runtime-facing only." in workflow

    for fragment in (
        "A common first pass is help -> start -> tour, then the path that fits the folder.",
        "Use a compact table with four columns:",
        "Use this when",
        "Do not use this when",
        "Example",
        "grd:plan-phase",
        "grd:execute-phase",
        "grd:verify-work",
        "grd:peer-review",
        "grd:respond-to-referees",
        "grd:arxiv-submission",
        "grd:branch-hypothesis",
        "grd:set-profile",
        "grd:set-tier-models",
        "Use `start` when you are still deciding, not `new-project`",
        "Use `resume-work` only when the project already has GRD state",
        "Use `set-tier-models` when you want to pin concrete runtime model ids only",
        "Use `help` when you want the command reference, not a setup wizard",
        "A few terms in plain English",
        "`GRD project` - a folder where GRD already saved its own project files and state",
        "`research map` - GRD's summary of an existing research folder before full project setup",
        "`phase` - one chunk of the project plan that GRD will organize later",
        "If you are still unsure, run grd:start.",
        "If you want to pin concrete tier-1, tier-2, and tier-3 model ids, run \\`grd:set-tier-models\\`.",
        "If you want to change permissions, autonomy, or runtime preferences after your first successful start or later, run \\`grd:settings\\`.",
    ):
        assert fragment in workflow
