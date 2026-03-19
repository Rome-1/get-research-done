from __future__ import annotations

from pathlib import Path

import pytest

from gpd.core.commands import cmd_summary_extract
from gpd.core.errors import ValidationError

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "stage4"


def _summary_with_reference_usage(*, status: str, completed_actions: str, missing_actions: str) -> str:
    return (
        (FIXTURES_DIR / "summary_with_contract_results.md")
        .read_text(encoding="utf-8")
        .replace("status: completed", f"status: {status}", 1)
        .replace("completed_actions: [read, compare, cite]", f"completed_actions: {completed_actions}", 1)
        .replace("missing_actions: []", f"missing_actions: {missing_actions}", 1)
    )


def test_summary_extract_parses_contract_results_and_comparison_verdicts(tmp_path: Path) -> None:
    summary_path = tmp_path / "01-SUMMARY.md"
    summary_path.write_text((FIXTURES_DIR / "summary_with_contract_results.md").read_text(encoding="utf-8"), encoding="utf-8")

    result = cmd_summary_extract(tmp_path, "01-SUMMARY.md")

    assert result.key_files == ["figures/benchmark.png", "src/benchmark.py"]
    assert result.key_files_created == ["figures/benchmark.png"]
    assert result.key_files_modified == ["src/benchmark.py"]
    assert result.plan_contract_ref == ".gpd/phases/01-benchmark/01-01-PLAN.md#/contract"
    assert result.contract_results is not None
    assert result.contract_results.claims["claim-benchmark"].status == "passed"
    assert result.contract_results.references["ref-benchmark"].completed_actions == ["read", "compare", "cite"]
    assert result.comparison_verdicts[0].subject_id == "claim-benchmark"
    assert result.comparison_verdicts[0].verdict == "pass"


def test_summary_extract_field_filter_returns_contract_results(tmp_path: Path) -> None:
    summary_path = tmp_path / "01-SUMMARY.md"
    summary_path.write_text((FIXTURES_DIR / "summary_with_contract_results.md").read_text(encoding="utf-8"), encoding="utf-8")

    result = cmd_summary_extract(tmp_path, "01-SUMMARY.md", fields=["contract_results", "comparison_verdicts"])

    assert isinstance(result, dict)
    assert result["contract_results"]["claims"]["claim-benchmark"]["status"] == "passed"
    assert result["comparison_verdicts"][0]["subject_role"] == "decisive"


@pytest.mark.parametrize("placeholder", ["[]", "null"])
def test_summary_extract_rejects_placeholder_contract_results_section_shapes(
    tmp_path: Path,
    placeholder: str,
) -> None:
    summary_path = tmp_path / "broken-SUMMARY.md"
    summary_path.write_text(
        (
            "---\n"
            "phase: 01\n"
            "plan: 01\n"
            "depth: full\n"
            "provides: []\n"
            "completed: 2026-03-13\n"
            "contract_results:\n"
            f"  claims: {placeholder}\n"
            "  uncertainty_markers:\n"
            "    weakest_anchors: []\n"
            "    disconfirming_observations: []\n"
            "---\n\n"
            "# Summary\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="claims"):
        cmd_summary_extract(tmp_path, "broken-SUMMARY.md")


def test_summary_extract_requires_explicit_uncertainty_markers(tmp_path: Path) -> None:
    summary_path = tmp_path / "broken-SUMMARY.md"
    summary_path.write_text(
        (FIXTURES_DIR / "summary_with_contract_results.md").read_text(encoding="utf-8").replace(
            "  uncertainty_markers:\n"
            "    weakest_anchors: [Reference tolerance interpretation]\n"
            "    disconfirming_observations: [Benchmark agreement disappears once normalization is fixed]\n",
            "",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="uncertainty_markers"):
        cmd_summary_extract(tmp_path, "broken-SUMMARY.md")


def test_summary_extract_normalizes_reference_action_ledgers(tmp_path: Path) -> None:
    summary_path = tmp_path / "01-SUMMARY.md"
    summary_path.write_text(
        _summary_with_reference_usage(
            status="missing",
            completed_actions='[" read ", read, "read", "  "]',
            missing_actions='[" compare ", compare, cite, " ", cite]',
        ),
        encoding="utf-8",
    )

    result = cmd_summary_extract(tmp_path, "01-SUMMARY.md")

    assert result.contract_results is not None
    assert result.contract_results.references["ref-benchmark"].completed_actions == ["read"]
    assert result.contract_results.references["ref-benchmark"].missing_actions == ["compare", "cite"]


@pytest.mark.parametrize(
    ("status", "completed_actions", "missing_actions", "expected_completed", "expected_missing"),
    [
        ("Completed", "Read", "[]", ["read"], []),
        ("Missing", "[]", "Compare", [], ["compare"]),
    ],
)
def test_summary_extract_normalizes_singleton_and_case_variant_reference_action_ledgers(
    tmp_path: Path,
    status: str,
    completed_actions: str,
    missing_actions: str,
    expected_completed: list[str],
    expected_missing: list[str],
) -> None:
    summary_path = tmp_path / "01-SUMMARY.md"
    summary_path.write_text(
        _summary_with_reference_usage(
            status=status,
            completed_actions=completed_actions,
            missing_actions=missing_actions,
        ),
        encoding="utf-8",
    )

    result = cmd_summary_extract(tmp_path, "01-SUMMARY.md")

    assert result.contract_results is not None
    assert result.contract_results.references["ref-benchmark"].status == status.casefold()
    assert result.contract_results.references["ref-benchmark"].completed_actions == expected_completed
    assert result.contract_results.references["ref-benchmark"].missing_actions == expected_missing


@pytest.mark.parametrize(
    ("status", "completed_actions", "missing_actions", "message"),
    [
        ("completed", "[]", "[]", "status=completed requires completed_actions"),
        ("completed", "[read]", "[compare]", "status=completed requires missing_actions to be empty"),
        ("missing", "[read]", "[]", "status=missing requires missing_actions"),
        (
            "not_applicable",
            "[read]",
            "[]",
            "status=not_applicable requires completed_actions and missing_actions to be empty",
        ),
        (
            "missing",
            "[read, compare]",
            "[compare]",
            "completed_actions and missing_actions must not overlap: compare",
        ),
    ],
)
def test_summary_extract_rejects_contradictory_reference_action_ledgers(
    tmp_path: Path,
    status: str,
    completed_actions: str,
    missing_actions: str,
    message: str,
) -> None:
    summary_path = tmp_path / "01-SUMMARY.md"
    summary_path.write_text(
        _summary_with_reference_usage(
            status=status,
            completed_actions=completed_actions,
            missing_actions=missing_actions,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError) as excinfo:
        cmd_summary_extract(tmp_path, "01-SUMMARY.md")

    assert message in str(excinfo.value)


def test_summary_extract_rejects_non_list_comparison_verdicts(tmp_path: Path) -> None:
    summary_path = tmp_path / "broken-SUMMARY.md"
    summary_path.write_text(
        "---\n"
        "phase: 01\n"
        "plan: 01\n"
        "depth: full\n"
        "provides: []\n"
        "completed: 2026-03-13\n"
        "comparison_verdicts:\n"
        "  claim-benchmark:\n"
        "    verdict: pass\n"
        "---\n\n"
        "# Summary\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="expected a list"):
        cmd_summary_extract(tmp_path, "broken-SUMMARY.md")
