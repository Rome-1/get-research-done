"""Helpers for surfacing review contracts inside model-visible prompt bodies."""

from __future__ import annotations

from collections.abc import Mapping

import yaml

VALID_REVIEW_MODES = ("publication", "review")
VALID_REVIEW_PREFLIGHT_CHECKS = (
    "project_state",
    "roadmap",
    "conventions",
    "research_artifacts",
    "manuscript",
    "compiled_manuscript",
    "referee_report_source",
    "phase_artifacts",
)
VALID_REVIEW_REQUIRED_STATES = ("phase_executed",)

REVIEW_CONTRACT_FIELD_ORDER = (
    "schema_version",
    "review_mode",
    "required_outputs",
    "required_evidence",
    "blocking_conditions",
    "preflight_checks",
    "stage_ids",
    "stage_artifacts",
    "final_decision_output",
    "requires_fresh_context_per_stage",
    "max_review_rounds",
    "required_state",
)
REVIEW_CONTRACT_FRONTMATTER_KEY = "review-contract"
REVIEW_CONTRACT_PROMPT_WRAPPER_KEY = "review_contract"
REVIEW_CONTRACT_WRAPPER_KEYS = (REVIEW_CONTRACT_PROMPT_WRAPPER_KEY, REVIEW_CONTRACT_FRONTMATTER_KEY)
REVIEW_CONTRACT_KEYS = frozenset(REVIEW_CONTRACT_FIELD_ORDER)


def extract_frontmatter_block(frontmatter: str, field_name: str) -> str:
    """Return one top-level YAML frontmatter block, preserving raw formatting."""

    lines = frontmatter.split("\n")
    prefix = f"{field_name}:"
    collected: list[str] = []
    collecting = False

    for line in lines:
        stripped = line.strip()
        is_top_level = line == line.lstrip()
        if not collecting:
            if is_top_level and stripped.startswith(prefix):
                collected.append(line.rstrip())
                collecting = True
            continue
        if is_top_level and stripped:
            break
        collected.append(line.rstrip())

    while collected and not collected[-1]:
        collected.pop()
    return "\n".join(collected)


def extract_review_contract_frontmatter_block(frontmatter: str) -> str:
    """Return the canonical review-contract frontmatter block."""

    canonical_block = extract_frontmatter_block(frontmatter, REVIEW_CONTRACT_FRONTMATTER_KEY)
    legacy_block = extract_frontmatter_block(frontmatter, "review_contract")
    if canonical_block and legacy_block:
        raise ValueError("review contract frontmatter must use only one frontmatter key")
    if legacy_block:
        raise ValueError("review contract frontmatter must use the canonical frontmatter key 'review-contract'")
    return canonical_block


def _load_review_contract_payload(review_contract: object) -> tuple[dict[str, object], bool]:
    """Return a strict review-contract mapping and whether it was wrapped."""

    if review_contract is None:
        return {}, False
    if isinstance(review_contract, str):
        block = review_contract.strip()
        if not block:
            return {}, False
        loaded = yaml.safe_load(block)
    elif isinstance(review_contract, Mapping):
        loaded = dict(review_contract)
    else:
        raise ValueError("review contract must be provided as YAML text or a mapping")

    if loaded is None:
        return {}, False
    if not isinstance(loaded, dict):
        raise ValueError(f"review contract must parse to a mapping, got {type(loaded).__name__}")

    wrapped_key_matches = [key for key in REVIEW_CONTRACT_WRAPPER_KEYS if key in loaded]
    if len(wrapped_key_matches) > 1:
        raise ValueError("review contract must use only one wrapper key")

    wrapped_key = wrapped_key_matches[0] if wrapped_key_matches else None
    wrapped_candidate = loaded.get(wrapped_key) if wrapped_key is not None else None
    wrapped = dict(wrapped_candidate) if isinstance(wrapped_candidate, Mapping) else None

    if wrapped is not None:
        unknown_top_level_keys = sorted(
            str(key) for key in loaded if key not in REVIEW_CONTRACT_WRAPPER_KEYS
        )
        if unknown_top_level_keys:
            formatted = ", ".join(unknown_top_level_keys)
            raise ValueError(f"Unknown review-contract field(s): {formatted}")
        unknown_inner_keys = sorted(str(key) for key in wrapped if str(key) not in REVIEW_CONTRACT_KEYS)
        if unknown_inner_keys:
            formatted = ", ".join(unknown_inner_keys)
            raise ValueError(f"Unknown review-contract field(s): {formatted}")
        return wrapped, True

    unknown_keys = sorted(str(key) for key in loaded if str(key) not in REVIEW_CONTRACT_KEYS)
    if unknown_keys:
        formatted = ", ".join(unknown_keys)
        raise ValueError(f"Unknown review-contract field(s): {formatted}")

    return loaded, False


def _normalize_review_contract_required_str(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _normalize_review_contract_optional_str(value: object, *, field_name: str, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    return value.strip()


def _normalize_review_contract_string_list(value: object, *, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of strings")

    normalized: list[str] = []
    for item in value:
        normalized.append(_normalize_review_contract_required_str(item, field_name=field_name))
    return normalized


def _normalize_review_contract_choice(value: object, *, field_name: str, valid_values: tuple[str, ...]) -> str:
    normalized = _normalize_review_contract_required_str(value, field_name=field_name)
    if normalized not in valid_values:
        valid = ", ".join(valid_values)
        raise ValueError(f"{field_name} must be one of: {valid}; got {normalized!r}")
    return normalized


def _normalize_review_contract_choice_list(
    value: object,
    *,
    field_name: str,
    valid_values: tuple[str, ...],
) -> list[str]:
    normalized = _normalize_review_contract_string_list(value, field_name=field_name)
    invalid_values = [item for item in normalized if item not in valid_values]
    if invalid_values:
        valid = ", ".join(valid_values)
        formatted = ", ".join(repr(item) for item in invalid_values)
        raise ValueError(f"{field_name} must contain only: {valid}; got {formatted}")
    return normalized


def _normalize_review_contract_bool(value: object, *, field_name: str, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be a boolean")


def _normalize_review_contract_non_negative_int(value: object, *, field_name: str, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    normalized = value
    if normalized < 0:
        raise ValueError(f"{field_name} must be >= 0")
    return normalized


def normalize_review_contract_payload(review_contract: object) -> dict[str, object]:
    """Return a canonical typed payload for rendering a review contract section."""

    loaded, wrapped = _load_review_contract_payload(review_contract)
    if not loaded:
        if wrapped:
            raise ValueError("review contract must set schema_version, review_mode")
        return {}

    if "schema_version" not in loaded or "review_mode" not in loaded:
        missing = [field for field in ("schema_version", "review_mode") if field not in loaded]
        formatted = ", ".join(missing)
        raise ValueError(f"review contract must set {formatted}")

    schema_version = loaded.get("schema_version")
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise ValueError("schema_version must be the integer 1")
    if schema_version != 1:
        raise ValueError("schema_version must be 1")

    required_state_raw = loaded.get("required_state")
    required_state = _normalize_review_contract_optional_str(
        required_state_raw,
        field_name="required_state",
    )
    if required_state and required_state not in VALID_REVIEW_REQUIRED_STATES:
        valid = ", ".join(VALID_REVIEW_REQUIRED_STATES)
        raise ValueError(f"required_state must be one of: {valid}; got {required_state!r}")

    return {
        "schema_version": schema_version,
        "review_mode": _normalize_review_contract_choice(
            loaded.get("review_mode"),
            field_name="review_mode",
            valid_values=VALID_REVIEW_MODES,
        ),
        "required_outputs": _normalize_review_contract_string_list(
            loaded.get("required_outputs"),
            field_name="required_outputs",
        ),
        "required_evidence": _normalize_review_contract_string_list(
            loaded.get("required_evidence"),
            field_name="required_evidence",
        ),
        "blocking_conditions": _normalize_review_contract_string_list(
            loaded.get("blocking_conditions"),
            field_name="blocking_conditions",
        ),
        "preflight_checks": _normalize_review_contract_choice_list(
            loaded.get("preflight_checks"),
            field_name="preflight_checks",
            valid_values=VALID_REVIEW_PREFLIGHT_CHECKS,
        ),
        "stage_ids": _normalize_review_contract_string_list(
            loaded.get("stage_ids"),
            field_name="stage_ids",
        ),
        "stage_artifacts": _normalize_review_contract_string_list(
            loaded.get("stage_artifacts"),
            field_name="stage_artifacts",
        ),
        "final_decision_output": _normalize_review_contract_optional_str(
            loaded.get("final_decision_output"),
            field_name="final_decision_output",
        ),
        "requires_fresh_context_per_stage": _normalize_review_contract_bool(
            loaded.get("requires_fresh_context_per_stage"),
            field_name="requires_fresh_context_per_stage",
        ),
        "max_review_rounds": _normalize_review_contract_non_negative_int(
            loaded.get("max_review_rounds"),
            field_name="max_review_rounds",
        ),
        "required_state": required_state,
    }


def render_review_contract_prompt(review_contract: object) -> str:
    """Render a canonical model-visible review-contract section."""

    payload = normalize_review_contract_payload(review_contract)
    if not payload:
        return ""
    rendered = yaml.safe_dump(
        {REVIEW_CONTRACT_PROMPT_WRAPPER_KEY: payload},
        sort_keys=False,
        allow_unicode=False,
    ).rstrip()
    return (
        "## Review Contract\n\n"
        "This command is enforced against the following hard review contract. "
        "Satisfy it directly in the generated artifacts.\n\n"
        f"```yaml\n{rendered}\n```"
    )
