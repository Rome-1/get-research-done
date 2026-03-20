"""Remaining standalone commands and minor subcommand groups.

Covers: health, doctor, query, suggest, init_*, roadmap, milestone, progress,
approximation, uncertainty, question, calculation, config, json, commit,
pre_commit_check, version, timestamp, slug, resolve_tier, resolve_model,
verify_path, history_digest, summary_extract, regression_check, validate_return,
trace, and observe.
"""

from __future__ import annotations

import json
import sys

import typer

from grd.cli._helpers import (
    _collect_file_option_args,
    _emit_observability_event,
    _error,
    _filter_observability_events,
    _filter_observability_sessions,
    _get_cwd,
    _json_cli_output,
    _load_state_dict,
    _output,
    _print_version,
    _runtime_override_help,
    _supported_runtime_names,
    app,
)
from grd.core.errors import ConfigError

# ═══════════════════════════════════════════════════════════════════════════
# health
# ═══════════════════════════════════════════════════════════════════════════


@app.command("health")
def health(
    fix: bool = typer.Option(False, "--fix", help="Auto-fix issues where possible"),
) -> None:
    """Run the project health diagnostic."""
    from grd.core.health import run_health

    report = run_health(_get_cwd(), fix=fix)
    _output(report)
    if report.overall == "fail":
        raise typer.Exit(code=1)


# ═══════════════════════════════════════════════════════════════════════════
# doctor
# ═══════════════════════════════════════════════════════════════════════════


@app.command("doctor")
def doctor() -> None:
    """Check GRD installation and environment health."""
    from grd.core.health import run_doctor
    from grd.specs import SPECS_DIR

    _output(run_doctor(specs_dir=SPECS_DIR))


# ═══════════════════════════════════════════════════════════════════════════
# query
# ═══════════════════════════════════════════════════════════════════════════

query_app = typer.Typer(help="Cross-phase search and dependency tracing")


@query_app.command("search")
def query_search(
    provides: str | None = typer.Option(None, "--provides", help="Search by provides"),
    requires: str | None = typer.Option(None, "--requires", help="Search by requires"),
    affects: str | None = typer.Option(None, "--affects", help="Search by affects"),
    equation: str | None = typer.Option(None, "--equation", help="Search by equation"),
    text: str | None = typer.Option(None, "--text", help="Full-text search"),
    phase_range: str | None = typer.Option(None, "--phase-range", help="Phase range filter (e.g. 10-20)"),
) -> None:
    """Search across phases by provides/requires/text."""
    from grd.core.query import query as query_search

    _output(
        query_search(
            _get_cwd(),
            provides=provides,
            requires=requires,
            affects=affects,
            equation=equation,
            text=text,
            phase_range=phase_range,
        )
    )


@query_app.command("deps")
def query_deps(
    identifier: str = typer.Argument(..., help="Result identifier to trace dependencies for"),
) -> None:
    """Show what provides and requires a given result identifier."""
    from grd.core.query import query_deps

    _output(query_deps(_get_cwd(), identifier))


@query_app.command("assumptions")
def query_assumptions(
    assumption: list[str] = typer.Argument(None, help="Assumption text to search for"),
) -> None:
    """Search for assumptions across phases."""
    from grd.core.query import query_assumptions

    text = " ".join(assumption) if assumption else ""
    if not text.strip():
        _error("Usage: grd query assumptions <search-term>")
    _output(query_assumptions(_get_cwd(), text))


# ═══════════════════════════════════════════════════════════════════════════
# suggest
# ═══════════════════════════════════════════════════════════════════════════


@app.command("suggest")
def suggest(
    limit: int | None = typer.Option(None, "--limit", help="Max suggestions to return"),
) -> None:
    """Suggest what to do next based on project state."""
    from grd.core.suggest import suggest_next

    kwargs: dict[str, int] = {}
    if limit is not None:
        kwargs["limit"] = limit
    _output(suggest_next(_get_cwd(), **kwargs))


# ═══════════════════════════════════════════════════════════════════════════
# roadmap
# ═══════════════════════════════════════════════════════════════════════════

roadmap_app = typer.Typer(help="Roadmap analysis and phase lookup")


@roadmap_app.command("get-phase")
def roadmap_get_phase(
    phase_num: str = typer.Argument(..., help="Phase number"),
) -> None:
    """Get detailed roadmap entry for a phase."""
    from grd.core.phases import roadmap_get_phase

    _output(roadmap_get_phase(_get_cwd(), phase_num))


@roadmap_app.command("analyze")
def roadmap_analyze() -> None:
    """Analyze roadmap structure, dependencies, and coverage."""
    from grd.core.phases import roadmap_analyze

    _output(roadmap_analyze(_get_cwd()))


# ═══════════════════════════════════════════════════════════════════════════
# milestone
# ═══════════════════════════════════════════════════════════════════════════

milestone_app = typer.Typer(help="Milestone lifecycle")


@milestone_app.command("complete")
def milestone_complete(
    version: str = typer.Argument(..., help="Milestone version (e.g. v1.0)"),
    name: str | None = typer.Option(None, "--name", help="Milestone name"),
) -> None:
    """Archive a completed milestone."""
    from grd.core.phases import milestone_complete

    _output(milestone_complete(_get_cwd(), version, name=name))


# ═══════════════════════════════════════════════════════════════════════════
# progress
# ═══════════════════════════════════════════════════════════════════════════


@app.command("progress")
def progress(
    fmt: str = typer.Argument("json", help="Format: json, bar, or table"),
) -> None:
    """Render progress in the specified format."""
    from grd.core.phases import progress_render

    _output(progress_render(_get_cwd(), fmt))


# ═══════════════════════════════════════════════════════════════════════════
# init — Workflow context assembly
# ═══════════════════════════════════════════════════════════════════════════

init_app = typer.Typer(help="Assemble context for AI agent workflows")


@init_app.command("execute-phase")
def init_execute_phase(
    phase: str | None = typer.Argument(None, help="Phase number"),
    include: str | None = typer.Option(None, "--include", help="Additional context includes"),
) -> None:
    """Assemble context for executing a phase."""
    from grd.core.context import init_execute_phase

    includes = set(include.split(",")) if include else set()
    _output(init_execute_phase(_get_cwd(), phase, includes=includes))


@init_app.command("plan-phase")
def init_plan_phase(
    phase: str | None = typer.Argument(None, help="Phase number"),
    include: str | None = typer.Option(None, "--include", help="Additional context includes"),
) -> None:
    """Assemble context for planning a phase."""
    from grd.core.context import init_plan_phase

    includes = set(include.split(",")) if include else set()
    _output(init_plan_phase(_get_cwd(), phase, includes=includes))


@init_app.command("new-project")
def init_new_project() -> None:
    """Assemble context for starting a new project."""
    from grd.core.context import init_new_project

    _output(init_new_project(_get_cwd()))


@init_app.command("new-milestone")
def init_new_milestone() -> None:
    """Assemble context for starting a new milestone."""
    from grd.core.context import init_new_milestone

    _output(init_new_milestone(_get_cwd()))


@init_app.command("quick")
def init_quick(
    description: list[str] = typer.Argument(None, help="Task description"),
) -> None:
    """Assemble context for a quick task."""
    from grd.core.context import init_quick

    text = " ".join(description) if description else None
    _output(init_quick(_get_cwd(), description=text))


@init_app.command("resume")
def init_resume() -> None:
    """Assemble context for resuming previous work."""
    from grd.core.context import init_resume

    _output(init_resume(_get_cwd()))


@init_app.command("verify-work")
def init_verify_work(
    phase: str | None = typer.Argument(None, help="Phase to verify"),
) -> None:
    """Assemble context for verifying completed work."""
    from grd.core.context import init_verify_work

    _output(init_verify_work(_get_cwd(), phase))


@init_app.command("progress")
def init_progress(
    include: str | None = typer.Option(None, "--include", help="Additional context includes"),
) -> None:
    """Assemble context for progress review."""
    from grd.core.context import init_progress

    includes = set(include.split(",")) if include else set()
    _output(init_progress(_get_cwd(), includes=includes))


@init_app.command("map-research")
def init_map_research() -> None:
    """Assemble context for research mapping."""
    from grd.core.context import init_map_research

    _output(init_map_research(_get_cwd()))


@init_app.command("todos")
def init_todos(
    area: str | None = typer.Argument(None, help="Area to filter todos"),
) -> None:
    """Assemble context for todo review."""
    from grd.core.context import init_todos

    _output(init_todos(_get_cwd(), area))


@init_app.command("phase-op")
def init_phase_op(
    phase: str | None = typer.Argument(None, help="Phase number"),
    include: str | None = typer.Option(None, "--include", help="Additional context includes"),
) -> None:
    """Assemble context for generic phase operations."""
    from grd.core.context import init_phase_op

    includes = set(include.split(",")) if include else set()
    _output(init_phase_op(_get_cwd(), phase, includes))


@init_app.command("milestone-op")
def init_milestone_op() -> None:
    """Assemble context for milestone operations."""
    from grd.core.context import init_milestone_op

    _output(init_milestone_op(_get_cwd()))


# ═══════════════════════════════════════════════════════════════════════════
# approximation
# ═══════════════════════════════════════════════════════════════════════════

approx_app = typer.Typer(help="Approximation tracking and validity checks")


@approx_app.command("add")
def approximation_add(
    name: str | None = typer.Argument(None, help="Approximation name"),
    validity_range: str | None = typer.Option(None, "--validity-range", help="Validity range"),
    controlling_param: str | None = typer.Option(None, "--controlling-param", help="Controlling parameter"),
    current_value: str | None = typer.Option(None, "--current-value", help="Current value"),
    status: str | None = typer.Option(None, "--status", help="Status"),
) -> None:
    """Add an approximation to track."""
    import json as _json

    from grd.core.constants import ProjectLayout
    from grd.core.extras import approximation_add
    from grd.core.state import save_state_json_locked
    from grd.core.utils import file_lock

    # Filter None values so core function defaults ("", "valid") take effect
    kwargs: dict[str, str] = {}
    if validity_range is not None:
        kwargs["validity_range"] = validity_range
    if controlling_param is not None:
        kwargs["controlling_param"] = controlling_param
    if current_value is not None:
        kwargs["current_value"] = current_value
    if status is not None:
        kwargs["status"] = status

    cwd = _get_cwd()
    state_path = ProjectLayout(cwd).state_json

    with file_lock(state_path):
        try:
            state = _json.loads(state_path.read_text(encoding="utf-8"))
        except OSError:
            state = {}
        except _json.JSONDecodeError as e:
            _error(f"Malformed state.json: {e}")
        res = approximation_add(state, name=name or "", **kwargs)
        save_state_json_locked(cwd, state)
    _output(res)


@approx_app.command("list")
def approximation_list() -> None:
    """List all tracked approximations."""
    from grd.core.extras import approximation_list

    _output(approximation_list(_load_state_dict()))


@approx_app.command("check")
def approximation_check() -> None:
    """Check validity of all approximations."""
    from grd.core.extras import approximation_check

    _output(approximation_check(_load_state_dict()))


# ═══════════════════════════════════════════════════════════════════════════
# uncertainty
# ═══════════════════════════════════════════════════════════════════════════

uncertainty_app = typer.Typer(help="Uncertainty propagation tracking")


@uncertainty_app.command("add")
def uncertainty_add(
    quantity: str | None = typer.Argument(None, help="Physical quantity"),
    value: str | None = typer.Option(None, "--value", help="Value"),
    uncertainty: str | None = typer.Option(None, "--uncertainty", help="Uncertainty"),
    phase: str | None = typer.Option(None, "--phase", help="Phase number"),
    method: str | None = typer.Option(None, "--method", help="Method used"),
) -> None:
    """Add an uncertainty measurement."""
    import json as _json

    from grd.core.constants import ProjectLayout
    from grd.core.extras import uncertainty_add
    from grd.core.state import save_state_json_locked
    from grd.core.utils import file_lock

    # Filter None values so core function defaults ("") take effect
    kwargs: dict[str, str] = {}
    if value is not None:
        kwargs["value"] = value
    if uncertainty is not None:
        kwargs["uncertainty"] = uncertainty
    if phase is not None:
        kwargs["phase"] = phase
    if method is not None:
        kwargs["method"] = method

    cwd = _get_cwd()
    state_path = ProjectLayout(cwd).state_json

    with file_lock(state_path):
        try:
            state = _json.loads(state_path.read_text(encoding="utf-8"))
        except OSError:
            state = {}
        except _json.JSONDecodeError as e:
            _error(f"Malformed state.json: {e}")
        res = uncertainty_add(state, quantity=quantity or "", **kwargs)
        save_state_json_locked(cwd, state)
    _output(res)


@uncertainty_app.command("list")
def uncertainty_list() -> None:
    """List all tracked uncertainties."""
    from grd.core.extras import uncertainty_list

    _output(uncertainty_list(_load_state_dict()))


# ═══════════════════════════════════════════════════════════════════════════
# question
# ═══════════════════════════════════════════════════════════════════════════

question_app = typer.Typer(help="Open research questions")


@question_app.command("add")
def question_add(
    text: list[str] = typer.Argument(..., help="Question text"),
) -> None:
    """Add an open research question."""
    import json as _json

    from grd.core.constants import ProjectLayout
    from grd.core.extras import question_add
    from grd.core.state import save_state_json_locked
    from grd.core.utils import file_lock

    cwd = _get_cwd()
    state_path = ProjectLayout(cwd).state_json

    with file_lock(state_path):
        try:
            state = _json.loads(state_path.read_text(encoding="utf-8"))
        except OSError:
            state = {}
        except _json.JSONDecodeError as e:
            _error(f"Malformed state.json: {e}")
        res = question_add(state, " ".join(text))
        save_state_json_locked(cwd, state)
    _output(res)


@question_app.command("list")
def question_list() -> None:
    """List open research questions."""
    from grd.core.extras import question_list

    _output(question_list(_load_state_dict()))


@question_app.command("resolve")
def question_resolve(
    text: list[str] = typer.Argument(..., help="Question text to resolve"),
) -> None:
    """Mark a question as resolved."""
    import json as _json

    from grd.core.constants import ProjectLayout
    from grd.core.extras import question_resolve
    from grd.core.state import save_state_json_locked
    from grd.core.utils import file_lock

    cwd = _get_cwd()
    state_path = ProjectLayout(cwd).state_json

    with file_lock(state_path):
        try:
            state = _json.loads(state_path.read_text(encoding="utf-8"))
        except OSError:
            state = {}
        except _json.JSONDecodeError as e:
            _error(f"Malformed state.json: {e}")
        res = question_resolve(state, " ".join(text))
        save_state_json_locked(cwd, state)
    _output(res)


# ═══════════════════════════════════════════════════════════════════════════
# calculation
# ═══════════════════════════════════════════════════════════════════════════

calculation_app = typer.Typer(help="Calculation tracking")


@calculation_app.command("add")
def calculation_add(
    text: list[str] = typer.Argument(..., help="Calculation description"),
) -> None:
    """Add a calculation to track."""
    import json as _json

    from grd.core.constants import ProjectLayout
    from grd.core.extras import calculation_add
    from grd.core.state import save_state_json_locked
    from grd.core.utils import file_lock

    cwd = _get_cwd()
    state_path = ProjectLayout(cwd).state_json

    with file_lock(state_path):
        try:
            state = _json.loads(state_path.read_text(encoding="utf-8"))
        except OSError:
            state = {}
        except _json.JSONDecodeError as e:
            _error(f"Malformed state.json: {e}")
        res = calculation_add(state, " ".join(text))
        save_state_json_locked(cwd, state)
    _output(res)


@calculation_app.command("list")
def calculation_list() -> None:
    """List tracked calculations."""
    from grd.core.extras import calculation_list

    _output(calculation_list(_load_state_dict()))


@calculation_app.command("complete")
def calculation_complete(
    text: list[str] = typer.Argument(..., help="Calculation to mark complete"),
) -> None:
    """Mark a calculation as complete."""
    import json as _json

    from grd.core.constants import ProjectLayout
    from grd.core.extras import calculation_complete
    from grd.core.state import save_state_json_locked
    from grd.core.utils import file_lock

    cwd = _get_cwd()
    state_path = ProjectLayout(cwd).state_json

    with file_lock(state_path):
        try:
            state = _json.loads(state_path.read_text(encoding="utf-8"))
        except OSError:
            state = {}
        except _json.JSONDecodeError as e:
            _error(f"Malformed state.json: {e}")
        res = calculation_complete(state, " ".join(text))
        save_state_json_locked(cwd, state)
    _output(res)


# ═══════════════════════════════════════════════════════════════════════════
# config
# ═══════════════════════════════════════════════════════════════════════════

config_app = typer.Typer(help="GRD configuration")


@config_app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Config key path (dot-separated)"),
) -> None:
    """Get a configuration value."""
    try:
        from grd.core.config import effective_config_value, load_config

        config = load_config(_get_cwd())
        found, value = effective_config_value(config, key)
    except ConfigError as exc:
        _error(str(exc))
    if not found:
        _output({"key": key, "found": False})
        return
    _output({"key": key, "value": value, "found": True})


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key path (dot-separated)"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a configuration value."""
    from grd.core.config import apply_config_update, effective_config_value, load_config
    from grd.core.constants import ProjectLayout
    from grd.core.utils import atomic_write, file_lock

    config_path = ProjectLayout(_get_cwd()).config_json
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(config_path):
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raw = {}
        except json.JSONDecodeError as e:
            _error(f"Malformed config.json: {e}")
        except OSError as exc:
            _error(f"Cannot read config.json: {exc}")
        if not isinstance(raw, dict):
            _error("config.json must be a JSON object")
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            parsed = value
        try:
            updated_config, canonical_key = apply_config_update(raw, key, parsed)
        except ConfigError as exc:
            _error(str(exc))
        atomic_write(config_path, json.dumps(updated_config, indent=2) + "\n")

    config = load_config(_get_cwd())
    _found, effective_value = effective_config_value(config, key)
    _output({"key": key, "canonical_key": canonical_key, "value": effective_value, "updated": True})


@config_app.command("ensure-section")
def config_ensure_section() -> None:
    """Ensure config directory structure exists."""
    from grd.core.config import GRDProjectConfig
    from grd.core.constants import ProjectLayout
    from grd.core.utils import atomic_write

    config_path = ProjectLayout(_get_cwd()).config_json
    if config_path.exists():
        _output({"created": False, "path": str(config_path)})
        return
    config_path.parent.mkdir(parents=True, exist_ok=True)
    defaults = GRDProjectConfig()
    config_dict = {
        "autonomy": defaults.autonomy.value,
        "execution": {
            "review_cadence": defaults.review_cadence.value,
            "max_unattended_minutes_per_plan": defaults.max_unattended_minutes_per_plan,
            "max_unattended_minutes_per_wave": defaults.max_unattended_minutes_per_wave,
            "checkpoint_after_n_tasks": defaults.checkpoint_after_n_tasks,
            "checkpoint_after_first_load_bearing_result": defaults.checkpoint_after_first_load_bearing_result,
            "checkpoint_before_downstream_dependent_tasks": defaults.checkpoint_before_downstream_dependent_tasks,
        },
        "research_mode": defaults.research_mode.value,
        "commit_docs": defaults.commit_docs,
        "parallelization": defaults.parallelization,
        "model_profile": defaults.model_profile.value,
        "workflow": {
            "research": defaults.research,
            "plan_checker": defaults.plan_checker,
            "verifier": defaults.verifier,
        },
        "git": {
            "branching_strategy": defaults.branching_strategy.value,
            "phase_branch_template": defaults.phase_branch_template,
            "milestone_branch_template": defaults.milestone_branch_template,
        },
    }
    atomic_write(config_path, json.dumps(config_dict, indent=2) + "\n")
    _output({"created": True, "path": str(config_path)})


# ═══════════════════════════════════════════════════════════════════════════
# json — lightweight JSON manipulation (jq-lite)
# ═══════════════════════════════════════════════════════════════════════════

json_app = typer.Typer(help="JSON manipulation utilities (jq-lite)")


@json_app.command("get")
def json_get_cmd(
    key: str = typer.Argument(..., help="Dot-path key (e.g. .section, .directories[-1])"),
    default: str | None = typer.Option(None, "--default", help="Default value if key is missing"),
) -> None:
    """Read a value from stdin JSON at the given dot-path key."""

    from grd.core.json_utils import json_get

    stdin_text = sys.stdin.read()
    try:
        result = json_get(stdin_text, key, default=default)
    except ValueError as exc:
        _error(str(exc))
    _json_cli_output(result)


@json_app.command("keys")
def json_keys_cmd(
    key: str = typer.Argument(..., help="Dot-path to object (e.g. .waves)"),
) -> None:
    """List top-level keys of the object at the given path from stdin JSON."""

    from grd.core.json_utils import json_keys

    stdin_text = sys.stdin.read()
    result = json_keys(stdin_text, key)
    _json_cli_output(result)


@json_app.command("list")
def json_list_cmd(
    key: str = typer.Argument(..., help="Dot-path to array or object"),
) -> None:
    """List items from the array at the given path from stdin JSON."""

    from grd.core.json_utils import json_list

    stdin_text = sys.stdin.read()
    result = json_list(stdin_text, key)
    _json_cli_output(result)


@json_app.command("pluck")
def json_pluck_cmd(
    key: str = typer.Argument(..., help="Dot-path to array of objects"),
    field: str = typer.Argument(..., help="Field name to extract from each object"),
) -> None:
    """Extract a field from each object in the array at the given path."""

    from grd.core.json_utils import json_pluck

    stdin_text = sys.stdin.read()
    result = json_pluck(stdin_text, key, field)
    _json_cli_output(result)


@json_app.command("set")
def json_set_cmd(
    file: str = typer.Option(..., "--file", help="Path to JSON file"),
    path: str = typer.Option(..., "--path", help="Dot-path key to set"),
    value: str = typer.Option(..., "--value", help="Value to set"),
) -> None:
    """Set a key in a JSON file (creates file if needed)."""
    from grd.core.json_utils import json_set

    _json_cli_output(json_set(str(_get_cwd() / file), path, value))


@json_app.command("merge-files")
def json_merge_files_cmd(
    files: list[str] = typer.Argument(..., help="JSON files to merge"),
    out: str = typer.Option(..., "--out", help="Output file path"),
) -> None:
    """Merge multiple JSON files into one (shallow dict merge)."""
    from grd.core.json_utils import json_merge_files

    cwd = _get_cwd()
    _json_cli_output(json_merge_files(str(cwd / out), [str(cwd / f) for f in files]))


@json_app.command("sum-lengths")
def json_sum_lengths_cmd(
    keys: list[str] = typer.Argument(..., help="Dot-path keys to arrays"),
) -> None:
    """Sum the lengths of arrays at the given paths from stdin JSON."""

    from grd.core.json_utils import json_sum_lengths

    stdin_text = sys.stdin.read()
    result = json_sum_lengths(stdin_text, keys)
    _json_cli_output(result)


# ═══════════════════════════════════════════════════════════════════════════
# trace
# ═══════════════════════════════════════════════════════════════════════════

trace_app = typer.Typer(help="JSONL execution tracing for debugging and audit")


@trace_app.command("start")
def trace_start(
    phase: str = typer.Argument(..., help="Phase number"),
    plan: str = typer.Argument(..., help="Plan name"),
) -> None:
    """Start a new trace session."""
    from grd.core.trace import trace_start

    _output(trace_start(_get_cwd(), phase, plan))


@trace_app.command("log")
def trace_log(
    event: str = typer.Argument(..., help="Event type"),
    data: str | None = typer.Option(None, "--data", help="JSON event data"),
) -> None:
    """Log an event to the active trace."""
    from grd.core.trace import trace_log

    parsed_data = None
    if data:
        try:
            parsed_data = json.loads(data)
        except json.JSONDecodeError:
            parsed_data = {"raw": data}
    _output(trace_log(_get_cwd(), event, data=parsed_data))


@trace_app.command("stop")
def trace_stop() -> None:
    """Stop the active trace session."""
    from grd.core.trace import trace_stop

    _output(trace_stop(_get_cwd()))


@trace_app.command("show")
def trace_show(
    phase: str | None = typer.Option(None, "--phase", help="Filter by phase"),
    plan: str | None = typer.Option(None, "--plan", help="Filter by plan"),
    event_type: str | None = typer.Option(None, "--type", help="Filter by event type"),
    last: int | None = typer.Option(None, "--last", help="Show last N events"),
) -> None:
    """Show trace events with optional filters."""
    from grd.core.trace import trace_show

    _output(trace_show(_get_cwd(), phase=phase, plan=plan, event_type=event_type, last=last))


# ═══════════════════════════════════════════════════════════════════════════
# observe
# ═══════════════════════════════════════════════════════════════════════════

observe_app = typer.Typer(help="Inspect local observability sessions and events")


@observe_app.command("sessions")
def observe_sessions(
    status: str | None = typer.Option(None, "--status", help="Filter by session status"),
    command: str | None = typer.Option(None, "--command", help="Filter by command label"),
    last: int | None = typer.Option(None, "--last", help="Show most recent N sessions"),
) -> None:
    """List recorded local observability sessions."""
    _output(_filter_observability_sessions(_get_cwd(), status=status, command=command, last=last))


@observe_app.command("event")
def observe_event(
    category: str = typer.Argument(..., help="Event category"),
    name: str = typer.Argument(..., help="Event name"),
    action: str = typer.Option("log", "--action", help="Event action"),
    status: str = typer.Option("ok", "--status", help="Event status"),
    command: str | None = typer.Option(None, "--command", help="Associated command label"),
    phase: str | None = typer.Option(None, "--phase", help="Associated phase"),
    plan: str | None = typer.Option(None, "--plan", help="Associated plan"),
    session: str | None = typer.Option(None, "--session", help="Explicit session id"),
    data: str | None = typer.Option(None, "--data", help="JSON event payload"),
) -> None:
    """Append one local observability event."""
    parsed_data = None
    if data:
        try:
            raw_data = json.loads(data)
        except json.JSONDecodeError:
            parsed_data = {"raw": data}
        else:
            parsed_data = raw_data if isinstance(raw_data, dict) else {"value": raw_data}
    _output(
        _emit_observability_event(
            _get_cwd(),
            category=category,
            name=name,
            action=action,
            status=status,
            command=command,
            phase=phase,
            plan=plan,
            session_id=session,
            data=parsed_data,
            end_session=action in {"finish", "error", "stop"},
        )
    )


@observe_app.command("show")
def observe_show(
    session: str | None = typer.Option(None, "--session", help="Filter by session id"),
    category: str | None = typer.Option(None, "--category", help="Filter by event category"),
    name: str | None = typer.Option(None, "--name", help="Filter by event name"),
    action: str | None = typer.Option(None, "--action", help="Filter by event action"),
    status: str | None = typer.Option(None, "--status", help="Filter by event status"),
    command: str | None = typer.Option(None, "--command", help="Filter by command label"),
    phase: str | None = typer.Option(None, "--phase", help="Filter by phase"),
    plan: str | None = typer.Option(None, "--plan", help="Filter by plan"),
    last: int | None = typer.Option(None, "--last", help="Show last N matching events"),
) -> None:
    """Show local observability events with optional filters."""
    _output(
        _filter_observability_events(
            _get_cwd(),
            session=session,
            category=category,
            name=name,
            action=action,
            status=status,
            command=command,
            phase=phase,
            plan=plan,
            last=last,
        )
    )


# ═══════════════════════════════════════════════════════════════════════════
# commit
# ═══════════════════════════════════════════════════════════════════════════


@app.command("commit", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def commit(
    ctx: typer.Context,
    message: str = typer.Argument(..., help="Commit message"),
    files: list[str] | None = typer.Option(None, "--files", help="Files to stage and commit"),
) -> None:
    """Stage planning files and create a git commit.

    If --files is not specified, stages all .grd/ changes.
    Skips cleanly when commit_docs is disabled for the project.

    Examples::

        grd commit "docs: update roadmap" --files .grd/ROADMAP.md
        grd commit "docs: initialize research project" --files .grd/PROJECT.md .grd/state.json
        grd commit "wip: phase 3 progress"
    """
    from grd.core.git_ops import cmd_commit

    result = cmd_commit(_get_cwd(), message, files=_collect_file_option_args(ctx, files) or None)
    _output(result)
    if not result.committed and not getattr(result, "skipped", False):
        raise typer.Exit(code=1)


@app.command("pre-commit-check", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def pre_commit_check(
    ctx: typer.Context,
    files: list[str] | None = typer.Option(None, "--files", help="Files to validate"),
) -> None:
    """Run pre-commit validation on planning files.

    Checks storage-path policy, frontmatter YAML validity, and NaN/Inf values.
    If --files is omitted, validates the currently staged files.

    Examples::

        grd pre-commit-check --files .grd/ROADMAP.md .grd/STATE.md
    """
    from grd.core.git_ops import cmd_pre_commit_check

    result = cmd_pre_commit_check(_get_cwd(), _collect_file_option_args(ctx, files))
    _output(result)
    if not result.passed:
        raise typer.Exit(code=1)


# ═══════════════════════════════════════════════════════════════════════════
# version
# ═══════════════════════════════════════════════════════════════════════════


@app.command("version")
def version_cmd() -> None:
    """Show GRD version."""
    _print_version()


# ═══════════════════════════════════════════════════════════════════════════
# timestamp
# ═══════════════════════════════════════════════════════════════════════════


@app.command("timestamp")
def timestamp(
    fmt: str = typer.Argument("full", help="Format: date, filename, or full"),
) -> None:
    """Return current timestamp in the requested format."""
    from grd.core.commands import cmd_current_timestamp

    _output(cmd_current_timestamp(fmt))


# ═══════════════════════════════════════════════════════════════════════════
# slug
# ═══════════════════════════════════════════════════════════════════════════


@app.command("slug")
def slug(
    text: str = typer.Argument(..., help="Text to convert to a slug"),
) -> None:
    """Generate a URL-safe slug from text."""
    from grd.core.commands import cmd_generate_slug

    _output(cmd_generate_slug(text))


# ═══════════════════════════════════════════════════════════════════════════
# resolve-tier / resolve-model
# ═══════════════════════════════════════════════════════════════════════════


@app.command("resolve-tier")
def resolve_tier_cmd(
    agent_name: str = typer.Argument(..., help="Agent name (e.g. grd-executor)"),
) -> None:
    """Resolve the abstract model tier for an agent in the current project."""
    from grd.core.config import resolve_tier, validate_agent_name

    try:
        validate_agent_name(agent_name)
        _output(resolve_tier(_get_cwd(), agent_name))
    except ConfigError as exc:
        _error(str(exc))


@app.command("resolve-model")
def resolve_model_cmd(
    agent_name: str = typer.Argument(..., help="Agent name (e.g. grd-executor)"),
    runtime: str | None = typer.Option(
        None,
        "--runtime",
        help=_runtime_override_help(),
    ),
) -> None:
    """Resolve the runtime-specific model override for an agent.

    Prints nothing when no override is configured so callers can omit the
    runtime model parameter and let the platform use its default model.
    """
    from grd.core.config import resolve_model, validate_agent_name
    from grd.hooks.runtime_detect import detect_runtime_for_grd_use

    supported_runtimes = _supported_runtime_names()
    if runtime is not None and supported_runtimes and runtime not in supported_runtimes:
        supported = ", ".join(supported_runtimes)
        _error(f"Unknown runtime {runtime!r}. Supported: {supported}")

    active_runtime = runtime or detect_runtime_for_grd_use(cwd=_get_cwd())
    try:
        validate_agent_name(agent_name)
        _output(resolve_model(_get_cwd(), agent_name, runtime=active_runtime))
    except ConfigError as exc:
        _error(str(exc))


# ═══════════════════════════════════════════════════════════════════════════
# verify-path
# ═══════════════════════════════════════════════════════════════════════════


@app.command("verify-path")
def verify_path(
    target_path: str = typer.Argument(..., help="Path to verify (relative or absolute)"),
) -> None:
    """Verify whether a file or directory path exists."""
    from grd.core.commands import cmd_verify_path_exists

    result = cmd_verify_path_exists(_get_cwd(), target_path)
    _output(result)
    if not result.exists:
        raise typer.Exit(code=1)


# ═══════════════════════════════════════════════════════════════════════════
# history-digest
# ═══════════════════════════════════════════════════════════════════════════


@app.command("history-digest")
def history_digest() -> None:
    """Build a digest of project history from phase SUMMARY files."""
    from grd.core.commands import cmd_history_digest

    _output(cmd_history_digest(_get_cwd()))


# ═══════════════════════════════════════════════════════════════════════════
# summary-extract
# ═══════════════════════════════════════════════════════════════════════════


@app.command("summary-extract")
def summary_extract(
    summary_path: str = typer.Argument(..., help="Path to SUMMARY.md file (relative to cwd)"),
    field: list[str] | None = typer.Option(None, "--field", help="Specific fields to extract"),
) -> None:
    """Extract structured data from a SUMMARY.md file."""
    from grd.core.commands import cmd_summary_extract

    _output(cmd_summary_extract(_get_cwd(), summary_path, fields=field))


# ═══════════════════════════════════════════════════════════════════════════
# regression-check
# ═══════════════════════════════════════════════════════════════════════════


@app.command("regression-check")
def regression_check(
    quick: bool = typer.Option(False, "--quick", help="Only check most recent 2 completed phases"),
) -> None:
    """Check for regressions across completed phases."""
    from grd.core.commands import cmd_regression_check

    result = cmd_regression_check(_get_cwd(), quick=quick)
    _output(result)
    if not result.passed:
        raise typer.Exit(code=1)


# ═══════════════════════════════════════════════════════════════════════════
# validate-return
# ═══════════════════════════════════════════════════════════════════════════


@app.command("validate-return")
def validate_return(
    file_path: str = typer.Argument(..., help="Path to file containing grd_return YAML block"),
) -> None:
    """Validate a grd_return YAML block in a file."""
    from grd.core.commands import cmd_validate_return

    resolved = _get_cwd() / file_path
    result = cmd_validate_return(resolved)
    _output(result)
    if not result.passed:
        raise typer.Exit(code=1)
