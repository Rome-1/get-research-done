from __future__ import annotations

import json
from pathlib import Path

from grd.contracts import ProjectContractParseResult, ResearchContract
from grd.core import context as context_module

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "stage0"


def _load_contract_fixture() -> ResearchContract:
    payload = json.loads((FIXTURES_DIR / "project_contract.json").read_text(encoding="utf-8"))
    return ResearchContract.model_validate(payload)


def test_canonicalize_project_contract_surfaces_recoverable_salvage_findings(monkeypatch) -> None:
    contract = _load_contract_fixture()

    recovered_contract = contract.model_copy(
        update={
            "references": [
                reference.model_copy(update={"aliases": ["benchmark-anchor"]})
                if reference.id == contract.references[0].id
                else reference
                for reference in contract.references
            ]
        }
    )

    monkeypatch.setattr(
        context_module,
        "parse_project_contract_data_salvage",
        lambda payload: ProjectContractParseResult(
            contract=recovered_contract,
            recoverable_errors=["references.0.aliases must be a list, not str"],
        ),
    )

    canonical, warnings = context_module._canonicalize_project_contract(
        contract,
        active_references=[reference.model_dump(mode="json") for reference in contract.references],
        effective_reference_intake=contract.context_intake.model_dump(mode="json"),
    )

    assert canonical is not None
    assert canonical.references[0].aliases == ["benchmark-anchor"]
    assert any("canonical project_contract merge required salvage" in warning for warning in warnings)


def test_load_project_contract_blocks_raw_payload_missing_required_schema_fields(tmp_path: Path) -> None:
    planning = tmp_path / "GRD"
    planning.mkdir(parents=True, exist_ok=True)
    (planning / "phases").mkdir(exist_ok=True)
    (planning / "PROJECT.md").write_text("# Test Project\n", encoding="utf-8")
    (planning / "ROADMAP.md").write_text("# Roadmap\n", encoding="utf-8")

    state = {
        "project_contract": json.loads((FIXTURES_DIR / "project_contract.json").read_text(encoding="utf-8")),
    }
    state["project_contract"].pop("schema_version")
    (tmp_path / "GRD" / "state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    contract, load_info = context_module._load_project_contract(tmp_path)

    assert contract is None
    assert load_info["status"] == "blocked_schema"
    assert load_info["raw_project_contract_classified"] is True
    assert load_info["source_path"].endswith("GRD/state.json")
    assert "schema_version is required" in load_info["errors"]
