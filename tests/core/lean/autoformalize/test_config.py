"""Tests for ``grd.core.lean.autoformalize.config``.

Covers default construction, threshold validation, and loading from
``.grd/lean-env.json`` — including the "section absent" and "partial section"
paths that callers rely on for forward compatibility.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from grd.core.constants import PLANNING_DIR_NAME
from grd.core.lean.autoformalize.config import (
    DEFAULT_AUTO_ACCEPT_SIMILARITY,
    DEFAULT_ESCALATE_BELOW_SIMILARITY,
    DEFAULT_MODEL_ID,
    DEFAULT_NUM_CANDIDATES,
    DEFAULT_REPAIR_BUDGET,
    AutoformalizeConfig,
    load_autoformalize_config,
)


def test_defaults_match_published_targets() -> None:
    cfg = AutoformalizeConfig()
    # These defaults are contract with AUTOFORMALIZATION.md §8.2 — don't drift
    # them without updating the doc.
    assert cfg.num_candidates == 4
    assert cfg.repair_budget == 15
    assert cfg.auto_accept_similarity == pytest.approx(0.85)
    assert cfg.escalate_below_similarity == pytest.approx(0.70)
    assert cfg.model_id == DEFAULT_MODEL_ID


def test_rejects_invalid_thresholds() -> None:
    with pytest.raises(ValueError, match="thresholds"):
        AutoformalizeConfig(auto_accept_similarity=0.5, escalate_below_similarity=0.8)
    with pytest.raises(ValueError, match="thresholds"):
        AutoformalizeConfig(auto_accept_similarity=1.5)


def test_rejects_invalid_candidate_count() -> None:
    with pytest.raises(ValueError, match="num_candidates"):
        AutoformalizeConfig(num_candidates=0)


def test_rejects_negative_repair_budget() -> None:
    with pytest.raises(ValueError, match="repair_budget"):
        AutoformalizeConfig(repair_budget=-1)


def test_load_returns_defaults_when_file_missing(tmp_path: Path) -> None:
    cfg = load_autoformalize_config(tmp_path)
    assert cfg.num_candidates == DEFAULT_NUM_CANDIDATES
    assert cfg.repair_budget == DEFAULT_REPAIR_BUDGET
    assert cfg.auto_accept_similarity == DEFAULT_AUTO_ACCEPT_SIMILARITY
    assert cfg.escalate_below_similarity == DEFAULT_ESCALATE_BELOW_SIMILARITY


def test_load_merges_partial_overrides(tmp_path: Path) -> None:
    grd_dir = tmp_path / PLANNING_DIR_NAME
    grd_dir.mkdir()
    (grd_dir / "lean-env.json").write_text(
        json.dumps(
            {
                "autoformalize": {
                    "num_candidates": 8,
                    "auto_accept_similarity": 0.9,
                    "mathlib_names_path": "custom/mathlib-names.txt",
                },
                "other_section": "unused",
            }
        )
    )
    cfg = load_autoformalize_config(tmp_path)
    assert cfg.num_candidates == 8
    assert cfg.auto_accept_similarity == pytest.approx(0.9)
    # escalate threshold falls back to default when not specified.
    assert cfg.escalate_below_similarity == DEFAULT_ESCALATE_BELOW_SIMILARITY
    assert cfg.mathlib_names_path == "custom/mathlib-names.txt"


def test_load_ignores_non_dict_section(tmp_path: Path) -> None:
    grd_dir = tmp_path / PLANNING_DIR_NAME
    grd_dir.mkdir()
    (grd_dir / "lean-env.json").write_text(json.dumps({"autoformalize": "garbage"}))
    cfg = load_autoformalize_config(tmp_path)
    assert cfg.num_candidates == DEFAULT_NUM_CANDIDATES
