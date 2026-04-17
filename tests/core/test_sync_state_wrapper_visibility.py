"""Focused regression for the sync-state wrapper and schema visibility."""

from __future__ import annotations

from pathlib import Path

from grd.registry import get_command

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMAND = REPO_ROOT / "src" / "grd" / "commands" / "sync-state.md"


def test_sync_state_wrapper_stays_thin_while_schema_visibility_remains_in_the_expanded_surface() -> None:
    raw = COMMAND.read_text(encoding="utf-8")
    expanded = get_command("grd:sync-state").content

    assert raw.count("@{GRD_INSTALL_DIR}/workflows/sync-state.md") == 1
    assert "@{GRD_INSTALL_DIR}/templates/state-json-schema.md" not in raw
    assert "@GRD/STATE.md" not in raw
    assert "@GRD/state.json" not in raw
    assert "Read both state representations" not in raw
    assert "The workflow handles all logic including" not in raw

    assert "# state.json Schema" in expanded
    assert "Authoritative vs Derived" in expanded
    assert "`project_contract`" in expanded
    assert "`convention_lock`" in expanded
