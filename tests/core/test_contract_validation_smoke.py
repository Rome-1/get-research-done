"""Focused smoke coverage for project-contract validation invariants."""

from __future__ import annotations

import json
from pathlib import Path

from gpd.core.contract_validation import validate_project_contract

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "stage0"


def _load_contract_fixture() -> dict[str, object]:
    return json.loads((FIXTURES_DIR / "project_contract.json").read_text(encoding="utf-8"))


def test_validate_project_contract_smoke_rejects_coercive_schema_version_scalar() -> None:
    contract = _load_contract_fixture()
    contract["schema_version"] = True

    result = validate_project_contract(contract)

    assert result.valid is False
    assert result.errors == ["schema_version must be the integer 1"]
    assert result.warnings == []


def test_validate_project_contract_smoke_rejects_coercive_reference_must_surface_scalar() -> None:
    contract = _load_contract_fixture()
    contract["references"][0]["must_surface"] = "yes"

    result = validate_project_contract(contract)

    assert result.valid is False
    assert "references.0.must_surface must be a boolean" in result.errors
    assert "references.0.must_surface: Value error, must be a boolean" in result.errors
    assert not any("unknown reference" in issue for issue in result.errors + result.warnings)
    assert not any(
        "must include at least one must_surface=true anchor" in issue for issue in result.errors + result.warnings
    )

