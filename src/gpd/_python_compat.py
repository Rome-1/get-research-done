"""Python-runtime compatibility helpers for import-time surfaces."""

from __future__ import annotations

import importlib
import sys
from types import ModuleType

MIN_SUPPORTED_PYTHON = (3, 11)


def unsupported_python_message(*, version_info: tuple[int, ...] | None = None) -> str:
    """Return the canonical error for unsupported Python interpreters."""

    version = version_info if version_info is not None else sys.version_info
    major = int(version[0]) if len(version) > 0 else 0
    minor = int(version[1]) if len(version) > 1 else 0
    required = ".".join(str(part) for part in MIN_SUPPORTED_PYTHON)
    return (
        "get-physics-done requires Python "
        f"{required}+; current interpreter is Python {major}.{minor}. "
        "Use `uv run ...` or a Python 3.11+ environment."
    )


def require_supported_python(*, version_info: tuple[int, ...] | None = None) -> None:
    """Raise a stable error when the active interpreter is too old."""

    version = version_info if version_info is not None else sys.version_info
    if tuple(version[:2]) < MIN_SUPPORTED_PYTHON:
        raise RuntimeError(unsupported_python_message(version_info=tuple(version)))


def load_tomllib() -> ModuleType:
    """Import ``tomllib`` or raise a user-facing runtime-compatibility error."""

    require_supported_python()
    try:
        return importlib.import_module("tomllib")
    except ModuleNotFoundError as exc:  # pragma: no cover - guarded above on supported interpreters
        version = f"{sys.version_info.major}.{sys.version_info.minor}"
        raise RuntimeError(
            "get-physics-done expected the Python 3.11+ standard-library `tomllib` module, "
            f"but it was unavailable under Python {version}. "
            "Use `uv run ...` or repair the interpreter."
        ) from exc
