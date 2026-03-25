"""Integration tests: install → read back → verify for all 4 runtimes.

Tests that installed content matches source expectations for each adapter.
Exercises both the write path (install) and the read path (loading/parsing
installed content) to catch serialization/deserialization mismatches.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pytest

from grd.adapters import iter_adapters
from grd.adapters.claude_code import ClaudeCodeAdapter
from grd.adapters.codex import CodexAdapter
from grd.adapters.gemini import GeminiAdapter
from grd.adapters.install_utils import (
    convert_tool_references_in_body,
    expand_at_includes,
    translate_frontmatter_tool_names,
)
from grd.adapters.opencode import OpenCodeAdapter
from grd.adapters.tool_names import build_canonical_alias_map
from grd.registry import load_agents_from_dir

REPO_GRD_ROOT = Path(__file__).resolve().parents[2] / "src" / "grd"
RUNTIME_ALIAS_MAP = build_canonical_alias_map(adapter.tool_name_map for adapter in iter_adapters())


def _install_real_repo_for_runtime(tmp_path: Path, runtime: str) -> Path:
    if runtime == "claude-code":
        target = tmp_path / ".claude"
        target.mkdir()
        ClaudeCodeAdapter().install(REPO_GRD_ROOT, target)
        return target

    if runtime == "codex":
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        CodexAdapter().install(REPO_GRD_ROOT, target, skills_dir=skills)
        return target

    if runtime == "gemini":
        target = tmp_path / ".gemini"
        target.mkdir()
        adapter = GeminiAdapter()
        result = adapter.install(REPO_GRD_ROOT, target)
        adapter.finalize_install(result)
        return target

    if runtime == "opencode":
        target = tmp_path / ".opencode"
        target.mkdir()
        OpenCodeAdapter().install(REPO_GRD_ROOT, target)
        return target

    raise AssertionError(f"Unsupported runtime {runtime}")


def _canonicalize_runtime_markdown(content: str, *, runtime: str) -> str:
    content = re.sub(
        r"@(?:\./)?[^\s`>)]*get-research-done/([^\s`>)]+)",
        r"@{GRD_INSTALL_DIR}/\1",
        content,
    )
    content = re.sub(
        r"@(?:\./)?[^\s`>)]*agents/([^\s`>)]+)",
        r"@{GRD_AGENTS_DIR}/\1",
        content,
    )
    content = re.sub(
        (
            r"(?:'[^']+'|\"[^\"]+\"|[^ \n`]+)\s+-m grd\.runtime_cli\s+--runtime\s+[a-z-]+\s+"
            r"--config-dir\s+(?:'[^']+'|\"[^\"]+\"|[^ \n`]+)\s+--install-scope\s+(?:local|global)"
            r"(?:\s+--explicit-target)?"
        ),
        "grd",
        content,
    )
    content = expand_at_includes(
        content,
        REPO_GRD_ROOT / "specs",
        "/normalized/",
        runtime=runtime,
    )
    content = translate_frontmatter_tool_names(content, lambda name: RUNTIME_ALIAS_MAP.get(name, name))
    content = convert_tool_references_in_body(content, RUNTIME_ALIAS_MAP)
    content = content.replace("$grd-", "/grd:")
    content = content.replace("/grd-", "/grd:")
    return content


def _read_compare_experiment_command(tmp_path: Path, target: Path, runtime: str) -> str:
    if runtime == "claude-code":
        return (target / "commands" / "grd" / "compare-experiment.md").read_text(encoding="utf-8")

    if runtime == "codex":
        return (tmp_path / "skills" / "grd-compare-experiment" / "SKILL.md").read_text(encoding="utf-8")

    if runtime == "gemini":
        parsed = tomllib.loads((target / "commands" / "grd" / "compare-experiment.toml").read_text(encoding="utf-8"))
        prompt = parsed.get("prompt")
        assert isinstance(prompt, str)
        return prompt

    if runtime == "opencode":
        return (target / "command" / "grd-compare-experiment.md").read_text(encoding="utf-8")

    raise AssertionError(f"Unsupported runtime {runtime}")


# ---------------------------------------------------------------------------
# Claude Code: install → read back → compare
# ---------------------------------------------------------------------------


class TestClaudeCodeRoundtrip:
    """Install into .claude/, then verify installed files match source semantics."""

    @pytest.fixture()
    def installed(self, grd_root: Path, tmp_path: Path) -> Path:
        target = tmp_path / ".claude"
        target.mkdir()
        ClaudeCodeAdapter().install(grd_root, target)
        return target

    def test_commands_roundtrip(self, installed: Path, grd_root: Path) -> None:
        """Installed commands/grd/ files correspond 1:1 with source commands/."""
        src_mds = sorted(f.name for f in (grd_root / "commands").rglob("*.md"))
        dest_mds = sorted(f.name for f in (installed / "commands" / "grd").rglob("*.md"))
        assert dest_mds == src_mds

    def test_command_placeholders_resolved(self, installed: Path) -> None:
        """All {GRD_INSTALL_DIR} and ~/.claude/ placeholders are replaced."""
        for md in (installed / "commands" / "grd").rglob("*.md"):
            content = md.read_text(encoding="utf-8")
            assert "{GRD_INSTALL_DIR}" not in content

    def test_agents_roundtrip(self, installed: Path, grd_root: Path) -> None:
        """Installed agents match source agent filenames."""
        src_agents = sorted(f.name for f in (grd_root / "agents").glob("*.md"))
        dest_agents = sorted(f.name for f in (installed / "agents").glob("grd-*.md"))
        assert dest_agents == src_agents

    def test_agent_frontmatter_preserved(self, installed: Path) -> None:
        """Claude Code agents keep frontmatter intact (tools, description)."""
        for md in (installed / "agents").glob("grd-*.md"):
            content = md.read_text(encoding="utf-8")
            assert content.startswith("---"), f"{md.name} missing frontmatter"
            # Frontmatter should have description and either tools: or allowed-tools:
            end = content.find("---", 3)
            frontmatter = content[3:end]
            assert "description:" in frontmatter, f"{md.name} missing description"

    def test_grd_content_subdirs(self, installed: Path) -> None:
        """get-research-done/ has all expected subdirectories with files."""
        grd = installed / "get-research-done"
        for subdir in ("references", "templates", "workflows"):
            d = grd / subdir
            assert d.is_dir(), f"Missing {subdir}/"
            files = list(d.rglob("*"))
            assert len(files) > 0, f"{subdir}/ is empty"

    def test_grd_content_placeholders_resolved(self, installed: Path) -> None:
        """get-research-done/ .md files have placeholders replaced."""
        for md in (installed / "get-research-done").rglob("*.md"):
            content = md.read_text(encoding="utf-8")
            assert "{GRD_INSTALL_DIR}" not in content

    def test_shared_content_tool_references_are_translated(self, installed: Path) -> None:
        """Shared markdown content should use Claude-native tool names."""
        workflow = (installed / "get-research-done" / "workflows" / "wor.md").read_text(encoding="utf-8")
        reference = (installed / "get-research-done" / "references" / "ref.md").read_text(encoding="utf-8")

        assert "AskUserQuestion([" in workflow
        assert "ask_user(" not in workflow
        assert "Task(" in workflow
        assert "task(" not in workflow
        assert "WebSearch" in reference
        assert "web_search" not in reference

    def test_hooks_copied(self, installed: Path, grd_root: Path) -> None:
        """Hook scripts are copied faithfully."""
        for hook in (grd_root / "hooks").iterdir():
            if hook.is_file() and not hook.name.startswith("__"):
                dest = installed / "hooks" / hook.name
                assert dest.exists(), f"Missing hook: {hook.name}"
                assert dest.read_bytes() == hook.read_bytes()

    def test_version_file(self, installed: Path) -> None:
        """VERSION file exists and is non-empty."""
        version = installed / "get-research-done" / "VERSION"
        assert version.exists()
        assert len(version.read_text(encoding="utf-8").strip()) > 0

    def test_manifest_tracks_all_files(self, installed: Path) -> None:
        """File manifest lists entries for commands, agents, and content."""
        manifest = json.loads((installed / "grd-file-manifest.json").read_text(encoding="utf-8"))
        files = manifest["files"]
        assert any(k.startswith("commands/grd/") for k in files)
        assert any(k.startswith("agents/") for k in files)
        assert any(k.startswith("get-research-done/") for k in files)
        assert "version" in manifest


# ---------------------------------------------------------------------------
# Gemini: install → read back → compare
# ---------------------------------------------------------------------------


class TestGeminiRoundtrip:
    """Install into .gemini/, verify TOML commands and converted agents."""

    @pytest.fixture()
    def installed(self, grd_root: Path, tmp_path: Path) -> Path:
        target = tmp_path / ".gemini"
        target.mkdir()
        adapter = GeminiAdapter()
        result = adapter.install(grd_root, target)
        adapter.finalize_install(result)
        return target

    def test_commands_are_toml(self, installed: Path) -> None:
        """Gemini commands are .toml files (not .md)."""
        toml_files = list((installed / "commands" / "grd").rglob("*.toml"))
        assert len(toml_files) > 0
        md_files = list((installed / "commands" / "grd").rglob("*.md"))
        assert len(md_files) == 0, "Should not have .md files in Gemini commands"

    def test_toml_has_prompt_field(self, installed: Path) -> None:
        """Each TOML command has a prompt field."""
        for toml_file in (installed / "commands" / "grd").rglob("*.toml"):
            content = toml_file.read_text(encoding="utf-8")
            assert "prompt" in content, f"{toml_file.name} missing prompt field"

    def test_toml_preserves_non_runtime_metadata_as_comments(self, grd_root: Path, tmp_path: Path) -> None:
        """Gemini TOML commands keep canonical non-runtime metadata as comments."""
        (grd_root / "commands" / "progress.md").write_text(
            "---\n"
            "name: grd:progress\n"
            "description: Check research progress\n"
            'argument-hint: "[--brief] [--full] [--reconcile]"\n'
            "context_mode: project-required\n"
            "requires:\n"
            '  files: [".grd/ROADMAP.md"]\n'
            "allowed-tools:\n"
            "  - file_read\n"
            "  - shell\n"
            "---\n"
            "Progress body.\n",
            encoding="utf-8",
        )
        target = tmp_path / ".gemini"
        target.mkdir()
        adapter = GeminiAdapter()
        result = adapter.install(grd_root, target)
        adapter.finalize_install(result)

        content = (target / "commands" / "grd" / "progress.toml").read_text(encoding="utf-8")
        parsed = tomllib.loads(content)

        assert "# Source frontmatter preserved for parity:" in content
        assert "# name: grd:progress" in content
        assert '# argument-hint: "[--brief] [--full] [--reconcile]"' in content
        assert "# requires:" in content
        assert '#   files: [".grd/ROADMAP.md"]' in content
        assert "# allowed-tools:" not in content
        assert parsed["context_mode"] == "project-required"

    def test_toml_command_count_matches_source(self, installed: Path, grd_root: Path) -> None:
        """Number of TOML commands matches source .md count."""
        src_count = sum(1 for _ in (grd_root / "commands").rglob("*.md"))
        dest_count = sum(1 for _ in (installed / "commands" / "grd").rglob("*.toml"))
        assert dest_count == src_count

    def test_agents_use_tools_array(self, installed: Path) -> None:
        """Gemini agents convert allowed-tools to tools: YAML array."""
        for md in (installed / "agents").glob("grd-*.md"):
            content = md.read_text(encoding="utf-8")
            # Should not have allowed-tools (Claude format)
            assert "allowed-tools:" not in content, f"{md.name} still has allowed-tools"
            # Should not have color field (causes Gemini validation error)
            end = content.find("---", 3)
            if end > 0:
                fm = content[3:end]
                assert "color:" not in fm, f"{md.name} still has color field"

    def test_agents_tool_names_converted(self, installed: Path) -> None:
        """Gemini agents use Gemini tool names (read_file, not Read)."""
        verifier = installed / "agents" / "grd-verifier.md"
        if not verifier.exists():
            pytest.skip("grd-verifier.md not found in installed agents")
        agent_content = verifier.read_text(encoding="utf-8")
        if "tools:" not in agent_content:
            pytest.skip("grd-verifier.md has no tools: field")
        end = agent_content.find("---", 3)
        assert end > 0, "grd-verifier.md has malformed frontmatter"
        fm = agent_content[3:end]
        tools_idx = fm.find("tools:")
        assert tools_idx >= 0, "tools: not found in frontmatter"
        tools_section = fm[tools_idx:]
        assert "read_file" in tools_section or "Read" not in tools_section

    def test_grd_content_installed(self, installed: Path) -> None:
        """get-research-done/ content is present."""
        grd = installed / "get-research-done"
        assert grd.is_dir()
        for subdir in ("references", "templates", "workflows"):
            assert (grd / subdir).is_dir()

    def test_shared_content_tool_references_are_translated(self, installed: Path) -> None:
        """Shared markdown content should use Gemini runtime tool names."""
        workflow = (installed / "get-research-done" / "workflows" / "wor.md").read_text(encoding="utf-8")
        reference = (installed / "get-research-done" / "references" / "ref.md").read_text(encoding="utf-8")

        assert "ask_user([" in workflow
        assert "AskUserQuestion" not in workflow
        assert "task(" in workflow
        assert "Task(" not in workflow
        assert "google_web_search" in reference
        assert "WebSearch" not in reference

    def test_settings_json_has_experimental(self, installed: Path) -> None:
        """settings.json enables experimental.enableAgents."""
        settings_path = installed / "settings.json"
        assert settings_path.exists(), "settings.json not written to disk"
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        experimental = settings.get("experimental", {})
        assert experimental.get("enableAgents") is True

    def test_manifest_present(self, installed: Path) -> None:
        """File manifest exists and has version."""
        manifest_path = installed / "grd-file-manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "version" in manifest
        assert "files" in manifest


# ---------------------------------------------------------------------------
# Codex: install → read back → compare
# ---------------------------------------------------------------------------


class TestCodexRoundtrip:
    """Install into .codex/ + skills/, verify command skills plus agent roles."""

    @pytest.fixture()
    def installed(self, grd_root: Path, tmp_path: Path) -> tuple[Path, Path]:
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        CodexAdapter().install(grd_root, target, skills_dir=skills)
        return target, skills

    def test_commands_become_skill_dirs(self, installed: tuple[Path, Path]) -> None:
        """Each command becomes a grd-<name>/SKILL.md directory."""
        _, skills = installed
        skill_dirs = [d for d in skills.iterdir() if d.is_dir() and d.name.startswith("grd-")]
        assert len(skill_dirs) > 0
        for skill_dir in skill_dirs:
            skill_md = skill_dir / "SKILL.md"
            assert skill_md.exists(), f"{skill_dir.name}/ missing SKILL.md"

    def test_skill_md_has_frontmatter(self, installed: tuple[Path, Path]) -> None:
        """SKILL.md files have YAML frontmatter with name and description."""
        _, skills = installed
        for skill_dir in skills.iterdir():
            if not skill_dir.is_dir() or not skill_dir.name.startswith("grd-"):
                continue
            skill_md = skill_dir / "SKILL.md"
            content = skill_md.read_text(encoding="utf-8")
            assert content.startswith("---"), f"{skill_dir.name}/SKILL.md missing frontmatter"
            end = content.find("---", 3)
            fm = content[3:end]
            assert "name:" in fm, f"{skill_dir.name} missing name field"
            assert "description:" in fm, f"{skill_dir.name} missing description field"

    def test_skill_names_are_hyphen_case(self, installed: tuple[Path, Path]) -> None:
        """Codex skill names must be hyphen-case (a-z0-9-)."""
        _, skills = installed
        import re

        for skill_dir in skills.iterdir():
            if skill_dir.is_dir() and skill_dir.name.startswith("grd-"):
                assert re.match(r"^[a-z0-9-]+$", skill_dir.name), f"Skill name not hyphen-case: {skill_dir.name}"

    def test_command_count_matches_source(self, installed: tuple[Path, Path], grd_root: Path) -> None:
        """Number of skills matches source command count."""
        _, skills = installed
        src_count = sum(1 for _ in (grd_root / "commands").rglob("*.md"))
        skill_count = sum(1 for d in skills.iterdir() if d.is_dir() and d.name.startswith("grd-"))
        assert skill_count == src_count

    def test_agents_not_installed_as_skills(self, installed: tuple[Path, Path], grd_root: Path) -> None:
        """Codex agents are registered as roles, not duplicated as discoverable skills."""
        _, skills = installed
        agents = load_agents_from_dir(grd_root / "agents")
        for agent_name in sorted(agents):
            assert not (skills / agent_name).exists(), f"Agent should not be a Codex skill: {agent_name}"

    def test_agents_installed_as_md_files(self, installed: tuple[Path, Path], grd_root: Path) -> None:
        """Agents are also installed as .md files under .codex/agents/."""
        target, _ = installed
        agents_dir = target / "agents"
        assert agents_dir.is_dir()
        src_agents = sorted(f.name for f in (grd_root / "agents").glob("*.md"))
        dest_agents = sorted(f.name for f in agents_dir.glob("*.md"))
        assert dest_agents == src_agents

    def test_agent_role_configs_installed(self, installed: tuple[Path, Path], grd_root: Path) -> None:
        """Each installed Codex agent also gets a role config TOML."""
        target, _ = installed
        agents_dir = target / "agents"
        src_agent_names = sorted(f.stem for f in (grd_root / "agents").glob("*.md"))
        dest_role_names = sorted(f.stem for f in agents_dir.glob("grd-*.toml"))
        assert dest_role_names == src_agent_names

    def test_grd_content_installed(self, installed: tuple[Path, Path]) -> None:
        """get-research-done/ has expected content."""
        target, _ = installed
        grd = target / "get-research-done"
        assert grd.is_dir()
        for subdir in ("references", "templates", "workflows"):
            assert (grd / subdir).is_dir()

    def test_shared_content_tool_references_are_translated(self, installed: tuple[Path, Path]) -> None:
        """Shared markdown content should use Codex runtime tool names."""
        target, _ = installed
        workflow = (target / "get-research-done" / "workflows" / "wor.md").read_text(encoding="utf-8")
        reference = (target / "get-research-done" / "references" / "ref.md").read_text(encoding="utf-8")

        assert "<codex_questioning>" in workflow
        assert "ask_user([" in workflow
        assert "AskUserQuestion" not in workflow
        assert "task(" in workflow
        assert "Task(" not in workflow
        assert "web_search" in reference
        assert "WebSearch" not in reference

    def test_slash_commands_converted(self, installed: tuple[Path, Path]) -> None:
        """Content replaces /grd: with $grd- for Codex invocation syntax."""
        target, _ = installed
        for md in (target / "get-research-done").rglob("*.md"):
            content = md.read_text(encoding="utf-8")
            assert "/grd:" not in content, f"{md.name} still has /grd:"

    def test_config_toml_has_notify(self, installed: tuple[Path, Path]) -> None:
        """config.toml has a notify hook entry."""
        target, _ = installed
        toml_path = target / "config.toml"
        assert toml_path.exists()
        content = toml_path.read_text(encoding="utf-8")
        assert "notify" in content
        assert "multi_agent = true" in content
        assert "[agents.grd-executor]" in content

    def test_manifest_tracks_skills(self, installed: tuple[Path, Path]) -> None:
        """File manifest includes skill entries."""
        target, _ = installed
        manifest_path = target / "grd-file-manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "version" in manifest
        assert "files" in manifest


# ---------------------------------------------------------------------------
# OpenCode: install → read back → compare
# ---------------------------------------------------------------------------


class TestOpenCodeRoundtrip:
    """Install into .opencode/, verify flattened commands and permissions."""

    @pytest.fixture()
    def installed(self, grd_root: Path, tmp_path: Path) -> Path:
        target = tmp_path / ".opencode"
        target.mkdir()
        OpenCodeAdapter().install(grd_root, target)
        return target

    def test_commands_are_flattened(self, installed: Path) -> None:
        """OpenCode commands are flat: command/grd-help.md (not commands/grd/help.md)."""
        command_dir = installed / "command"
        assert command_dir.is_dir()
        grd_cmds = [f for f in command_dir.iterdir() if f.name.startswith("grd-") and f.suffix == ".md"]
        assert len(grd_cmds) > 0

    def test_flattened_command_names(self, installed: Path, grd_root: Path) -> None:
        """Flattened command names follow grd-<name>.md convention."""
        command_dir = installed / "command"
        # help.md -> grd-help.md, sub/deep.md -> grd-sub-deep.md
        names = sorted(f.name for f in command_dir.iterdir() if f.name.startswith("grd-"))
        assert "grd-help.md" in names
        assert "grd-sub-deep.md" in names

    def test_frontmatter_converted(self, installed: Path) -> None:
        """OpenCode frontmatter strips name: field, converts colors to hex."""
        for md in (installed / "command").glob("grd-*.md"):
            content = md.read_text(encoding="utf-8")
            if content.startswith("---"):
                end = content.find("---", 3)
                fm = content[3:end]
                # name: should be stripped (OpenCode uses filename)
                assert "name:" not in fm, f"{md.name} still has name: field"

    def test_tool_names_converted(self, installed: Path) -> None:
        """OpenCode commands convert tool references (AskUserQuestion → question)."""
        for md in (installed / "command").glob("grd-*.md"):
            content = md.read_text(encoding="utf-8")
            # AskUserQuestion should be converted to question
            assert "AskUserQuestion" not in content, f"{md.name} still has AskUserQuestion"

    def test_agents_installed(self, installed: Path, grd_root: Path) -> None:
        """Agents are installed with OpenCode frontmatter conversion."""
        agents_dir = installed / "agents"
        assert agents_dir.is_dir()
        src_agents = sorted(f.name for f in (grd_root / "agents").glob("*.md"))
        dest_agents = sorted(f.name for f in agents_dir.glob("*.md"))
        assert dest_agents == src_agents

    def test_grd_content_installed(self, installed: Path) -> None:
        """get-research-done/ content is installed."""
        grd = installed / "get-research-done"
        assert grd.is_dir()
        for subdir in ("references", "templates", "workflows"):
            assert (grd / subdir).is_dir()

    def test_shared_content_tool_references_are_translated(self, installed: Path) -> None:
        """Shared markdown content should use OpenCode runtime tool names."""
        workflow = (installed / "get-research-done" / "workflows" / "wor.md").read_text(encoding="utf-8")
        reference = (installed / "get-research-done" / "references" / "ref.md").read_text(encoding="utf-8")

        assert "question([" in workflow
        assert "AskUserQuestion" not in workflow
        assert "ask_user(" not in workflow
        assert "task(" in workflow
        assert "Task(" not in workflow
        assert "websearch" in reference
        assert "WebSearch" not in reference

    def test_shared_content_command_syntax_is_converted(self, installed: Path) -> None:
        """OpenCode shared content should use flat /grd- command syntax."""
        for md in (installed / "get-research-done").rglob("*.md"):
            content = md.read_text(encoding="utf-8")
            assert "/grd:" not in content, f"{md.name} still has /grd:"

    def test_version_file(self, installed: Path) -> None:
        """VERSION file present in get-research-done/."""
        version = installed / "get-research-done" / "VERSION"
        assert version.exists()
        assert len(version.read_text(encoding="utf-8").strip()) > 0

    def test_permissions_configured(self, installed: Path) -> None:
        """opencode.json has read + external_directory permissions for GRD."""
        config = json.loads((installed / "opencode.json").read_text(encoding="utf-8"))
        perms = config.get("permission", {})
        read_perms = perms.get("read", {})
        ext_perms = perms.get("external_directory", {})
        assert any("get-research-done" in k for k in read_perms)
        assert any("get-research-done" in k for k in ext_perms)

    def test_manifest_present(self, installed: Path) -> None:
        """File manifest tracks flattened commands."""
        manifest_path = installed / "grd-file-manifest.json"
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = manifest.get("files", {})
        assert any(k.startswith("command/grd-") for k in files)


# ---------------------------------------------------------------------------
# Cross-runtime: install/uninstall cycle for each runtime
# ---------------------------------------------------------------------------


class TestInstallUninstallCycle:
    """Install then uninstall for each runtime — verify clean removal."""

    def test_claude_code_cycle(self, grd_root: Path, tmp_path: Path) -> None:
        adapter = ClaudeCodeAdapter()
        target = tmp_path / ".claude"
        target.mkdir()

        adapter.install(grd_root, target)
        assert (target / "commands" / "grd").is_dir()
        assert (target / "get-research-done").is_dir()

        adapter.uninstall(target)
        assert not (target / "commands" / "grd").exists()
        assert not (target / "get-research-done").exists()

    def test_gemini_cycle(self, grd_root: Path, tmp_path: Path) -> None:
        adapter = GeminiAdapter()
        target = tmp_path / ".gemini"
        target.mkdir()

        adapter.install(grd_root, target)
        assert (target / "commands" / "grd").is_dir()
        assert (target / "get-research-done").is_dir()

        adapter.uninstall(target)
        assert not (target / "commands" / "grd").exists()
        assert not (target / "get-research-done").exists()

    def test_codex_cycle(self, grd_root: Path, tmp_path: Path) -> None:
        adapter = CodexAdapter()
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()

        adapter.install(grd_root, target, skills_dir=skills)
        assert any(d.name.startswith("grd-") for d in skills.iterdir() if d.is_dir())
        assert (target / "get-research-done").is_dir()

        adapter.uninstall(target, skills_dir=skills)
        assert not any(d.name.startswith("grd-") for d in skills.iterdir() if d.is_dir())
        assert not (target / "get-research-done").exists()

    def test_opencode_cycle(self, grd_root: Path, tmp_path: Path) -> None:
        adapter = OpenCodeAdapter()
        target = tmp_path / ".opencode"
        target.mkdir()

        adapter.install(grd_root, target)
        assert (target / "command").is_dir()
        assert (target / "get-research-done").is_dir()

        adapter.uninstall(target)
        assert not (target / "get-research-done").exists()
        grd_cmds = (
            [f for f in (target / "command").iterdir() if f.name.startswith("grd-")]
            if (target / "command").exists()
            else []
        )
        assert len(grd_cmds) == 0


# ---------------------------------------------------------------------------
# Serialization roundtrip: source spec → install → re-read matches
# ---------------------------------------------------------------------------


class TestSerializationRoundtrip:
    """Verify that content survives serialization through each adapter."""

    def test_claude_code_body_preserved(self, grd_root: Path, tmp_path: Path) -> None:
        """The body text of a command survives Claude Code install."""
        target = tmp_path / ".claude"
        target.mkdir()
        ClaudeCodeAdapter().install(grd_root, target)

        installed = (target / "commands" / "grd" / "help.md").read_text(encoding="utf-8")
        # Body should contain the non-placeholder text
        assert "Help body" in installed

    def test_gemini_toml_preserves_body(self, grd_root: Path, tmp_path: Path) -> None:
        """Command body text survives TOML conversion for Gemini."""
        target = tmp_path / ".gemini"
        target.mkdir()
        GeminiAdapter().install(grd_root, target)

        toml_file = target / "commands" / "grd" / "help.toml"
        content = toml_file.read_text(encoding="utf-8")
        assert "Help body" in content

    def test_codex_skill_preserves_body(self, grd_root: Path, tmp_path: Path) -> None:
        """Command body text survives Codex SKILL.md conversion."""
        target = tmp_path / ".codex"
        target.mkdir()
        skills = tmp_path / "skills"
        skills.mkdir()
        CodexAdapter().install(grd_root, target, skills_dir=skills)

        skill_md = skills / "grd-help" / "SKILL.md"
        content = skill_md.read_text(encoding="utf-8")
        assert "Help body" in content

    def test_opencode_flat_preserves_body(self, grd_root: Path, tmp_path: Path) -> None:
        """Command body text survives OpenCode flattening."""
        target = tmp_path / ".opencode"
        target.mkdir()
        OpenCodeAdapter().install(grd_root, target)

        cmd = target / "command" / "grd-help.md"
        content = cmd.read_text(encoding="utf-8")
        assert "Help body" in content

    def test_nested_command_survives_all_runtimes(self, grd_root: Path, tmp_path: Path) -> None:
        """The nested sub/deep.md command is reachable in every runtime."""
        # Claude Code: commands/grd/sub/deep.md
        cc_target = tmp_path / "cc" / ".claude"
        cc_target.mkdir(parents=True)
        ClaudeCodeAdapter().install(grd_root, cc_target)
        assert (cc_target / "commands" / "grd" / "sub" / "deep.md").exists()

        # Gemini: commands/grd/sub/deep.toml
        gem_target = tmp_path / "gem" / ".gemini"
        gem_target.mkdir(parents=True)
        GeminiAdapter().install(grd_root, gem_target)
        assert (gem_target / "commands" / "grd" / "sub" / "deep.toml").exists()

        # Codex: skills/grd-sub-deep/SKILL.md
        codex_target = tmp_path / "codex" / ".codex"
        codex_target.mkdir(parents=True)
        codex_skills = tmp_path / "codex" / "skills"
        codex_skills.mkdir(parents=True)
        CodexAdapter().install(grd_root, codex_target, skills_dir=codex_skills)
        assert (codex_skills / "grd-sub-deep" / "SKILL.md").exists()

        # OpenCode: command/grd-sub-deep.md
        oc_target = tmp_path / "oc" / ".opencode"
        oc_target.mkdir(parents=True)
        OpenCodeAdapter().install(grd_root, oc_target)
        assert (oc_target / "command" / "grd-sub-deep.md").exists()


@pytest.mark.parametrize("runtime", ["claude-code", "codex", "gemini", "opencode"])
def test_real_installed_command_include_semantics_are_equivalent_across_runtimes(tmp_path: Path, runtime: str) -> None:
    target = _install_real_repo_for_runtime(tmp_path, runtime)
    content = _read_compare_experiment_command(tmp_path, target, runtime)
    normalized = _canonicalize_runtime_markdown(content, runtime=runtime)
    lowered = normalized.lower()

    assert "@ include not resolved:" not in content.lower()
    assert "@ include cycle detected:" not in content.lower()
    assert "@ include read error:" not in content.lower()
    assert "@ include depth limit reached:" not in content.lower()
    assert "Systematically compare theoretical predictions with experimental or observational data." in normalized
    assert "unit mismatches and convention mismatches are the two most common sources of discrepancy" in lowered
    assert "what decisive output or contract target was predicted" in lowered


@pytest.mark.parametrize("runtime", ["claude-code", "codex", "gemini", "opencode"])
def test_real_installed_shared_prompt_semantics_are_equivalent_across_runtimes(tmp_path: Path, runtime: str) -> None:
    target = _install_real_repo_for_runtime(tmp_path, runtime)
    delegation = _canonicalize_runtime_markdown(
        (target / "get-research-done" / "references" / "orchestration" / "agent-delegation.md").read_text(
            encoding="utf-8"
        ),
        runtime=runtime,
    )
    execute_plan = _canonicalize_runtime_markdown(
        (target / "get-research-done" / "workflows" / "execute-plan.md").read_text(encoding="utf-8"),
        runtime=runtime,
    )

    assert "grd resolve-model" in delegation
    assert "Fresh context" in delegation
    assert "Assign an explicit write scope" in delegation
    assert "review_cadence" in execute_plan
    assert "Required first-result sanity gate" in execute_plan
    assert "Contract-backed plans" in execute_plan
