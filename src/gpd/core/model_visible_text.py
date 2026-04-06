"""Tiny dependency-free strings shared by model-visible prompt wrappers."""

from __future__ import annotations

__all__ = [
    "agent_visibility_note",
    "command_visibility_note",
    "review_contract_visibility_note",
]


def agent_visibility_note() -> str:
    return (
        "Model-visible agent requirements. Follow this YAML. "
        "Closed schema; no extra keys. "
        "Use only the declared enum values for `commit_authority`, `surface`, `role_family`, "
        "`artifact_write_authority`, and `shared_state_authority`."
    )


def command_visibility_note() -> str:
    return (
        "Model-visible command constraints. Follow this YAML. "
        "Closed schema; no extra keys. "
        "Strict booleans only. "
        "Use only declared values for `context_mode`, `agent`, and `project_reentry_capable`."
    )


def review_contract_visibility_note() -> str:
    return (
        "Review contract schema. Follow this YAML. "
        "Closed schema; no extra keys. "
        "`schema_version` must be `1`; `review_mode` must be `publication` or `review`; "
        "`conditional_requirements[].when` must be one of the declared triggers; "
        "`conditional_requirements[].blocking_preflight_checks` must reuse declared `preflight_checks`."
    )
