"""Shared CLI helpers, output utilities, global state, and the main app/callback.

All submodules import from here for ``_output``, ``_error``, ``_get_cwd``,
``console``, ``err_console``, the ``app`` instance, etc.
"""

from __future__ import annotations

import dataclasses
import json
import os
import shlex
import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

import typer
from pydantic import ValidationError as PydanticValidationError
from rich.console import Console
from rich.table import Table
from rich.text import Text

from grd.core.constants import ENV_GRD_DISABLE_CHECKOUT_REEXEC
from grd.core.errors import GRDError

if TYPE_CHECKING:
    from grd.mcp.paper.models import PaperConfig

# ─── Output helpers ─────────────────────────────────────────────────────────

console = Console()
err_console = Console(stderr=True)

# Global state threaded through typer context
_raw: bool = False
_cwd: Path = Path(".")


def _output(data: object) -> None:
    """Print result -- JSON when --raw, rich text otherwise."""
    if _raw:
        if data is None:
            console.print_json(json.dumps({"result": None}))
        elif isinstance(data, (list, tuple)):
            items = [
                item.model_dump(mode="json", by_alias=True)
                if hasattr(item, "model_dump")
                else dataclasses.asdict(item)
                if dataclasses.is_dataclass(item) and not isinstance(item, type)
                else item
                for item in data
            ]
            console.print_json(json.dumps(items, default=str))
        elif hasattr(data, "model_dump"):
            console.print_json(json.dumps(data.model_dump(mode="json", by_alias=True), default=str))
        elif dataclasses.is_dataclass(data) and not isinstance(data, type):
            console.print_json(json.dumps(dataclasses.asdict(data), default=str))
        elif isinstance(data, dict):
            console.print_json(json.dumps(data, default=str))
        else:
            console.print_json(json.dumps({"result": str(data)}, default=str))
    else:
        if data is None:
            return  # nothing to display
        elif isinstance(data, (list, tuple)):
            for item in data:
                _output(item)
        elif hasattr(data, "model_dump"):
            _pretty_print(data.model_dump(mode="json", by_alias=True))
        elif dataclasses.is_dataclass(data) and not isinstance(data, type):
            _pretty_print(dataclasses.asdict(data))
        elif isinstance(data, dict):
            _pretty_print(data)
        else:
            console.print(str(data))


def _pretty_print(d: dict) -> None:
    """Render a dict as a rich table."""
    table = Table(show_header=True, header_style=f"bold {_INSTALL_ACCENT_COLOR}")
    table.add_column("Key")
    table.add_column("Value")
    for k, v in d.items():
        val = json.dumps(v, default=str) if isinstance(v, (dict, list)) else str(v)
        table.add_row(str(k), val)
    console.print(table)


def _error(msg: str, *, code: int = 1) -> NoReturn:
    """Print error and exit -- JSON when --raw, rich text otherwise."""
    if _raw:
        err_console.print_json(json.dumps({"error": str(msg)}))
    else:
        err_console.print(f"[bold red]Error:[/] {msg}", highlight=False)
    raise typer.Exit(code=code)


def _get_cwd() -> Path:
    return _cwd.resolve()


def _split_global_cli_options(argv: list[str]) -> tuple[list[str], list[str]]:
    """Partition root-global CLI options from the rest of the argv stream.

    This keeps ``--raw`` / ``--json`` and ``--cwd`` usable even when agents
    append them after the subcommand, while still respecting the ``--``
    end-of-options marker. ``--json`` is an alias for ``--raw``; both hoist
    identically.
    """
    global_args: list[str] = []
    remaining_args: list[str] = []
    passthrough = False
    index = 0

    while index < len(argv):
        arg = str(argv[index])
        if passthrough:
            remaining_args.append(arg)
            index += 1
            continue

        if arg == "--":
            passthrough = True
            remaining_args.append(arg)
            index += 1
            continue

        if arg in ("--raw", "--json"):
            global_args.append(arg)
            index += 1
            continue

        if arg == "--cwd":
            global_args.append(arg)
            if index + 1 < len(argv):
                global_args.append(str(argv[index + 1]))
                index += 2
            else:
                index += 1
            continue

        if arg.startswith("--cwd="):
            global_args.append(arg)
            index += 1
            continue

        remaining_args.append(arg)
        index += 1

    return global_args, remaining_args


def _normalize_global_cli_options(argv: list[str]) -> list[str]:
    """Move root-global options to the front of the argv stream."""
    global_args, remaining_args = _split_global_cli_options(argv)
    return [*global_args, *remaining_args]


def _resolve_cli_cwd_from_argv(argv: list[str]) -> Path:
    """Resolve the effective CLI cwd from raw argv before Typer parses it."""
    raw_cwd = "."
    global_args, _ = _split_global_cli_options(argv)
    for index, arg in enumerate(global_args):
        if arg == "--cwd" and index + 1 < len(global_args):
            raw_cwd = global_args[index + 1]
            break
        if arg.startswith("--cwd="):
            raw_cwd = arg.split("=", 1)[1]
            break

    candidate = Path(raw_cwd).expanduser()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    return (Path.cwd() / candidate).resolve(strict=False)


def _maybe_reexec_from_checkout(argv: list[str] | None = None) -> None:
    """Re-exec through the nearest checkout when launched from an installed package."""
    from grd.version import checkout_root

    if os.environ.get(ENV_GRD_DISABLE_CHECKOUT_REEXEC) == "1":
        return

    effective_argv = list(sys.argv[1:] if argv is None else argv)
    root = checkout_root(_resolve_cli_cwd_from_argv(effective_argv))
    if root is None:
        return

    checkout_grd = (root / "src" / "grd").resolve(strict=False)
    active_grd = Path(__file__).resolve().parent.parent
    if active_grd == checkout_grd:
        return

    env = os.environ.copy()
    checkout_src = str((root / "src").resolve(strict=False))
    existing_pythonpath = [entry for entry in env.get("PYTHONPATH", "").split(os.pathsep) if entry]
    if checkout_src not in existing_pythonpath:
        env["PYTHONPATH"] = (
            os.pathsep.join([checkout_src, *existing_pythonpath]) if existing_pythonpath else checkout_src
        )
    env[ENV_GRD_DISABLE_CHECKOUT_REEXEC] = "1"
    os.execve(sys.executable, [sys.executable, "-m", "grd.cli", *effective_argv], env)


def _format_display_path(target: str | Path | None) -> str:
    """Format a path for concise, user-facing CLI output."""
    if target is None:
        return ""

    raw_target = str(target)
    if not raw_target:
        return ""

    target_path = Path(raw_target).expanduser()
    if not target_path.is_absolute():
        target_path = _get_cwd() / target_path

    resolved_target = target_path.resolve(strict=False)
    resolved_cwd = _get_cwd().expanduser().resolve(strict=False)
    resolved_home = Path.home().expanduser().resolve(strict=False)

    try:
        relative_to_cwd = resolved_target.relative_to(resolved_cwd)
    except ValueError:
        pass
    else:
        relative_text = relative_to_cwd.as_posix()
        return "." if relative_text in ("", ".") else f"./{relative_text}"

    try:
        relative_to_home = resolved_target.relative_to(resolved_home)
    except ValueError:
        return resolved_target.as_posix()

    relative_text = relative_to_home.as_posix()
    return "~" if relative_text in ("", ".") else f"~/{relative_text}"


@dataclasses.dataclass(frozen=True)
class ReviewPreflightCheck:
    """One executable preflight check for a review command."""

    name: str
    passed: bool
    blocking: bool
    detail: str


@dataclasses.dataclass(frozen=True)
class ReviewPreflightResult:
    """Summary of preflight readiness for a review-grade command."""

    command: str
    review_mode: str
    strict: bool
    passed: bool
    checks: list[ReviewPreflightCheck]
    required_outputs: list[str]
    required_evidence: list[str]
    blocking_conditions: list[str]


@dataclasses.dataclass(frozen=True)
class CommandContextCheck:
    """One executable context check for a command."""

    name: str
    passed: bool
    blocking: bool
    detail: str


@dataclasses.dataclass(frozen=True)
class CommandContextPreflightResult:
    """Summary of whether a command can run in the current workspace context."""

    command: str
    context_mode: str
    passed: bool
    project_exists: bool
    explicit_inputs: list[str]
    guidance: str
    checks: list[CommandContextCheck]


def _format_runtime_list(runtime_names: list[str]) -> str:
    """Render runtime identifiers as human-friendly names."""
    from grd.adapters import get_adapter

    display_names = [get_adapter(runtime_name).display_name for runtime_name in runtime_names]
    if not display_names:
        return "no runtimes"
    if len(display_names) == 1:
        return display_names[0]
    if len(display_names) == 2:
        return f"{display_names[0]} and {display_names[1]}"
    return f"{', '.join(display_names[:-1])}, and {display_names[-1]}"


def _supported_runtime_names() -> list[str]:
    """Return runtime ids from the loaded adapter registry."""
    from grd.adapters import list_runtimes

    try:
        return list_runtimes()
    except Exception:
        return []


def _runtime_override_help() -> str:
    """Build runtime option help from adapter metadata."""
    supported = _supported_runtime_names()
    if not supported:
        return "Runtime name override"
    return f"Runtime name override ({', '.join(supported)})"


def _print_version(*, ctx: typer.Context | None = None) -> None:
    """Emit the CLI version using the active raw/non-raw output contract."""
    from grd.version import resolve_active_version

    cwd = _get_cwd()
    if ctx is not None:
        raw_cwd = ctx.params.get("cwd")
        if isinstance(raw_cwd, str) and raw_cwd.strip():
            cwd = Path(raw_cwd)

    value = f"grd {resolve_active_version(cwd)}"
    raw_requested = False
    if ctx is not None:
        meta_raw = ctx.meta.get("raw_requested")
        if isinstance(meta_raw, bool):
            raw_requested = meta_raw
    if not raw_requested:
        raw_requested = _raw
    if raw_requested:
        console.print_json(json.dumps({"result": value}))
    else:
        console.print(value)


def _raw_option_callback(ctx: typer.Context, _: typer.CallbackParam, value: bool) -> bool:
    """Capture --json / --raw early enough for the eager --version option."""
    global _raw  # noqa: PLW0603
    ctx.meta["raw_requested"] = value
    _raw = value
    return value


def _version_option_callback(ctx: typer.Context, _: typer.CallbackParam, value: bool) -> bool:
    """Handle --version before Typer requires a subcommand."""
    if value:
        _print_version(ctx=ctx)
        raise typer.Exit()
    return value


def _json_cli_output(data: object) -> None:
    """Emit literal JSON for the lightweight JSON subcommands.

    In --raw mode, serializes as JSON (with Pydantic/dataclass support).
    In non-raw mode, prints plain text (no Rich table wrapper).
    """
    if hasattr(data, "model_dump"):
        serializable = data.model_dump(mode="json", by_alias=True)
    elif dataclasses.is_dataclass(data) and not isinstance(data, type):
        serializable = dataclasses.asdict(data)
    else:
        serializable = data

    if _raw:
        console.print_json(json.dumps(serializable, default=str))
    else:
        console.print(serializable, highlight=False)


def _format_pydantic_schema_error(error: dict[str, object], *, root_label: str) -> str:
    """Return a concise, user-facing schema error."""

    location = ".".join(str(part) for part in error.get("loc", ()) if str(part))
    label = f"{root_label}.{location}" if location else root_label
    message = str(error.get("msg", "validation failed")).strip() or "validation failed"
    input_value = error.get("input")

    if message == "Field required":
        return f"{label} is required"
    if "valid dictionary" in message.lower():
        return f"{label} must be an object, not {type(input_value).__name__}"
    if "valid list" in message.lower():
        return f"{label} must be an array, not {type(input_value).__name__}"
    return f"{label}: {message}"


def _raise_pydantic_schema_error(
    *,
    label: str,
    exc: PydanticValidationError,
    schema_reference: str | None = None,
) -> NoReturn:
    """Render Pydantic payload errors without a traceback and exit."""

    rendered: list[str] = []
    seen: set[str] = set()
    for error in exc.errors():
        formatted = _format_pydantic_schema_error(error, root_label=label)
        if formatted in seen:
            continue
        seen.add(formatted)
        rendered.append(formatted)

    message = "; ".join(rendered[:5]) or f"{label} validation failed"
    if len(rendered) > 5:
        message += f" (+{len(rendered) - 5} more)"
    if schema_reference:
        message += f". See `{schema_reference}`"
    _error(message)


def _collect_file_option_args(ctx: typer.Context, files: list[str] | None) -> list[str]:
    """Return normalized file args, allowing multiple paths after one ``--files``."""

    normalized_files = list(files or [])
    extra_args = [str(arg).strip() for arg in ctx.args if str(arg).strip()]
    if not extra_args:
        return normalized_files

    unexpected_options = [arg for arg in extra_args if arg.startswith("-")]
    if unexpected_options:
        _error("Unexpected option(s): " + " ".join(unexpected_options))

    if files is None:
        _error("Unexpected extra arguments. If these are file paths, pass them after --files.")

    normalized_files.extend(extra_args)
    return normalized_files


def _emit_observability_event(
    cwd: Path,
    *,
    category: str,
    name: str,
    action: str = "log",
    status: str = "ok",
    command: str | None = None,
    phase: str | None = None,
    plan: str | None = None,
    session_id: str | None = None,
    data: dict[str, object] | None = None,
    end_session: bool = False,
) -> object:
    from grd.core.observability import observe_event

    result = observe_event(
        cwd.resolve(strict=False),
        category=category,
        name=name,
        action=action,
        status=status,
        command=command,
        phase=phase,
        plan=plan,
        session_id=session_id,
        data=data,
        end_session=end_session,
    )
    if hasattr(result, "recorded") and result.recorded is False:
        raise GRDError("Local observability unavailable for this working directory")
    return result


def _filter_observability_events(
    cwd: Path,
    *,
    session: str | None = None,
    category: str | None = None,
    name: str | None = None,
    action: str | None = None,
    status: str | None = None,
    command: str | None = None,
    phase: str | None = None,
    plan: str | None = None,
    last: int | None = None,
) -> dict[str, object]:
    from grd.core.observability import show_events

    return show_events(
        cwd,
        session=session,
        category=category,
        name=name,
        action=action,
        status=status,
        command=command,
        phase=phase,
        plan=plan,
        last=last,
    ).model_dump(mode="json")


def _filter_observability_sessions(
    cwd: Path,
    *,
    status: str | None = None,
    command: str | None = None,
    last: int | None = None,
) -> dict[str, object]:
    from grd.core.observability import list_sessions

    sessions = list_sessions(cwd, command=command, last=last).model_dump(mode="json")
    if status:
        filtered = [session_info for session_info in sessions["sessions"] if str(session_info.get("status")) == status]
        return {"count": len(filtered), "sessions": filtered}
    return sessions


def _load_state_dict() -> dict:
    """Load state.json as a plain dict for commands that need raw state."""
    import json

    from grd.core.constants import ProjectLayout

    state_path = ProjectLayout(_get_cwd()).state_json
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except OSError:
        return {}
    except json.JSONDecodeError as e:
        _error(f"Malformed state.json: {e}")
    if not isinstance(data, dict):
        _error(f"state.json must be a JSON object, got {type(data).__name__}")
    return data


def _load_json_document(input_path: str) -> object:
    """Load a JSON document from a file path or stdin marker ``-``."""

    if input_path == "-":
        raw = sys.stdin.read()
        source = "stdin"
    else:
        target = Path(input_path)
        if not target.is_absolute():
            target = _get_cwd() / target
        source = _format_display_path(target)
        try:
            raw = target.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise GRDError(f"JSON input not found: {source}") from exc
        except OSError as exc:
            raise GRDError(f"Failed to read JSON input from {source}: {exc}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise GRDError(f"Invalid JSON from {source}: {exc}") from exc


def _load_text_document(input_path: str) -> tuple[Path, str]:
    """Load a UTF-8 text document relative to the effective CLI cwd."""

    target = Path(input_path)
    if not target.is_absolute():
        target = _get_cwd() / target
    source = _format_display_path(target)
    try:
        return target, target.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise GRDError(f"Text input not found: {source}") from exc
    except OSError as exc:
        raise GRDError(f"Failed to read text input from {source}: {exc}") from exc


def _first_existing_path(*candidates: Path) -> Path | None:
    """Return the first existing path from *candidates*, if any."""
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _resolve_existing_input_path(input_path: str | None, *, candidates: tuple[str, ...], label: str) -> Path:
    """Resolve an explicit or default input path under the current cwd."""
    if input_path:
        target = Path(input_path)
        if not target.is_absolute():
            target = _get_cwd() / target
        if not target.exists():
            raise GRDError(f"{label} not found: {_format_display_path(target)}")
        return target

    resolved = _first_existing_path(*(_get_cwd() / candidate for candidate in candidates))
    if resolved is not None:
        return resolved

    searched = ", ".join(candidates)
    raise GRDError(f"No {label} found. Searched: {searched}")


def _resolve_paper_config_paths(config: object, *, base_dir: Path) -> PaperConfig:
    """Resolve relative figure paths in a PaperConfig against its config file directory."""
    from grd.mcp.paper.models import FigureRef, PaperConfig

    paper_config = PaperConfig.model_validate(config)
    if not paper_config.figures:
        return paper_config

    resolved_figures: list[FigureRef] = []
    for figure in paper_config.figures:
        resolved_path = figure.path if figure.path.is_absolute() else (base_dir / figure.path).resolve(strict=False)
        resolved_figures.append(figure.model_copy(update={"path": resolved_path}))
    return paper_config.model_copy(update={"figures": resolved_figures})


def _resolve_bibliography_path(
    *,
    explicit_path: str | None,
    config_path: Path,
    output_dir: Path,
    bib_stem: str,
) -> Path | None:
    """Resolve an optional bibliography source path for a paper build."""
    if explicit_path:
        target = Path(explicit_path)
        if not target.is_absolute():
            target = _get_cwd() / target
        if not target.exists():
            raise GRDError(f"Bibliography file not found: {_format_display_path(target)}")
        return target

    candidates = (
        config_path.parent / f"{bib_stem}.bib",
        output_dir / f"{bib_stem}.bib",
        _get_cwd() / "references" / f"{bib_stem}.bib",
    )
    return _first_existing_path(*candidates)


def _default_paper_output_dir(config_file: Path) -> Path:
    """Resolve the default durable output directory for a paper build."""
    return config_file.resolve(strict=False).parent


def _reject_legacy_paper_config_location(config_file: Path) -> None:
    """Reject removed paper-config locations under internal planning storage."""
    from grd.core.storage_paths import ProjectStorageLayout

    legacy_config_root = ProjectStorageLayout(_get_cwd()).internal_root / "paper"
    resolved_config = config_file.resolve(strict=False)
    try:
        resolved_config.relative_to(legacy_config_root)
    except ValueError:
        return
    raise GRDError(
        "Paper configs under `.grd/paper/` are no longer supported. "
        "Move the config to `paper/`, `manuscript/`, or `draft/`."
    )


def _split_command_arguments(arguments: str | None) -> list[str]:
    """Split a raw command argument string into shell-like tokens."""
    if not arguments:
        return []
    try:
        return shlex.split(arguments)
    except ValueError:
        return arguments.split()


def _has_flag_value(tokens: list[str], flag: str) -> bool:
    """Return True when ``flag`` is present with a non-empty value."""
    for index, token in enumerate(tokens):
        if token == flag:
            if index + 1 < len(tokens):
                next_token = tokens[index + 1]
                if next_token and not next_token.startswith("-"):
                    return True
        elif token.startswith(f"{flag}="):
            return bool(token.partition("=")[2].strip())
    return False


def _positional_tokens(arguments: str | None, *, flags_with_values: tuple[str, ...] = ()) -> list[str]:
    """Extract positional tokens after removing known long-option/value pairs."""
    tokens = _split_command_arguments(arguments)
    positionals: list[str] = []
    skip_next = False
    value_flags = set(flags_with_values)

    for index, token in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue
        if token == "--":
            return positionals + tokens[index + 1 :]
        if token in value_flags:
            skip_next = True
            continue
        if any(token.startswith(f"{flag}=") for flag in value_flags):
            continue
        if token.startswith("--"):
            continue
        positionals.append(token)

    return positionals


def _has_discover_explicit_inputs(arguments: str | None) -> bool:
    """Discover standalone mode needs either a phase number or a topic."""
    return bool(_positional_tokens(arguments, flags_with_values=("--depth", "-d")))


def _has_simple_positional_inputs(arguments: str | None) -> bool:
    """Generic detector for commands satisfied by any positional topic/target."""
    return bool(_positional_tokens(arguments))


def _has_sensitivity_explicit_inputs(arguments: str | None) -> bool:
    """Sensitivity analysis standalone mode requires both target and parameter list."""
    tokens = _split_command_arguments(arguments)
    return _has_flag_value(tokens, "--target") and _has_flag_value(tokens, "--params")


_PROJECT_AWARE_EXPLICIT_INPUTS: dict[str, tuple[list[str], Callable[[str | None], bool]]] = {
    "grd:compare-experiment": (["prediction, dataset path, or phase identifier"], _has_simple_positional_inputs),
    "grd:compare-results": (["phase, artifact, or comparison target"], _has_simple_positional_inputs),
    "grd:derive-equation": (["equation or topic to derive"], _has_simple_positional_inputs),
    "grd:dimensional-analysis": (["phase number or file path"], _has_simple_positional_inputs),
    "grd:discover": (["phase number or standalone topic"], _has_discover_explicit_inputs),
    "grd:explain": (["concept, result, method, notation, or paper"], _has_simple_positional_inputs),
    "grd:limiting-cases": (["phase number or file path"], _has_simple_positional_inputs),
    "grd:literature-review": (["topic or research question"], _has_simple_positional_inputs),
    "grd:numerical-convergence": (["phase number or file path"], _has_simple_positional_inputs),
    "grd:sensitivity-analysis": (["--target quantity", "--params p1,p2,..."], _has_sensitivity_explicit_inputs),
}


def _build_project_aware_guidance(explicit_inputs: list[str]) -> str:
    """Render the standardized project-aware guidance string."""
    if not explicit_inputs:
        return "Either provide explicit inputs for this command, or run `grd init new-project`."
    if len(explicit_inputs) == 1:
        requirement_text = explicit_inputs[0]
    elif len(explicit_inputs) == 2:
        requirement_text = f"{explicit_inputs[0]} and {explicit_inputs[1]}"
    else:
        requirement_text = ", ".join(explicit_inputs[:-1]) + f", and {explicit_inputs[-1]}"
    return f"Either provide {requirement_text} explicitly, or run `grd init new-project`."


def _unique_preserving_order(values: list[str]) -> list[str]:
    """Return unique strings from *values* without reordering first appearances."""
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _canonical_command_name(command_name: str) -> str:
    """Normalize a CLI command name to the registry's public grd:name form."""
    normalized = command_name.strip()
    if normalized.startswith("/"):
        normalized = normalized[1:]
    return normalized if normalized.startswith("grd:") else f"grd:{normalized}"


def _resolve_registry_command(command_name: str) -> tuple[object, str]:
    """Resolve a command name through the registry and preserve its public name."""
    from grd import registry as content_registry

    command = content_registry.get_command(command_name)
    return command, _canonical_command_name(command_name)


def _parse_meta_options(meta: list[str] | None) -> dict[str, str]:
    """Parse --meta key=value pairs into a dict."""
    if not meta:
        return {}
    result: dict[str, str] = {}
    for item in meta:
        if "=" not in item:
            raise typer.BadParameter(f"--meta must be key=value, got: {item!r}")
        key, _, value = item.partition("=")
        key = key.strip()
        if not key:
            raise typer.BadParameter(f"--meta key must be non-empty, got: {item!r}")
        result[key] = value
    return result


def _run_frontmatter_validation(file: str, schema: str) -> None:
    """Validate one markdown file against a named frontmatter schema."""

    from grd.core.frontmatter import validate_frontmatter

    file_path, fm_content = _load_text_document(file)
    result = validate_frontmatter(fm_content, schema, source_path=file_path)
    _output(result)
    if not result.valid:
        raise typer.Exit(code=1)


def _resolve_cli_target_dir(target_dir: str) -> Path:
    """Resolve a CLI target-dir argument relative to the active --cwd."""
    resolved = Path(target_dir).expanduser()
    if resolved.is_absolute():
        return resolved
    return _get_cwd() / resolved


# ─── Install branding constants ─────────────────────────────────────────────

_GRD_BANNER = r"""
 ██████╗ ██████╗ ██████╗
██╔════╝ ██╔══██╗██╔══██╗
██║  ███╗██████╔╝██║  ██║
██║   ██║██╔═══╝ ██║  ██║
╚██████╔╝██║     ██████╔╝
 ╚═════╝ ╚═╝     ╚═════╝
"""

_GRD_DISPLAY_NAME = "Get Research Done"
_GRD_OWNER = "Physical Superintelligence PBC"
_GRD_OWNER_SHORT = "PSI"
_GRD_COPYRIGHT_YEAR = 2026
_INSTALL_LOGO_COLOR = "#F3F0E8"
_INSTALL_TITLE_COLOR = "#F7F4ED"
_INSTALL_META_COLOR = "#9E988C"
_INSTALL_ACCENT_COLOR = "#D8C7A3"


def _format_install_header_lines(version: str) -> tuple[str, str]:
    """Return the branded header shown during interactive install."""
    return (
        f"GRD v{version} - {_GRD_DISPLAY_NAME}",
        f"\u00a9 {_GRD_COPYRIGHT_YEAR} {_GRD_OWNER} ({_GRD_OWNER_SHORT})",
    )


def _render_install_option_line(index: int, label: str, *details: str, label_width: int | None = None) -> Text:
    """Return a single-line formatted install menu option."""
    rendered = Text("  ")
    rendered.append(f"[{index}]", style=f"bold {_INSTALL_ACCENT_COLOR}")
    rendered.append(" ")
    rendered.append(label.ljust(label_width or len(label)), style=f"bold {_INSTALL_TITLE_COLOR}")
    filtered_details = [detail for detail in details if detail]
    if filtered_details:
        rendered.append("  ")
        for detail_index, detail in enumerate(filtered_details):
            if detail_index:
                rendered.append(" ")
            rendered.append("\u00b7", style=f"bold {_INSTALL_ACCENT_COLOR}")
            rendered.append(" ")
            rendered.append(detail, style=f"dim {_INSTALL_META_COLOR}")
    return rendered


def _render_install_choice_prompt() -> Text:
    """Return the shared interactive prompt label for install menus."""
    rendered = Text()
    rendered.append("Enter choice", style=f"bold {_INSTALL_TITLE_COLOR}")
    rendered.append(" [1]", style=f"dim {_INSTALL_META_COLOR}")
    return rendered


# ─── App setup ──────────────────────────────────────────────────────────────


class _GRDTyper(typer.Typer):
    """Typer subclass that catches GRDError and prints a user-friendly message."""

    def __call__(self, *args: object, **kwargs: object) -> object:
        global _raw, _cwd  # noqa: PLW0603
        _raw = False
        _cwd = Path(".")
        normalized_kwargs = dict(kwargs)
        raw_args = normalized_kwargs.get("args")
        if raw_args is None and not args:
            raw_args = sys.argv[1:]
        if raw_args is not None:
            normalized_kwargs["args"] = _normalize_global_cli_options([str(arg) for arg in raw_args])
        try:
            return super().__call__(*args, **normalized_kwargs)
        except KeyError as exc:
            msg = f"Internal error (missing key): {exc}"
            if _raw:
                err_console.print_json(json.dumps({"error": msg}))
            else:
                err_console.print(f"[bold red]Error:[/] {msg}", highlight=False)
            raise SystemExit(1) from None
        except GRDError as exc:
            if _raw:
                err_console.print_json(json.dumps({"error": str(exc)}))
            else:
                err_console.print(f"[bold red]Error:[/] {exc}", highlight=False)
            raise SystemExit(1) from None
        except TimeoutError as exc:
            if _raw:
                err_console.print_json(json.dumps({"error": str(exc)}))
            else:
                err_console.print(f"[bold red]Error:[/] {exc}", highlight=False)
            raise SystemExit(1) from None
        except SystemExit:
            raise
        except Exception:
            raise


app = _GRDTyper(
    name="grd",
    help="GRD \u2014 Get Research Done: domain-agnostic research CLI",
    no_args_is_help=True,
    add_completion=True,
)


@app.callback()
def main(
    _ctx: typer.Context,
    raw: bool = typer.Option(
        False,
        "--json",
        "--raw",
        help="Emit JSON output for programmatic consumption (alias: --raw)",
        callback=_raw_option_callback,
        is_eager=True,
    ),
    cwd: str = typer.Option(".", "--cwd", help="Working directory (default: current)"),
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version",
        callback=_version_option_callback,
        is_eager=True,
    ),
) -> None:
    """GRD \u2014 Get Research Done."""
    global _raw, _cwd  # noqa: PLW0603
    _raw = raw
    _cwd = Path(cwd)
