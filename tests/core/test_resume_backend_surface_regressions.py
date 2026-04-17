"""Regression tests for model-visible resume backend naming."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_model_visible_resume_surfaces_use_public_raw_resume_command() -> None:
    model_visible_paths = (
        "src/grd/specs/templates/state-machine.md",
        "src/grd/specs/templates/continue-here.md",
        "src/grd/specs/templates/state-json-schema.md",
        "src/grd/specs/references/orchestration/state-portability.md",
    )

    for relative_path in model_visible_paths:
        text = _read(relative_path)
        assert "grd --raw resume" in text, relative_path
        assert "grd init resume" not in text, relative_path
