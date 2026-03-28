"""Shared helpers for installed hook layout selection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

from grd.adapters.install_utils import CACHE_DIR_NAME, UPDATE_CACHE_FILENAME
from grd.core.constants import TODOS_DIR_NAME
from grd.hooks.install_metadata import (
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


def self_owned_update_cache_candidate(self_install: SelfOwnedInstallContext) -> SimpleNamespace:
    """Return an update-cache candidate that points at a self-owned install."""
    return SimpleNamespace(
        path=self_install.cache_file,
        runtime=self_install.runtime,
        scope=self_install.install_scope,
    )


def self_owned_todo_candidate(self_install: SelfOwnedInstallContext) -> SimpleNamespace:
    """Return a todo candidate that points at a self-owned install."""
    return SimpleNamespace(
        path=self_install.todo_dir,
        runtime=self_install.runtime,
        scope=self_install.install_scope,
    )
