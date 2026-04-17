from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMAND = REPO_ROOT / "src/grd/commands/discover.md"
WORKFLOW = REPO_ROOT / "src/grd/specs/workflows/discover.md"
RESEARCH_TEMPLATE = REPO_ROOT / "src/grd/specs/templates/research.md"


def test_discover_quick_depth_is_verification_only() -> None:
    command_text = COMMAND.read_text(encoding="utf-8")
    workflow_text = WORKFLOW.read_text(encoding="utf-8")

    assert "`--depth quick` (`depth: quick`) is verification-only and returns without writing `RESEARCH.md`." in command_text
    assert "Level 1 (`--depth quick`) is verification-only and does not write a file." in workflow_text
    assert "- `--depth quick` or `depth=quick` -> Level 1 (Quick Verification)" in workflow_text
    assert "No RESEARCH.md needed." in workflow_text
    assert "depth=verify" not in workflow_text


def test_discover_standard_and_deep_depths_write_research_without_separate_commit() -> None:
    command_text = COMMAND.read_text(encoding="utf-8")
    workflow_text = WORKFLOW.read_text(encoding="utf-8")

    assert "Produces RESEARCH.md for `--depth medium` or `--depth deep`" in command_text
    assert "Do not commit `RESEARCH.md` separately." in command_text
    assert (
        "Produces a Level 2-3 discovery artifact that informs planning: phase-scoped `RESEARCH.md` or standalone "
        "`GRD/analysis/discovery-{slug}.md`."
        in workflow_text
    )
    assert "See {GRD_INSTALL_DIR}/templates/research.md for the RESEARCH.md template structure used by Levels 2-3." in workflow_text
    assert "Write to `GRD/analysis/discovery-{slug}.md`" in workflow_text
    assert (
        "NOTE: No discovery artifact is committed separately. Phase-scoped `RESEARCH.md` is committed with phase completion."
        in workflow_text
    )


def test_discover_follow_up_and_research_template_match_quick_no_file_behavior() -> None:
    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    template_text = RESEARCH_TEMPLATE.read_text(encoding="utf-8")

    assert "Discovery complete: ${phase_dir}/RESEARCH.md" not in workflow_text
    assert "- Level 1 quick verify: no file written" in workflow_text
    assert "- Phase-scoped Level 2-3: ${phase_dir}/RESEARCH.md" in workflow_text
    assert "- Standalone Level 2-3: GRD/analysis/discovery-{slug}.md" in workflow_text
    assert "After creating the Level 2-3 discovery artifact, check confidence level." in workflow_text
    assert "If the Level 2-3 discovery artifact has open_questions:" in workflow_text
    assert "discover workflow's `depth: quick` RESEARCH.md output" not in template_text
    assert (
        "use `grd:discover`: `--depth quick` verifies without writing a file, while `--depth medium` or `--depth deep` writes the discovery artifact."
        in template_text
    )
    assert (
        "Template for phase-scoped `GRD/phases/XX-name/{phase}-RESEARCH.md` and standalone discovery artifacts such as "
        "`GRD/analysis/discovery-{slug}.md`."
        in template_text
    )
    assert "# [Phase [X]: ] [Name or Topic] - Research" in template_text
    assert (
        "- For quick landscape scans, use `grd:discover --depth quick` for verification-only checks, or `grd:discover --depth medium` when you need a lightweight written artifact"
        in template_text
    )
