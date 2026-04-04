"""Tests for shared runtime-lookup helper behavior."""

from __future__ import annotations

from pathlib import Path

from gpd.hooks.runtime_lookup import resolve_runtime_lookup_dir
from tests.hooks.helpers import mark_complete_install as _mark_complete_install


def test_resolve_runtime_lookup_dir_prefers_same_runtime_nested_install_for_explicit_project_dir(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    workspace = project_root / "src" / "analysis"
    workspace.mkdir(parents=True)

    _mark_complete_install(workspace / ".codex", runtime="codex")

    resolved = resolve_runtime_lookup_dir(
        workspace_dir=str(workspace),
        project_root=str(project_root),
        explicit_project_dir=True,
        active_runtime="codex",
    )

    assert resolved == str(workspace)


def test_resolve_runtime_lookup_dir_does_not_let_unrelated_nested_install_hijack_explicit_project_dir(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    workspace = project_root / "src" / "analysis"
    workspace.mkdir(parents=True)

    _mark_complete_install(project_root / ".claude", runtime="claude-code")
    _mark_complete_install(workspace / ".codex", runtime="codex")

    resolved = resolve_runtime_lookup_dir(
        workspace_dir=str(workspace),
        project_root=str(project_root),
        explicit_project_dir=True,
        active_runtime="claude-code",
    )

    assert resolved == str(project_root)
