from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from grd import registry

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMANDS_DIR = REPO_ROOT / "src/grd/commands"
REFERENCES_DIR = REPO_ROOT / "src/grd/specs/references"
TEMPLATES_DIR = REPO_ROOT / "src/grd/specs/templates"


def _manual_model_visible_yaml_section(*, heading: str, note: str, payload: dict[str, object]) -> str:
    rendered = yaml.safe_dump(payload, sort_keys=False, allow_unicode=False).rstrip()
    return f"## {heading}\n\n{note}\n\n```yaml\n{rendered}\n```"


def _read_command(name: str) -> str:
    return Path(registry.get_command(name).path).read_text(encoding="utf-8")


def _read_workflow(name: str) -> str:
    return (WORKFLOWS_DIR / f"{name}.md").read_text(encoding="utf-8")


def test_review_grade_commands_surface_registry_contract_requirements_in_source() -> None:
    for command_name in registry.list_review_commands():
        source = _read_command(command_name)
        command = registry.get_command(command_name)
        contract = command.review_contract

        assert contract is not None
        assert f"{REVIEW_CONTRACT_FRONTMATTER_KEY}:" in source
        assert f"review_mode: {contract.review_mode}" in source

        for output in contract.required_outputs:
            assert output in source
        for evidence in contract.required_evidence:
            assert evidence in source
        for blocker in contract.blocking_conditions:
            assert blocker in source
        for check in contract.preflight_checks:
            assert check in source
        for artifact in contract.stage_artifacts:
            assert artifact in source
        for conditional in contract.conditional_requirements:
            assert conditional.when in source
            for output in conditional.required_outputs:
                assert output in source
            for evidence in conditional.required_evidence:
                assert evidence in source
            for blocker in conditional.blocking_conditions:
                assert blocker in source
            for artifact in conditional.stage_artifacts:
                assert artifact in source

        if contract.required_state:
            assert f"required_state: {contract.required_state}" in source


def test_review_contract_registry_uses_the_shared_frontmatter_key_constants() -> None:
    assert REVIEW_CONTRACT_FRONTMATTER_KEY in registry._COMMAND_FRONTMATTER_KEYS
    assert REVIEW_CONTRACT_FRONTMATTER_KEY == "review-contract"
    assert REVIEW_CONTRACT_PROMPT_WRAPPER_KEY == "review_contract"


def test_peer_review_workflow_keeps_contract_gate_prose_concise() -> None:
    workflow = _read_workflow("peer-review")
    assert "project_contract_gate.authoritative" in workflow
    assert "effective_reference_intake" in workflow
    assert "Bundle guidance" in workflow
    assert "additive only" in workflow
    assert "Reader-visible claims" in workflow
    assert "surfaced evidence" in workflow
    assert "first-class" in workflow
    assert "Apply the gate rule above." not in workflow


def test_review_grade_commands_prepend_model_visible_review_contract_to_registry_content() -> None:
    for command_name in registry.list_review_commands():
        command = registry.get_command(command_name)
        contract = command.review_contract

        assert contract is not None
        expected_section = render_review_contract_prompt(contract)
        assert command.content.startswith("## Command Requirements\n")
        assert "## Command Requirements" in command.content
        assert command_visibility_note() in command.content
        if command.requires:
            assert "requires:" in command.content
        assert "## Review Contract" in command.content
        assert expected_section in command.content
        assert f"{REVIEW_CONTRACT_PROMPT_WRAPPER_KEY}:" in command.content
        assert "wrapper key" in expected_section
        assert "schema_version" in expected_section
        assert "required_state" in expected_section
        assert "conditional_requirements" in expected_section
        assert review_contract_visibility_note() in expected_section
        assert f"review_mode: {contract.review_mode}" in expected_section
        for output in contract.required_outputs:
            assert output in expected_section
        for artifact in contract.stage_artifacts:
            assert artifact in expected_section
        for conditional in contract.conditional_requirements:
            assert conditional.when in expected_section
            for output in conditional.required_outputs:
                assert output in expected_section
            for evidence in conditional.required_evidence:
                assert evidence in expected_section
            for blocker in conditional.blocking_conditions:
                assert blocker in expected_section
            for artifact in conditional.stage_artifacts:
                assert artifact in expected_section
        if command.requires:
            for require_key, require_value in command.requires.items():
                assert str(require_key) in command.content
                if isinstance(require_value, list):
                    for item in require_value:
                        assert str(item) in command.content
                else:
                    assert str(require_value) in command.content


def test_model_visible_section_renderers_share_one_canonical_wrapper_structure() -> None:
    agent_section = registry.render_agent_requirements_section(
        tools=["git", "python"],
        commit_authority="orchestrator",
        surface="internal",
        role_family="analysis",
        artifact_write_authority="scoped_write",
        shared_state_authority="return_only",
    )
    command_section = registry.render_command_requires_section(
        context_mode="project-required",
        project_reentry_capable=False,
        agent="grd-planner",
        allowed_tools=["git", "python"],
        requires={"files": ["PROJECT.md"]},
    )
    review_contract_payload_data = normalize_review_contract_payload(
        {
            "schema_version": 1,
            "review_mode": "review",
            "preflight_checks": ["manuscript"],
        }
    )
    review_section = render_review_contract_prompt(review_contract_payload_data)

    assert agent_section == _manual_model_visible_yaml_section(
        heading="Agent Requirements",
        note=agent_visibility_note(),
        payload={
            "commit_authority": "orchestrator",
            "surface": "internal",
            "role_family": "analysis",
            "artifact_write_authority": "scoped_write",
            "shared_state_authority": "return_only",
            "tools": ["git", "python"],
        },
    )
    assert command_section == _manual_model_visible_yaml_section(
        heading="Command Requirements",
        note=command_visibility_note(),
        payload={
            "context_mode": "project-required",
            "project_reentry_capable": False,
            "agent": "grd-planner",
            "allowed_tools": ["git", "python"],
            "requires": {"files": ["PROJECT.md"]},
        },
    )
    assert review_section == _manual_model_visible_yaml_section(
        heading="Review Contract",
        note=review_contract_visibility_note(),
        payload={
            REVIEW_CONTRACT_PROMPT_WRAPPER_KEY: {
                "schema_version": 1,
                "review_mode": "review",
                "preflight_checks": ["manuscript"],
            }
        },
    )


def test_model_visible_wrapper_notes_surface_their_closed_schema_rules() -> None:
    note = review_contract_visibility_note()
    command_note = command_visibility_note()
    agent_note = agent_visibility_note()
    command_agent_labels = registry.canonical_agent_names()
    review_modes = " or ".join(f"`{value}`" for value in REVIEW_CONTRACT_MODES)
    conditional_whens = " or ".join(f"`{value}`" for value in REVIEW_CONTRACT_CONDITIONAL_WHENS)
    preflight_checks = " or ".join(f"`{value}`" for value in REVIEW_CONTRACT_PREFLIGHT_CHECKS)
    required_states = " or ".join(f"`{value}`" for value in REVIEW_CONTRACT_REQUIRED_STATES)
    agent_values = (
        *AGENT_COMMIT_AUTHORITIES,
        *AGENT_SURFACES,
        *AGENT_ROLE_FAMILIES,
        *AGENT_ARTIFACT_WRITE_AUTHORITIES,
        *AGENT_SHARED_STATE_AUTHORITIES,
    )

    assert MODEL_VISIBLE_CLOSED_SCHEMA_PHRASE in agent_note
    assert MODEL_VISIBLE_CLOSED_SCHEMA_PHRASE in command_note
    assert MODEL_VISIBLE_CLOSED_SCHEMA_PHRASE in note
    assert agent_note.count(MODEL_VISIBLE_CLOSED_SCHEMA_PHRASE) == 1
    assert command_note.count(MODEL_VISIBLE_CLOSED_SCHEMA_PHRASE) == 1
    assert note.count(MODEL_VISIBLE_CLOSED_SCHEMA_PHRASE) == 1
    assert "Empty optional fields may be omitted." in note
    assert "strict booleans" in command_note.lower()
    assert "`allowed_tools` is a list of tool names when present;" in command_note
    assert "`requires` is a closed mapping when present; only `files` is supported." in command_note
    assert "`requires.files` is a string or list of strings." in command_note
    assert "Empty optional fields may be omitted." in command_note
    for value in VALID_CONTEXT_MODES:
        assert value in command_note
    for value in command_agent_labels:
        assert value in command_note
    for value in agent_values:
        assert value in agent_note
    assert "`schema_version` must be the integer `1`" in note
    assert "context_mode" in command_note
    assert "project_reentry_capable" in command_note
    assert "may be `true` only when `context_mode` is `project-required`" in command_note

    assert "wrapper key" in note
    assert f"`review_mode` must be {review_modes}" in note
    assert f"`required_state` when present must be {required_states}" in note
    assert f"`conditional_requirements[].when` must be one of {conditional_whens}" in note
    assert f"`preflight_checks` entries must be {preflight_checks};" in note
    assert "`conditional_requirements[].blocking_preflight_checks` is a list when present" in note
    assert "appear in the top-level `preflight_checks` list." in note
    assert "Each `conditional_requirements[].when` value may appear at most once." in note
    assert "List fields reject blank entries and duplicates." in note
    assert "Each conditional requirement must declare at least one non-empty field." in note


@pytest.mark.parametrize(
    ("normalizer", "payload"),
    [
        (
            normalize_review_contract_payload,
            "schema_version: 1\nreview_mode: review\nreview_mode: publication\n",
        ),
        (
            normalize_review_contract_frontmatter_payload,
            (
                "review-contract:\n"
                "  schema_version: 1\n"
                "  review_mode: review\n"
                "  conditional_requirements:\n"
                "    - when: theorem-bearing claims are present\n"
                "      required_outputs:\n"
                "        - one\n"
                "      required_outputs:\n"
                "        - two\n"
            ),
        ),
    ],
)
def test_review_contract_normalizers_reject_duplicate_yaml_keys(normalizer, payload: str) -> None:
    with pytest.raises(ValueError, match="duplicate key"):
        normalizer(payload)


def test_review_contract_renderer_rejects_unknown_keys() -> None:
    contract = review_contract_payload(registry.get_command("write-paper").review_contract)
    assert contract is not None
    contract["unknown_field"] = "legacy drift"

    with pytest.raises(ValueError, match="Unknown review-contract field"):
        render_review_contract_prompt(contract)


def test_non_review_commands_with_requires_still_prepend_model_visible_command_requirements() -> None:
    for command_name in registry.list_commands():
        command = registry.get_command(command_name)
        if not command.requires or command.review_contract is not None:
            continue

        assert command.content.startswith("## Command Requirements\n")
        assert "requires:" in command.content
        assert command_visibility_note() in command.content
        for require_key, require_value in command.requires.items():
            assert str(require_key) in command.content
            if isinstance(require_value, list):
                for item in require_value:
                    assert str(item) in command.content
            else:
                assert str(require_value) in command.content


def test_review_contract_renderer_rejects_unknown_keys_inside_wrapped_payload() -> None:
    with pytest.raises(ValueError, match="Unknown review-contract field"):
        render_review_contract_prompt(
            {
                "review_contract": {
                    "schema_version": 1,
                    "review_mode": "review",
                    "legacy_note": "stale",
                }
            }
        )


def test_review_contract_renderer_rejects_frontmatter_wrapper_alias() -> None:
    with pytest.raises(ValueError, match="wrapper key 'review_contract'"):
        render_review_contract_prompt(
            {
                "review-contract": {
                    "schema_version": 1,
                    "review_mode": "review",
                }
            }
        )


def test_review_contract_renderer_rejects_unknown_nested_conditional_keys() -> None:
    with pytest.raises(ValueError, match=r"Unknown review-contract field\(s\): conditional_requirements\[0\]\.legacy_note"):
        render_review_contract_prompt(
            {
                "schema_version": 1,
                "review_mode": "publication",
                "conditional_requirements": [
                    {
                        "when": "theorem-bearing claims are present",
                        "legacy_note": "stale",
                    }
                ],
            }
        )


def test_review_contract_renderer_rejects_invalid_conditional_when_and_empty_payload() -> None:
    with pytest.raises(ValueError, match=r"conditional_requirements\[0\]\.when must be one of:"):
        render_review_contract_prompt(
            {
                "schema_version": 1,
                "review_mode": "publication",
                "conditional_requirements": [
                    {
                        "when": "proof-bearing work is present",
                        "required_outputs": ["GRD/review/PROOF-REDTEAM{round_suffix}.md"],
                    }
                ],
            }
        )

    with pytest.raises(
        ValueError,
        match=r"conditional_requirements\[0\] must declare at least one of:",
    ):
        render_review_contract_prompt(
            {
                "schema_version": 1,
                "review_mode": "publication",
                "conditional_requirements": [{"when": "theorem-bearing claims are present"}],
            }
        )


def test_review_contract_renderer_rejects_conflicting_wrapper_aliases_when_secondary_is_malformed() -> None:
    with pytest.raises(ValueError, match="review contract must use only one wrapper key"):
        render_review_contract_prompt(
            {
                "review_contract": {
                    "schema_version": 1,
                    "review_mode": "review",
                },
                "review-contract": "oops",
            }
        )


def test_review_contract_visibility_note_surfaces_the_hard_constraints() -> None:
    note = review_contract_visibility_note()
    review_modes = " or ".join(f"`{value}`" for value in REVIEW_CONTRACT_MODES)
    conditional_whens = " or ".join(f"`{value}`" for value in REVIEW_CONTRACT_CONDITIONAL_WHENS)
    preflight_checks = " or ".join(f"`{value}`" for value in REVIEW_CONTRACT_PREFLIGHT_CHECKS)

    assert "Closed schema; no extra keys." in note
    assert "`schema_version` must be the integer `1`;" in note
    assert f"`review_mode` must be {review_modes};" in note
    assert f"`conditional_requirements[].when` must be one of {conditional_whens};" in note
    assert "`required_state` when present must be" in note
    assert (
        "`required_outputs`, `required_evidence`, `blocking_conditions`, `preflight_checks`, and `stage_artifacts` "
        "are lists when present;"
    ) in note
    assert f"`preflight_checks` entries must be {preflight_checks};" in note
    assert "`conditional_requirements[].blocking_preflight_checks` is a list when present" in note
    assert "appear in the top-level `preflight_checks` list." in note


@pytest.mark.parametrize(
    ("normalizer", "payload", "error_fragment"),
    [
        (
            normalize_review_contract_payload,
            {
                "schema_version": 1,
                "review_mode": "publication",
                "required_outputs": "GRD/review/PROOF-REDTEAM{round_suffix}.md",
            },
            "required_outputs must be a list of strings",
        ),
        (
            normalize_review_contract_frontmatter_payload,
            {
                "review-contract": {
                    "schema_version": 1,
                    "review_mode": "publication",
                    "preflight_checks": "manuscript",
                }
            },
            "preflight_checks must be a list of strings",
        ),
        (
            normalize_review_contract_payload,
            {
                "schema_version": 1,
                "review_mode": "publication",
                "conditional_requirements": [
                    {
                        "when": "theorem-bearing claims are present",
                        "required_outputs": "GRD/review/PROOF-REDTEAM{round_suffix}.md",
                    }
                ],
            },
            "conditional_requirements[0].required_outputs must be a list of strings",
        ),
    ],
)
def test_review_contract_normalizers_reject_singleton_string_list_fields(
    normalizer,
    payload: dict[str, object],
    error_fragment: str,
) -> None:
    with pytest.raises(ValueError, match=re.escape(error_fragment)):
        normalizer(payload)


def test_review_contract_payload_elides_blank_required_state() -> None:
    payload = review_contract_payload(
        {
            "schema_version": 1,
            "review_mode": "review",
            "required_state": " ",
        }
    )

    assert payload == {"schema_version": 1, "review_mode": "review"}


@pytest.mark.parametrize(
    ("normalizer", "payload", "error_fragment"),
    [
        (
            normalize_review_contract_payload,
            {
                "schema_version": 1,
                "review_mode": "publication",
                "required_outputs": ["GRD/review/PROOF-REDTEAM{round_suffix}.md", "GRD/review/PROOF-REDTEAM{round_suffix}.md"],
            },
            "required_outputs must not contain duplicates",
        ),
        (
            normalize_review_contract_frontmatter_payload,
            {
                "review-contract": {
                    "schema_version": 1,
                    "review_mode": "publication",
                    "required_outputs": ["GRD/review/PROOF-REDTEAM{round_suffix}.md", "GRD/review/PROOF-REDTEAM{round_suffix}.md"],
                }
            },
            "required_outputs must not contain duplicates",
        ),
        (
            normalize_review_contract_payload,
            {
                "schema_version": 1,
                "review_mode": "publication",
                "preflight_checks": ["Manuscript", "manuscript"],
            },
            "preflight_checks must not contain duplicates",
        ),
        (
            normalize_review_contract_frontmatter_payload,
            {
                "review-contract": {
                    "schema_version": 1,
                    "review_mode": "publication",
                    "preflight_checks": ["Manuscript", "manuscript"],
                }
            },
            "preflight_checks must not contain duplicates",
        ),
    ],
)
def test_review_contract_normalizers_reject_duplicate_list_entries(
    normalizer,
    payload: dict[str, object],
    error_fragment: str,
) -> None:
    with pytest.raises(ValueError, match=re.escape(error_fragment)):
        normalizer(payload)


def test_review_contract_normalizer_canonicalizes_case_only_enum_drift() -> None:
    payload = {
        "schema_version": 1,
        "review_mode": "Publication",
        "preflight_checks": ["Manuscript", "Compiled_Manuscript"],
        "required_state": "PHASE_EXECUTED",
        "conditional_requirements": [
            {
                "when": "Theorem-Bearing Claims Are Present",
                "blocking_preflight_checks": ["Compiled_Manuscript"],
                "required_outputs": ["GRD/review/PROOF-REDTEAM{round_suffix}.md"],
            }
        ],
    }

    normalized = normalize_review_contract_payload(payload)
    parsed = registry._parse_review_contract(payload, "grd:test")

    assert normalized["review_mode"] == "publication"
    assert normalized["preflight_checks"] == ["manuscript", "compiled_manuscript"]
    assert normalized["required_state"] == "phase_executed"
    assert normalized["conditional_requirements"] == [
        {
            "when": "theorem-bearing claims are present",
            "required_outputs": ["GRD/review/PROOF-REDTEAM{round_suffix}.md"],
            "required_evidence": [],
            "blocking_conditions": [],
            "blocking_preflight_checks": ["compiled_manuscript"],
            "stage_artifacts": [],
        }
    ]
    assert parsed is not None
    assert dataclasses.asdict(parsed) == normalized


@pytest.mark.parametrize(
    ("payload", "error_fragment"),
    [
        (
            {
                "schema_version": 1,
                "review_mode": "publication",
                "required_outputs": "GRD/REFEREE-REPORT{round_suffix}.md",
            },
            "required_outputs must be a list of strings",
        ),
        (
            {
                "schema_version": 1,
                "review_mode": "publication",
                "preflight_checks": "manuscript",
            },
            "preflight_checks must be a list of strings",
        ),
        (
            {
                "schema_version": 1,
                "review_mode": "publication",
                "conditional_requirements": [
                    {
                        "when": "theorem-bearing claims are present",
                        "required_outputs": "GRD/review/PROOF-REDTEAM{round_suffix}.md",
                    }
                ],
            },
            "conditional_requirements[0].required_outputs must be a list of strings",
        ),
    ],
)
def test_review_contract_prompt_and_registry_reject_singleton_string_list_fields_consistently(
    payload: dict[str, object], error_fragment: str
) -> None:
    with pytest.raises(ValueError, match=re.escape(error_fragment)):
        normalize_review_contract_payload(payload)
    with pytest.raises(ValueError, match=re.escape(error_fragment)):
        registry._parse_review_contract(payload, "grd:test")


@pytest.mark.parametrize(
    ("normalizer", "payload"),
    [
        (
            normalize_review_contract_payload,
            {
                "schema_version": 1,
                "review_mode": "publication",
                "conditional_requirements": [
                    {
                        "when": "theorem-bearing claims are present",
                        "required_outputs": ["GRD/review/PROOF-REDTEAM{round_suffix}.md"],
                    },
                    {
                        "when": "theorem-bearing claims are present",
                        "required_evidence": ["duplicate activation clause"],
                    },
                ],
            },
        ),
        (
            normalize_review_contract_frontmatter_payload,
            {
                "review-contract": {
                    "schema_version": 1,
                    "review_mode": "publication",
                    "conditional_requirements": [
                        {
                            "when": "theorem-bearing claims are present",
                            "required_outputs": ["GRD/review/PROOF-REDTEAM{round_suffix}.md"],
                        },
                        {
                            "when": "theorem-bearing claims are present",
                            "required_evidence": ["duplicate activation clause"],
                        },
                    ],
                }
            },
        ),
    ],
)
def test_review_contract_normalizers_reject_duplicate_conditional_requirement_when(
    normalizer, payload: dict[str, object]
) -> None:
    with pytest.raises(
        ValueError,
        match=r"conditional_requirements\[1\]\.when duplicates conditional_requirements\[0\]\.when: theorem-bearing claims are present",
    ):
        normalizer(payload)


def test_review_contract_frontmatter_normalizer_rejects_prompt_wrapper_alias() -> None:
    with pytest.raises(ValueError, match="wrapper key 'review-contract'"):
        normalize_review_contract_frontmatter_payload(
            {
                "review_contract": {
                    "schema_version": 1,
                    "review_mode": "publication",
                }
            }
        )


@pytest.mark.parametrize(
    ("payload", "error_fragment"),
    [
        (
            {"schema_version": 1, "review_mode": "publication", "preflight_checks": ["legacy_gate"]},
            "preflight_checks",
        ),
        (
            {
                "schema_version": 1,
                "review_mode": "publication",
                "conditional_requirements": [{"when": "proof-bearing work is present"}],
            },
            "conditional_requirements[0].when",
        ),
    ],
)
def test_review_contract_prompt_and_registry_reject_the_same_invalid_payloads(
    payload: dict[str, object], error_fragment: str
) -> None:
    with pytest.raises(ValueError, match=re.escape(error_fragment)):
        normalize_review_contract_payload(payload)

    with pytest.raises(ValueError, match=re.escape(error_fragment)):
        registry._parse_review_contract(payload, "grd:test")


def test_review_contract_renderer_rejects_incomplete_payloads() -> None:
    with pytest.raises(ValueError, match="review contract must set schema_version"):
        render_review_contract_prompt({"review_mode": "review"})


def test_review_contract_renderer_rejects_empty_wrapped_payloads() -> None:
    with pytest.raises(ValueError, match="review contract must set schema_version, review_mode"):
        render_review_contract_prompt({"review_contract": {}})


def test_review_contract_renderer_rejects_explicit_null_wrapped_payloads() -> None:
    with pytest.raises(ValueError, match="review contract must set schema_version, review_mode"):
        render_review_contract_prompt({"review_contract": None})


def test_review_contract_renderer_rejects_non_integer_schema_version() -> None:
    with pytest.raises(ValueError, match="schema_version must be the integer 1"):
        render_review_contract_prompt({"schema_version": "1", "review_mode": "review"})


def test_review_contract_renderer_rejects_unknown_review_mode() -> None:
    with pytest.raises(ValueError, match="review_mode must be one of: publication, review"):
        render_review_contract_prompt({"schema_version": 1, "review_mode": "publication-review"})


def test_review_contract_renderer_rejects_unknown_preflight_checks() -> None:
    with pytest.raises(ValueError, match="preflight_checks must contain only:"):
        render_review_contract_prompt(
            {
                "schema_version": 1,
                "review_mode": "review",
                "preflight_checks": ["compiled_manuscript", "legacy_gate"],
            }
        )


def test_review_contract_renderer_always_surfaces_blocking_preflight_dependency_rule() -> None:
    section = render_review_contract_prompt({"schema_version": 1, "review_mode": "review"})

    assert review_contract_visibility_note() in section
    assert "preflight_checks: []" not in section
    assert "required_outputs: []" not in section
    assert "required_evidence: []" not in section
    assert "blocking_conditions: []" not in section
    assert "stage_artifacts: []" not in section
    assert "conditional_requirements: []" not in section
    assert "`conditional_requirements[].blocking_preflight_checks`" in section


def test_review_contract_renderer_rejects_conditional_blocking_preflight_checks_not_declared_top_level() -> None:
    with pytest.raises(
        ValueError,
        match=(
            r"conditional_requirements\[0\]\.blocking_preflight_checks must also appear in preflight_checks: "
            r"manuscript_proof_review"
        ),
    ):
        render_review_contract_prompt(
            {
                "schema_version": 1,
                "review_mode": "publication",
                "preflight_checks": ["manuscript"],
                "conditional_requirements": [
                    {
                        "when": "theorem-bearing manuscripts are present",
                        "blocking_preflight_checks": ["manuscript_proof_review"],
                    }
                ],
            }
        )


def test_review_contract_renderer_accepts_publication_artifact_preflight_checks() -> None:
    section = render_review_contract_prompt(
        {
            "schema_version": 1,
            "review_mode": "publication",
            "preflight_checks": [
                "command_context",
                "verification_reports",
                "artifact_manifest",
                "bibliography_audit",
                "bibliography_audit_clean",
                "publication_blockers",
                "reproducibility_manifest",
                "reproducibility_ready",
            ],
        }
    )

    assert "command_context" in section
    assert "verification_reports" in section
    assert "artifact_manifest" in section
    assert "bibliography_audit" in section
    assert "bibliography_audit_clean" in section
    assert "publication_blockers" in section
    assert "reproducibility_manifest" in section
    assert "reproducibility_ready" in section


def test_render_agent_requirements_section_normalizes_public_inputs() -> None:
    section = registry.render_agent_requirements_section(
        tools=["file_read", "file_read", "file_write"],
        commit_authority="orchestrator",
        surface="internal",
        role_family="analysis",
        artifact_write_authority="scoped_write",
        shared_state_authority="return_only",
    )

    assert "tools:\n- file_read\n- file_write" in section


def test_render_command_requires_section_normalizes_public_inputs() -> None:
    section = registry.render_command_requires_section(
        context_mode="project-required",
        project_reentry_capable=False,
        agent="grd-planner",
        allowed_tools=["git", "git", "python"],
        requires={"files": ["PROJECT.md", "PROJECT.md"]},
    )

    assert "allowed_tools:\n- git\n- python" in section
    assert "files:\n  - PROJECT.md" in section


@pytest.mark.parametrize(
    ("kwargs", "error_fragment"),
    [
        (
            {
                "context_mode": "project-aware",
                "project_reentry_capable": True,
                "agent": None,
                "allowed_tools": [],
                "requires": {},
            },
            "requires context_mode 'project-required'",
        ),
        (
            {
                "context_mode": "project-required",
                "project_reentry_capable": False,
                "agent": "execute-phase",
                "allowed_tools": [],
                "requires": {},
            },
            "Unknown agent",
        ),
        (
            {
                "context_mode": "project-required",
                "project_reentry_capable": False,
                "agent": None,
                "allowed_tools": [],
                "requires": {"artifact_manifest": "required"},
            },
            "only supports files",
        ),
    ],
)
def test_render_command_requires_section_rejects_invalid_public_inputs(
    kwargs: dict[str, object],
    error_fragment: str,
) -> None:
    with pytest.raises(ValueError, match=re.escape(error_fragment)):
        registry.render_command_requires_section(**kwargs)


def test_render_agent_requirements_section_rejects_invalid_public_inputs() -> None:
    with pytest.raises(ValueError, match="Invalid role_family"):
        registry.render_agent_requirements_section(
            tools=["file_read"],
            commit_authority="orchestrator",
            surface="internal",
            role_family="planner",
            artifact_write_authority="scoped_write",
            shared_state_authority="return_only",
        )


def test_review_contract_renderer_rejects_invalid_required_state_field() -> None:
    with pytest.raises(ValueError, match="required_state must be one of: phase_executed"):
        render_review_contract_prompt(
            {
                "schema_version": 1,
                "review_mode": "review",
                "required_state": "phase_planned",
            }
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "stage_ids",
        "final_decision_output",
        "requires_fresh_context_per_stage",
        "max_review_rounds",
    ],
)
def test_review_contract_renderer_rejects_removed_dead_review_fields(field_name: str) -> None:
    with pytest.raises(ValueError, match=r"Unknown review-contract field\(s\):"):
        render_review_contract_prompt(
            {
                "schema_version": 1,
                "review_mode": "review",
                field_name: "legacy-value",
            }
        )


def test_review_contract_renderer_normalizes_blank_required_state() -> None:
    section = render_review_contract_prompt(
        {
            "schema_version": 1,
            "review_mode": "review",
            "required_state": "   ",
        }
    )

    assert "required_state: ''" not in section


def test_review_contract_renderer_surfaces_required_state_constraint_in_note() -> None:
    section = render_review_contract_prompt(
        {
            "schema_version": 1,
            "review_mode": "review",
            "required_state": REVIEW_CONTRACT_REQUIRED_STATES[0],
        }
    )

    assert "required_state: phase_executed" in section
    assert "required_state" in section


def test_review_contract_renderer_rejects_non_list_and_non_mapping_conditional_shapes() -> None:
    with pytest.raises(ValueError, match="conditional_requirements must be a list of mappings"):
        render_review_contract_prompt(
            {
                "schema_version": 1,
                "review_mode": "publication",
                "conditional_requirements": True,
            }
        )

    with pytest.raises(ValueError, match=r"conditional_requirements\[0\] must be a mapping"):
        render_review_contract_prompt(
            {
                "schema_version": 1,
                "review_mode": "publication",
                "conditional_requirements": ["oops"],
            }
        )


def test_review_contract_renderer_fills_canonical_defaults_for_minimal_payload() -> None:
    section = render_review_contract_prompt({"schema_version": 1, "review_mode": "review"})

    assert "required_outputs: []" not in section
    assert "required_evidence: []" not in section
    assert "blocking_conditions: []" not in section
    assert "preflight_checks: []" not in section
    assert "stage_artifacts: []" not in section
    assert "conditional_requirements: []" not in section
    assert "required_state:" not in section
    assert "stage_ids" not in section
    assert "final_decision_output" not in section
    assert "requires_fresh_context_per_stage" not in section
    assert "max_review_rounds" not in section


def test_review_contract_renderer_renders_conditional_requirements() -> None:
    section = render_review_contract_prompt(
        {
            "schema_version": 1,
            "review_mode": "publication",
            "preflight_checks": ["manuscript_proof_review"],
            "conditional_requirements": [
                {
                    "when": "theorem-bearing claims are present",
                    "required_outputs": ["GRD/review/PROOF-REDTEAM{round_suffix}.md"],
                    "blocking_preflight_checks": ["manuscript_proof_review"],
                    "stage_artifacts": ["GRD/review/PROOF-REDTEAM{round_suffix}.md"],
                }
            ],
        }
    )

    assert "conditional_requirements:" in section
    assert "- when: theorem-bearing claims are present" in section
    assert "required_outputs:" in section
    assert "required_evidence: []" not in section
    assert "blocking_conditions: []" not in section
    assert "blocking_preflight_checks:" in section
    assert "stage_artifacts:" in section
    assert "GRD/review/PROOF-REDTEAM{round_suffix}.md" in section


def test_peer_review_contract_surfaces_typed_conditional_proof_requirements() -> None:
    contract = registry.get_command("peer-review").review_contract

    assert contract is not None
    assert contract.conditional_requirements == [
        registry.ReviewContractConditionalRequirement(
            when="theorem-bearing claims are present",
            required_outputs=["GRD/review/PROOF-REDTEAM{round_suffix}.md"],
            stage_artifacts=["GRD/review/PROOF-REDTEAM{round_suffix}.md"],
        )
    ]
    source = _read_command("peer-review")
    assert "conditional_requirements:" in source
    assert "when: theorem-bearing claims are present" in source


def test_verify_work_review_contract_uses_phase_scoped_output_path() -> None:
    contract = registry.get_command("verify-work").review_contract

    assert contract is not None
    assert contract.required_outputs == [".grd/phases/XX-name/XX-VERIFICATION.md"]
    assert ".grd/phases/XX-name/XX-VERIFICATION.md" in _read_command("verify-work")


def test_respond_to_referees_review_contract_uses_round_suffixed_output_paths() -> None:
    contract = registry.get_command("respond-to-referees").review_contract

    assert contract is not None
    assert contract.required_outputs == [
        ".grd/paper/REFEREE_RESPONSE{round_suffix}.md",
        ".grd/AUTHOR-RESPONSE{round_suffix}.md",
    ]
    assert ".grd/paper/REFEREE_RESPONSE{round_suffix}.md" in _read_command("respond-to-referees")
    assert ".grd/AUTHOR-RESPONSE{round_suffix}.md" in _read_command("respond-to-referees")


def test_write_paper_review_contract_uses_round_suffixed_referee_outputs() -> None:
    contract = registry.get_command("write-paper").review_contract

    assert contract is not None
    assert contract.required_outputs == [
        "paper/main.tex",
        ".grd/REFEREE-REPORT{round_suffix}.md",
        ".grd/REFEREE-REPORT{round_suffix}.tex",
    ]
    assert ".grd/REFEREE-REPORT{round_suffix}.md" in _read_command("write-paper")
    assert ".grd/REFEREE-REPORT{round_suffix}.tex" in _read_command("write-paper")


def test_summary_template_surfaces_plan_contract_ref_rule_for_contract_ledgers() -> None:
    summary_template = (TEMPLATES_DIR / "summary.md").read_text(encoding="utf-8")
    contract_results_schema = (TEMPLATES_DIR / "contract-results-schema.md").read_text(encoding="utf-8")

    assert "If `contract_results` or `comparison_verdicts` are present, `plan_contract_ref` is also required." in summary_template
    assert "plan_contract_ref (required when `contract_results` or `comparison_verdicts` are present)" in summary_template
    assert "Reload `@{GRD_INSTALL_DIR}/templates/contract-results-schema.md` immediately before writing the YAML" in summary_template
    assert "canonical project-root-relative `.grd/phases/XX-name/{phase}-{plan}-PLAN.md#/contract` path" in summary_template
    assert "Choose the depth explicitly" in summary_template
    assert "default: full" not in summary_template
    assert "Keep `uncertainty_markers` explicit and user-visible" in summary_template
    assert "uncertainty_markers:" in summary_template
    assert "weakest_anchors: [anchor-1]" in summary_template
    assert "disconfirming_observations: [observation-1]" in summary_template
    assert "For contract-backed summaries, `contract_results` is required" in summary_template
    assert "It must not be absolute, parent-traversing, or collapse to a bare sibling reference." in summary_template
    assert "`completed` needs non-empty `completed_actions`" in summary_template
    assert "If a decisive external anchor was used, include `reference_id`" in summary_template
    assert "Do not invent extra keys in `contract_results`, `comparison_verdicts`, or `suggested_contract_checks`" in summary_template


def test_verification_template_surfaces_strict_passed_and_blocked_semantics() -> None:
    verification_template = (TEMPLATES_DIR / "verification-report.md").read_text(encoding="utf-8")

    assert "status: passed` is strict" in verification_template
    assert "every claim, deliverable, and acceptance_test entry in `contract_results` is `passed`" in verification_template
    assert "If any contract target is `partial`, `failed`, `blocked`, `missing`, or `unresolved`, use `gaps_found`, `expert_needed`, or `human_needed` instead of `passed`." in verification_template
    assert "every reference entry is `completed`" in verification_template
    assert "every `must_surface` reference has all `required_actions` recorded in `completed_actions`" in verification_template
    assert "Reload `@{GRD_INSTALL_DIR}/templates/contract-results-schema.md` immediately before writing the YAML" in verification_template
    assert "verification-side `suggested_contract_checks`" in verification_template
    assert "same canonical schema surface as the rest of the verification ledger" in verification_template
    assert "uncertainty_markers:" in verification_template
    assert "weakest_anchors: [anchor-1]" in verification_template
    assert "disconfirming_observations: [observation-1]" in verification_template


def test_research_verification_template_surfaces_non_empty_uncertainty_markers() -> None:
    research_verification = (TEMPLATES_DIR / "research-verification.md").read_text(encoding="utf-8")

    assert "Use `@{GRD_INSTALL_DIR}/templates/verification-report.md` for the canonical verification frontmatter contract." in research_verification
    assert "verification-side `suggested_contract_checks` entries are part of the same canonical schema surface" in research_verification
    assert "comparison_kind: benchmark" in research_verification
    assert "Allowed body enum values:" in research_verification
    assert "`comparison_kind`: benchmark|prior_work|experiment|cross_method|baseline|other" in research_verification
    assert "comparison_kind: [benchmark | prior_work | experiment | cross_method | baseline | other]" not in research_verification
    assert "comparison_kind: [benchmark | prior_work | experiment | cross_method | baseline | other | \"\"]" not in research_verification
    assert 'comparison_kind: "benchmark"' in research_verification
    assert 'comparison_kind: "benchmark | prior_work | experiment | cross_method | baseline | other"' not in research_verification
    assert "omit both `comparison_kind` and `comparison_reference_id` instead of leaving blank placeholders" in research_verification
    assert "uncertainty_markers:" in research_verification
    assert "weakest_anchors: [anchor-1]" in research_verification
    assert "disconfirming_observations: [observation-1]" in research_verification


def test_write_paper_prompt_discovers_plan_scoped_phase_summaries() -> None:
    source = _read_workflow("write-paper")

    assert "ls .grd/phases/*/*SUMMARY.md 2>/dev/null" in source


def test_write_paper_prompt_loads_figure_tracker_schema_before_updating_tracker() -> None:
    source = _read_workflow("write-paper")
    staging = registry.get_command("write-paper").staged_loading

    assert staging is not None

    assert "@{GRD_INSTALL_DIR}/templates/paper/figure-tracker.md" in source
    assert ".grd/paper/FIGURE_TRACKER.md" in source
    assert "canonical schema/template surfaces it loads there" in source


def test_comparison_templates_match_full_comparison_verdict_subject_kind_enum() -> None:
    internal = (TEMPLATES_DIR / "paper" / "internal-comparison.md").read_text(encoding="utf-8")
    experimental = (TEMPLATES_DIR / "paper" / "experimental-comparison.md").read_text(encoding="utf-8")
    contract_results = (TEMPLATES_DIR / "contract-results-schema.md").read_text(encoding="utf-8")

    assert "subject_kind: claim|deliverable|acceptance_test|reference" not in internal
    assert "subject_kind: claim|deliverable|acceptance_test|reference" not in experimental
    assert "comparison_kind: benchmark|prior_work|experiment|cross_method|baseline|other" not in internal
    assert "comparison_kind: benchmark|prior_work|experiment|cross_method|baseline|other" not in experimental
    assert "subject_kind: claim" in internal
    assert "subject_kind: claim" in experimental
    assert "comparison_kind: cross_method" in internal
    assert "comparison_kind: experiment" in experimental
    assert "comparison_kind: benchmark|prior_work|experiment|cross_method|baseline|other" in contract_results
    assert "uncertainty_markers:" in contract_results
    assert "weakest_anchors: [anchor-1]" in contract_results
    assert "disconfirming_observations: [observation-1]" in contract_results
    assert "Only `subject_role: decisive` closes a decisive requirement" in internal
    assert "Only `subject_role: decisive` closes a decisive requirement" in experimental
    assert "Must be the canonical project-root-relative `.grd/phases/XX-name/XX-YY-PLAN.md#/contract` path" in contract_results


def test_contract_ledgers_surface_decisive_only_verdict_rules_and_strict_suggested_check_keys() -> None:
    contract_results = (TEMPLATES_DIR / "contract-results-schema.md").read_text(encoding="utf-8")
    verification_template = (TEMPLATES_DIR / "verification-report.md").read_text(encoding="utf-8")

    assert "Do not invent `artifact` or `other` subject kinds" in contract_results
    assert "Only `subject_role: decisive` satisfies a required decisive comparison" in contract_results
    assert "`subject_role` must be explicit on every verdict" in contract_results
    assert "canonical project-root-relative `.grd/phases/XX-name/XX-YY-PLAN.md#/contract` path" in contract_results
    assert "If a decisive external anchor was used, include `reference_id`" in contract_results
    assert "reference-backed decisive comparison is required" in contract_results
    assert "acceptance test with `kind: benchmark` or `kind: cross_method`" in contract_results
    assert "`contract_results` and every nested entry use a closed schema" in contract_results
    assert "uncertainty_markers:" in contract_results
    assert "weakest_anchors: [anchor-1]" in contract_results
    assert "disconfirming_observations: [observation-1]" in contract_results
    assert "Invented keys such as `check_id` fail validation." in contract_results
    assert "Copy the `check_key` returned by `suggest_contract_checks(contract)` into the frontmatter `check` field" in contract_results
    assert "comparison_verdicts" in verification_template
    assert "suggested_contract_checks" in verification_template


def test_contract_ledgers_surface_forbidden_proxy_bindings_and_action_vocabulary() -> None:
    summary_template = (TEMPLATES_DIR / "summary.md").read_text(encoding="utf-8")
    contract_results = (TEMPLATES_DIR / "contract-results-schema.md").read_text(encoding="utf-8")
    state_schema = (TEMPLATES_DIR / "state-json-schema.md").read_text(encoding="utf-8")

    assert "single detailed rule source" in summary_template
    assert "contract_results" in summary_template
    assert "comparison_verdicts" in summary_template
    assert "legacy frontmatter aliases" in summary_template.lower()
    assert "forbidden_proxy_id" in contract_results
    assert "closed action vocabulary: `read`, `use`, `compare`, `cite`, `avoid`" in contract_results
    assert "Blank-after-trim entries are invalid" in contract_results
    assert "duplicate-after-trim entries are invalid" in contract_results
    assert "weakest_anchors: [anchor-1]" in contract_results
    assert "disconfirming_observations: [observation-1]" in contract_results
    assert "uncertainty_markers.weakest_anchors" in state_schema
    assert "uncertainty_markers.disconfirming_observations" in state_schema
    assert "`.grd/phases/.../*-SUMMARY.md` or `paper/main.tex`" in state_schema
    assert "`.grd/phases/.../SUMMARY.md`" not in state_schema


def test_prompt_visible_contracts_surface_literal_boolean_requirements() -> None:
    plan_schema = (TEMPLATES_DIR / "plan-contract-schema.md").read_text(encoding="utf-8")
    review_reader = (AGENTS_DIR / "grd-review-reader.md").read_text(encoding="utf-8")
    panel = (REFERENCES_DIR / "publication" / "peer-review-panel.md").read_text(encoding="utf-8")

    assert "`required_in_proof` must be a literal JSON boolean (`true` or `false`)" in plan_schema
    assert "not a quoted string or synonym such as `\"yes\"` / `\"no\"`" in plan_schema
    assert "{GRD_INSTALL_DIR}/references/publication/peer-review-panel.md" in review_reader
    assert "shared source of truth for the full `ClaimIndex` and `StageReviewReport` contracts" in review_reader
    assert "`blocking` in each finding must be a literal JSON boolean (`true` or `false`)" in panel
    assert "not a quoted string or synonym such as `\"yes\"` / `\"no\"`" in panel


def test_referee_schema_and_panel_surface_strict_stage_artifact_naming_and_round_suffix_rules() -> None:
    referee_schema = (TEMPLATES_DIR / "paper" / "referee-decision-schema.md").read_text(encoding="utf-8")
    review_ledger_schema = (TEMPLATES_DIR / "paper" / "review-ledger-schema.md").read_text(encoding="utf-8")
    panel = (REFERENCES_DIR / "publication" / "peer-review-panel.md").read_text(encoding="utf-8")
    review_math = (AGENTS_DIR / "grd-review-math.md").read_text(encoding="utf-8")

    assert ".grd/review/REFEREE-DECISION{round_suffix}.json" in referee_schema
    assert ".grd/REFEREE-REPORT{round_suffix}.md" in referee_schema
    assert "REVIEW-LEDGER{round_suffix}.json" in referee_schema
    assert "STAGE-(reader|literature|math|physics|interestingness)(-R<round>)?.json" in referee_schema
    assert "same optional `-R<round>` suffix" in referee_schema
    assert "`{round_suffix}` in path examples means empty for initial review and `-R<round>`" in referee_schema
    assert ".grd/review/REVIEW-LEDGER{round_suffix}.json" in review_ledger_schema
    assert "`manuscript_path` must be non-empty" in review_ledger_schema
    assert "REFEREE-DECISION{round_suffix}.json" in review_ledger_schema
    assert ".grd/review/CLAIMS{round_suffix}.json" in panel
    assert ".grd/review/STAGE-reader{round_suffix}.json" in panel
    assert "Strict-stage specialist artifacts must use canonical names `STAGE-reader`, `STAGE-literature`, `STAGE-math`, `STAGE-physics`, `STAGE-interestingness`." in panel
    assert "all five must share the same optional `-R<round>` suffix." in panel
    assert "every theorem-bearing Stage 1 claim must be reviewed and proof-audited" in panel
    assert "every theorem-bearing Stage 1 claim must be reviewed and proof-audited" in review_math


def test_executor_completion_reference_requires_loading_contract_schema_before_summary_frontmatter() -> None:
    completion = (REFERENCES_DIR / "execution" / "executor-completion.md").read_text(encoding="utf-8")

    assert "Canonical ledger schema to load before writing SUMMARY frontmatter:" in completion
    assert "@{GRD_INSTALL_DIR}/templates/contract-results-schema.md" in completion
