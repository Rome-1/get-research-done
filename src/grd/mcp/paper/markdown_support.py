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
    PandocNotAvailable,
    PandocStatus,
    detect_pandoc,
    markdown_to_latex_fragment,
)

logger = logging.getLogger(__name__)

# Markers that say "this is already LaTeX, don't feed it to pandoc".
# Order matters: the first match wins. We look for structural LaTeX, not
# inline math (math is valid inside markdown). Display-math environments
# (equation/align/...) *do* count -- those are LaTeX-specific. We also
# treat explicitly fenced ```latex / ```tex blocks as an author-declared
# LaTeX signal.
_LATEX_SIGIL_PATTERN = re.compile(
    r"(?m)"
    r"^\s*\\documentclass\b"  # full document
    r"|^\s*\\begin\{(?:document|thebibliography|figure|table|abstract|itemize|enumerate|description|tabular|center|quote|quotation|verbatim|lstlisting|equation|align|gather|multline|eqnarray|displaymath|split|alignat|flalign)\*?\}"
    r"|^\s*\\(?:section|subsection|subsubsection|paragraph|subparagraph|chapter|part)\*?\s*\{"
    r"|^\s*\\(?:documentclass|title|author|date|maketitle|tableofcontents|bibliography|bibliographystyle|addbibresource|printbibliography|usepackage|input|include|appendix|frontmatter|mainmatter|backmatter)\b"
    r"|^\s*```(?:latex|tex|plaintex)\b"
)

# Strips ``` fenced code blocks (any language tag, including none) before
# scanning for LaTeX sigils. Without this, a markdown section that *shows*
# a LaTeX example inside a triple-backtick fence would be misread as
# already-LaTeX and bypass pandoc.
_FENCED_CODE_BLOCK_PATTERN = re.compile(r"(?ms)^\s*```[^\n]*\n.*?^\s*```\s*$")


def looks_like_latex(content: str) -> bool:
    """Return True if *content* appears to already be raw LaTeX.

    The check is conservative -- we only treat content as LaTeX when it
    contains structural commands (``\\section{``, ``\\begin{document}``,
    ``\\documentclass``, ``\\begin{equation}``, etc.) that would not
    appear inside a markdown body. Inline math (``$x$``, ``$$...$$``) is
    valid in markdown and does not trigger the heuristic.

    Fenced code blocks are stripped before the scan so a markdown body
    that *quotes* a LaTeX example inside ``` fences is not misread as
    raw LaTeX. An explicit ``` ```latex / ```tex `` fence still counts
    as an author-declared LaTeX signal because that pattern is matched
    before stripping.
    """
    if not content:
        return False
    # Author-declared latex/tex fences win regardless of surrounding fences.
    if re.search(r"(?m)^\s*```(?:latex|tex|plaintex)\b", content):
        return True
    stripped = _FENCED_CODE_BLOCK_PATTERN.sub("", content)
    return _LATEX_SIGIL_PATTERN.search(stripped) is not None


def maybe_convert_to_latex(
    content: str,
    *,
    lua_filters: list[Path] | None = None,
    bibliography: Path | None = None,
    citeproc: bool = False,
    natbib: bool = True,
    external_filters: list[str] | None = None,
    pandoc_status: PandocStatus | None = None,
) -> str:
    """Convert *content* to a LaTeX fragment if it looks like markdown.

    Behaviour matrix:

    ============================  ==============================
    content looks like LaTeX      returned unchanged
    pandoc unavailable            returned unchanged (logged)
    pandoc conversion raises      PandocExecutionError re-raised
    otherwise                     pandoc output
    ============================  ==============================

    Pandoc-unavailable is the only soft-fail path: a missing pandoc
    binary on a compile host is an environment quirk we degrade past.
    A conversion *failure* (pandoc ran but errored) is a real bug --
    silently returning the markdown source there used to compile a
    .tex file full of unprocessed ``# headings`` and produce garbage
    output. Surface the error instead so callers can react.

    ``natbib`` defaults to True: the paper pipeline emits natbib
    commands (``\\citet{key}`` for textual ``@key`` and ``\\citep{k1, k2}``
    for ``[@k1; @k2]`` groups) so the template's ``\\bibliography{...}``
    can resolve them via bibtex. Literal ``@token`` in prose will be
    misread as a cite key in this mode -- pass ``natbib=False`` or
    escape as ``\\@`` if the content has email addresses or social
    handles. ``citeproc=True`` takes precedence and disables natbib.

    External filters (currently only ``pandoc-crossref``) are
    auto-detected via ``status.installed_filters`` and prepended to the
    filter chain. Pass ``external_filters=[]`` to opt out. Legacy
    ``pandoc-citeproc`` is deliberately excluded from auto-detection to
    prevent double-processing alongside ``--natbib``; callers that
    genuinely need it must request it explicitly.

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
            natbib=natbib,
            external_filters=external_filters,
            status=status,
        )
    except PandocNotAvailable as exc:
        logger.warning("pandoc unavailable mid-conversion, using content as-is: %s", exc)
        return content


__all__ = ["looks_like_latex", "maybe_convert_to_latex"]
