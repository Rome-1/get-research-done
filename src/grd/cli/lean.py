"""``grd lean ...`` — Lean 4 verification backend.

Thin typer surface over ``grd.core.lean.*``. See that package's ``__init__``
for the layering rationale and PITCH.md §Architecture Design for the
"CLI + skills, not MCP" decision.
"""

from __future__ import annotations

import contextlib
import json
import sys
import traceback
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TYPE_CHECKING

import typer

from grd.cli import _helpers
from grd.cli._helpers import _error, _get_cwd, _output, console, err_console, is_audit_mode

if TYPE_CHECKING:
    from grd.core.lean.events import ProgressEvent
    from grd.core.lean.find_counterexample import CounterexampleResult
    from grd.core.lean.heartbeats import HeartbeatRetryReport
    from grd.core.lean.protocol import LeanCheckResult
    from grd.core.lean.prove import ProveResult
    from grd.core.lean.try_prove import TryProveResult

lean_app = typer.Typer(help="Lean 4 verification backend (type-check, proof daemon, env)")

# ─── Exit code convention (ge-oc0) ─────────────────────────────────────────
#   0 = success
#   1 = soft-fail: Lean/proof/faithfulness rejection (the check ran, answer is "no")
#   2 = user input error (bad flag combo, malformed claim, missing required arg)
#   3 = environment / bootstrap error (lean not found, mathlib stale, consent needed)
#   4 = daemon / internal error (backend crashed, unexpected exception)

EXIT_SOFT_FAIL = 1
EXIT_INPUT_ERROR = 2
EXIT_ENV_ERROR = 3
EXIT_INTERNAL_ERROR = 4

_ERROR_KIND_TO_EXIT: dict[str, int] = {
    "lean_not_found": EXIT_ENV_ERROR,
    "timeout": EXIT_SOFT_FAIL,
    "daemon_unavailable": EXIT_INTERNAL_ERROR,
    "invalid_request": EXIT_INPUT_ERROR,
    "io_error": EXIT_INTERNAL_ERROR,
    "internal_error": EXIT_INTERNAL_ERROR,
}


def _exit_code_for_result(result: object) -> int:
    """Map a ``LeanCheckResult`` or ``ProveResult`` to the right exit code.

    If the result carries an ``error`` field (orchestration failures),
    route to the appropriate bucket. Otherwise the Lean/proof check
    ran but the answer was "no" — soft-fail (exit 1).
    """
    error_kind = getattr(result, "error", None)
    if error_kind is not None:
        return _ERROR_KIND_TO_EXIT.get(error_kind, EXIT_INTERNAL_ERROR)
    return EXIT_SOFT_FAIL


# ─── Event streaming helpers ─────────────────────────────────────────────────


def _make_emitter(events: str | None) -> Callable[[ProgressEvent], None]:
    """Build the progress-event callback for the given ``--events`` mode.

    ``"jsonl"`` streams one JSON line per event to stdout (flush after each).
    ``None`` (default) uses the TTY status line on interactive terminals,
    or a no-op callback when stderr is not a TTY / ``--raw`` is active.
    """
    from grd.core.lean.events import jsonl_emitter, noop_emitter, tty_emitter  # noqa: PLC0415

    if events == "jsonl":
        return jsonl_emitter
    if _helpers._raw:
        return noop_emitter
    if sys.stderr.isatty():
        return tty_emitter
    return noop_emitter


def _output_for_events(data: object, events: str | None) -> None:
    """Emit the final aggregate result, routing to stderr when streaming.

    When ``--events jsonl`` is active, stdout carries the NDJSON event
    stream. The final aggregate result goes to stderr so machine consumers
    can distinguish events (stdout) from the summary (stderr).
    """
    if events == "jsonl":
        import dataclasses  # noqa: PLC0415

        if hasattr(data, "model_dump"):
            payload = data.model_dump(mode="json", by_alias=True)
        elif dataclasses.is_dataclass(data) and not isinstance(data, type):
            payload = dataclasses.asdict(data)
        elif isinstance(data, dict):
            payload = data
        else:
            payload = {"result": str(data)}
        err_console.print_json(json.dumps(payload, default=str))
    else:
        _output(data)


_EVENTS_OPTION = typer.Option(
    None,
    "--events",
    help="Enable streaming progress events. 'jsonl' emits NDJSON to stdout with the final aggregate on stderr.",
)


@contextlib.contextmanager
def _lean_internal_guard() -> Iterator[None]:
    """Catch unexpected exceptions and emit structured error JSON.

    Wraps commands whose call stacks are deep and hard to predict
    (verify-claim, bootstrap, daemon ops). Known exception classes
    that ``_GRDTyper`` already handles are re-raised so their existing
    exit semantics are preserved.
    """
    from grd.core.errors import GRDError

    try:
        yield
    except (GRDError, KeyError, TimeoutError, typer.Exit):
        raise  # _GRDTyper handles these; typer.Exit is a RuntimeError subclass
    except Exception as exc:
        # Capture the tail of the traceback (last 6 frames) for diagnostics
        # without dumping the full stack at the user.
        tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
        tb_tail = "".join(tb_lines[-6:]).strip()

        payload = {
            "ok": False,
            "error": {
                "kind": "internal_error",
                "message": str(exc),
                "detail": tb_tail,
            },
        }
        if _helpers._raw:
            err_console.print_json(json.dumps(payload))
        else:
            err_console.print(
                f"[bold red]Internal error:[/] {exc}\n[dim](Run with --raw for machine-readable diagnostics.)[/]",
                highlight=False,
            )
        raise typer.Exit(code=EXIT_INTERNAL_ERROR) from None


def _print_goal_state(result: object, *, show_goal: bool = False) -> None:
    """Print the goal state from a LeanCheckResult when ``--show-goal`` is set.

    Renders ``goals_after`` (remaining goals) to stderr. On success the list
    is empty (all goals closed); on failure it shows what's left, giving the
    user the same live proof-state experience they'd get in VS Code's
    Lean infoview (ge-2zu / P1-7).
    """
    if _helpers._raw or not show_goal:
        return
    goals_after = getattr(result, "goals_after", None)
    if goals_after is None:
        return
    if not goals_after:
        err_console.print("[green]all goals closed[/]", highlight=False)
        return
    err_console.print("")
    err_console.print(f"[bold]Goals[/] ({len(goals_after)} remaining)", highlight=False)
    for i, goal in enumerate(goals_after, 1):
        err_console.print(f"  [dim]goal {i}:[/]", highlight=False)
        for line in goal.splitlines():
            err_console.print(f"    {line}", highlight=False)


def _print_prove_goal_state(result: object, *, show_goal: bool = False) -> None:
    """Print goal state from the last failing ProofAttempt."""
    if _helpers._raw or not show_goal:
        return
    attempts = getattr(result, "attempts", []) or []
    if not attempts:
        return
    # Show the goal state from the last attempt (whether it succeeded or failed).
    last = attempts[-1]
    goal_before = getattr(last, "goal_before", None)
    goal_after = getattr(last, "goal_after", None)
    if goal_before is None and goal_after is None:
        return
    err_console.print("")
    if goal_before:
        err_console.print(f"[bold]Initial goal:[/] {goal_before}", highlight=False)
    if goal_after is not None:
        if not goal_after:
            err_console.print("[green]all goals closed[/]", highlight=False)
        else:
            err_console.print(f"[bold]Remaining goals[/] ({len(goal_after)}):", highlight=False)
            for i, goal in enumerate(goal_after, 1):
                err_console.print(f"  [dim]goal {i}:[/]", highlight=False)
                for line in goal.splitlines():
                    err_console.print(f"    {line}", highlight=False)


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


def _print_heartbeat_retry(report: HeartbeatRetryReport | None) -> None:
    """Surface the heartbeat auto-retry ladder + winning set_option suggestion.

    Only printed in non-raw mode when the layer actually retried — a
    zero-retry report means the baseline already passed (or failed for
    non-heartbeat reasons) and there is nothing to say.
    """
    if _helpers._raw or report is None or report.retries_used == 0:
        return
    err_console.print("")
    if report.winning_heartbeats is not None:
        err_console.print(
            f"[bold green]Heartbeat auto-retry:[/] succeeded at "
            f"maxHeartbeats={report.winning_heartbeats} "
            f"(after {report.retries_used} retr{'ies' if report.retries_used != 1 else 'y'}).",
            highlight=False,
        )
        if report.suggestion:
            err_console.print(f"  [dim]{report.suggestion}[/]", highlight=False)
    else:
        tail = " (ceiling reached)" if report.ceiling_hit else ""
        err_console.print(
            f"[bold yellow]Heartbeat auto-retry:[/] exhausted "
            f"{report.retries_used} retr{'ies' if report.retries_used != 1 else 'y'}"
            f"{tail} without closing the goal.",
            highlight=False,
        )


def _print_prove_heartbeat_retries(result: ProveResult) -> None:
    """Surface heartbeat retries from the tactic whose retry actually helped.

    Scans attempts back-to-front so the most recent (i.e. winning) retry is
    reported first. Non-interesting (zero-retry) attempts are skipped.
    """
    if _helpers._raw:
        return
    attempts = getattr(result, "attempts", []) or []
    # Prefer the winning attempt's retry report; fall back to the last
    # attempt that retried, so even on overall failure the user sees which
    # tactic burned through retries.
    winner = next(
        (a for a in reversed(attempts) if getattr(a, "ok", False) and getattr(a, "heartbeat_retry", None)),
        None,
    )
    if winner is None:
        winner = next(
            (a for a in reversed(attempts) if getattr(a, "heartbeat_retry", None)),
            None,
        )
    if winner is None:
        return
    report = winner.heartbeat_retry
    err_console.print("")
    tactic = getattr(winner, "tactic", "<tactic>")
    if report.winning_heartbeats is not None:
        err_console.print(
            f"[bold green]Heartbeat auto-retry:[/] tactic `{tactic}` closed "
            f"the goal at maxHeartbeats={report.winning_heartbeats} "
            f"(after {report.retries_used} retr"
            f"{'ies' if report.retries_used != 1 else 'y'}).",
            highlight=False,
        )
        if report.suggestion:
            err_console.print(f"  [dim]{report.suggestion}[/]", highlight=False)
    else:
        tail = " (ceiling reached)" if report.ceiling_hit else ""
        err_console.print(
            f"[bold yellow]Heartbeat auto-retry:[/] tactic `{tactic}` "
            f"exhausted {report.retries_used} retr"
            f"{'ies' if report.retries_used != 1 else 'y'}{tail}.",
            highlight=False,
        )


def _print_daemon_spawn_failure() -> None:
    """Surface daemon startup failure with the log tail (ge-f9i / P1-5).

    When the daemon failed to start the client falls back to one-shot
    subprocess silently — the user doesn't know why things are slow or
    broken. This helper reads the daemon log and shows the last ~20 lines
    so they can diagnose the cause without hunting for the file.
    """
    if _helpers._raw:
        return
    from grd.core.lean.client import _last_spawn_failed, read_daemon_log_tail  # noqa: PLC0415
    from grd.core.lean.env import daemon_log_path  # noqa: PLC0415

    project_root = _get_cwd()
    key = str(project_root)
    if not _last_spawn_failed.get(key):
        return
    log = daemon_log_path(project_root)
    err_console.print("")
    err_console.print(
        f"[bold yellow]daemon failed to start[/] — see {log}",
        highlight=False,
    )
    tail = read_daemon_log_tail(project_root, lines=20)
    if tail:
        err_console.print("[dim]Last lines from daemon log:[/]", highlight=False)
        for line in tail.splitlines():
            err_console.print(f"  [dim]{line}[/]", highlight=False)


def _print_verify_claim_warning(result: object) -> None:
    """Announce when escalation wanted to file a bead but couldn't.

    Silent failure here is the ge-1hr / UX-STUDY.md §P0-8 trap: the pipeline
    "escalated" but no human will ever see the bead because ``bd`` was
    missing from ``PATH`` (or errored mid-run). We promote ``outcome`` to
    ``"escalate_unfiled"`` in the pipeline and surface the ``warning`` text
    here as a prominent banner above the normal output, so a human skimming
    the terminal can't miss it. ``--raw`` consumers get the same information
    from the top-level ``warning`` / ``escalation_attempted`` /
    ``escalation_error`` fields in JSON.
    """
    if _helpers._raw:
        return
    warning = getattr(result, "warning", None)
    if not warning:
        return
    err_console.print("")
    err_console.print(f"[bold yellow]⚠ {warning}[/]", highlight=False)


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


def _print_verify_claim_diff(result: object) -> None:
    """Print a structured semantic diff when the faithfulness gate rejects.

    In non-raw mode, surfaces the specific divergences (quantifiers, domains,
    conventions, missing terms) so the user sees *what* changed, not just a
    similarity float (ge-cla / UX-STUDY.md §P1-6).
    """
    if _helpers._raw:
        return
    if getattr(result, "outcome", None) == "auto_accept":
        return
    diff = getattr(result, "chosen_semantic_diff", None)
    if diff is None:
        return

    lines: list[str] = []
    if getattr(diff, "changed_quantifiers", None):
        lines.append(f"  Quantifiers: {', '.join(diff.changed_quantifiers)}")
    if getattr(diff, "changed_domains", None):
        lines.append(f"  Domains: {', '.join(diff.changed_domains)}")
    if getattr(diff, "changed_convention_terms", None):
        lines.append(f"  Conventions: {', '.join(diff.changed_convention_terms)}")
    if getattr(diff, "missing_hypotheses", None):
        lines.append(f"  Missing from translation: {', '.join(diff.missing_hypotheses)}")
    if getattr(diff, "only_in_translation", None):
        lines.append(f"  Added in translation: {', '.join(diff.only_in_translation)}")

    if not lines:
        return
    err_console.print("")
    err_console.print("[bold]Semantic diff[/]", highlight=False)
    for ln in lines:
        err_console.print(ln, highlight=False)


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
    events: str | None = _EVENTS_OPTION,
    show_goal: bool = typer.Option(
        False,
        "--show-goal",
        help="Show remaining proof goals after elaboration (extracted from diagnostics).",
    ),
    max_heartbeat_retries: int = typer.Option(
        3,
        "--max-heartbeat-retries",
        help="On a heartbeat-timeout diagnostic, rerun with 2× maxHeartbeats up "
        "to N times (default 3; 0 disables auto-retry).",
        min=0,
    ),
    initial_heartbeats: int | None = typer.Option(
        None,
        "--initial-heartbeats",
        help="Starting maxHeartbeats value for the first run. Omit to use Lean's "
        "default (~200000); pass an explicit value to start from a larger budget.",
        min=1,
    ),
) -> None:
    """Type-check Lean 4 source.

    Exit codes: 0 success, 1 Lean elaboration error, 2 bad input,
    3 missing toolchain, 4 internal/daemon error.

    SIDE EFFECTS:
      - Process spawns: Lean type-checker (via daemon unless --no-daemon),
        spawns daemon on first use unless --no-spawn.
      - Filesystem: reads --file path; daemon writes a socket under
        .grd/lean-daemon.sock and a PID file under .grd/.
      - Network: none.
      - Beads: none.
      - Dependencies: requires an installed Lean toolchain (see `grd lean bootstrap`).
      - Audit-safe under --audit-mode (aliases --no-daemon --no-spawn;
        no daemon spawn, no socket/PID file writes).
    """
    from grd.core.lean.client import check, check_file
    from grd.core.lean.events import DiagnosticEmitted, StageCompleted, StageStarted, tty_finish
    from grd.core.lean.heartbeats import check_with_heartbeat_retry

    if is_audit_mode():
        no_daemon = True
        no_spawn = True
    emit = _make_emitter(events)

    if code is None and file is None:
        # Fall back to stdin to support `grd lean check <<< '...'` style piping.
        import sys as _sys

        if not _sys.stdin.isatty():
            code = _sys.stdin.read()
        if not code:
            _error("Provide inline Lean code, --file <path>, or pipe source on stdin.", code=EXIT_INPUT_ERROR)

    if code is not None and file is not None:
        _error("Pass only one of inline code or --file, not both.", code=EXIT_INPUT_ERROR)

    emit(StageStarted(stage="check"))
    if file is not None:
        resolved = file if file.is_absolute() else (_get_cwd() / file).resolve()
        if not resolved.is_file():
            _error(f"File not found: {resolved}", code=EXIT_INPUT_ERROR)
        result, retry_report = check_with_heartbeat_retry(
            check_file,
            initial_heartbeats=initial_heartbeats,
            max_retries=max_heartbeat_retries,
            path=resolved,
            project_root=_get_cwd(),
            timeout_s=timeout_s,
            use_daemon=not no_daemon,
            auto_spawn=not no_spawn,
        )
    else:
        assert code is not None  # for type checker
        result, retry_report = check_with_heartbeat_retry(
            check,
            initial_heartbeats=initial_heartbeats,
            max_retries=max_heartbeat_retries,
            code=code,
            project_root=_get_cwd(),
            imports=list(import_module),
            timeout_s=timeout_s,
            use_daemon=not no_daemon,
            auto_spawn=not no_spawn,
        )

    for diag in result.diagnostics:
        emit(
            DiagnosticEmitted(
                severity=diag.severity,
                message=diag.message,
                line=diag.line,
                column=diag.column,
            )
        )
    emit(
        StageCompleted(
            stage="check",
            status="ok" if result.ok else "failed",
            elapsed_ms=result.elapsed_ms,
        )
    )
    if events:
        tty_finish()
    _output_for_events(result, events)
    _print_daemon_spawn_failure()
    _print_diagnostic_hints(result)
    _print_heartbeat_retry(retry_report)
    _print_goal_state(result, show_goal=show_goal)
    if not result.ok:
        raise typer.Exit(code=_exit_code_for_result(result))


@lean_app.command("typecheck-file")
def lean_typecheck_file(
    path: Path = typer.Argument(..., help="Path to .lean file to type-check."),
    timeout_s: float = typer.Option(60.0, "--timeout", min=0.1, max=600.0),
    no_daemon: bool = typer.Option(False, "--no-daemon"),
    no_spawn: bool = typer.Option(False, "--no-spawn"),
) -> None:
    """Type-check a ``.lean`` file by path (alias for ``check --file``).

    SIDE EFFECTS: same as ``grd lean check``. Audit-safe under --audit-mode.
    """
    from grd.core.lean.client import check_file

    if is_audit_mode():
        no_daemon = True
        no_spawn = True

    resolved = path if path.is_absolute() else (_get_cwd() / path).resolve()
    if not resolved.is_file():
        _error(f"File not found: {resolved}", code=EXIT_INPUT_ERROR)

    result = check_file(
        path=resolved,
        project_root=_get_cwd(),
        timeout_s=timeout_s,
        use_daemon=not no_daemon,
        auto_spawn=not no_spawn,
    )
    _output(result)
    _print_daemon_spawn_failure()
    _print_diagnostic_hints(result)
    if not result.ok:
        raise typer.Exit(code=_exit_code_for_result(result))


@lean_app.command("prove")
def lean_prove(
    statement: str | None = typer.Argument(
        None,
        help="Lean 4 statement to prove. Accepts a bare proposition (e.g. '1 + 1 = 2'), "
        "a signature with a keyword header ('theorem foo : P → P'), or a full definition "
        "whose ':=' tail will be rewritten with each candidate tactic. "
        "Omit only when passing --list-tactics.",
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
    list_tactics: bool = typer.Option(
        False,
        "--list-tactics",
        help="Print the default tactic ladder as JSON and exit. Authoritative source "
        "for tooling and agents that would otherwise hardcode the ladder and drift.",
    ),
    events: str | None = _EVENTS_OPTION,
    show_goal: bool = typer.Option(
        False,
        "--show-goal",
        help="Show initial goal and remaining goals for each tactic attempt.",
    ),
    max_heartbeat_retries: int = typer.Option(
        3,
        "--max-heartbeat-retries",
        help="Per-tactic heartbeat retry cap. On a heartbeat timeout, rerun the "
        "same tactic with 2× maxHeartbeats up to N times (default 3; 0 disables).",
        min=0,
    ),
    initial_heartbeats: int | None = typer.Option(
        None,
        "--initial-heartbeats",
        help="Starting maxHeartbeats for each tactic's first run. Omit to use Lean's default (~200000).",
        min=1,
    ),
) -> None:
    """Tactic-search a proof for the given Lean 4 statement.

    Iterates the default ladder (``rfl``, ``decide``, ``norm_num``, ``ring``,
    ``linarith``, ``omega``, ``simp``, ``aesop``) and returns the first one
    that type-checks. Exit 0 on success, 1 if no tactic closed the goal.

    Pass ``--list-tactics`` with no statement to dump the current ladder —
    the single source of truth for agents and docs.

    SIDE EFFECTS:
      - Process spawns: one Lean invocation per tactic attempt (via daemon
        unless --no-daemon); may spawn daemon unless --no-spawn.
      - Filesystem: daemon socket + PID file under .grd/ when daemon is used.
      - Network: none.
      - Beads: none.
      - Dependencies: requires an installed Lean toolchain.
      - Audit-safe under --audit-mode (aliases --no-daemon --no-spawn).
    """
    from grd.core.lean.events import tty_finish
    from grd.core.lean.prove import DEFAULT_TACTIC_LADDER, prove_statement

    if is_audit_mode():
        no_daemon = True
        no_spawn = True

    if list_tactics:
        _output({"tactics": list(DEFAULT_TACTIC_LADDER)})
        return

    if statement is None:
        _error("Provide a Lean 4 statement, or pass --list-tactics to dump the default ladder.", code=EXIT_INPUT_ERROR)

    emit = _make_emitter(events)
    result = prove_statement(
        statement,
        project_root=_get_cwd(),
        tactics=list(tactic) if tactic else None,
        imports=list(import_module),
        max_attempts=max_attempts,
        timeout_s=timeout_s,
        use_daemon=not no_daemon,
        auto_spawn=not no_spawn,
        on_event=emit,
        max_heartbeat_retries=max_heartbeat_retries,
        initial_heartbeats=initial_heartbeats,
    )
    if events:
        tty_finish()
    _output_for_events(result, events)
    _print_daemon_spawn_failure()
    _print_prove_hints(result)
    _print_prove_heartbeat_retries(result)
    _print_prove_goal_state(result, show_goal=show_goal)
    if not result.ok:
        raise typer.Exit(code=_exit_code_for_result(result))


def _print_try_prove_summary(result: TryProveResult) -> None:
    """Render the ranked candidate list to stderr, Sledgehammer-style.

    Matches Isabelle's "Try this:" UX — one line per kernel-checked
    candidate, so the user can click or copy any of them. Failures are
    summarised with a count so the user sees that the hammer actually
    tried a range without flooding the terminal with stack traces.
    """
    if _helpers._raw:
        return
    if result.successes:
        err_console.print("")
        err_console.print(
            f"[bold]Try this[/] ({len(result.successes)} candidate{'s' if len(result.successes) != 1 else ''}, ranked)",
            highlight=False,
        )
        for cand in result.successes:
            tag = " [dim](llm)[/]" if cand.via_llm else ""
            rank_label = f"#{(cand.rank or 0) + 1}"
            err_console.print(
                f"  [green]{rank_label}[/] [cyan]{cand.snippet}[/] [dim]({cand.elapsed_ms}ms){tag}[/]",
                highlight=False,
            )
    else:
        err_console.print("")
        err_console.print(
            "[yellow]No tactic closed the goal.[/]",
            highlight=False,
        )

    if result.failures:
        err_console.print(
            f"[dim]{len(result.failures)} candidate"
            f"{'s' if len(result.failures) != 1 else ''} rejected by the "
            f"kernel (run with --raw for details).[/]",
            highlight=False,
        )


@lean_app.command("try-prove")
def lean_try_prove(
    statement: str | None = typer.Argument(
        None,
        help="Lean 4 statement to hammer. Accepts a bare proposition, a signature "
        "with a keyword header, or a full definition whose ':=' tail will be "
        "rewritten with each candidate tactic. Omit only with --list-tactics.",
    ),
    tactic: list[str] = typer.Option(
        [],
        "--tactic",
        help="Override the default hammer tactics. Repeatable; order is preserved.",
    ),
    import_module: list[str] = typer.Option(
        [],
        "--import",
        "-i",
        help="Module to prepend as 'import <module>'. Repeatable.",
    ),
    max_candidates: int | None = typer.Option(
        None,
        "--max-candidates",
        help="Cap the size of the parallel candidate pool (before --with-llm additions).",
        min=1,
    ),
    timeout_s: float = typer.Option(
        30.0,
        "--timeout",
        help="Per-candidate wall-clock timeout in seconds.",
        min=0.1,
        max=600.0,
    ),
    with_llm: bool = typer.Option(
        False,
        "--with-llm",
        help="Also ask the configured LLM (Anthropic) for llmqed-style candidate "
        "tactics. Requires ANTHROPIC_API_KEY; silently skipped when unset.",
    ),
    no_daemon: bool = typer.Option(
        False,
        "--no-daemon",
        help="Skip the socket daemon; run each candidate via a one-shot subprocess.",
    ),
    no_spawn: bool = typer.Option(
        False,
        "--no-spawn",
        help="Do not auto-spawn the daemon if the socket is absent.",
    ),
    list_tactics: bool = typer.Option(
        False,
        "--list-tactics",
        help="Print the default hammer tactics as JSON and exit.",
    ),
    events: str | None = _EVENTS_OPTION,
) -> None:
    """Sledgehammer-style parallel hammer (ge-k8s / P2-1).

    Runs ``exact?``, ``apply?``, ``simp_all``, ``aesop``, and ``hammer`` in
    parallel, kernel-checks each, and returns a ranked list of tactic
    snippets that actually close the goal. Follows Isabelle/Sledgehammer's
    "never ship an oracle" discipline — a snippet is surfaced only if the
    Lean kernel accepts it.

    Exit 0 when at least one candidate closes the goal, 1 otherwise.

    SIDE EFFECTS:
      - Process spawns: parallel Lean invocations (one per hammer tactic),
        via daemon unless --no-daemon; may spawn daemon unless --no-spawn.
      - Filesystem: daemon socket + PID file under .grd/ when daemon is used.
      - Network: LLM call to Anthropic when --with-llm is set
        (requires ANTHROPIC_API_KEY; silently skipped otherwise).
      - Beads: none.
      - Dependencies: requires an installed Lean toolchain; --with-llm
        requires the autoformalize optional extra.
      - Audit-safe under --audit-mode (aliases --no-daemon --no-spawn).
    """
    from grd.core.lean.events import tty_finish
    from grd.core.lean.try_prove import DEFAULT_HAMMER_TACTICS, try_prove_statement

    if is_audit_mode():
        no_daemon = True
        no_spawn = True

    if list_tactics:
        _output({"tactics": list(DEFAULT_HAMMER_TACTICS)})
        return

    if statement is None:
        _error(
            "Provide a Lean 4 statement, or pass --list-tactics to dump the default hammer.",
            code=EXIT_INPUT_ERROR,
        )

    llm = _build_llmqed_backend() if with_llm else None

    emit = _make_emitter(events)
    result = try_prove_statement(
        statement,
        project_root=_get_cwd(),
        tactics=list(tactic) if tactic else None,
        imports=list(import_module),
        max_candidates=max_candidates,
        timeout_s=timeout_s,
        with_llm=with_llm,
        llm=llm,
        use_daemon=not no_daemon,
        auto_spawn=not no_spawn,
        on_event=emit,
    )
    if events:
        tty_finish()
    _output_for_events(result, events)
    _print_daemon_spawn_failure()
    _print_try_prove_summary(result)
    if not result.ok:
        raise typer.Exit(code=EXIT_SOFT_FAIL)


def _print_find_counterexample_summary(result: CounterexampleResult) -> None:
    """Render counterexample search results to stderr (ge-16j / P2-3).

    Mirrors :func:`_print_try_prove_summary`. A confirmed counterexample is
    one line per method+witness; rejected candidates collapse to a count so
    the terminal stays readable under LLM-heavy workloads.
    """
    if _helpers._raw:
        return
    if result.counterexamples:
        err_console.print("")
        err_console.print(
            f"[bold]Counterexample[/] ({len(result.counterexamples)} verified, ranked)",
            highlight=False,
        )
        for cand in result.counterexamples:
            rank_label = f"#{(cand.rank or 0) + 1}"
            via = " [dim](llm)[/]" if cand.via_llm else ""
            err_console.print(
                f"  [green]{rank_label}[/] [cyan]{cand.snippet}[/] [dim]({cand.elapsed_ms}ms){via}[/]",
                highlight=False,
            )
    else:
        err_console.print("")
        err_console.print(
            "[yellow]No counterexample found.[/]",
            highlight=False,
        )

    if result.rejected:
        err_console.print(
            f"[dim]{len(result.rejected)} candidate"
            f"{'s' if len(result.rejected) != 1 else ''} did not yield a "
            f"kernel-verified counterexample (run with --raw for details).[/]",
            highlight=False,
        )


@lean_app.command("find-counterexample")
def lean_find_counterexample(
    statement: str | None = typer.Argument(
        None,
        help="Lean 4 statement to search for counterexamples. Accepts a bare "
        "proposition (e.g. '∀ n : Nat, n * n ≠ 5'), a signature with a keyword "
        "header, or a full definition whose ':=' tail will be discarded. "
        "Omit only with --list-methods.",
    ),
    method: list[str] = typer.Option(
        [],
        "--method",
        help="Override the default methods. Repeatable. Valid: decide, plausible, llm.",
    ),
    import_module: list[str] = typer.Option(
        [],
        "--import",
        "-i",
        help="Module to prepend as 'import <module>'. Repeatable.",
    ),
    budget: int | None = typer.Option(
        None,
        "--budget",
        help="Cap the total number of candidates checked across all methods.",
        min=1,
    ),
    witness_tactic: str = typer.Option(
        "decide",
        "--witness-tactic",
        help="Tactic used to kernel-check each LLM-proposed witness refutation.",
    ),
    timeout_s: float = typer.Option(
        30.0,
        "--timeout",
        help="Per-candidate wall-clock timeout in seconds.",
        min=0.1,
        max=600.0,
    ),
    with_llm: bool = typer.Option(
        False,
        "--with-llm",
        help="Also ask the configured LLM (Anthropic) for concrete witness "
        "values. Requires ANTHROPIC_API_KEY; silently skipped when unset.",
    ),
    no_daemon: bool = typer.Option(
        False,
        "--no-daemon",
        help="Skip the socket daemon; run each candidate via a one-shot subprocess.",
    ),
    no_spawn: bool = typer.Option(
        False,
        "--no-spawn",
        help="Do not auto-spawn the daemon if the socket is absent.",
    ),
    list_methods: bool = typer.Option(
        False,
        "--list-methods",
        help="Print the default methods as JSON and exit.",
    ),
    events: str | None = _EVENTS_OPTION,
) -> None:
    """First-class counterexample search (ge-16j / P2-3).

    Runs ``decide``, ``plausible``, and (with ``--with-llm``) LLM-proposed
    concrete witnesses in parallel, kernel-checking each to produce a ranked
    list of verified refutations. "Never ship an oracle": a candidate is
    surfaced only when the Lean kernel accepts its refutation (or, for
    Plausible, rejects the goal with a reported counterexample).

    Exit 0 when at least one kernel-verified counterexample is found,
    1 otherwise.

    SIDE EFFECTS:
      - Process spawns: parallel Lean invocations (one per method/candidate),
        via daemon unless --no-daemon; may spawn daemon unless --no-spawn.
      - Filesystem: daemon socket + PID file under .grd/ when daemon is used.
      - Network: LLM call to Anthropic when --with-llm is set
        (requires ANTHROPIC_API_KEY; silently skipped otherwise).
      - Beads: none.
      - Dependencies: requires an installed Lean toolchain; --with-llm
        requires the autoformalize optional extra; ``plausible`` method
        requires the Plausible Lean dep in the target project.
      - Audit-safe under --audit-mode (aliases --no-daemon --no-spawn).
    """
    from grd.core.lean.events import tty_finish
    from grd.core.lean.find_counterexample import (
        DEFAULT_METHODS,
        find_counterexample,
    )

    if is_audit_mode():
        no_daemon = True
        no_spawn = True

    if list_methods:
        _output({"methods": list(DEFAULT_METHODS), "available": ["decide", "plausible", "llm"]})
        return

    if statement is None:
        _error(
            "Provide a Lean 4 statement, or pass --list-methods to dump the default methods.",
            code=EXIT_INPUT_ERROR,
        )

    llm = _build_llmqed_backend() if with_llm else None

    emit = _make_emitter(events)
    try:
        result = find_counterexample(
            statement,
            project_root=_get_cwd(),
            methods=list(method) if method else None,
            budget=budget,
            witness_tactic=witness_tactic,
            imports=list(import_module),
            timeout_s=timeout_s,
            with_llm=with_llm,
            llm=llm,
            use_daemon=not no_daemon,
            auto_spawn=not no_spawn,
            on_event=emit,
        )
    except ValueError as exc:
        _error(str(exc), code=EXIT_INPUT_ERROR)
    if events:
        tty_finish()
    _output_for_events(result, events)
    _print_daemon_spawn_failure()
    _print_find_counterexample_summary(result)
    if not result.ok:
        raise typer.Exit(code=EXIT_SOFT_FAIL)


def _build_llmqed_backend() -> object | None:
    """Instantiate the Anthropic LLM for the --with-llm path.

    Returns ``None`` (silent degrade) when ``ANTHROPIC_API_KEY`` is unset or
    the optional ``autoformalize`` extra isn't installed — the hammer still
    runs with its built-in tactics.
    """
    import os as _os  # noqa: PLC0415

    api_key = _os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        from grd.core.lean.autoformalize import load_autoformalize_config  # noqa: PLC0415
        from grd.core.lean.autoformalize.llm import AnthropicLLM  # noqa: PLC0415
    except ImportError:
        return None
    config = load_autoformalize_config(_get_cwd())
    try:
        return AnthropicLLM(model_id=config.model_id, api_key=api_key)
    except RuntimeError:
        return None


@lean_app.command("search")
def lean_search(
    query: str = typer.Argument(
        ...,
        help="Search query: a Lean type signature (e.g. '(_ → _) → List _ → List _'), "
        "an identifier (e.g. 'Nat.Prime'), or natural-language prose "
        "(e.g. 'continuous function bounded on compact set').",
    ),
    limit: int = typer.Option(
        10,
        "--limit",
        "-n",
        help="Maximum number of results per backend.",
        min=1,
        max=200,
    ),
    timeout_s: float = typer.Option(
        10.0,
        "--timeout",
        help="Per-backend HTTP timeout in seconds.",
        min=1.0,
        max=60.0,
    ),
) -> None:
    """Search Lean 4 / Mathlib for lemmas, theorems, and definitions.

    Routes automatically by intent — type-signature queries go to Loogle,
    natural-language queries go to LeanExplore + Lean Finder side-by-side.
    No manual backend selection needed.

    Exit codes: 0 results found, 1 no results, 2 bad input, 4 internal error.

    SIDE EFFECTS:
      - Process spawns: none.
      - Filesystem: none.
      - Network: HTTP(S) calls to Loogle, LeanExplore, and Lean Finder.
      - Beads: none.
      - Dependencies: none beyond GRD itself.
      - NOT audit-safe — this is an online-lookup command. Run in audit
        contexts only when outbound HTTP is permitted.
    """
    from grd.core.lean.search import search

    with _lean_internal_guard():
        result = search(query, limit=limit, timeout_s=timeout_s)

    _output(result)

    if not _helpers._raw:
        _print_search_results(result)

    if not result.hits and not result.errors:
        raise typer.Exit(code=EXIT_SOFT_FAIL)
    if not result.hits and result.errors:
        raise typer.Exit(code=EXIT_INTERNAL_ERROR)


def _print_search_results(result: object) -> None:
    """Render search results to stderr for human consumption."""
    from grd.core.lean.search import SearchResponse

    if not isinstance(result, SearchResponse):
        return
    if not result.hits and not result.errors:
        err_console.print("[yellow]No results found.[/]", highlight=False)
        return

    # Group hits by backend for side-by-side display.
    by_backend: dict[str, list] = {}
    for hit in result.hits:
        by_backend.setdefault(hit.backend, []).append(hit)

    for backend, hits in by_backend.items():
        label = backend.replace("_", " ").title()
        err_console.print(f"\n[bold]{label}[/] ({len(hits)} results)", highlight=False)
        for i, hit in enumerate(hits, 1):
            name_str = f"[cyan]{hit.name}[/]"
            type_str = f" [dim]: {hit.type}[/]" if hit.type else ""
            err_console.print(f"  {i}. {name_str}{type_str}", highlight=False)
            if hit.module:
                err_console.print(f"     [dim]{hit.module}[/]", highlight=False)
            if hit.doc:
                doc_line = hit.doc.splitlines()[0][:100]
                err_console.print(f"     {doc_line}", highlight=False)
            if hit.informal and not hit.doc:
                err_console.print(f"     {hit.informal[:100]}", highlight=False)
            if hit.source_url:
                err_console.print(f"     [dim]{hit.source_url}[/]", highlight=False)

    for error in result.errors:
        label = error.backend.replace("_", " ").title()
        err_console.print(f"\n[yellow]{label}:[/] {error.message}", highlight=False)

    err_console.print(f"\n[dim]Intent: {result.intent} | {result.elapsed_ms}ms[/]", highlight=False)


@lean_app.command("gen-conventions")
def lean_gen_conventions(
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write the preamble to this path. Default: print to stdout (raw) or stderr (human).",
    ),
) -> None:
    """Generate a Lean 4 preamble from the project's convention lock.

    Reads ``.grd/state.json`` and maps each convention field to a Lean type
    class instance. Fields with no Lean counterpart emit TODO comments
    suitable for filing discovered-from children of ge-tau.

    Exit codes: 0 success, 2 no state.json, 4 internal error.

    SIDE EFFECTS:
      - Process spawns: none.
      - Filesystem: reads ``.grd/state.json``; writes ``--output`` path
        when provided. With no ``--output``, prints to stdout/stderr only.
      - Network: none.
      - Beads: none.
      - Dependencies: none.
      - Audit-safe when ``--output`` is omitted (read-only).
    """
    from grd.core.lean.convention_bridge import generate_preamble

    with _lean_internal_guard():
        result = generate_preamble(_get_cwd(), output_path=output)

    _output(result)

    if not _helpers._raw:
        if result.path:
            err_console.print(f"[green]Wrote preamble to {result.path}[/]", highlight=False)
        err_console.print(
            f"[dim]Mapped: {result.mapped_count} | "
            f"Unsupported: {result.unsupported_count} | "
            f"Unset: {result.unset_count}[/]",
            highlight=False,
        )
        todos = [m for m in result.mappings if m.todo]
        if todos:
            err_console.print("\n[bold]TODOs (file discovered-from:ge-tau):[/]", highlight=False)
            for m in todos:
                err_console.print(f"  - {m.todo}", highlight=False)


@lean_app.command("env")
def lean_env() -> None:
    """Show detected Lean toolchain, env file status, and daemon state.

    Prefixes non-raw output with a single-line readiness summary (``ready``
    or ``blocked on: …``) so a human scanning the terminal knows whether to
    run ``/grd:lean-bootstrap`` before anything else. The JSON ``--raw`` mode
    emits only the structured payload — the summary is redundant there.

    SIDE EFFECTS:
      - Process spawns: invokes the installed daemon with a ``ping`` RPC
        when the socket exists (no daemon spawn).
      - Filesystem: reads ``.grd/lean-env.json`` and ``.grd/lean-daemon.sock``.
      - Network: none.
      - Beads: none.
      - Dependencies: none installed; just reports what it found.
      - Audit-safe — read-only.
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
        # Daemon responsiveness line (ge-f9i / P1-5).
        if status.daemon_responsive is True:
            console.print("[green]daemon: responsive[/] (pinged ok)")
        elif status.daemon_responsive is False:
            console.print(
                f"[bold yellow]daemon: stale socket[/] — socket exists but daemon is unresponsive"
                f"{' (see ' + status.daemon_log + ')' if status.daemon_log else ''}"
            )
        elif status.daemon_running:
            console.print("[yellow]daemon: running but ping failed[/]")
    _output(status)


@lean_app.command("stub-claim")
def lean_stub_claim(
    claim: str = typer.Argument(
        ...,
        help="Informal mathematical/physical claim (e.g. 'for every prime p, p > 1').",
    ),
    physics: bool = typer.Option(
        False,
        "--physics",
        help="Force physics retrieval path (Mathlib4 + PhysLean).",
    ),
    no_physics: bool = typer.Option(
        False,
        "--no-physics",
        help="Force non-physics retrieval path (Mathlib4 only).",
    ),
    import_module: list[str] = typer.Option(
        [],
        "--import",
        "-i",
        help="Module to prepend as 'import <module>'. Repeatable.",
    ),
    no_llm: bool = typer.Option(
        False,
        "--no-llm",
        help="Dry-run: skip LLM calls and emit a placeholder skeleton "
        "(useful for testing plumbing without an API key).",
    ),
) -> None:
    """Generate a skeleton Lean 4 statement from a natural-language claim.

    Runs stages 1-3 of the autoformalization pipeline (context extraction,
    retrieval, candidate generation) without compilation or faithfulness
    checking. Emits:

    \\b
    - skeleton Lean statement with ``sorry`` body
    - ranked retrieval hits from the Mathlib4/PhysLean name index
    - suggested import list
    - "what to try next" block

    Flows into ``grd lean verify-claim`` as an optional preprocessing step.

    SIDE EFFECTS:
      - Process spawns: none (retrieval is offline against the bundled index).
      - Filesystem: reads the pinned Mathlib4/PhysLean name index.
      - Network: Anthropic LLM call (unless ``--no-llm``).
      - Beads: none.
      - Dependencies: requires the ``autoformalize`` optional extra for the
        real LLM path.
      - Audit-safe under --audit-mode (aliases ``--no-llm`` → stub response,
        no network).
    """
    if physics and no_physics:
        _error("Pass at most one of --physics / --no-physics.", code=EXIT_INPUT_ERROR)

    if is_audit_mode():
        no_llm = True

    with _lean_internal_guard():
        import os as _os  # noqa: PLC0415

        from grd.core.lean.autoformalize import (
            AutoformalizeConfig,
            MockLLM,
            StubClaimResult,
            load_autoformalize_config,
            stub_claim,
        )

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
            stub_response = (
                "```lean\n-- stub-claim dry run (LLM disabled)\ntheorem stub_claim_placeholder : True := sorry\n```"
            )
            llm = MockLLM(responses=[stub_response])
        else:
            from grd.core.lean.autoformalize.llm import AnthropicLLM  # noqa: PLC0415

            api_key = _os.environ.get("ANTHROPIC_API_KEY")
            llm = AnthropicLLM(model_id=config.model_id, api_key=api_key)

        result: StubClaimResult = stub_claim(
            claim=claim,
            project_root=project_root,
            llm=llm,  # type: ignore[arg-type]
            config=config,
            physics_override=physics_override,
            imports=list(import_module) if import_module else None,
        )

        _output(_stub_result_to_dict(result))
        _print_stub_claim_summary(result)


def _stub_result_to_dict(result: object) -> dict:
    """Serialize a ``StubClaimResult`` to a plain dict."""
    from dataclasses import asdict, is_dataclass  # noqa: PLC0415

    if is_dataclass(result) and not isinstance(result, type):
        return asdict(result)  # type: ignore[call-overload]
    raise TypeError(f"Cannot serialize {type(result).__name__}")


def _print_stub_claim_summary(result: object) -> None:
    """Print a human-readable summary of the stub-claim result."""
    if _helpers._raw:
        return
    skeleton = getattr(result, "skeleton", "")
    if skeleton:
        err_console.print("")
        err_console.print("[bold]Skeleton[/]", highlight=False)
        err_console.print(f"```lean\n{skeleton}\n```", highlight=False)

    hits = getattr(result, "retrieval_hits", []) or []
    if hits:
        err_console.print("")
        err_console.print("[bold]Retrieval hits[/]", highlight=False)
        for h in hits[:10]:
            err_console.print(f"  {h}", highlight=False)
        if len(hits) > 10:
            err_console.print(f"  ... ({len(hits) - 10} more)", highlight=False)

    imports = getattr(result, "suggested_imports", []) or []
    if imports:
        err_console.print("")
        err_console.print("[bold]Suggested imports[/]", highlight=False)
        for imp in imports:
            err_console.print(f"  import {imp}", highlight=False)

    steps = getattr(result, "next_steps", []) or []
    if steps:
        err_console.print("")
        err_console.print("[bold]What to try next[/]", highlight=False)
        for i, step in enumerate(steps, 1):
            err_console.print(f"  {i}. {step}", highlight=False)

    notes = getattr(result, "notes", []) or []
    for note in notes:
        err_console.print(f"\n[dim]{note}[/]", highlight=False)


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
    events: str | None = _EVENTS_OPTION,
) -> None:
    """Autoformalize an informal claim into a Lean 4 theorem (6-stage pipeline).

    Runs: extract → retrieve → generate → compile-repair → faithfulness →
    decide. On high confidence (SBERT/Jaccard >= 0.85) emits the accepted
    Lean statement. On low confidence or failed compile, files a `bd new -l
    human` bead with the specific ambiguity and exits 1.

    Requires ``ANTHROPIC_API_KEY`` (and the ``autoformalize`` optional extra)
    unless ``--no-llm`` is passed.

    SIDE EFFECTS:
      - Process spawns: many Lean invocations (candidate compile + faithfulness
        back-translation), via daemon unless --no-daemon.
      - Filesystem: reads phase artifacts under .grd/; daemon socket + PID
        file under .grd/ when daemon is used.
      - Network: Anthropic LLM calls (unless --no-llm). Respects
        ANTHROPIC_API_KEY; no key ⇒ runtime error.
      - Beads: escalation path opens a ``bd new -l human`` bead on low-
        confidence / failed-compile outcomes.
      - Dependencies: requires an installed Lean toolchain and the
        ``autoformalize`` optional extra.
      - Audit-safe under --audit-mode (aliases --no-daemon and --no-llm;
        LLM disabled ⇒ emits a stub "unconfigured" result, no network).
    """
    if physics and no_physics:
        _error("Pass at most one of --physics / --no-physics.", code=EXIT_INPUT_ERROR)

    if is_audit_mode():
        no_daemon = True
        no_llm = True

    with _lean_internal_guard():
        import os as _os  # noqa: PLC0415

        from grd.core.lean.autoformalize import (
            AutoformalizeConfig,
            MockLLM,
            VerifyClaimResult,
            load_autoformalize_config,
            verify_claim,
        )
        from grd.core.lean.events import tty_finish

        emit = _make_emitter(events)
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
            on_event=emit,
        )

        if events:
            tty_finish()
        _output_for_events(_verify_result_to_dict(result), events)
        _print_verify_claim_warning(result)
        _print_verify_claim_diff(result)
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


@lean_app.command("init-blueprint")
def lean_init_blueprint(
    phase: str = typer.Argument(
        ...,
        help="Phase identifier (number, name prefix, or slug) to generate blueprint for.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing blueprint directory.",
    ),
) -> None:
    """Generate a leanblueprint-compatible LaTeX skeleton from a GRD phase.

    Maps plan entries to blueprint nodes (``\\begin{lemma}``/``\\begin{theorem}``),
    plan ``depends_on`` edges to ``\\uses{...}``, and creates stub ``.lean``
    proof files under ``Proofs/``.

    The output directory is ``<phase-dir>/blueprint/`` with:
    ``content.tex``, ``lakefile.lean``, ``lean-toolchain``, ``Blueprint.lean``,
    and one ``Proofs/<PlanName>.lean`` stub per plan entry.

    SIDE EFFECTS:
      - Process spawns: none.
      - Filesystem: writes ``<phase-dir>/blueprint/`` and everything inside.
        ``--force`` overwrites an existing directory.
      - Network: none.
      - Beads: none.
      - Dependencies: none beyond GRD itself.
      - NOT audit-safe by default — does not honor ``--audit-mode`` because
        blueprint scaffolding is the point of the command.
    """
    from grd.core.lean.blueprint_core import init_blueprint

    result = init_blueprint(_get_cwd(), phase, force=force)
    _output(result)
    if not result.ok:
        _error(result.error or "init-blueprint failed", code=EXIT_INPUT_ERROR)
    if not _helpers._raw:
        console.print(
            f"[green]Blueprint created[/] at [cyan]{result.blueprint_dir}[/] "
            f"({result.node_count} nodes, {result.edge_count} edges)"
        )


@lean_app.command("blueprint-status")
def lean_blueprint_status(
    phase: str = typer.Argument(
        ...,
        help="Phase identifier to check blueprint status for.",
    ),
    no_typecheck: bool = typer.Option(
        False,
        "--no-typecheck",
        help="Skip Lean type-checking; report only what content.tex declares.",
    ),
    svg: bool = typer.Option(
        False,
        "--svg",
        help="Render dependency graph as SVG (requires graphviz). Falls back to ASCII.",
    ),
) -> None:
    """Walk a phase blueprint and report formalization status.

    Cross-references each ``\\lean{...}`` in ``content.tex`` against actual
    Lean type-checks and auto-marks ``\\leanok`` for proofs that pass.

    Renders the standard dependency graph color-coded by status:
    ``[OK]`` proved (green), ``[--]`` stated (yellow),
    ``[  ]`` informal (grey), ``[!!]`` failed (red).

    SIDE EFFECTS:
      - Process spawns: invokes Lean (one-shot) per ``\\lean{...}`` node
        unless ``--no-typecheck`` is set.
      - Filesystem: reads ``<phase-dir>/blueprint/content.tex`` and ``.lean``
        files; writes ``\\leanok`` annotations back into ``content.tex`` for
        nodes that type-check.
      - Network: none.
      - Beads: none.
      - Dependencies: requires an installed Lean toolchain when type-checking.
      - NOT audit-safe by default — use ``--no-typecheck`` plus read-only
        filesystem to get a pure-read traversal.
    """
    from grd.core.lean.blueprint_core import blueprint_status

    result = blueprint_status(_get_cwd(), phase, typecheck=not no_typecheck)
    _output(result)

    if not result.ok:
        _error(result.error or "blueprint-status failed", code=EXIT_INPUT_ERROR)

    if not _helpers._raw and result.ascii_graph:
        console.print("")
        console.print(result.ascii_graph)
        if result.summary.get("leanok_updated", 0) > 0:
            console.print(f"\n[green]Auto-marked {result.summary['leanok_updated']} node(s) as \\leanok[/]")


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
    for_persona: str | None = typer.Option(
        None,
        "--for",
        help="Persona-aware on-ramp: 'mathematician', 'physicist', or 'ml-researcher'. "
        "Auto-enables stage defaults for the persona and references a tailored walkthrough.",
    ),
    events: str | None = _EVENTS_OPTION,
) -> None:
    """Lazy bootstrap: idempotently install elan, the Lean toolchain, and Pantograph.

    Stages 1–3 run unconditionally (no consent). Stages 4–5 (graphviz,
    tectonic) run only when their flag is passed. Stages 6–7 (Mathlib cache,
    LeanDojo) require both the flag AND ``--yes``. State is recorded to
    ``.grd/lean-env.json`` after every stage so partial runs resume cleanly.

    Pass ``--for mathematician|physicist|ml-researcher`` for a persona-tailored
    on-ramp that auto-enables the right optional stages and references a
    walkthrough skill body for that domain.

    SIDE EFFECTS:
      - Process spawns: shells out to ``curl``, ``elan``, ``lake``, ``pip``,
        system package managers, and ``cargo`` depending on enabled stages.
      - Filesystem: writes ``.grd/lean-env.json``; installs to ``~/.elan``,
        ``~/.cache/mathlib``, the project ``.lake`` directory; ``--uninstall``
        removes these.
      - Network: downloads elan, the Lean toolchain, Pantograph, Mathlib
        olean cache, LeanDojo wheels as selected.
      - Beads: none.
      - Dependencies: installs them. This is the one GRD command that is
        always side-effectful by design — use ``--dry-run`` to preview.
      - Audit-safe under --audit-mode (aliases --dry-run; no installs).
    """
    with _lean_internal_guard():
        from grd.core.lean.bootstrap import (
            VALID_PERSONAS,
            BootstrapOptions,
            run_bootstrap,
            uninstall,
        )
        from grd.core.lean.events import tty_finish

        if is_audit_mode():
            dry_run = True

        if for_persona is not None and for_persona not in VALID_PERSONAS:
            _error(
                f"Unknown persona '{for_persona}'. Valid: {', '.join(sorted(VALID_PERSONAS))}",
                code=EXIT_INPUT_ERROR,
            )

        emit = _make_emitter(events)
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
                persona=for_persona,
            ),
            on_event=emit,
        )
        if events:
            tty_finish()
        _output_for_events(report, events)
        if not _helpers._raw and for_persona and report.ok:
            _PERSONA_SKILL_HINT = {
                "mathematician": "/grd:lean-bootstrap-mathematician",
                "physicist": "/grd:lean-bootstrap-physicist",
                "ml-researcher": "/grd:lean-bootstrap-ml-researcher",
            }
            skill = _PERSONA_SKILL_HINT.get(for_persona, "")
            if skill:
                console.print(f"\n[bold]Next step:[/] Run [cyan]{skill}[/] for a guided walkthrough.")
        if not report.ok:
            raise typer.Exit(code=EXIT_ENV_ERROR)


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

    SIDE EFFECTS:
      - Process spawns: starts a long-lived daemon holding a Lean REPL.
      - Filesystem: creates ``.grd/lean-daemon.sock`` and ``.grd/lean-daemon.pid``.
      - Network: none (Unix domain socket is local only).
      - Beads: none.
      - Dependencies: requires an installed Lean toolchain.
      - NOT audit-safe — command's purpose is to spawn the daemon.
    """
    with _lean_internal_guard():
        from grd.core.lean.daemon import serve
        from grd.core.lean.env import socket_path

        project_root = _get_cwd()
        if detach:
            from grd.core.lean.client import spawn_daemon

            ok = spawn_daemon(project_root, idle_timeout_s=idle_timeout_s)
            if not ok:
                _error(
                    f"Failed to spawn detached daemon (socket never appeared at {socket_path(project_root)}).",
                    code=EXIT_ENV_ERROR,
                )
            _output({"ok": True, "socket": str(socket_path(project_root))})
            return

        serve(project_root, idle_timeout_s=idle_timeout_s, read_timeout_s=read_timeout_s)


@lean_app.command("stop-repl")
def lean_stop_repl() -> None:
    """Ask the running daemon to shut down.

    SIDE EFFECTS:
      - Process spawns: none; sends a shutdown RPC to the running daemon.
      - Filesystem: daemon cleans up ``.grd/lean-daemon.sock`` and PID file
        on shutdown. No-op when no daemon is running.
      - Network: none.
      - Beads: none.
      - Dependencies: none.
      - Audit-safe — stops a running daemon (equivalent to terminating a
        spawned background process; read-only contexts have nothing to stop).
    """
    with _lean_internal_guard():
        from grd.core.lean.client import shutdown_daemon

        _output(shutdown_daemon(_get_cwd()))


@lean_app.command("ping")
def lean_ping() -> None:
    """Check whether the daemon is alive on this project's socket.

    SIDE EFFECTS:
      - Process spawns: none.
      - Filesystem: reads ``.grd/lean-daemon.sock``.
      - Network: none (Unix socket, local).
      - Beads: none.
      - Dependencies: none.
      - Audit-safe — read-only.
    """
    from grd.core.lean.client import ping_daemon

    alive = ping_daemon(_get_cwd())
    _output({"ok": alive, "alive": alive})
    if not alive:
        raise typer.Exit(code=1)
