"""Tests for the shared installed runtime CLI bridge."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from grd.core.constants import ENV_GRD_ACTIVE_RUNTIME, ENV_GRD_DISABLE_CHECKOUT_REEXEC
from grd.runtime_cli import main


def _mark_complete_install(config_dir: Path, *, runtime: str, install_scope: str = "local") -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "get-research-done").mkdir(parents=True, exist_ok=True)
    (config_dir / "grd-file-manifest.json").write_text(
        json.dumps({"runtime": runtime, "install_scope": install_scope}),
        encoding="utf-8",
    )


def test_runtime_cli_fails_cleanly_for_incomplete_install(tmp_path: Path, capsys) -> None:
    config_dir = tmp_path / ".codex"
    config_dir.mkdir()

    exit_code = main(
        [
            "--runtime",
            "codex",
            "--config-dir",
            str(config_dir),
            "--install-scope",
            "local",
            "state",
            "load",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 127
    assert "GRD runtime install incomplete for Codex" in captured.err
    assert "`grd-file-manifest.json`" in captured.err
    assert "`get-research-done`" in captured.err
    assert "npx -y get-research-done --codex --local" in captured.err


def test_runtime_cli_dispatches_with_runtime_pin(monkeypatch, tmp_path: Path) -> None:
    config_dir = tmp_path / ".codex"
    _mark_complete_install(config_dir, runtime="codex")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("grd.version.checkout_root", lambda start=None: None)

    observed: dict[str, object] = {}

    def fake_entrypoint() -> int:
        observed["argv"] = list(sys.argv)
        observed["runtime"] = os.environ.get(ENV_GRD_ACTIVE_RUNTIME)
        observed["disable_reexec"] = os.environ.get(ENV_GRD_DISABLE_CHECKOUT_REEXEC)
        return 0

    monkeypatch.setattr("grd.cli.entrypoint", fake_entrypoint)

    exit_code = main(
        [
            "--runtime",
            "codex",
            "--config-dir",
            "./.codex",
            "--install-scope",
            "local",
            "state",
            "load",
        ]
    )

    assert exit_code == 0
    assert observed["argv"] == ["grd", "state", "load"]
    assert observed["runtime"] == "codex"
    assert observed["disable_reexec"] == "1"
