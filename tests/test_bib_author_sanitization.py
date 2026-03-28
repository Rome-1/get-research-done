"""Tests for BibTeX author field sanitization (issue #18).

Verifies that ``et al.`` variants are replaced with proper BibTeX
``and others`` syntax, and non-Latin characters are stripped to prevent
Unicode compilation errors like ``! LaTeX Error: Unicode character 就
(U+5C31) not set up for use with LaTeX``.
"""

from __future__ import annotations

from grd.mcp.paper.bibliography import (
    CitationSource,
    create_bibliography,
    sanitize_bib_author_field,
    sanitize_bib_authors,
)


class TestSanitizeBibAuthors:
    def test_et_al_replaced_with_others(self) -> None:
        result = sanitize_bib_authors(["Frisch, H.", "Chapel, J.", "R. Viday et al."])
        assert result == ["Frisch, H.", "Chapel, J.", "R. Viday", "others"]

    def test_standalone_et_al_becomes_others(self) -> None:
        result = sanitize_bib_authors(["Frisch, H.", "et al."])
        assert result == ["Frisch, H.", "others"]

    def test_etal_no_space(self) -> None:
        result = sanitize_bib_authors(["Smith, A.", "Jones, B. etal."])
        assert result == ["Smith, A.", "Jones, B", "others"]

    def test_et_dot_al(self) -> None:
        result = sanitize_bib_authors(["Smith, A.", "et. al."])
        assert result == ["Smith, A.", "others"]

    def test_no_et_al_unchanged(self) -> None:
        result = sanitize_bib_authors(["Frisch, H.", "Chapel, J.", "Viday, R."])
        assert result == ["Frisch, H.", "Chapel, J.", "Viday, R."]

    def test_already_has_others(self) -> None:
        result = sanitize_bib_authors(["Smith, A.", "others"])
        assert result == ["Smith, A.", "others"]

    def test_cjk_characters_stripped(self) -> None:
        result = sanitize_bib_authors(["Smith, J.", "R就地"])
        assert result == ["Smith, J.", "R"]

    def test_unicode_author_stripped(self) -> None:
        result = sanitize_bib_authors(["Smith, J.", "\u5c31\u5730Wang"])
        assert result == ["Smith, J.", "Wang"]

    def test_latin_extended_preserved(self) -> None:
        result = sanitize_bib_authors(["M\u00fcller, K.", "Erd\u0151s, P."])
        assert result == ["M\u00fcller, K.", "Erd\u0151s, P."]

    def test_empty_authors(self) -> None:
        result = sanitize_bib_authors([])
        assert result == []

    def test_only_et_al(self) -> None:
        result = sanitize_bib_authors(["et al."])
        assert result == ["others"]


class TestSanitizeBibAuthorField:
    def test_replaces_et_al(self) -> None:
        result = sanitize_bib_author_field(
            "Frisch, H. and Chapel, J. and R. Viday et al."
        )
        assert result == "Frisch, H. and Chapel, J. and R. Viday and others"

    def test_no_et_al_unchanged(self) -> None:
        result = sanitize_bib_author_field("Smith, A. and Jones, B.")
        assert result == "Smith, A. and Jones, B."

    def test_strips_cjk(self) -> None:
        result = sanitize_bib_author_field("Smith, A. and R\u5c31\u5730")
        assert "\u5c31" not in result
        assert "\u5730" not in result


class TestPipelineIntegration:
    def test_create_bibliography_sanitizes_authors(self) -> None:
        source = CitationSource(
            source_type="paper",
            title="Test paper",
            authors=["Frisch, H.", "Chapel, J.", "R. Viday et al."],
            year="2009",
        )
        bib = create_bibliography([source])
        entry = list(bib.entries.values())[0]
        author_field = entry.fields["author"]
        assert "et al" not in author_field
        assert "and others" in author_field

    def test_create_bibliography_no_unicode_in_author(self) -> None:
        source = CitationSource(
            source_type="paper",
            title="Test paper",
            authors=["Smith, J.", "\u5c31\u5730Wang, L."],
            year="2020",
        )
        bib = create_bibliography([source])
        entry = list(bib.entries.values())[0]
        author_field = entry.fields["author"]
        # No CJK characters should survive
        for char in author_field:
            assert ord(char) < 0x4E00 or ord(char) > 0x9FFF, (
                f"CJK character U+{ord(char):04X} found in author field"
            )

    def test_bib_file_output_is_clean(self, tmp_path) -> None:
        from grd.mcp.paper.bibliography import write_bib_file

        source = CitationSource(
            source_type="paper",
            title="Thermal management systems",
            authors=["Frisch, H.", "Chapel, J.", "R. Viday et al."],
            year="2009",
            journal="Progress in Nuclear Energy",
            volume="51",
            pages="542-551",
        )
        bib = create_bibliography([source])
        bib_path = tmp_path / "references.bib"
        write_bib_file(bib, bib_path)

        content = bib_path.read_text(encoding="utf-8")
        assert "et al" not in content
        assert "and others" in content
        assert "\u5c31" not in content
        # Verify it's valid ASCII-safe content
        content.encode("ascii", errors="strict")  # Should not raise
