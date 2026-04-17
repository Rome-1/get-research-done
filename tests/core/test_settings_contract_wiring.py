"""Prompt/spec regressions for settings and project-contract wiring."""

from __future__ import annotations

from pathlib import Path

from grd.adapters.install_utils import expand_at_includes

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / "src/grd/specs/workflows"
COMMANDS_DIR = REPO_ROOT / "src/grd/commands"
REFERENCES_DIR = REPO_ROOT / "src/grd/specs/references"
TEMPLATES_DIR = REPO_ROOT / "src/grd/specs/templates"


def test_new_project_minimal_contract_guidance_surfaces_contract_enum_vocabulary() -> None:
    workflow_text = (WORKFLOWS_DIR / "new-project.md").read_text(encoding="utf-8")

    assert "`observables[].kind`: `scalar | curve | map | classification | proof_obligation | other`" in workflow_text
    assert "`acceptance_tests[].automation`: `automated | hybrid | human`" in workflow_text
    assert (
        "`references[].role`: `definition | benchmark | method | must_consider | background | other`" in workflow_text
    )
    assert (
        "`links[].relation`: `supports | computes | visualizes | benchmarks | depends_on | evaluated_by | other`"
        in workflow_text
    )
    assert (
        "do **not** invent near-miss enum values such as `anchor`, `manual`, `content-check`, `benchmark-record`, or `anchors`"
        in workflow_text
    )

    assert "templates/project-contract-schema.md" in workflow_text
    assert "templates/state-json-schema.md" not in workflow_text
    assert "use that schema as the canonical source of truth for the object rules" in workflow_text
    assert "Do not restate the full contract rules here; keep only the approval-critical reminders below." in workflow_text
    assert '`observables[]` — `{ "id", "name", "kind", "definition", "regime?", "units?" }`' in project_contract_schema_text
    assert '`acceptance_tests[]` — `{ "id", "subject", "kind", "procedure", "pass_condition", "evidence_required[]", "automation" }`' in project_contract_schema_text
    assert '`references[]` — `{ "id", "kind", "locator", "aliases[]", "role", "why_it_matters", "applies_to[]", "carry_forward_to[]", "must_surface": true|false, "required_actions[]" }`' in project_contract_schema_text
    assert '`links[]` — `{ "id", "source", "target", "relation", "verified_by[]" }`' in project_contract_schema_text
    assert "`claims[].claim_kind` must use the closed vocabulary: `theorem | lemma | corollary | proposition | result | claim | other`." in project_contract_schema_text
    assert "`required_actions[]` uses the same closed action vocabulary enforced downstream in contract ledgers: `read`, `use`, `compare`, `cite`, `avoid`." in project_contract_schema_text
    assert (
        "if `references[].must_surface` is `true`, both `references[].applies_to[]` and "
        "`references[].required_actions[]` must be non-empty"
    ) not in workflow_text
    assert "If a project-contract reference sets `must_surface: true`, `required_actions[]` must not be empty." in project_contract_schema_text
    assert "If a project-contract reference sets `must_surface: true`, `applies_to[]` must not be empty." in project_contract_schema_text


def test_settings_and_planning_config_keep_conventions_outside_config_json() -> None:
    settings_command = (COMMANDS_DIR / "settings.md").read_text(encoding="utf-8")
    settings_workflow = (WORKFLOWS_DIR / "settings.md").read_text(encoding="utf-8")
    planning_config = (REFERENCES_DIR / "planning" / "planning-config.md").read_text(encoding="utf-8")
    new_project = (WORKFLOWS_DIR / "new-project.md").read_text(encoding="utf-8")

    assert "physics research preferences" not in settings_command
    assert "physics-specific settings" not in settings_workflow
    assert "Project conventions do **not** live in `.grd/config.json`." in settings_workflow
    assert (
        "Project conventions still live in `.grd/CONVENTIONS.md` and `.grd/state.json` (`convention_lock`)"
        in settings_workflow
    )
    assert '"physics": {' not in planning_config
    assert "Project conventions are not part of `config.json`." in planning_config
    assert "Do **not** introduce a `physics` block there." in planning_config
    assert (
        "The user can run `grd convention set ...` or `/grd:validate-conventions` later to complete convention setup."
        in new_project
    )
