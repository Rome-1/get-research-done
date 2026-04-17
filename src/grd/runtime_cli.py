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
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from grd.adapters import get_adapter
from grd.adapters.install_utils import (
    AGENTS_DIR_NAME,
    COMMANDS_DIR_NAME,
    FLAT_COMMANDS_DIR_NAME,
    GRD_INSTALL_DIR_NAME,
    HOOKS_DIR_NAME,
    build_runtime_install_repair_command,
)
from grd.core.cli_args import resolve_root_global_cli_cwd_from_argv as _resolve_cli_cwd_from_argv
from grd.core.constants import ENV_GRD_ACTIVE_RUNTIME, ENV_GRD_DISABLE_CHECKOUT_REEXEC
from grd.hooks.install_metadata import load_install_manifest_runtime_status
from grd.hooks.runtime_detect import normalize_runtime_name


def _parse_args(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    """Parse bridge arguments and return the remaining GRD CLI args."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--config-dir", required=True)
    parser.add_argument("--install-scope", choices=("local", "global"), required=True)
    parser.add_argument("--explicit-target", action="store_true")
    bridge_args: list[str] = []
    index = 0
    while index < len(argv):
        arg = str(argv[index])
        if arg == "--explicit-target":
            bridge_args.append(arg)
            index += 1
            continue
        if any(arg.startswith(prefix) for prefix in ("--runtime=", "--config-dir=", "--install-scope=")):
            bridge_args.append(arg)
            index += 1
            continue
        if arg in {"--runtime", "--config-dir", "--install-scope"}:
            bridge_args.append(arg)
            if index + 1 < len(argv):
                bridge_args.append(str(argv[index + 1]))
            index += 2
            continue
        break

    options = parser.parse_args(bridge_args)
    grd_args = argv[index:]
    if grd_args[:1] == ["--"]:
        grd_args = grd_args[1:]
    try:
        _validate_root_global_cli_passthrough(grd_args)
    except ValueError as exc:
        raise _BridgeArgumentError(str(exc)) from exc
    return options, grd_args


def _bridge_argument_error_message(message: str) -> str:
    """Return a stable user-facing message for malformed bridge invocations."""
    return f"GRD runtime bridge rejected malformed bridge invocation.\n{message}"


def _runtime_display_name(runtime: str) -> str:
    """Return a human-readable runtime label when the runtime is known."""
    try:
        return get_adapter(runtime).display_name
    except KeyError:
        return runtime


def _format_unknown_runtime_error(exc: KeyError) -> str:
    """Return the stable user-facing message for an unknown runtime."""
    if len(exc.args) == 1 and isinstance(exc.args[0], str):
        return exc.args[0]
    return str(exc)


def _bridge_failure(kind: _BridgeFailureKind, message: str, *, exit_code: int = 127) -> _BridgeFailure:
    """Build a structured failure record for bridge rejection paths."""

    return _BridgeFailure(kind=kind, message=message, exit_code=exit_code)


def _emit_bridge_failure(failure: _BridgeFailure) -> int:
    """Write a structured bridge failure to stderr and return its exit code."""

    sys.stderr.write(failure.message)
    if not failure.message.endswith("\n"):
        sys.stderr.write("\n")
    return failure.exit_code


def _canonical_runtime_name(runtime: str) -> str:
    """Return the canonical runtime id for aliases and display names."""
    normalized = normalize_runtime_name(runtime)
    if normalized is not None:
        return normalized
    return runtime.strip()


def _paths_equal(left: Path, right: Path) -> bool:
    """Return whether two paths resolve to the same location when comparable."""
    try:
        return left.expanduser().resolve() == right.expanduser().resolve()
    except OSError:
        return left.expanduser() == right.expanduser()


def _is_matching_local_install_candidate(candidate: Path, *, runtime: str) -> bool:
    """Return whether *candidate* should satisfy a local bridge config-dir lookup."""
    if not candidate.is_dir():
        return False

    adapter = get_adapter(runtime)
    manifest_status, manifest, manifest_runtime = load_install_manifest_runtime_status(candidate)
    if manifest_status == "ok":
        if manifest_runtime != runtime:
            return False

        manifest_scope = manifest.get("install_scope")
        return manifest_scope == "local"

    global_config_dirs = resolve_global_config_dir_candidates(adapter.runtime_descriptor, home=Path.home())
    has_install_markers = config_dir_has_managed_install_markers(candidate)
    if not has_install_markers:
        return False
    if any(_paths_equal(candidate, global_dir) for global_dir in global_config_dirs):
        return False
    return True


def _has_managed_install_markers(config_dir: Path) -> bool:
    """Return whether *config_dir* already looks like a managed install surface."""
    return any(
        (
            (config_dir / GRD_INSTALL_DIR_NAME).is_dir(),
            (config_dir / COMMANDS_DIR_NAME / "grd").is_dir(),
            (config_dir / FLAT_COMMANDS_DIR_NAME).is_dir(),
            (config_dir / AGENTS_DIR_NAME).is_dir(),
            (config_dir / HOOKS_DIR_NAME).is_dir(),
        )
    )


def _resolve_local_config_dir(raw_value: str, *, runtime: str, cli_cwd: Path) -> Path:
    """Resolve a local config dir reference against the nearest matching ancestor."""
    relative = Path(raw_value).expanduser()
    resolved_cwd = cli_cwd.resolve(strict=False)
    for base in (resolved_cwd, *resolved_cwd.parents):
        candidate = (base / relative).resolve(strict=False)
        if _is_matching_local_install_candidate(candidate, runtime=runtime):
            return candidate
    return (resolved_cwd / relative).resolve(strict=False)


def _resolve_config_dir(
    raw_value: str,
    *,
    runtime: str,
    install_scope: str,
    explicit_target: bool,
    cli_cwd: Path,
) -> Path:
    """Resolve the configured runtime dir from an absolute or local-workspace reference."""
    candidate = Path(raw_value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    if install_scope == "local" and not explicit_target:
        return _resolve_local_config_dir(raw_value, runtime=runtime, cli_cwd=cli_cwd)
    return (cli_cwd / candidate).resolve(strict=False)


def _uses_effective_explicit_target(
    *,
    runtime: str,
    config_dir: Path,
    install_scope: str,
    explicit_target: bool,
    cli_cwd: Path,
) -> bool:
    """Return whether repair guidance must emit ``--target-dir``."""
    if explicit_target:
        return True

    adapter = get_adapter(runtime)
    if install_scope == "global":
        canonical_global_dir = adapter.resolve_global_config_dir(home=Path.home())
        return not _paths_equal(config_dir, canonical_global_dir)

    default_local_config_dir = adapter.resolve_local_config_dir(cli_cwd).resolve(strict=False)
    return not _paths_equal(config_dir, default_local_config_dir)


def _build_repair_command(
    *,
    runtime: str,
    config_dir: Path,
    install_scope: str,
    explicit_target: bool,
    cli_cwd: Path,
) -> str:
    """Return the reinstall command with the effective target-dir projection."""

    return build_runtime_install_repair_command(
        runtime,
        install_scope=install_scope,
        target_dir=config_dir,
        explicit_target=_uses_effective_explicit_target(
            runtime=runtime,
            config_dir=config_dir,
            install_scope=install_scope,
            explicit_target=explicit_target,
            cli_cwd=cli_cwd,
        ),
    )


def _maybe_reexec_from_checkout(raw_argv: list[str], *, cli_cwd: Path) -> None:
    """Re-exec through a checkout when the active package does not match it."""
    from grd.version import checkout_root

    if os.environ.get(ENV_GRD_DISABLE_CHECKOUT_REEXEC) == "1":
        return

    root = checkout_root(cli_cwd)
    if root is None:
        return

    checkout_grd = (root / "src" / "grd").resolve(strict=False)
    active_grd = Path(__file__).resolve().parent
    if active_grd == checkout_grd:
        return

    env = os.environ.copy()
    checkout_src = str((root / "src").resolve(strict=False))
    existing_pythonpath = [entry for entry in env.get("PYTHONPATH", "").split(os.pathsep) if entry]
    if checkout_src not in existing_pythonpath:
        env["PYTHONPATH"] = os.pathsep.join([checkout_src, *existing_pythonpath]) if existing_pythonpath else checkout_src
    env[ENV_GRD_DISABLE_CHECKOUT_REEXEC] = "1"
    os.execve(sys.executable, [sys.executable, "-m", "grd.runtime_cli", *raw_argv], env)


def _install_error_message(
    *,
    runtime: str,
    config_dir: Path,
    install_scope: str,
    explicit_target: bool,
    cli_cwd: Path,
    missing: tuple[str, ...],
) -> str:
    """Return a deterministic repair message for an incomplete runtime install."""
    adapter = get_adapter(runtime)
    missing_list = ", ".join(f"`{relpath}`" for relpath in missing)
    repair_command = _build_repair_command(
        runtime=runtime,
        config_dir=config_dir,
        install_scope=install_scope,
        explicit_target=explicit_target,
        cli_cwd=cli_cwd,
    )
    return (
        f"GRD runtime install incomplete for {adapter.display_name} at `{config_dir}`.\n"
        f"Missing required install artifacts: {missing_list}\n"
        f"Repair the install with: `{repair_command}`"
    )


def _runtime_mismatch_error_message(
    *,
    runtime: str,
    manifest_runtime: str,
    manifest_install_scope: str | None,
    config_dir: Path,
    install_scope: str,
    explicit_target: bool,
    cli_cwd: Path,
) -> str:
    """Return repair guidance when the resolved config dir belongs to another runtime."""
    owning_install_scope = manifest_install_scope if manifest_install_scope in {"local", "global"} else install_scope
    repair_command = _build_repair_command(
        runtime=manifest_runtime,
        config_dir=config_dir,
        install_scope=owning_install_scope,
        explicit_target=explicit_target,
        cli_cwd=cli_cwd,
    )
    return (
        f"GRD runtime bridge mismatch for {_runtime_display_name(runtime)} at `{config_dir}`.\n"
        f"Resolved install manifest pins {_runtime_display_name(manifest_runtime)} (`{manifest_runtime}`), "
        "so this bridge cannot safely continue.\n"
        f"Repair or reinstall with the owning runtime: `{repair_command}`"
    )


def _install_scope_mismatch_error_message(
    *,
    runtime: str,
    manifest_install_scope: str,
    config_dir: Path,
    install_scope: str,
    explicit_target: bool,
    cli_cwd: Path,
) -> str:
    """Return repair guidance when the manifest scope disagrees with the bridge scope."""
    repair_command = _build_repair_command(
        runtime=runtime,
        config_dir=config_dir,
        install_scope=manifest_install_scope,
        explicit_target=explicit_target,
        cli_cwd=cli_cwd,
    )
    return (
        f"GRD runtime bridge scope mismatch for {_runtime_display_name(runtime)} at `{config_dir}`.\n"
        f"Resolved install manifest pins `{manifest_install_scope}`, but this bridge was launched as `{install_scope}`.\n"
        f"Repair or reinstall with the owning scope: `{repair_command}`"
    )


def _malformed_manifest_runtime_error_message(
    *,
    runtime: str,
    config_dir: Path,
    install_scope: str,
    explicit_target: bool,
    cli_cwd: Path,
) -> str:
    """Return repair guidance when the install manifest runtime field is malformed."""
    repair_command = _build_repair_command(
        runtime=runtime,
        config_dir=config_dir,
        install_scope=install_scope,
        explicit_target=explicit_target,
        cli_cwd=cli_cwd,
    )
    return (
        f"GRD runtime bridge rejected malformed install manifest at `{config_dir}`.\n"
        "The manifest `runtime` field must be a recognized non-empty runtime string.\n"
        f"Repair or reinstall with: `{repair_command}`"
    )


def _missing_manifest_runtime_error_message(
    *,
    runtime: str,
    config_dir: Path,
    install_scope: str,
    explicit_target: bool,
    cli_cwd: Path,
) -> str:
    """Return repair guidance when the install manifest omits ``runtime``."""
    repair_command = _build_repair_command(
        runtime=runtime,
        config_dir=config_dir,
        install_scope=install_scope,
        explicit_target=explicit_target,
        cli_cwd=cli_cwd,
    )
    return (
        f"GRD runtime bridge rejected incomplete install manifest at `{config_dir}`.\n"
        "The manifest must declare a non-empty `runtime` field.\n"
        f"Repair or reinstall with: `{repair_command}`"
    )


def _install_scope_status_error_message(
    *,
    runtime: str,
    config_dir: Path,
    install_scope: str,
    explicit_target: bool,
    cli_cwd: Path,
    state: str,
) -> str:
    """Return repair guidance when the manifest install_scope field is missing or malformed."""
    repair_command = _build_repair_command(
        runtime=runtime,
        config_dir=config_dir,
        install_scope=install_scope,
        explicit_target=explicit_target,
        cli_cwd=cli_cwd,
    )
    if state == "missing_install_scope":
        scope_issue = "The manifest must declare a non-empty `install_scope` field."
    else:
        scope_issue = "The manifest `install_scope` field must be exactly `local` or `global`."
    return (
        f"GRD runtime bridge rejected incomplete install manifest at `{config_dir}`.\n"
        f"{scope_issue}\n"
        f"Repair or reinstall with: `{repair_command}`"
    )


def _classify_bridge_failure(
    *,
    runtime: str,
    config_dir: Path,
    install_scope: str,
    explicit_target: bool,
    cli_cwd: Path,
    manifest_status: str,
    manifest_runtime: str | None,
    manifest_scope_status: str,
    manifest_install_scope: str | None,
    missing: tuple[str, ...] | None,
    has_managed_install_markers: bool,
) -> _BridgeFailure | None:
    """Return the first structured bridge failure for the current install state."""

    if manifest_scope_status == "missing_install_scope":
        return _bridge_failure(
            _BridgeFailureKind.MISSING_INSTALL_SCOPE,
            _install_scope_status_error_message(
                runtime=runtime,
                config_dir=config_dir,
                install_scope=install_scope,
                explicit_target=explicit_target,
                cli_cwd=cli_cwd,
                state=manifest_scope_status,
            ),
        )
    if manifest_scope_status == "malformed_install_scope":
        return _bridge_failure(
            _BridgeFailureKind.MALFORMED_INSTALL_SCOPE,
            _install_scope_status_error_message(
                runtime=runtime,
                config_dir=config_dir,
                install_scope=install_scope,
                explicit_target=explicit_target,
                cli_cwd=cli_cwd,
                state=manifest_scope_status,
            ),
        )
    if manifest_status == "missing" and has_managed_install_markers:
        return _bridge_failure(
            _BridgeFailureKind.MISSING_MANIFEST,
            _missing_manifest_error_message(
                runtime=runtime,
                config_dir=config_dir,
                install_scope=install_scope,
                explicit_target=explicit_target,
                cli_cwd=cli_cwd,
            ),
        )
    if manifest_status == "corrupt":
        return _bridge_failure(
            _BridgeFailureKind.CORRUPT_MANIFEST,
            _untrusted_manifest_error_message(
                runtime=runtime,
                config_dir=config_dir,
                install_scope=install_scope,
                explicit_target=explicit_target,
                cli_cwd=cli_cwd,
            ),
        )
    if manifest_status == "invalid":
        return _bridge_failure(
            _BridgeFailureKind.INVALID_MANIFEST,
            _untrusted_manifest_error_message(
                runtime=runtime,
                config_dir=config_dir,
                install_scope=install_scope,
                explicit_target=explicit_target,
                cli_cwd=cli_cwd,
            ),
        )
    if manifest_status == "missing_runtime":
        return _bridge_failure(
            _BridgeFailureKind.MISSING_RUNTIME,
            _missing_manifest_runtime_error_message(
                runtime=runtime,
                config_dir=config_dir,
                install_scope=install_scope,
                explicit_target=explicit_target,
                cli_cwd=cli_cwd,
            ),
        )
    if manifest_status == "malformed_runtime":
        return _bridge_failure(
            _BridgeFailureKind.MALFORMED_RUNTIME,
            _malformed_manifest_runtime_error_message(
                runtime=runtime,
                config_dir=config_dir,
                install_scope=install_scope,
                explicit_target=explicit_target,
                cli_cwd=cli_cwd,
            ),
        )
    if manifest_runtime is not None and manifest_runtime != runtime:
        return _bridge_failure(
            _BridgeFailureKind.RUNTIME_MISMATCH,
            _runtime_mismatch_error_message(
                runtime=runtime,
                manifest_runtime=manifest_runtime,
                manifest_install_scope=manifest_install_scope,
                config_dir=config_dir,
                install_scope=install_scope,
                explicit_target=explicit_target,
                cli_cwd=cli_cwd,
            ),
        )
    if isinstance(manifest_install_scope, str) and manifest_install_scope in {"local", "global"}:
        if manifest_install_scope != install_scope:
            return _bridge_failure(
                _BridgeFailureKind.INSTALL_SCOPE_MISMATCH,
                _install_scope_mismatch_error_message(
                    runtime=runtime,
                    manifest_install_scope=manifest_install_scope,
                    config_dir=config_dir,
                    install_scope=install_scope,
                    explicit_target=explicit_target,
                    cli_cwd=cli_cwd,
                ),
            )
    if missing:
        return _bridge_failure(
            _BridgeFailureKind.MISSING_INSTALL_ARTIFACTS,
            _install_error_message(
                runtime=runtime,
                config_dir=config_dir,
                install_scope=install_scope,
                explicit_target=explicit_target,
                cli_cwd=cli_cwd,
                missing=missing,
            ),
        )
    return None


def _missing_manifest_error_message(
    *,
    runtime: str,
    config_dir: Path,
    install_scope: str,
    explicit_target: bool,
    cli_cwd: Path,
) -> str:
    """Return repair guidance when a managed install surface has no manifest."""
    repair_command = _build_repair_command(
        runtime=runtime,
        config_dir=config_dir,
        install_scope=install_scope,
        explicit_target=explicit_target,
        cli_cwd=cli_cwd,
    )
    shared_install = get_shared_install_metadata()
    return (
        f"GRD runtime bridge rejected missing install manifest at `{config_dir}`.\n"
        "Managed installs must include `grd-file-manifest.json` so runtime identity stays authoritative.\n"
        f"Repair or reinstall with: `{repair_command}`\n"
    )


def _untrusted_manifest_error_message(
    *,
    runtime: str,
    config_dir: Path,
    install_scope: str,
    explicit_target: bool,
    cli_cwd: Path,
) -> str:
    """Return repair guidance when the install manifest cannot be trusted."""
    repair_command = _build_repair_command(
        runtime=runtime,
        config_dir=config_dir,
        install_scope=install_scope,
        explicit_target=explicit_target,
        cli_cwd=cli_cwd,
    )
    return (
        f"GRD runtime bridge rejected unreadable install manifest at `{config_dir}`.\n"
        "The manifest must be a JSON object with a non-empty `runtime` field.\n"
        f"Repair or reinstall with: `{repair_command}`"
    )


def main(argv: list[str] | None = None) -> int:
    """Validate the install contract, then dispatch into ``grd.cli``."""
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    try:
        options, grd_args = _parse_args(raw_argv)
    except _BridgeArgumentError as exc:
        return _emit_bridge_failure(
            _bridge_failure(
                _BridgeFailureKind.MALFORMED_INVOCATION,
                _bridge_argument_error_message(str(exc)),
            )
        )
    runtime = _canonical_runtime_name(options.runtime)
    cli_cwd = _resolve_cli_cwd_from_argv(grd_args)
    _maybe_reexec_from_checkout(raw_argv, cli_cwd=cli_cwd)
    try:
        adapter = get_adapter(runtime)
    except KeyError as exc:
        return _emit_bridge_failure(_bridge_failure(_BridgeFailureKind.UNKNOWN_RUNTIME, _format_unknown_runtime_error(exc)))
    config_dir = _resolve_config_dir(
        options.config_dir,
        runtime=runtime,
        install_scope=options.install_scope,
        explicit_target=bool(options.explicit_target),
        cli_cwd=cli_cwd,
    )
    manifest_status, manifest_payload, manifest_runtime = load_install_manifest_runtime_status(config_dir)
    manifest_scope_status, manifest_scope_payload, manifest_install_scope = load_install_manifest_scope_status(config_dir)
    manifest_explicit_target = manifest_payload.get("explicit_target")
    if not isinstance(manifest_explicit_target, bool):
        manifest_explicit_target = None
    repair_explicit_target = (
        manifest_explicit_target if manifest_explicit_target is not None else bool(options.explicit_target)
    )
    if manifest_scope_status == "ok":
        manifest_install_scope = manifest_scope_payload.get("install_scope")
        if not isinstance(manifest_install_scope, str):
            manifest_install_scope = None
    has_managed_install_markers = config_dir_has_managed_install_markers(config_dir)
    failure = _classify_bridge_failure(
        runtime=runtime,
        config_dir=config_dir,
        install_scope=options.install_scope,
        explicit_target=repair_explicit_target,
        cli_cwd=cli_cwd,
        manifest_status=manifest_status,
        manifest_runtime=manifest_runtime,
        manifest_scope_status=manifest_scope_status,
        manifest_install_scope=manifest_install_scope,
        missing=None,
        has_managed_install_markers=has_managed_install_markers,
    )
    if failure is None:
        failure = _classify_bridge_failure(
            runtime=runtime,
            config_dir=config_dir,
            install_scope=options.install_scope,
            explicit_target=repair_explicit_target,
            cli_cwd=cli_cwd,
            manifest_status=manifest_status,
            manifest_runtime=manifest_runtime,
            manifest_scope_status=manifest_scope_status,
            manifest_install_scope=manifest_install_scope,
            missing=adapter.missing_install_artifacts(config_dir),
            has_managed_install_markers=has_managed_install_markers,
        )
    if failure is not None:
        return _emit_bridge_failure(failure)

    os.environ[ENV_GRD_ACTIVE_RUNTIME] = adapter.runtime_name
    os.environ[ENV_GRD_DISABLE_CHECKOUT_REEXEC] = "1"

    from grd.cli import entrypoint

    original_argv = list(sys.argv)
    try:
        sys.argv = ["grd", *grd_args]
        result = entrypoint()
    finally:
        sys.argv = original_argv
        if prior_active_runtime is None:
            os.environ.pop(ENV_GPD_ACTIVE_RUNTIME, None)
        else:
            os.environ[ENV_GPD_ACTIVE_RUNTIME] = prior_active_runtime
        if prior_disable_checkout_reexec is None:
            os.environ.pop(ENV_GPD_DISABLE_CHECKOUT_REEXEC, None)
        else:
            os.environ[ENV_GPD_DISABLE_CHECKOUT_REEXEC] = prior_disable_checkout_reexec

    if result is None:
        return 0
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
