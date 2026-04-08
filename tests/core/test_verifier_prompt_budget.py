"""Prompt budget regressions for the `gpd-verifier` agent surface."""

from __future__ import annotations

from pathlib import Path

from tests.prompt_metrics_support import measure_prompt_surface

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / "src" / "gpd" / "agents"
SOURCE_ROOT = REPO_ROOT / "src" / "gpd"
PATH_PREFIX = "/runtime/"


def test_gpd_verifier_prompt_surface_stays_within_expected_budget() -> None:
    metrics = measure_prompt_surface(
        AGENTS_DIR / "gpd-verifier.md",
        src_root=SOURCE_ROOT,
        path_prefix=PATH_PREFIX,
    )

    assert metrics.raw_include_count <= 7
    assert metrics.expanded_line_count <= 9000
    assert metrics.expanded_char_count <= 540000
