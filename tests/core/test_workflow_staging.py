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


def _new_project_payload() -> dict[str, object]:
    return json.loads(NEW_PROJECT_STAGE_MANIFEST_PATH.read_text(encoding="utf-8"))


def test_resolve_workflow_stage_manifest_path_matches_canonical_manifest() -> None:
    assert resolve_workflow_stage_manifest_path("new-project") == NEW_PROJECT_STAGE_MANIFEST_PATH


def test_load_workflow_stage_manifest_is_cached() -> None:
    first = load_workflow_stage_manifest("new-project")
    second = load_workflow_stage_manifest("new-project")

    assert first is second
    assert first.stage_ids() == ("scope_intake", "scope_approval", "post_scope")
    assert "references/shared/canonical-schema-discipline.md" in first.stages[0].must_not_eager_load


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
    payload = _new_project_payload()
    mutator(payload)

    with pytest.raises(ValueError, match=message):
        validate_workflow_stage_manifest_payload(payload)


def test_load_workflow_stage_manifest_from_path_respects_cache_invalidation(tmp_path: Path) -> None:
    payload = _new_project_payload()
    manifest_path = tmp_path / "new-project-stage-manifest.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    first = load_workflow_stage_manifest_from_path(manifest_path, expected_workflow_id="new-project")
    payload["stages"][0]["purpose"] = "updated purpose"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    second = load_workflow_stage_manifest_from_path(manifest_path, expected_workflow_id="new-project")
    assert second is first
    assert second.stages[0].purpose != "updated purpose"

    invalidate_workflow_stage_manifest_cache()
    third = load_workflow_stage_manifest_from_path(manifest_path, expected_workflow_id="new-project")

    assert third is not first
    assert third.stages[0].purpose == "updated purpose"
