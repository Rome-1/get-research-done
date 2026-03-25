"""Regression tests for the specs/references and domains/physics layout.

After the Phase 2 domain migration, physics-specific content lives in
src/grd/domains/physics/ while domain-agnostic content remains in
src/grd/specs/references/.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
REFERENCES_DIR = REPO_ROOT / "src/grd/specs/references"
PHYSICS_DIR = REPO_ROOT / "src/grd/domains/physics"

# Domain-agnostic reference directories (remain in specs/references/)
EXPECTED_AGNOSTIC_DIRS = {
    "architecture",
    "examples",
    "execution",
    "methods",
    "orchestration",
    "planning",
    "research",
    "shared",
    "templates",
    "tooling",
    "ui",
}

# Physics domain pack directories (now in domains/physics/)
EXPECTED_PHYSICS_DIRS = {
    "conventions",
    "protocols",
    "publication",
    "subfields",
    "verification",
}

EXPECTED_TEMPLATE_DIRS = {
    "research-mapper",
}

EXPECTED_VERIFICATION_DIRS = {
    "audits",
    "core",
    "domains",
    "errors",
    "examples",
    "meta",
}

REFERENCE_TOKEN_RE = re.compile(r"references/[A-Za-z0-9_./-]+\.md")
DOMAIN_TOKEN_RE = re.compile(r"domains/(?:physics|\{GRD_DOMAIN\})/[A-Za-z0-9_./-]+\.md")
INLINE_DOC_TOKEN_RE = re.compile(r"`((?:references/|\.{1,2}/)[A-Za-z0-9_./-]+\.md(?:#[^`]+)?)`")
NON_SPEC_REFERENCE_TOKENS = {
    "references/references-pending.md",
}

# Files that were in the previous flat refs layout and moved to refs subdirs
# (these remain in specs/references/ — domain-agnostic content)
MOVED_AGNOSTIC_FILES = [
    ("agent-delegation.md", "orchestration/agent-delegation.md"),
    ("agent-infrastructure.md", "orchestration/agent-infrastructure.md"),
    ("approximation-selection.md", "methods/approximation-selection.md"),
    ("artifact-review-architecture.md", "architecture/artifact-review-architecture.md"),
    ("checkpoints.md", "orchestration/checkpoints.md"),
    ("context-budget.md", "orchestration/context-budget.md"),
    ("context-pressure-thresholds.md", "orchestration/context-pressure-thresholds.md"),
    ("continuation-format.md", "orchestration/continuation-format.md"),
    ("contradiction-resolution-example.md", "examples/contradiction-resolution-example.md"),
    ("cross-project-patterns.md", "shared/cross-project-patterns.md"),
    ("execute-plan-checkpoints.md", "execution/execute-plan-checkpoints.md"),
    ("execute-plan-recovery.md", "execution/execute-plan-recovery.md"),
    ("execute-plan-validation.md", "execution/execute-plan-validation.md"),
    ("executor-completion.md", "execution/executor-completion.md"),
    ("executor-deviation-rules.md", "execution/executor-deviation-rules.md"),
    ("executor-index.md", "execution/executor-index.md"),
    ("executor-subfield-guide.md", "execution/executor-subfield-guide.md"),
    ("executor-task-checkpoints.md", "execution/executor-task-checkpoints.md"),
    ("executor-verification-flows.md", "execution/executor-verification-flows.md"),
    ("executor-worked-example.md", "execution/executor-worked-example.md"),
    ("git-integration.md", "execution/git-integration.md"),
    ("ising-experiment-design-example.md", "examples/ising-experiment-design-example.md"),
    ("meta-orchestration.md", "orchestration/meta-orchestration.md"),
    ("model-profile-resolution.md", "orchestration/model-profile-resolution.md"),
    ("model-profiles.md", "orchestration/model-profiles.md"),
    ("planner-approximations.md", "planning/planner-approximations.md"),
    ("planner-conventions.md", "planning/planner-conventions.md"),
    ("planner-iterative.md", "planning/planner-iterative.md"),
    ("planner-scope-examples.md", "planning/planner-scope-examples.md"),
    ("planner-tdd.md", "planning/planner-tdd.md"),
    ("planning-config.md", "planning/planning-config.md"),
    ("questioning.md", "research/questioning.md"),
    ("research-modes.md", "research/research-modes.md"),
    ("researcher-shared.md", "research/researcher-shared.md"),
    ("shared-protocols.md", "shared/shared-protocols.md"),
    ("tool-integration.md", "tooling/tool-integration.md"),
    ("ui-brand.md", "ui/ui-brand.md"),
]

# Files that moved from specs/references/ to domains/physics/
MOVED_TO_PHYSICS = [
    ("bibtex-standards.md", "publication/bibtex-standards.md"),
    ("code-testing-physics.md", "verification/core/code-testing-physics.md"),
    ("computational-verification-templates.md", "verification/core/computational-verification-templates.md"),
    ("conventions-quick-reference.md", "conventions/conventions-quick-reference.md"),
    ("error-propagation-protocol.md", "protocols/error-propagation-protocol.md"),
    ("figure-generation-templates.md", "publication/figure-generation-templates.md"),
    ("hypothesis-driven-research.md", "protocols/hypothesis-driven-research.md"),
    ("llm-errors-core.md", "verification/errors/llm-errors-core.md"),
    ("llm-errors-deep.md", "verification/errors/llm-errors-deep.md"),
    ("llm-errors-extended.md", "verification/errors/llm-errors-extended.md"),
    ("llm-errors-field-theory.md", "verification/errors/llm-errors-field-theory.md"),
    ("llm-errors-traceability.md", "verification/errors/llm-errors-traceability.md"),
    ("llm-physics-errors.md", "verification/errors/llm-physics-errors.md"),
    ("paper-quality-scoring.md", "publication/paper-quality-scoring.md"),
    ("publication-pipeline-modes.md", "publication/publication-pipeline-modes.md"),
    ("reproducibility.md", "protocols/reproducibility.md"),
    ("subfield-convention-defaults.md", "conventions/subfield-convention-defaults.md"),
    ("verification-core.md", "verification/core/verification-core.md"),
    ("verification-domain-algebraic-qft.md", "verification/domains/verification-domain-algebraic-qft.md"),
    ("verification-domain-amo.md", "verification/domains/verification-domain-amo.md"),
    ("verification-domain-astrophysics.md", "verification/domains/verification-domain-astrophysics.md"),
    ("verification-domain-condmat.md", "verification/domains/verification-domain-condmat.md"),
    ("verification-domain-fluid-plasma.md", "verification/domains/verification-domain-fluid-plasma.md"),
    ("verification-domain-gr-cosmology.md", "verification/domains/verification-domain-gr-cosmology.md"),
    ("verification-domain-mathematical-physics.md", "verification/domains/verification-domain-mathematical-physics.md"),
    ("verification-domain-nuclear-particle.md", "verification/domains/verification-domain-nuclear-particle.md"),
    ("verification-domain-qft.md", "verification/domains/verification-domain-qft.md"),
    ("verification-domain-quantum-info.md", "verification/domains/verification-domain-quantum-info.md"),
    ("verification-domain-soft-matter.md", "verification/domains/verification-domain-soft-matter.md"),
    ("verification-domain-statmech.md", "verification/domains/verification-domain-statmech.md"),
    ("verification-domain-string-field-theory.md", "verification/domains/verification-domain-string-field-theory.md"),
    ("verification-gap-analysis.md", "verification/audits/verification-gap-analysis.md"),
    ("verification-gap-summary.md", "verification/audits/verification-gap-summary.md"),
    ("verification-hierarchy-mapping.md", "verification/meta/verification-hierarchy-mapping.md"),
    ("verification-independence.md", "verification/meta/verification-independence.md"),
    ("verification-numerical.md", "verification/core/verification-numerical.md"),
    ("verification-patterns.md", "verification/core/verification-patterns.md"),
    ("verification-quick-reference.md", "verification/core/verification-quick-reference.md"),
    ("verifier-profile-checks.md", "verification/meta/verifier-profile-checks.md"),
    ("verifier-worked-examples.md", "verification/examples/verifier-worked-examples.md"),
]


def test_references_root_has_no_physics_files() -> None:
    """After migration, specs/references root should have no physics .md files."""
    root_markdown = {path.name for path in REFERENCES_DIR.glob("*.md")}
    # physics-subfields.md and README.md moved to domains/physics/
    assert "physics-subfields.md" not in root_markdown
    assert "README.md" not in root_markdown


def test_references_top_level_directories_are_domain_agnostic() -> None:
    actual_dirs = {path.name for path in REFERENCES_DIR.iterdir() if path.is_dir()}
    assert EXPECTED_AGNOSTIC_DIRS <= actual_dirs
    # Physics dirs should NOT be in specs/references anymore
    for physics_dir in ("protocols", "subfields", "publication", "conventions"):
        assert physics_dir not in actual_dirs


def test_physics_domain_directories_exist() -> None:
    actual_dirs = {path.name for path in PHYSICS_DIR.iterdir() if path.is_dir()}
    assert EXPECTED_PHYSICS_DIRS <= actual_dirs


def test_references_nested_directories_exist() -> None:
    template_dirs = {path.name for path in (REFERENCES_DIR / "templates").iterdir() if path.is_dir()}
    assert template_dirs == EXPECTED_TEMPLATE_DIRS


def test_physics_verification_directories_exist() -> None:
    verification_dirs = {path.name for path in (PHYSICS_DIR / "verification").iterdir() if path.is_dir()}
    assert EXPECTED_VERIFICATION_DIRS <= verification_dirs


@pytest.mark.parametrize(("old_rel", "new_rel"), MOVED_AGNOSTIC_FILES)
def test_moved_agnostic_files_exist_in_new_home(old_rel: str, new_rel: str) -> None:
    assert not (REFERENCES_DIR / old_rel).exists(), old_rel
    assert (REFERENCES_DIR / new_rel).exists(), new_rel


@pytest.mark.parametrize(("old_rel", "new_rel"), MOVED_TO_PHYSICS)
def test_physics_files_exist_in_domain_pack(old_rel: str, new_rel: str) -> None:
    # Not in specs/references anymore (not even in subdirs)
    assert not (REFERENCES_DIR / old_rel).exists(), f"still in refs root: {old_rel}"
    # Now lives in domains/physics/
    assert (PHYSICS_DIR / new_rel).exists(), f"missing in physics pack: {new_rel}"


def test_deleted_decimal_phase_reference_is_gone() -> None:
    assert not (REFERENCES_DIR / "decimal-phase-calculation.md").exists()


def test_insert_phase_workflow_points_to_merged_decimal_phase_section() -> None:
    content = (REPO_ROOT / "src/grd/specs/workflows/insert-phase.md").read_text(encoding="utf-8")
    assert "references/decimal-phase-calculation.md" not in content
    assert "references/orchestration/agent-infrastructure.md" in content
    assert "Decimal Phase Calculation" in content


def test_research_mapper_references_use_renamed_template_tree() -> None:
    agent = (REPO_ROOT / "src/grd/agents/grd-research-mapper.md").read_text(encoding="utf-8")
    workflow = (REPO_ROOT / "src/grd/specs/workflows/map-research.md").read_text(encoding="utf-8")

    expected_paths = [
        "references/templates/research-mapper/FORMALISM.md",
        "references/templates/research-mapper/REFERENCES.md",
        "references/templates/research-mapper/ARCHITECTURE.md",
        "references/templates/research-mapper/STRUCTURE.md",
        "references/templates/research-mapper/CONVENTIONS.md",
        "references/templates/research-mapper/VALIDATION.md",
        "references/templates/research-mapper/CONCERNS.md",
    ]
    for token in expected_paths:
        assert token in agent
    assert "references/templates/research-mapper/" in workflow


def test_source_files_only_reference_existing_content_files() -> None:
    """Verify that references/ and domains/physics/ tokens in source point to real files."""
    referenced_refs: set[str] = set()
    referenced_domains: set[str] = set()

    for path in (REPO_ROOT / "src/grd").rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".py"}:
            continue
        # Skip content directories themselves
        if REFERENCES_DIR in path.parents or PHYSICS_DIR in path.parents:
            continue
        content = path.read_text(encoding="utf-8")
        referenced_refs.update(REFERENCE_TOKEN_RE.findall(content))
        referenced_domains.update(DOMAIN_TOKEN_RE.findall(content))

    referenced_refs -= NON_SPEC_REFERENCE_TOKENS
    assert referenced_refs or referenced_domains

    for token in sorted(referenced_refs):
        resolved = REFERENCES_DIR / token.removeprefix("references/")
        assert resolved.is_file(), f"missing ref: {token}"

    for token in sorted(referenced_domains):
        # Resolve {GRD_DOMAIN} placeholder to "physics" (default domain) for file checks
        resolved_token = token.replace("{GRD_DOMAIN}", "physics")
        resolved = REPO_ROOT / "src/grd" / resolved_token
        assert resolved.is_file(), f"missing domain content: {token}"


def test_reference_docs_inline_markdown_targets_resolve() -> None:
    found_tokens: set[str] = set()

    for path in REFERENCES_DIR.rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        for token in INLINE_DOC_TOKEN_RE.findall(content):
            found_tokens.add(token)
            without_anchor = token.split("#", 1)[0]
            if without_anchor.startswith("references/"):
                resolved = REFERENCES_DIR / without_anchor.removeprefix("references/")
            else:
                resolved = (path.parent / without_anchor).resolve()
            assert resolved.is_file(), f"{path.relative_to(REPO_ROOT)} -> {token}"

    # Also check physics domain content
    for path in PHYSICS_DIR.rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        for token in INLINE_DOC_TOKEN_RE.findall(content):
            found_tokens.add(token)
            without_anchor = token.split("#", 1)[0]
            if without_anchor.startswith("references/"):
                # Physics docs may still reference domain-agnostic refs
                resolved = REFERENCES_DIR / without_anchor.removeprefix("references/")
            else:
                resolved = (path.parent / without_anchor).resolve()
            assert resolved.is_file(), f"{path.relative_to(REPO_ROOT)} -> {token}"


def test_no_stale_root_reference_paths_remain_in_prompt_sources() -> None:
    source_roots = [
        REPO_ROOT / "src/grd/agents",
        REPO_ROOT / "src/grd/commands",
        REPO_ROOT / "src/grd/specs/templates",
        REPO_ROOT / "src/grd/specs/workflows",
    ]
    stale_tokens = [
        "references/decimal-phase-calculation.md",
        "references/agent-delegation.md",
        "references/verification-core.md",
        "references/model-profiles.md",
    ]

    for root in source_roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".py"}:
                continue
            content = path.read_text(encoding="utf-8")
            for token in stale_tokens:
                assert token not in content, f"{path.relative_to(REPO_ROOT)} still contains {token}"
