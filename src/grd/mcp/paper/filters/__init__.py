"""GRD Lua filters for pandoc markdown-to-LaTeX conversion.

Each filter is independently usable via pandoc's ``--lua-filter`` flag and
can be chained in any order -- they don't share state across the pandoc run.
The filters are intentionally domain-agnostic where cheap; a rename of the
``grd-`` prefix is enough to port them to a sibling project.
"""

from __future__ import annotations

from importlib.resources import as_file, files
from pathlib import Path

FILTER_NAMES: tuple[str, ...] = (
    "grd-obsidian-compat",
    "grd-crossref",
    "grd-math",
    "grd-figure",
)


def filter_path(name: str) -> Path:
    """Return the on-disk path to a bundled Lua filter.

    Filter names are given without extension (e.g. ``"grd-crossref"``). The
    returned path is safe to pass to ``pandoc --lua-filter``.
    """
    if name not in FILTER_NAMES:
        raise ValueError(f"unknown filter {name!r}; known: {FILTER_NAMES}")
    resource = files("grd.mcp.paper.filters").joinpath(f"{name}.lua")
    with as_file(resource) as path:
        return Path(path)


def all_filter_paths() -> list[Path]:
    """Return paths to every bundled filter, in the recommended order.

    Recommended chain:
        grd-crossref -> grd-obsidian-compat -> grd-math -> grd-figure

    Crossref runs first so that ``[[namespace:id]]`` is converted to raw
    LaTeX ``\\ref{}`` before grd-obsidian-compat's wikilink handler can
    swallow it as a plain wikilink. The two filters share the ``[[...]]``
    surface syntax and the namespaced form belongs to crossref.
    """
    return [filter_path(n) for n in ("grd-crossref", "grd-obsidian-compat", "grd-math", "grd-figure")]


__all__ = ["FILTER_NAMES", "all_filter_paths", "filter_path"]
