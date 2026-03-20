"""Claude Code runtime adapter."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from grd.adapters.base import RuntimeAdapter
from grd.adapters.install_utils import (
    HOOK_SCRIPTS,
    build_hook_command,
    cleanup_settings_hooks,
    compile_markdown_for_runtime,
    copy_with_path_replacement,
    ensure_update_hook,
    hook_python_interpreter,
    parse_jsonc,
    read_settings,
    remove_stale_agents,
    rewrite_grd_cli_in_shell_fences,
    translate_frontmatter_tool_names,
    verify_installed,
    write_settings,
)

logger = logging.getLogger(__name__)

_TOOL_NAME_MAP: dict[str, str] = {
    "file_read": "Read",
    "file_write": "Write",
    "file_edit": "Edit",
    "shell": "Bash",
    "search_files": "Grep",
    "find_files": "Glob",
    "web_search": "WebSearch",
    "web_fetch": "WebFetch",
    "notebook_edit": "NotebookEdit",
    "agent": "Agent",
    "ask_user": "AskUserQuestion",
    "todo_write": "TodoWrite",
    "task": "Task",
    "slash_command": "SlashCommand",
    "tool_search": "ToolSearch",
}


class ClaudeCodeAdapter(RuntimeAdapter):
    """Adapter for Anthropic Claude Code (CLI)."""

    tool_name_map = _TOOL_NAME_MAP

    @property
    def runtime_name(self) -> str:
        return "claude-code"

    # --- Template method hooks ---

    def _install_commands(self, grd_root: Path, target_dir: Path, path_prefix: str, failures: list[str]) -> int:
        commands_src = grd_root / "commands"
        commands_dest = target_dir / "commands" / "grd"
        (target_dir / "commands").mkdir(parents=True, exist_ok=True)
        bridge_command = self.runtime_cli_bridge_command(target_dir)

        def _translate(content: str, prefix: str, install_scope: str | None = None) -> str:
            translated = super(ClaudeCodeAdapter, self).translate_shared_markdown(
                content,
                prefix,
                install_scope=install_scope,
            )
            return _rewrite_gpd_cli_invocations(translated, bridge_command)

        copy_with_path_replacement(
            commands_src,
            commands_dest,
            path_prefix,
            self.runtime_name,
            self._current_install_scope_flag(),
            markdown_transform=_translate,
        )
        if verify_installed(commands_dest, "commands/grd"):
            logger.info("Installed commands/grd")
        else:
            failures.append("commands/grd")
        return sum(1 for f in commands_dest.rglob("*.md") if f.is_file()) if commands_dest.exists() else 0

    def _install_agents(self, grd_root: Path, target_dir: Path, path_prefix: str, failures: list[str]) -> int:
        agents_src = grd_root / "agents"
        agents_dest = target_dir / "agents"
        bridge_command = self.runtime_cli_bridge_command(target_dir)
        _copy_agents_native(
            agents_src,
            agents_dest,
            path_prefix,
            self.runtime_name,
            self._current_install_scope_flag(),
            translate_tool_name=self.translate_frontmatter_tool_name,
            content_transform=lambda content: _rewrite_gpd_cli_invocations(content, bridge_command),
        )
        if verify_installed(agents_dest, "agents"):
            logger.info("Installed agents")
        else:
            failures.append("agents")
        return sum(1 for f in agents_dest.iterdir() if f.is_file() and f.suffix == ".md") if agents_dest.exists() else 0

    def _install_content(self, grd_root: Path, target_dir: Path, path_prefix: str, failures: list[str]) -> None:
        """Install shared specs content with the shared runtime CLI bridge."""
        bridge_command = self.runtime_cli_bridge_command(target_dir)

        def _translate(content: str, prefix: str, install_scope: str | None = None) -> str:
            translated = super(ClaudeCodeAdapter, self).translate_shared_markdown(
                content,
                prefix,
                install_scope=install_scope,
            )
            return _rewrite_gpd_cli_invocations(translated, bridge_command)

        from grd.adapters.install_utils import install_grd_content

        failures.extend(
            install_grd_content(
                grd_root / "specs",
                target_dir,
                path_prefix,
                self.runtime_name,
                install_scope=self._current_install_scope_flag(),
                markdown_transform=_translate,
            )
        )

    def _configure_runtime(self, target_dir: Path, is_global: bool) -> dict[str, object]:
        settings_path = target_dir / "settings.json"
        settings = read_settings(settings_path)
        statusline_command = build_hook_command(
            target_dir,
            HOOK_SCRIPTS["statusline"],
            is_global=is_global,
            config_dir_name=self.config_dir_name,
            explicit_target=getattr(self, "_install_explicit_target", False),
        )
        update_check_command = build_hook_command(
            target_dir,
            HOOK_SCRIPTS["check_update"],
            is_global=is_global,
            config_dir_name=self.config_dir_name,
            explicit_target=getattr(self, "_install_explicit_target", False),
        )
        ensure_update_hook(
            settings,
            update_check_command,
            target_dir=target_dir,
            config_dir_name=self.config_dir_name,
        )

        # Wire MCP servers into the correct config file.
        # Claude Code reads mcpServers from:
        #   Global: ~/.claude.json
        #   Project: .mcp.json (in project root, parent of .claude/)
        import json as _json

        from grd.mcp.builtin_servers import build_mcp_servers_dict, merge_managed_mcp_servers

        mcp_servers = build_mcp_servers_dict(python_path=hook_python_interpreter())
        mcp_count = 0
        if mcp_servers:
            mcp_config_path = _mcp_config_path(target_dir, is_global=is_global)

            mcp_config: dict = {}
            if mcp_config_path.exists():
                try:
                    mcp_config = parse_jsonc(mcp_config_path.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    mcp_config = {}
            if not isinstance(mcp_config, dict):
                mcp_config = {}

            existing_mcp = mcp_config.get("mcpServers", {})
            mcp_config["mcpServers"] = merge_managed_mcp_servers(existing_mcp, mcp_servers)

            mcp_config_path.write_text(_json.dumps(mcp_config, indent=2) + "\n", encoding="utf-8")
            mcp_count = len(mcp_servers)

        return {
            "settingsPath": str(settings_path),
            "settings": settings,
            "statuslineCommand": statusline_command,
            "mcpServers": mcp_count,
        }

    def uninstall(self, target_dir: Path) -> dict[str, object]:
        """Remove GRD from Claude Code config and clean the matching MCP config."""
        manifest = read_settings(target_dir / "grd-file-manifest.json")
        install_scope = manifest.get("install_scope")
        result = super().uninstall(target_dir)

        if install_scope == "global":
            is_global_target = True
        elif install_scope == "local":
            is_global_target = False
        else:
            try:
                is_global_target = target_dir.expanduser().resolve() == self.global_config_dir.expanduser().resolve()
            except OSError:
                is_global_target = target_dir.expanduser() == self.global_config_dir.expanduser()

        settings_path = target_dir / "settings.json"
        if settings_path.exists():
            settings = read_settings(settings_path)
            if cleanup_settings_hooks(
                settings,
                target_dir=target_dir,
                config_dir_name=self.config_dir_name,
            ):
                write_settings(settings_path, settings)

        if not is_global_target:
            import json as _json

            mcp_config_path = target_dir.parent / ".mcp.json"
            if mcp_config_path.exists():
                try:
                    mcp_config = parse_jsonc(mcp_config_path.read_text(encoding="utf-8"))
                except (ValueError, OSError):
                    mcp_config = None
                if isinstance(mcp_config, dict) and isinstance(mcp_config.get("mcpServers"), dict):
                    from grd.mcp.builtin_servers import GRD_MCP_SERVER_KEYS

                    removed_keys = [key for key in list(mcp_config["mcpServers"]) if key in GRD_MCP_SERVER_KEYS]
                    if removed_keys:
                        for key in removed_keys:
                            del mcp_config["mcpServers"][key]
                        if not mcp_config["mcpServers"]:
                            del mcp_config["mcpServers"]
                        mcp_config_path.write_text(_json.dumps(mcp_config, indent=2) + "\n", encoding="utf-8")
                        result["removed"].append(f"MCP servers from {mcp_config_path.name}")
            return result

        mcp_config_path = _mcp_config_path(target_dir, is_global=True)
        if not mcp_config_path.exists():
            return result

        import json as _json

        from grd.mcp.builtin_servers import GRD_MCP_SERVER_KEYS

        mcp_config = read_settings(mcp_config_path)
        mcp_servers = mcp_config.get("mcpServers")
        if not isinstance(mcp_servers, dict):
            return result

        removed_keys = [key for key in list(mcp_servers) if key in GRD_MCP_SERVER_KEYS]
        if not removed_keys:
            return result

        for key in removed_keys:
            del mcp_servers[key]
        if not mcp_servers:
            del mcp_config["mcpServers"]

        mcp_config_path.write_text(_json.dumps(mcp_config, indent=2) + "\n", encoding="utf-8")
        result["removed"].append("MCP servers from .claude.json")
        return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _copy_agents_native(
    agents_src: Path,
    agents_dest: Path,
    path_prefix: str,
    runtime: str,
    install_scope: str | None = None,
    translate_tool_name: Callable[[str], str | None] | None = None,
    content_transform: Callable[[str], str] | None = None,
) -> None:
    """Copy agent .md files with placeholder replacement and tool-name translation.

    Claude Code keeps native @ includes — no expansion needed.
    Tool-name translation ensures installed agents use runtime-native names
    (e.g. ``Read`` instead of ``file_read``), which affects how Claude Code
    resolves subagent tool permissions.
    """
    if not agents_src.is_dir():
        return

    agents_dest.mkdir(parents=True, exist_ok=True)

    new_agent_names: set[str] = set()
    for agent_md in sorted(agents_src.glob("*.md")):
        content = compile_markdown_for_runtime(
            agent_md.read_text(encoding="utf-8"),
            runtime=runtime,
            path_prefix=path_prefix,
            install_scope=install_scope,
            protect_agent_prompt_body=True,
        )
        if translate_tool_name is not None:
            content = translate_frontmatter_tool_names(content, translate_tool_name)
        if content_transform is not None:
            content = content_transform(content)
        (agents_dest / agent_md.name).write_text(content, encoding="utf-8")
        new_agent_names.add(agent_md.name)

    remove_stale_agents(agents_dest, new_agent_names)


def _rewrite_gpd_cli_invocations(content: str, command: str) -> str:
    """Rewrite shell-command ``grd`` invocations to the shared CLI bridge."""
    return rewrite_grd_cli_in_shell_fences(content, command)


def _mcp_config_path(target_dir: Path, *, is_global: bool) -> Path:
    """Return the Claude MCP config path associated with *target_dir*.

    The adapter should keep config mutation scoped to the install target instead
    of always reaching out to the caller's real home directory.
    """
    return target_dir.parent / (".claude.json" if is_global else ".mcp.json")


__all__ = ["ClaudeCodeAdapter"]
