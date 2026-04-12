"""Markdown-aware section handling for the paper pipeline.

Paper-writer agents authored in raw LaTeX historically. This module lets
them author in markdown instead and converts the content to a LaTeX
fragment before the template registry substitutes it. Content that still
looks like raw LaTeX is passed through unchanged, so existing
``PaperConfig`` payloads keep working.

The module is intentionally thin: pandoc does the real work (via
``grd.utils.pandoc``), this module just decides *when* to invoke it and
falls back gracefully when pandoc is missing.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from grd.utils.pandoc import (
    PandocExecutionError,
    PandocNotAvailable,
    PandocStatus,
    detect_pandoc,
    markdown_to_latex_fragment,
)

logger = logging.getLogger(__name__)

# Markers that say "this is already LaTeX, don't feed it to pandoc".
# Order matters: the first match wins. We look for structural LaTeX, not
# math blocks (math is valid inside markdown). We also treat explicitly
# fenced ```latex / ```tex blocks as an author-declared LaTeX signal.
_LATEX_SIGIL_PATTERN = re.compile(
    r"(?m)"
    r"^\s*\\documentclass\b"       # full document
    r"|^\s*\\begin\{(?:document|thebibliography|figure|table|abstract|itemize|enumerate|description|tabular|center|quote|quotation|verbatim|lstlisting)\*?\}"
    r"|^\s*\\(?:section|subsection|subsubsection|paragraph|subparagraph|chapter)\*?\s*\{"
    r"|^\s*\\(?:title|author|date|maketitle|tableofcontents|bibliography|bibliographystyle|addbibresource|printbibliography)\b"
    r"|^\s*```(?:latex|tex|plaintex)\b"
)


def looks_like_latex(content: str) -> bool:
    """Return True if *content* appears to already be raw LaTeX.

    The check is conservative -- we only treat content as LaTeX when it
    contains structural commands (``\\section{``, ``\\begin{document}``,
    ``\\documentclass``, etc.) that would not appear inside a markdown
    body. Inline math (``$x$``, ``$$...$$``) is valid in markdown and does
    not trigger the heuristic.
    """
    if not content:
        return False
    return _LATEX_SIGIL_PATTERN.search(content) is not None


def maybe_convert_to_latex(
    content: str,
    *,
    lua_filters: list[Path] | None = None,
    bibliography: Path | None = None,
    citeproc: bool = False,
    pandoc_status: PandocStatus | None = None,
) -> str:
    """Convert *content* to a LaTeX fragment if it looks like markdown.

    Behaviour matrix:

    ============================  ==============================
    content looks like LaTeX      returned unchanged
    pandoc unavailable            returned unchanged (logged)
    pandoc conversion raises      returned unchanged (logged)
    otherwise                     pandoc output
    ============================  ==============================

    The graceful degradation path lets this function replace direct
    ``content`` use everywhere without risking regressions when pandoc
    isn't installed on the compile host.
    """
    if not content:
        return content
    if looks_like_latex(content):
        return content

    status = pandoc_status if pandoc_status is not None else detect_pandoc()
    if not status.available or not status.meets_minimum:
        logger.debug(
            "pandoc unavailable (%s); leaving section content as-is",
            status.error or ("version below minimum" if status.available else "not found"),
        )
        return content

    try:
        return markdown_to_latex_fragment(
            content,
            lua_filters=lua_filters,
            bibliography=bibliography,
            citeproc=citeproc,
            status=status,
        )
    except (PandocNotAvailable, PandocExecutionError) as exc:
        logger.warning("pandoc conversion failed, using content as-is: %s", exc)
        return content


__all__ = ["looks_like_latex", "maybe_convert_to_latex"]
