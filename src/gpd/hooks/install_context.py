"""Shared helpers for installed hook layout selection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from gpd.adapters.install_utils import CACHE_DIR_NAME, UPDATE_CACHE_FILENAME
from gpd.core.constants import TODOS_DIR_NAME
from gpd.core.root_resolution import resolve_project_root
from gpd.hooks.install_metadata import (
    config_dir_has_complete_install,
    install_scope_from_manifest,
    installed_runtime,
    installed_update_command,
)
from gpd.hooks.runtime_lookup import resolve_runtime_lookup_dir


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


@dataclass(frozen=True, slots=True)
class HookLookupContext:
    """Shared runtime-lookup inputs for hook surfaces."""

    lookup_cwd: Path | None
    resolved_home: Path
    active_runtime: str | None
    preferred_runtime: str | None


def _prefer_runtime_lookup_cwd(
    *,
    resolved_cwd: Path | None,
    runtime_hint: str | None = None,
) -> Path | None:
    """Choose the cwd used for runtime-owned hook lookups.

    Nested workspaces should honor a concrete local runtime install in the
    actual current directory. When there is no such install, project-root
    fallback preserves ancestor-local installs for existing GPD projects.
    """
    if resolved_cwd is None:
        return None

    project_root = resolve_project_root(resolved_cwd)
    lookup_dir = resolve_runtime_lookup_dir(
        workspace_dir=str(resolved_cwd),
        project_root=str(project_root or resolved_cwd),
        explicit_project_dir=project_root is not None and project_root != resolved_cwd,
        project_dir_trusted=True,
        active_runtime=runtime_hint,
    )
    return Path(lookup_dir).expanduser().resolve(strict=False)


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
    active_runtime: str | None = None,
    workspace_path: Path | None,
) -> bool:
    """Return whether self-owned hook layout should win over detected runtime layout."""
    if self_install is None:
        return False
    if active_install_target is None or self_install.config_dir == active_install_target.config_dir:
        return True
    if workspace_path is None or getattr(active_install_target, "install_scope", None) != "local":
        return True
    return False


def resolve_hook_lookup_context(
    *,
    cwd: str | Path | None,
    home: str | Path | None = None,
    active_installed_runtime: str | None = None,
    preferred_runtime: str | None = None,
) -> HookLookupContext:
    """Resolve the shared cwd/home/runtime preference context for hook lookups."""
    from gpd.hooks.runtime_detect import (
        ALL_RUNTIMES,
        RUNTIME_UNKNOWN,
        detect_active_runtime,
        detect_active_runtime_with_gpd_install,
        detect_local_runtime_with_gpd_install,
        detect_runtime_for_gpd_use,
        normalize_runtime_name,
    )

    def _normalize_runtime_hint(runtime: str | None) -> str | None:
        if runtime is None:
            return None
        normalized = normalize_runtime_name(runtime)
        if normalized in (None, RUNTIME_UNKNOWN):
            return None
        return normalized if normalized in ALL_RUNTIMES else None

    resolved_cwd = Path(cwd).expanduser().resolve(strict=False) if cwd is not None else None
    resolved_home = Path.home() if home is None else Path(home).expanduser().resolve(strict=False)
    raw_active_runtime_hint = (
        active_installed_runtime
        if active_installed_runtime is not None
        else detect_active_runtime(cwd=resolved_cwd, home=resolved_home)
    )
    active_runtime_hint = _normalize_runtime_hint(raw_active_runtime_hint)
    normalized_preferred_runtime = _normalize_runtime_hint(preferred_runtime)
    runtime_hint = active_runtime_hint or normalized_preferred_runtime
    lookup_cwd = _prefer_runtime_lookup_cwd(
        resolved_cwd=resolved_cwd,
        runtime_hint=runtime_hint,
    )
    raw_active_runtime = (
        raw_active_runtime_hint
        if active_installed_runtime is not None
        else detect_active_runtime_with_gpd_install(cwd=lookup_cwd, home=resolved_home)
    )
    active_runtime = _normalize_runtime_hint(raw_active_runtime)
    prioritized_runtime = (
        normalized_preferred_runtime
        if preferred_runtime is not None
        else _normalize_runtime_hint(detect_runtime_for_gpd_use(cwd=lookup_cwd, home=resolved_home))
    )
    if active_runtime is None:
        local_runtime = _normalize_runtime_hint(detect_local_runtime_with_gpd_install(cwd=lookup_cwd, home=resolved_home))
        if local_runtime is not None:
            active_runtime = local_runtime
    return HookLookupContext(
        lookup_cwd=lookup_cwd,
        resolved_home=resolved_home,
        active_runtime=active_runtime,
        preferred_runtime=prioritized_runtime,
    )


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
    from gpd.hooks.runtime_detect import (
        RUNTIME_UNKNOWN,
        detect_runtime_install_target,
        get_todo_candidates,
        should_consider_todo_candidate,
    )

    lookup = resolve_hook_lookup_context(
        cwd=cwd,
        home=home,
        active_installed_runtime=active_installed_runtime,
        preferred_runtime=preferred_runtime,
    )
    todo_candidates = get_todo_candidates(
        cwd=lookup.lookup_cwd,
        home=lookup.resolved_home,
        preferred_runtime=lookup.preferred_runtime,
    )
    self_install = detect_self_owned_install(hook_file)
    self_candidate_path: Path | None = None
    active_install_target = (
        detect_runtime_install_target(lookup.active_runtime, cwd=lookup.lookup_cwd, home=lookup.resolved_home)
        if lookup.active_runtime not in (None, "", RUNTIME_UNKNOWN)
        else None
    )
    if should_prefer_self_owned_install(
        self_install,
        active_install_target=active_install_target,
        active_runtime=lookup.active_runtime,
        workspace_path=lookup.lookup_cwd,
    ):
        if self_install is not None:
            self_candidate = self_owned_todo_candidate(self_install)
            todo_candidates = [candidate for candidate in todo_candidates if candidate.path != self_candidate.path]
            todo_candidates = [self_candidate, *todo_candidates]
            self_candidate_path = self_candidate.path

    return [
        candidate
        for candidate in todo_candidates
        if candidate.path == self_candidate_path
        or should_consider_todo_candidate(
            candidate,
            active_installed_runtime=lookup.active_runtime,
            cwd=lookup.lookup_cwd,
            home=lookup.resolved_home,
        )
    ]
