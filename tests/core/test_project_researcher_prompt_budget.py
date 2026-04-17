"""Prompt budget regressions for the `grd-project-researcher` agent surface."""

from __future__ import annotations

from pathlib import Path

from tests.prompt_metrics_support import expanded_prompt_text, measure_prompt_surface

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / "src" / "grd" / "agents"
SOURCE_ROOT = REPO_ROOT / "src" / "grd"
PATH_PREFIX = "/runtime/"


def test_grd_project_researcher_prompt_stays_within_expected_budget_and_keeps_one_shot_checkpoint_language() -> None:
    path = AGENTS_DIR / "grd-project-researcher.md"
    source = path.read_text(encoding="utf-8")
    metrics = measure_prompt_surface(path, src_root=SOURCE_ROOT, path_prefix=PATH_PREFIX)
    expanded = expanded_prompt_text(path, src_root=SOURCE_ROOT, path_prefix=PATH_PREFIX)

    assert metrics.raw_include_count == 2
    assert metrics.expanded_line_count < 2_250
    assert metrics.expanded_char_count < 115_000

    assert "This is a one-shot handoff." in source
    assert "return typed `grd_return.status: checkpoint` and stop" in source
    assert "The orchestrator presents the checkpoint and spawns a fresh continuation after the response." in source
    assert "Do not wait inside the same spawned run." in source
    assert "STOP immediately, write checkpoint with research completed so far, return with CHECKPOINT status" in source
    assert "Structured return provided to orchestrator" in source
    assert "single-session scope is predictable" in source

    for phrase in (
        "wait for user confirmation",
        "ask the user then continue",
        "pause here for approval",
        "wait inside the same run",
    ):
        assert phrase not in expanded
