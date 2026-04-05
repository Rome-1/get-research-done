"""Direct tests for shared root-global CLI argv parsing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from gpd.core.cli_args import (
    normalize_root_global_cli_options,
    resolve_root_global_cli_cwd_from_argv,
    split_root_global_cli_options,
)


def test_split_root_global_cli_options_moves_global_options_before_subcommand_and_keeps_passthrough() -> None:
    argv = [
        "validate",
        "command-context",
        "gpd:new-project",
        "--cwd",
        "/tmp/workspace",
        "--raw",
        "--",
        "--cwd",
        "/tmp/ignored",
        "--raw",
    ]

    global_args, remaining_args = split_root_global_cli_options(argv)

    assert global_args == ["--cwd", "/tmp/workspace", "--raw"]
    assert remaining_args == [
        "validate",
        "command-context",
        "gpd:new-project",
        "--",
        "--cwd",
        "/tmp/ignored",
        "--raw",
    ]


def test_normalize_root_global_cli_options_preserves_root_global_prefix_order() -> None:
    argv = [
        "validate",
        "command-context",
        "gpd:new-project",
        "--cwd",
        "/tmp/workspace",
        "--raw",
    ]

    assert normalize_root_global_cli_options(argv) == [
        "--cwd",
        "/tmp/workspace",
        "--raw",
        "validate",
        "command-context",
        "gpd:new-project",
    ]


def test_resolve_root_global_cli_cwd_from_argv_uses_last_pre_passthrough_cwd(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    argv = [
        "validate",
        "command-context",
        "--cwd",
        "first",
        "--raw",
        "--cwd",
        "second",
        "--",
        "--cwd",
        "ignored",
    ]

    with patch("gpd.core.cli_args.Path.cwd", return_value=tmp_path):
        resolved = resolve_root_global_cli_cwd_from_argv(argv)

    assert resolved == second.resolve(strict=False)
