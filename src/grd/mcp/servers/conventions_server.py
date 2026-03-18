"""MCP server for GRD convention management.

Thin MCP wrapper around grd.core.conventions. Exposes convention lock
operations as MCP tools for solver agents.

Usage:
    python -m grd.mcp.servers.conventions_server
    # or via entry point:
    grd-mcp-conventions
"""

import json
import logging
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from mcp.server.fastmcp import FastMCP

from grd.contracts import ConventionLock
from grd.core.constants import ProjectLayout
from grd.core.conventions import (
    ConventionSetResult,
    convention_list,
    normalize_key,
    normalize_value,
    validate_assertions,
)
from grd.core.conventions import (
    convention_check as _convention_check,
)
from grd.core.conventions import (
    convention_diff as _convention_diff,
)
from grd.core.conventions import (
    convention_set as _convention_set,
)
from grd.core.errors import ConventionError
from grd.core.observability import grd_span

T = TypeVar("T")

# MCP stdio uses stdout for JSON-RPC — redirect logging to stderr
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")
logger = logging.getLogger("grd-conventions")

mcp = FastMCP("grd-conventions")


# ─── Domain-Aware Helpers ────────────────────────────────────────────────────


def _get_domain_ctx():
    """Load the active domain context from GRD_DOMAIN env var."""
    from grd.domains.loader import DomainContext, load_domain

    domain_name = os.environ.get("GRD_DOMAIN", "physics")
    return load_domain(domain_name)


def _get_convention_options(ctx=None) -> dict[str, list[str]]:
    """Return convention options from domain context."""
    if ctx is None:
        ctx = _get_domain_ctx()
    if ctx is not None:
        return ctx.convention_options
    return {}


def _get_subfield_defaults(ctx=None) -> dict[str, dict[str, str]]:
    """Return subfield defaults from domain context."""
    if ctx is None:
        ctx = _get_domain_ctx()
    if ctx is not None:
        return ctx.subfield_defaults
    return {}


def _get_known_conventions(ctx=None) -> list[str]:
    """Return known convention names from domain context."""
    if ctx is None:
        ctx = _get_domain_ctx()
    if ctx is not None:
        return ctx.known_convention_names
    return []


def _get_critical_fields(ctx=None) -> set[str]:
    """Return critical field names from domain context."""
    if ctx is None:
        ctx = _get_domain_ctx()
    if ctx is not None:
        return set(ctx.critical_fields)
    return set()


# ─── Project I/O ──────────────────────────────────────────────────────────────


def _load_lock_from_project(project_dir: str) -> ConventionLock:
    """Load convention lock from project state.json."""
    state_path = ProjectLayout(Path(project_dir)).state_json
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return ConventionLock()
    except json.JSONDecodeError as e:
        raise ConventionError(f"Malformed state.json: {e}") from e


    if not isinstance(raw, dict):
        return ConventionLock()
    lock_data = raw.get("convention_lock", {})
    if not isinstance(lock_data, dict):
        return ConventionLock()
    return ConventionLock(**lock_data)


def _update_lock_in_project(
    project_dir: str,
    mutate_fn: Callable[[ConventionLock], T],
) -> tuple[ConventionLock, T]:
    """Atomically load, mutate, and save a convention lock."""
    from grd.core.state import save_state_json_locked
    from grd.core.utils import file_lock

    state_path = ProjectLayout(Path(project_dir)).state_json
    cwd = Path(project_dir)
    with file_lock(state_path):
        # --- read ---
        try:
            raw = json.loads(state_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raw = {}
        except json.JSONDecodeError as e:
            raise ConventionError(f"Malformed state.json: {e}") from e


        if not isinstance(raw, dict):
            raw = {}
        lock_data = raw.get("convention_lock", {})
        if not isinstance(lock_data, dict):
            lock_data = {}
        lock = ConventionLock(**lock_data)

        # --- mutate ---
        result = mutate_fn(lock)

        # --- write (only when the lock was actually changed) ---
        new_lock_data = lock.model_dump(exclude_none=True)
        if new_lock_data != lock_data:
            raw["convention_lock"] = new_lock_data
            save_state_json_locked(cwd, raw)

    return lock, result


# ─── MCP Tools ────────────────────────────────────────────────────────────────


@mcp.tool()
def convention_lock_status(project_dir: str) -> dict:
    """Get the current convention lock state for a GRD project.

    Returns all set conventions and lists which standard fields are still unset.
    """
    with grd_span("mcp.conventions.lock_status"):
        try:
            ctx = _get_domain_ctx()
            known = _get_known_conventions(ctx)
            lock = _load_lock_from_project(project_dir)
            result = convention_list(lock, domain_ctx=ctx)

            set_fields = [k for k, e in result.conventions.items() if e.is_set and e.canonical]
            unset_fields = [k for k in known if k not in set_fields]
            custom = {k: e.value for k, e in result.conventions.items() if not e.canonical and e.is_set}

            return {
                "lock": lock.model_dump(exclude_none=True),
                "set_count": result.set_count,
                "total_standard_fields": result.canonical_total,
                "set_fields": set_fields,
                "unset_fields": unset_fields,
                "custom_conventions": custom,
                "completeness_percent": round(len(set_fields) / max(result.canonical_total, 1) * 100, 1),
            }
        except (ConventionError, OSError, ValueError, TimeoutError) as e:
            return {"error": str(e)}


@mcp.tool()
def convention_set(
    project_dir: str,
    key: str,
    value: str,
    force: bool = False,
) -> dict:
    """Set a convention in the project's convention lock.

    Standard convention fields are validated against known options.
    Use force=True to override an already-set convention (dangerous
    mid-project -- can invalidate prior derivations).

    Custom conventions use the 'custom:' prefix: key="custom:my_convention".
    """
    with grd_span("mcp.conventions.set", convention_key=key):
        try:
            ctx = _get_domain_ctx()

            # Validate custom key eagerly (before acquiring the file lock).
            if key.startswith("custom:"):
                custom_key = key[len("custom:"):]
                if not custom_key:
                    raise ConventionError("Custom convention key cannot be empty")

            def _mutate(lock: ConventionLock) -> ConventionSetResult:
                if key.startswith("custom:"):
                    return _convention_set(lock, key[len("custom:"):], value, force=force, domain_ctx=ctx)
                return _convention_set(lock, key, value, force=force, domain_ctx=ctx)

            # Atomic read-modify-write under file lock to prevent TOCTOU races.
            _lock, result = _update_lock_in_project(project_dir, _mutate)
        except (ConventionError, OSError, ValueError, TimeoutError) as e:
            return {"error": str(e)}

        if not result.updated:
            return {
                "status": "already_set",
                "key": result.key,
                "current_value": result.previous,
                "requested_value": result.value,
                "message": result.hint or f"Convention '{result.key}' already set. Use force=True to override.",
            }

        response: dict[str, object] = {
            "status": "set",
            "key": result.key,
            "value": result.value,
            "type": "custom" if result.custom else "standard",
        }
        if result.previous is not None:
            response["previous_value"] = result.previous
            response["forced"] = True

        # Warn about non-standard values for known fields
        canonical = normalize_key(key, domain_ctx=ctx)
        options = _get_convention_options(ctx).get(canonical, [])
        if options:
            normalized_options = [normalize_value(canonical, o, domain_ctx=ctx) for o in options]
            if result.value not in options and result.value not in normalized_options:
                response["warning"] = f"Non-standard value '{result.value}' for '{canonical}'. Known options: {options}"

        return response


@mcp.tool()
def convention_check(lock: dict) -> dict:
    """Validate a convention lock for completeness and consistency.

    Checks which fields are set, flags missing critical conventions,
    and identifies potential inconsistencies between related fields.
    """
    with grd_span("mcp.conventions.check"):
        try:
            ctx = _get_domain_ctx()
            parsed = ConventionLock(**lock)
            result = _convention_check(parsed, domain_ctx=ctx)

            # Critical fields from domain pack
            critical = _get_critical_fields(ctx)
            missing_critical = [m.key for m in result.missing if m.key in critical]

            return {
                "valid": len(missing_critical) == 0,
                "completeness_percent": round(result.set_count / max(result.total, 1) * 100, 1),
                "set_fields": [s.key for s in result.set_conventions],
                "unset_fields": [m.key for m in result.missing],
                "missing_critical": missing_critical,
                "total_standard_fields": result.total,
            }
        except (ConventionError, OSError, ValueError, TimeoutError) as e:
            return {"error": str(e)}


@mcp.tool()
def convention_diff(lock_a: dict, lock_b: dict) -> dict:
    """Compare two convention lock dictionaries and identify differences.

    Useful for detecting convention drift between phases or comparing
    a plan's conventions against the project lock.
    """
    with grd_span("mcp.conventions.diff"):
        try:
            ctx = _get_domain_ctx()
            parsed_a = ConventionLock(**lock_a)
            parsed_b = ConventionLock(**lock_b)
            result = _convention_diff(parsed_a, parsed_b)
        except (ConventionError, OSError, ValueError, TimeoutError) as e:
            return {"error": str(e)}

    critical_fields = _get_critical_fields(ctx)
    diffs: list[dict[str, object]] = []

    for d in result.changed:
        diffs.append(
            {
                "field": d.key,
                "value_a": d.from_value,
                "value_b": d.to_value,
                "severity": "critical" if d.key in critical_fields else "warning",
            }
        )
    for d in result.added:
        diffs.append(
            {
                "field": d.key,
                "value_a": None,
                "value_b": d.to_value,
                "severity": "info",
            }
        )
    for d in result.removed:
        diffs.append(
            {
                "field": d.key,
                "value_a": d.from_value,
                "value_b": None,
                "severity": "info",
            }
        )

    return {
        "identical": len(diffs) == 0,
        "diff_count": len(diffs),
        "diffs": diffs,
        "critical_diffs": [d for d in diffs if d["severity"] == "critical"],
    }


@mcp.tool()
def assert_convention_validate(file_content: str, lock: dict) -> dict:
    """Verify ASSERT_CONVENTION lines in a file against the project lock."""
    from grd.core.conventions import parse_assert_conventions

    with grd_span("mcp.conventions.assert_validate"):
        try:
            parsed_lock = ConventionLock(**lock)
            assertions = parse_assert_conventions(file_content)
            mismatches = validate_assertions(file_content, parsed_lock, filename="<mcp_input>")
        except (ConventionError, OSError, ValueError, TimeoutError) as e:
            return {"error": str(e)}

    if not assertions:
        return {
            "valid": False,
            "assertions_found": 0,
            "message": "No ASSERT_CONVENTION lines found. Every derivation file must include at least one.",
            "mismatches": [],
            "assertions": [],
        }

    return {
        "valid": len(mismatches) == 0,
        "assertions_found": len(assertions),
        "assertions": [{"key": k, "value": v} for k, v in assertions],
        "mismatches": [
            {
                "key": m.key,
                "file_value": m.file_value,
                "lock_value": m.lock_value,
                "message": f"Convention mismatch: file declares {m.key}={m.file_value} but lock has {m.key}={m.lock_value}",
            }
            for m in mismatches
        ],
    }


@mcp.tool()
def subfield_defaults(domain: str) -> dict:
    """Return recommended default conventions for a research subfield.

    Provides sensible starting conventions for common subfields within
    the active domain. These are recommendations, not requirements.
    """
    with grd_span("mcp.conventions.subfield_defaults", domain=domain):
        ctx = _get_domain_ctx()
        all_defaults = _get_subfield_defaults(ctx)
        known = _get_known_conventions(ctx)
        defaults = all_defaults.get(domain)

    if defaults is None:
        return {
            "found": False,
            "domain": domain,
            "available_domains": sorted(all_defaults.keys()),
            "message": f"No defaults for subfield '{domain}'.",
        }

    return {
        "found": True,
        "domain": domain,
        "defaults": defaults,
        "field_count": len(defaults),
        "unset_fields": [f for f in known if f not in defaults],
        "message": (
            f"Recommended conventions for {domain}. Sets {len(defaults)} of {len(known)} standard fields."
        ),
    }


# ─── Entry Point ──────────────────────────────────────────────────────────────


def main() -> None:
    """Run the MCP server via stdio transport."""
    from grd.mcp.servers import run_mcp_server

    run_mcp_server(mcp, "GRD Conventions MCP Server")


if __name__ == "__main__":
    main()
