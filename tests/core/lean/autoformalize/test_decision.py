"""Tests for ``grd.core.lean.autoformalize.decision`` — pure threshold logic."""

from __future__ import annotations

from grd.core.lean.autoformalize.config import AutoformalizeConfig
from grd.core.lean.autoformalize.decision import decide_faithfulness


def test_auto_accept_above_threshold() -> None:
    cfg = AutoformalizeConfig()  # 0.85 / 0.70 defaults
    d = decide_faithfulness(similarity=0.91, config=cfg)
    assert d.outcome == "auto_accept"
    assert d.requires_cluster_consensus is False
    assert "0.91" in d.reason


def test_escalate_below_threshold() -> None:
    cfg = AutoformalizeConfig()
    d = decide_faithfulness(similarity=0.5, config=cfg)
    assert d.outcome == "escalate"


def test_ambiguous_band_without_cluster_flags_needs_review() -> None:
    cfg = AutoformalizeConfig()
    d = decide_faithfulness(similarity=0.78, config=cfg, cluster_size=1)
    assert d.outcome == "cluster_consensus"
    assert d.requires_cluster_consensus is True


def test_ambiguous_band_with_cluster_upgrades_to_accept() -> None:
    cfg = AutoformalizeConfig()
    d = decide_faithfulness(similarity=0.78, config=cfg, cluster_size=3)
    assert d.outcome == "auto_accept"
    assert d.requires_cluster_consensus is True
    assert "cluster consensus" in d.reason


def test_thresholds_can_be_tightened_per_project() -> None:
    strict = AutoformalizeConfig(auto_accept_similarity=0.95, escalate_below_similarity=0.8)
    # 0.9 is above default auto-accept (0.85) but below strict's (0.95).
    d = decide_faithfulness(similarity=0.9, config=strict, cluster_size=1)
    assert d.outcome == "cluster_consensus"


def test_boundary_exactly_at_auto_accept_passes() -> None:
    cfg = AutoformalizeConfig()
    # Exactly 0.85 is accept (>=), per decision.py; pins against off-by-one drift.
    d = decide_faithfulness(similarity=0.85, config=cfg)
    assert d.outcome == "auto_accept"


def test_boundary_exactly_at_escalate_is_ambiguous() -> None:
    cfg = AutoformalizeConfig()
    # Exactly 0.70 is NOT below escalate threshold — it's in the ambiguous band.
    d = decide_faithfulness(similarity=0.70, config=cfg, cluster_size=1)
    assert d.outcome == "cluster_consensus"
