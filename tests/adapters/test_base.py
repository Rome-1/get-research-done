"""Tests for the base RuntimeAdapter ABC and shared behavior."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from grd.adapters import get_adapter
from grd.adapters.runtime_catalog import list_runtime_names

RUNTIME_NAMES = list_runtime_names()
_SHARED_INSTALL = get_shared_install_metadata()
INSTALL_ROOT_DIR_NAME = _SHARED_INSTALL.install_root_dir_name
MANIFEST_NAME = _SHARED_INSTALL.manifest_name
PATCHES_DIR_NAME = _SHARED_INSTALL.patches_dir_name


def _write_owned_manifest(target: Path, *, runtime: str = "claude-code") -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "grd-file-manifest.json").write_text(
        json.dumps({"runtime": runtime, "install_scope": "local"}),
        encoding="utf-8",
    )


class TestResolveTargetDir:
    """Test resolve_target_dir for all adapters."""

    @pytest.mark.parametrize("runtime", RUNTIME_NAMES)
    def test_local_uses_cwd(self, runtime: str, tmp_path: Path) -> None:
        adapter = get_adapter(runtime)
        result = adapter.resolve_target_dir(is_global=False, cwd=tmp_path)
        assert result == tmp_path / adapter.config_dir_name

    @pytest.mark.parametrize("runtime", RUNTIME_NAMES)
    def test_global_uses_global_config(self, runtime: str) -> None:
        adapter = get_adapter(runtime)
        result = adapter.resolve_target_dir(is_global=True)
        assert result == adapter.global_config_dir


class TestUninstallBase:
    """Test the base uninstall method (used by Claude Code adapter)."""

    def test_removes_commands_grd(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude-code")
        target = tmp_path / ".claude"
        _write_owned_manifest(target)
        (target / "commands" / "grd").mkdir(parents=True)
        (target / "commands" / "grd" / "help.md").write_text("help", encoding="utf-8")

        result = adapter.uninstall(target)
        assert not (target / "commands" / "grd").exists()
        assert "commands/grd/" in result["removed"]

    def test_removes_get_research_done(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude-code")
        target = tmp_path / ".claude"
        _write_owned_manifest(target)
        (target / "get-research-done").mkdir(parents=True)
        (target / "get-research-done" / "file.md").write_text("x", encoding="utf-8")

        result = adapter.uninstall(target)
        assert not (target / "get-research-done").exists()
        assert "get-research-done/" in result["removed"]

    def test_removes_only_grd_agents(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude-code")
        target = tmp_path / ".claude"
        agents = target / "agents"
        agents.mkdir(parents=True)
        (agents / "grd-verifier.md").write_text("v", encoding="utf-8")
        (agents / "grd-executor.md").write_text("e", encoding="utf-8")
        (agents / "custom-agent.md").write_text("c", encoding="utf-8")

        adapter.uninstall(target)

        assert not (agents / "grd-verifier.md").exists()
        assert not (agents / "grd-executor.md").exists()
        assert (agents / "custom-agent.md").exists()

    def test_preserves_unmanaged_hooks_without_manifest(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude-code")
        target = tmp_path / ".claude"
        hooks = target / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "statusline.py").write_text("s", encoding="utf-8")
        (hooks / "check_update.py").write_text("u", encoding="utf-8")
        (hooks / "user-hook.py").write_text("keep", encoding="utf-8")

        adapter.uninstall(target)

        assert (hooks / "statusline.py").exists()
        assert (hooks / "check_update.py").exists()
        assert (hooks / "user-hook.py").exists()

    def test_removes_manifest_tracked_grd_hooks(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude-code")
        target = tmp_path / ".claude"
        hooks = target / "hooks"
        hooks.mkdir(parents=True)
        (hooks / "statusline.py").write_text("s", encoding="utf-8")
        (hooks / "check_update.py").write_text("u", encoding="utf-8")
        (hooks / "user-hook.py").write_text("keep", encoding="utf-8")
        (target / "grd-file-manifest.json").write_text(
            json.dumps(
                {
                    "runtime": "claude-code",
                    "files": {
                        "hooks/statusline.py": "hash-1",
                        "hooks/check_update.py": "hash-2",
                    },
                }
            ),
            encoding="utf-8",
        )

        adapter.uninstall(target)

        assert not (hooks / "statusline.py").exists()
        assert not (hooks / "check_update.py").exists()
        assert (hooks / "user-hook.py").exists()

    def test_removes_owned_manifest(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude-code")
        target = tmp_path / ".claude"
        _write_owned_manifest(target)

        adapter.uninstall(target)
        assert not (target / "grd-file-manifest.json").exists()

    def test_refuses_untrusted_manifest_without_runtime(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude-code")
        target = tmp_path / ".claude"
        target.mkdir(parents=True)
        (target / "grd-file-manifest.json").write_text("{}", encoding="utf-8")

        with pytest.raises(RuntimeError, match="manifest cannot be trusted"):
            adapter.uninstall(target)

        assert (target / "grd-file-manifest.json").exists()

    def test_removes_patches_dir(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude-code")
        target = tmp_path / ".claude"
        patches = target / "grd-local-patches"
        patches.mkdir(parents=True)
        (patches / "backup.md").write_text("b", encoding="utf-8")

        adapter.uninstall(target)
        assert not patches.exists()

    def test_empty_dir_returns_empty_removed(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude-code")
        target = tmp_path / "empty"
        target.mkdir()
        result = adapter.uninstall(target)
        assert result["removed"] == []

    def test_uninstall_cleans_jsonc_settings(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude-code")
        target = tmp_path / ".claude"
        target.mkdir(parents=True)
        (target / "settings.json").write_text(
            "{\n"
            "  // user comment\n"
            '  "statusLine": {"type": "command", "command": "python .claude/hooks/statusline.py"},\n'
            '  "hooks": {\n'
            '    "SessionStart": [\n'
            '      {"hooks": [{"type": "command", "command": "python .claude/hooks/check_update.py"}]}\n'
            "    ]\n"
            "  },\n"
            '  "theme": "solarized",\n'
            "}\n",
            encoding="utf-8",
        )

        adapter.uninstall(target)

        settings = json.loads((target / "settings.json").read_text(encoding="utf-8"))
        assert settings["theme"] == "solarized"
        assert "statusLine" not in settings
        assert settings.get("hooks") in ({}, None)


class TestInstallValidationAndHooks:
    """Targeted regressions for base install validation and bundled hooks."""

    def test_validate_target_runtime_rejects_manifestless_managed_surface(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude-code")
        target = tmp_path / ".claude"
        (target / "agents").mkdir(parents=True)
        (target / "hooks").mkdir(parents=True)
        (target / "agents" / "grd-verifier.md").write_text("agent\n", encoding="utf-8")
        (target / "hooks" / "statusline.py").write_text("hook\n", encoding="utf-8")

        with pytest.raises(RuntimeError, match="GRD artifacts but no manifest"):
            adapter.validate_target_runtime(target, action="install into")

    def test_validate_target_runtime_allows_manifestless_agent_only_surface(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude-code")
        target = tmp_path / ".claude"
        agents = target / "agents"
        agents.mkdir(parents=True)
        (agents / "grd-verifier.md").write_text("agent\n", encoding="utf-8")
        (agents / "custom-agent.md").write_text("custom\n", encoding="utf-8")

        adapter.validate_target_runtime(target, action="install into")

    def test_validate_target_runtime_allows_manifestless_agent_surface_with_empty_dirs(self, tmp_path: Path) -> None:
        adapter = get_adapter("claude-code")
        target = tmp_path / ".claude"
        agents = target / "agents"
        agents.mkdir(parents=True)
        (agents / "grd-verifier.md").write_text("agent\n", encoding="utf-8")
        (target / "commands" / "grd").mkdir(parents=True)
        (target / INSTALL_ROOT_DIR_NAME).mkdir(parents=True)

        adapter.validate_target_runtime(target, action="install into")

    def test_copy_hook_scripts_preserves_unmanaged_matching_filename(self, tmp_path: Path) -> None:
        grd_root = Path(__file__).resolve().parents[2] / "src" / "grd"
        target = tmp_path / ".claude"
        hooks = target / "hooks"
        hooks.mkdir(parents=True)
        stale_hook = hooks / "statusline.py"
        stale_hook.write_text("# stale non-grd hook\n", encoding="utf-8")

        failures = copy_hook_scripts(grd_root, target)

        assert failures == []
        assert stale_hook.read_text(encoding="utf-8") == "# stale non-grd hook\n"
        assert (hooks / "check_update.py").exists()

    def test_codex_notify_path_comes_from_descriptor_config_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from grd.adapters import codex as codex_module
        from grd.adapters.codex import _configure_config_toml

        target = tmp_path / ".codex"
        target.mkdir()
        (target / "config.toml").write_text("", encoding="utf-8")

        monkeypatch.setattr(
            codex_module,
            "get_runtime_descriptor",
            lambda runtime: SimpleNamespace(config_dir_name=".codex-next"),
        )

        _configure_config_toml(target, is_global=False)

        content = (target / "config.toml").read_text(encoding="utf-8")
        assert ".codex-next/hooks/notify.py" in content
        assert ".codex/hooks/notify.py" not in content


class TestAdapterConformance:
    """Verify all adapters implement the runtime-facing interface."""

    @pytest.mark.parametrize("runtime", RUNTIME_NAMES)
    def test_has_required_properties(self, runtime: str) -> None:
        adapter = get_adapter(runtime)
        assert isinstance(adapter.runtime_name, str)
        assert isinstance(adapter.display_name, str)
        assert isinstance(adapter.config_dir_name, str)
        assert isinstance(adapter.help_command, str)
        assert isinstance(adapter.global_config_dir, Path)

    @pytest.mark.parametrize("runtime", RUNTIME_NAMES)
    def test_has_required_methods(self, runtime: str) -> None:
        adapter = get_adapter(runtime)
        assert callable(adapter.finalize_install)
        assert callable(adapter.format_command)
        assert callable(adapter.install)
        assert callable(adapter.uninstall)

    @pytest.mark.parametrize(
        ("runtime", "expected"),
        [
            ("claude-code", "/grd:help"),
            ("gemini", "/grd:help"),
            ("codex", "$grd-help"),
            ("opencode", "/grd-help"),
        ],
    )
    def test_help_command_uses_runtime_formatter(self, runtime: str, expected: str) -> None:
        adapter = get_adapter(runtime)
        assert adapter.help_command == expected

    @pytest.mark.parametrize("runtime", RUNTIME_NAMES)
    def test_config_dir_name_starts_with_dot(self, runtime: str) -> None:
        adapter = get_adapter(runtime)
        assert adapter.config_dir_name.startswith(".")

    @pytest.mark.parametrize("runtime", RUNTIME_NAMES)
    def test_runtime_name_matches_registry(self, runtime: str) -> None:
        adapter = get_adapter(runtime)
        assert adapter.runtime_name == runtime
