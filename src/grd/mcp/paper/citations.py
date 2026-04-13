"""Markdown citation audit for the paper pipeline.

When paper-writer agents author sections in markdown, they write pandoc
``@key`` citations rather than raw ``\\cite{key}`` LaTeX. Pandoc turns
``@key`` into ``\\cite{key}`` during conversion; pdflatex + bibtex/biber
resolves those against the bibliography declared by the journal template.

This module reuses nothing from pandoc itself at runtime; it just gives
callers an inexpensive way to validate that every ``@key`` a markdown
section refers to is actually defined in the project's ``.bib`` file
*before* the LaTeX compile stage, where missing keys surface as opaque
``?? `` placeholders.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_CITATION_RE = re.compile(
    r"(?<![\w@/])"       # not preceded by word char, another @, or a slash (avoids @@ and URLs)
    r"@"
    r"(?:\{(?P<braced>[^}]+)\}"                   # @{key with spaces or punctuation}
    r"|(?P<bare>"                                 # bare key: pandoc-style
    r"[A-Za-z]"                                   #   must start with letter
    r"(?:[\w:+#$%&/?<>~-]*[A-Za-z0-9])?"          #   mid chars, must end on alnum
    r"(?:\.[A-Za-z0-9][\w:+#$%&/?<>~-]*[A-Za-z0-9]*)*"  #   dots allowed only mid-key
    r"))"
)

_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"(?<!`)`[^`\n]+`")


def _strip_code_regions(text: str) -> str:
    """Blank out fenced and inline code so @keys inside them aren't cited."""
    without_fences = _FENCE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return _INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), without_fences)


def extract_markdown_citations(text: str) -> list[str]:
    """Return every ``@key`` pandoc-style citation in *text*, in order.

    Keys inside fenced or inline code blocks are ignored. Duplicate keys
    are preserved so callers can reason about citation frequency.
    """
    if not text:
        return []
    cleaned = _strip_code_regions(text)
    keys: list[str] = []
    for match in _CITATION_RE.finditer(cleaned):
        keys.append(match.group("braced") or match.group("bare"))
    return keys


class CitationAuditRecord(BaseModel):
    """Audit entry for one unique citation key referenced from markdown."""

    key: str
    count: int
    defined: bool


class MarkdownCitationAudit(BaseModel):
    """Summary of markdown ``@key`` citations versus the known .bib keys."""

    version: Literal[1] = 1
    total_citations: int
    unique_keys: int
    unresolved_keys: list[str] = Field(default_factory=list)
    entries: list[CitationAuditRecord] = Field(default_factory=list)


def audit_markdown_citations(
    text: str,
    bib_keys: Iterable[str],
) -> MarkdownCitationAudit:
    """Audit markdown citations against a set of defined bibliography keys.

    The audit is advisory: it records which keys appear, how often, and
    whether each is defined in the .bib file. Callers decide whether an
    unresolved key is a hard error or a warning.
    """
    defined = set(bib_keys)
    citations = extract_markdown_citations(text)
    counts: dict[str, int] = {}
    for key in citations:
        counts[key] = counts.get(key, 0) + 1

    entries = [
        CitationAuditRecord(key=key, count=count, defined=key in defined)
        for key, count in sorted(counts.items())
    ]
    unresolved = sorted(key for key, count in counts.items() if key not in defined)

    return MarkdownCitationAudit(
        total_citations=sum(counts.values()),
        unique_keys=len(counts),
        unresolved_keys=unresolved,
        entries=entries,
    )


def load_bib_keys(bib_path: Path) -> set[str]:
    """Return the set of citation keys defined in a BibTeX file.

    Returns an empty set if the file does not exist or cannot be parsed;
    callers should treat this as "bibliography unavailable, skip audit"
    rather than as a hard failure.
    """
    if not bib_path.exists():
        logger.debug("Bibliography file not found: %s", bib_path)
        return set()

    try:
        from pybtex.database import parse_file

        bib = parse_file(str(bib_path))
    except Exception as exc:  # noqa: BLE001 - pybtex raises a variety of types
        logger.warning("Failed to parse bibliography %s: %s", bib_path, exc)
        return set()

    return set(bib.entries.keys())


__all__ = [
    "CitationAuditRecord",
    "MarkdownCitationAudit",
    "audit_markdown_citations",
    "extract_markdown_citations",
    "load_bib_keys",
]
