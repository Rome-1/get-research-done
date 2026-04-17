"""Tests for grd.core.lean.blueprint_core — init-blueprint + blueprint-status."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from grd.core.lean.blueprint_core import (
    BlueprintNode,
    BlueprintStatusResult,
    InitBlueprintResult,
    _generate_content_tex,
    _generate_lakefile,
    _generate_lean_root,
    _generate_lean_stub,
    _generate_lean_toolchain,
    _lean_module_name,
    _parse_content_tex,
    _render_ascii_graph,
    _sanitize_id,
    BlueprintGraph,
    init_blueprint,
    blueprint_status,
)


# ---------------------------------------------------------------------------
# Unit tests — helpers
# ---------------------------------------------------------------------------


class TestSanitizeId:
    def test_simple(self):
        assert _sanitize_id("analysis-A") == "analysis_A"

    def test_dots_and_spaces(self):
        assert _sanitize_id("plan.sub item") == "plan_sub_item"

    def test_already_clean(self):
        assert _sanitize_id("main") == "main"


class TestLeanModuleName:
    def test_hyphenated(self):
        assert _lean_module_name("analysis-A") == "AnalysisA"

    def test_underscored(self):
        assert _lean_module_name("wave_1_setup") == "Wave1Setup"

    def test_single_word(self):
        assert _lean_module_name("main") == "Main"


# ---------------------------------------------------------------------------
# Unit tests — generators
# ---------------------------------------------------------------------------


class TestGenerateContentTex:
    def test_basic_structure(self):
        nodes = [
            BlueprintNode(id="thm1", label="thm1", kind="theorem", objective="Main result"),
            BlueprintNode(id="lem1", label="lem1", kind="lemma"),
        ]
        edges = [("thm1", "lem1")]
        content = _generate_content_tex(nodes, edges, "Test Phase", "01", "TestProject")
        assert "\\title{Test Phase}" in content
        assert "\\begin{theorem}\\label{thm1}" in content
        assert "\\begin{lemma}\\label{lem1}" in content
        assert "\\uses{lem1}" in content
        assert "\\end{document}" in content

    def test_no_edges(self):
        nodes = [BlueprintNode(id="x", label="x", kind="definition")]
        content = _generate_content_tex(nodes, [], None, "03", None)
        assert "\\title{Phase 03}" in content
        # \uses{...} command should not appear in the body (comment header mentions it)
        assert "\\uses{" not in content


class TestGenerateLakefile:
    def test_contains_package(self):
        lf = _generate_lakefile("Test", "01")
        assert "Blueprint01" in lf
        assert "lean_lib" in lf

    def test_dot_phase(self):
        lf = _generate_lakefile(None, "02.1")
        assert "Blueprint02_1" in lf


class TestGenerateLeanRoot:
    def test_imports(self):
        nodes = [
            BlueprintNode(id="analysis-A", label="x"),
            BlueprintNode(id="main", label="y"),
        ]
        root = _generate_lean_root(nodes)
        assert "import Proofs.AnalysisA" in root
        assert "import Proofs.Main" in root


class TestGenerateLeanStub:
    def test_stub_content(self):
        stub = _generate_lean_stub("analysis-A")
        assert "theorem AnalysisA" in stub
        assert "sorry" in stub


class TestGenerateLeanToolchain:
    def test_with_version(self):
        tc = _generate_lean_toolchain("v4.14.0")
        assert tc.strip() == "leanprover/lean4:v4.14.0"

    def test_full_prefix(self):
        tc = _generate_lean_toolchain("leanprover/lean4:v4.12.0")
        assert tc.strip() == "leanprover/lean4:v4.12.0"

    def test_default(self):
        tc = _generate_lean_toolchain(None)
        assert "leanprover/lean4:" in tc


# ---------------------------------------------------------------------------
# Unit tests — parsing
# ---------------------------------------------------------------------------


class TestParseContentTex:
    def test_basic_parse(self):
        content = textwrap.dedent(r"""
        \begin{theorem}\label{thm1}
          \uses{lem1, lem2}
          \lean{Proofs.Thm1}
          \leanok
          Some informal statement.
        \end{theorem}

        \begin{lemma}\label{lem1}
          Another statement.
        \end{lemma}

        \begin{lemma}\label{lem2}
          \lean{Proofs.Lem2}
          Yet another.
        \end{lemma}
        """)
        nodes, edges = _parse_content_tex(content)
        assert len(nodes) == 3

        thm1 = next(n for n in nodes if n.id == "thm1")
        assert thm1.kind == "theorem"
        assert thm1.lean_name == "Proofs.Thm1"
        assert thm1.leanok is True
        assert thm1.status == "proved"
        assert thm1.depends_on == ["lem1", "lem2"]

        lem1 = next(n for n in nodes if n.id == "lem1")
        assert lem1.status == "informal"
        assert lem1.lean_name is None

        lem2 = next(n for n in nodes if n.id == "lem2")
        assert lem2.status == "stated"
        assert lem2.lean_name == "Proofs.Lem2"

        assert ("thm1", "lem1") in edges
        assert ("thm1", "lem2") in edges

    def test_empty(self):
        nodes, edges = _parse_content_tex("No environments here.")
        assert nodes == []
        assert edges == []


# ---------------------------------------------------------------------------
# Unit tests — rendering
# ---------------------------------------------------------------------------


class TestRenderAsciiGraph:
    def test_basic_render(self):
        graph = BlueprintGraph(
            phase="01",
            nodes=[
                BlueprintNode(id="a", label="a", status="proved", wave=1, leanok=True),
                BlueprintNode(id="b", label="b", status="stated", wave=1, depends_on=["a"]),
                BlueprintNode(id="c", label="c", status="informal", wave=2),
            ],
            edges=[("b", "a")],
        )
        text = _render_ascii_graph(graph)
        assert "[OK] a" in text
        assert "[--] b" in text
        assert "[  ] c" in text
        assert "Wave 1:" in text
        assert "Wave 2:" in text

    def test_empty_graph(self):
        graph = BlueprintGraph(phase="01")
        assert "(empty blueprint)" in _render_ascii_graph(graph)


# ---------------------------------------------------------------------------
# Integration tests — init_blueprint
# ---------------------------------------------------------------------------


def _make_project(tmp_path: Path, phase: str = "01-test") -> Path:
    """Create a minimal GRD project with one phase and plan."""
    grd_dir = tmp_path / ".grd"
    grd_dir.mkdir()
    (grd_dir / "PROJECT.md").write_text("# Test Project\n", encoding="utf-8")
    (grd_dir / "state.json").write_text('{"project": {"name": "TestProject"}}', encoding="utf-8")

    phase_dir = grd_dir / "phases" / phase
    phase_dir.mkdir(parents=True)
    (phase_dir / "PLAN.md").write_text(
        textwrap.dedent("""\
            ---
            objective: "Main analysis task"
            wave: 1
            depends_on: []
            ---
            ## Task 1
            Do the thing.
        """),
        encoding="utf-8",
    )
    (phase_dir / "secondary-PLAN.md").write_text(
        textwrap.dedent("""\
            ---
            objective: "Supporting lemma"
            wave: 1
            depends_on: ["PLAN"]
            ---
            ## Task 1
            Support the thing.
        """),
        encoding="utf-8",
    )
    return tmp_path


def test_init_blueprint_creates_directory(tmp_path: Path):
    project = _make_project(tmp_path)
    result = init_blueprint(project, "01")
    assert result.ok
    assert result.node_count >= 1
    assert "content.tex" in result.files_created
    assert "lakefile.lean" in result.files_created
    assert "Blueprint.lean" in result.files_created

    bp_dir = project / result.blueprint_dir
    assert bp_dir.is_dir()
    assert (bp_dir / "content.tex").is_file()
    assert (bp_dir / "Proofs").is_dir()


def test_init_blueprint_refuses_existing(tmp_path: Path):
    project = _make_project(tmp_path)
    result1 = init_blueprint(project, "01")
    assert result1.ok

    result2 = init_blueprint(project, "01")
    assert not result2.ok
    assert "already exists" in result2.error


def test_init_blueprint_force_overwrites(tmp_path: Path):
    project = _make_project(tmp_path)
    init_blueprint(project, "01")
    result = init_blueprint(project, "01", force=True)
    assert result.ok


def test_init_blueprint_nonexistent_phase(tmp_path: Path):
    project = _make_project(tmp_path)
    result = init_blueprint(project, "99")
    assert not result.ok
    assert "not found" in result.error


def test_init_blueprint_captures_plan_deps(tmp_path: Path):
    project = _make_project(tmp_path)
    result = init_blueprint(project, "01")
    assert result.ok
    assert result.edge_count >= 1

    content = (project / result.blueprint_dir / "content.tex").read_text(encoding="utf-8")
    assert "\\uses{" in content


# ---------------------------------------------------------------------------
# Integration tests — blueprint_status
# ---------------------------------------------------------------------------


def test_blueprint_status_reads_content_tex(tmp_path: Path):
    project = _make_project(tmp_path)
    init_blueprint(project, "01")

    result = blueprint_status(project, "01", typecheck=False)
    assert result.ok
    assert len(result.graph.nodes) >= 1
    assert result.ascii_graph is not None
    assert "Wave" in result.ascii_graph


def test_blueprint_status_no_blueprint(tmp_path: Path):
    project = _make_project(tmp_path)
    result = blueprint_status(project, "01", typecheck=False)
    assert not result.ok
    assert "No blueprint found" in result.error


def test_blueprint_status_nonexistent_phase(tmp_path: Path):
    project = _make_project(tmp_path)
    result = blueprint_status(project, "99", typecheck=False)
    assert not result.ok
    assert "not found" in result.error


def test_blueprint_status_summary_counts(tmp_path: Path):
    project = _make_project(tmp_path)
    init_blueprint(project, "01")
    result = blueprint_status(project, "01", typecheck=False)
    assert result.ok
    assert result.summary["total"] >= 1
    assert result.summary["informal"] >= 1  # freshly generated = all informal
    assert result.summary["proved"] == 0
