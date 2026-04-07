from __future__ import annotations

import json
from pathlib import Path

import anyio


def test_verification_contract_policy_text_stays_aligned_across_public_surfaces() -> None:
    from gpd.mcp.builtin_servers import build_public_descriptors
    from gpd.mcp.servers.verification_server import (
        _CONTRACT_PAYLOAD_INPUT_SCHEMA,
        _CONTRACT_SCOPE_INPUT_SCHEMA,
        mcp,
    )
    from gpd.mcp.verification_contract_policy import (
        VERIFICATION_CONTRACT_POLICY_TEXT,
        verification_server_description,
    )

    descriptors = build_public_descriptors()
    verification_descriptor = descriptors["gpd-verification"]
    tools = {tool.name: tool for tool in anyio.run(mcp.list_tools)}
    infra_descriptor = json.loads((Path(__file__).resolve().parents[2] / "infra" / "gpd-verification.json").read_text())
    repo_root = Path(__file__).resolve().parents[2]
    plan_schema = (repo_root / "src/gpd/specs/templates/plan-contract-schema.md").read_text(encoding="utf-8")
    state_schema = (repo_root / "src/gpd/specs/templates/state-json-schema.md").read_text(encoding="utf-8")

    assert _CONTRACT_PAYLOAD_INPUT_SCHEMA["description"] == VERIFICATION_CONTRACT_POLICY_TEXT
    assert verification_descriptor["description"] == verification_server_description()
    assert infra_descriptor["description"].startswith("GPD physics verification checks.")
    assert tools["run_contract_check"].description is not None
    assert tools["suggest_contract_checks"].description is not None
    assert tools["run_contract_check"].description.count(VERIFICATION_CONTRACT_POLICY_TEXT) == 1
    assert tools["suggest_contract_checks"].description.count(VERIFICATION_CONTRACT_POLICY_TEXT) == 1
    assert "request.check_key" in tools["run_contract_check"].description
    assert "supported_binding_fields" in tools["run_contract_check"].description
    assert "project_dir" in tools["run_contract_check"].description
    assert "request_template" in tools["suggest_contract_checks"].description
    assert "active_checks" in tools["suggest_contract_checks"].description
    assert "contract payload" in tools["suggest_contract_checks"].description
    conditional_anchor_rule = (
        "When `references[]` is present and no other concrete grounding exists, at least one "
        "`references[].must_surface=true` anchor is required; otherwise missing `must_surface=true` "
        "is a warning that should be repaired."
    )
    assert conditional_anchor_rule in VERIFICATION_CONTRACT_POLICY_TEXT
    assert (
        "If `references[]` is non-empty and the contract does not already carry concrete grounding elsewhere, "
        "at least one reference must set `must_surface: true`."
    ) in plan_schema
    assert "a missing `must_surface: true` reference is a warning, not a blocker" in plan_schema
    assert (
        "If a project contract has any `references[]` and does not already carry concrete prior-output, "
        "user-anchor, or baseline grounding, at least one reference must set `must_surface: true`."
    ) in state_schema
    assert "a missing `must_surface: true` reference is still a warning" in state_schema
    assert (
        "Project-scoping contracts must also provide non-empty `scope.in_scope` naming at least one concrete "
        "objective or boundary"
    ) in _CONTRACT_SCOPE_INPUT_SCHEMA["description"]
    assert "`scope.in_scope` is required and must name at least one project boundary or objective." in plan_schema
    assert "`scope.in_scope` must name at least one project boundary or objective." in state_schema
