"""Shared runtime-lookup decisions for hook surfaces."""

from __future__ import annotations

from pathlib import Path

import gpd.hooks.install_context as hook_layout
from gpd.hooks.runtime_detect import ALL_RUNTIMES, SCOPE_LOCAL, detect_runtime_install_target


def resolve_runtime_lookup_dir(
    *,
    workspace_dir: str,
    project_root: str,
    explicit_project_dir: bool,
    active_runtime: str | None = None,
) -> str:
    """Return the cwd hook surfaces should use for runtime-owned lookups."""
    if explicit_project_dir:
        if isinstance(active_runtime, str) and active_runtime in ALL_RUNTIMES:
            resolved_workspace = Path(workspace_dir).expanduser().resolve(strict=False)
            install_target = detect_runtime_install_target(active_runtime, cwd=resolved_workspace)
            if install_target is not None and install_target.install_scope == SCOPE_LOCAL:
                return workspace_dir
        return project_root

    lookup = hook_layout.resolve_hook_lookup_context(cwd=workspace_dir)
    return str(lookup.lookup_cwd) if lookup.lookup_cwd is not None else workspace_dir
