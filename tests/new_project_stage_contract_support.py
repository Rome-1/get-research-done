"""Test-only wrappers for the staged `new-project` manifest."""

from __future__ import annotations

from pathlib import Path

from grd.core.workflow_staging import (
    WorkflowStage as NewProjectStage,
)
from grd.core.workflow_staging import (
    WorkflowStageConditionalAuthority as NewProjectConditionalAuthority,
)
from grd.core.workflow_staging import (
    WorkflowStageManifest as NewProjectStageContract,
)
from grd.core.workflow_staging import (
    load_workflow_stage_manifest,
    load_workflow_stage_manifest_from_path,
    resolve_workflow_stage_manifest_path,
    validate_workflow_stage_manifest_payload,
)

__all__ = [
    "NEW_PROJECT_STAGE_MANIFEST_PATH",
    "NewProjectConditionalAuthority",
    "NewProjectStage",
    "NewProjectStageContract",
    "load_new_project_stage_contract",
    "load_new_project_stage_contract_from_path",
    "validate_new_project_stage_contract_payload",
]


REPO_ROOT = Path(__file__).resolve().parents[1]
NEW_PROJECT_STAGE_MANIFEST_PATH = resolve_workflow_stage_manifest_path("new-project")


def load_new_project_stage_contract() -> NewProjectStageContract:
    return load_workflow_stage_manifest("new-project")


def load_new_project_stage_contract_from_path(manifest_path: Path) -> NewProjectStageContract:
    return load_workflow_stage_manifest_from_path(manifest_path, expected_workflow_id="new-project")


def validate_new_project_stage_contract_payload(raw: object) -> NewProjectStageContract:
    return validate_workflow_stage_manifest_payload(raw, expected_workflow_id="new-project")
