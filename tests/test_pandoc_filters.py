"""Integration tests for bundled Lua filters (grd.mcp.paper.filters).

These tests invoke real pandoc against each filter and assert on the emitted
LaTeX. Skipped automatically when pandoc is not installed.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from grd.mcp.paper.filters import FILTER_NAMES, all_filter_paths, filter_path
from grd.utils.pandoc import markdown_to_latex_fragment, run_pandoc

HAS_PANDOC = shutil.which("pandoc") is not None

pytestmark = pytest.mark.skipif(not HAS_PANDOC, reason="pandoc not installed")


# ─── filter_path() / all_filter_paths() ──────────────────────────────────────


def test_filter_path_returns_existing_lua_file() -> None:
    for name in FILTER_NAMES:
        path = filter_path(name)
        assert path.exists(), f"missing filter: {path}"
        assert path.suffix == ".lua"
        assert path.read_text().startswith("--")  # Lua comment header


def test_filter_path_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown filter"):
        filter_path("grd-nope")


def test_all_filter_paths_returns_every_bundled_filter() -> None:
    paths = all_filter_paths()
    assert len(paths) == len(FILTER_NAMES)
    assert {p.stem for p in paths} == set(FILTER_NAMES)


# ─── grd-obsidian-compat.lua ─────────────────────────────────────────────────


def test_obsidian_compat_rewrites_wikilinks_to_display_text() -> None:
    md = "See [[notes/alpha|the alpha note]] for context.\n"
    out = markdown_to_latex_fragment(md, lua_filters=[filter_path("grd-obsidian-compat")])
    assert "the alpha note" in out
    assert "[[" not in out
    assert "|" not in out.replace("$|$", "")  # no residual pipe from wikilink


def test_obsidian_compat_rewrites_bare_wikilinks_to_tail() -> None:
    md = "Jump to [[notes/folder/alpha]] now.\n"
    out = markdown_to_latex_fragment(md, lua_filters=[filter_path("grd-obsidian-compat")])
    assert "alpha" in out
    assert "[[" not in out


def test_obsidian_compat_converts_callout_to_bold_label() -> None:
    md = "> [!note] Heads up\n> This is the body.\n"
    out = markdown_to_latex_fragment(md, lua_filters=[filter_path("grd-obsidian-compat")])
    assert "\\textbf{Note: Heads up}" in out
    assert "\\begin{quote}" in out


def test_obsidian_compat_strips_obsidian_yaml_fields() -> None:
    md = "---\ntitle: Paper\nkb_type: note\ntags: [foo, bar]\ncssclass: fancy\n---\n\nBody text.\n"
    # Need --standalone to render Meta; fragment mode omits it. Use run_pandoc directly.
    out = run_pandoc(
        md,
        from_format="markdown",
        to_format="latex",
        lua_filters=[filter_path("grd-obsidian-compat")],
        standalone=True,
    )
    assert "\\title{Paper}" in out
    assert "kb_type" not in out
    assert "cssclass" not in out


def test_obsidian_compat_wikilink_ref_style_emits_latex_ref() -> None:
    md = "---\nobsidian_wikilink_style: ref\n---\n\nSee [[Phase Three]].\n"
    out = run_pandoc(
        md,
        from_format="markdown",
        to_format="latex",
        lua_filters=[filter_path("grd-obsidian-compat")],
        standalone=False,
    )
    assert "\\ref{phase-three}" in out


# ─── grd-crossref.lua ────────────────────────────────────────────────────────


def test_crossref_rewrites_phase_reference() -> None:
    md = "See [[phase:3]] for the derivation.\n"
    out = markdown_to_latex_fragment(md, lua_filters=[filter_path("grd-crossref")])
    assert "\\ref{phase:3}" in out
    assert "[[phase:3]]" not in out


def test_crossref_prefixes_figure_and_table_references() -> None:
    md = "See [[fig:conv]] and [[tab:results]] for data.\n"
    out = markdown_to_latex_fragment(md, lua_filters=[filter_path("grd-crossref")])
    assert "Figure~\\ref{fig:conv}" in out
    assert "Table~\\ref{tab:results}" in out


def test_crossref_leaves_unknown_namespace_intact() -> None:
    md = "Some [[custom:thing]] here.\n"
    out = markdown_to_latex_fragment(md, lua_filters=[filter_path("grd-crossref")])
    # Unknown namespace -> not rewritten, so no \ref command.
    assert "\\ref{" not in out


def test_crossref_respects_namespace_override_via_metadata() -> None:
    md = "---\ncrossref_namespaces: [custom]\n---\n\nSee [[custom:foo]].\n"
    out = run_pandoc(
        md,
        from_format="markdown",
        to_format="latex",
        lua_filters=[filter_path("grd-crossref")],
        standalone=False,
    )
    assert "\\ref{custom:foo}" in out


# ─── grd-math.lua ────────────────────────────────────────────────────────────


def test_math_promotes_labeled_display_math_to_equation_env() -> None:
    md = "Here's Einstein:\n\n$$E = mc^2$$ {#eq:einstein}\n"
    out = markdown_to_latex_fragment(md, lua_filters=[filter_path("grd-math")])
    assert "\\begin{equation}" in out
    assert "\\label{eq:einstein}" in out
    assert "E = mc^2" in out


def test_math_leaves_unlabeled_display_math_alone() -> None:
    md = "Just math: $$x + y = z$$\n"
    out = markdown_to_latex_fragment(md, lua_filters=[filter_path("grd-math")])
    # Pandoc's default for unlabeled display math is \[...\].
    assert "\\begin{equation}" not in out
    assert "x + y = z" in out


def test_math_preserves_inline_math_untouched() -> None:
    md = "Inline $a^2 + b^2 = c^2$ stays inline.\n"
    out = markdown_to_latex_fragment(md, lua_filters=[filter_path("grd-math")])
    assert "a^2 + b^2 = c^2" in out
    assert "\\begin{equation}" not in out


# ─── grd-figure.lua ──────────────────────────────────────────────────────────


def test_figure_emits_figure_environment_with_label() -> None:
    md = "![Convergence result](figures/conv.png){#fig:conv width=0.8\\linewidth}\n"
    out = markdown_to_latex_fragment(md, lua_filters=[filter_path("grd-figure")])
    assert "\\begin{figure}[H]" in out
    assert "\\includegraphics" in out
    assert "figures/conv.png" in out
    assert "\\caption{Convergence result}" in out
    assert "\\label{fig:conv}" in out


def test_figure_resolves_relative_path_against_base(tmp_path: Path) -> None:
    md = "---\nfigure_base_path: assets/figs\n---\n\n![A caption](conv.png){#fig:conv}\n"
    out = run_pandoc(
        md,
        from_format="markdown",
        to_format="latex",
        lua_filters=[filter_path("grd-figure")],
        standalone=False,
    )
    assert "assets/figs/conv.png" in out


def test_figure_preserves_absolute_paths(tmp_path: Path) -> None:
    md = "---\nfigure_base_path: assets/figs\n---\n\n![A caption](/abs/path/conv.png){#fig:conv}\n"
    out = run_pandoc(
        md,
        from_format="markdown",
        to_format="latex",
        lua_filters=[filter_path("grd-figure")],
        standalone=False,
    )
    assert "/abs/path/conv.png" in out
    assert "assets/figs/" not in out


def test_figure_honors_placement_override() -> None:
    md = "---\nfigure_placement: htbp\n---\n\n![A caption](conv.png){#fig:conv}\n"
    out = run_pandoc(
        md,
        from_format="markdown",
        to_format="latex",
        lua_filters=[filter_path("grd-figure")],
        standalone=False,
    )
    assert "\\begin{figure}[htbp]" in out


# ─── Filter composition ──────────────────────────────────────────────────────


def test_all_filters_compose_without_error() -> None:
    md = (
        "---\nfigure_base_path: figures\n---\n\n"
        "# Results\n\n"
        "As shown in [[fig:conv]], the system converges. See also [[phase:2]].\n\n"
        "$$E = mc^2$$ {#eq:einstein}\n\n"
        "![A figure](conv.png){#fig:conv}\n"
    )
    out = markdown_to_latex_fragment(md, lua_filters=all_filter_paths())
    assert "Figure~\\ref{fig:conv}" in out
    assert "\\ref{phase:2}" in out
    assert "\\label{eq:einstein}" in out
    assert "\\begin{figure}" in out
    assert "figures/conv.png" in out
