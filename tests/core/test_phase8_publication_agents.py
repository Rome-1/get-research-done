from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / "src" / "grd" / "agents"


def _read_agent(name: str) -> str:
    return (AGENTS_DIR / name).read_text(encoding="utf-8")


def test_paper_writer_balanced_mode_avoids_in_run_approval_language() -> None:
    source = _read_agent("grd-paper-writer.md")

    assert "proceed unless objected" not in source
    assert "Draft the outline, self-review it, and pause only if the narrative or claims need user judgment" in source
    assert "Balanced mode follows the publication-pipeline matrix" in source
    assert "Checkpoint ownership is orchestrator-side" in source
    assert "fresh continuation handoff" in source


def test_bibliographer_balanced_mode_adds_verified_citations_without_approval_loop() -> None:
    source = _read_agent("grd-bibliographer.md")

    assert "Present a batch for approval" not in source
    assert "Add verified citations automatically; pause only for uncertain matches, borderline relevance, or citation-scope changes." in source
    assert "| Citation addition |" in source
    assert "Checkpoint ownership is orchestrator-side" in source
    assert "fresh continuation handoff" in source


def test_referee_checkpoint_ownership_and_mode_routing_are_explicit() -> None:
    source = _read_agent("grd-referee.md")

    assert "Checkpoint ownership is orchestrator-side" in source
    assert "fresh continuation handoff" in source
    assert "publication-pipeline-modes.md" in source
