"""``grd lean ...`` — Lean 4 verification backend.

Thin typer surface over ``grd.core.lean.*``. See that package's ``__init__``
for the layering rationale and PITCH.md §Architecture Design for the
"CLI + skills, not MCP" decision.
"""

from __future__ import annotations

from pathlib import Path

import typer

from grd.cli._helpers import _error, _get_cwd, _output

lean_app = typer.Typer(help="Lean 4 verification backend (type-check, proof daemon, env)")


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
    if not result.ok:
        raise typer.Exit(code=1)


@lean_app.command("env")
def lean_env() -> None:
    """Show detected Lean toolchain, env file status, and daemon state."""
    from grd.core.lean.env import compute_env_status

    _output(compute_env_status(_get_cwd()))


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
