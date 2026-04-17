"""Shared scaffolding for model-visible YAML contract sections."""

from __future__ import annotations

from collections.abc import Mapping

import yaml

MODEL_VISIBLE_CLOSED_SCHEMA_PHRASE = "Closed schema; no extra keys."


def render_model_visible_note(prefix: str, *clauses: str) -> str:
    """Return a concise model-visible note with the shared closed-schema phrase."""

    parts = [prefix, "Use this YAML.", MODEL_VISIBLE_CLOSED_SCHEMA_PHRASE]
    parts.extend(clauses)
    return " ".join(parts)


def render_model_visible_yaml_section(*, heading: str, note: str, payload: Mapping[str, object]) -> str:
    """Render one canonical model-visible YAML section."""

    rendered = yaml.safe_dump(dict(payload), sort_keys=False, allow_unicode=False).rstrip()
    return f"## {heading}\n\n{note}\n\n```yaml\n{rendered}\n```"
