"""Tests for grd.core.lean.backend — one-shot subprocess runner + parser."""

from __future__ import annotations

import stat
from pathlib import Path

import pytest

from grd.core.lean import backend as lean_backend


def _write_fake_lean(
    tmp_path: Path,
    *,
    stdout: str = "",
    stderr: str = "",
    exit_code: int = 0,
    sleep_s: float = 0.0,
) -> Path:
    """Create an executable stub that mimics the ``lean`` CLI surface we use.

    The stub ignores its arguments, emits the requested streams, sleeps
    optionally (to exercise timeouts), and exits with the requested code.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    lean = bin_dir / "lean"
    script = (
        "#!/bin/bash\n"
        f"{'sleep ' + str(sleep_s) if sleep_s else ''}\n"
        f"cat <<'__GRD_LEAN_STDERR__' 1>&2\n{stderr}\n__GRD_LEAN_STDERR__\n"
        f"cat <<'__GRD_LEAN_STDOUT__'\n{stdout}\n__GRD_LEAN_STDOUT__\n"
        f"exit {exit_code}\n"
    )
    lean.write_text(script, encoding="utf-8")
    lean.chmod(lean.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return lean


class TestParseDiagnostics:
    def test_empty_input_yields_no_diagnostics(self) -> None:
        assert lean_backend.parse_diagnostics("") == []

    def test_single_error_line(self) -> None:
        text = "/tmp/x.lean:3:12: error: unknown identifier 'foo'\n"
        diags = lean_backend.parse_diagnostics(text)
        assert len(diags) == 1
        d = diags[0]
        assert d.severity == "error"
        assert d.file == "/tmp/x.lean"
        assert d.line == 3
        assert d.column == 12
        assert d.message == "unknown identifier 'foo'"

    def test_multi_line_message_preserved(self) -> None:
        text = "/tmp/x.lean:5:0: error: unsolved goals\n  x : Nat\n  ⊢ x + 0 = x\n"
        diags = lean_backend.parse_diagnostics(text)
        assert len(diags) == 1
        assert diags[0].severity == "error"
        assert "unsolved goals" in diags[0].message
        assert "x : Nat" in diags[0].message
        assert "x + 0 = x" in diags[0].message

    def test_multiple_diagnostics_distinct_entries(self) -> None:
        text = "/tmp/x.lean:3:12: warning: deprecated\n/tmp/x.lean:5:0: error: unsolved goals\n  ⊢ False\n"
        diags = lean_backend.parse_diagnostics(text)
        assert len(diags) == 2
        assert diags[0].severity == "warning"
        assert diags[1].severity == "error"
        assert "⊢ False" in diags[1].message

    def test_non_diagnostic_chatter_is_ignored(self) -> None:
        text = "loading Mathlib.Tactic...\n/tmp/x.lean:1:0: info: hello\ndone.\n"
        diags = lean_backend.parse_diagnostics(text)
        assert len(diags) == 1
        assert diags[0].severity == "info"


class TestRunCheck:
    def test_rejects_both_code_and_path(self, tmp_path: Path) -> None:
        result = lean_backend.run_check(code="x", path="/tmp/x.lean")
        assert result.ok is False
        assert result.error == "invalid_request"

    def test_rejects_neither_code_nor_path(self) -> None:
        result = lean_backend.run_check()
        assert result.ok is False
        assert result.error == "invalid_request"

    def test_missing_lean_reports_structured_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Empty PATH ⇒ shutil.which returns None for all tool lookups.
        monkeypatch.setenv("PATH", str(tmp_path / "does-not-exist"))
        result = lean_backend.run_check(code="theorem t : 1 = 1 := rfl")
        assert result.ok is False
        assert result.error == "lean_not_found"
        assert "grd:lean-bootstrap" in (result.error_detail or "")

    def test_missing_file_reports_io_error(self, tmp_path: Path) -> None:
        fake_lean = _write_fake_lean(tmp_path)
        result = lean_backend.run_check(
            path=str(tmp_path / "nonexistent.lean"),
            lean_path=str(fake_lean),
        )
        assert result.ok is False
        assert result.error == "io_error"

    def test_successful_run_reports_ok_and_no_error(self, tmp_path: Path) -> None:
        fake_lean = _write_fake_lean(tmp_path, stdout="", stderr="", exit_code=0)
        result = lean_backend.run_check(
            code="theorem t : 1 + 1 = 2 := by norm_num",
            lean_path=str(fake_lean),
        )
        assert result.ok is True
        assert result.error is None
        assert result.exit_code == 0
        assert result.backend == "subprocess"
        assert result.elapsed_ms >= 0

    def test_error_diagnostic_marks_result_not_ok_even_if_exit_zero(self, tmp_path: Path) -> None:
        # Real Lean exits non-zero on errors, but the parser must be
        # defensive — never report ok=True when an error diagnostic exists.
        stderr = "/tmp/x.lean:1:0: error: synthetic error for test\n"
        fake_lean = _write_fake_lean(tmp_path, stderr=stderr, exit_code=0)
        result = lean_backend.run_check(
            code="theorem bad : False := sorry",
            lean_path=str(fake_lean),
        )
        assert result.ok is False
        assert any(d.severity == "error" for d in result.diagnostics)

    def test_nonzero_exit_with_no_diagnostics_still_not_ok(self, tmp_path: Path) -> None:
        fake_lean = _write_fake_lean(tmp_path, exit_code=17)
        result = lean_backend.run_check(
            code="x",
            lean_path=str(fake_lean),
        )
        assert result.ok is False
        assert result.exit_code == 17

    def test_timeout_surfaces_structured_error(self, tmp_path: Path) -> None:
        fake_lean = _write_fake_lean(tmp_path, sleep_s=5)
        result = lean_backend.run_check(
            code="x",
            lean_path=str(fake_lean),
            timeout_s=0.3,
        )
        assert result.ok is False
        assert result.error == "timeout"

    def test_imports_prepended_to_source(self, tmp_path: Path) -> None:
        """Capture the tempfile Lean is invoked on and inspect its contents."""
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        captured = tmp_path / "captured.lean"
        lean = bin_dir / "lean"
        # Copy the source Lean was asked to compile so the test can inspect it.
        lean.write_text(
            f'#!/bin/bash\ncp -- "$1" {captured}\nexit 0\n',
            encoding="utf-8",
        )
        lean.chmod(lean.stat().st_mode | stat.S_IXUSR)

        result = lean_backend.run_check(
            code="theorem t : 1 = 1 := rfl",
            imports=["Mathlib.Tactic", "Std.Data.Nat.Basic"],
            lean_path=str(lean),
        )
        assert result.ok is True
        src = captured.read_text(encoding="utf-8")
        assert "import Mathlib.Tactic" in src
        assert "import Std.Data.Nat.Basic" in src
        assert "theorem t : 1 = 1 := rfl" in src

    def test_tempfile_removed_after_run(self, tmp_path: Path) -> None:
        fake_lean = _write_fake_lean(tmp_path)
        before = {p.name for p in Path("/tmp").iterdir() if p.name.startswith("grd_lean_check_")}
        lean_backend.run_check(
            code="x",
            lean_path=str(fake_lean),
        )
        after = {p.name for p in Path("/tmp").iterdir() if p.name.startswith("grd_lean_check_")}
        # No grd tempfiles added by our call.
        assert after - before == set()
