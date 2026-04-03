"""Contract test for help inventory coverage."""

from __future__ import annotations

import re

from gpd import registry as content_registry


def _repo_root():
    from pathlib import Path

    return Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (_repo_root() / relative_path).read_text(encoding="utf-8")


def _help_command_inventory(*contents: str) -> set[str]:
    surfaces: set[str] = set()
    pattern = re.compile(r"(?m)(?<![A-Za-z0-9-])(?:/gpd:|gpd\s+)([a-z0-9-]+)\b")
    for content in contents:
        surfaces.update(pattern.findall(content))
    return surfaces


def test_help_inventory_covers_registry_command_inventory() -> None:
    content_registry.invalidate_cache()

    registry_commands = set(content_registry.list_commands())
    help_inventory = _help_command_inventory(
        _read("src/gpd/commands/help.md"),
        _read("src/gpd/specs/workflows/help.md"),
    )

    missing = sorted(registry_commands - help_inventory)
    assert missing == []


def test_help_inventory_avoids_slash_command_framing_in_shared_source() -> None:
    help_sources = [
        _read("src/gpd/commands/help.md"),
        _read("src/gpd/specs/workflows/help.md"),
    ]

    assert all("canonical in-runtime slash-command names in `/gpd:*` form" not in content for content in help_sources)
    assert all("/gpd:*" not in content for content in help_sources)
    assert any("slash-command names" in content for content in help_sources)
