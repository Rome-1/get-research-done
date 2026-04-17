"""Tests for the Codex CLI runtime adapter."""

from __future__ import annotations

import json
import os
import re
import shutil
import tomllib
from pathlib import Path

import pytest

from grd.adapters.codex import (
    CodexAdapter,
    _convert_codex_tool_name,
    _convert_to_codex_skill,
    _normalize_codex_questioning,
    _tracked_codex_generated_skill_dirs,
)
from grd.adapters.install_utils import build_runtime_cli_bridge_command
from grd.registry import load_agents_from_dir


@pytest.fixture()
def adapter() -> CodexAdapter:
    return CodexAdapter()


def expected_codex_bridge(target: Path, *, is_global: bool = False, explicit_target: bool = False) -> str:
    return build_runtime_cli_bridge_command(
        "codex",
        target_dir=target,
        config_dir_name=".codex",
        is_global=is_global,
        explicit_target=explicit_target,
    )


def _make_checkout(tmp_path: Path, version: str) -> Path:
    """Create a minimal GRD source checkout with an explicit version."""
    repo_root = tmp_path / "checkout"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "package.json").write_text(
        json.dumps(
            {
                "name": "get-physics-done",
                "version": version,
                "gpdPythonVersion": version,
            }
        ),
        encoding="utf-8",
    )
    (repo_root / "pyproject.toml").write_text(
        f'[project]\nname = "get-physics-done"\nversion = "{version}"\n',
        encoding="utf-8",
    )

    grd_root = repo_root / "src" / "grd"
    (grd_root / "commands").mkdir(parents=True, exist_ok=True)
    (grd_root / "agents").mkdir(parents=True, exist_ok=True)
    (grd_root / "hooks").mkdir(parents=True, exist_ok=True)
    for subdir in ("references", "templates", "workflows"):
        (grd_root / "specs" / subdir).mkdir(parents=True, exist_ok=True)

    (grd_root / "commands" / "help.md").write_text(
        "---\nname: grd:help\ndescription: Help\n---\nHelp body.\n",
        encoding="utf-8",
    )
    (grd_root / "agents" / "grd-verifier.md").write_text(
        "---\nname: grd-verifier\ndescription: Verify\n---\nVerifier body.\n",
        encoding="utf-8",
    )
    (grd_root / "hooks" / "statusline.py").write_text("print('ok')\n", encoding="utf-8")
    (grd_root / "hooks" / "check_update.py").write_text("print('ok')\n", encoding="utf-8")
    (grd_root / "specs" / "references" / "ref.md").write_text("# references\n", encoding="utf-8")
    (grd_root / "specs" / "templates" / "tpl.md").write_text("# templates\n", encoding="utf-8")
    (grd_root / "specs" / "workflows" / "flow.md").write_text("# workflows\n", encoding="utf-8")
    return grd_root


def _make_managed_home_python(tmp_path: Path) -> Path:
    managed_home = tmp_path / "managed-home"
    python_relpath = Path("Scripts/python.exe") if os.name == "nt" else Path("bin/python")
    managed_python = managed_home / "venv" / python_relpath
    managed_python.parent.mkdir(parents=True, exist_ok=True)
    managed_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    return managed_python


class TestProperties:
    def test_runtime_name(self, adapter: CodexAdapter) -> None:
        assert adapter.runtime_name == "codex"

    def test_display_name(self, adapter: CodexAdapter) -> None:
        assert adapter.display_name == "Codex"

    def test_config_dir_name(self, adapter: CodexAdapter) -> None:
        assert adapter.config_dir_name == ".codex"

    def test_help_command(self, adapter: CodexAdapter) -> None:
        assert adapter.help_command == "$grd-help"


class TestConvertCodexToolName:
    def test_known_mappings(self) -> None:
        assert _convert_codex_tool_name("Bash") == "shell"
        assert _convert_codex_tool_name("Read") == "read_file"
        assert _convert_codex_tool_name("Write") == "write_file"
        assert _convert_codex_tool_name("Edit") == "apply_patch"
        assert _convert_codex_tool_name("Grep") == "grep"

    def test_task_excluded(self) -> None:
        assert _convert_codex_tool_name("Task") is None

    def test_mcp_passthrough(self) -> None:
        assert _convert_codex_tool_name("mcp__physics_server") == "mcp__physics_server"

    def test_unknown_passthrough(self) -> None:
        assert _convert_codex_tool_name("CustomTool") == "CustomTool"


class TestConvertToCodexSkill:
    def test_no_frontmatter_wraps(self) -> None:
        result = _convert_to_codex_skill("Just body text", "grd-help")
        assert result.startswith("---\n")
        assert "name: grd-help" in result
        assert "Just body text" in result

    def test_frontmatter_name_converted(self) -> None:
        content = "---\nname: grd:help\ndescription: Show help\n---\nBody"
        result = _convert_to_codex_skill(content, "grd-help")
        assert "name: grd-help" in result
        assert "grd:help" not in result

    def test_color_stripped(self) -> None:
        content = "---\nname: test\ncolor: cyan\ndescription: D\n---\nBody"
        result = _convert_to_codex_skill(content, "grd-test")
        assert "color:" not in result

    def test_allowed_tools_converted(self) -> None:
        content = "---\nname: test\ndescription: D\nallowed-tools:\n  - Read\n  - Bash\n---\nBody"
        result = _convert_to_codex_skill(content, "grd-test")
        assert "allowed-tools:" in result
        assert "read_file" in result
        assert "shell" in result

    def test_task_excluded_from_tools(self) -> None:
        content = "---\nname: test\ndescription: D\nallowed-tools:\n  - Read\n  - Task\n---\nBody"
        result = _convert_to_codex_skill(content, "grd-test")
        assert "Task" not in result.split("---", 2)[1]

    def test_slash_command_conversion(self) -> None:
        content = "---\nname: test\ndescription: D\n---\nUse /grd:execute-phase to run."
        result = _convert_to_codex_skill(content, "grd-test")
        assert "$grd-execute-phase" in result

    def test_canonical_command_conversion(self) -> None:
        content = "---\nname: test\ndescription: D\n---\nRun grd:reapply-patches after the update."
        result = _convert_to_codex_skill(content, "grd-test")
        assert "$grd-reapply-patches" in result

    def test_path_conversion(self) -> None:
        """Path conversion is handled by replace_placeholders in the install pipeline.
        _convert_to_codex_skill only handles /grd: -> $grd- and frontmatter conversion."""
        content = "---\nname: test\ndescription: D\n---\nSee /grd:execute-phase"
        result = _convert_to_codex_skill(content, "grd-test")
        assert "$grd-execute-phase" in result

    def test_description_preserved(self) -> None:
        content = "---\nname: test\ndescription: My description\n---\nBody"
        result = _convert_to_codex_skill(content, "grd-test")
        assert "description: My description" in result

    def test_description_with_triple_dash_is_preserved(self) -> None:
        content = "---\nname: test\ndescription: before --- after\n---\nBody"
        result = _convert_to_codex_skill(content, "grd-test")
        assert "description: before --- after" in result
        assert result.rstrip().endswith("Body")

    def test_missing_name_added(self) -> None:
        content = "---\ndescription: D\n---\nBody"
        result = _convert_to_codex_skill(content, "grd-test")
        assert "name: grd-test" in result

    def test_missing_description_added(self) -> None:
        content = "---\nname: test\n---\nBody"
        result = _convert_to_codex_skill(content, "grd-test")
        assert "description: GRD skill - grd-test" in result

    def test_duplicate_tools_deduplicated(self) -> None:
        """Tools appearing in both tools: and allowed-tools: are deduplicated."""
        content = (
            "---\n"
            "name: test\n"
            "description: D\n"
            "tools: Read, Bash\n"
            "allowed-tools:\n"
            "  - Read\n"
            "  - Write\n"
            "---\n"
            "Body"
        )
        result = _convert_to_codex_skill(content, "grd-test")
        # Extract allowed-tools entries from the frontmatter
        fm = result.split("---")[1]
        tool_entries = [line.strip()[2:] for line in fm.splitlines() if line.strip().startswith("- ")]
        assert tool_entries == ["read_file", "shell", "write_file"]

    def test_duplicate_tools_in_allowed_tools_only(self) -> None:
        """Duplicate entries within allowed-tools: alone are deduplicated."""
        content = (
            "---\n"
            "name: test\n"
            "description: D\n"
            "allowed-tools:\n"
            "  - Read\n"
            "  - Bash\n"
            "  - Read\n"
            "---\n"
            "Body"
        )
        result = _convert_to_codex_skill(content, "grd-test")
        fm = result.split("---")[1]
        tool_entries = [line.strip()[2:] for line in fm.splitlines() if line.strip().startswith("- ")]
        assert tool_entries == ["read_file", "shell"]

    def test_review_contract_is_prepended_to_skill_body(self) -> None:
        content = compile_review_contract_fixture_for_runtime("codex", command_name="test")

        result = _convert_to_codex_skill(content, "grd-test")

        assert_review_contract_prompt_surface(result)


class TestInstall:
    def test_help_skill_does_not_describe_codex_commands_as_slash_commands(
        self,
        adapter: CodexAdapter,
        tmp_path: Path,
    ) -> None:
        grd_root = Path(__file__).resolve().parents[2] / "src" / "grd"
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, is_global=False, skills_dir=skills)

        content = (skills / "grd-help" / "SKILL.md").read_text(encoding="utf-8")
        assert "slash-command" not in content
        assert "canonical in-runtime command names" in content
        assert "$grd-" in content

    def test_local_install_uses_repo_scoped_skills_dir_by_default(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        shared_skills = tmp_path / "global-skills"
        preserved_skill = shared_skills / "custom-keep"
        preserved_skill.mkdir(parents=True)
        (preserved_skill / "SKILL.md").write_text("keep", encoding="utf-8")
        monkeypatch.setenv("CODEX_SKILLS_DIR", str(shared_skills))

        result = adapter.install(grd_root, target, is_global=False)
        local_skills = tmp_path / ".agents" / "skills"

        assert result["skills_dir"] == str(local_skills)
        assert any(d.name.startswith("grd-") for d in local_skills.iterdir() if d.is_dir())
        assert not any(d.name.startswith("grd-") for d in shared_skills.iterdir() if d.is_dir())
        assert (shared_skills / "custom-keep" / "SKILL.md").exists()

    def test_install_creates_skills(self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, is_global=False, skills_dir=skills)

        grd_skills = [d for d in skills.iterdir() if d.is_dir() and d.name.startswith("grd-")]
        assert len(grd_skills) > 0
        for skill_dir in grd_skills:
            assert (skill_dir / "SKILL.md").exists()

    def test_reinstall_preserves_untracked_user_owned_grd_skills(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, is_global=False, skills_dir=skills)

        preserved_skill = skills / "grd-user-keep"
        preserved_skill.mkdir()
        (preserved_skill / "SKILL.md").write_text("keep", encoding="utf-8")
        (preserved_skill / "notes.txt").write_text("extra", encoding="utf-8")

        adapter.install(grd_root, target, skills_dir=skills)

        assert (preserved_skill / "SKILL.md").read_text(encoding="utf-8") == "keep"
        assert (preserved_skill / "notes.txt").read_text(encoding="utf-8") == "extra"

    def test_reinstall_removes_stale_manifest_tracked_generated_grd_skills(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, skills_dir=skills)

        stale_skill = skills / "grd-stale-command"
        stale_skill.mkdir()
        (stale_skill / "SKILL.md").write_text("stale", encoding="utf-8")

        manifest_path = target / "grd-file-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["codex_generated_skill_dirs"] = sorted({*manifest["codex_generated_skill_dirs"], "grd-stale-command"})
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        adapter.install(grd_root, target, skills_dir=skills)

        assert not stale_skill.exists()
        assert (skills / "grd-help" / "SKILL.md").exists()

    def test_install_failure_preserves_live_skills(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        existing_skill = skills / "grd-help"
        existing_skill.mkdir()
        (existing_skill / "SKILL.md").write_text("old help", encoding="utf-8")
        preserved_skill = skills / "custom-keep"
        preserved_skill.mkdir()
        (preserved_skill / "SKILL.md").write_text("keep", encoding="utf-8")

        def fail_compile(*args, **kwargs):
            raise RuntimeError("boom")

        monkeypatch.setattr("grd.adapters.codex.compile_markdown_for_runtime", fail_compile)

        with pytest.raises(RuntimeError, match="boom"):
            adapter.install(grd_root, target, skills_dir=skills)

        assert (existing_skill / "SKILL.md").read_text(encoding="utf-8") == "old help"
        assert (preserved_skill / "SKILL.md").read_text(encoding="utf-8") == "keep"

    def test_install_failure_after_live_backup_restores_original_skills(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        existing_skill = skills / "grd-help"
        existing_skill.mkdir()
        (existing_skill / "SKILL.md").write_text("old help", encoding="utf-8")
        preserved_skill = skills / "custom-keep"
        preserved_skill.mkdir()
        (preserved_skill / "SKILL.md").write_text("keep", encoding="utf-8")

        original_rename = Path.rename

        def fake_render(*args, **kwargs):
            return None

        def fake_rename(self: Path, target_path: Path):
            if target_path == skills and self.name.endswith(".backup"):
                return original_rename(self, target_path)
            if target_path == skills:
                raise RuntimeError("boom after backup")
            return original_rename(self, target_path)

        monkeypatch.setattr("grd.adapters.codex._render_commands_as_skills", fake_render)
        monkeypatch.setattr(Path, "rename", fake_rename)

        with pytest.raises(RuntimeError, match="boom after backup"):
            adapter.install(grd_root, target, skills_dir=skills)

        assert (existing_skill / "SKILL.md").read_text(encoding="utf-8") == "old help"
        assert (preserved_skill / "SKILL.md").read_text(encoding="utf-8") == "keep"

    def test_install_rewrites_grd_cli_calls_to_runtime_cli_bridge(
        self,
        adapter: CodexAdapter,
        tmp_path: Path,
    ) -> None:
        grd_root = Path(__file__).resolve().parents[2] / "src" / "grd"
        target = tmp_path / ".codex"
        target.mkdir()
        adapter.install(grd_root, target, is_global=False)
        local_skills = tmp_path / ".agents" / "skills"

        expected_bridge = expected_codex_bridge(target, is_global=False)
        skill = (local_skills / "grd-set-profile" / "SKILL.md").read_text(encoding="utf-8")
        workflow = (target / "get-research-done" / "workflows" / "set-profile.md").read_text(encoding="utf-8")
        execute_phase = (target / "get-research-done" / "workflows" / "execute-phase.md").read_text(encoding="utf-8")
        agent = (target / "agents" / "grd-planner.md").read_text(encoding="utf-8")

        assert "Codex shell compatibility:" in skill
        assert f"When shell steps call the GRD CLI, use {expected_bridge}" in skill
        assert "validates the install contract" in skill
        assert "`GRD_ACTIVE_RUNTIME=codex uv run grd ...`" not in skill
        assert expected_bridge + " config ensure-section" in skill
        assert f'INIT=$({expected_bridge} init progress --include state,config)' in skill
        assert 'echo "ERROR: grd initialization failed: $INIT"' in skill
        assert expected_bridge + " config ensure-section" in workflow
        assert f'if ! {expected_bridge} verify plan "$plan"; then' in execute_phase
        assert f'INIT=$({expected_bridge} --raw init plan-phase "${{PHASE}}")' in agent
        assert "```bash\ngrd config ensure-section\n" not in workflow
        assert 'if ! grd verify plan "$plan"; then' not in execute_phase
        assert 'INIT=$(grd init plan-phase "${PHASE}")' not in agent

    def test_install_does_not_expose_agents_as_skills(
        self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, skills_dir=skills)

        installed_skill_names = {d.name for d in skills.iterdir() if d.is_dir() and d.name.startswith("grd-")}
        agents = load_agents_from_dir(grd_root / "agents")
        agent_names = {agent.name for agent in agents.values()}

        assert installed_skill_names.isdisjoint(agent_names)

    def test_install_creates_grd_content(self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        grd_dest = target / "get-research-done"
        assert grd_dest.is_dir()
        for subdir in ("references", "templates", "workflows"):
            assert (grd_dest / subdir).is_dir()

    def test_install_creates_agents(self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        agents_dir = target / "agents"
        assert agents_dir.is_dir()
        agent_files = list(agents_dir.glob("grd-*.md"))
        assert len(agent_files) >= 2

    def test_install_writes_agent_role_config_files(
        self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, skills_dir=skills)

        executor_role = target / "agents" / "grd-executor.toml"
        assert executor_role.exists()
        parsed = tomllib.loads(executor_role.read_text(encoding="utf-8"))
        assert parsed["sandbox_mode"] == "workspace-write"
        assert (target / "agents" / "grd-executor.md").resolve().as_posix() in parsed["developer_instructions"]

    def test_install_preserves_shell_placeholders_for_codex_agents(
        self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path
    ) -> None:
        (grd_root / "agents" / "grd-shell-vars.md").write_text(
            "---\nname: grd-shell-vars\ndescription: shell vars\n---\n"
            "Use ${PHASE_ARG} and $ARGUMENTS in prose.\n"
            'Inspect with `file_read("$artifact_path")`.\n'
            "```bash\n"
            'echo "$phase_dir" "$file"\n'
            "```\n"
            "Math stays $T$.\n",
            encoding="utf-8",
        )
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        checker = (target / "agents" / "grd-shell-vars.md").read_text(encoding="utf-8")
        assert "Use ${PHASE_ARG} and $ARGUMENTS in prose." in checker
        assert "$artifact_path" in checker
        assert 'echo "$phase_dir" "$file"' in checker
        assert "Math stays $T$." in checker

    def test_install_writes_version(self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        assert (target / "get-research-done" / "VERSION").exists()

    def test_install_configures_toml(self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        config_toml = target / "config.toml"
        assert config_toml.exists()
        content = config_toml.read_text(encoding="utf-8")
        escaped_exe = hook_python_interpreter().replace("\\", "\\\\")
        expected_notify = (
            f'notify = ["{escaped_exe}", '
            f'"{(target / "hooks" / "notify.py").as_posix()}"]'
        )
        assert "# GRD update notification" in content
        assert expected_notify in content
        assert "[features]" in content
        assert "multi_agent = true" in content
        assert "[agents.grd-executor]" in content
        assert 'config_file = "agents/grd-executor.toml"' in content

    def test_install_registers_agent_roles_in_config_toml(
        self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, skills_dir=skills)

        parsed = tomllib.loads((target / "config.toml").read_text(encoding="utf-8"))
        assert parsed["agents"]["grd-executor"]["config_file"] == "agents/grd-executor.toml"
        assert parsed["agents"]["grd-verifier"]["config_file"] == "agents/grd-verifier.toml"
        assert parsed["agents"]["grd-executor"]["description"]

    def test_install_writes_codex_mcp_startup_timeout(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, skills_dir=skills)

        parsed = tomllib.loads((target / "config.toml").read_text(encoding="utf-8"))
        assert parsed["mcp_servers"]["grd-state"]["startup_timeout_sec"] == 30

    def test_install_projects_wolfram_mcp_server_and_preserves_overrides(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from grd.mcp.builtin_servers import build_mcp_servers_dict

        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        (target / "config.toml").write_text(
            '[mcp_servers.grd-wolfram]\n'
            'command = "python3"\n'
            'args = ["-m", "legacy.wolfram"]\n'
            'cwd = "/tmp/custom-wolfram"\n'
            '\n'
            '[mcp_servers.grd-wolfram.env]\n'
            'EXTRA_FLAG = "1"\n'
            '\n'
            '[mcp_servers.custom-server]\n'
            'command = "node"\n'
            'args = ["custom.js"]\n',
            encoding="utf-8",
        )
        monkeypatch.setenv(WOLFRAM_MCP_API_KEY_ENV_VAR, "codex-test-key")
        monkeypatch.setenv(WOLFRAM_MCP_ENDPOINT_ENV_VAR, "https://example.invalid/api/mcp")

        result = adapter.install(grd_root, target, skills_dir=skills)

        parsed = tomllib.loads((target / "config.toml").read_text(encoding="utf-8"))
        server = parsed["mcp_servers"][WOLFRAM_MANAGED_SERVER_KEY]
        assert server["command"] == "grd-mcp-wolfram"
        assert server["args"] == []
        assert server["cwd"] == "/tmp/custom-wolfram"
        assert server["env"] == {
            "EXTRA_FLAG": "1",
            WOLFRAM_MCP_ENDPOINT_ENV_VAR: "https://example.invalid/api/mcp",
        }
        assert parsed["mcp_servers"]["custom-server"] == {"command": "node", "args": ["custom.js"]}
        assert "codex-test-key" not in (target / "config.toml").read_text(encoding="utf-8")
        assert result["mcpServers"] == len(build_mcp_servers_dict(python_path=hook_python_interpreter())) + 1

    def test_install_omits_managed_wolfram_when_project_override_disables_it(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        (tmp_path / "GRD").mkdir()
        (tmp_path / "GRD" / "integrations.json").write_text('{"wolfram":{"enabled":false}}', encoding="utf-8")
        monkeypatch.setenv(WOLFRAM_MCP_API_KEY_ENV_VAR, "codex-test-key")

        adapter.install(grd_root, target, is_global=False, skills_dir=skills)

        parsed = tomllib.loads((target / "config.toml").read_text(encoding="utf-8"))
        assert WOLFRAM_MANAGED_SERVER_KEY not in parsed.get("mcp_servers", {})

    def test_install_fails_closed_for_invalid_project_local_wolfram_override(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        (tmp_path / "GRD").mkdir()
        (tmp_path / "GRD" / "integrations.json").write_text(
            '{"wolfram":{"enabled":"yes"}}',
            encoding="utf-8",
        )
        config_toml_path = target / "config.toml"
        config_toml_path.write_text('[model]\nname = "gpt-5"\n', encoding="utf-8")
        before = config_toml_path.read_text(encoding="utf-8")
        monkeypatch.setenv(WOLFRAM_MCP_API_KEY_ENV_VAR, "codex-test-key")

        with pytest.raises(RuntimeError, match="enabled must be a boolean"):
            adapter.install(grd_root, target, is_global=False, skills_dir=skills)

        assert config_toml_path.read_text(encoding="utf-8") == before

    def test_install_translates_tool_references_in_skill_body(self, adapter: CodexAdapter, tmp_path: Path) -> None:
        grd_root = _make_checkout(tmp_path, "9.9.9")
        (grd_root / "commands" / "body-check.md").write_text(
            "---\n"
            "name: grd:body-check\n"
            "description: Check body translation\n"
            "allowed-tools:\n"
            "  - file_read\n"
            "  - search_files\n"
            "  - find_files\n"
            "  - file_edit\n"
            "  - file_write\n"
            "---\n"
            "Use `file_read` to inspect the repo, then `search_files` and `find_files` to locate the target.\n"
            "If needed, call `file_edit` before `file_write` to update the result.\n",
            encoding="utf-8",
        )

        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        body = (skills / "grd-body-check" / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[2]

        assert "file_read" not in body
        assert "search_files" not in body
        assert "find_files" not in body
        assert "file_edit" not in body
        assert "file_write" not in body
        assert "read_file" in body
        assert "grep" in body
        assert "glob" in body
        assert "apply_patch" in body
        assert "write_file" in body

    def test_install_notify_not_inside_existing_section(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        """Notify must be at TOML root level, not inside an existing section."""
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        # Pre-populate config.toml with a section that would swallow the notify
        (target / "config.toml").write_text(
            '[notice.model_migrations]\n"gpt-5.3-codex" = "gpt-5.4"\n',
            encoding="utf-8",
        )

        adapter.install(grd_root, target, skills_dir=skills)

        content = (target / "config.toml").read_text(encoding="utf-8")
        # Verify notify appears BEFORE the section, not inside it
        notify_pos = content.index("notify =")
        section_pos = content.index("[notice.model_migrations]")
        assert notify_pos < section_pos, (
            f"notify (pos {notify_pos}) must appear before [notice.model_migrations] (pos {section_pos}) "
            f"to stay at TOML root level. Full content:\n{content}"
        )

    def test_install_with_explicit_target_uses_absolute_notify_path(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / "custom-codex"
        target.mkdir()
        real_grd_root = Path(__file__).resolve().parents[2] / "src" / "grd"

        adapter.install(real_grd_root, target, is_global=False, explicit_target=True)

        content = (target / "config.toml").read_text(encoding="utf-8")
        assert f'"{(target / "hooks" / "notify.py").as_posix()}"' in content
        assert '".codex/hooks/notify.py"' not in content
        workflow = (target / "get-research-done" / "workflows" / "set-profile.md").read_text(encoding="utf-8")
        assert expected_codex_bridge(target, explicit_target=True) + " config ensure-section" in workflow


class TestRuntimePermissions:
    def test_runtime_permissions_status_marks_yolo_as_relaunch_required(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)
        adapter.sync_runtime_permissions(target, autonomy="yolo")

        status = adapter.runtime_permissions_status(target, autonomy="yolo")

        assert status["config_aligned"] is True
        assert status["requires_relaunch"] is True
        assert "Restart Codex" in str(status["next_step"])

    def test_sync_runtime_permissions_yolo_updates_codex_root_and_role_configs(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        result = adapter.sync_runtime_permissions(target, autonomy="yolo")

        parsed = tomllib.loads((target / "config.toml").read_text(encoding="utf-8"))
        role = tomllib.loads((target / "agents" / "grd-executor.toml").read_text(encoding="utf-8"))
        manifest = json.loads((target / "grd-file-manifest.json").read_text(encoding="utf-8"))

        assert parsed["approval_policy"] == "never"
        assert parsed["sandbox_mode"] == "danger-full-access"
        assert role["approval_policy"] == "never"
        assert role["sandbox_mode"] == "danger-full-access"
        assert manifest["grd_runtime_permissions"]["mode"] == "yolo"
        assert result["sync_applied"] is True
        assert result["requires_relaunch"] is True

    def test_sync_runtime_permissions_restores_previous_codex_settings(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        (target / "config.toml").write_text(
            'approval_policy = "on-request"\n'
            'sandbox_mode = "workspace-write"\n',
            encoding="utf-8",
        )
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        adapter.sync_runtime_permissions(target, autonomy="yolo")
        adapter.sync_runtime_permissions(target, autonomy="balanced")

        parsed = tomllib.loads((target / "config.toml").read_text(encoding="utf-8"))
        role = tomllib.loads((target / "agents" / "grd-executor.toml").read_text(encoding="utf-8"))
        content = (target / "config.toml").read_text(encoding="utf-8")
        manifest = json.loads((target / "grd-file-manifest.json").read_text(encoding="utf-8"))

        assert parsed["approval_policy"] == "on-request"
        assert parsed["sandbox_mode"] == "workspace-write"
        assert "approval_policy" not in role
        assert role["sandbox_mode"] == "workspace-write"
        assert "GRD runtime approval policy" not in content
        assert "GRD runtime sandbox mode" not in content
        assert "grd_runtime_permissions" not in manifest

    def test_sync_runtime_permissions_balanced_cleans_live_role_yolo_state_after_manifest_drift(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)
        adapter.sync_runtime_permissions(target, autonomy="yolo")

        # Simulate drift: manifest runtime-permissions state and root yolo markers are lost,
        # while role files remain yolo-configured.
        manifest_path = target / "grd-file-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.pop("grd_runtime_permissions", None)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        (target / "config.toml").write_text("", encoding="utf-8")

        # Additional drift: one role is manually edited back to default while others stay yolo.
        role_path = target / "agents" / "grd-executor.toml"
        role_content = role_path.read_text(encoding="utf-8")
        role_path.write_text(
            role_content.replace('sandbox_mode = "danger-full-access"', 'sandbox_mode = "workspace-write"').replace(
                'approval_policy = "never"\n',
                "",
            ),
            encoding="utf-8",
        )

        status = adapter.runtime_permissions_status(target, autonomy="balanced")
        assert status["managed_by_gpd"] is True
        assert status["config_aligned"] is False

        result = adapter.sync_runtime_permissions(target, autonomy="balanced")
        assert result["changed"] is True
        assert result["sync_applied"] is True

        role_files = sorted((target / "agents").glob("grd-*.toml"))
        assert role_files
        for role_file in role_files:
            parsed_role = tomllib.loads(role_file.read_text(encoding="utf-8"))
            assert parsed_role["sandbox_mode"] == "workspace-write"
            assert "approval_policy" not in parsed_role

        status_after = adapter.runtime_permissions_status(target, autonomy="balanced")
        assert status_after["managed_by_gpd"] is False
        assert status_after["config_aligned"] is True

    def test_malformed_config_toml_fails_closed_for_status_and_sync(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        config_path = target / "config.toml"
        config_path.write_text('approval_policy = [\n', encoding="utf-8")
        before = config_path.read_text(encoding="utf-8")

        status = adapter.runtime_permissions_status(target, autonomy="yolo")
        result = adapter.sync_runtime_permissions(target, autonomy="yolo")

        assert status["config_valid"] is False
        assert status["configured_mode"] == "malformed"
        assert status["config_aligned"] is False
        assert "malformed" in str(status["message"]).lower()
        assert result["config_valid"] is False
        assert result["changed"] is False
        assert result["sync_applied"] is False
        assert result["requires_relaunch"] is False
        assert "malformed" in str(result["warning"]).lower()
        assert config_path.read_text(encoding="utf-8") == before

    def test_malformed_config_toml_fails_closed_during_install(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        config_path = target / "config.toml"
        config_path.write_text('approval_policy = [\n', encoding="utf-8")
        before = config_path.read_text(encoding="utf-8")

        with pytest.raises(RuntimeError, match="malformed"):
            adapter.install(grd_root, target, skills_dir=skills)

        assert config_path.read_text(encoding="utf-8") == before
        assert not (target / "grd-file-manifest.json").exists()

    @pytest.mark.parametrize("config_line", ('mcp_servers = "oops"\n', 'agents = "oops"\n'))
    def test_wrong_shaped_config_toml_fails_closed_during_install(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        config_line: str,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        config_path = target / "config.toml"
        config_path.write_text(config_line, encoding="utf-8")
        before = config_path.read_text(encoding="utf-8")

        with pytest.raises(RuntimeError, match="malformed"):
            adapter.install(grd_root, target, skills_dir=skills)

        assert config_path.read_text(encoding="utf-8") == before
        assert not (target / "grd-file-manifest.json").exists()

    def test_reinstall_rewrites_stale_managed_notify_interpreter(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        (target / "config.toml").write_text(
            '# GRD update notification\nnotify = ["python3", ".codex/hooks/notify.py"]\n',
            encoding="utf-8",
        )
        shared_skills = tmp_path / "shared-skills"
        managed_python = _make_managed_home_python(tmp_path)
        monkeypatch.setenv("CODEX_SKILLS_DIR", str(shared_skills))
        monkeypatch.delenv("GPD_PYTHON", raising=False)
        monkeypatch.setenv("GPD_HOME", str(tmp_path / "managed-home"))
        monkeypatch.setattr("grd.adapters.install_utils.sys.executable", "/custom/venv/bin/python")
        monkeypatch.setattr("grd.version.checkout_root", lambda start=None: None)

        selected_python = hook_python_interpreter()
        assert selected_python == str(managed_python)
        adapter.install(grd_root, target, is_global=False)

        content = (target / "config.toml").read_text(encoding="utf-8")
        parsed_config = tomllib.loads(content)
        assert parsed_config["notify"] == [selected_python, ".codex/hooks/notify.py"]
        assert 'notify = ["python3", ".codex/hooks/notify.py"]' not in content

    def test_install_uses_grd_python_override_for_notify_and_mcp(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        monkeypatch.setenv("GRD_PYTHON", "/env/override/python")
        monkeypatch.setattr("grd.version.checkout_root", lambda start=None: None)

        adapter.install(grd_root, target, skills_dir=skills)

        parsed = tomllib.loads((target / "config.toml").read_text(encoding="utf-8"))
        assert parsed["notify"] == ["/env/override/python", (target / "hooks" / "notify.py").as_posix()]
        assert parsed["mcp_servers"]["grd-state"]["command"] == "/env/override/python"

    def test_install_writes_manifest(self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        manifest = json.loads((target / "grd-file-manifest.json").read_text(encoding="utf-8"))
        assert manifest["codex_skills_dir"] == str(skills)
        assert "skills_dir" not in manifest
        assert manifest["codex_generated_skill_dirs"]
        assert all(name.startswith("grd-") for name in manifest["codex_generated_skill_dirs"])

    def test_manifest_hashes_external_skill_entries(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        manifest = json.loads((target / "grd-file-manifest.json").read_text(encoding="utf-8"))
        skill_md = skills / "grd-help" / "SKILL.md"

        assert manifest["files"]["skills/grd-help/SKILL.md"] == file_hash(skill_md)

    def test_install_manifest_ignores_foreign_grd_skill_dirs(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        foreign_skill = skills / "grd-user-keep"
        foreign_skill.mkdir()
        (foreign_skill / "SKILL.md").write_text("keep", encoding="utf-8")

        result = adapter.install(grd_root, target, skills_dir=skills)

        manifest = json.loads((target / "grd-file-manifest.json").read_text(encoding="utf-8"))
        assert "skills/grd-user-keep/SKILL.md" not in manifest["files"]
        assert manifest["codex_generated_skill_dirs"]
        assert result["skills"] == len(manifest["codex_generated_skill_dirs"])
        assert (foreign_skill / "SKILL.md").exists()

    def test_install_returns_counts(self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        result = adapter.install(grd_root, target, skills_dir=skills)

        assert result["runtime"] == "codex"
        assert result["skills"] > 0
        assert result["agents"] > 0
        assert result["agentRoles"] > 0

    def test_install_nested_commands_flattened(self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        # commands/sub/deep.md should become grd-sub-deep/ skill
        assert (skills / "grd-sub-deep" / "SKILL.md").exists()

    def test_nested_command_include_expands_in_recursive_codex_install(
        self,
        adapter: CodexAdapter,
        tmp_path: Path,
    ) -> None:
        source_root = Path(__file__).resolve().parents[2] / "src" / "grd"
        grd_root = tmp_path / "grd"
        shutil.copytree(source_root, grd_root)

        nested_command = grd_root / "commands" / "nested" / "include.md"
        nested_command.parent.mkdir(parents=True, exist_ok=True)
        nested_command.write_text(
            """---
name: grd:nested-include
description: Nested command include expansion regression
---

<execution_context>
@{GRD_INSTALL_DIR}/workflows/update.md
</execution_context>
""",
            encoding="utf-8",
        )

        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        content = (skills / "grd-nested-include" / "SKILL.md").read_text(encoding="utf-8")
        assert "<!-- [included: update.md] -->" in content
        assert "Check for a newer GRD release" in content
        assert re.search(r"^\s*@.*?/workflows/update\.md\s*$", content, flags=re.MULTILINE) is None

    def test_update_skill_expands_workflow_include(
        self,
        adapter: CodexAdapter,
        tmp_path: Path,
    ) -> None:
        grd_root = Path(__file__).resolve().parents[2] / "src" / "grd"
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        content = (skills / "grd-update" / "SKILL.md").read_text(encoding="utf-8")
        assert "<!-- [included: update.md] -->" in content
        assert "Check for a newer GRD release" in content
        assert re.search(r"^\s*@.*?/workflows/update\.md\s*$", content, flags=re.MULTILINE) is None
        assert "$grd-reapply-patches" in content
        assert "<codex_questioning>" in content
        assert "> **Platform note:** If `ask_user` is not available" not in content
        assert "Use ask_user:" not in content
        assert "Ask the user once using a single compact prompt block:" in content

    @pytest.mark.parametrize(
        ("content", "expected"),
        [
            (
                "> **Platform note:** if `ask_user` is not available, present these options in plain text and wait for the user's freeform response.\n\n"
                "use ask_user with current values pre-selected:\n\n"
                "```\n"
                "ask_user([\n"
                "  {\"question\": \"How much autonomy should the AI have?\"}\n"
                "])\n"
                "```\n",
                "plain_text_prompt([",
            ),
            (
                "> **Platform note:** if `ask_user` is not available, present these options in plain text and wait for the user's freeform response.\n\n"
                "if overlapping, use ask_user:\n",
                "If overlapping, present the duplicate choices in plain text:",
            ),
            (
                "ask inline (freeform, not ask_user):\n\n"
                "based on what they said, ask follow-up questions that dig into their response. use ask_user with options that probe what they mentioned — interpretations, clarifications, concrete examples.\n\n"
                "when you could write a clear scoping contract, use ask_user:\n",
                "When you could write a clear scoping contract, ask the user inline:",
            ),
        ],
    )
    def test_normalize_codex_questioning_rewrites_lowercase_fallback_variants(
        self,
        content: str,
        expected: str,
    ) -> None:
        normalized = _normalize_codex_questioning(content)

        assert "ask_user" not in normalized.lower()
        assert expected.lower() in normalized.lower()

    def test_new_project_workflow_normalizes_codex_questioning(
        self,
        adapter: CodexAdapter,
        tmp_path: Path,
    ) -> None:
        grd_root = Path(__file__).resolve().parents[2] / "src" / "grd"
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, skills_dir=skills)

        workflow = (target / "get-research-done" / "workflows" / "new-project.md").read_text(encoding="utf-8")
        assert "<codex_questioning>" in workflow
        assert "> **Platform note:** If `ask_user` is not available" not in workflow
        assert "Use ask_user:" not in workflow
        assert "Ask exactly one inline freeform question with no preamble or restatement:" in workflow
        assert "Ask one inline freeform question with no preamble or restatement:" in workflow

    def test_install_agents_inline_grd_agents_dir_in_agent_surfaces_only(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        agents_src = grd_root / "agents"
        (agents_src / "grd-shared.md").write_text(
            "---\nname: grd-shared\ndescription: shared\nsurface: internal\nrole_family: coordination\n---\n"
            "Shared agent body.\n",
            encoding="utf-8",
        )
        (agents_src / "grd-main.md").write_text(
            "---\nname: grd-main\ndescription: main\nsurface: public\nrole_family: worker\n---\n"
            "@{GRD_AGENTS_DIR}/grd-shared.md\n",
            encoding="utf-8",
        )

        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        content = (target / "agents" / "grd-main.md").read_text(encoding="utf-8")
        assert "Shared agent body." in content
        assert "<!-- [included: grd-shared.md] -->" in content
        assert "@ include not resolved:" not in content.lower()
        assert not (skills / "grd-main").exists()

    def test_complete_milestone_skill_expands_bullet_list_includes(
        self,
        adapter: CodexAdapter,
        tmp_path: Path,
    ) -> None:
        grd_root = Path(__file__).resolve().parents[2] / "src" / "grd"
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        content = (skills / "grd-complete-milestone" / "SKILL.md").read_text(encoding="utf-8")
        assert "<!-- [included: complete-milestone.md] -->" in content
        assert "<!-- [included: milestone-archive.md] -->" in content
        assert "Mark a completed research stage" in content
        assert "# Milestone Archive Template" in content
        assert re.search(r"^\s*-\s*@.*?/workflows/complete-milestone\.md.*$", content, flags=re.MULTILINE) is None
        assert re.search(r"^\s*-\s*@.*?/templates/milestone-archive\.md.*$", content, flags=re.MULTILINE) is None


class TestUninstall:
    def test_global_uninstall_uses_manifest_skills_dir_when_env_drifts(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        original_shared_skills = tmp_path / "shared-skills-a"
        monkeypatch.setenv("CODEX_CONFIG_DIR", str(target))
        monkeypatch.setenv("CODEX_SKILLS_DIR", str(original_shared_skills))

        adapter.install(grd_root, target, is_global=True)

        manifest = json.loads((target / "grd-file-manifest.json").read_text(encoding="utf-8"))
        assert manifest["codex_skills_dir"] == str(original_shared_skills)

        drifted_shared_skills = tmp_path / "shared-skills-b"
        preserved_skill = drifted_shared_skills / "grd-foreign"
        preserved_skill.mkdir(parents=True)
        (preserved_skill / "SKILL.md").write_text("keep", encoding="utf-8")
        monkeypatch.setenv("CODEX_SKILLS_DIR", str(drifted_shared_skills))

        adapter.uninstall(target)

        assert not original_shared_skills.exists() or not any(
            entry.is_dir() and entry.name.startswith("grd-")
            for entry in original_shared_skills.iterdir()
        )
        assert (preserved_skill / "SKILL.md").exists()

    def test_local_uninstall_uses_repo_scoped_skills_dir_by_default(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        shared_skills = tmp_path / "global-skills"
        preserved_skill = shared_skills / "custom-keep"
        preserved_skill.mkdir(parents=True)
        (preserved_skill / "SKILL.md").write_text("keep", encoding="utf-8")
        monkeypatch.setenv("CODEX_SKILLS_DIR", str(shared_skills))

        adapter.install(grd_root, target, is_global=False)
        adapter.uninstall(target)
        local_skills = tmp_path / ".agents" / "skills"

        assert not local_skills.exists() or not any(d.name.startswith("grd-") for d in local_skills.iterdir() if d.is_dir())
        assert (shared_skills / "custom-keep" / "SKILL.md").exists()

    def test_uninstall_removes_skills(self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        result = adapter.uninstall(target, skills_dir=skills)

        grd_skills = [d for d in skills.iterdir() if d.is_dir() and d.name.startswith("grd-")] if skills.exists() else []
        assert len(grd_skills) == 0
        assert any("skills" in item for item in result["removed"])

    def test_uninstall_preserves_untracked_grd_skill_dir(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, skills_dir=skills)
        manifest = json.loads((target / "grd-file-manifest.json").read_text(encoding="utf-8"))
        tracked_skill_names = set(manifest["codex_generated_skill_dirs"])
        preserved_skill = skills / "grd-user-keep"
        preserved_skill.mkdir()
        (preserved_skill / "SKILL.md").write_text("keep", encoding="utf-8")

        adapter.uninstall(target, skills_dir=skills)

        assert (preserved_skill / "SKILL.md").exists()
        assert "grd-user-keep" not in tracked_skill_names

    def test_install_completeness_and_uninstall_fallback_to_live_skill_surface_when_manifest_drifts(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, skills_dir=skills)
        manifest_path = target / "grd-file-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        tracked_skill_names = set(manifest["codex_generated_skill_dirs"])
        manifest.pop("codex_generated_skill_dirs", None)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        assert adapter.has_complete_install(target) is True

        adapter.uninstall(target, skills_dir=skills)

        assert all(not (skills / name).exists() for name in tracked_skill_names)

    def test_missing_install_artifacts_does_not_use_packaged_source_skill_fallback(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, skills_dir=skills)
        manifest_path = target / "grd-file-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        tracked_skill_names = set(manifest["codex_generated_skill_dirs"])
        manifest.pop("codex_generated_skill_dirs", None)
        manifest.pop("files", None)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        for name in tracked_skill_names:
            (skills / name / "SKILL.md").write_text("user-customized skill\n", encoding="utf-8")

        monkeypatch.setattr(
            "grd.adapters.codex._planned_installed_codex_skill_dirs",
            lambda target_dir: (),
        )

        assert _tracked_codex_generated_skill_dirs(target, skills_dir=skills) == ()
        assert str(skills) in adapter.missing_install_artifacts(target)
        assert adapter.has_complete_install(target) is False

    def test_missing_codex_skills_dir_metadata_does_not_fall_back_to_generic_manifest_skills_dir(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "custom-skills"
        skills.mkdir()
        env_skills = tmp_path / "ignored-global-skills"
        monkeypatch.setenv("CODEX_SKILLS_DIR", str(env_skills))

        adapter.install(grd_root, target, is_global=False, skills_dir=skills)
        manifest_path = target / "grd-file-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        tracked_skill_names = set(manifest["codex_generated_skill_dirs"])
        manifest.pop("codex_skills_dir", None)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        missing = adapter.missing_install_artifacts(target)
        expected_local_skills = target.parent / ".agents" / "skills"
        assert str(skills) not in missing
        assert str(expected_local_skills) in missing
        assert str(env_skills) not in missing

        adapter.uninstall(target)

        assert all((skills / name).exists() for name in tracked_skill_names)

    def test_uninstall_fails_closed_when_manifest_and_install_metadata_drift_past_live_skill_tracking(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, skills_dir=skills)

        manifest_path = target / "grd-file-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        tracked_skill_names = set(manifest["codex_generated_skill_dirs"])
        manifest.pop("codex_generated_skill_dirs", None)
        manifest.pop("files", None)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        shutil.rmtree(target / "get-physics-done")
        for name in tracked_skill_names:
            (skills / name / "SKILL.md").write_text("user-customized skill\n", encoding="utf-8")

        adapter.uninstall(target, skills_dir=skills)

        assert all((skills / name).exists() for name in tracked_skill_names)

    def test_uninstall_fails_closed_when_generated_skill_ownership_is_ambiguous(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, skills_dir=skills)
        tracked_skill_names = {d.name for d in skills.iterdir() if d.is_dir() and d.name.startswith("grd-")}

        monkeypatch.setattr(
            "grd.adapters.codex._load_manifest_codex_generated_skill_dirs",
            lambda target_dir: ("grd-phantom",),
        )

        adapter.uninstall(target, skills_dir=skills)

        assert tracked_skill_names
        assert all((skills / name).exists() for name in tracked_skill_names)

    def test_uninstall_removes_agents(self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)

        # Add non-GRD agent to make sure it survives
        (target / "agents" / "custom.md").write_text("keep", encoding="utf-8")
        (target / "agents" / "custom.toml").write_text('developer_instructions = "keep"\n', encoding="utf-8")

        adapter.uninstall(target, skills_dir=skills)

        agents_dir = target / "agents"
        assert not agents_dir.exists() or not any(f.name.startswith("grd-") for f in agents_dir.iterdir())
        assert (agents_dir / "custom.md").exists()
        assert (agents_dir / "custom.toml").exists()

    def test_uninstall_cleans_toml(self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.install(grd_root, target, skills_dir=skills)
        adapter.uninstall(target, skills_dir=skills)

        config_toml = target / "config.toml"
        if config_toml.exists():
            content = config_toml.read_text(encoding="utf-8")
            assert "grd-" not in content
            assert "notify.py" not in content
            assert "multi_agent" not in content

    def test_uninstall_removes_wolfram_mcp_server_from_config_toml(
        self,
        adapter: CodexAdapter,
        grd_root: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        (target / "config.toml").write_text(
            '[mcp_servers.grd-wolfram]\n'
            'command = "python3"\n'
            'args = ["-m", "legacy.wolfram"]\n'
            '\n'
            '[mcp_servers.custom-server]\n'
            'command = "node"\n'
            'args = ["custom.js"]\n',
            encoding="utf-8",
        )
        monkeypatch.setenv(WOLFRAM_MCP_API_KEY_ENV_VAR, "codex-test-key")

        adapter.install(grd_root, target, skills_dir=skills)
        adapter.uninstall(target, skills_dir=skills)

        content = (target / "config.toml").read_text(encoding="utf-8")
        parsed = tomllib.loads(content)
        assert WOLFRAM_MANAGED_SERVER_KEY not in parsed["mcp_servers"]
        assert parsed["mcp_servers"]["custom-server"] == {"command": "node", "args": ["custom.js"]}

    def test_uninstall_on_empty_dir(self, adapter: CodexAdapter, tmp_path: Path) -> None:
        target = tmp_path / "empty"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        result = adapter.uninstall(target, skills_dir=skills)
        assert result["removed"] == []

    def test_uninstall_preserves_non_grd_toml_lines(self, adapter: CodexAdapter, tmp_path: Path) -> None:
        """Uninstall must not destroy user TOML content that happens to contain 'grd-'."""
        target = tmp_path / ".codex"
        target.mkdir()
        config_toml = target / "config.toml"
        hook_python = hook_python_interpreter().replace("\\", "\\\\")
        config_toml.write_text(
            'model = "gpt-4"\n'
            '# My notes about grd-style naming\n'
            'custom = "my-grd-tool"\n'
            f'notify = ["{sys.executable or "python3"}", "/path/notify.py"]\n',
            encoding="utf-8",
        )
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.uninstall(target, skills_dir=skills)

        content = config_toml.read_text(encoding="utf-8")
        assert 'model = "gpt-4"' in content
        assert "grd-style naming" in content
        assert 'custom = "my-grd-tool"' in content
        assert f'notify = ["{sys.executable or "python3"}", "/path/notify.py"]' in content

    def test_uninstall_preserves_non_grd_agent_roles(
        self, adapter: CodexAdapter, grd_root: Path, tmp_path: Path
    ) -> None:
        target = tmp_path / ".codex"
        target.mkdir()
        (target / "config.toml").write_text(
            '[agents.reviewer]\n'
            'description = "Code reviewer"\n'
            'config_file = "agents/reviewer.toml"\n',
            encoding="utf-8",
        )
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, skills_dir=skills)
        adapter.uninstall(target, skills_dir=skills)

        parsed = tomllib.loads((target / "config.toml").read_text(encoding="utf-8"))
        assert parsed["agents"]["reviewer"]["config_file"] == "agents/reviewer.toml"
        assert "grd-executor" not in parsed["agents"]
        assert "grd-verifier" not in parsed["agents"]

    def test_uninstall_removes_grd_comment_with_notify(self, adapter: CodexAdapter, tmp_path: Path) -> None:
        """The '# GRD update notification' comment should be cleaned alongside the notify line."""
        target = tmp_path / ".codex"
        target.mkdir()
        config_toml = target / "config.toml"
        hook_python = hook_python_interpreter().replace("\\", "\\\\")
        config_toml.write_text(
            'model = "gpt-4"\n'
            "\n"
            "# GRD update notification\n"
            f'notify = ["{sys.executable or "python3"}", "/path/notify.py"]\n',
            encoding="utf-8",
        )
        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.uninstall(target, skills_dir=skills)

        content = config_toml.read_text(encoding="utf-8")
        assert "GRD update notification" not in content
        assert "notify.py" not in content


class TestNotifyConfiguration:
    def test_wraps_existing_notify_and_restores_it_on_uninstall(
        self,
        adapter: CodexAdapter,
        tmp_path: Path,
    ) -> None:
        from grd.adapters.codex import _configure_config_toml

        target = tmp_path / ".codex"
        target.mkdir()
        (target / "hooks").mkdir()
        config_toml = target / "config.toml"
        config_toml.write_text(
            'model = "gpt-5"\n'
            'notify = ["toolctl", "/path/to/my-tool"]\n',
            encoding="utf-8",
        )

        _configure_config_toml(target, is_global=True)

        content = config_toml.read_text(encoding="utf-8")
        assert '# GRD original notify: ["toolctl", "/path/to/my-tool"]' in content
        escaped_exe = (sys.executable or "python3").replace("\\", "\\\\")
        assert f'notify = ["{escaped_exe}", "-c",' in content
        assert "grd-codex-notify-wrapper-v1" in content
        assert "/path/to/my-tool" in content
        assert "notify.py" in content

        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.uninstall(target, skills_dir=skills)

        cleaned = config_toml.read_text(encoding="utf-8")
        assert 'notify = ["toolctl", "/path/to/my-tool"]' in cleaned
        assert "notify.py" not in cleaned
        assert "GRD original notify" not in cleaned

    def test_wraps_custom_notify_py_and_restores_it_on_uninstall(
        self,
        adapter: CodexAdapter,
        tmp_path: Path,
    ) -> None:
        from grd.adapters.codex import _configure_config_toml

        target = tmp_path / ".codex"
        target.mkdir()
        (target / "hooks").mkdir()
        config_toml = target / "config.toml"
        config_toml.write_text(
            'notify = ["python", "/Users/me/custom/notify.py"]\n',
            encoding="utf-8",
        )

        _configure_config_toml(target, is_global=False)

        content = config_toml.read_text(encoding="utf-8")
        assert '# GRD original notify: ["python", "/Users/me/custom/notify.py"]' in content
        assert 'notify = ["python", "/Users/me/custom/notify.py"]' not in content
        assert "grd-codex-notify-wrapper-v1" in content

        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.uninstall(target, skills_dir=skills)

        cleaned = config_toml.read_text(encoding="utf-8")
        assert 'notify = ["python", "/Users/me/custom/notify.py"]' in cleaned
        assert "grd-codex-notify-wrapper-v1" not in cleaned
        assert "GRD original notify" not in cleaned

    def test_mcp_toml_escapes_windows_paths(self, tmp_path: Path) -> None:
        from grd.adapters.codex import _write_mcp_servers_codex_toml

        target = tmp_path / ".codex"
        target.mkdir()

        count = _write_mcp_servers_codex_toml(
            target,
            {
                "grd-test": {
                    "command": r"C:\Python311\python.exe",
                    "args": [r"C:\Program Files\GRD\server.py"],
                    "env": {"PYTHONPATH": r"C:\Users\tester\venv"},
                }
            },
        )

        content = (target / "config.toml").read_text(encoding="utf-8")
        assert count == 1
        assert r'command = "C:\\Python311\\python.exe"' in content
        assert r'args = ["C:\\Program Files\\GRD\\server.py"]' in content
        assert r'PYTHONPATH = "C:\\Users\\tester\\venv"' in content

    def test_mcp_toml_preserves_user_overrides_and_custom_fields(self, tmp_path: Path) -> None:
        from grd.adapters.codex import _write_mcp_servers_codex_toml

        target = tmp_path / ".codex"
        target.mkdir()
        (target / "config.toml").write_text(
            '[mcp_servers.grd-state]\n'
            'command = "python3"\n'
            'args = ["-m", "old.server"]\n'
            'startup_timeout_sec = 45\n'
            'cwd = "/tmp/custom-grd"\n'
            '\n'
            '[mcp_servers.grd-state.env]\n'
            'LOG_LEVEL = "INFO"\n'
            'EXTRA_FLAG = "1"\n',
            encoding="utf-8",
        )

        count = _write_mcp_servers_codex_toml(
            target,
            {
                "grd-state": {
                    "command": "/custom/venv/bin/python",
                    "args": ["-m", "grd.mcp.servers.state_server"],
                    "env": {"LOG_LEVEL": "WARNING"},
                }
            },
        )

        parsed = tomllib.loads((target / "config.toml").read_text(encoding="utf-8"))
        server = parsed["mcp_servers"]["grd-state"]
        assert count == 1
        assert server["command"] == "/custom/venv/bin/python"
        assert server["args"] == ["-m", "grd.mcp.servers.state_server"]
        assert server["startup_timeout_sec"] == 45
        assert server["cwd"] == "/tmp/custom-grd"
        assert server["env"] == {"LOG_LEVEL": "INFO", "EXTRA_FLAG": "1"}

    def test_wraps_existing_false_multi_agent_and_restores_it_on_uninstall(
        self,
        adapter: CodexAdapter,
        tmp_path: Path,
    ) -> None:
        from grd.adapters.codex import _configure_config_toml

        target = tmp_path / ".codex"
        target.mkdir()
        (target / "hooks").mkdir()
        config_toml = target / "config.toml"
        config_toml.write_text(
            '[features]\n'
            'multi_agent = false\n',
            encoding="utf-8",
        )

        _configure_config_toml(target, is_global=True)

        content = config_toml.read_text(encoding="utf-8")
        assert "# GRD original multi_agent: multi_agent = false" in content
        assert "multi_agent = true" in content

        skills = tmp_path / "skills"
        skills.mkdir()
        adapter.uninstall(target, skills_dir=skills)

        cleaned = config_toml.read_text(encoding="utf-8")
        assert "GRD original multi_agent" not in cleaned
        assert "multi_agent = false" in cleaned
        assert "multi_agent = true" not in cleaned
