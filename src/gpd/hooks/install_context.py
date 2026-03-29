"""Shared helpers for installed hook layout selection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gpd.adapters.install_utils import CACHE_DIR_NAME, UPDATE_CACHE_FILENAME
from gpd.core.constants import TODOS_DIR_NAME
from gpd.hooks.install_metadata import (
    config_dir_has_complete_install,
    install_scope_from_manifest,
    installed_runtime,
    installed_update_command,
)


@dataclass(frozen=True, slots=True)
class SelfOwnedInstallContext:
    """Metadata and layout paths for a hook that is running from its own install."""

    config_dir: Path
    runtime: str | None
    install_scope: str | None

    @property
    def cache_file(self) -> Path:
        return self.config_dir / CACHE_DIR_NAME / UPDATE_CACHE_FILENAME

    @property
    def todo_dir(self) -> Path:
        return self.config_dir / TODOS_DIR_NAME

    @property
    def update_command(self) -> str | None:
        return installed_update_command(self.config_dir)


def detect_self_owned_install(hook_file: str | Path) -> SelfOwnedInstallContext | None:
    """Return the installed config-dir context for a hook file when it is self-owned."""
    hook_path = Path(hook_file).resolve(strict=False)
    candidate = hook_path.parent.parent
    if not config_dir_has_complete_install(candidate):
        return None
    return SelfOwnedInstallContext(
        config_dir=candidate,
        runtime=installed_runtime(candidate),
        install_scope=install_scope_from_manifest(candidate),
    )


def should_prefer_self_owned_install(
    self_install: SelfOwnedInstallContext | None,
    *,
    active_install_target,
    workspace_path: Path | None,
) -> bool:
    """Return whether self-owned hook layout should win over detected runtime layout."""
    if self_install is None:
        return False
    if active_install_target is None or self_install.config_dir == active_install_target.config_dir:
        return True
    return not (workspace_path is not None and getattr(active_install_target, "install_scope", None) == "local")


def self_owned_update_cache_candidate(self_install: SelfOwnedInstallContext):
    """Return an update-cache candidate that points at a self-owned install."""
    from gpd.hooks.runtime_detect import UpdateCacheCandidate

    return UpdateCacheCandidate(
        path=self_install.cache_file,
        runtime=self_install.runtime,
        scope=self_install.install_scope,
    )


def self_owned_todo_candidate(self_install: SelfOwnedInstallContext):
    """Return a todo candidate that points at a self-owned install."""
    from gpd.hooks.runtime_detect import TodoCandidate

    return TodoCandidate(
        path=self_install.todo_dir,
        runtime=self_install.runtime,
        scope=self_install.install_scope,
    )


def ordered_todo_lookup_candidates(
    *,
    hook_file: str | Path,
    cwd: str | Path | None,
    home: str | Path | None = None,
    active_installed_runtime: str | None = None,
    preferred_runtime: str | None = None,
) -> list[object]:
    """Return todo candidates in the shared precedence order for current-task lookup."""
    from gpd.core.observability import resolve_project_root
    from gpd.hooks.runtime_detect import (
        RUNTIME_UNKNOWN,
        detect_active_runtime_with_gpd_install,
        detect_runtime_for_gpd_use,
        detect_runtime_install_target,
        get_todo_candidates,
        should_consider_todo_candidate,
    )

    workspace_path = resolve_project_root(cwd) if cwd else None
    resolved_home = Path.home() if home is None else Path(home)
    active_runtime = (
        active_installed_runtime
        if active_installed_runtime is not None
        else detect_active_runtime_with_gpd_install(cwd=workspace_path, home=resolved_home)
    )
    prioritized_runtime = (
        preferred_runtime
        if preferred_runtime is not None
        else detect_runtime_for_gpd_use(cwd=workspace_path, home=resolved_home)
    )
    todo_candidates = get_todo_candidates(
        cwd=workspace_path,
        home=resolved_home,
        preferred_runtime=prioritized_runtime,
    )
    self_install = detect_self_owned_install(hook_file)
    active_install_target = (
        detect_runtime_install_target(active_runtime, cwd=workspace_path, home=resolved_home)
        if active_runtime not in (None, "", RUNTIME_UNKNOWN)
        else None
    )
    if should_prefer_self_owned_install(
        self_install,
        active_install_target=active_install_target,
        workspace_path=workspace_path,
    ):
        if self_install is not None:
            self_candidate = self_owned_todo_candidate(self_install)
            if all(candidate.path != self_candidate.path for candidate in todo_candidates):
                todo_candidates = [self_candidate, *todo_candidates]

    return [
        candidate
        for candidate in todo_candidates
        if should_consider_todo_candidate(
            candidate,
            active_installed_runtime=active_runtime,
            cwd=workspace_path,
            home=resolved_home,
        )
    ]
