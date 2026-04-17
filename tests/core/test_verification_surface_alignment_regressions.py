"""Regression tests for verification scaffold and workflow surface alignment."""

from __future__ import annotations

from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "src" / "grd" / "specs" / "templates"
WORKFLOWS_DIR = Path(__file__).resolve().parents[2] / "src" / "grd" / "specs" / "workflows"


def _read(relative_path: str) -> str:
    return (Path(__file__).resolve().parents[2] / relative_path).read_text(encoding="utf-8")


def test_verification_scaffolds_surface_closed_comparison_kind_enum_without_blank_placeholder() -> None:
    research_verification = _read("src/grd/specs/templates/research-verification.md")
    verify_workflow = _read("src/grd/specs/workflows/verify-work.md")

    expected_enum = "`comparison_kind`: benchmark|prior_work|experiment|cross_method|baseline|other"
    omit_instruction = "omit both `comparison_kind` and `comparison_reference_id` instead of leaving blank placeholders"
    paired_id_instruction = "omit both keys instead of leaving one blank"

    assert "Allowed body enum values:" in research_verification
    assert expected_enum in research_verification
    assert expected_enum not in verify_workflow
    assert research_verification.count(omit_instruction) == 1
    assert research_verification.count(paired_id_instruction) == 1
    assert "Update the session overlay only." in verify_workflow
    assert "The wrapper should present verifier-produced evidence exactly once per check." in verify_workflow


def test_verification_report_strict_pass_guidance_includes_reference_coverage_rules() -> None:
    verification_report = _read("src/grd/specs/templates/verification-report.md")

    assert "status: passed` is strict" in verification_report
    assert "every claim, deliverable, and acceptance_test entry in `contract_results` is `passed`" in verification_report
    assert "every reference entry is `completed`" in verification_report
    assert "every `must_surface` reference has all `required_actions` recorded in `completed_actions`" in verification_report
    assert "linked_ids: [deliverable-id, acceptance-test-id, reference-id]" in verification_report
    assert "evidence:\n        - verifier: grd-verifier" in verification_report
    assert "linked_ids: [claim-id, acceptance-test-id]" in verification_report
    assert "linked_ids: [claim-id, deliverable-id, reference-id]" in verification_report
    assert "suggested_contract_checks" in verification_report
    assert "status: passed" in verification_report


def test_verification_guidance_surfaces_the_same_canonical_suggestion_contract() -> None:
    research_verification = _read("src/grd/specs/templates/research-verification.md")
    verify_workflow = _read("src/grd/specs/workflows/verify-work.md")

    expected_suggestion = "suggested_contract_checks"

    assert expected_suggestion in research_verification
    assert expected_suggestion in verify_workflow
    assert decisive_gap_text in research_verification
    assert decisive_gap_text in verify_workflow
    assert "same canonical schema surface" in research_verification
    assert "frontmatter contract compatible with `@{GRD_INSTALL_DIR}/templates/verification-report.md`" in verify_workflow


def test_verify_work_scaffold_uses_yaml_strings_for_scalar_placeholders() -> None:
    verify_workflow = _read("src/grd/specs/workflows/verify-work.md")

    assert "Read the verifier-supplied current check from the verification file or report state." in verify_workflow
    assert "The wrapper should present verifier-produced evidence exactly once per check." in verify_workflow
    assert "Update the session overlay only. The canonical verifier verdict remains verifier-owned." in verify_workflow
    assert "one-shot delegation" in verify_workflow
    assert "summary: \"verification not started yet\"" not in verify_workflow


def test_verify_work_gap_repair_uses_explicit_stage_route_and_stays_fail_closed() -> None:
    verify_workflow = _read("src/grd/specs/workflows/verify-work.md")

    assert 'grd --raw init verify-work "${PHASE_ARG}" --stage gap_repair' in verify_workflow
    assert "Do not fall through to gap verification on the basis of preexisting `PLAN.md` files alone." in verify_workflow
    assert "skipping gap closure" not in verify_workflow


def test_model_visible_worked_examples_keep_summary_and_verdict_shapes_copy_safe() -> None:
    executor_example = _read("src/grd/specs/references/execution/executor-worked-example.md")
    verification_report = _read("src/grd/specs/templates/verification-report.md")
    verifier_prompt = _read("src/grd/agents/grd-verifier.md")

    assert "depth: full" in executor_example
    assert "completed: 2026-03-15" in executor_example
    assert "evidence:" in executor_example
    assert "verifier: grd-verifier" in executor_example
    assert 'recommended_action: "Keep the benchmark coefficient comparison explicit in the verification report."' in executor_example
    assert 'notes: "Exact pole agreement closes the decisive benchmark requirement for this claim."' in executor_example
    assert "linked_ids: [deliverable-id, acceptance-test-id, reference-id]" in verification_report
    assert "evidence:\n        - verifier: grd-verifier" in verification_report
    assert "linked_ids: [claim-id, acceptance-test-id]" in verification_report
    assert "linked_ids: [claim-id, deliverable-id, reference-id]" in verification_report
    assert "linked_ids: [deliverable-id, acceptance-test-id, reference-id]" in verifier_prompt
    assert "evidence:\n        - verifier: grd-verifier" in verifier_prompt
    assert 'recommended_action: "[what to do next]"' in verifier_prompt
    assert 'notes: "[optional context]"' in verifier_prompt


def test_research_verification_template_keeps_source_as_yaml_list() -> None:
    research_verification = _read("src/grd/specs/templates/research-verification.md")

    assert 'source:\n  - "[SUMMARY.md file validated]"' in research_verification
    assert 'source:\n  - "03-01-SUMMARY.md"\n  - "03-02-SUMMARY.md"\n  - "03-03-SUMMARY.md"' in research_verification
    assert "keep this as a YAML list even when only one SUMMARY path is present" in research_verification
    assert "source: 03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md" not in research_verification


def test_research_verification_template_keeps_contract_results_and_scalar_placeholders_copy_safe() -> None:
    research_verification = _read("src/grd/specs/templates/research-verification.md")

    assert "linked_ids: [deliverable-main, acceptance-test-main, reference-main]" in research_verification
    assert "linked_ids: [claim-main, acceptance-test-main]" in research_verification
    assert "linked_ids: [claim-main, deliverable-main, reference-main]" in research_verification
    assert "evidence:\n        - verifier: grd-verifier" in research_verification
    assert 'evidence_path: ".grd/phases/XX-name/{phase}-VERIFICATION.md"' in research_verification
    assert 'evidence_path: "[artifact path or expected evidence path]"' in research_verification
    assert 'started: "ISO timestamp"' in research_verification
    assert 'updated: "ISO timestamp"' in research_verification
    assert 'subject_id: "contract id or \\"\\""' in research_verification
    assert ".grd/phases/" not in research_verification
    assert 'evidence_path: [artifact path or expected evidence path]' not in research_verification
    assert 'started: [ISO timestamp]' not in research_verification
    assert 'updated: [ISO timestamp]' not in research_verification
    assert 'subject_id: [contract id or ""]' not in research_verification
