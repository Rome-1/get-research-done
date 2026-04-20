"""Integration tests: install → read back → verify for all 4 runtimes.

Tests that installed content matches source expectations for each adapter.
Exercises both the write path (install) and the read path (loading/parsing
installed content) to catch serialization/deserialization mismatches.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tomllib
from pathlib import Path

import pytest

from grd.adapters import iter_adapters
from grd.adapters.claude_code import ClaudeCodeAdapter
from grd.adapters.codex import CodexAdapter
from grd.adapters.gemini import GeminiAdapter
from grd.adapters.install_utils import (
    build_runtime_cli_bridge_command,
    convert_tool_references_in_body,
    expand_at_includes,
    translate_frontmatter_tool_names,
)
from grd.adapters.opencode import OpenCodeAdapter
from grd.adapters.runtime_catalog import get_shared_install_metadata, resolve_global_config_dir
from grd.adapters.tool_names import build_canonical_alias_map
from grd.registry import load_agents_from_dir

REPO_GRD_ROOT = Path(__file__).resolve().parents[2] / "src" / "grd"
RUNTIME_ALIAS_MAP = build_canonical_alias_map(adapter.tool_name_map for adapter in iter_adapters())
_SHARED_INSTALL = get_shared_install_metadata()
_INSTALL_CACHE: dict[tuple[str, tuple[str, ...]], Path] = {}


def expected_opencode_bridge(target: Path, *, is_global: bool = False, explicit_target: bool = False) -> str:
    return build_runtime_cli_bridge_command(
        "opencode",
        target_dir=target,
        config_dir_name=".opencode",
        is_global=is_global,
        explicit_target=explicit_target,
    )


def _make_checkout_stub(tmp_path: Path) -> tuple[Path, Path]:
    """Create a minimal checkout root with a local virtualenv interpreter."""
    checkout_root = tmp_path / "checkout"
    src_root = checkout_root / "src" / "grd"
    for subdir in ("commands", "agents", "hooks", "specs"):
        (src_root / subdir).mkdir(parents=True, exist_ok=True)
    (checkout_root / "package.json").write_text(
        json.dumps({"name": "get-physics-done", "version": "9.9.9", "gpdPythonVersion": "9.9.9"}),
        encoding="utf-8",
    )
    (checkout_root / "pyproject.toml").write_text(
        '[project]\nname = "get-physics-done"\nversion = "9.9.9"\n',
        encoding="utf-8",
    )
    venv_python_rel = Path("Scripts") / "python.exe" if os.name == "nt" else Path("bin") / "python"
    checkout_python = checkout_root / ".venv" / venv_python_rel
    checkout_python.parent.mkdir(parents=True, exist_ok=True)
    checkout_python.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    return checkout_root, checkout_python


def _collect_textual_artifacts(root: Path) -> str:
    """Return concatenated text from readable installed artifacts under *root*."""
    chunks: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            chunks.append(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
    return "\n".join(chunks)


def _install_real_repo_for_runtime(tmp_path: Path, runtime: str, source_root: Path = REPO_GPD_ROOT) -> Path:
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
        _install_gemini_for_tests(REPO_GRD_ROOT, target)
        return target

    if runtime == "opencode":
        target = tmp_path / ".opencode"
        target.mkdir()
        OpenCodeAdapter().install(REPO_GRD_ROOT, target)
        return target

    raise AssertionError(f"Unsupported runtime {runtime}")


def _install_gemini_for_tests(grd_root: Path, target: Path) -> GeminiAdapter:
    """Install Gemini artifacts and persist the deferred Gemini settings."""
    adapter = GeminiAdapter()
    result = adapter.install(grd_root, target)
    adapter.finalize_install(result)
    return adapter


def _source_signature(root: Path) -> tuple[str, ...]:
    signature_entries: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        signature_entries.append(f"{path.relative_to(root).as_posix()}:{digest}")
    return tuple(signature_entries)


def _cached_real_install(runtime: str, source_root: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    cache_key = (runtime, _source_signature(source_root))
    if cache_key not in _INSTALL_CACHE:
        _INSTALL_CACHE[cache_key] = _install_real_repo_for_runtime(
            tmp_path_factory.mktemp(f"{runtime}-real-install"),
            runtime,
            source_root=source_root,
        )
    return _INSTALL_CACHE[cache_key]


@pytest.fixture(scope="module")
def real_installed_repo_factory(tmp_path_factory: pytest.TempPathFactory):
    def factory(runtime: str) -> Path:
        return _cached_real_install(runtime, REPO_GPD_ROOT, tmp_path_factory)

    return factory


def _expected_local_bridge_for_runtime(runtime: str, target: Path) -> str:
    adapter = get_adapter(runtime)
    return build_runtime_cli_bridge_command(
        runtime,
        target_dir=target,
        config_dir_name=adapter.config_dir_name,
        is_global=False,
        explicit_target=False,
    )


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


def _read_runtime_command_prompt(tmp_path: Path, target: Path, runtime: str, command_name: str) -> str:
    if runtime == "claude-code":
        return (target / "commands" / "grd" / f"{command_name}.md").read_text(encoding="utf-8")

    if runtime == "codex":
        return (tmp_path / "skills" / f"grd-{command_name}" / "SKILL.md").read_text(encoding="utf-8")

    if runtime == "gemini":
        parsed = tomllib.loads((target / "commands" / "grd" / f"{command_name}.toml").read_text(encoding="utf-8"))
        prompt = parsed.get("prompt")
        assert isinstance(prompt, str)
        return prompt

    if runtime == "opencode":
        return (target / "command" / f"grd-{command_name}.md").read_text(encoding="utf-8")

    raise AssertionError(f"Unsupported runtime {runtime}")


def _read_runtime_update_surface(tmp_path: Path, target: Path, runtime: str) -> str:
    if runtime == "claude-code":
        return (target / "commands" / "grd" / "update.md").read_text(encoding="utf-8")

    if runtime == "codex":
        return (tmp_path / "skills" / "grd-update" / "SKILL.md").read_text(encoding="utf-8")

    if runtime == "gemini":
        parsed = tomllib.loads((target / "commands" / "grd" / "update.toml").read_text(encoding="utf-8"))
        prompt = parsed.get("prompt")
        assert isinstance(prompt, str)
        return prompt

    if runtime == "opencode":
        return (target / "command" / "grd-update.md").read_text(encoding="utf-8")

    raise AssertionError(f"Unsupported runtime {runtime}")


def _read_runtime_agent_prompt(target: Path, runtime: str, agent_name: str) -> str:
    if runtime in {"claude-code", "codex", "gemini", "opencode"}:
        return (target / "agents" / f"{agent_name}.md").read_text(encoding="utf-8")
    raise AssertionError(f"Unsupported runtime {runtime}")


def _assert_installed_contract_visibility(
    verifier: str,
    executor: str,
    new_project: str,
    plan_phase: str,
    write_paper: str,
    plan_schema: str,
    execute_phase: str,
    verify_work: str,
    *,
    runtime: str,
) -> None:
    verifier = _canonicalize_runtime_markdown(verifier, runtime=runtime)
    executor = _canonicalize_runtime_markdown(executor, runtime=runtime)
    new_project = _canonicalize_runtime_markdown(new_project, runtime=runtime)
    plan_phase = _canonicalize_runtime_markdown(plan_phase, runtime=runtime)
    write_paper = _canonicalize_runtime_markdown(write_paper, runtime=runtime)
    plan_schema = _canonicalize_runtime_markdown(plan_schema, runtime=runtime)
    execute_phase = _canonicalize_runtime_markdown(execute_phase, runtime=runtime)
    verify_work = _canonicalize_runtime_markdown(verify_work, runtime=runtime)

    assert "Execute all phase plans with wave-based parallelization" in execute_phase
    assert "Context budget: ~15% orchestrator, fresh context per subagent." in execute_phase

    assert "templates/contract-results-schema.md" in verifier
    assert "plan_contract_ref" in verifier
    assert "contract_results" in verifier
    assert "comparison_verdicts" in verifier
    assert "suggested_contract_checks" in verifier
    assert "contract_results.uncertainty_markers" in verifier

    assert "templates/contract-results-schema.md" in executor
    assert "plan_contract_ref" in executor
    assert "contract_results" in executor
    assert "comparison_verdicts" in executor
    assert "These ledgers are user-visible evidence." in executor

    assert "templates/project-contract-schema.md" in new_project
    assert "project_contract_load_info" in new_project
    assert "project_contract_validation" in new_project
    assert "`schema_version` must be the integer `1`" in new_project
    assert "`references[].must_surface` must stay a boolean `true` or `false`" in new_project
    assert "`context_intake`" in new_project
    assert "`approach_policy`" in new_project
    assert "`uncertainty_markers`" in new_project
    assert "`context_intake`, `approach_policy`, and `uncertainty_markers` must each stay as objects, not strings or lists." in new_project
    assert "review_mode: publication" in write_paper
    assert "GRD/AUTHOR-RESPONSE{round_suffix}.md" in write_paper
    assert "GRD/review/REFEREE_RESPONSE{round_suffix}.md" in write_paper
    assert "GRD/review/REVIEW-LEDGER{round_suffix}.json" in write_paper
    assert "GRD/review/REFEREE-DECISION{round_suffix}.json" in write_paper
    assert "GRD/REFEREE-REPORT{round_suffix}.md" in write_paper
    assert "GRD/REFEREE-REPORT{round_suffix}.tex" in write_paper

    assert "Canonical contract schema and hard validation rules" in plan_phase
    assert (
        "every proof-bearing plan must surface the theorem statement, named parameters, hypotheses, "
        "quantifier/domain obligations, and intended conclusion clauses visibly enough that a later audit can "
        "detect missing coverage"
    ) in plan_phase

    assert "`contract.context_intake` is required and must be a non-empty object" in plan_schema
    assert "`must_surface` is a boolean scalar. Use the YAML literals `true` and `false`" in plan_schema
    assert "If `must_surface: true`, `required_actions` must not be empty." in plan_schema
    assert "If `must_surface: true`, `applies_to[]` must not be empty." in plan_schema
    assert "`carry_forward_to[]` is optional free-text workflow scope" in plan_schema
    assert "`uncertainty_markers` must be a YAML object, not a string or list." in plan_schema

    assert "workflow.verifier=false" in execute_phase
    assert "skip verification" in execute_phase
    assert "proof red-teaming" in execute_phase
    assert "{plan_id}-PROOF-REDTEAM.md" in execute_phase
    assert "Targeted flags narrow the optional check mix only." in verify_work
    assert "Every spawned agent is a one-shot delegation" in verify_work
    assert "If a required proof-redteam audit is missing, stale, malformed, or not `passed`, spawn `grd-check-proof` once" in verify_work


@pytest.mark.parametrize("runtime", ["claude-code", "codex", "gemini", "opencode"])
def test_installed_verifier_prompt_surface_keeps_one_wrapper_and_stays_within_budget(
    real_installed_repo_factory,
    runtime: str,
) -> None:
    target = real_installed_repo_factory(runtime)
    verifier = _read_runtime_agent_prompt(target, runtime, "grd-verifier")
    descriptor = get_runtime_descriptor(runtime)
    line_budget, char_budget = (900, 60_000) if descriptor.native_include_support else (6_500, 430_000)

    assert verifier.count("## Agent Requirements") == 1
    assert verifier.index("## Agent Requirements") < verifier.index("## Bootstrap Discipline")
    if descriptor.native_include_support:
        assert verifier.count("verification-report.md") == 1
        assert verifier.count("contract-results-schema.md") == 1
        assert verifier.count("canonical-schema-discipline.md") == 1
    else:
        assert verifier.count("# Verification Report Template") == 1
        assert verifier.count("# Contract Results Schema") == 1
        assert verifier.count("# Canonical Schema Discipline") == 1
    assert len(verifier.splitlines()) <= line_budget
    assert len(verifier) <= char_budget


@pytest.mark.no_stable_hook_python
@pytest.mark.parametrize("runtime", ["claude-code"])
def test_install_artifacts_pin_checkout_python_when_running_from_checkout(
    tmp_path: Path,
    runtime: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the real checkout-python resolution path, not the stable fallback."""
    checkout_root, checkout_python = _make_checkout_stub(tmp_path)
    stale_managed_python = "/managed/grd/venv/bin/python"

    monkeypatch.setattr("grd.version.checkout_root", lambda start=None: checkout_root)
    monkeypatch.setattr("grd.adapters.install_utils.sys.executable", stale_managed_python)

    target = _install_real_repo_for_runtime(tmp_path, runtime)
    artifact_roots = [target]
    if runtime == "codex":
        artifact_roots.append(tmp_path / "skills")

    installed_text = "\n".join(_collect_textual_artifacts(root) for root in artifact_roots)

    assert str(checkout_python) in installed_text
    assert stale_managed_python not in installed_text


@pytest.mark.parametrize("runtime", ["codex"])
def test_update_surface_materializes_workflow_paths_in_compiled_artifacts(
    real_installed_repo_factory,
    runtime: str,
) -> None:
    target = real_installed_repo_factory(runtime)
    adapter = next(adapter for adapter in iter_adapters() if adapter.runtime_name == runtime)
    canonical_global_dir = resolve_global_config_dir(adapter.runtime_descriptor)
    content = _read_runtime_update_surface(target.parent, target, runtime)

    if runtime == "claude-code":
        assert f"@{target.as_posix()}/get-research-done/workflows/update.md" in content
        assert "{GRD_CONFIG_DIR}" not in content
    else:
        assert f'GRD_CONFIG_DIR="{target.as_posix()}"' in content
        assert f'GRD_GLOBAL_CONFIG_DIR="{canonical_global_dir.as_posix()}"' in content
        assert "TARGET_DIR_ARG=$(" in content

# ---------------------------------------------------------------------------
# Claude Code: install → read back → compare
# ---------------------------------------------------------------------------


class TestClaudeCodeRoundtrip:
    """Install into .claude/, then verify installed files match source semantics."""

    @pytest.fixture()
    def installed(self, tmp_path_factory: pytest.TempPathFactory) -> Path:
        return _cached_real_install("claude-code", REPO_GPD_ROOT, tmp_path_factory)

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
        _install_gemini_for_tests(grd_root, target)
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
            'description: Check research progress\n'
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
        _install_gemini_for_tests(grd_root, target)

        content = (target / "commands" / "grd" / "progress.toml").read_text(encoding="utf-8")
        parsed = tomllib.loads(content)

        assert "# Source frontmatter preserved for parity:" in content
        assert '# name: grd:progress' in content
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

    def test_runtime_cli_bridge_is_pinned_in_shell_heavy_surfaces(self, tmp_path: Path) -> None:
        """Gemini install rewrites the shell-heavy surfaces to the runtime bridge."""
        installed = _install_real_repo_for_runtime(tmp_path, "gemini")
        bridge_marker = "-m grd.runtime_cli --runtime gemini"
        command = _read_runtime_command_prompt(tmp_path, installed, "gemini", "set-profile")
        workflow = (installed / "get-research-done" / "workflows" / "set-profile.md").read_text(encoding="utf-8")
        execute_phase = (installed / "get-research-done" / "workflows" / "execute-phase.md").read_text(encoding="utf-8")
        agent = (installed / "agents" / "grd-planner.md").read_text(encoding="utf-8")

        assert bridge_marker in command
        assert bridge_marker in workflow
        assert bridge_marker in execute_phase
        assert bridge_marker in agent
        assert "config ensure-section" in command
        assert "config ensure-section" in workflow
        assert "init progress --include state,config" in command
        assert 'if !' in execute_phase and "verify plan \"$plan\"" in execute_phase
        assert 'INIT=$(' in agent and "init plan-phase \"<PHASE>\"" in agent
        assert "grd config ensure-section" not in command
        assert 'INIT=$(grd init progress --include state,config)' not in command
        assert 'if ! grd verify plan "$plan"; then' not in execute_phase
        assert 'INIT=$(grd init plan-phase "<PHASE>")' not in agent

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
    def installed(self, tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
        target = _cached_real_install("codex", REPO_GPD_ROOT, tmp_path_factory)
        return target, target.parent / "skills"

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

    def test_agents_not_installed_as_skills(self, installed: tuple[Path, Path]) -> None:
        """Codex agents are registered as roles, not duplicated as discoverable skills."""
        _, skills = installed
        agents = load_agents_from_dir(REPO_GPD_ROOT / "agents")
        for agent_name in sorted(agents):
            assert not (skills / agent_name).exists(), f"Agent should not be a Codex skill: {agent_name}"

    def test_agents_installed_as_md_files(self, installed: tuple[Path, Path]) -> None:
        """Agents are also installed as .md files under .codex/agents/."""
        target, _ = installed
        agents_dir = target / "agents"
        assert agents_dir.is_dir()
        src_agents = sorted(f.name for f in (REPO_GPD_ROOT / "agents").glob("*.md"))
        dest_agents = sorted(f.name for f in agents_dir.glob("*.md"))
        assert dest_agents == src_agents

    def test_agent_role_configs_installed(self, installed: tuple[Path, Path]) -> None:
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

    def test_runtime_cli_bridge_is_pinned_in_shell_heavy_surfaces(self, tmp_path: Path) -> None:
        """Codex install rewrites the shell-heavy surfaces to the runtime bridge."""
        target = _install_real_repo_for_runtime(tmp_path, "codex")
        bridge_marker = "-m grd.runtime_cli --runtime codex"
        command = _read_runtime_command_prompt(tmp_path, target, "codex", "set-profile")
        workflow = (target / "get-research-done" / "workflows" / "set-profile.md").read_text(encoding="utf-8")
        execute_phase = (target / "get-research-done" / "workflows" / "execute-phase.md").read_text(encoding="utf-8")
        agent = (target / "agents" / "grd-planner.md").read_text(encoding="utf-8")

        assert bridge_marker in command
        assert bridge_marker in workflow
        assert bridge_marker in execute_phase
        assert bridge_marker in agent
        assert "config ensure-section" in command
        assert "config ensure-section" in workflow
        assert "verify plan \"$plan\"" in execute_phase
        assert 'INIT=$(' in agent and "init plan-phase \"${PHASE}\"" in agent
        assert "```bash\ngrd config ensure-section\n" not in workflow
        assert 'if ! grd verify plan "$plan"; then' not in execute_phase
        assert 'INIT=$(grd init plan-phase "${PHASE}")' not in agent

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


def test_real_installed_opencode_artifacts_rewrite_grd_cli_calls_to_runtime_bridge(tmp_path: Path) -> None:
    target = _install_real_repo_for_runtime(tmp_path, "opencode")
    expected_bridge = expected_opencode_bridge(target, is_global=False)
    command = (target / "command" / "grd-settings.md").read_text(encoding="utf-8")
    workflow = (target / "get-research-done" / "workflows" / "settings.md").read_text(encoding="utf-8")
    agent = (target / "agents" / "grd-planner.md").read_text(encoding="utf-8")

    assert expected_bridge + " config ensure-section" in command
    assert f'INIT=$({expected_bridge} init progress --include state,config)' in command
    assert expected_bridge + " config ensure-section" in workflow
    assert f'INIT=$({expected_bridge} init progress --include state,config)' in workflow
    assert 'echo "ERROR: grd initialization failed: $INIT"' in workflow
    assert f'INIT=$({expected_bridge} init plan-phase "<PHASE>")' in agent
    assert 'INIT=$(grd init progress --include state,config)' not in workflow
    assert 'INIT=$(grd init plan-phase "<PHASE>")' not in agent


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
        target = tmp_path / ".gemini"
        target.mkdir()

        _install_gemini_for_tests(grd_root, target)
        assert (target / "commands" / "grd").is_dir()
        assert (target / "get-research-done").is_dir()

        GeminiAdapter().uninstall(target)
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
        assert not skills.exists() or not any(d.name.startswith("grd-") for d in skills.iterdir() if d.is_dir())
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
        _install_gemini_for_tests(grd_root, target)

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
        _install_gemini_for_tests(grd_root, gem_target)
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


@pytest.mark.parametrize("runtime", ["claude-code", "codex", "gemini", "opencode"])
def test_real_installed_contract_and_review_surfaces_keep_required_schema_bodies(
    tmp_path: Path, runtime: str
) -> None:
    target = _install_real_repo_for_runtime(tmp_path, runtime)

    verify_work = _canonicalize_runtime_markdown(
        _read_runtime_command_prompt(tmp_path, target, runtime, "verify-work"),
        runtime=runtime,
    )
    sync_state = _canonicalize_runtime_markdown(
        _read_runtime_command_prompt(tmp_path, target, runtime, "sync-state"),
        runtime=runtime,
    )
    write_paper = _canonicalize_runtime_markdown(
        _read_runtime_command_prompt(tmp_path, target, runtime, "write-paper"),
        runtime=runtime,
    )
    review_literature = _canonicalize_runtime_markdown(
        _read_runtime_agent_prompt(target, runtime, "grd-review-literature"),
        runtime=runtime,
    )
    review_reader = _canonicalize_runtime_markdown(
        _read_runtime_agent_prompt(target, runtime, "grd-review-reader"),
        runtime=runtime,
    )
    review_math = _canonicalize_runtime_markdown(
        _read_runtime_agent_prompt(target, runtime, "grd-review-math"),
        runtime=runtime,
    )
    review_physics = _canonicalize_runtime_markdown(
        _read_runtime_agent_prompt(target, runtime, "grd-review-physics"),
        runtime=runtime,
    )
    review_significance = _canonicalize_runtime_markdown(
        _read_runtime_agent_prompt(target, runtime, "grd-review-significance"),
        runtime=runtime,
    )
    referee = _canonicalize_runtime_markdown(
        _read_runtime_agent_prompt(target, runtime, "grd-referee"),
        runtime=runtime,
    )

    assert "grd:set-tier-models" in content
    assert "tier-1" in content
    assert "tier-2" in content
    assert "tier-3" in content
    assert "grd:set-profile" in content
    assert "grd:settings" in content
    assert "model_overrides.<runtime>" in content
    assert "strongest reasoning" in content
    assert "balanced default" in content
    assert "fastest / most economical" in content

@pytest.mark.parametrize("runtime", ["claude-code", "codex", "gemini", "opencode"])
def test_real_installed_public_local_cli_commands_stay_canonical(
    real_installed_repo_factory,
    runtime: str,
) -> None:
    target = real_installed_repo_factory(runtime)
    bridge_command = _expected_local_bridge_for_runtime(runtime, target)
    installed_text = _collect_textual_artifacts(target.parent)

    for public_command in local_cli_bridge_commands():
        assert public_command in installed_text
        assert f"{bridge_command}{public_command[3:]}" not in installed_text


def test_help_like_skills_keep_canonical_local_cli_language(tmp_path: Path) -> None:
    """Codex skills keep canonical local CLI names in prose even when shell steps bridge."""
    _install_real_repo_for_runtime(tmp_path, "codex")
    skills = tmp_path / "skills"
    help_skill = (skills / "grd-help" / "SKILL.md").read_text(encoding="utf-8")
    tour_skill = (skills / "grd-tour" / "SKILL.md").read_text(encoding="utf-8")
    settings_skill = (skills / "grd-settings" / "SKILL.md").read_text(encoding="utf-8")

    assert "Use `grd --help` to inspect the executable local install/readiness/permissions/diagnostics surface directly." in help_skill
    assert "For a normal-terminal, current-workspace read-only recovery snapshot without launching the runtime, use `grd resume`." in help_skill
    assert "For a normal-terminal, read-only machine-local usage / cost summary, use `grd cost`." in help_skill
    assert "The normal terminal is where you install GRD, run `grd --help`, and run" in tour_skill
    assert "`grd resume` is the normal-terminal recovery step for reopening the right" in tour_skill
    assert "use `grd --help` when you need the broader local CLI entrypoint" in settings_skill
    assert "use `grd cost` after runs for advisory local usage / cost, optional USD budget guardrails, and the current profile tier mix" in settings_skill
    assert re.search(r"`[^`\n]*grd\.runtime_cli[^`\n]*(?:--help|resume|cost)[^`\n]*`", help_skill) is None
    assert re.search(r"`[^`\n]*grd\.runtime_cli[^`\n]*(?:--help|resume|cost)[^`\n]*`", tour_skill) is None
    assert re.search(r"`[^`\n]*grd\.runtime_cli[^`\n]*(?:--help|resume|cost)[^`\n]*`", settings_skill) is None


@pytest.mark.parametrize("runtime", ["claude-code", "codex", "gemini", "opencode"])
def test_installed_prompt_contract_visibility_survives_adapter_projection(
    real_installed_repo_factory,
    runtime: str,
) -> None:
    target = real_installed_repo_factory(runtime)
    verifier = _read_runtime_agent_prompt(target, runtime, "grd-verifier")
    executor = _read_runtime_agent_prompt(target, runtime, "grd-executor")
    new_project = _read_runtime_command_prompt(target.parent, target, runtime, "new-project")
    plan_phase = _read_runtime_command_prompt(target.parent, target, runtime, "plan-phase")
    write_paper = _read_runtime_command_prompt(target.parent, target, runtime, "write-paper")
    plan_schema = (target / "get-physics-done" / "templates" / "plan-contract-schema.md").read_text(encoding="utf-8")
    execute_phase = _read_runtime_command_prompt(target.parent, target, runtime, "execute-phase")
    verify_work = _read_runtime_command_prompt(target.parent, target, runtime, "verify-work")

    _assert_installed_contract_visibility(
        verifier,
        executor,
        new_project,
        plan_phase,
        write_paper,
        plan_schema,
        execute_phase,
        verify_work,
        runtime=runtime,
    )
    assert "## Physics Stub Detection Patterns" not in verifier
    assert "Load on demand from `references/verification/examples/verifier-worked-examples.md`." in verifier


@pytest.mark.parametrize("runtime", ["claude-code", "codex", "gemini", "opencode"])
def test_installed_executor_bootstrap_surface_defers_completion_only_materials(
    real_installed_repo_factory,
    runtime: str,
) -> None:
    target = real_installed_repo_factory(runtime)
    executor = _read_runtime_agent_prompt(target, runtime, "grd-executor")
    bootstrap, _, _ = executor.partition("<summary_creation>")

    assert "templates/summary.md" not in bootstrap
    assert "templates/calculation-log.md" not in bootstrap
    assert "Order-of-Limits Awareness" not in bootstrap


@pytest.mark.parametrize("runtime", ["claude-code", "codex", "gemini", "opencode"])
def test_installed_planner_bootstrap_surface_defers_execution_and_completion_materials(
    real_installed_repo_factory,
    runtime: str,
) -> None:
    target = real_installed_repo_factory(runtime)
    planner = _read_runtime_agent_prompt(target, runtime, "grd-planner")
    bootstrap, separator, _ = planner.partition("On-demand references:")

    assert separator == "On-demand references:"
    assert "phase-prompt.md" in bootstrap
    assert "plan-contract-schema.md" in bootstrap
    assert "Read config.json for planning behavior settings." not in bootstrap
    assert "## Summary Template" not in bootstrap
    assert "Order-of-Limits Awareness" not in bootstrap
