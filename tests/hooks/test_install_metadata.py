"""Focused tests for managed install-surface detection."""

from __future__ import annotations

from pathlib import Path

import pytest

from grd.adapters.runtime_catalog import ManagedInstallSurfacePolicy
from grd.hooks.install_metadata import inspect_managed_install_surface


def test_inspect_managed_install_surface_uses_runtime_catalog_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_dir = tmp_path / ".custom-runtime"
    (config_dir / "managed-root" / "VERSION").parent.mkdir(parents=True, exist_ok=True)
    (config_dir / "managed-root" / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (config_dir / "managed-commands" / "grd" / "update.md").parent.mkdir(parents=True, exist_ok=True)
    (config_dir / "managed-commands" / "grd" / "update.md").write_text("body\n", encoding="utf-8")
    (config_dir / "managed-flat" / "grd-update.md").parent.mkdir(parents=True, exist_ok=True)
    (config_dir / "managed-flat" / "grd-update.md").write_text("body\n", encoding="utf-8")
    (config_dir / "managed-agents" / "grd-check-proof.toml").parent.mkdir(parents=True, exist_ok=True)
    (config_dir / "managed-agents" / "grd-check-proof.toml").write_text("prompt = 'ok'\n", encoding="utf-8")

    monkeypatch.setattr(
        "grd.hooks.install_metadata.get_managed_install_surface_policy",
        lambda runtime=None: ManagedInstallSurfacePolicy(
            grd_content_globs=("managed-root/**/*",),
            nested_command_globs=("managed-commands/grd/**/*",),
            flat_command_globs=("managed-flat/grd-*.md",),
            managed_agent_globs=("managed-agents/grd-*.toml",),
        ),
    )

    surface = inspect_managed_install_surface(config_dir)

    assert surface.has_grd_content is True
    assert surface.has_nested_commands is True
    assert surface.has_flat_commands is True
    assert surface.has_managed_agents is True


def test_inspect_managed_install_surface_does_not_fall_back_to_legacy_literal_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / ".custom-runtime"
    (config_dir / "get-physics-done" / "VERSION").parent.mkdir(parents=True, exist_ok=True)
    (config_dir / "get-physics-done" / "VERSION").write_text("1.0.0\n", encoding="utf-8")
    (config_dir / "commands" / "grd" / "update.md").parent.mkdir(parents=True, exist_ok=True)
    (config_dir / "commands" / "grd" / "update.md").write_text("body\n", encoding="utf-8")
    (config_dir / "command" / "grd-update.md").parent.mkdir(parents=True, exist_ok=True)
    (config_dir / "command" / "grd-update.md").write_text("body\n", encoding="utf-8")
    (config_dir / "agents" / "grd-check-proof.md").parent.mkdir(parents=True, exist_ok=True)
    (config_dir / "agents" / "grd-check-proof.md").write_text("body\n", encoding="utf-8")

    monkeypatch.setattr(
        "grd.hooks.install_metadata.get_managed_install_surface_policy",
        lambda runtime=None: ManagedInstallSurfacePolicy(),
    )

    surface = inspect_managed_install_surface(config_dir)

    assert surface.has_grd_content is False
    assert surface.has_nested_commands is False
    assert surface.has_flat_commands is False
    assert surface.has_managed_agents is False
