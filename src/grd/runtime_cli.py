"""Shared bridge for installed runtime shell invocations.

Installed prompt sources author plain ``grd`` commands. During install, runtime
adapters rewrite those shell invocations to this bridge so one runtime-agnostic
entrypoint can:

1. validate the install contract for the target runtime config dir
2. pin the active runtime deterministically
3. dispatch into the real GRD CLI without depending on runtime-private
   launcher files
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from grd.adapters import get_adapter
from grd.adapters.install_utils import build_runtime_install_repair_command
from grd.core.constants import ENV_GRD_ACTIVE_RUNTIME, ENV_GRD_DISABLE_CHECKOUT_REEXEC


def _parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    """Parse bridge arguments and return the remaining GRD CLI args."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--config-dir", required=True)
    parser.add_argument("--install-scope", choices=("local", "global"), required=True)
    parser.add_argument("--explicit-target", action="store_true")
    options, grd_args = parser.parse_known_args(argv)
    if grd_args[:1] == ["--"]:
        grd_args = grd_args[1:]
    return options, grd_args


def _resolve_config_dir(raw_value: str) -> Path:
    """Resolve the configured runtime dir from an absolute or workspace-relative reference."""
    candidate = Path(raw_value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    return (Path.cwd() / candidate).resolve(strict=False)


def _prepend_checkout_src() -> None:
    """Prefer the live checkout source tree when available."""
    from grd.version import checkout_root

    root = checkout_root()
    if root is None:
        return
    checkout_src = (root / "src").resolve(strict=False)
    if not checkout_src.is_dir():
        return

    checkout_src_str = str(checkout_src)
    if checkout_src_str not in sys.path:
        sys.path.insert(0, checkout_src_str)


def _install_error_message(
    *,
    runtime: str,
    config_dir: Path,
    install_scope: str,
    explicit_target: bool,
    missing: tuple[str, ...],
) -> str:
    """Return a deterministic repair message for an incomplete runtime install."""
    adapter = get_adapter(runtime)
    missing_list = ", ".join(f"`{relpath}`" for relpath in missing)
    repair_command = build_runtime_install_repair_command(
        runtime,
        install_scope=install_scope,
        target_dir=config_dir,
        explicit_target=explicit_target,
    )
    return (
        f"GRD runtime install incomplete for {adapter.display_name} at `{config_dir}`.\n"
        f"Missing required install artifacts: {missing_list}\n"
        f"Repair the install with: `{repair_command}`\n"
    )


def main(argv: list[str] | None = None) -> int:
    """Validate the install contract, then dispatch into ``grd.cli``."""
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    options, grd_args = _parse_args(raw_argv)
    config_dir = _resolve_config_dir(options.config_dir)
    adapter = get_adapter(options.runtime)
    missing = adapter.missing_install_artifacts(config_dir)
    if missing:
        sys.stderr.write(
            _install_error_message(
                runtime=adapter.runtime_name,
                config_dir=config_dir,
                install_scope=options.install_scope,
                explicit_target=bool(options.explicit_target),
                missing=missing,
            )
        )
        return 127

    os.environ[ENV_GRD_ACTIVE_RUNTIME] = adapter.runtime_name
    os.environ[ENV_GRD_DISABLE_CHECKOUT_REEXEC] = "1"
    _prepend_checkout_src()

    from grd.cli import entrypoint

    original_argv = list(sys.argv)
    try:
        sys.argv = ["grd", *grd_args]
        result = entrypoint()
    finally:
        sys.argv = original_argv

    if result is None:
        return 0
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
