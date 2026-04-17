"""Prompt-level coverage for the required GRD/PSI acknowledgment."""

from __future__ import annotations

from pathlib import Path

REQUIRED_GPD_ACKNOWLEDGMENT = (
    "This research made use of Get Physics Done (GPD) and was supported in part by a "
    "GRD Research Grant from Physical Superintelligence PBC (PSI)."
)
REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_required_acknowledgment_is_wired_into_paper_prompts() -> None:
    for relative_path in (
        "src/grd/specs/templates/paper/paper-config-schema.md",
        "src/grd/specs/workflows/write-paper.md",
        "src/grd/agents/grd-paper-writer.md",
    ):
        assert REQUIRED_GPD_ACKNOWLEDGMENT in _read(relative_path), relative_path
