"""Tests for \bibliographystyle + inline \thebibliography conflict fix (issue #24)."""

from __future__ import annotations

from grd.utils.latex import fix_bibliography_conflict, try_autofix


class TestFixBibliographyConflict:
    def test_strips_bibliographystyle_when_thebibliography_present(self) -> None:
        tex = (
            "\\bibliographystyle{unsrtnat}\n"
            "\n"
            "\\begin{thebibliography}{99}\n"
            "\\bibitem{ref1} Author, Title, 2024.\n"
            "\\end{thebibliography}\n"
        )
        result = fix_bibliography_conflict(tex)
        assert "\\bibliographystyle" not in result
        assert "\\begin{thebibliography}" in result
        assert "\\bibitem{ref1}" in result

    def test_strips_bibliography_command_when_thebibliography_present(self) -> None:
        tex = (
            "\\bibliographystyle{naturemag}\n"
            "\\bibliography{references}\n"
            "\n"
            "\\begin{thebibliography}{99}\n"
            "\\bibitem{ref1} Author, Title, 2024.\n"
            "\\end{thebibliography}\n"
        )
        result = fix_bibliography_conflict(tex)
        assert "\\bibliographystyle" not in result
        assert "\\bibliography{references}" not in result
        assert "\\begin{thebibliography}" in result

    def test_no_change_when_no_thebibliography(self) -> None:
        tex = (
            "\\bibliographystyle{unsrtnat}\n"
            "\\bibliography{references}\n"
            "\\end{document}\n"
        )
        result = fix_bibliography_conflict(tex)
        assert result == tex

    def test_no_change_when_no_bibliographystyle(self) -> None:
        tex = (
            "\\begin{thebibliography}{99}\n"
            "\\bibitem{ref1} Author, Title, 2024.\n"
            "\\end{thebibliography}\n"
        )
        result = fix_bibliography_conflict(tex)
        assert result == tex

    def test_preserves_thebibliography_content(self) -> None:
        tex = (
            "\\documentclass{article}\n"
            "\\usepackage{natbib}\n"
            "\\begin{document}\n"
            "Some text \\cite{ref1}.\n"
            "\\bibliographystyle{unsrtnat}\n"
            "\\bibliography{refs}\n"
            "\\begin{thebibliography}{99}\n"
            "\\bibitem{ref1} First Author, A Great Paper, 2024.\n"
            "\\bibitem{ref2} Second Author, Another Paper, 2023.\n"
            "\\end{thebibliography}\n"
            "\\end{document}\n"
        )
        result = fix_bibliography_conflict(tex)
        assert "\\bibliographystyle" not in result
        assert "\\bibitem{ref1}" in result
        assert "\\bibitem{ref2}" in result
        assert "\\begin{thebibliography}" in result
        assert "\\end{thebibliography}" in result
        assert "\\documentclass{article}" in result
        assert "\\end{document}" in result


class TestAutoFixIntegration:
    def test_natbib_error_triggers_bibliography_conflict_fix(self) -> None:
        tex = (
            "\\bibliographystyle{unsrtnat}\n"
            "\\begin{thebibliography}{99}\n"
            "\\bibitem{ref1} Author, Title, 2024.\n"
            "\\end{thebibliography}\n"
        )
        log = "! Package natbib Error: Bibliography not compatible with author-year citations."
        result = try_autofix(tex, log)
        assert result.was_modified is True
        assert "\\bibliographystyle" not in result.fixed_content
        assert "\\begin{thebibliography}" in result.fixed_content
