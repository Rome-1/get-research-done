"""Shared test helpers for seeding adapter-owned runtime installs."""

from __future__ import annotations

import inspect
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from grd.adapters import get_adapter

_GRD_ROOT = Path(__file__).resolve().parents[1] / "src" / "grd"


@contextmanager
def _temporary_environment(updates: dict[str, str]) -> Iterator[None]:
    previous: dict[str, str | None] = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            os.environ[key] = value
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def _install_kwargs(
    adapter: object,
    *,
    config_dir: Path,
    install_scope: str,
    home: Path | None,
    explicit_target: bool,
) -> dict[str, object]:
    """Return adapter.install kwargs without assuming every runtime exposes the same knobs."""

    install_kwargs: dict[str, object] = {
        "is_global": install_scope == "global",
        "explicit_target": explicit_target,
    }
    if install_scope != "global":
        return install_kwargs

    resolved_home = home or config_dir.parent
    install_signature = inspect.signature(adapter.install)
    if "skills_dir" in install_signature.parameters:
        install_kwargs["skills_dir"] = resolved_home / ".agents" / "skills"
    return install_kwargs


def seed_complete_runtime_install(
    config_dir: Path,
    *,
    runtime: str,
    install_scope: str = "local",
    home: Path | None = None,
    explicit_target: bool | None = None,
) -> None:
    """Materialize a real adapter-owned install surface for test runtime detection."""

    adapter = get_adapter(runtime)
    config_dir.mkdir(parents=True, exist_ok=True)
    resolved_explicit_target = explicit_target if explicit_target is not None else config_dir.name != adapter.config_dir_name
    env_updates: dict[str, str] = {}
    if install_scope == "global":
        env_updates["HOME"] = str(home or config_dir.parent)

    with _temporary_environment(env_updates):
        install_result = adapter.install(
            _GRD_ROOT,
            config_dir,
            **_install_kwargs(
                adapter,
                config_dir=config_dir,
                install_scope=install_scope,
                home=home,
                explicit_target=resolved_explicit_target,
            ),
        )
        adapter.finalize_install(install_result)
