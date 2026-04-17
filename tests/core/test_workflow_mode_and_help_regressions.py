import re
from pathlib import Path

WORKFLOWS_DIR = Path("src/grd/specs/workflows")

MODE_AWARE_WORKFLOWS = (
    "plan-phase.md",
    "research-phase.md",
    "map-research.md",
    "literature-review.md",
    "new-project.md",
    "new-milestone.md",
    "execute-phase.md",
)


def _read_workflow(name: str) -> str:
    return (WORKFLOWS_DIR / name).read_text(encoding="utf-8")


def _mode_aware_section(text: str) -> str:
    match = re.search(r"\*\*Mode-aware behavior:\*\*\n(?P<section>(?:- .+\n)+)", text)
    assert match is not None
    return match.group("section")


def test_owned_workflows_make_balanced_research_mode_explicit() -> None:
    for name in MODE_AWARE_WORKFLOWS:
        section = _mode_aware_section(_read_workflow(name))
        assert "research_mode=balanced" in section, name


def test_research_phase_splits_balanced_and_yolo_autonomy_rules() -> None:
    section = _mode_aware_section(_read_workflow("research-phase.md"))

    assert "autonomy=balanced/yolo" not in section
    assert "autonomy=balanced" in section
    assert "autonomy=yolo" in section


def test_help_dedupes_runtime_permission_readiness_trio() -> None:
    help_workflow = _read_workflow("help.md")

    assert help_workflow.count("grd permissions status --runtime <runtime> --autonomy balanced") == 1
    assert help_workflow.count("grd validate unattended-readiness --runtime <runtime> --autonomy balanced") == 1
    assert help_workflow.count("grd permissions sync --runtime <runtime> --autonomy balanced") == 1


def test_publication_workflows_read_mode_state_from_init_context() -> None:
    write_paper = _read_workflow("write-paper.md")
    respond = _read_workflow("respond-to-referees.md")

    assert 'INIT=$(grd --raw init phase-op --include config)' in write_paper
    assert 'AUTONOMY=$(echo "$INIT" | grd json get .autonomy --default balanced)' in write_paper
    assert 'RESEARCH_MODE=$(echo "$INIT" | grd json get .research_mode --default balanced)' in write_paper
    assert "grd --raw config get autonomy" not in write_paper
    assert "grd --raw config get research_mode" not in write_paper

    assert 'INIT=$(grd --raw init phase-op --include config)' in respond
    assert 'AUTONOMY=$(echo "$INIT" | grd json get .autonomy --default balanced)' in respond
    assert "grd --raw config get autonomy" not in respond
