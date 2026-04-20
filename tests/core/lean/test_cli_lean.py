"""Tests for the ``grd lean`` CLI surface."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest
from typer.testing import CliRunner

from grd.cli import app
from grd.cli.lean import EXIT_ENV_ERROR, EXIT_INPUT_ERROR, EXIT_SOFT_FAIL

runner = CliRunner()


def _stub_lean(bin_dir: Path, *, exit_code: int = 0) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    lean = bin_dir / "lean"
    lean.write_text(
        f"#!/bin/bash\nexit {exit_code}\n",
        encoding="utf-8",
    )
    lean.chmod(lean.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return lean


def test_help_lists_lean_subcommands() -> None:
    result = runner.invoke(app, ["lean", "--help"])
    assert result.exit_code == 0
    for cmd in (
        "check",
        "typecheck-file",
        "env",
        "serve-repl",
        "stop-repl",
        "ping",
        "bootstrap",
        "prove",
        "stub-claim",
    ):
        assert cmd in result.stdout


def test_env_command_raw_emits_valid_json(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(app, ["--raw", "--cwd", str(tmp_path), "lean", "env"])
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert "lean_found" in parsed
    assert "daemon_running" in parsed
    assert parsed["env_file"].endswith("/.grd/lean-env.json")
    # P0-3: callers branch on these synthesized fields, so they must be present.
    assert "ready" in parsed
    assert "blocked_by" in parsed


def test_env_command_human_output_prints_not_ready_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Empty PATH → elan/lean/lake all missing → summary line must surface the
    # bootstrap pointer so a human doesn't re-implement readiness by eye.
    (tmp_path / ".grd").mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    result = runner.invoke(app, ["--cwd", str(tmp_path), "lean", "env"])
    assert result.exit_code == 0, result.stdout
    assert "Lean environment not ready" in result.stdout
    assert "/grd:lean-bootstrap" in result.stdout
    assert "elan" in result.stdout


def test_check_with_missing_lean_exits_nonzero_and_emits_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".grd").mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "check",
            "theorem t : 1 = 1 := rfl",
            "--no-daemon",
        ],
    )
    # ge-oc0: lean_not_found is an environment error → exit 3, not 1.
    assert result.exit_code == EXIT_ENV_ERROR
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is False
    assert parsed["error"] == "lean_not_found"


def test_check_with_stub_lean_exits_zero_no_daemon(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / ".grd").mkdir()
    _stub_lean(tmp_path / "bin")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    result = runner.invoke(
        app,
        [
            "--raw",
            "--cwd",
            str(tmp_path),
            "lean",
            "check",
            "theorem t : 1 = 1 := rfl",
            "--no-daemon",
        ],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is True
    assert parsed["backend"] == "subprocess"


def test_check_rejects_both_inline_code_and_file(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    lean_file = tmp_path / "x.lean"
    lean_file.write_text("theorem t : 1 = 1 := rfl\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "lean",
            "check",
            "inline code",
            "--file",
            str(lean_file),
        ],
    )
    # ge-oc0: bad flag combo is a user input error → exit 2.
    assert result.exit_code == EXIT_INPUT_ERROR


def test_typecheck_file_nonexistent_errors(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "lean",
            "typecheck-file",
            str(tmp_path / "nope.lean"),
        ],
    )
    # ge-oc0: nonexistent file is user input error → exit 2.
    assert result.exit_code == EXIT_INPUT_ERROR


def test_ping_when_no_daemon_exits_nonzero(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(app, ["--raw", "--cwd", str(tmp_path), "lean", "ping"])
    assert result.exit_code == 1
    parsed = json.loads(result.stdout)
    assert parsed["ok"] is False
    assert parsed["alive"] is False


def test_stop_repl_is_noop_when_no_daemon(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(app, ["--raw", "--cwd", str(tmp_path), "lean", "stop-repl"])
    assert result.exit_code == 0, result.stdout


def test_bootstrap_dry_run_emits_structured_report(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(app, ["--raw", "--cwd", str(tmp_path), "lean", "bootstrap", "--dry-run"])
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert "stages" in parsed
    assert parsed["ok"] is True
    stage_names = [s["name"] for s in parsed["stages"]]
    assert "elan" in stage_names
    assert "toolchain" in stage_names
    assert "pantograph" in stage_names


def test_bootstrap_uninstall_dry_run(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(
        app,
        ["--raw", "--cwd", str(tmp_path), "lean", "bootstrap", "--uninstall", "--dry-run"],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed["dry_run"] is True
    assert isinstance(parsed["paths"], list)


# ─── ge-xvaw / P2-5: --audit-mode preset ─────────────────────────────────────


def test_audit_mode_aliases_bootstrap_dry_run(tmp_path: Path) -> None:
    # ge-xvaw: --audit-mode is the read-only preset. For bootstrap, it must
    # force --dry-run so CI / unprivileged audits never install. The must-run
    # stages (elan / toolchain / pantograph) emit detail lines prefixed with
    # "dry-run:" whenever they're in dry-run mode, so checking those three
    # is sufficient without over-specifying on the skippable stages.
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(
        app,
        ["--raw", "--audit-mode", "--cwd", str(tmp_path), "lean", "bootstrap"],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert "stages" in parsed
    stage_details = {s["name"]: (s.get("detail") or "") for s in parsed["stages"]}
    for must_run in ("elan", "toolchain", "pantograph"):
        assert stage_details[must_run].startswith("dry-run:"), stage_details[must_run]


def test_audit_mode_normalizer_hoists_from_end_of_argv() -> None:
    # ge-xvaw: --audit-mode must hoist like --raw / --cwd, so agents can
    # append it after the subcommand on the real argv (``sys.argv``). Typer's
    # CliRunner bypasses our __call__ override, so we test the normalizer
    # directly — the production path invokes ``_normalize_global_cli_options``
    # before Typer parses the argv.
    from grd.cli._helpers import _normalize_global_cli_options

    argv = ["lean", "bootstrap", "--audit-mode", "--cwd", "/x"]
    normalized = _normalize_global_cli_options(argv)
    # Both globals are hoisted ahead of the subcommand path.
    assert normalized.index("--audit-mode") < normalized.index("lean")
    assert normalized.index("--cwd") < normalized.index("lean")


def test_audit_mode_aliases_check_no_daemon(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # ge-xvaw: --audit-mode must force --no-daemon for ``grd lean check`` so
    # no socket/PID file is written and no daemon is auto-spawned.
    (tmp_path / ".grd").mkdir()
    _stub_lean(tmp_path / "bin")
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    result = runner.invoke(
        app,
        [
            "--raw",
            "--audit-mode",
            "--cwd",
            str(tmp_path),
            "lean",
            "check",
            "theorem t : 1 = 1 := rfl",
        ],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    # backend == "subprocess" confirms we did not go through the daemon.
    assert parsed["backend"] == "subprocess"
    # No daemon socket should have been created under .grd/.
    assert not (tmp_path / ".grd" / "lean-daemon.sock").exists()
    assert not (tmp_path / ".grd" / "lean-daemon.pid").exists()


def test_audit_mode_shown_in_root_help() -> None:
    # ge-xvaw: --audit-mode must be discoverable from the root --help.
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--audit-mode" in result.stdout


def test_check_help_lists_side_effects() -> None:
    # ge-xvaw: every lean subcommand that supports the audit preset must
    # document its side effects in --help.
    result = runner.invoke(app, ["lean", "check", "--help"])
    assert result.exit_code == 0
    assert "SIDE EFFECTS" in result.stdout


def test_bootstrap_help_lists_side_effects() -> None:
    result = runner.invoke(app, ["lean", "bootstrap", "--help"])
    assert result.exit_code == 0
    assert "SIDE EFFECTS" in result.stdout


def test_prove_list_tactics_raw_matches_default_ladder(tmp_path: Path) -> None:
    # P0-7: the CLI is the single source of truth for the ladder. The agent
    # doc (grd-prover.md) references this flag instead of hardcoding the list
    # so a mismatch here is a regression.
    from grd.core.lean.prove import DEFAULT_TACTIC_LADDER

    (tmp_path / ".grd").mkdir()
    result = runner.invoke(
        app,
        ["--raw", "--cwd", str(tmp_path), "lean", "prove", "--list-tactics"],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed == {"tactics": list(DEFAULT_TACTIC_LADDER)}


def test_prove_list_tactics_excludes_polyrith() -> None:
    # Doc drift guard: grd-prover.md used to advertise polyrith in the ladder
    # but it depends on an external Sage API call — deliberately not shipped.
    # If polyrith ever re-enters the default, update the agent doc too.
    from grd.core.lean.prove import DEFAULT_TACTIC_LADDER

    assert "polyrith" not in DEFAULT_TACTIC_LADDER


def test_prove_without_statement_or_flag_errors(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    result = runner.invoke(app, ["--raw", "--cwd", str(tmp_path), "lean", "prove"])
    # ge-oc0: missing required argument is user input error → exit 2.
    assert result.exit_code == EXIT_INPUT_ERROR
    # --raw routes the error through err_console as JSON; CliRunner merges
    # stdout+stderr into .output. The message must point at the flag so a
    # user who typos 'grd lean prove' learns about --list-tactics.
    assert "--list-tactics" in result.output


def test_prove_list_tactics_does_not_require_lean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Metadata query: must work on a bare machine with no Lean installed.
    (tmp_path / ".grd").mkdir()
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    result = runner.invoke(
        app,
        ["--raw", "--cwd", str(tmp_path), "lean", "prove", "--list-tactics"],
    )
    assert result.exit_code == 0, result.stdout
    parsed = json.loads(result.stdout)
    assert parsed["tactics"]  # non-empty list


# ─── ge-oc0: split exit code contract tests ─────────────────────────────────


def test_exit_code_constants_match_spec() -> None:
    """Guard the contract: if the constants change, tests will catch the drift."""
    from grd.cli.lean import EXIT_ENV_ERROR, EXIT_INPUT_ERROR, EXIT_INTERNAL_ERROR, EXIT_SOFT_FAIL

    assert EXIT_SOFT_FAIL == 1
    assert EXIT_INPUT_ERROR == 2
    assert EXIT_ENV_ERROR == 3
    assert EXIT_INTERNAL_ERROR == 4


def test_exit_code_for_result_maps_lean_not_found_to_env() -> None:
    from grd.cli.lean import _exit_code_for_result
    from grd.core.lean.protocol import LeanCheckResult

    result = LeanCheckResult(ok=False, error="lean_not_found", error_detail="lean binary not on PATH")
    assert _exit_code_for_result(result) == EXIT_ENV_ERROR


def test_exit_code_for_result_maps_internal_error_to_internal() -> None:
    from grd.cli.lean import EXIT_INTERNAL_ERROR, _exit_code_for_result
    from grd.core.lean.protocol import LeanCheckResult

    result = LeanCheckResult(ok=False, error="internal_error", error_detail="unexpected crash")
    assert _exit_code_for_result(result) == EXIT_INTERNAL_ERROR


def test_exit_code_for_result_maps_elaboration_error_to_soft_fail() -> None:
    from grd.cli.lean import _exit_code_for_result
    from grd.core.lean.protocol import LeanCheckResult, LeanDiagnostic

    # ok=False with no error field → elaboration error (Lean said "no").
    result = LeanCheckResult(
        ok=False,
        diagnostics=[LeanDiagnostic(severity="error", message="type mismatch")],
    )
    assert _exit_code_for_result(result) == EXIT_SOFT_FAIL


# ─── ge-4yl: _lean_internal_guard exception wrapping ──────────────────────


def test_guard_catches_unexpected_exception_with_exit_4(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected exceptions inside guarded commands must exit 4 with structured JSON."""
    (tmp_path / ".grd").mkdir()

    def _boom(*_a: object, **_kw: object) -> None:
        raise RuntimeError("kaboom from test")

    monkeypatch.setattr("grd.core.lean.bootstrap.run_bootstrap", _boom)

    result = runner.invoke(
        app,
        ["--raw", "--cwd", str(tmp_path), "lean", "bootstrap"],
    )
    assert result.exit_code == 4, f"exit={result.exit_code} out={result.output!r}"
    # err_console.print_json pretty-prints; parse the full output block.
    parsed = json.loads(result.output)
    assert parsed["ok"] is False
    assert parsed["error"]["kind"] == "internal_error"
    assert "kaboom from test" in parsed["error"]["message"]
    assert parsed["error"]["detail"]  # non-empty traceback tail


def test_guard_passes_through_known_exceptions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GRDError, KeyError, TimeoutError must NOT be caught by the guard."""
    from grd.core.errors import GRDError

    (tmp_path / ".grd").mkdir()

    def _raise_grd(*_a: object, **_kw: object) -> None:
        raise GRDError("deliberate GRDError")

    monkeypatch.setattr("grd.core.lean.bootstrap.run_bootstrap", _raise_grd)

    result = runner.invoke(
        app,
        ["--raw", "--cwd", str(tmp_path), "lean", "bootstrap"],
    )
    # _GRDTyper catches GRDError and exits 1, NOT 4.
    assert result.exit_code == 1


def test_guard_raw_output_for_unexpected_exception_in_verify_claim(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """verify-claim must emit structured JSON for unexpected exceptions."""
    (tmp_path / ".grd").mkdir()

    def _boom(**_kw: object) -> None:
        raise ValueError("bad pipeline value")

    monkeypatch.setattr("grd.core.lean.autoformalize.verify_claim", _boom)

    result = runner.invoke(
        app,
        ["--raw", "--cwd", str(tmp_path), "lean", "verify-claim", "x", "--no-llm"],
    )
    assert result.exit_code == 4
    # Parse only the last JSON object (guard output, not any prior output).
    parsed = json.loads(result.output)
    assert parsed["ok"] is False
    assert parsed["error"]["kind"] == "internal_error"
    assert "bad pipeline value" in parsed["error"]["message"]


def test_check_no_input_exits_with_input_error(tmp_path: Path) -> None:
    (tmp_path / ".grd").mkdir()
    # CliRunner simulates non-tty stdin, so stdin fallback reads empty → input error.
    result = runner.invoke(
        app,
        ["--cwd", str(tmp_path), "lean", "check"],
        input="",
    )
    assert result.exit_code == EXIT_INPUT_ERROR


def test_check_help_documents_heartbeat_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    """--max-heartbeat-retries / --initial-heartbeats must be discoverable (ge-l9cz)."""
    # Widen the help-output terminal so typer doesn't text-wrap the flag name
    # across column boundaries and hide the substring we're asserting on.
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.setenv("TERMINAL_WIDTH", "200")
    result = runner.invoke(app, ["lean", "check", "--help"], terminal_width=200)
    assert result.exit_code == 0
    assert "max-heartbeat-retries" in result.stdout
    assert "initial-heartbeats" in result.stdout


def test_prove_help_documents_heartbeat_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.setenv("TERMINAL_WIDTH", "200")
    result = runner.invoke(app, ["lean", "prove", "--help"], terminal_width=200)
    assert result.exit_code == 0
    assert "max-heartbeat-retries" in result.stdout
    assert "initial-heartbeats" in result.stdout


def _retry_stub_bin(tmp_path: Path, *, counter: Path, first_exit: int, later_exit: int, stderr: str) -> Path:
    """Create a lean stub bin_dir and return it.

    ``counter`` is an on-disk file updated by the stub on each call; the
    test reads it to confirm the retry layer fired. Uses ``awk`` via
    the shared PATH to avoid dragging ``cat`` into a hand-rolled stub
    PATH.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    script = bin_dir / "lean"
    # Absolute path to /bin/cat is hermetic — avoids PATH manipulation
    # issues when callers prepend bin_dir.
    script.write_text(
        "#!/bin/bash\n"
        f"n=$(/bin/cat {counter})\n"
        f"echo $((n+1)) > {counter}\n"
        'if [ "$n" = "0" ]; then\n'
        f"  echo '{stderr}' >&2\n"
        f"  exit {first_exit}\n"
        "fi\n"
        f"exit {later_exit}\n",
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return bin_dir


def test_check_retries_on_heartbeat_timeout_and_prints_suggestion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end: baseline times out, retry at 400k succeeds, suggestion lands."""
    (tmp_path / ".grd").mkdir()
    counter = tmp_path / "counter"
    counter.write_text("0", encoding="utf-8")

    bin_dir = _retry_stub_bin(
        tmp_path,
        counter=counter,
        first_exit=1,
        later_exit=0,
        stderr=(
            "stub.lean:1:0: error: (deterministic) timeout at `whnf`, "
            "maximum number of heartbeats (200000) has been reached"
        ),
    )
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "lean",
            "check",
            "theorem t : 1 = 1 := rfl",
            "--no-daemon",
            "--max-heartbeat-retries",
            "2",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Heartbeat auto-retry" in result.output
    assert "maxHeartbeats=400000" in result.output
    # Stub was called at least twice: baseline + one retry.
    assert int(counter.read_text()) >= 2


def test_check_no_auto_retry_when_flag_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--max-heartbeat-retries 0 preserves one-shot behaviour (no retry)."""
    (tmp_path / ".grd").mkdir()
    counter = tmp_path / "counter"
    counter.write_text("0", encoding="utf-8")

    bin_dir = _retry_stub_bin(
        tmp_path,
        counter=counter,
        first_exit=1,
        later_exit=1,
        stderr="stub.lean:1:0: error: maximum number of heartbeats has been reached",
    )
    monkeypatch.setenv("PATH", f"{bin_dir}:/usr/bin:/bin")

    result = runner.invoke(
        app,
        [
            "--cwd",
            str(tmp_path),
            "lean",
            "check",
            "x",
            "--no-daemon",
            "--max-heartbeat-retries",
            "0",
        ],
    )
    assert result.exit_code == EXIT_SOFT_FAIL
    assert int(counter.read_text()) == 1
    assert "Heartbeat auto-retry" not in result.output
