"""Focused regressions for Phase 11 execution-state ownership cleanup."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
EXECUTE_PHASE = REPO_ROOT / "src/grd/specs/workflows/execute-phase.md"
AGENT_INFRASTRUCTURE = REPO_ROOT / "src/grd/specs/references/orchestration/agent-infrastructure.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_execute_phase_only_applies_child_return_state_once() -> None:
    text = _read(EXECUTE_PHASE)

    assert "grd --raw apply-return-updates" in text
    assert "The orchestrator applies them through `grd apply-return-updates`" in text
    assert "grd state advance immediately" not in text
    assert "grd state record-metric" not in text


def test_agent_infrastructure_points_spawned_child_returns_at_canonical_applicator() -> None:
    text = _read(AGENT_INFRASTRUCTURE)

    assert "grd apply-return-updates <summary-file>" in text
    assert "grd state advance" not in text

