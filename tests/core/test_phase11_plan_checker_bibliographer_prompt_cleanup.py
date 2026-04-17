"""Focused regressions for Phase 11 plan-checker and bibliographer prompt cleanup."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_CHECKER = REPO_ROOT / "src/grd/agents/grd-plan-checker.md"
BIBLIOGRAPHER = REPO_ROOT / "src/grd/agents/grd-bibliographer.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _grd_return_block(source: str) -> str:
    return source.split("grd_return:\n", 1)[1].split("```", 1)[0]


def test_plan_checker_prompt_uses_typed_status_and_concise_presentation_language() -> None:
    source = _read(PLAN_CHECKER)
    envelope = _grd_return_block(source)

    assert "This is a one-shot handoff. If user input is needed, return `status: checkpoint`; do not wait inside the same run." in source
    assert "artifact_write_authority: read_only" in source
    assert "file_write" not in source
    assert "Headings above are presentation only. Route on `grd_return.status`, the approved/blocked plan lists, and `issues`." in source
    assert "Headings above are presentation only; route on grd_return.status." not in source
    assert "status: completed | checkpoint | blocked | failed" in envelope
    assert "files_written: []" in envelope
    assert "issues: [issue objects from Issue Format above]" in envelope
    assert "next_actions: [list of recommended follow-up actions]" in envelope
    assert "approved_plans: [list of plan IDs that passed]" in envelope
    assert "blocked_plans: [list of plan IDs needing revision or escalation]" in envelope


def test_bibliographer_prompt_uses_typed_checkpoint_language_and_shorter_heading_note() -> None:
    source = _read(BIBLIOGRAPHER)
    envelope = _grd_return_block(source)

    assert "Use `grd_return.status: checkpoint` as the control surface. The `## CHECKPOINT REACHED` heading below is presentation only." in source
    assert (
        "The headings in this section are presentation only. Route on `grd_return.status`. Use `status: completed` when the bibliography task finished, even if the human-readable heading is `## CITATION ISSUES FOUND`; use `status: checkpoint` only when researcher input is required to continue."
        in source
    )
    assert "The markdown headings in this section, including `## BIBLIOGRAPHY UPDATED`, `## CITATION ISSUES FOUND`, and `## CHECKPOINT REACHED`, are presentation only." not in source
    assert "status: completed | checkpoint | blocked | failed" in envelope
    assert "files_written: [references/references.bib, GRD/references-status.json]" in envelope
    assert "issues: [list of citation problems, if any]" in envelope
    assert "next_actions: [list of recommended follow-up actions]" in envelope
    assert "entries_added: N" in envelope
    assert "{GRD_INSTALL_DIR}/references/publication/publication-pipeline-modes.md" in source
    assert "@{GRD_INSTALL_DIR}/references/publication/publication-pipeline-modes.md" not in source
