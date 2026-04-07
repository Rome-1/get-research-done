"""Regression tests for shared workflow-stage manifest loading."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gpd.core.workflow_staging import (
    NEW_PROJECT_STAGE_MANIFEST_PATH,
    invalidate_workflow_stage_manifest_cache,
    load_workflow_stage_manifest,
    load_workflow_stage_manifest_from_path,
    resolve_workflow_stage_manifest_path,
    validate_workflow_stage_manifest_payload,
)


def _workflow_payload(workflow_id: str) -> dict[str, object]:
    manifest_path = resolve_workflow_stage_manifest_path(workflow_id)
    return json.loads(manifest_path.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("workflow_id", "expected_path"),
    [
        ("new-project", NEW_PROJECT_STAGE_MANIFEST_PATH),
        ("verify-work", NEW_PROJECT_STAGE_MANIFEST_PATH.parent / "verify-work-stage-manifest.json"),
    ],
)
def test_resolve_workflow_stage_manifest_path_matches_canonical_manifest(
    workflow_id: str,
    expected_path: Path,
) -> None:
    assert resolve_workflow_stage_manifest_path(workflow_id) == expected_path


def test_load_workflow_stage_manifest_is_cached() -> None:
    first = load_workflow_stage_manifest("new-project")
    second = load_workflow_stage_manifest("new-project")

    assert first is second
    assert first.stage_ids() == ("scope_intake", "scope_approval", "post_scope")
    assert "references/shared/canonical-schema-discipline.md" in first.stages[0].must_not_eager_load


def test_load_workflow_stage_manifest_loads_verify_work_manifest() -> None:
    manifest = load_workflow_stage_manifest("verify-work")

    assert manifest.workflow_id == "verify-work"
    assert manifest.stage_ids() == (
        "session_router",
        "phase_bootstrap",
        "inventory_build",
        "interactive_validation",
        "gap_repair",
    )
    assert manifest.stages[0].loaded_authorities == ("workflows/verify-work.md",)
    assert "references/verification/core/verification-core.md" in manifest.stages[0].must_not_eager_load
    assert "templates/verification-report.md" in manifest.stages[0].must_not_eager_load
    assert "references/verification/core/verification-core.md" in manifest.stages[2].loaded_authorities
    assert "templates/verification-report.md" in manifest.stages[3].loaded_authorities
    assert "references/protocols/error-propagation-protocol.md" in manifest.stages[4].loaded_authorities


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda payload: payload["stages"][0].__setitem__("loaded_authorities", ["/absolute/path.md"]), "normalized relative POSIX"),
        (
            lambda payload: payload["stages"][0].__setitem__(
                "must_not_eager_load", ["references/research/does-not-exist.md"]
            ),
            "existing markdown file",
        ),
        (lambda payload: payload["stages"][0].__setitem__("allowed_tools", ["file_read", "not-a-tool"]), "unknown tool"),
        (
            lambda payload: payload["stages"][0].__setitem__("required_init_fields", ["researcher_model", "not-a-field"]),
            "unknown field",
        ),
        (
            lambda payload: payload["stages"][0].__setitem__(
                "must_not_eager_load",
                [*payload["stages"][0]["must_not_eager_load"], "workflows/new-project.md"],
            ),
            "overlap with must_not_eager_load",
        ),
        (lambda payload: payload["stages"][1].__setitem__("writes_allowed", ["../escape.txt"]), "normalized relative POSIX path"),
    ],
)
def test_validate_workflow_stage_manifest_payload_rejects_bad_entries(
    mutator,
    message: str,
) -> None:
    payload = _workflow_payload("new-project")
    mutator(payload)

    with pytest.raises(ValueError, match=message):
        validate_workflow_stage_manifest_payload(payload)


@pytest.mark.parametrize("workflow_id", ["new-project", "verify-work"])
def test_load_workflow_stage_manifest_from_path_respects_cache_invalidation(
    workflow_id: str,
    tmp_path: Path,
) -> None:
    payload = _workflow_payload(workflow_id)
    manifest_path = tmp_path / f"{workflow_id}-stage-manifest.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    first = load_workflow_stage_manifest_from_path(manifest_path, expected_workflow_id=workflow_id)
    payload["stages"][0]["purpose"] = "updated purpose"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    second = load_workflow_stage_manifest_from_path(manifest_path, expected_workflow_id=workflow_id)
    assert second is first
    assert second.stages[0].purpose != "updated purpose"

    invalidate_workflow_stage_manifest_cache()
    third = load_workflow_stage_manifest_from_path(manifest_path, expected_workflow_id=workflow_id)

    assert third is not first
    assert third.stages[0].purpose == "updated purpose"
