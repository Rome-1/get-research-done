"""Focused regressions for the Phase 11 debug-wrapper typed child-return cleanup."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMAND_PATH = REPO_ROOT / "src/grd/commands/debug.md"


def test_debug_wrapper_routes_on_typed_child_return_contract() -> None:
    text = COMMAND_PATH.read_text(encoding="utf-8")

    assert "workflow-owned typed child-return contract" in text
    assert "grd_return.status: completed" in text
    assert "grd_return.status: checkpoint" in text
    assert "grd_return.status: blocked` or `failed" in text
    assert "frontmatter/body reconcile the expected debug session artifact" in text
    assert "artifact gate" in text
    assert "goal: find_root_cause_only" in text
    assert "Create: GRD/debug/{slug}.md" in text
    assert "Do not branch on heading text here." in text

    for marker in (
        "ROOT CAUSE FOUND",
        "CHECKPOINT REACHED",
        "INVESTIGATION INCONCLUSIVE",
        "goal: find_and_fix",
        "Physics debugging follows a hierarchy of checks",
    ):
        assert marker not in text


def test_debug_wrapper_checkpoint_continuation_stays_file_backed_and_fresh() -> None:
    text = COMMAND_PATH.read_text(encoding="utf-8")

    assert "spawn a fresh continuation run" in text
    assert "Spawn Fresh Continuation agent (After Checkpoint)" in text
    assert "Debug file path: GRD/debug/{slug}.md\nRead that file before continuing" in text
    assert "instead of relying on an inline `@...` attachment." in text
    assert "@GRD/debug/{slug}.md" not in text
    assert "goal: find_root_cause_only" in text
