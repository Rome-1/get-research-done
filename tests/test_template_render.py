"""End-to-end PDF-content smoke tests for journal template renders.

Regression coverage for the bst/natbib pairing class of bugs (see ge-chy
cross-cutting audit, ge-kus, ge-5iu naturemag fix). Every tex-level assertion
in the suite passed while the rendered PDF silently showed ``(author?)``
because ``plain.bst`` / ``naturemag.bst`` do not implement natbib's
``\\citet`` / ``\\citep`` author-name macros. String-level invariants on the
``.tex`` output cannot catch that class; only the bibtex-resolved PDF can.

For each journal template we:

    1. Build a :class:`PaperConfig` with markdown that forces pandoc's natbib
       writer to emit both ``\\citep`` (``[@key]``) and ``\\citet`` (``@key``).
    2. Run the real :func:`render_paper` pipeline (pandoc + GRD Lua filters +
       Jinja template substitution + sanitization).
    3. Compile ``pdflatex -> bibtex -> pdflatex -> pdflatex``.
    4. Extract text with ``pdftotext -layout``.
    5. Assert none of the sentinels survive: ``(author?)`` (bst/natbib
       mismatch), ``[?]`` (unresolved cite key), and raw ``\\citet{`` /
       ``\\citep{`` (undefined control sequence, never replaced by bibtex).

Gating
------

The suite is gated three ways to keep it invisible on minimal CI images:

* ``RUN_LATEX_TESTS=1`` must be set (explicit opt-in).
* ``pdflatex``, ``bibtex``, ``pandoc``, and ``pdftotext`` must all be on
  PATH.
* Per-template, the document class and every ``required_tex_files`` entry
  from :data:`grd.mcp.paper.journal_map.JOURNAL_SPECS` must resolve via
  ``kpsewhich``; otherwise that template's case is skipped individually so
  partial TeX Live installs still run the tests they can.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from grd.mcp.paper.journal_map import JOURNAL_SPECS
from grd.mcp.paper.models import Author, PaperConfig, Section
from grd.mcp.paper.template_registry import render_paper
from grd.utils.pandoc import detect_pandoc

_RUN_LATEX = os.environ.get("RUN_LATEX_TESTS") == "1"
_TOOLS = ("pdflatex", "bibtex", "pdftotext", "pandoc")
_missing_tools = [t for t in _TOOLS if shutil.which(t) is None]

pytestmark = [
    pytest.mark.requires_latex,
    pytest.mark.skipif(
        not _RUN_LATEX,
        reason="set RUN_LATEX_TESTS=1 to enable end-to-end LaTeX render smoke tests",
    ),
    pytest.mark.skipif(
        bool(_missing_tools),
        reason=f"required LaTeX toolchain missing: {', '.join(_missing_tools)}",
    ),
]


_FIXTURE_BIB = r"""@article{einstein1905,
  author  = {Einstein, Albert},
  title   = {On the Electrodynamics of Moving Bodies},
  journal = {Annalen der Physik},
  year    = {1905},
}
@article{maxwell1865,
  author  = {Maxwell, James Clerk},
  title   = {A Dynamical Theory of the Electromagnetic Field},
  journal = {Phil. Trans. Roy. Soc.},
  year    = {1865},
}
"""

# Exercises both natbib citation forms pandoc emits under --natbib:
#   `@einstein1905` -> \citet{einstein1905}   (textual; the form that rendered
#                                              as "(author?)" against plain /
#                                              naturemag bsts)
#   `[@maxwell1865; @einstein1905]` -> \citep{maxwell1865, einstein1905}
_FIXTURE_SECTION_MD = (
    "Textual cite of @einstein1905 and a parenthetical group "
    "[@maxwell1865; @einstein1905] to exercise both forms pandoc's "
    "natbib writer emits.\n"
)


def _kpsewhich(name: str) -> str | None:
    """Return the resolved TeX path for *name*, or None if it is not installed."""
    kpse = shutil.which("kpsewhich")
    if kpse is None:
        return None
    proc = subprocess.run([kpse, name], capture_output=True, text=True, check=False, timeout=10)
    path = proc.stdout.strip()
    return path or None


def _skip_if_template_assets_missing(journal: str) -> None:
    spec = JOURNAL_SPECS[journal]
    class_file = f"{spec.document_class}.cls"
    missing: list[str] = []
    if _kpsewhich(class_file) is None:
        missing.append(class_file)
    for required in spec.required_tex_files:
        if _kpsewhich(required) is None:
            missing.append(required)
    if missing:
        pytest.skip(
            f"{journal}: kpsewhich cannot resolve required files: "
            f"{', '.join(missing)} (install texlive-{spec.texlive_package} or similar)"
        )


def _build_config(journal: str) -> PaperConfig:
    return PaperConfig(
        journal=journal,
        title=f"Smoke Test for {journal.upper()} Template",
        authors=[Author(name="Alice Test", affiliation="GRD Test Suite")],
        abstract=(
            "Two-key fixture used by the template-render smoke suite to assert "
            "the rendered PDF resolves natbib citations correctly."
        ),
        sections=[Section(title="Introduction", content=_FIXTURE_SECTION_MD)],
        bib_file="references",
    )


def _compile(tex_path: Path, workdir: Path) -> None:
    """Run pdflatex -> bibtex -> pdflatex -> pdflatex; raise on failure."""
    stem = tex_path.stem
    commands = [
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
        ["bibtex", stem],
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
    ]
    for cmd in commands:
        proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, check=False, timeout=120)
        if proc.returncode != 0:
            tail_out = proc.stdout[-2000:] if proc.stdout else ""
            tail_err = proc.stderr[-2000:] if proc.stderr else ""
            raise AssertionError(
                f"{' '.join(cmd)} failed (exit {proc.returncode}) in {workdir}\n"
                f"--- stdout tail ---\n{tail_out}\n"
                f"--- stderr tail ---\n{tail_err}"
            )


def _pdftotext(pdf_path: Path) -> str:
    proc = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return proc.stdout


def _assert_clean_citation_render(text: str, journal: str) -> None:
    assert "(author?)" not in text, (
        f"{journal}: rendered PDF contains '(author?)' — bst is not natbib-aware "
        "against pandoc's \\citet output (same failure mode as ge-kus / naturemag)"
    )
    assert "[?]" not in text, (
        f"{journal}: rendered PDF contains '[?]' — bibtex could not resolve one of the fixture citation keys"
    )
    # Raw natbib commands should never leak into rendered text; if they do,
    # bibtex or the bst never substituted them.
    for raw in (r"\citet{", r"\citep{", r"\citealp{", r"\citeyearpar{"):
        assert raw not in text, (
            f"{journal}: rendered PDF contains literal {raw!r} — a citation command escaped unresolved into the output"
        )


@pytest.fixture(scope="module")
def _pandoc_available() -> None:
    status = detect_pandoc()
    if not status.available or not status.meets_minimum:
        pytest.skip("pandoc (>= minimum version) required for template render smoke tests")


@pytest.mark.parametrize("journal", sorted(JOURNAL_SPECS))
def test_template_render_resolves_citations(journal: str, tmp_path: Path, _pandoc_available: None) -> None:
    """Render the fixture paper through each template and assert no citation
    sentinels survive in the extracted PDF text.
    """
    _skip_if_template_assets_missing(journal)

    workdir = tmp_path / journal
    workdir.mkdir()
    (workdir / "references.bib").write_text(_FIXTURE_BIB, encoding="utf-8")

    config = _build_config(journal)
    tex = render_paper(config, bib_keys={"einstein1905", "maxwell1865"})
    tex_path = workdir / "paper.tex"
    tex_path.write_text(tex, encoding="utf-8")

    _compile(tex_path, workdir)

    pdf_path = workdir / "paper.pdf"
    assert pdf_path.exists(), f"{journal}: pdflatex produced no PDF in {workdir}"

    text = _pdftotext(pdf_path)
    _assert_clean_citation_render(text, journal)
