"""Tests for ``grd lean render-proof`` (ge-epra / P3-1).

The renderer is a heuristic reviewability tool, so these tests check the
shape of the output — key narrative phrases, presence of tactic scripts,
warnings on ``sorry`` — rather than an exact string match. The CLI tests
exercise the end-to-end contract through the typer runner.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from grd.cli import app
from grd.cli.lean import EXIT_INPUT_ERROR
from grd.core.lean.render_proof import (
    RenderProofResult,
    extract_theorems,
    render_proof,
)

runner = CliRunner()


SAMPLE_PROOF = """\
theorem add_zero (n : Nat) : n + 0 = n := by
  induction n with
  | zero => rfl
  | succ k ih =>
    simp [Nat.add_succ]
    exact congrArg Nat.succ ih

lemma and_comm (p q : Prop) : p ∧ q → q ∧ p := by
  intro h
  cases h with
  | intro hp hq => exact ⟨hq, hp⟩

example : 1 + 1 = 2 := rfl
"""


SAMPLE_SORRY = """\
theorem todo (n : Nat) : n = n := by
  sorry
"""


# ─── extract_theorems ───────────────────────────────────────────────────────


def test_extract_theorems_finds_all_declarations() -> None:
    blocks = extract_theorems(SAMPLE_PROOF)
    kinds = [b.kind for b in blocks]
    names = [b.name for b in blocks]
    assert "theorem" in kinds and "lemma" in kinds and "example" in kinds
    assert "add_zero" in names and "and_comm" in names


def test_extract_theorems_labels_proof_mode() -> None:
    blocks = extract_theorems(SAMPLE_PROOF)
    by_name = {b.name: b for b in blocks}
    assert by_name["add_zero"].proof_mode == "tactic"
    assert by_name["and_comm"].proof_mode == "tactic"
    # The anonymous example has an empty name but is term-mode (`:= rfl`).
    examples = [b for b in blocks if b.kind == "example"]
    assert examples and examples[0].proof_mode == "term"


def test_extract_theorems_nests_match_alternatives() -> None:
    blocks = extract_theorems(SAMPLE_PROOF)
    add_zero = next(b for b in blocks if b.name == "add_zero")
    # The top step is the `induction` tactic; its sub_steps are the `| pat`
    # match alternatives. This is the "million-line proof becomes readable"
    # property — match cases must be grouped under their driver tactic.
    assert len(add_zero.steps) == 1
    induction_step = add_zero.steps[0]
    assert "induction" in induction_step.narrative.lower()
    assert len(induction_step.sub_steps) == 2
    zero_case = induction_step.sub_steps[0]
    succ_case = induction_step.sub_steps[1]
    assert "zero" in zero_case.narrative
    assert "succ" in succ_case.narrative
    # The succ case's body (simp, exact) nests one level deeper.
    assert [ss.tactic.split()[0] for ss in succ_case.sub_steps] == ["simp", "exact"]


def test_extract_theorems_warns_on_sorry() -> None:
    blocks = extract_theorems(SAMPLE_SORRY)
    assert len(blocks) == 1
    warnings = blocks[0].warnings
    assert any("sorry" in warning for warning in warnings)


def test_extract_theorems_handles_block_comments() -> None:
    source = """\
/- a block comment with := inside that must not
   be mistaken for the real assignment -/
theorem t : 1 = 1 := by rfl
"""
    blocks = extract_theorems(source)
    assert len(blocks) == 1
    assert blocks[0].name == "t"
    assert blocks[0].proof_mode == "tactic"


def test_extract_theorems_handles_line_comments() -> None:
    source = """\
theorem t : 1 = 1 := by
  rfl -- the easy case
"""
    blocks = extract_theorems(source)
    assert len(blocks) == 1
    assert blocks[0].steps
    assert "reflexivity" in blocks[0].steps[0].narrative.lower()


# ─── render_proof (markdown/latex) ──────────────────────────────────────────


def test_render_proof_markdown_includes_signature_narrative_and_script() -> None:
    result = render_proof(SAMPLE_PROOF, format="markdown")
    rendered = result.combined_narrative
    # Signature block and tactic script are both surfaced verbatim.
    assert "theorem add_zero" in rendered
    assert "```lean" in rendered
    # Narrative prose appears alongside the raw tactic.
    assert "Proceed by induction" in rendered
    # Bullet/ordinal numbering is present so reviewers can refer to steps.
    assert "\n1." in rendered


def test_render_proof_markdown_labels_incomplete_proof() -> None:
    result = render_proof(SAMPLE_SORRY, format="markdown")
    rendered = result.combined_narrative
    assert "sorry" in rendered.lower()
    assert "Gap" in rendered or "incomplete" in rendered


def test_render_proof_latex_emits_valid_environment_pairs() -> None:
    result = render_proof(SAMPLE_PROOF, format="latex")
    rendered = result.combined_narrative
    # Every begin has a matching end (structural sanity — not a compile).
    for env in ("verbatim", "enumerate"):
        assert rendered.count(f"\\begin{{{env}}}") == rendered.count(f"\\end{{{env}}}")
    # Markdown-ish styling from the narrative is translated, not leaked.
    assert "**" not in rendered


def test_render_proof_theorem_filter_narrows_output() -> None:
    result = render_proof(SAMPLE_PROOF, theorem="and_comm", format="markdown")
    assert len(result.theorems) == 1
    assert result.theorems[0].theorem.name == "and_comm"
    # The skipped list surfaces what was filtered out so callers can report it.
    assert "add_zero" in result.skipped


def test_render_proof_missing_theorem_filter_records_warning() -> None:
    result = render_proof(SAMPLE_PROOF, theorem="nope", format="markdown")
    assert result.theorems == []
    assert any("nope" in warning for warning in result.warnings)


def test_render_proof_empty_file_reports_no_declarations() -> None:
    result = render_proof("-- just a comment\n", format="markdown")
    assert result.theorems == []
    assert any("no theorem" in warning.lower() for warning in result.warnings)


# ─── CLI surface ────────────────────────────────────────────────────────────


def test_cli_render_proof_markdown_roundtrip(tmp_path: Path) -> None:
    lean_file = tmp_path / "sample.lean"
    lean_file.write_text(SAMPLE_PROOF, encoding="utf-8")
    result = runner.invoke(app, ["--cwd", str(tmp_path), "lean", "render-proof", str(lean_file)])
    assert result.exit_code == 0, result.stdout
    assert "theorem add_zero" in result.stdout
    assert "Proceed by induction" in result.stdout


def test_cli_render_proof_raw_emits_structured_json(tmp_path: Path) -> None:
    lean_file = tmp_path / "sample.lean"
    lean_file.write_text(SAMPLE_PROOF, encoding="utf-8")
    result = runner.invoke(
        app,
        ["--raw", "--cwd", str(tmp_path), "lean", "render-proof", str(lean_file), "--format", "json"],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed["format"] == "json"
    names = [rendered["theorem"]["name"] for rendered in parsed["theorems"]]
    assert "add_zero" in names and "and_comm" in names


def test_cli_render_proof_writes_output_file(tmp_path: Path) -> None:
    lean_file = tmp_path / "sample.lean"
    lean_file.write_text(SAMPLE_PROOF, encoding="utf-8")
    out_file = tmp_path / "narrative.md"
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "lean",
            "render-proof",
            str(lean_file),
            "--output",
            str(out_file),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert out_file.exists()
    body = out_file.read_text(encoding="utf-8")
    assert "theorem add_zero" in body


def test_cli_render_proof_rejects_unknown_format(tmp_path: Path) -> None:
    lean_file = tmp_path / "sample.lean"
    lean_file.write_text(SAMPLE_PROOF, encoding="utf-8")
    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "lean", "render-proof", str(lean_file), "--format", "html"],
    )
    assert result.exit_code == EXIT_INPUT_ERROR


def test_cli_render_proof_missing_file_errors(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "lean", "render-proof", str(tmp_path / "nope.lean")],
    )
    assert result.exit_code == EXIT_INPUT_ERROR


def test_render_proof_result_has_stable_shape() -> None:
    result = render_proof(SAMPLE_PROOF, format="json")
    assert isinstance(result, RenderProofResult)
    dumped = result.model_dump(mode="json")
    # The CLI --raw contract depends on these top-level keys.
    assert set(dumped.keys()) >= {"source_path", "format", "theorems", "warnings"}
