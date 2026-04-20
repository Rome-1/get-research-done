"""Tests for grd.mcp.paper.markdown_support and its render_paper integration."""

from __future__ import annotations

import shutil

import pytest

from grd.mcp.paper import markdown_support
from grd.mcp.paper.markdown_support import looks_like_latex, maybe_convert_to_latex
from grd.mcp.paper.models import PaperConfig, Section
from grd.mcp.paper.template_registry import render_paper
from grd.utils.pandoc import PandocExecutionError, PandocStatus

HAS_PANDOC = shutil.which("pandoc") is not None


# ─── looks_like_latex ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "content",
    [
        "\\documentclass{article}\n",
        "\\section{Intro}\nBody.\n",
        "\\subsection{Method}",
        "\\begin{document}\nHi.\n",
        "\\begin{figure}\n\\includegraphics{x.png}\n\\end{figure}",
        "\\begin{itemize}\n\\item a\n\\end{itemize}",
        "\\title{Paper}\n\\author{Me}",
        "Intro paragraph.\n\n\\section{Results}\nMore text.",
        "```latex\nE = mc^2\n```",
        "```tex\n\\frac{a}{b}\n```",
        # Display-math environments are LaTeX-specific, not markdown.
        "\\begin{equation}\nE = mc^2\n\\end{equation}",
        "\\begin{equation*}\nx = y\n\\end{equation*}",
        "\\begin{align}\na &= b \\\\ c &= d\n\\end{align}",
        "\\begin{gather}\nx = y\n\\end{gather}",
        "\\begin{multline}\na + b\n\\end{multline}",
        "\\begin{eqnarray}\na &=& b\n\\end{eqnarray}",
        # Other structural commands the broader sigil set should catch.
        "\\maketitle",
        "\\bibliography{refs}",
        "\\usepackage{amsmath}",
        "\\appendix\n\\section{Proofs}",
        "\\part{Foundations}",
    ],
)
def test_looks_like_latex_detects_structural_commands(content: str) -> None:
    assert looks_like_latex(content) is True


@pytest.mark.parametrize(
    "content",
    [
        "",
        "Plain markdown paragraph.",
        "# Heading\n\nBody with *emphasis*.\n",
        "Inline math $a^2 + b^2 = c^2$ is valid markdown.",
        "$$x = y$$\n",
        "Text with \\alpha in the middle but no structural command.",  # stray command, not a header
    ],
)
def test_looks_like_latex_rejects_plain_markdown(content: str) -> None:
    assert looks_like_latex(content) is False


@pytest.mark.parametrize(
    "content",
    [
        # Bare ``` fence quoting LaTeX must not fool the heuristic.
        "Here's an example:\n\n```\n\\section{Quoted}\nNot real.\n```\n\nBack to prose.",
        # Untagged fence quoting an equation env -- still markdown.
        "Example:\n```\n\\begin{equation}\nE = mc^2\n\\end{equation}\n```\n",
        # Markdown content surrounding fenced LaTeX example.
        "# Tutorial\n\nWrite section headers like this:\n\n```\n\\section{Foo}\n```\n\nThen save the file.",
        # Python fence happens to mention \documentclass in a string.
        "```python\nprint('\\\\documentclass{article}')\n```",
    ],
)
def test_looks_like_latex_ignores_latex_inside_fenced_code_blocks(content: str) -> None:
    assert looks_like_latex(content) is False


def test_looks_like_latex_still_honors_explicit_latex_fence_inside_other_fence() -> None:
    # Author explicitly tagged a ```latex fence -- that is a declared LaTeX
    # signal and wins over the fence-stripping heuristic.
    content = "Some prose.\n\n```latex\n\\section{Real}\n```\n"
    assert looks_like_latex(content) is True


# ─── maybe_convert_to_latex ──────────────────────────────────────────────────


def _stub_status(*, available: bool, meets_minimum: bool = True) -> PandocStatus:
    return PandocStatus(
        available=available,
        binary_path="/usr/bin/pandoc" if available else None,
        version=(3, 1, 3) if available else None,
        version_string="pandoc 3.1.3" if available else None,
        meets_minimum=meets_minimum,
    )


def test_maybe_convert_passes_through_latex_unchanged() -> None:
    content = "\\section{Results}\nBody.\n"
    out = maybe_convert_to_latex(content, pandoc_status=_stub_status(available=True))
    assert out is content


def test_maybe_convert_passes_through_when_pandoc_missing() -> None:
    content = "# Plain markdown\n\nWith body.\n"
    out = maybe_convert_to_latex(content, pandoc_status=_stub_status(available=False))
    assert out == content


def test_maybe_convert_passes_through_when_pandoc_too_old() -> None:
    content = "# Plain markdown\n\nWith body.\n"
    status = _stub_status(available=True, meets_minimum=False)
    out = maybe_convert_to_latex(content, pandoc_status=status)
    assert out == content


def test_maybe_convert_returns_empty_for_empty_input() -> None:
    assert maybe_convert_to_latex("", pandoc_status=_stub_status(available=True)) == ""


def test_maybe_convert_reraises_pandoc_execution_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # If pandoc runs but errors, we must surface it -- silently returning
    # the markdown source compiles a .tex file full of unprocessed ``# ``
    # headings and yields garbage output.
    def _boom(*_args, **_kwargs):
        raise PandocExecutionError("pandoc exited 1", stderr="bad input", returncode=1)

    monkeypatch.setattr(markdown_support, "markdown_to_latex_fragment", _boom)

    with pytest.raises(PandocExecutionError):
        maybe_convert_to_latex(
            "# Plain markdown\n\nBody.\n",
            pandoc_status=_stub_status(available=True),
        )


@pytest.mark.skipif(not HAS_PANDOC, reason="pandoc not installed")
def test_maybe_convert_runs_pandoc_on_markdown_when_available() -> None:
    content = "## Header\n\nWith *emphasis* and `code`.\n"
    out = maybe_convert_to_latex(content)  # uses real detect_pandoc()
    assert "\\emph{emphasis}" in out
    assert "\\texttt{code}" in out
    assert "\\documentclass" not in out  # fragment, not full document


# ─── render_paper integration ────────────────────────────────────────────────


@pytest.mark.skipif(not HAS_PANDOC, reason="pandoc not installed")
def test_render_paper_converts_markdown_sections_to_latex() -> None:
    rendered = render_paper(
        PaperConfig(
            journal="prl",
            title="A Paper",
            authors=[],
            abstract="Abstract text.",
            sections=[
                Section(title="Intro", content="Plain markdown with *emphasis*.\n"),
            ],
        )
    )
    assert "\\emph{emphasis}" in rendered


@pytest.mark.skipif(not HAS_PANDOC, reason="pandoc not installed")
def test_render_paper_preserves_existing_latex_sections() -> None:
    rendered = render_paper(
        PaperConfig(
            journal="prl",
            title="A Paper",
            authors=[],
            abstract="Abstract",
            sections=[
                Section(title="Intro", content="\\section{Intro}\n\\emph{Legacy LaTeX} content.\n"),
            ],
        )
    )
    assert "\\emph{Legacy LaTeX}" in rendered
    # Legacy LaTeX must not be double-wrapped or converted.
    assert rendered.count("\\emph{Legacy LaTeX}") == 1


def test_render_paper_still_works_without_pandoc(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force the markdown-conversion path to see "pandoc unavailable".
    from grd.mcp.paper import template_registry

    monkeypatch.setattr(
        template_registry,
        "detect_pandoc",
        lambda: _stub_status(available=False),
    )
    rendered = render_paper(
        PaperConfig(
            journal="prl",
            title="A Paper",
            authors=[],
            abstract="Abstract",
            sections=[Section(title="Intro", content="Plain markdown stays as-is.\n")],
        )
    )
    # Without pandoc, markdown is inserted verbatim -- we should still see
    # the original text in the output.
    assert "Plain markdown stays as-is." in rendered
