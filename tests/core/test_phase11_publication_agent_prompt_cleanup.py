"""Focused regressions for the Phase 11 publication-agent prompt cleanup."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PAPER_WRITER = REPO_ROOT / "src/grd/agents/grd-paper-writer.md"
BIBLIOGRAPHER = REPO_ROOT / "src/grd/agents/grd-bibliographer.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _grd_return_block(path: Path) -> str:
    source = _read(path)
    return source.split("grd_return:\n", 1)[1].split("```", 1)[0]


def test_paper_writer_prompt_uses_typed_status_and_one_shot_checkpoint_language() -> None:
    source = _read(PAPER_WRITER)

    assert "return `grd_return.status: checkpoint` and stop" in source
    assert "This is a one-shot checkpoint handoff." in source
    assert "do not wait for user input inside the current run" not in source
    assert "Use `grd_return.status: checkpoint` as the control surface." in source
    assert "The `## CHECKPOINT REACHED` heading below is presentation only." in source
    assert (
        "The markdown headings in this section, including `## SECTION DRAFTED`, `## CHECKPOINT REACHED`, and `## WRITING BLOCKED`, are presentation only."
        in source
    )
    assert "return with CHECKPOINT status" not in source
    assert "Return WRITING BLOCKED." not in source


def test_paper_writer_return_example_shows_required_base_fields_before_extensions() -> None:
    source = _read(PAPER_WRITER)
    envelope = _grd_return_block(PAPER_WRITER)

    assert "status: completed | checkpoint | blocked | failed" in envelope
    assert "files_written: [paper/sections/{section_file}.tex]" in envelope
    assert "issues: [list of issues encountered, if any]" in envelope
    assert "next_actions: [list of recommended follow-up actions]" in envelope
    assert 'section_name: "{section drafted}"' in envelope
    assert envelope.index("status: completed | checkpoint | blocked | failed") < envelope.index(
        "files_written: [paper/sections/{section_file}.tex]"
    )
    assert envelope.index("files_written: [paper/sections/{section_file}.tex]") < envelope.index(
        "issues: [list of issues encountered, if any]"
    )
    assert envelope.index("issues: [list of issues encountered, if any]") < envelope.index(
        "next_actions: [list of recommended follow-up actions]"
    )
    assert envelope.index("next_actions: [list of recommended follow-up actions]") < envelope.index(
        'section_name: "{section drafted}"'
    )
    assert "base fields (status, files_written, issues, next_actions)" not in source


def test_bibliographer_prompt_uses_typed_status_and_base_field_first_return_example() -> None:
    source = _read(BIBLIOGRAPHER)
    envelope = _grd_return_block(BIBLIOGRAPHER)

    assert "This is a one-shot checkpoint handoff: do not wait for user input inside the current run." in source
    assert "Use `grd_return.status: checkpoint` as the control surface." in source
    assert "The `## CHECKPOINT REACHED` heading below is presentation only." in source
    assert (
        "Return `grd_return.status: completed`; use a `## BIBLIOGRAPHY UPDATED` or `## CITATION ISSUES FOUND` heading only as a human-readable presentation choice."
        in source
    )
    assert (
        "Use `status: completed` when the bibliography task finished, even if the human-readable heading is `## CITATION ISSUES FOUND`"
        in source
    )
    assert "Return BIBLIOGRAPHY UPDATED or CITATION ISSUES FOUND" not in source
    assert "status: completed | checkpoint | blocked | failed" in envelope
    assert "files_written: [references/references.bib, GRD/references-status.json]" in envelope
    assert "issues: [list of citation problems, if any]" in envelope
    assert "next_actions: [list of recommended follow-up actions]" in envelope
    assert "entries_added: N" in envelope
    assert envelope.index("status: completed | checkpoint | blocked | failed") < envelope.index(
        "files_written: [references/references.bib, GRD/references-status.json]"
    )
    assert envelope.index("files_written: [references/references.bib, GRD/references-status.json]") < envelope.index(
        "issues: [list of citation problems, if any]"
    )
    assert envelope.index("issues: [list of citation problems, if any]") < envelope.index(
        "next_actions: [list of recommended follow-up actions]"
    )
    assert envelope.index("next_actions: [list of recommended follow-up actions]") < envelope.index("entries_added: N")
    assert "base fields (status, files_written, issues, next_actions)" not in source
