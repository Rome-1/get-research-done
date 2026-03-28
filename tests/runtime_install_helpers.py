"""Shared test helpers for seeding adapter-owned runtime installs."""

from __future__ import annotations

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


def seed_complete_runtime_install(
    config_dir: Path,
    *,
    runtime: str,
    install_scope: str = "local",
    home: Path | None = None,
) -> None:
    """Materialize a real adapter-owned install surface for test runtime detection."""

    adapter = get_adapter(runtime)
    config_dir.mkdir(parents=True, exist_ok=True)
    explicit_target = config_dir.name != adapter.config_dir_name
    env_updates: dict[str, str] = {}
    if install_scope == "global":
        env_updates["HOME"] = str(home or config_dir.parent)

    with _temporary_environment(env_updates):
        install_result = adapter.install(
            _GRD_ROOT,
            config_dir,
            is_global=install_scope == "global",
            explicit_target=explicit_target,
        )
        adapter.finalize_install(install_result)
