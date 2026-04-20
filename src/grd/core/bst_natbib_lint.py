"""Static lint for ``\\bibliographystyle`` / natbib pairings in LaTeX templates.

Catches the silent-rendering bug class where pandoc's ``--natbib`` mode emits
``\\citet`` / ``\\citep`` against a numeric-only bst (e.g. ``naturemag``,
``plain``), which compiles cleanly but renders ``(author?)`` in the PDF.

History: two review cycles missed this class — ge-kus (``plain.bst`` + natbib)
and the naturemag bug — because every string-level test passed and pdflatex
never failed. See ge-chy audit for the full pairing matrix.

The lint complements (does not replace) a pdftotext smoke test (ge-blo): the
smoke test catches *any* bst that renders wrong; this lint catches the
*specific* bsts we know about, at template-edit time, with no LaTeX install.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

# Bsts that implement the natbib citation API (\citet, \citep, \citeyearpar,
# \citealp, ...). Safe to pair with \usepackage{natbib} or pandoc --natbib.
NATBIB_AWARE_BSTS: frozenset[str] = frozenset(
    {
        "plainnat",
        "abbrvnat",
        "unsrtnat",
        "mnras",
        "jfm",
        "apsrev4-2",
        "apsrmp",
        "aasjournal",
        "JHEP",
        "elsarticle-num",
        "iopart-num",
    }
)

# Numeric-only bsts. \citet against these renders "(author?)" in the PDF
# while compiling cleanly — the silent-failure mode that motivated this lint.
NUMERIC_ONLY_BSTS: frozenset[str] = frozenset(
    {
        "plain",
        "abbrv",
        "alpha",
        "unsrt",
        "naturemag",
        "ieeetr",
    }
)

# Wrapper packages that load natbib (or provide its citation commands)
# transparently, so a template using them does not need an explicit
# \usepackage{natbib}. Detected by \usepackage{<name>}.
NATBIB_PROVIDER_PACKAGES: frozenset[str] = frozenset(
    {
        "jheppub",
        "aastex",
        "aastex62",
        "aastex63",
        "aastex631",
        "aastex7",
    }
)

# Document classes that load natbib themselves when no class option is given
# (rare — most require an opt-in option like [natbib] or [usenatbib]).
NATBIB_PROVIDER_CLASSES: frozenset[str] = frozenset(
    {
        "aastex",
        "aastex62",
        "aastex63",
        "aastex631",
        "aastex7",
    }
)


@dataclass(frozen=True)
class Finding:
    """A single lint hit on a template."""

    source: str  # Human-readable label (path, template name, ...)
    severity: str  # "error" | "warning"
    message: str


_BST_RE = re.compile(r"\\bibliographystyle\{([^}]+)\}")
_USEPKG_NATBIB_RE = re.compile(r"\\usepackage(?:\[[^\]]*\])?\{natbib\}")
_DOCCLASS_RE = re.compile(r"\\documentclass(?:\[([^\]]*)\])?\{([^}]+)\}")
_USEPKG_ANY_RE = re.compile(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}")


def _strip_comments(tex: str) -> str:
    """Drop LaTeX line comments so we don't false-positive on commented-out code.

    Honours backslash-escaped percent signs (``\\%``).
    """
    out_lines: list[str] = []
    for line in tex.splitlines():
        i = 0
        while i < len(line):
            ch = line[i]
            if ch == "\\" and i + 1 < len(line):
                i += 2
                continue
            if ch == "%":
                line = line[:i]
                break
            i += 1
        out_lines.append(line)
    return "\n".join(out_lines)


def _natbib_loaded(tex: str) -> bool:
    """Return True iff *tex* loads natbib (directly or via a wrapper package)."""
    if _USEPKG_NATBIB_RE.search(tex):
        return True

    for match in _DOCCLASS_RE.finditer(tex):
        opts_raw, cls = match.group(1), match.group(2)
        opts = {opt.strip() for opt in (opts_raw or "").split(",") if opt.strip()}
        if "natbib" in opts or "usenatbib" in opts:
            return True
        if cls in NATBIB_PROVIDER_CLASSES:
            return True

    for match in _USEPKG_ANY_RE.finditer(tex):
        if match.group(1).strip() in NATBIB_PROVIDER_PACKAGES:
            return True

    return False


def lint_template(tex: str, source: str) -> list[Finding]:
    """Lint a single LaTeX source for bst/natbib pairing problems.

    Returns one ``Finding`` per detected mismatch. A template with no
    ``\\bibliographystyle`` literal returns no findings (the bst is whatever
    the document class defaults to — out of scope for this string-level lint).
    """
    stripped = _strip_comments(tex)
    findings: list[Finding] = []

    natbib = _natbib_loaded(stripped)
    for match in _BST_RE.finditer(stripped):
        bst = match.group(1).strip()
        if bst in NUMERIC_ONLY_BSTS and natbib:
            findings.append(
                Finding(
                    source=source,
                    severity="error",
                    message=(
                        f"bst {bst!r} is numeric-only but natbib is loaded: "
                        f"\\citet will render as '(author?)' in the PDF"
                    ),
                )
            )
        elif bst in NATBIB_AWARE_BSTS and not natbib:
            findings.append(
                Finding(
                    source=source,
                    severity="error",
                    message=(
                        f"bst {bst!r} expects natbib but natbib is not loaded: \\citet/\\citep will be undefined macros"
                    ),
                )
            )

    return findings


def iter_packaged_template_sources() -> Iterator[tuple[str, str]]:
    """Yield ``(label, text)`` for every shipped journal template plus the
    standalone wrapper documented in ``specs/workflows/export.md``.
    """
    pkg = files("grd.mcp.paper.templates")
    for journal_dir in sorted(pkg.iterdir(), key=lambda p: p.name):
        if not journal_dir.is_dir():
            continue
        if journal_dir.name.startswith("_") or journal_dir.name.startswith("."):
            continue
        for resource in sorted(journal_dir.iterdir(), key=lambda p: p.name):
            if resource.name.endswith(".tex"):
                yield (
                    f"templates/{journal_dir.name}/{resource.name}",
                    resource.read_text(encoding="utf-8"),
                )

    yield from _iter_export_wrapper_sources()


def _iter_export_wrapper_sources() -> Iterator[tuple[str, str]]:
    """Extract LaTeX wrapper(s) embedded in the export.md spec.

    The spec ships fenced ``latex`` blocks that document the recommended
    standalone wrapper used when a template is missing. We lint those blocks
    so the documented fallback can't drift back into the ge-kus state.
    """
    spec = files("grd.specs").joinpath("workflows", "export.md")
    try:
        text = spec.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return

    pattern = re.compile(r"```(?:latex|tex)\n(.*?)\n```", re.DOTALL)
    for idx, match in enumerate(pattern.finditer(text), start=1):
        block = match.group(1)
        if "\\bibliographystyle" not in block:
            continue
        yield (f"specs/workflows/export.md#latex-block-{idx}", block)


def lint_sources(sources: Iterable[tuple[str, str]]) -> list[Finding]:
    """Run :func:`lint_template` over each ``(label, text)`` pair."""
    findings: list[Finding] = []
    for label, text in sources:
        findings.extend(lint_template(text, label))
    return findings


def lint_default_sources() -> list[Finding]:
    """Lint all packaged templates plus the export.md standalone wrapper(s)."""
    return lint_sources(iter_packaged_template_sources())


def lint_directory(root: Path) -> list[Finding]:
    """Lint every ``*.tex`` under *root* (recursive). Useful for ``gpd health``
    or callers operating on an out-of-tree template tree.
    """
    findings: list[Finding] = []
    for path in sorted(root.rglob("*.tex")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        rel = path.relative_to(root) if path.is_relative_to(root) else path
        findings.extend(lint_template(text, str(rel)))
    return findings
