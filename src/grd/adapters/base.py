"""Base adapter ABC for runtime-specific installation surfaces."""

from __future__ import annotations

import abc
import logging
import os
from collections.abc import Mapping
from pathlib import Path

from grd.adapters.install_utils import (
    AGENTS_DIR_NAME,
    COMMANDS_DIR_NAME,
    FLAT_COMMANDS_DIR_NAME,
    GRD_INSTALL_DIR_NAME,
    HOOK_SCRIPTS,
    HOOKS_DIR_NAME,
    MANIFEST_NAME,
    build_runtime_cli_bridge_command,
    compute_path_prefix,
    convert_tool_references_in_body,
    copy_hook_scripts,
    install_grd_content,
    pre_install_cleanup,
    process_settings_commit_attribution,
    replace_placeholders,
    strip_sub_tags,
    translate_frontmatter_tool_names,
    validate_package_integrity,
    write_manifest,
    write_version_file,
)
from grd.adapters.runtime_catalog import get_runtime_descriptor, resolve_global_config_dir
from grd.adapters.tool_names import (
    build_runtime_alias_map,
    reference_translation_map,
    translate_for_runtime,
)
from grd.registry import AgentDef, load_agents_from_dir

logger = logging.getLogger(__name__)


class RuntimeAdapter(abc.ABC):
    """Abstract base for GRD runtime adapters."""

    tool_name_map: Mapping[str, str] = {}
    auto_discovered_tools: frozenset[str] = frozenset()
    drop_mcp_frontmatter_tools: bool = False
    strip_sub_tags_in_shared_markdown: bool = False

    @property
    @abc.abstractmethod
    def runtime_name(self) -> str:
        """Short identifier for this runtime."""

    @property
    def display_name(self) -> str:
        """Human-readable runtime name."""
        return self.runtime_descriptor.display_name

    @property
    def config_dir_name(self) -> str:
        """Name of the runtime's config directory."""
        return self.runtime_descriptor.config_dir_name

    @property
    def help_command(self) -> str:
        """Runtime-specific help command."""
        return self.format_command("help")

    @property
    def launch_command(self) -> str:
        """System-terminal command for opening this runtime."""
        return self.runtime_descriptor.launch_command

    @property
    def new_project_command(self) -> str:
        """Runtime-specific command for starting a new project."""
        return self.format_command("new-project")

    @property
    def map_research_command(self) -> str:
        """Runtime-specific command for mapping existing work."""
        return self.format_command("map-research")

    @property
    def activation_env_vars(self) -> tuple[str, ...]:
        """Environment variables that signal this runtime is active."""
        return self.runtime_descriptor.activation_env_vars

    @property
    def local_config_dir_name(self) -> str:
        """Workspace-local config directory name for this runtime."""
        return self.config_dir_name

    @property
    def install_flag(self) -> str:
        """Bootstrap installer flag for this runtime."""
        return self.runtime_descriptor.install_flag

    @property
    def selection_flags(self) -> tuple[str, ...]:
        """Public bootstrap flags accepted for selecting this runtime."""
        return self.runtime_descriptor.selection_flags

    @property
    def selection_aliases(self) -> tuple[str, ...]:
        """Interactive/runtime aliases accepted by the bootstrap installer."""
        return self.runtime_descriptor.selection_aliases

    @property
    def command_prefix(self) -> str:
        """Runtime-native command prefix."""
        return self.runtime_descriptor.command_prefix

    @property
    def tool_alias_map(self) -> Mapping[str, str]:
        """Runtime-native tool aliases back to canonical GRD names."""
        return build_runtime_alias_map(self.tool_name_map)

    def translate_tool_name(self, name: str) -> str:
        """Translate a canonical or runtime-native tool name to this runtime."""
        return translate_for_runtime(name, self.tool_name_map) or ""

    def translate_frontmatter_tool_name(self, name: str) -> str | None:
        """Translate a frontmatter tool token for this runtime."""
        return translate_for_runtime(
            name,
            self.tool_name_map,
            auto_discovered_tools=self.auto_discovered_tools,
            drop_mcp_frontmatter_tools=self.drop_mcp_frontmatter_tools,
        )

    def tool_reference_translation_map(self) -> dict[str, str]:
        """Canonical prompt tool references rewritten for this runtime."""
        return reference_translation_map(
            self.tool_name_map,
            auto_discovered_tools=self.auto_discovered_tools,
            drop_mcp_frontmatter_tools=self.drop_mcp_frontmatter_tools,
        )

    def translate_shared_command_references(self, content: str) -> str:
        """Rewrite shared command references for this runtime."""
        return content

    def translate_shared_markdown(
        self,
        content: str,
        path_prefix: str,
        *,
        install_scope: str | None = None,
    ) -> str:
        """Translate installed shared markdown from canonical form to this runtime."""
        content = replace_placeholders(content, path_prefix, self.runtime_name, install_scope)
        content = translate_frontmatter_tool_names(content, self.translate_frontmatter_tool_name)
        content = self.translate_shared_command_references(content)
        if self.strip_sub_tags_in_shared_markdown:
            content = strip_sub_tags(content)
        return convert_tool_references_in_body(content, self.tool_reference_translation_map())

    def get_commit_attribution(self, *, explicit_config_dir: str | None = None) -> str | None:
        """Return commit attribution override for this runtime."""
        settings_path = self.resolve_global_config_dir() / "settings.json"
        if explicit_config_dir:
            settings_path = Path(explicit_config_dir).expanduser() / "settings.json"
        return process_settings_commit_attribution(settings_path)

    @property
    def runtime_descriptor(self):
        """Adapter-owned metadata descriptor for this runtime."""
        return get_runtime_descriptor(self.runtime_name)

    @property
    def global_config_dir(self) -> Path:
        """Global config directory for this runtime.

        Defaults are resolved from the runtime descriptor. Most runtimes use a
        home-relative dot-directory, while descriptors with env-var or XDG
        precedence are resolved via ``resolve_global_config_dir()``.
        """
        return self.resolve_global_config_dir()

    def resolve_global_config_dir(self, *, home: Path | None = None) -> Path:
        """Resolve the runtime's global config dir."""
        return resolve_global_config_dir(self.runtime_descriptor, home=home)

    def resolve_local_config_dir(self, cwd: Path | None = None) -> Path:
        """Resolve the runtime's local config dir."""
        return Path(cwd or os.getcwd()) / self.local_config_dir_name

    def format_command(self, action: str) -> str:
        """Format a runtime-native GRD command."""
        return f"{self.command_prefix}{action}"

    @property
    def update_command(self) -> str:
        """Public bootstrap command that updates this runtime install."""
        base = "npx -y get-research-done"
        return f"{base} {self.install_flag}".strip()

    def install_completeness_relpaths(self) -> tuple[str, ...]:
        """Return relative artifacts required for a usable runtime install.

        Runtime detection, install-metadata lookups, and the runtime CLI bridge
        all use the same shared contract. Adapters may extend this when their
        installed surface requires additional runtime-owned files.
        """
        return (MANIFEST_NAME, GRD_INSTALL_DIR_NAME)

    def missing_install_artifacts(self, target_dir: Path) -> tuple[str, ...]:
        """Return missing install artifacts relative to *target_dir*."""
        missing: list[str] = []
        for relpath in self.install_completeness_relpaths():
            if not (target_dir / relpath).exists():
                missing.append(relpath)
        return tuple(missing)

    def has_complete_install(self, target_dir: Path) -> bool:
        """Return whether *target_dir* satisfies the shared install contract."""
        return not self.missing_install_artifacts(target_dir)

    def runtime_cli_bridge_command(self, target_dir: Path) -> str:
        """Return the shared runtime CLI bridge command for installed shell calls."""
        return build_runtime_cli_bridge_command(
            self.runtime_name,
            target_dir=target_dir,
            config_dir_name=self.config_dir_name,
            is_global=getattr(self, "_install_is_global", False),
            explicit_target=getattr(self, "_install_explicit_target", False),
        )

    # ---------------------------------------------------------------------------
    # Template method: install pipeline
    # ---------------------------------------------------------------------------

    def install(
        self,
        grd_root: Path,
        target_dir: Path,
        *,
        is_global: bool = False,
        explicit_target: bool = False,
    ) -> dict[str, object]:
        """Install GRD into the target runtime configuration directory.

        Template method — calls hooks in standard order.  Subclasses override
        individual ``_install_*`` hooks for runtime-specific behavior.
        Override ``install()`` itself only when the signature must change.

        Args:
            grd_root: Root of GRD package data (commands/, agents/, specs/, hooks/).
            target_dir: The runtime's config directory to install into.
            is_global: True for global (home-dir) installs, False for local.

        Returns:
            Summary dict with at minimum: runtime, commands, agents.
        """
        from grd.core.observability import grd_span
        from grd.version import __version__, version_for_grd_root

        with grd_span("adapter.install", runtime=self.runtime_name, target=str(target_dir)) as span:
            previous_explicit_target = getattr(self, "_install_explicit_target", False)
            previous_is_global = getattr(self, "_install_is_global", False)
            self._install_explicit_target = explicit_target
            self._install_is_global = is_global
            try:
                self._validate(grd_root)
                path_prefix = self._compute_path_prefix(target_dir, is_global)
                self._pre_cleanup(target_dir)
                install_version = version_for_grd_root(grd_root) or __version__

                failures: list[str] = []
                command_count = self._install_commands(grd_root, target_dir, path_prefix, failures)
                self._install_content(grd_root, target_dir, path_prefix, failures)
                agent_count = self._install_agents(grd_root, target_dir, path_prefix, failures)
                self._install_version(target_dir, install_version, failures)
                self._install_hooks(grd_root, target_dir, failures)

                if failures:
                    span.set_attribute("grd.install_failures", ", ".join(failures))
                    raise RuntimeError(f"Installation incomplete! Failed: {', '.join(failures)}")

                extra = self._configure_runtime(target_dir, is_global)
                self._write_manifest(target_dir, install_version)
                self._verify(target_dir)

                span.set_attribute("grd.commands_count", command_count)
                span.set_attribute("grd.agents_count", agent_count)
                logger.info(
                    "Installed GRD for %s: %d commands, %d agents",
                    self.runtime_name,
                    command_count,
                    agent_count,
                )

                summary: dict[str, object] = {
                    "runtime": self.runtime_name,
                    "target": str(target_dir),
                    "commands": command_count,
                    "agents": agent_count,
                }
                if extra:
                    summary.update(extra)
                return summary
            finally:
                self._install_explicit_target = previous_explicit_target
                self._install_is_global = previous_is_global

    # ---------------------------------------------------------------------------
    # Install hooks — override in subclasses for runtime-specific behavior
    # ---------------------------------------------------------------------------

    def _validate(self, grd_root: Path) -> None:
        """Validate package integrity before install."""
        validate_package_integrity(grd_root)

    def _compute_path_prefix(self, target_dir: Path, is_global: bool) -> str:
        """Compute path prefix for placeholder replacement."""
        return compute_path_prefix(
            target_dir,
            self.config_dir_name,
            is_global=is_global,
            explicit_target=getattr(self, "_install_explicit_target", False),
        )

    def _pre_cleanup(self, target_dir: Path) -> None:
        """Clean up files from previous installations."""
        pre_install_cleanup(target_dir)

    def _install_commands(self, grd_root: Path, target_dir: Path, path_prefix: str, failures: list[str]) -> int:
        """Install commands in runtime-specific format.

        Appends to *failures* on error.  Returns the number of commands installed.
        """
        return 0

    def _install_content(self, grd_root: Path, target_dir: Path, path_prefix: str, failures: list[str]) -> None:
        """Install get-research-done/ content from specs/."""
        failures.extend(
            install_grd_content(
                grd_root / "specs",
                target_dir,
                path_prefix,
                self.runtime_name,
                install_scope=self._current_install_scope_flag(),
                markdown_transform=self.translate_shared_markdown,
            )
        )

    def _install_agents(self, grd_root: Path, target_dir: Path, path_prefix: str, failures: list[str]) -> int:
        """Install agents in runtime-specific format.

        Appends to *failures* on error.  Returns the number of agents installed.
        """
        return 0

    def _install_version(self, target_dir: Path, version: str, failures: list[str]) -> None:
        """Write VERSION file into the runtime install root."""
        grd_dest = target_dir / GRD_INSTALL_DIR_NAME
        failures.extend(write_version_file(grd_dest, version))

    def _install_hooks(self, grd_root: Path, target_dir: Path, failures: list[str]) -> None:
        """Copy hook scripts."""
        failures.extend(copy_hook_scripts(grd_root, target_dir))

    def _current_install_scope_flag(self) -> str:
        """Return the active install scope as a bootstrap-friendly flag."""
        return "--global" if getattr(self, "_install_is_global", False) else "--local"

    def load_runtime_agents(self, grd_root: Path) -> tuple[AgentDef, ...]:
        """Load runtime-projected agent metadata from an install source root."""
        agents = load_agents_from_dir(grd_root / "agents")
        projected = (self.project_agent_metadata(agent) for _, agent in sorted(agents.items()))
        return tuple(projected)

    def project_agent_metadata(self, agent: AgentDef) -> AgentDef:
        """Project canonical agent metadata into runtime-specific install policy."""
        return agent

    def should_install_agent_as_discoverable_surface(self, agent: AgentDef) -> bool:
        """Return whether an agent should be installed into discoverable skill surfaces."""
        return True

    def _configure_runtime(self, target_dir: Path, is_global: bool) -> dict[str, object]:
        """Runtime-specific configuration (settings, permissions, etc.).

        Returns extra data to merge into the install summary dict.
        """
        return {}

    def _write_manifest(self, target_dir: Path, version: str) -> None:
        """Write file manifest for modification detection."""
        write_manifest(
            target_dir,
            version,
            runtime=self.runtime_name,
            install_scope=self._current_install_scope_flag(),
        )

    def _verify(self, target_dir: Path) -> None:  # noqa: B027
        """Post-install verification.  Override for runtime-specific checks."""
        missing = self.missing_install_artifacts(target_dir)
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(f"{self.display_name} install incomplete: missing {joined}")

    def finalize_install(  # noqa: B027
        self,
        install_result: dict[str, object],
        *,
        force_statusline: bool = False,
    ) -> None:
        """Apply any runtime-specific post-install finalization."""

    def _cleanup_runtime_config(self, target_dir: Path) -> list[str]:
        """Remove runtime-managed config entries outside shared GRD files."""
        return []

    def uninstall(self, target_dir: Path) -> dict[str, object]:
        """Remove GRD from the target runtime configuration directory.

        Default implementation removes common GRD directories and files.
        Override for runtime-specific cleanup.
        """
        import shutil

        from grd.core.observability import grd_span

        with grd_span("adapter.uninstall", runtime=self.runtime_name, target=str(target_dir)) as span:
            removed: list[str] = []

            # Remove nested commands/grd/ directory
            grd_commands = target_dir / COMMANDS_DIR_NAME / "grd"
            if grd_commands.is_dir():
                shutil.rmtree(grd_commands)
                removed.append(f"{COMMANDS_DIR_NAME}/grd/")

            # Remove flat command/ directory used by some runtimes.
            flat_commands = target_dir / FLAT_COMMANDS_DIR_NAME
            if flat_commands.is_dir():
                shutil.rmtree(flat_commands)
                removed.append(f"{FLAT_COMMANDS_DIR_NAME}/")

            # Remove the shared GRD install root.
            grd_dir = target_dir / GRD_INSTALL_DIR_NAME
            if grd_dir.is_dir():
                shutil.rmtree(grd_dir)
                removed.append(f"{GRD_INSTALL_DIR_NAME}/")

            # Remove grd-*.md agent files
            agents_dir = target_dir / AGENTS_DIR_NAME
            if agents_dir.is_dir():
                agent_count = 0
                for f in agents_dir.iterdir():
                    if f.name.startswith("grd-") and f.suffix == ".md":
                        f.unlink()
                        agent_count += 1
                if agent_count:
                    removed.append(f"{agent_count} GRD agents")

            # Remove GRD hooks
            hooks_dir = target_dir / HOOKS_DIR_NAME
            if hooks_dir.is_dir():
                hook_count = 0
                for hook_path in hooks_dir.iterdir():
                    if not hook_path.is_file():
                        continue
                    if hook_path.name in HOOK_SCRIPTS.values():
                        hook_path.unlink()
                        hook_count += 1
                if hook_count:
                    removed.append(f"{hook_count} GRD hooks")

            removed.extend(self._cleanup_runtime_config(target_dir))

            # Remove file manifest
            manifest = target_dir / "grd-file-manifest.json"
            if manifest.exists():
                manifest.unlink()
                removed.append("grd-file-manifest.json")

            # Remove local patches directory
            patches_dir = target_dir / "grd-local-patches"
            if patches_dir.is_dir():
                shutil.rmtree(patches_dir)
                removed.append("grd-local-patches/")

            span.set_attribute("grd.removed_count", len(removed))
            logger.info("Uninstalled GRD from %s: removed %d items", self.runtime_name, len(removed))

            return {"runtime": self.runtime_name, "target": str(target_dir), "removed": removed}

    def resolve_target_dir(self, is_global: bool, cwd: Path | None = None) -> Path:
        """Resolve the target directory for install/uninstall.

        Args:
            is_global: If True, use global config dir. If False, use local (cwd-relative).
            cwd: Working directory for local installs. Defaults to os.getcwd().
        """
        if is_global:
            return self.resolve_global_config_dir()
        return self.resolve_local_config_dir(cwd)


__all__ = ["RuntimeAdapter"]
