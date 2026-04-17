"""Regression tests for context/runtime abstraction boundaries."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

from grd.adapters.runtime_catalog import iter_runtime_descriptors


def test_context_import_does_not_require_adapter_instantiation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import grd.adapters as adapters

    def _boom():
        raise AssertionError("iter_adapters should not be needed for grd.core.context import")

    monkeypatch.setattr(adapters, "iter_adapters", _boom)
    sys.modules.pop("grd.core.context", None)

    context = importlib.import_module("grd.core.context")
    payload = context.init_new_project(tmp_path)

    expected_runtime_dirs = {descriptor.config_dir_name for descriptor in iter_runtime_descriptors()}
    assert expected_runtime_dirs <= context._runtime_config_dirs()
    assert expected_runtime_dirs <= context._ignore_dirs()
    assert payload["has_research_files"] is False
