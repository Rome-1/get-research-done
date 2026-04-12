"""Tests for grd.mcp.paper.citations: markdown @key extraction and audit."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from grd.mcp.paper.citations import (
    audit_markdown_citations,
    extract_markdown_citations,
    load_bib_keys,
)
from grd.mcp.paper.models import PaperConfig, Section
from grd.mcp.paper.template_registry import render_paper

# ─── extract_markdown_citations ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "text, expected",
    [
        ("", []),
        ("No citations here.", []),
        ("See @smith2020.", ["smith2020"]),
        ("Two refs: @smith2020 and @jones2019.", ["smith2020", "jones2019"]),
        ("[@smith2020; @jones2019]", ["smith2020", "jones2019"]),
        ("[@smith2020, chapter 3; @jones2019, p. 45]", ["smith2020", "jones2019"]),
        ("@smith2020a and @smith2020b.", ["smith2020a", "smith2020b"]),
        ("Braced: @{weird key with spaces}.", ["weird key with spaces"]),
        ("Duplicate: @smith2020 @smith2020.", ["smith2020", "smith2020"]),
        ("Underscore key: @foo_bar:baz.", ["foo_bar:baz"]),
    ],
)
def test_extract_markdown_citations(text: str, expected: list[str]) -> None:
    assert extract_markdown_citations(text) == expected


def test_extract_markdown_citations_ignores_emails_and_code() -> None:
    text = (
        "Email user@example.com is not a citation.\n"
        "Inline `@fake` should be skipped.\n"
        "```\n@also_fake_in_fence\n```\n"
        "But @real2024 survives.\n"
    )
    assert extract_markdown_citations(text) == ["real2024"]


def test_extract_markdown_citations_handles_double_at() -> None:
    # `@@` is pandoc's escape for a literal `@` and should not match a key.
    assert extract_markdown_citations("Escaped @@notakey here.") == []


# ─── audit_markdown_citations ───────────────────────────────────────────────


def test_audit_markdown_citations_reports_defined_and_unresolved() -> None:
    text = "See @ok2020 and @missing2021; also @ok2020 again."
    audit = audit_markdown_citations(text, {"ok2020", "other2019"})

    assert audit.total_citations == 3
    assert audit.unique_keys == 2
    assert audit.unresolved_keys == ["missing2021"]
    by_key = {entry.key: entry for entry in audit.entries}
    assert by_key["ok2020"].count == 2
    assert by_key["ok2020"].defined is True
    assert by_key["missing2021"].count == 1
    assert by_key["missing2021"].defined is False


def test_audit_markdown_citations_empty_text() -> None:
    audit = audit_markdown_citations("", {"a", "b"})
    assert audit.total_citations == 0
    assert audit.unique_keys == 0
    assert audit.unresolved_keys == []
    assert audit.entries == []


# ─── load_bib_keys ──────────────────────────────────────────────────────────


def test_load_bib_keys_reads_known_entries(tmp_path: Path) -> None:
    bib = tmp_path / "references.bib"
    bib.write_text(
        "@article{smith2020,\n"
        "  author = {Smith, Jane},\n"
        "  title  = {A Paper},\n"
        "  year   = {2020},\n"
        "  journal = {Journal of Stuff},\n"
        "}\n"
        "@misc{jones2019,\n"
        "  title = {A Note},\n"
        "  year  = {2019},\n"
        "}\n",
        encoding="utf-8",
    )
    assert load_bib_keys(bib) == {"smith2020", "jones2019"}


def test_load_bib_keys_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_bib_keys(tmp_path / "nope.bib") == set()


def test_load_bib_keys_invalid_file_returns_empty(tmp_path: Path, caplog) -> None:
    bad = tmp_path / "bad.bib"
    bad.write_text("this is not bibtex", encoding="utf-8")
    with caplog.at_level(logging.WARNING):
        keys = load_bib_keys(bad)
    assert keys == set()


# ─── render_paper integration ────────────────────────────────────────────────


def test_render_paper_logs_warning_for_unresolved_keys(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger="grd.mcp.paper.template_registry")
    config = PaperConfig(
        journal="prl",
        title="A Paper",
        authors=[],
        abstract="Abstract",
        sections=[
            Section(title="Intro", content="Reference @known2020 and @unknown2099 here.\n"),
        ],
    )
    render_paper(config, bib_keys={"known2020"})
    messages = [record.getMessage() for record in caplog.records]
    assert any("unknown2099" in m for m in messages)
    assert not any("known2020" in m for m in messages)


def test_render_paper_no_warning_when_all_keys_resolved(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger="grd.mcp.paper.template_registry")
    config = PaperConfig(
        journal="prl",
        title="A Paper",
        authors=[],
        abstract="Abstract",
        sections=[Section(title="Intro", content="Cite @ok2020.\n")],
    )
    render_paper(config, bib_keys={"ok2020"})
    assert not any("citation key" in record.getMessage() for record in caplog.records)


def test_render_paper_skips_audit_when_bib_keys_is_none(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger="grd.mcp.paper.template_registry")
    config = PaperConfig(
        journal="prl",
        title="A Paper",
        authors=[],
        abstract="Abstract",
        sections=[Section(title="Intro", content="Cite @never_defined.\n")],
    )
    render_paper(config)  # no bib_keys → no audit → no warning
    assert not any("citation key" in record.getMessage() for record in caplog.records)


def test_render_paper_audit_ignores_latex_sections(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger="grd.mcp.paper.template_registry")
    # Raw-LaTeX sections use \cite{...}, not pandoc @key, so they must not
    # be audited as markdown.
    config = PaperConfig(
        journal="prl",
        title="A Paper",
        authors=[],
        abstract="Abstract",
        sections=[
            Section(
                title="Intro",
                content="\\section{Intro}\nAs in \\cite{something_that_looks_like_at_key}.\n",
            ),
        ],
    )
    render_paper(config, bib_keys=set())
    assert not any("citation key" in record.getMessage() for record in caplog.records)
