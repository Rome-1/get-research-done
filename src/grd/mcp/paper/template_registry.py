"""Jinja2 template registry for LaTeX journal templates.

Uses custom LaTeX-safe delimiters to avoid conflicts with LaTeX curly braces:
    \\VAR{...}   for variables
    \\BLOCK{...} for control flow
    \\#{...}     for comments
"""

from __future__ import annotations

import logging
from importlib.resources import files

from jinja2 import BaseLoader, Environment, TemplateNotFound

from grd.mcp.paper.citations import extract_markdown_citations
from grd.mcp.paper.filters import all_filter_paths
from grd.mcp.paper.markdown_support import looks_like_latex, maybe_convert_to_latex
from grd.mcp.paper.models import Author, FigureRef, PaperConfig, Section
from grd.utils.latex import clean_latex_fences, fix_bibliography_conflict, sanitize_latex
from grd.utils.pandoc import detect_pandoc

logger = logging.getLogger(__name__)


class _PackageTemplateLoader(BaseLoader):
    """Jinja2 loader that reads templates from package data via importlib.resources."""

    def get_source(self, environment: Environment, template: str) -> tuple[str, str, None]:
        pkg = files("grd.mcp.paper.templates")
        # template name is like "prl/prl_template.tex"
        try:
            resource = pkg.joinpath(template)
            source = resource.read_text(encoding="utf-8")
            return source, template, None
        except (FileNotFoundError, TypeError, AttributeError) as exc:
            raise TemplateNotFound(template) from exc


# Jinja2 environment with LaTeX-safe custom delimiters.
_env = Environment(
    loader=_PackageTemplateLoader(),
    block_start_string=r"\BLOCK{",
    block_end_string="}",
    variable_start_string=r"\VAR{",
    variable_end_string="}",
    comment_start_string=r"\#{",
    comment_end_string="}",
    line_statement_prefix="%%",
    line_comment_prefix="%#",
    trim_blocks=True,
    autoescape=False,
)


def load_template(journal: str):
    """Load a Jinja2 template for the given journal.

    Raises:
        FileNotFoundError: If the template file does not exist.
    """
    template_name = f"{journal}/{journal}_template.tex"
    try:
        return _env.get_template(template_name)
    except TemplateNotFound as exc:
        raise FileNotFoundError(f"Template not found for journal '{journal}': {template_name}") from exc


def _clean_author(author: Author) -> Author:
    return author.model_copy(
        update={
            "name": clean_latex_fences(author.name),
            "email": clean_latex_fences(author.email),
            "affiliation": clean_latex_fences(author.affiliation),
        }
    )


def _clean_section(section: Section) -> Section:
    return section.model_copy(
        update={
            "title": clean_latex_fences(section.title),
            "content": clean_latex_fences(section.content),
        }
    )


def _convert_section_markdown(section: Section, *, lua_filters: list | None, pandoc_status) -> Section:
    """Run markdown-to-LaTeX conversion on section content when applicable."""
    converted = maybe_convert_to_latex(
        section.content,
        lua_filters=lua_filters,
        pandoc_status=pandoc_status,
    )
    if converted is section.content:
        return section
    return section.model_copy(update={"content": converted})


def _clean_figure(figure: FigureRef) -> FigureRef:
    return figure.model_copy(update={"caption": clean_latex_fences(figure.caption)})


def _audit_markdown_citations_over_sections(
    sections: list[Section],
    bib_keys: set[str],
) -> None:
    """Log a warning for every ``@key`` in markdown sections missing from *bib_keys*.

    The audit only looks at sections whose content is still markdown at
    render time (i.e. not raw LaTeX). Missing keys are advisory — pdflatex
    will still run — but they let callers spot citation typos before the
    compile step turns them into ``?`` placeholders.
    """
    referenced: set[str] = set()
    for section in sections:
        if looks_like_latex(section.content):
            continue
        referenced.update(extract_markdown_citations(section.content))
    if not referenced:
        return
    unresolved = sorted(referenced - bib_keys)
    if unresolved:
        logger.warning(
            "Markdown sections reference %d citation key(s) not found in the bibliography: %s",
            len(unresolved),
            ", ".join(unresolved),
        )


def render_paper(config: PaperConfig, *, bib_keys: set[str] | None = None) -> str:
    """Render a complete LaTeX document from a PaperConfig.

    Loads the template for config.journal, renders it with all config fields,
    and applies LaTeX sanitization to the output.

    Section content written in markdown (no ``\\section{``/``\\begin{...}``
    sigils) is converted to a LaTeX fragment via pandoc + the bundled GRD
    Lua filters before template substitution. Content that already looks
    like LaTeX is passed through unchanged, preserving the existing
    contract for PaperConfig payloads authored in raw LaTeX.

    When *bib_keys* is supplied (the set of citation keys defined in the
    project's ``.bib`` file), any markdown section that references a
    key not in that set triggers a warning log. This is advisory only;
    the render never fails on unresolved keys because pdflatex + bibtex
    is the authoritative resolver.
    """
    template = load_template(config.journal)
    pandoc_status = detect_pandoc()
    lua_filters = all_filter_paths() if pandoc_status.available and pandoc_status.meets_minimum else None

    if bib_keys is not None:
        all_md_sections = [*config.sections, *config.appendix_sections]
        _audit_markdown_citations_over_sections(all_md_sections, bib_keys)

    authors = [_clean_author(author) for author in config.authors]
    sections = [
        _clean_section(_convert_section_markdown(s, lua_filters=lua_filters, pandoc_status=pandoc_status))
        for s in config.sections
    ]
    appendix_sections = [
        _clean_section(_convert_section_markdown(s, lua_filters=lua_filters, pandoc_status=pandoc_status))
        for s in config.appendix_sections
    ]
    figures = [_clean_figure(figure) for figure in config.figures]
    rendered = template.render(
        title=clean_latex_fences(config.title),
        authors=authors,
        abstract=clean_latex_fences(config.abstract),
        sections=sections,
        figures=figures,
        acknowledgments=clean_latex_fences(config.acknowledgments) if config.acknowledgments else None,
        bib_file=config.bib_file,
        appendix_sections=appendix_sections,
        attribution_footer=clean_latex_fences(config.attribution_footer),
    )

    # Apply LaTeX sanitization as a safety net
    rendered = sanitize_latex(rendered)

    # Fix conflicting bibliography styles: if the paper-writer agent injected
    # inline \begin{thebibliography} entries, strip the template's
    # \bibliographystyle and \bibliography commands which are incompatible.
    rendered = fix_bibliography_conflict(rendered)

    return rendered
