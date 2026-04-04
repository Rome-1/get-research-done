"""Shared runtime-lookup decisions for hook surfaces."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from gpd.hooks.payload_roots import PayloadRoots
from gpd.hooks.runtime_detect import (
    ALL_RUNTIMES,
    RUNTIME_UNKNOWN,
    SCOPE_LOCAL,
    detect_runtime_install_target,
    normalize_runtime_name,
)


@dataclass(frozen=True)
class RuntimeLookupContext:
    """Resolved runtime-owned lookup inputs for one hook payload."""

    lookup_dir: str
    active_runtime: str | None


def _project_dir_is_trusted(explicit_project_dir: bool, project_dir_trusted: bool | None) -> bool:
    return project_dir_trusted if project_dir_trusted is not None else explicit_project_dir


def _normalized_runtime_hint(runtime: str | None) -> str | None:
    if runtime is None:
        return None
    normalized = normalize_runtime_name(runtime) or runtime.strip() or None
    if normalized in (None, RUNTIME_UNKNOWN):
        return None
    return normalized if normalized in ALL_RUNTIMES else None


def resolve_runtime_lookup_active_runtime(
    *,
    workspace_dir: str,
    project_root: str,
    explicit_project_dir: bool,
    project_dir_trusted: bool | None = None,
    runtime_resolver: Callable[[str | None], str | None],
) -> str | None:
    """Resolve the active runtime without letting nested installs hijack explicit project roots."""
    if _project_dir_is_trusted(explicit_project_dir, project_dir_trusted):
        project_runtime = _normalized_runtime_hint(runtime_resolver(project_root))
        if project_runtime or workspace_dir == project_root:
            return project_runtime
        return _normalized_runtime_hint(runtime_resolver(workspace_dir))

    return _normalized_runtime_hint(runtime_resolver(workspace_dir))


def resolve_runtime_lookup_dir(
    *,
    workspace_dir: str,
    project_root: str,
    explicit_project_dir: bool,
    project_dir_trusted: bool | None = None,
    active_runtime: str | None = None,
) -> str:
    """Return the cwd hook surfaces should use for runtime-owned lookups."""
    normalized_runtime = _normalized_runtime_hint(active_runtime)
    if _project_dir_is_trusted(explicit_project_dir, project_dir_trusted):
        resolved_workspace = Path(workspace_dir).expanduser().resolve(strict=False)
        resolved_project = Path(project_root).expanduser().resolve(strict=False)
        if normalized_runtime is None:
            for runtime in ALL_RUNTIMES:
                install_target = detect_runtime_install_target(runtime, cwd=resolved_workspace)
                if install_target is not None and install_target.install_scope == SCOPE_LOCAL:
                    return str(resolved_workspace)
            return project_root
        if normalized_runtime is not None:
            install_target = detect_runtime_install_target(normalized_runtime, cwd=resolved_workspace)
            if install_target is not None and install_target.install_scope == SCOPE_LOCAL:
                return workspace_dir
            project_target = detect_runtime_install_target(normalized_runtime, cwd=resolved_project)
            if project_target is not None and project_target.install_scope == SCOPE_LOCAL:
                return project_root
            for runtime in ALL_RUNTIMES:
                if runtime == normalized_runtime:
                    continue
                install_target = detect_runtime_install_target(runtime, cwd=resolved_workspace)
                if install_target is not None and install_target.install_scope == SCOPE_LOCAL:
                    return str(resolved_workspace)
        return project_root

    return str(Path(workspace_dir).expanduser().resolve(strict=False))


def resolve_runtime_lookup_context(
    *,
    workspace_dir: str,
    project_root: str,
    explicit_project_dir: bool,
    project_dir_trusted: bool | None = None,
    runtime_resolver: Callable[[str | None], str | None],
) -> RuntimeLookupContext:
    """Resolve both the runtime attribution and the lookup directory for one hook payload."""
    active_runtime = resolve_runtime_lookup_active_runtime(
        workspace_dir=workspace_dir,
        project_root=project_root,
        explicit_project_dir=explicit_project_dir,
        project_dir_trusted=project_dir_trusted,
        runtime_resolver=runtime_resolver,
    )
    return RuntimeLookupContext(
        lookup_dir=resolve_runtime_lookup_dir(
            workspace_dir=workspace_dir,
            project_root=project_root,
            explicit_project_dir=explicit_project_dir,
            project_dir_trusted=project_dir_trusted,
            active_runtime=active_runtime,
        ),
        active_runtime=active_runtime,
    )


def resolve_runtime_lookup_context_from_payload_roots(
    roots: PayloadRoots,
    *,
    runtime_resolver: Callable[[str | None], str | None],
) -> RuntimeLookupContext:
    """Resolve runtime lookup decisions from payload-root provenance."""
    return resolve_runtime_lookup_context(
        workspace_dir=roots.workspace_dir,
        project_root=roots.project_root,
        explicit_project_dir=roots.project_dir_present,
        project_dir_trusted=roots.project_dir_trusted,
        runtime_resolver=runtime_resolver,
    )
