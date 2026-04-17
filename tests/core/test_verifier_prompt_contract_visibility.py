from __future__ import annotations

import re
from pathlib import Path

from grd.adapters.install_utils import expand_at_includes
from grd.core.frontmatter import validate_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / "src/grd/agents"
TEMPLATES_DIR = REPO_ROOT / "src/grd/specs/templates"
WORKFLOWS_DIR = REPO_ROOT / "src/grd/specs/workflows"


def _read_verifier_prompt() -> str:
    return (AGENTS_DIR / "grd-verifier.md").read_text(encoding="utf-8")


def _read_verification_template() -> str:
    return (TEMPLATES_DIR / "verification-report.md").read_text(encoding="utf-8")


def _read_research_verification_template() -> str:
    return (TEMPLATES_DIR / "research-verification.md").read_text(encoding="utf-8")


def _read_verify_work_template() -> str:
    return (WORKFLOWS_DIR / "verify-work.md").read_text(encoding="utf-8")


def _read_expanded_verifier_prompt() -> str:
    return expand_at_includes(_read_verifier_prompt(), REPO_ROOT / "src/grd", "/runtime/")


def _read_example_frontmatter(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    match = re.search(r"```markdown\n(.*?)\n```", content, re.S)
    assert match is not None
    return match.group(1)


def test_verifier_prompt_points_to_canonical_verification_schema_sources() -> None:
    verifier = _read_verifier_prompt()
    expanded_verifier = _read_expanded_verifier_prompt()
    expanded_lines = expanded_verifier.splitlines()

    assert "`@{GRD_INSTALL_DIR}/templates/verification-report.md` is the canonical `VERIFICATION.md` frontmatter/body surface." in verifier
    assert "`@{GRD_INSTALL_DIR}/templates/contract-results-schema.md` is the canonical source of truth for `plan_contract_ref`, `contract_results`, `comparison_verdicts`, and verification-side `suggested_contract_checks`." in verifier
    assert "Do not invent a verifier-local schema, relax required ledgers, or treat body prose as a substitute for frontmatter consumed by validation and downstream tooling." in verifier
    assert "@{GRD_INSTALL_DIR}/templates/verification-report.md" in verifier_lines
    assert "@{GRD_INSTALL_DIR}/templates/contract-results-schema.md" in verifier_lines


def test_verifier_prompt_surfaces_validator_enforced_contract_ledger_rules() -> None:
    verifier = _read_verifier_prompt()
    contract_results_schema = (TEMPLATES_DIR / "contract-results-schema.md").read_text(encoding="utf-8")

    assert "If `contract_results` or `comparison_verdicts` are present, `plan_contract_ref` is required." in verifier
    assert "`plan_contract_ref` must be a string ending with the exact `#/contract` fragment" in verifier
    assert "`contract_results` must cover every declared claim, deliverable, acceptance test, reference, and forbidden proxy ID from the PLAN contract." in verifier
    assert "contract_results.uncertainty_markers" in verifier
    assert "Only `subject_role: decisive` satisfies a required decisive comparison or participates in pass/fail consistency checks against `contract_results`" in verifier
    assert "For reference-backed decisive comparisons, only `comparison_kind: benchmark|prior_work|experiment|baseline|cross_method` satisfies the requirement; `comparison_kind: other` does not." in verifier
    assert "`suggested_contract_checks` entries in `VERIFICATION.md` may only use `check`, `reason`, `suggested_subject_kind`, `suggested_subject_id`, and `evidence_path`." in verifier
    assert "When the gap comes from `suggest_contract_checks(contract)`, `check` must copy the returned `check_key`." in verifier
    assert "If you bind a `suggested_contract_checks` entry to a known contract target, `suggested_subject_kind` and `suggested_subject_id` must appear together; otherwise omit both." in contract_results_schema
    assert "For each suggested check, start from `request_template`" in verifier
    assert "`schema_required_request_fields`" in verifier
    assert "`schema_required_request_anyof_fields`" in verifier
    assert "satisfy one full alternative from `schema_required_request_anyof_fields`" in verifier
    assert "keep `project_dir` as the top-level absolute project root argument" in verifier
    assert "bind only `supported_binding_fields`" in verifier
    assert "Execute `run_contract_check(request=..., project_dir=...)`." in verifier
    assert "required reference actions missing" in verifier
    assert "`suggested_contract_check`" not in verifier


def test_verifier_prompt_keeps_reference_actions_within_the_canonical_enum() -> None:
    verifier = _read_verifier_prompt()

    assert "Verify the required action (`read`, `compare`, `cite`, etc.) was actually completed" in verifier
    assert "Verify the required action (`read`, `compare`, `cite`, `reproduce`, etc.) was actually completed" not in verifier


def test_verifier_prompt_loads_conventions_from_state_json_with_degraded_state_md_fallback() -> None:
    verifier = _read_verifier_prompt()

    assert "**Load conventions from `state.json` `convention_lock` first.**" in verifier
    assert "`state.json` is the machine-readable source of truth." in verifier
    assert "use `STATE.md` only as a degraded fallback" in verifier
    assert "Do NOT parse STATE.md for conventions" not in verifier


def test_verifier_prompt_reloads_the_canonical_schema_files_once() -> None:
    verifier = _read_verifier_prompt()

    assert verifier.count("templates/verification-report.md") == 1
    assert verifier.count("templates/contract-results-schema.md") == 1
    assert verifier.count("references/shared/canonical-schema-discipline.md") == 1
    assert "load the canonical schema references on demand" in verifier
    assert "from Step 2" not in verifier


def test_verifier_prompt_surfaces_schema_sources_before_the_verification_writer_section() -> None:
    verifier = _read_verifier_prompt()
    create_verification_section = verifier.index("## Create VERIFICATION.md")

    assert verifier.index("templates/verification-report.md") < create_verification_section
    assert verifier.index("templates/contract-results-schema.md") < create_verification_section
    assert verifier.index("references/shared/canonical-schema-discipline.md") < create_verification_section


def test_verifier_prompt_frontmatter_example_includes_contract_ledgers() -> None:
    verifier = _read_verifier_prompt()

    assert "plan_contract_ref: .grd/phases/{phase_number}-{phase_name}/{phase_number}-{plan}-PLAN.md#/contract" in verifier
    assert "contract_results:" in verifier
    assert "uncertainty_markers:" in verifier
    assert "comparison_verdicts:    # Required when a decisive comparison was required or attempted" in verifier
    assert "subject_kind: claim|deliverable|acceptance_test|reference" in verifier
    assert "subject_role: decisive|supporting|supplemental|other" in verifier
    assert "comparison_kind: benchmark|prior_work|experiment|cross_method|baseline|other" in verifier
    assert "weakest_anchors: [anchor-1]" in verifier
    assert "disconfirming_observations: [observation-1]" in verifier
    assert "weakest_anchors: []" not in verifier
    assert "disconfirming_observations: []" not in verifier
