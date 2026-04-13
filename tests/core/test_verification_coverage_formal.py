"""Tests for formal proof coverage aggregation (checks 5.20 / 5.21)."""

from __future__ import annotations

import pytest

from grd.core.verification_coverage import (
    FORMAL_PROOF_METHODS,
    FORMAL_STATEMENT_METHODS,
    collect_verification_records_from_state,
    formal_proof_coverage_from_records,
    formal_proof_coverage_from_state,
)


def _record(method: str, *, claim_id: str | None = None, **extra: object) -> dict:
    rec: dict[str, object] = {"method": method, "confidence": "medium"}
    if claim_id is not None:
        rec["claim_id"] = claim_id
    rec.update(extra)
    return rec


class TestFormalCoverageFromRecords:
    def test_empty_records_returns_zero_metrics(self) -> None:
        out = formal_proof_coverage_from_records([])
        assert out["claims_with_formal_statement"] == 0
        assert out["claims_with_formal_proof"] == 0
        assert out["claims_with_statement_only"] == 0
        assert out["blueprint_completion_percent"] == 0.0
        assert out["total_claims"] is None
        assert out["unbound_formal_statements"] == 0
        assert out["unbound_formal_proofs"] == 0
        assert out["claim_ids"] == {
            "formal_statement": [],
            "formal_proof": [],
            "statement_only": [],
        }

    def test_counts_distinct_claims_with_formal_statement(self) -> None:
        records = [
            _record("5.20", claim_id="C1"),
            _record("5.20", claim_id="C1"),
            _record("5.20", claim_id="C2"),
            _record("5.1", claim_id="C3"),
        ]
        out = formal_proof_coverage_from_records(records)
        assert out["claims_with_formal_statement"] == 2
        assert out["claims_with_formal_proof"] == 0
        assert out["claim_ids"]["formal_statement"] == ["C1", "C2"]
        assert out["claim_ids"]["statement_only"] == ["C1", "C2"]

    def test_formal_proof_implies_formal_statement(self) -> None:
        records = [_record("5.21", claim_id="C1")]
        out = formal_proof_coverage_from_records(records)
        assert out["claims_with_formal_statement"] == 1
        assert out["claims_with_formal_proof"] == 1
        assert out["claims_with_statement_only"] == 0
        assert out["blueprint_completion_percent"] == 100.0

    def test_blueprint_completion_against_statement_count(self) -> None:
        records = [
            _record("5.20", claim_id="C1"),
            _record("5.20", claim_id="C2"),
            _record("5.21", claim_id="C3"),
            _record("5.21", claim_id="C4"),
        ]
        out = formal_proof_coverage_from_records(records)
        # 4 distinct claims entered the formal track, 2 fully proven.
        assert out["claims_with_formal_statement"] == 4
        assert out["claims_with_formal_proof"] == 2
        assert out["blueprint_completion_percent"] == 50.0
        assert out["claim_ids"]["statement_only"] == ["C1", "C2"]

    def test_blueprint_completion_uses_total_claims_when_given(self) -> None:
        records = [_record("5.21", claim_id="C1")]
        out = formal_proof_coverage_from_records(records, total_claims=4)
        assert out["total_claims"] == 4
        assert out["blueprint_completion_percent"] == 25.0

    def test_total_claims_zero_falls_back_to_formal_statement_count(self) -> None:
        records = [_record("5.21", claim_id="C1")]
        out = formal_proof_coverage_from_records(records, total_claims=0)
        assert out["blueprint_completion_percent"] == 100.0

    def test_accepts_check_key_form(self) -> None:
        records = [
            _record("universal.formal_statement", claim_id="C1"),
            _record("universal.formal_proof", claim_id="C2"),
        ]
        out = formal_proof_coverage_from_records(records)
        assert out["claims_with_formal_statement"] == 2
        assert out["claims_with_formal_proof"] == 1

    def test_falls_back_to_deliverable_id_when_no_claim_id(self) -> None:
        records = [_record("5.21", deliverable_id="D1")]
        out = formal_proof_coverage_from_records(records)
        assert out["claims_with_formal_proof"] == 1
        assert out["claim_ids"]["formal_proof"] == ["D1"]

    def test_counts_unbound_formal_records_separately(self) -> None:
        records = [
            _record("5.20"),
            _record("5.21"),
            _record("5.20", claim_id="C1"),
        ]
        out = formal_proof_coverage_from_records(records)
        assert out["claims_with_formal_statement"] == 1
        assert out["unbound_formal_statements"] == 1
        assert out["unbound_formal_proofs"] == 1

    def test_skips_non_formal_methods(self) -> None:
        records = [
            _record("5.1", claim_id="C1"),
            _record("5.5", claim_id="C2"),
        ]
        out = formal_proof_coverage_from_records(records)
        assert out["claims_with_formal_statement"] == 0
        assert out["claims_with_formal_proof"] == 0

    def test_defensive_against_non_dict_entries(self) -> None:
        records = [None, "not-a-record", 42, _record("5.20", claim_id="C1")]
        out = formal_proof_coverage_from_records(records)
        assert out["claims_with_formal_statement"] == 1

    def test_defensive_against_non_string_method(self) -> None:
        records = [{"method": 520, "claim_id": "C1"}, _record("5.20", claim_id="C2")]
        out = formal_proof_coverage_from_records(records)
        assert out["claims_with_formal_statement"] == 1
        assert out["claim_ids"]["formal_statement"] == ["C2"]

    def test_whitespace_method_is_ignored(self) -> None:
        records = [{"method": "   ", "claim_id": "C1"}, _record("  5.20  ", claim_id="C2")]
        out = formal_proof_coverage_from_records(records)
        # Whitespace-only method: ignored. Padded "5.20" still recognised.
        assert out["claims_with_formal_statement"] == 1
        assert out["claim_ids"]["formal_statement"] == ["C2"]

    def test_claim_id_whitespace_is_normalized(self) -> None:
        records = [
            _record("5.20", claim_id="  C1  "),
            _record("5.21", claim_id="C1"),
        ]
        out = formal_proof_coverage_from_records(records)
        # Both records resolve to the same claim after trimming.
        assert out["claims_with_formal_statement"] == 1
        assert out["claims_with_formal_proof"] == 1
        assert out["blueprint_completion_percent"] == 100.0

    def test_method_constants_do_not_overlap(self) -> None:
        assert FORMAL_STATEMENT_METHODS.isdisjoint(FORMAL_PROOF_METHODS)


class TestCollectRecordsFromState:
    def test_returns_empty_for_non_dict_state(self) -> None:
        assert collect_verification_records_from_state(None) == []
        assert collect_verification_records_from_state([]) == []
        assert collect_verification_records_from_state("state") == []

    def test_flattens_records_across_results(self) -> None:
        state = {
            "intermediate_results": [
                {
                    "id": "R1",
                    "verification_records": [
                        _record("5.20", claim_id="C1"),
                        _record("5.21", claim_id="C1"),
                    ],
                },
                {
                    "id": "R2",
                    "verification_records": [_record("5.20", claim_id="C2")],
                },
                {"id": "R3"},  # missing verification_records
                "not-a-dict",  # defensive
                {"id": "R4", "verification_records": "not-a-list"},  # defensive
            ],
        }
        records = collect_verification_records_from_state(state)
        assert len(records) == 3
        assert {r.get("claim_id") for r in records} == {"C1", "C2"}

    def test_state_wrapper_computes_coverage(self) -> None:
        state = {
            "intermediate_results": [
                {
                    "id": "R1",
                    "verification_records": [
                        _record("5.20", claim_id="C1"),
                        _record("5.21", claim_id="C2"),
                    ],
                }
            ]
        }
        out = formal_proof_coverage_from_state(state)
        assert out["claims_with_formal_statement"] == 2
        assert out["claims_with_formal_proof"] == 1
        assert out["blueprint_completion_percent"] == 50.0


class TestMCPCoverageTool:
    def test_formal_proof_block_absent_without_records(self) -> None:
        from grd.mcp.servers.verification_server import get_verification_coverage

        result = get_verification_coverage(error_class_ids=[15], active_checks=["5.1"])
        assert "formal_proof" not in result

    def test_formal_proof_block_present_when_records_provided(self) -> None:
        from grd.mcp.servers.verification_server import get_verification_coverage

        result = get_verification_coverage(
            error_class_ids=[15],
            active_checks=["5.1"],
            verification_records=[
                _record("5.20", claim_id="C1"),
                _record("5.21", claim_id="C2"),
            ],
        )
        assert "formal_proof" in result
        fp = result["formal_proof"]
        assert fp["claims_with_formal_statement"] == 2
        assert fp["claims_with_formal_proof"] == 1
        assert fp["blueprint_completion_percent"] == 50.0

    def test_empty_records_list_still_emits_formal_proof_block(self) -> None:
        from grd.mcp.servers.verification_server import get_verification_coverage

        result = get_verification_coverage(
            error_class_ids=[15],
            active_checks=["5.1"],
            verification_records=[],
        )
        assert result["formal_proof"]["claims_with_formal_statement"] == 0
        assert result["formal_proof"]["blueprint_completion_percent"] == 0.0

    def test_total_claims_feeds_blueprint_denominator(self) -> None:
        from grd.mcp.servers.verification_server import get_verification_coverage

        result = get_verification_coverage(
            error_class_ids=[15],
            active_checks=["5.1"],
            verification_records=[_record("5.21", claim_id="C1")],
            total_claims=4,
        )
        assert result["formal_proof"]["total_claims"] == 4
        assert result["formal_proof"]["blueprint_completion_percent"] == 25.0

    def test_invalid_verification_records_returns_error_envelope(self) -> None:
        from grd.mcp.servers.verification_server import get_verification_coverage

        result = get_verification_coverage(
            error_class_ids=[15],
            active_checks=["5.1"],
            verification_records=[{"ok": True}, "bad"],  # type: ignore[list-item]
        )
        assert result["error"] == "verification_records[1] must be an object"

    def test_invalid_total_claims_returns_error_envelope(self) -> None:
        from grd.mcp.servers.verification_server import get_verification_coverage

        result = get_verification_coverage(
            error_class_ids=[15],
            active_checks=["5.1"],
            verification_records=[],
            total_claims=-1,
        )
        assert result["error"] == "total_claims must be a non-negative integer"

    def test_boolean_total_claims_rejected(self) -> None:
        from grd.mcp.servers.verification_server import get_verification_coverage

        result = get_verification_coverage(
            error_class_ids=[15],
            active_checks=["5.1"],
            verification_records=[],
            total_claims=True,  # type: ignore[arg-type]
        )
        assert result["error"] == "total_claims must be a non-negative integer"


class TestVerifyFormalCoverageCLI:
    def test_cli_reports_metrics_from_state_json(self, tmp_path, monkeypatch) -> None:
        from typer.testing import CliRunner

        from grd.cli import app

        # Minimal project with a GRD state.json containing formal evidence.
        planning = tmp_path / ".grd"
        planning.mkdir()
        state = {
            "intermediate_results": [
                {
                    "id": "R1",
                    "verified": True,
                    "verification_records": [
                        _record("5.20", claim_id="C1"),
                        _record("5.21", claim_id="C2"),
                    ],
                }
            ]
        }
        import json

        (planning / "state.json").write_text(json.dumps(state))
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["--raw", "verify", "formal-coverage"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["claims_with_formal_statement"] == 2
        assert payload["claims_with_formal_proof"] == 1
        assert payload["blueprint_completion_percent"] == 50.0

    def test_cli_handles_missing_state(self, tmp_path, monkeypatch) -> None:
        from typer.testing import CliRunner

        from grd.cli import app

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["--raw", "verify", "formal-coverage"])
        assert result.exit_code == 0, result.output
        import json

        payload = json.loads(result.output)
        assert payload["claims_with_formal_statement"] == 0
        assert payload["claims_with_formal_proof"] == 0

    def test_cli_rejects_malformed_state(self, tmp_path, monkeypatch) -> None:
        from typer.testing import CliRunner

        from grd.cli import app

        planning = tmp_path / ".grd"
        planning.mkdir()
        (planning / "state.json").write_text("{ not valid json")
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["--raw", "verify", "formal-coverage"])
        # BadParameter → non-zero exit
        assert result.exit_code != 0

    def test_cli_total_claims_option(self, tmp_path, monkeypatch) -> None:
        from typer.testing import CliRunner

        from grd.cli import app

        planning = tmp_path / ".grd"
        planning.mkdir()
        state = {
            "intermediate_results": [
                {
                    "id": "R1",
                    "verified": True,
                    "verification_records": [_record("5.21", claim_id="C1")],
                }
            ]
        }
        import json

        (planning / "state.json").write_text(json.dumps(state))
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(app, ["--raw", "verify", "formal-coverage", "--total-claims", "4"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["total_claims"] == 4
        assert payload["blueprint_completion_percent"] == 25.0


def test_module_exports_are_stable() -> None:
    """Guard against accidental API drift for the metric method sets."""
    assert "5.20" in FORMAL_STATEMENT_METHODS
    assert "5.21" in FORMAL_PROOF_METHODS
    assert "universal.formal_statement" in FORMAL_STATEMENT_METHODS
    assert "universal.formal_proof" in FORMAL_PROOF_METHODS


@pytest.mark.parametrize(
    "records,expected_pct",
    [
        ([_record("5.21", claim_id="C1")], 100.0),
        (
            [
                _record("5.20", claim_id="C1"),
                _record("5.20", claim_id="C2"),
                _record("5.21", claim_id="C3"),
            ],
            round(1 / 3 * 100, 1),
        ),
    ],
)
def test_blueprint_completion_rounds_to_one_decimal(
    records: list[dict], expected_pct: float
) -> None:
    out = formal_proof_coverage_from_records(records)
    assert out["blueprint_completion_percent"] == expected_pct
