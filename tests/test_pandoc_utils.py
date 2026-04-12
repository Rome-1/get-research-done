"""Tests for grd.utils.pandoc."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from grd.utils import pandoc as pandoc_mod
from grd.utils.pandoc import (
    MIN_PANDOC_VERSION,
    PandocExecutionError,
    PandocNotAvailable,
    PandocStatus,
    _parse_version,
    detect_pandoc,
    markdown_to_latex_fragment,
    run_pandoc,
)

HAS_PANDOC = shutil.which("pandoc") is not None


# ─── Unit tests: version parsing ─────────────────────────────────────────────


def test_parse_version_standard_output() -> None:
    output = "pandoc 3.1.3\nFeatures: +server +lua\nScripting engine: Lua 5.4"
    version, line = _parse_version(output)
    assert version == (3, 1, 3)
    assert line == "pandoc 3.1.3"


def test_parse_version_two_component() -> None:
    version, line = _parse_version("pandoc 2.17\n")
    assert version == (2, 17, 0)
    assert line == "pandoc 2.17"


def test_parse_version_windows_exe() -> None:
    version, _ = _parse_version("pandoc.exe 3.0.1\n")
    assert version == (3, 0, 1)


def test_parse_version_unrecognised_output() -> None:
    version, line = _parse_version("not pandoc at all")
    assert version is None
    assert line is None


# ─── Unit tests: detect_pandoc with mocks ────────────────────────────────────


def test_detect_pandoc_missing_binary() -> None:
    with patch("grd.utils.pandoc.shutil.which", return_value=None):
        status = detect_pandoc()
    assert status.available is False
    assert status.binary_path is None
    assert status.error and "not found" in status.error


def test_detect_pandoc_invokes_version(monkeypatch: pytest.MonkeyPatch) -> None:
    # shutil.which returns a stub path; subprocess.run returns a fake pandoc
    monkeypatch.setattr(pandoc_mod.shutil, "which", lambda name: f"/usr/bin/{name}" if name == "pandoc" else None)
    fake = MagicMock(returncode=0, stdout="pandoc 3.1.3\n", stderr="")
    monkeypatch.setattr(pandoc_mod.subprocess, "run", lambda *a, **kw: fake)
    status = detect_pandoc()
    assert status.available is True
    assert status.version == (3, 1, 3)
    assert status.meets_minimum is True


def test_detect_pandoc_below_minimum(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pandoc_mod.shutil, "which", lambda name: f"/usr/bin/{name}" if name == "pandoc" else None)
    fake = MagicMock(returncode=0, stdout="pandoc 2.5\n", stderr="")
    monkeypatch.setattr(pandoc_mod.subprocess, "run", lambda *a, **kw: fake)
    status = detect_pandoc()
    assert status.available is True
    assert status.meets_minimum is False


def test_detect_pandoc_version_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pandoc_mod.shutil, "which", lambda name: "/usr/bin/pandoc" if name == "pandoc" else None)
    fake = MagicMock(returncode=2, stdout="", stderr="boom")
    monkeypatch.setattr(pandoc_mod.subprocess, "run", lambda *a, **kw: fake)
    status = detect_pandoc()
    assert status.available is False
    assert status.error and "exited" in status.error


def test_detect_pandoc_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pandoc_mod.shutil, "which", lambda name: "/usr/bin/pandoc" if name == "pandoc" else None)

    def raise_timeout(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd="pandoc --version", timeout=5)

    monkeypatch.setattr(pandoc_mod.subprocess, "run", raise_timeout)
    status = detect_pandoc()
    assert status.available is False
    assert status.error and "timed out" in status.error


def test_pandoc_status_require_raises_when_missing() -> None:
    with pytest.raises(PandocNotAvailable):
        PandocStatus(available=False, error="nope").require()


def test_pandoc_status_require_raises_when_too_old() -> None:
    with pytest.raises(PandocNotAvailable):
        PandocStatus(
            available=True,
            binary_path="/usr/bin/pandoc",
            version=(2, 0, 0),
            version_string="pandoc 2.0",
            meets_minimum=False,
        ).require()


def test_pandoc_status_require_ok_when_meets_minimum() -> None:
    PandocStatus(
        available=True,
        binary_path="/usr/bin/pandoc",
        version=MIN_PANDOC_VERSION + (0,),
        version_string=f"pandoc {MIN_PANDOC_VERSION[0]}.{MIN_PANDOC_VERSION[1]}",
        meets_minimum=True,
    ).require()


# ─── Unit tests: run_pandoc error handling (mocked) ──────────────────────────


def test_run_pandoc_raises_when_not_available() -> None:
    status = PandocStatus(available=False, error="missing")
    with pytest.raises(PandocNotAvailable):
        run_pandoc("hi", status=status)


def test_run_pandoc_raises_on_nonzero_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    status = PandocStatus(
        available=True,
        binary_path="/usr/bin/pandoc",
        version=(3, 1, 3),
        version_string="pandoc 3.1.3",
        meets_minimum=True,
    )
    fake = MagicMock(returncode=1, stdout="", stderr="syntax error")
    monkeypatch.setattr(pandoc_mod.subprocess, "run", lambda *a, **kw: fake)
    with pytest.raises(PandocExecutionError) as exc:
        run_pandoc("# hi", status=status)
    assert "exited 1" in str(exc.value)
    assert exc.value.stderr == "syntax error"


def test_run_pandoc_builds_expected_command(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    status = PandocStatus(
        available=True,
        binary_path="/usr/bin/pandoc",
        version=(3, 1, 3),
        version_string="pandoc 3.1.3",
        meets_minimum=True,
    )
    recorded: dict[str, object] = {}

    def fake_run(cmd: list[str], *, input: str, capture_output: bool, text: bool, timeout: float, check: bool) -> MagicMock:
        recorded["cmd"] = cmd
        recorded["input"] = input
        return MagicMock(returncode=0, stdout="LATEX", stderr="")

    monkeypatch.setattr(pandoc_mod.subprocess, "run", fake_run)
    lua = tmp_path / "foo.lua"
    lua.write_text("-- noop")
    out = run_pandoc(
        "hello",
        lua_filters=[lua],
        citeproc=True,
        extra_args=["--wrap=none"],
        status=status,
    )
    assert out == "LATEX"
    cmd = recorded["cmd"]
    assert cmd[0] == "/usr/bin/pandoc"
    assert "--lua-filter" in cmd and str(lua) in cmd
    assert "--citeproc" in cmd
    assert "--wrap=none" in cmd
    assert "-f" in cmd and "-t" in cmd


# ─── Integration tests: real pandoc ──────────────────────────────────────────


@pytest.mark.skipif(not HAS_PANDOC, reason="pandoc not installed")
def test_detect_pandoc_real_binary() -> None:
    status = detect_pandoc()
    assert status.available is True
    assert status.binary_path is not None
    assert status.version is not None


@pytest.mark.skipif(not HAS_PANDOC, reason="pandoc not installed")
def test_markdown_to_latex_fragment_basic() -> None:
    out = markdown_to_latex_fragment("# Hello\n\nWorld with *emphasis*.\n")
    assert "\\section" in out or "\\hypertarget" in out  # depends on pandoc version
    assert "\\emph{emphasis}" in out
    # No document wrapper for fragments.
    assert "\\documentclass" not in out
    assert "\\begin{document}" not in out


@pytest.mark.skipif(not HAS_PANDOC, reason="pandoc not installed")
def test_markdown_to_latex_fragment_escapes_underscores() -> None:
    # The very error category that `latex.py`'s autofix exists for:
    # unescaped underscores in prose. Pandoc escapes them correctly in the AST.
    out = markdown_to_latex_fragment("A variable named `foo_bar` is used.\n")
    assert "foo\\_bar" in out or "\\texttt{foo\\_bar}" in out


@pytest.mark.skipif(not HAS_PANDOC, reason="pandoc not installed")
def test_markdown_to_latex_fragment_preserves_math() -> None:
    out = markdown_to_latex_fragment("Einstein said $E = mc^2$.\n")
    # Pandoc passes math through in dollar form for LaTeX output.
    assert "E = mc^2" in out


@pytest.mark.skipif(not HAS_PANDOC, reason="pandoc not installed")
def test_markdown_to_latex_fragment_preserves_display_math() -> None:
    out = markdown_to_latex_fragment("$$\\int_0^1 x\\,dx = \\tfrac{1}{2}$$\n")
    assert "\\int_0^1" in out
