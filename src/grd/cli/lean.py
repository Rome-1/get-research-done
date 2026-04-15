"""``grd lean ...`` — Lean 4 verification backend.

Thin typer surface over ``grd.core.lean.*``. See that package's ``__init__``
for the layering rationale and PITCH.md §Architecture Design for the
"CLI + skills, not MCP" decision.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer

from grd.cli import _helpers
from grd.cli._helpers import _error, _get_cwd, _output, console, err_console

if TYPE_CHECKING:
    from grd.core.lean.protocol import LeanCheckResult
    from grd.core.lean.prove import ProveResult

lean_app = typer.Typer(help="Lean 4 verification backend (type-check, proof daemon, env)")


def _print_diagnostic_hints(result: LeanCheckResult) -> None:
    """Print per-diagnostic hints to stderr for human consumption.

    Runs after ``_output`` in non-raw mode so the rendered rich table still
    owns the primary presentation but the error-explanation layer surfaces a
    concrete next-step under each diagnostic Lean produced. Skipped when the
    caller asked for ``--raw`` — the JSON already carries ``hint`` fields,
    and duplicating them to stderr would interleave with machine consumers.
    """
    if _helpers._raw:
        return
    diagnostics = getattr(result, "diagnostics", None) or []
    with_hints = [d for d in diagnostics if getattr(d, "hint", None)]
    if not with_hints:
        return
    err_console.print("")
    err_console.print("[bold]Hints[/]", highlight=False)
    for diag in with_hints:
        loc = ""
        if getattr(diag, "line", None) is not None:
            col = getattr(diag, "column", None)
            loc = f" (line {diag.line}" + (f":{col}" if col is not None else "") + ")"
        severity = getattr(diag, "severity", "error")
        err_console.print(f"  [dim]{severity}{loc}[/] {diag.hint}", highlight=False)


def _print_prove_hints(result: ProveResult) -> None:
    """Print the hint for the last failing tactic attempt, if any."""
    if _helpers._raw or getattr(result, "ok", True):
        return
    last_hint: str | None = None
    last_tactic: str | None = None
    for attempt in getattr(result, "attempts", []) or []:
        if getattr(attempt, "hint", None):
            last_hint = attempt.hint
            last_tactic = attempt.tactic
    if not last_hint:
        return
    err_console.print("")
    err_console.print("[bold]Hint[/]", highlight=False)
    err_console.print(f"  [dim]last tactic: {last_tactic}[/] {last_hint}", highlight=False)


def _print_verify_claim_hints(result: object) -> None:
    """Surface hints from the last failing candidate's last compile step.

    verify-claim runs a repair loop per candidate; diagnostics are only kept
    inside ``RepairStep.lean_hints``. When no candidate compiles we print the
    hints from the most-informative failing step so the human sees *why* the
    pipeline escalated without hunting through the JSON trace.
    """
    if _helpers._raw:
        return
    if getattr(result, "outcome", None) == "auto_accept":
        return
    candidates = getattr(result, "candidates", []) or []
    hints: list[str] = []
    for cand in reversed(candidates):
        repair = getattr(cand, "repair", None)
        steps = getattr(repair, "steps", None) or []
        for step in reversed(steps):
            step_hints = getattr(step, "lean_hints", None) or []
            if step_hints:
                hints = list(step_hints)
                break
        if hints:
            break
    if not hints:
        return
    err_console.print("")
    err_console.print("[bold]Hints[/]", highlight=False)
    for h in hints:
        err_console.print(f"  {h}", highlight=False)


@lean_app.command("check")
def lean_check(
    code: str | None = typer.Argument(
        None,
        help="Inline Lean 4 source. Omit and pipe via stdin, or use --file.",
    ),
    file: Path | None = typer.Option(
        None,
        "--file",
        "-f",
        help="Path to a .lean file to type-check (alternative to inline code).",
    ),
    import_module: list[str] = typer.Option(
        [],
        "--import",
        "-i",
        help="Module to prepend as 'import <module>'. Repeatable.",
    ),
    timeout_s: float = typer.Option(
        30.0,
        "--timeout",
        help="Hard wall-clock timeout for Lean in seconds.",
        min=0.1,
        max=600.0,
    ),
    no_daemon: bool = typer.Option(
        False,
        "--no-daemon",
        help="Skip the socket daemon; run Lean directly in this process's child.",
    ),
    no_spawn: bool = typer.Option(
        False,
        "--no-spawn",
        help="Do not auto-spawn the daemon if the socket is absent (implies one-shot).",
    ),
) -> None:
    """Type-check Lean 4 source.

    Fails (exit 1) when Lean reports error-severity diagnostics or an
    orchestration error occurs. Successful compiles — including those with
    warnings — exit 0.
    """
    from grd.core.lean.client import check, check_file

    if code is None and file is None:
        # Fall back to stdin to support `grd lean check <<< '...'` style piping.
        import sys as _sys

        if not _sys.stdin.isatty():
            code = _sys.stdin.read()
        if not code:
            _error("Provide inline Lean code, --file <path>, or pipe source on stdin.")

    if code is not None and file is not None:
        _error("Pass only one of inline code or --file, not both.")

    if file is not None:
        resolved = file if file.is_absolute() else (_get_cwd() / file).resolve()
        if not resolved.is_file():
            _error(f"File not found: {resolved}")
        result = check_file(
            path=resolved,
            project_root=_get_cwd(),
            timeout_s=timeout_s,
            use_daemon=not no_daemon,
            auto_spawn=not no_spawn,
        )
    else:
        assert code is not None  # for type checker
        result = check(
            code=code,
            project_root=_get_cwd(),
            imports=list(import_module),
            timeout_s=timeout_s,
            use_daemon=not no_daemon,
            auto_spawn=not no_spawn,
        )

    _output(result)
    _print_diagnostic_hints(result)
    if not result.ok:
        raise typer.Exit(code=1)


@lean_app.command("typecheck-file")
def lean_typecheck_file(
    path: Path = typer.Argument(..., help="Path to .lean file to type-check."),
    timeout_s: float = typer.Option(60.0, "--timeout", min=0.1, max=600.0),
    no_daemon: bool = typer.Option(False, "--no-daemon"),
    no_spawn: bool = typer.Option(False, "--no-spawn"),
) -> None:
    """Type-check a ``.lean`` file by path (alias for ``check --file``)."""
    from grd.core.lean.client import check_file

    resolved = path if path.is_absolute() else (_get_cwd() / path).resolve()
    if not resolved.is_file():
        _error(f"File not found: {resolved}")

    result = check_file(
        path=resolved,
        project_root=_get_cwd(),
        timeout_s=timeout_s,
        use_daemon=not no_daemon,
        auto_spawn=not no_spawn,
    )
    _output(result)
    _print_diagnostic_hints(result)
    if not result.ok:
        raise typer.Exit(code=1)


@lean_app.command("prove")
def lean_prove(
    statement: str = typer.Argument(
        ...,
        help="Lean 4 statement to prove. Accepts a bare proposition (e.g. '1 + 1 = 2'), "
        "a signature with a keyword header ('theorem foo : P → P'), or a full definition "
        "whose ':=' tail will be rewritten with each candidate tactic.",
    ),
    tactic: list[str] = typer.Option(
        [],
        "--tactic",
        help="Override the tactic ladder. Repeatable; order is preserved.",
    ),
    import_module: list[str] = typer.Option(
        [],
        "--import",
        "-i",
        help="Module to prepend as 'import <module>'. Repeatable.",
    ),
    max_attempts: int | None = typer.Option(
        None,
        "--max-attempts",
        help="Cap the number of tactics tried. Default: run the full ladder.",
        min=1,
    ),
    timeout_s: float = typer.Option(
        30.0,
        "--timeout",
        help="Per-attempt wall-clock timeout in seconds.",
        min=0.1,
        max=600.0,
    ),
    no_daemon: bool = typer.Option(
        False,
        "--no-daemon",
        help="Skip the socket daemon; run each attempt via a one-shot subprocess.",
    ),
    no_spawn: bool = typer.Option(
        False,
        "--no-spawn",
        help="Do not auto-spawn the daemon if the socket is absent.",
    ),
) -> None:
    """Tactic-search a proof for the given Lean 4 statement.

    Iterates a fixed ladder of common tactics (``rfl``, ``decide``,
    ``norm_num``, ``ring``, ``linarith``, ``omega``, ``simp``, ``aesop``)
    and returns the first one that type-checks. Exit 0 on success, 1 if no
    tactic closed the goal. JSON output is suitable for agent consumption.
    """
    from grd.core.lean.prove import prove_statement

    result = prove_statement(
        statement,
        project_root=_get_cwd(),
        tactics=list(tactic) if tactic else None,
        imports=list(import_module),
        max_attempts=max_attempts,
        timeout_s=timeout_s,
        use_daemon=not no_daemon,
        auto_spawn=not no_spawn,
    )
    _output(result)
    _print_prove_hints(result)
    if not result.ok:
        raise typer.Exit(code=1)


@lean_app.command("env")
def lean_env() -> None:
    """Show detected Lean toolchain, env file status, and daemon state.

    Prefixes non-raw output with a single-line readiness summary (``ready``
    or ``blocked on: …``) so a human scanning the terminal knows whether to
    run ``/grd:lean-bootstrap`` before anything else. The JSON ``--raw`` mode
    emits only the structured payload — the summary is redundant there.
    """
    from grd.cli._helpers import _raw
    from grd.core.lean.env import compute_env_status

    status = compute_env_status(_get_cwd())
    if not _raw:
        if status.ready:
            console.print("[bold green]Lean environment ready[/]")
        else:
            missing = ", ".join(status.blocked_by) if status.blocked_by else "unknown"
            console.print(
                f"[bold yellow]Lean environment not ready[/] — blocked on: {missing} "
                "(run [cyan]/grd:lean-bootstrap[/] to install)"
            )
    _output(status)


@lean_app.command("verify-claim")
def lean_verify_claim(
    claim: str = typer.Argument(
        ...,
        help="Informal mathematical/physical claim to autoformalize (e.g. 'for every prime p, p > 1').",
    ),
    phase: str | None = typer.Option(
        None,
        "--phase",
        help="Phase identifier for logging / JSON trace. Does not alter behavior.",
    ),
    physics: bool = typer.Option(
        False,
        "--physics",
        help="Force physics retrieval path (Mathlib4 + PhysLean); overrides auto-detection.",
    ),
    no_physics: bool = typer.Option(
        False,
        "--no-physics",
        help="Force non-physics retrieval path (Mathlib4 only); overrides auto-detection.",
    ),
    import_module: list[str] = typer.Option(
        [],
        "--import",
        "-i",
        help="Module to prepend to each candidate as 'import <module>'. Repeatable.",
    ),
    timeout_s: float = typer.Option(
        30.0,
        "--timeout",
        help="Per-compile wall-clock timeout in seconds.",
        min=0.1,
        max=600.0,
    ),
    no_daemon: bool = typer.Option(
        False,
        "--no-daemon",
        help="Skip the socket daemon; run each compile via a one-shot subprocess.",
    ),
    no_llm: bool = typer.Option(
        False,
        "--no-llm",
        help="Dry-run: skip LLM calls and emit a structured 'unconfigured' result "
        "(useful for testing plumbing without an API key).",
    ),
) -> None:
    """Autoformalize an informal claim into a Lean 4 theorem (6-stage pipeline).

    Runs: extract → retrieve → generate → compile-repair → faithfulness →
    decide. On high confidence (SBERT/Jaccard >= 0.85) emits the accepted
    Lean statement. On low confidence or failed compile, files a `bd new -l
    human` bead with the specific ambiguity and exits 1.

    Requires ``ANTHROPIC_API_KEY`` (and the ``autoformalize`` optional extra)
    unless ``--no-llm`` is passed.
    """
    import os as _os  # noqa: PLC0415

    from grd.core.lean.autoformalize import (
        AutoformalizeConfig,
        MockLLM,
        VerifyClaimResult,
        load_autoformalize_config,
        verify_claim,
    )

    if physics and no_physics:
        _error("Pass at most one of --physics / --no-physics.")
    physics_override: bool | None
    if physics:
        physics_override = True
    elif no_physics:
        physics_override = False
    else:
        physics_override = None

    project_root = _get_cwd()
    config: AutoformalizeConfig = load_autoformalize_config(project_root)

    llm: object
    if no_llm:
        llm = MockLLM(responses=_unconfigured_llm_responses(config.num_candidates))
    else:
        from grd.core.lean.autoformalize.llm import AnthropicLLM  # noqa: PLC0415

        api_key = _os.environ.get("ANTHROPIC_API_KEY")
        llm = AnthropicLLM(model_id=config.model_id, api_key=api_key)

    result: VerifyClaimResult = verify_claim(
        claim=claim,
        project_root=project_root,
        llm=llm,  # type: ignore[arg-type]
        config=config,
        phase=phase,
        physics_override=physics_override,
        imports=list(import_module) if import_module else None,
        timeout_s=timeout_s,
        use_daemon=not no_daemon,
    )

    _output(_verify_result_to_dict(result))
    _print_verify_claim_hints(result)
    if result.outcome != "auto_accept":
        raise typer.Exit(code=1)


def _unconfigured_llm_responses(n: int) -> list[str]:
    """Provide placeholder responses for --no-llm dry-runs.

    Each response is a visibly-stub Lean block so the rest of the pipeline
    runs end-to-end without network; callers reading the JSON see the
    ``sorry`` and the skipped status and know it wasn't real inference.
    """
    stub = "```lean\ntheorem autoformalize_dry_run : True := sorry\n```"
    # Candidates + (potentially) back-translations + (potentially) repairs.
    # We oversize the pool so the pipeline never aborts mid-run.
    return [stub] * max(n * 4, 16) + ["stub (dry run — LLM disabled)"] * 16


def _verify_result_to_dict(result: object) -> dict:
    """Serialize a ``VerifyClaimResult`` (frozen dataclass) into a plain dict.

    We prefer this over ``dataclasses.asdict`` because some nested fields
    carry ``LeanDiagnostic`` Pydantic models that already know how to dump
    themselves; mixing the two cleanly in one pass yields prettier JSON.
    """
    from dataclasses import asdict, is_dataclass  # noqa: PLC0415

    if is_dataclass(result) and not isinstance(result, type):
        return asdict(result)  # type: ignore[call-overload]
    raise TypeError(f"Cannot serialize {type(result).__name__}")


@lean_app.command("bootstrap")
def lean_bootstrap(
    with_graphviz: bool = typer.Option(
        False,
        "--with-graphviz",
        help="Try to install graphviz via a user-level package manager (brew/nix-env). Falls back to ASCII dep graphs silently.",
    ),
    with_tectonic: bool = typer.Option(
        False,
        "--with-tectonic",
        help="Install tectonic via cargo if no LaTeX compiler is present. HTML-only Blueprint works without this.",
    ),
    with_mathlib_cache: bool = typer.Option(
        False,
        "--with-mathlib-cache",
        help="Opt-in: download Mathlib olean cache (~10 GB). Requires --yes or prior recorded consent.",
    ),
    with_leandojo: bool = typer.Option(
        False,
        "--with-leandojo",
        help="Opt-in: install lean-dojo for premise retrieval (~3–5 GB). Requires --yes or prior recorded consent.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Auto-confirm consent-gated stages (mathlib cache, leandojo). Also recorded in .grd/lean-env.json.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Re-attempt every stage, ignoring cached skips or prior 'never' consent.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Report what would happen without touching anything.",
    ),
    uninstall_flag: bool = typer.Option(
        False,
        "--uninstall",
        help="Remove GRD-added Lean artifacts (~/.elan, caches, project .lake).",
    ),
) -> None:
    """Lazy bootstrap: idempotently install elan, the Lean toolchain, and Pantograph.

    Stages 1–3 run unconditionally (no consent). Stages 4–5 (graphviz,
    tectonic) run only when their flag is passed. Stages 6–7 (Mathlib cache,
    LeanDojo) require both the flag AND ``--yes``. State is recorded to
    ``.grd/lean-env.json`` after every stage so partial runs resume cleanly.
    """
    from grd.core.lean.bootstrap import BootstrapOptions, run_bootstrap, uninstall

    project_root = _get_cwd()
    if uninstall_flag:
        _output(uninstall(project_root, dry_run=dry_run))
        return

    report = run_bootstrap(
        project_root,
        options=BootstrapOptions(
            yes=yes,
            with_graphviz=with_graphviz,
            with_tectonic=with_tectonic,
            with_mathlib_cache=with_mathlib_cache,
            with_leandojo=with_leandojo,
            dry_run=dry_run,
            force=force,
        ),
    )
    _output(report)
    if not report.ok:
        raise typer.Exit(code=1)


@lean_app.command("serve-repl")
def lean_serve_repl(
    idle_timeout_s: float = typer.Option(
        600.0,
        "--idle-timeout",
        help="Exit the daemon after this many seconds without any requests.",
    ),
    read_timeout_s: float = typer.Option(
        60.0,
        "--read-timeout",
        help="Per-connection read timeout in seconds.",
    ),
    detach: bool = typer.Option(
        False,
        "--detach",
        help="Double-fork into the background. Returns once the socket is up.",
    ),
) -> None:
    """Start the Lean REPL daemon on the project's Unix socket.

    Normally users don't invoke this directly — the client auto-spawns a
    daemon on the first ``grd lean check``. Exposed for debugging and for
    integration tests.
    """
    from grd.core.lean.daemon import serve
    from grd.core.lean.env import socket_path

    project_root = _get_cwd()
    if detach:
        from grd.core.lean.client import spawn_daemon

        ok = spawn_daemon(project_root, idle_timeout_s=idle_timeout_s)
        if not ok:
            _error(f"Failed to spawn detached daemon (socket never appeared at {socket_path(project_root)}).")
        _output({"ok": True, "socket": str(socket_path(project_root))})
        return

    serve(project_root, idle_timeout_s=idle_timeout_s, read_timeout_s=read_timeout_s)


@lean_app.command("stop-repl")
def lean_stop_repl() -> None:
    """Ask the running daemon to shut down."""
    from grd.core.lean.client import shutdown_daemon

    _output(shutdown_daemon(_get_cwd()))


@lean_app.command("ping")
def lean_ping() -> None:
    """Check whether the daemon is alive on this project's socket."""
    from grd.core.lean.client import ping_daemon

    alive = ping_daemon(_get_cwd())
    _output({"ok": alive, "alive": alive})
    if not alive:
        raise typer.Exit(code=1)
