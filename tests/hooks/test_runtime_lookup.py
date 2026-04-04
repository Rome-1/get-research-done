"""Tests for shared runtime-lookup helper behavior."""

from __future__ import annotations

from pathlib import Path

from gpd.hooks.payload_roots import PayloadRoots
from gpd.hooks.runtime_lookup import (
    resolve_runtime_lookup_active_runtime,
    resolve_runtime_lookup_context,
    resolve_runtime_lookup_context_from_payload_roots,
    resolve_runtime_lookup_dir,
)
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


def test_resolve_runtime_lookup_dir_ignores_untrusted_project_dir_hint(
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
        project_dir_trusted=False,
        active_runtime="claude-code",
    )

    assert resolved == str(workspace)


def test_resolve_runtime_lookup_active_runtime_prefers_project_runtime_for_explicit_project_dir() -> None:
    calls: list[str | None] = []

    def _runtime_resolver(cwd: str | None) -> str | None:
        calls.append(cwd)
        if cwd == "/tmp/project":
            return "codex"
        if cwd == "/tmp/project/src/analysis":
            return "claude-code"
        return None

    resolved = resolve_runtime_lookup_active_runtime(
        workspace_dir="/tmp/project/src/analysis",
        project_root="/tmp/project",
        explicit_project_dir=True,
        runtime_resolver=_runtime_resolver,
    )

    assert resolved == "codex"
    assert calls == ["/tmp/project"]


def test_resolve_runtime_lookup_context_falls_back_to_workspace_runtime_when_project_runtime_missing(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    workspace = project_root / "src" / "analysis"
    workspace.mkdir(parents=True)

    _mark_complete_install(workspace / ".codex", runtime="codex")

    calls: list[str | None] = []

    def _runtime_resolver(cwd: str | None) -> str | None:
        calls.append(cwd)
        if cwd == str(project_root):
            return None
        if cwd == str(workspace):
            return "codex"
        return None

    resolved = resolve_runtime_lookup_context(
        workspace_dir=str(workspace),
        project_root=str(project_root),
        explicit_project_dir=True,
        runtime_resolver=_runtime_resolver,
    )

    assert resolved.active_runtime == "codex"
    assert resolved.lookup_dir == str(workspace)
    assert calls == [str(project_root), str(workspace)]


def test_resolve_runtime_lookup_context_from_payload_roots_respects_trusted_project_dir_provenance() -> None:
    calls: list[str | None] = []

    def _runtime_resolver(cwd: str | None) -> str | None:
        calls.append(cwd)
        if cwd == "/tmp/project":
            return "codex"
        if cwd == "/tmp/project/src/analysis":
            return "claude-code"
        return None

    roots = PayloadRoots(
        workspace_dir="/tmp/project/src/analysis",
        project_root="/tmp/project",
        project_dir_present=True,
        project_dir_trusted=True,
    )

    resolved = resolve_runtime_lookup_context_from_payload_roots(
        roots,
        runtime_resolver=_runtime_resolver,
    )

    assert resolved.active_runtime == "codex"
    assert resolved.lookup_dir == "/tmp/project"
    assert calls == ["/tmp/project"]


def test_resolve_runtime_lookup_context_from_payload_roots_uses_workspace_when_project_dir_is_only_present() -> None:
    calls: list[str | None] = []

    def _runtime_resolver(cwd: str | None) -> str | None:
        calls.append(cwd)
        if cwd == "/tmp/project":
            return "codex"
        if cwd == "/tmp/project/src/analysis":
            return "claude-code"
        return None

    roots = PayloadRoots(
        workspace_dir="/tmp/project/src/analysis",
        project_root="/tmp/project",
        project_dir_present=True,
        project_dir_trusted=False,
    )

    resolved = resolve_runtime_lookup_context_from_payload_roots(
        roots,
        runtime_resolver=_runtime_resolver,
    )

    expected_workspace = str(Path("/tmp/project/src/analysis").resolve(strict=False))
    assert resolved.active_runtime == "claude-code"
    assert resolved.lookup_dir == expected_workspace
    assert calls == ["/tmp/project/src/analysis"]
