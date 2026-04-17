"""Guardrails that keep prompt-authored CLI references aligned with the real CLI."""

from __future__ import annotations

import re
from pathlib import Path

from grd.adapters.install_utils import expand_at_includes
from grd.core import public_surface_contract as public_surface_contract_module
from grd.core.cli_args import _ROOT_GLOBAL_FLAG_TOKENS
from grd.core.public_surface_contract import (
    local_cli_bridge_note,
    local_cli_doctor_global_command,
    local_cli_doctor_local_command,
    local_cli_permissions_status_command,
    local_cli_plan_preflight_command,
    local_cli_resume_command,
    local_cli_resume_recent_command,
    local_cli_unattended_readiness_command,
    local_cli_validate_command_context_command,
    resume_authority_fields,
)
from grd.registry import VALID_CONTEXT_MODES, _parse_frontmatter
from tests.doc_surface_contracts import (
    DOCTOR_RUNTIME_SCOPE_RE,
    assert_beginner_startup_routing_contract,
    assert_cost_advisory_contract,
    assert_cost_surface_discoverability,
    assert_health_command_public_contract,
    assert_help_command_all_extract_contract,
    assert_help_command_quick_start_extract_contract,
    assert_help_command_single_command_extract_contract,
    assert_help_workflow_command_index_contract,
    assert_help_workflow_quick_start_taxonomy_contract,
    assert_help_workflow_runtime_reference_contract,
    assert_recovery_ladder_contract,
    assert_resume_authority_contract,
    assert_runtime_reset_rediscovery_contract,
    assert_start_workflow_router_contract,
    assert_tour_command_surface_contract,
    assert_unattended_readiness_contract,
    assert_wolfram_plan_boundary_contract,
    assert_workflow_preset_surface_contract,
    resume_authority_public_vocabulary_intro,
    resume_compat_alias_fields,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = REPO_ROOT / "src/grd/cli.py"
COMMANDS_DIR = REPO_ROOT / "src/grd/commands"
WORKFLOWS_DIR = REPO_ROOT / "src/grd/specs/workflows"
PROMPT_ROOTS = (
    COMMANDS_DIR,
    REPO_ROOT / "src/grd/agents",
    WORKFLOWS_DIR,
    REPO_ROOT / "src/grd/specs/references",
    REPO_ROOT / "src/grd/specs/templates",
)
ROOT_COMMAND_RE = re.compile(r"@app\.command\(\s*\"([a-z0-9-]+)\"(?:,|\))", re.MULTILINE)
TYPER_GROUP_RE = re.compile(r"app\.add_typer\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*name=\"([a-z0-9-]+)\"", re.MULTILINE)
GROUP_COMMAND_RE = re.compile(r"@{group}\.command\(\s*\"([a-z0-9-]+)\"(?:,|\))", re.MULTILINE)
NON_CANONICAL_GRD_COMMAND_RE = re.compile(r"(?<![A-Za-z0-9_./}])(?:\$grd-[A-Za-z0-9{}-]+|/grd-[A-Za-z0-9{}-]+)(?!\.md)")
RAW_AFTER_SUBCOMMAND_RE = re.compile(r"\bgpd\s+(?!--raw\b)[^`\n]*\s+--raw\b")
SUMMARY_EXTRACT_FIELDS_RE = re.compile(r"\bgpd\s+summary-extract\b[^\n`]*\s--fields\b")


def _extract_between(content: str, start_marker: str, end_marker: str) -> str:
    start = content.index(start_marker) + len(start_marker)
    end = content.index(end_marker, start)
    return content[start:end]


def _iter_prompt_sources() -> list[Path]:
    files: list[Path] = []
    for root in PROMPT_ROOTS:
        files.extend(sorted(root.rglob("*.md")))
    return files


def _declared_command_surfaces() -> set[str]:
    content = CLI_PATH.read_text(encoding="utf-8")
    surfaces = set(ROOT_COMMAND_RE.findall(content))
    surfaces.update(_declared_group_surfaces(content))
    return surfaces


def _declared_group_surfaces(content: str) -> set[str]:
    groups = dict(TYPER_GROUP_RE.findall(content))
    surfaces: set[str] = set(groups.values())
    for group_var, group_name in groups.items():
        command_re = re.compile(GROUP_COMMAND_RE.pattern.format(group=re.escape(group_var)), re.MULTILINE)
        for subcommand in command_re.findall(content):
            surfaces.add(f"{group_name} {subcommand}")
    return surfaces


def _declared_root_commands(content: str) -> set[str]:
    return set(ROOT_COMMAND_RE.findall(content))


def _declared_groups(content: str) -> dict[str, set[str]]:
    groups = dict(TYPER_GROUP_RE.findall(content))
    result: dict[str, set[str]] = {}
    for group_var, group_name in groups.items():
        command_re = re.compile(GROUP_COMMAND_RE.pattern.format(group=re.escape(group_var)), re.MULTILINE)
        result[group_name] = set(command_re.findall(content))
    return result


def _iter_markdown_code_samples(content: str) -> list[str]:
    samples: list[str] = []
    fenced_pattern = re.compile(r"```(?:[^\n`]*)\n(.*?)```", re.DOTALL)
    for match in fenced_pattern.finditer(content):
        samples.append(match.group(1))
    inline_source = fenced_pattern.sub("\n", content)
    samples.extend(re.findall(r"`([^`]+)`", inline_source))
    return samples


def _extract_grd_command_surfaces(
    content: str,
    *,
    root_commands: set[str],
    group_commands: dict[str, set[str]],
) -> list[str]:
    command_roots = root_commands | set(group_commands)
    if not command_roots:
        return []

    root_pattern = "|".join(sorted((re.escape(root) for root in command_roots), key=len, reverse=True))
    root_flag_pattern = "|".join(sorted((re.escape(flag) for flag in _ROOT_GLOBAL_FLAG_TOKENS), key=len, reverse=True))
    prefix_pattern = rf"(?:\s+(?:{root_flag_pattern}|--cwd(?:=[^\s`]+)?|--cwd\s+[^\s`]+))*"
    pattern = re.compile(rf"\bgpd{prefix_pattern}\s+({root_pattern})(?:\s+([a-z0-9-]+))?")
    surfaces: list[str] = []
    for sample in _iter_markdown_code_samples(content):
        for match in pattern.finditer(sample):
            command = match.group(1)
            subcommand = match.group(2)
            if command in root_commands and command not in group_commands:
                surfaces.append(command)
                continue
            if command in group_commands:
                surfaces.append(command if subcommand is None else f"{command} {subcommand}")
    return surfaces


def test_prompt_sources_use_only_real_grd_command_surfaces() -> None:
    allowed = _declared_command_surfaces()
    cli_content = CLI_PATH.read_text(encoding="utf-8")
    root_commands = _declared_root_commands(cli_content)
    group_commands = _declared_groups(cli_content)

    invalid_surfaces: list[str] = []
    noncanonical_surfaces: list[str] = []
    raw_after_subcommand: list[str] = []
    summary_extract_fields: list[str] = []

    for path in _iter_prompt_sources():
        content = path.read_text(encoding="utf-8")
        for surface in _extract_grd_command_surfaces(content, root_commands=root_commands, group_commands=group_commands):
            if surface not in allowed:
                invalid_surfaces.append(f"{relpath} -> {surface}")

    assert invalid == []


def test_prompt_sources_use_canonical_grd_command_syntax() -> None:
    invalid: list[str] = []

    for path in _iter_prompt_sources():
        content = path.read_text(encoding="utf-8")
        for match in NON_CANONICAL_GRD_COMMAND_RE.finditer(content):
            invalid.append(f"{path.relative_to(REPO_ROOT)} -> {match.group(0)}")

        for match in RAW_AFTER_SUBCOMMAND_RE.finditer(content):
            raw_after_subcommand.append(f"{relpath} -> {match.group(0)}")

        for match in SUMMARY_EXTRACT_FIELDS_RE.finditer(content):
            summary_extract_fields.append(f"{relpath} -> {match.group(0)}")

    assert invalid_surfaces == []
    assert noncanonical_surfaces == []
    assert raw_after_subcommand == []
    assert summary_extract_fields == []


def test_help_prompt_command_count_matches_live_inventory() -> None:
    command_count = len(list(COMMANDS_DIR.glob("*.md")))
    help_prompt = (REPO_ROOT / "src/grd/commands/help.md").read_text(encoding="utf-8")

    assert f"Run `/grd:help --all` for all {command_count} commands." in help_prompt


def test_suggest_next_prompt_uses_real_cli_subcommand() -> None:
    suggest_prompt = (REPO_ROOT / "src/grd/commands/suggest-next.md").read_text(encoding="utf-8")

    assert "Uses `grd --raw suggest`" in suggest_prompt
    assert "Local CLI fallback: `grd --raw suggest`" in suggest_prompt
    assert "grd suggest-next to scan" not in suggest_prompt


def test_tangent_prompt_routes_into_existing_workflows() -> None:
    tangent_command = (COMMANDS_DIR / "tangent.md").read_text(encoding="utf-8")
    tangent_workflow = (WORKFLOWS_DIR / "tangent.md").read_text(encoding="utf-8")

    assert "name: grd:tangent" in tangent_command
    assert "@{GRD_INSTALL_DIR}/workflows/tangent.md" in tangent_command
    assert "grd:quick" in tangent_command
    assert "grd:add-todo" in tangent_command
    assert "grd:branch-hypothesis" in tangent_command

    for token in (
        "Stay on the main path",
        "Run a bounded quick check now",
        "Capture and defer",
        "Open a hypothesis branch",
        "live execution review stop surfaces a tangent proposal",
        "{GRD_INSTALL_DIR}/workflows/quick.md",
        "{GRD_INSTALL_DIR}/workflows/add-todo.md",
        "{GRD_INSTALL_DIR}/workflows/branch-hypothesis.md",
    ):
        assert token in tangent_workflow


def test_progress_prompt_runs_preflight_after_init_context() -> None:
    command = (REPO_ROOT / "src/grd/commands/progress.md").read_text(encoding="utf-8")
    workflow = (REPO_ROOT / "src/grd/specs/workflows/progress.md").read_text(encoding="utf-8")

    for content in (command, workflow):
        assert "INIT=$(grd init progress --include state,roadmap,project,config)" in content
        assert "CONTEXT=$(grd --raw validate command-context progress \"$ARGUMENTS\")" in content
        assert content.index("INIT=$(grd init progress --include state,roadmap,project,config)") < content.index(
            "CONTEXT=$(grd --raw validate command-context progress \"$ARGUMENTS\")"
        )


def test_progress_prompt_requires_project_not_roadmap() -> None:
    command = (REPO_ROOT / "src/grd/commands/progress.md").read_text(encoding="utf-8")

    assert 'files: [".grd/PROJECT.md"]' in command
    assert 'files: [".grd/ROADMAP.md"]' not in command


def test_progress_prompt_and_help_clarify_runtime_vs_local_cli_boundary() -> None:
    command = (REPO_ROOT / "src/grd/commands/progress.md").read_text(encoding="utf-8")
    help_workflow = (WORKFLOWS_DIR / "help.md").read_text(encoding="utf-8")
    progress_section = _extract_between(help_workflow, "### Progress Tracking", "### Session Management")
    normalized_command = " ".join(command.split())
    normalized_progress_section = " ".join(progress_section.split())

    assert "The local CLI `grd progress` is a separate read-only renderer" in normalized_command
    assert "takes `json|bar|table` and does not accept these flags" in normalized_command
    assert "The local CLI `grd progress` is a separate read-only renderer" in normalized_progress_section
    assert "Local CLI: `grd progress json|bar|table`" in normalized_progress_section


def test_plan_phase_prompt_is_a_thin_dispatch_shell() -> None:
    command = (REPO_ROOT / "src/grd/commands/plan-phase.md").read_text(encoding="utf-8")

    assert "@{GRD_INSTALL_DIR}/workflows/plan-phase.md" in command
    assert "@{GRD_INSTALL_DIR}/templates/plan-contract-schema.md" not in command
    assert "@{GRD_INSTALL_DIR}/references/ui/ui-brand.md" not in command
    assert "Follow the included workflow file exactly." in command
    assert "agent: grd-planner" in command
    assert "What Makes a Good Physics Plan" not in command
    assert "Common Failure Modes" not in command
    assert "Quick Checklist Before Approving a Plan" not in command
    assert "Domain-Aware Planning" not in command
    assert "grd --raw init plan-phase" not in command


def test_new_milestone_prompt_mentions_planning_commit_docs() -> None:
    command = (REPO_ROOT / "src/grd/commands/new-milestone.md").read_text(encoding="utf-8")
    workflow = (REPO_ROOT / "src/grd/specs/workflows/new-milestone.md").read_text(encoding="utf-8")

    for content in (command, workflow):
        assert "planning.commit_docs" in content
        assert "/grd:discuss-phase [N]" in content or "/grd:discuss-phase 1" in content


def test_doc_sources_place_global_raw_before_subcommands() -> None:
    invalid: list[str] = []
    doc_paths = [*(_iter_prompt_sources()), GRAPH_PATH]

    for path in doc_paths:
        content = path.read_text(encoding="utf-8")
        for match in RAW_AFTER_SUBCOMMAND_RE.finditer(content):
            invalid.append(f"{path.relative_to(REPO_ROOT)} -> {match.group(0)}")

    assert invalid == []


def test_command_prompts_declare_valid_context_modes() -> None:
    missing: list[str] = []
    invalid: list[str] = []

    for path in sorted((REPO_ROOT / "src/grd/commands").glob("*.md")):
        meta, _body = _parse_frontmatter(path.read_text(encoding="utf-8"))
        mode = meta.get("context_mode")
        if mode is None:
            missing.append(str(path.relative_to(REPO_ROOT)))
            continue
        if str(mode) not in VALID_CONTEXT_MODES:
            invalid.append(f"{path.relative_to(REPO_ROOT)} -> {mode}")

    assert missing == []
    assert invalid == []


def test_new_project_prompt_uses_stdin_for_contract_validation_and_persistence() -> None:
    workflow = (REPO_ROOT / "src/grd/specs/workflows/new-project.md").read_text(encoding="utf-8")

    assert 'printf \'%s\\n\' "$PROJECT_CONTRACT_JSON" | grd --raw validate project-contract -' in workflow
    assert 'printf \'%s\\n\' "$PROJECT_CONTRACT_JSON" | grd state set-project-contract -' in workflow
    assert "/tmp/grd-project-contract.json" not in workflow
    assert "temporary JSON file if needed" not in workflow


def test_state_json_schema_stays_aligned_with_stdin_contract_persistence_flow() -> None:
    schema = (REPO_ROOT / "src/grd/specs/templates/state-json-schema.md").read_text(encoding="utf-8")

    assert 'printf \'%s\\n\' "$PROJECT_CONTRACT_JSON" | grd --raw validate project-contract -' in schema
    assert 'printf \'%s\\n\' "$PROJECT_CONTRACT_JSON" | grd state set-project-contract -' in schema
    assert "grd state advance" in schema
    assert "grd state advance-plan" not in schema
    assert "Preferred write path: `grd state set-project-contract <path-to-contract.json>`." not in schema


def test_new_project_and_state_schema_surface_contract_id_integrity_rules() -> None:
    workflow = (REPO_ROOT / "src/grd/specs/workflows/new-project.md").read_text(encoding="utf-8")
    schema = expand_at_includes(
        (REPO_ROOT / "src/grd/specs/templates/state-json-schema.md").read_text(encoding="utf-8"),
        REPO_ROOT / "src/grd/specs",
        "/runtime/",
    )

    assert "do not paraphrase the schema here; reuse its exact keys, enum values, list/object shapes, ID-linkage rules, and proof-bearing claim requirements" in workflow
    assert "Same-kind IDs must be unique within each section." in schema
    assert "must not match any declared contract ID" in schema


def test_compare_branches_prompt_keeps_branch_summary_extraction_in_memory() -> None:
    workflow = (REPO_ROOT / "src/grd/specs/workflows/compare-branches.md").read_text(encoding="utf-8")

    assert "Prefer parsing the `git show` output directly in memory." in workflow
    assert "do not write it to `.grd/tmp/` just to run a path-based extractor." in workflow
    assert "Keep branch-summary extraction in memory/stdout only" in workflow
    assert "do not use `.grd/tmp/`, `/tmp`, or another temp root for this step." in workflow


def test_help_prompts_surface_tangent_command_for_side_investigations() -> None:
    help_workflow = (WORKFLOWS_DIR / "help.md").read_text(encoding="utf-8")

    assert "grd:tangent" in help_workflow
    assert re.search(r"grd:tangent[^\n]*?(?:tangent|side investigation|alternative direction|parallel)", help_workflow, re.I)


def test_settings_and_research_mode_docs_keep_tangent_branch_taxonomy_strict() -> None:
    settings = (WORKFLOWS_DIR / "settings.md").read_text(encoding="utf-8")
    new_project = (WORKFLOWS_DIR / "new-project.md").read_text(encoding="utf-8")
    research_modes = (
        REPO_ROOT / "src/grd/specs/references/research/research-modes.md"
    ).read_text(encoding="utf-8")

    assert "Which starting workflow preset should GRD use for `GRD/config.json`?" in new_project
    assert "offer a preset choice before individual questions" in new_project
    assert "preset bundle over the existing config knobs" in new_project
    assert "preview" in new_project
    assert "writing `GRD/config.json`" in new_project
    assert "Do not persist a separate preset key." in new_project
    assert '"Core research (Recommended)"' in new_project
    assert '"Theory"' in new_project
    assert '"Numerics"' in new_project
    assert '"Publication / manuscript"' in new_project
    assert '"Full research"' in new_project
    assert "multiple hypothesis branches" not in settings
    assert "Minimal branching, fast convergence." not in settings
    assert "auto-switch to exploit once approach is validated" not in settings
    assert "does **not** by itself authorize git-backed hypothesis branches" in settings
    assert "surface tangent decisions explicitly" in settings
    assert "Suppress optional tangents unless the user explicitly requests them" in settings
    assert "preview" in settings
    assert "explicit apply or customize choice" in settings
    assert "do **not** silently create git-backed hypothesis branches" in research_modes
    assert "only explicit tangent decisions become hypothesis branches or parallel plans" in research_modes
    assert "Flag complementary approaches as tangent candidates for optional parallel investigation" in research_modes


def test_regression_check_prompt_examples_include_optional_phase_before_quick_flag() -> None:
    verifier = (REPO_ROOT / "src/grd/agents/grd-verifier.md").read_text(encoding="utf-8")
    infra = (REPO_ROOT / "src/grd/specs/references/orchestration/agent-infrastructure.md").read_text(encoding="utf-8")

    for content in (verifier, infra):
        assert "grd regression-check [phase] [--quick]" in content
        assert "grd regression-check [--quick]" not in content


def test_verifier_prompt_does_not_claim_regression_check_spawns_verifier() -> None:
    verifier = (REPO_ROOT / "src/grd/agents/grd-verifier.md").read_text(encoding="utf-8")

    assert "The regression-check command" not in verifier


def test_help_prompt_workflow_modes_match_current_settings_vocabulary() -> None:
    help_workflow = (WORKFLOWS_DIR / "help.md").read_text(encoding="utf-8")

    for content in (help_command, help_workflow):
        assert "Interactive Mode" not in content
        assert "YOLO Mode" not in content
        assert "Change anytime by editing `.grd/config.json`" not in content
        assert "Supervised" in content
        assert "Balanced (Recommended)" in content
        assert "YOLO" in content
        assert "/grd:settings" in content
        assert "/grd:discuss-phase" in content
        assert "execution.review_cadence" in content
        assert "planning.commit_docs" in content
        assert "git.branching_strategy" in content


def test_new_project_prompt_surfaces_discuss_phase_before_planning() -> None:
    command = (REPO_ROOT / "src/grd/commands/new-project.md").read_text(encoding="utf-8")
    workflow = (REPO_ROOT / "src/grd/specs/workflows/new-project.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    for content in (command, workflow, readme):
        assert "/grd:discuss-phase 1" in content

    assert "Discuss phase 1 now?" in command
    assert "Discuss phase 1 now?" in workflow
    assert "Plan phase 1 now?" not in command
    assert "Plan phase 1 now?" not in workflow


def test_execute_phase_failure_recovery_counts_only_top_level_verification_statuses() -> None:
    workflow = (REPO_ROOT / "src/grd/specs/workflows/execute-phase.md").read_text(encoding="utf-8")

    assert (
        "FAILED_COUNT=$(rg -c '^status: (gaps_found|expert_needed|human_needed)$'"
        in workflow
    )
    assert (
        "TOTAL_COUNT=$(rg -c '^status: (passed|gaps_found|expert_needed|human_needed)$'"
        in workflow
    )
    assert 'grep -c "status: failed"' not in workflow
    assert 'grep -c "status:"' not in workflow
