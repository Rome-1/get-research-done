from __future__ import annotations

import re
from pathlib import Path

from gpd.adapters import get_adapter
from gpd.adapters.runtime_catalog import get_runtime_capabilities, iter_runtime_descriptors

_RUNTIME_DESCRIPTORS = tuple(iter_runtime_descriptors())
RUNTIME_NAMES = tuple(descriptor.runtime_name for descriptor in _RUNTIME_DESCRIPTORS)


def _runtime_with_permissions_surface_or_first(surface: str) -> str:
    for descriptor in _RUNTIME_DESCRIPTORS:
        if get_runtime_capabilities(descriptor.runtime_name).permissions_surface == surface:
            return descriptor.runtime_name
    return RUNTIME_NAMES[0]


PRIMARY_RUNTIME = _runtime_with_permissions_surface_or_first("config-file")
FOREIGN_RUNTIME = next((runtime_name for runtime_name in RUNTIME_NAMES if runtime_name != PRIMARY_RUNTIME), PRIMARY_RUNTIME)


def runtime_descriptor(runtime_name: str):
    return next(descriptor for descriptor in _RUNTIME_DESCRIPTORS if descriptor.runtime_name == runtime_name)


def runtime_config_dir_name(runtime_name: str) -> str:
    return get_adapter(runtime_name).config_dir_name


def runtime_launch_executable(runtime_name: str) -> str:
    launch_command = get_adapter(runtime_name).launch_command
    return launch_command.split()[0] if launch_command.split() else launch_command


def runtime_display_name(runtime_name: str) -> str:
    return get_adapter(runtime_name).display_name


def runtime_install_flag(runtime_name: str) -> str:
    return runtime_descriptor(runtime_name).install_flag


def runtime_help_command(runtime_name: str) -> str:
    return get_adapter(runtime_name).help_command


def runtime_start_command(runtime_name: str) -> str:
    return get_adapter(runtime_name).format_command("start")


def runtime_tour_command(runtime_name: str) -> str:
    return get_adapter(runtime_name).format_command("tour")


def runtime_new_project_command(runtime_name: str) -> str:
    return get_adapter(runtime_name).new_project_command


def runtime_map_research_command(runtime_name: str) -> str:
    return get_adapter(runtime_name).map_research_command


def runtime_resume_work_command(runtime_name: str) -> str:
    return get_adapter(runtime_name).format_command("resume-work")


def runtime_onboarding_doc_filename(runtime_name: str) -> str:
    display_name = runtime_display_name(runtime_name)
    slug = re.sub(r"[^a-z0-9]+", "-", display_name.lower()).strip("-")
    return f"{slug}.md"


def _runtime_primary_config_surface(runtime_name: str) -> str:
    descriptor = runtime_descriptor(runtime_name)
    for surface in (
        descriptor.capabilities.permission_surface_kind,
        descriptor.capabilities.statusline_config_surface,
        descriptor.capabilities.notify_config_surface,
    ):
        if surface != "none" and ":" in surface:
            return surface
    raise LookupError(f"No config-file surface found for runtime {runtime_name!r}")


def runtime_primary_config_filename(runtime_name: str) -> str:
    return _runtime_primary_config_surface(runtime_name).split(":", 1)[0]


def runtime_empty_config_content(runtime_name: str) -> str:
    return "{}" if runtime_primary_config_filename(runtime_name).endswith(".json") else ""


def runtime_suggest_next_command(runtime_name: str) -> str:
    return get_adapter(runtime_name).format_command("suggest-next")


def runtime_pause_work_command(runtime_name: str) -> str:
    return get_adapter(runtime_name).format_command("pause-work")


def runtime_without_telemetry() -> str:
    return next(
        descriptor.runtime_name
        for descriptor in _RUNTIME_DESCRIPTORS
        if descriptor.capabilities.telemetry_completeness == "none"
    )


def runtime_with_manifest_file_prefix(prefix: str) -> str:
    return next(
        descriptor.runtime_name
        for descriptor in _RUNTIME_DESCRIPTORS
        if prefix in descriptor.manifest_file_prefixes
    )


def runtime_with_permissions_surface(surface: str) -> str:
    return next(
        descriptor.runtime_name
        for descriptor in _RUNTIME_DESCRIPTORS
        if get_runtime_capabilities(descriptor.runtime_name).permissions_surface == surface
    )


def runtime_prompt_free_mode_value(runtime_name: str) -> str:
    value = get_runtime_capabilities(runtime_name).prompt_free_mode_value
    if not isinstance(value, str) or not value.strip():
        raise LookupError(f"Runtime {runtime_name!r} does not advertise a prompt-free permissions mode value")
    return value


def runtime_with_multiword_alias(*, exclude: tuple[str, ...] = ()) -> tuple[str, str]:
    excluded = set(exclude)
    for descriptor in _RUNTIME_DESCRIPTORS:
        if descriptor.runtime_name in excluded:
            continue
        aliases = tuple(alias for alias in descriptor.selection_aliases if " " in alias)
        if aliases:
            return descriptor.runtime_name, aliases[0]
    raise LookupError("No runtime with a multiword selection alias was found")


def runtime_target_dir(root: Path, runtime_name: str = PRIMARY_RUNTIME) -> Path:
    return root / runtime_config_dir_name(runtime_name)
