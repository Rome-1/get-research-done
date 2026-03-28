"""Tests for cross-platform LaTeX toolchain detection."""

from __future__ import annotations

import pytest

from grd.mcp.paper.compiler import (
    detect_latex_toolchain,
    find_latex_compiler,
    get_latex_install_guidance,
)


class TestFindLatexCompiler:
    def test_returns_path_when_compiler_on_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("grd.mcp.paper.compiler.shutil.which", lambda _: "/usr/bin/pdflatex")
        assert find_latex_compiler("pdflatex") == "/usr/bin/pdflatex"

    def test_returns_none_when_not_found_on_non_windows(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("grd.mcp.paper.compiler.shutil.which", lambda _: None)
        monkeypatch.setattr("grd.mcp.paper.compiler.platform.system", lambda: "Linux")
        assert find_latex_compiler("pdflatex") is None

    def test_searches_windows_paths_when_not_on_path(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("grd.mcp.paper.compiler.shutil.which", lambda _: None)
        monkeypatch.setattr("grd.mcp.paper.compiler.platform.system", lambda: "Windows")

        # Create a fake MiKTeX install directory
        miktex_bin = tmp_path / "MiKTeX" / "miktex" / "bin" / "x64"
        miktex_bin.mkdir(parents=True)
        (miktex_bin / "pdflatex.exe").write_text("fake")

        monkeypatch.setattr(
            "grd.mcp.paper.compiler._WINDOWS_LATEX_SEARCH_DIRS",
            [str(tmp_path / "MiKTeX" / "miktex" / "bin" / "x64")],
        )

        result = find_latex_compiler("pdflatex")
        assert result is not None
        assert "pdflatex.exe" in result

    def test_searches_texlive_year_dirs_on_windows(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("grd.mcp.paper.compiler.shutil.which", lambda _: None)
        monkeypatch.setattr("grd.mcp.paper.compiler.platform.system", lambda: "Windows")

        # Create a fake TeX Live install directory with year subdir
        tl_bin = tmp_path / "texlive" / "2024" / "bin" / "windows"
        tl_bin.mkdir(parents=True)
        (tl_bin / "pdflatex.exe").write_text("fake")

        monkeypatch.setattr(
            "grd.mcp.paper.compiler._WINDOWS_LATEX_SEARCH_DIRS",
            [str(tmp_path / "texlive")],
        )

        result = find_latex_compiler("pdflatex")
        assert result is not None
        assert "pdflatex.exe" in result


class TestDetectLatexToolchain:
    def test_available_on_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "grd.mcp.paper.compiler.find_latex_compiler",
            lambda compiler: "/usr/bin/pdflatex",
        )
        status = detect_latex_toolchain()
        assert status.available is True
        assert status.compiler_path == "/usr/bin/pdflatex"
        assert status.distribution is not None

    def test_not_available(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "grd.mcp.paper.compiler.find_latex_compiler",
            lambda compiler: None,
        )
        status = detect_latex_toolchain()
        assert status.available is False
        assert status.compiler_path is None
        assert "No LaTeX compiler found" in status.message

    def test_detects_miktex_distribution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "grd.mcp.paper.compiler.find_latex_compiler",
            lambda compiler: "C:\\Users\\user\\AppData\\Local\\Programs\\MiKTeX\\miktex\\bin\\x64\\pdflatex.exe",
        )
        status = detect_latex_toolchain()
        assert status.available is True
        assert status.distribution == "MiKTeX"

    def test_detects_texlive_distribution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "grd.mcp.paper.compiler.find_latex_compiler",
            lambda compiler: "C:\\texlive\\2024\\bin\\windows\\pdflatex.exe",
        )
        status = detect_latex_toolchain()
        assert status.available is True
        assert status.distribution == "TeX Live"

    def test_detects_mactex_distribution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "grd.mcp.paper.compiler.find_latex_compiler",
            lambda compiler: "/Library/TeX/texbin/pdflatex",
        )
        status = detect_latex_toolchain()
        assert status.available is True
        assert status.distribution == "MacTeX"


class TestGetLatexInstallGuidance:
    def test_windows_guidance(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("grd.mcp.paper.compiler.platform.system", lambda: "Windows")
        msg = get_latex_install_guidance()
        assert "MiKTeX" in msg
        assert "miktex.org" in msg
        assert "TeX Live" in msg

    def test_macos_guidance(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("grd.mcp.paper.compiler.platform.system", lambda: "Darwin")
        msg = get_latex_install_guidance()
        assert "MacTeX" in msg or "mactex" in msg
        assert "brew" in msg

    def test_linux_guidance(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("grd.mcp.paper.compiler.platform.system", lambda: "Linux")
        msg = get_latex_install_guidance()
        assert "texlive" in msg
        assert "apt" in msg


class TestCompilePaperMissingCompiler:
    def test_compile_paper_returns_guidance_when_compiler_missing(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """compile_paper returns install guidance when no compiler is found."""
        import asyncio

        from grd.mcp.paper.compiler import compile_paper

        tex_path = tmp_path / "paper.tex"
        tex_path.write_text(r"\documentclass{article}\begin{document}test\end{document}", encoding="utf-8")

        monkeypatch.setattr("grd.mcp.paper.compiler.find_latex_compiler", lambda compiler: None)
        monkeypatch.setattr("grd.mcp.paper.compiler.platform.system", lambda: "Windows")

        result = asyncio.run(compile_paper(tex_path, tmp_path))
        assert result.success is False
        assert "not found" in result.error
        assert "MiKTeX" in result.error
