"""MCP server for the canonical GRD skill index.

Reads shared skill definitions from the GRD registry and provides discovery,
content retrieval, auto-routing, and prompt injection support. Runtime
adapters may project different installed or discoverable surfaces, but they
all derive from this shared index.

Usage:
    python -m grd.mcp.servers.skills_server
    # or via entry point:
    grd-mcp-skills
"""

import dataclasses
import logging
import re
import sys
from collections.abc import Callable
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from grd import registry as content_registry
from grd.adapters.tool_names import canonical
from grd.command_labels import rewrite_runtime_command_surfaces
from grd.core.errors import GRDError
from grd.core.observability import grd_span
from grd.mcp.servers import parse_frontmatter_safe, stable_mcp_error, stable_mcp_response

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(name)s %(levelname)s: %(message)s")
logger = logging.getLogger("grd-skills")

mcp = FastMCP("grd-skills")

_CONTRACT_REFERENCE_NAMES = {
    "contract-results-schema.md",
    "peer-review-reliability.md",
    "peer-review-panel.md",
    "reproducibility-manifest.md",
    "summary.md",
    "verification-report.md",
}

_SPEC_ROOT = content_registry.SPECS_DIR.resolve()
_AGENT_ROOT = content_registry.AGENTS_DIR.resolve()
_COMMAND_ROOT = content_registry.COMMANDS_DIR.resolve()
_REPO_ROOT = _SPEC_ROOT.parents[2]
_SPEC_RELATIVE_REFERENCE_PREFIXES = (
    "references/",
    "workflows/",
    "templates/",
    "bundles/",
    "shared/",
    "domains/",
    "execution/",
    "verification/",
    "conventions/",
    "research/",
    "publication/",
    "protocols/",
    "subfields/",
    "orchestration/",
)
_MARKDOWN_REFERENCE_RE = re.compile(
    r"(?P<path>(?:@?\{GRD_(?:INSTALL|AGENTS)_DIR\}/|(?:\.\./|\.\/)?"
    r"(?:references|workflows|templates|agents|commands|bundles|shared|domains|execution|verification|conventions|research|publication|protocols|subfields|orchestration|GRD|src/grd)/)"
    r"[^\s`\"')]+?\.md)"
)


def _load_skill_index() -> list[content_registry.SkillDef]:
    """Load the canonical registry/MCP skill index from shared commands and agents."""
    return [content_registry.get_skill(name) for name in content_registry.list_skills()]


def _resolve_skill(name: str) -> content_registry.SkillDef | None:
    """Resolve a public label, canonical skill name, or registry key to a skill record."""
    try:
        return content_registry.get_skill(name)
    except KeyError:
        return None


def _public_skill(skill: content_registry.SkillDef) -> dict[str, str]:
    return {
        "name": skill.name,
        "category": skill.category,
        "description": skill.description,
    }


def _skill_index_label(skill: content_registry.SkillDef) -> str:
    """Render a canonical skill label for the shared MCP surface."""
    return skill.name


def _canonicalize_command_surface(content: str) -> str:
    """Rewrite runtime-facing command examples to canonical ``grd-*`` names."""
    return rewrite_runtime_command_surfaces(content, canonical="skill")


def _portable_skill_content(content: str) -> str:
    """Keep skill content portable while normalizing runtime command references."""
    content = re.sub(r"(?<!@)\{GRD_INSTALL_DIR\}/", "@{GRD_INSTALL_DIR}/", content)
    content = re.sub(r"(?<!@)\{GRD_AGENTS_DIR\}/", "@{GRD_AGENTS_DIR}/", content)
    content = re.sub(r"(?<!@)\{GRD_INSTALL_DIR\}(?=[^\s/`\"')])", "@{GRD_INSTALL_DIR}/", content)
    content = re.sub(r"(?<!@)\{GRD_AGENTS_DIR\}(?=[^\s/`\"')])", "@{GRD_AGENTS_DIR}/", content)
    return _canonicalize_command_surface(content)


def _normalize_allowed_tools(tools: list[str]) -> list[str]:
    """Normalize allowed tools into a stable, deduplicated canonical list."""
    normalized: list[str] = []
    seen: set[str] = set()
    for tool in tools:
        canonical_name = canonical(tool.strip())
        if not canonical_name or canonical_name in seen:
            continue
        seen.add(canonical_name)
        normalized.append(canonical_name)
    return normalized


def _portable_reference_path(raw_path: str, *, base_path: Path | None = None) -> tuple[str, Path | None] | None:
    """Return a stable reference path plus its local file path, if resolvable."""
    candidate = raw_path.rstrip(".,:;")
    if not candidate:
        return None

    def _normalize_resolved_path(resolved: Path) -> tuple[str, Path] | None:
        resolved = resolved.resolve()
        if not resolved.is_file():
            return None
        try:
            rel = resolved.relative_to(_SPEC_ROOT)
        except ValueError:
            pass
        else:
            portable = f"@{{GRD_INSTALL_DIR}}/{rel.as_posix()}"
            return portable, resolved
        try:
            rel = resolved.relative_to(_AGENT_ROOT)
        except ValueError:
            pass
        else:
            portable = f"@{{GRD_AGENTS_DIR}}/{rel.as_posix()}"
            return portable, resolved
        try:
            rel = resolved.relative_to(_COMMAND_ROOT)
        except ValueError:
            return None
        portable = f"@{{GRD_INSTALL_DIR}}/commands/{rel.as_posix()}"
        return portable, resolved

    if candidate.startswith("@{GRD_INSTALL_DIR}/") or candidate.startswith("{GRD_INSTALL_DIR}/"):
        relative = candidate.split("}/", 1)[1]
        resolved = _SPEC_ROOT / relative if not relative.startswith("commands/") else _COMMAND_ROOT / relative.removeprefix("commands/")
        normalized = _normalize_resolved_path(resolved)
        return normalized

    if candidate.startswith("@{GRD_AGENTS_DIR}/") or candidate.startswith("{GRD_AGENTS_DIR}/"):
        relative = candidate.split("}/", 1)[1]
        resolved = _AGENT_ROOT / relative
        normalized = _normalize_resolved_path(resolved)
        return normalized

    raw_path_obj = Path(candidate)
    if raw_path_obj.is_absolute():
        normalized = _normalize_resolved_path(raw_path_obj)
        if normalized is not None:
            return normalized
        return None

    if candidate.startswith(_SPEC_RELATIVE_REFERENCE_PREFIXES):
        resolved = _SPEC_ROOT / candidate
        normalized = _normalize_resolved_path(resolved)
        return normalized

    if candidate.startswith("commands/"):
        relative = candidate.removeprefix("commands/")
        resolved = _COMMAND_ROOT / relative
        normalized = _normalize_resolved_path(resolved)
        return normalized

    if candidate.startswith("agents/"):
        relative = candidate.removeprefix("agents/")
        resolved = _AGENT_ROOT / relative
        normalized = _normalize_resolved_path(resolved)
        return normalized

    if candidate.startswith((".grd/", "@.grd/")):
        project_path = candidate.removeprefix("@")
        return f"@{project_path}", None

    if candidate.startswith("src/grd/"):
        resolved = (_REPO_ROOT / candidate).resolve()
        normalized = _normalize_resolved_path(resolved)
        if normalized is not None:
            return normalized
        return candidate, None

    if base_path is not None:
        resolved = (base_path.parent / candidate).resolve()
        normalized = _normalize_resolved_path(resolved)
        if normalized is not None:
            return normalized

    return None


def _reference_kind(path: str) -> str:
    if path.startswith("@.grd/"):
        return "project"
    if path.startswith("@{GRD_AGENTS_DIR}/"):
        return "agent"
    if path.startswith("@{GRD_INSTALL_DIR}/commands/"):
        return "command"
    if path.startswith("@{GRD_INSTALL_DIR}/templates/"):
        return "template"
    if path.startswith("@{GRD_INSTALL_DIR}/workflows/"):
        return "workflow"
    if path.startswith("@{GRD_INSTALL_DIR}/bundles/"):
        return "bundle"
    if path.startswith("@{GRD_INSTALL_DIR}/references/"):
        return "reference"
    return "spec"


def _extract_referenced_files(content: str, *, source_path: Path | None = None) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    seen: set[str] = set()
    visited_docs: set[str] = set()

    def _collect(markdown: str, *, current_path: Path | None) -> None:
        for match in _MARKDOWN_REFERENCE_RE.finditer(markdown):
            normalized = _portable_reference_path(match.group("path"), base_path=current_path)
            if normalized is None:
                continue
            path, referenced_path = normalized
            if path not in seen:
                seen.add(path)
                references.append({"path": path, "kind": _reference_kind(path)})
            if path in visited_docs:
                continue
            visited_docs.add(path)
            if referenced_path is None or referenced_path.suffix != ".md" or not referenced_path.exists():
                continue
            try:
                nested = _portable_skill_content(referenced_path.read_text(encoding="utf-8"))
            except OSError:
                continue
            _collect(nested, current_path=referenced_path)

    _collect(content, current_path=source_path)
    return references


def _is_schema_reference(path: str) -> bool:
    name = Path(path).name
    return name.endswith("-schema.md") or name in {
        "summary.md",
        "verification-report.md",
        "contract-results-schema.md",
    }


def _is_contract_reference(path: str) -> bool:
    name = Path(path).name
    return _is_schema_reference(path) or name in _CONTRACT_REFERENCE_NAMES


def _load_reference_document(path: str, *, kind: str) -> dict[str, object]:
    document: dict[str, object] = {
        "path": path,
        "name": Path(path).name,
        "kind": kind,
    }
    resolved = _portable_reference_path(path)
    reference_path = resolved[1] if resolved is not None else None
    if reference_path is None:
        document["error"] = "Reference file not found"
        return document

    if not reference_path.is_file():
        document["error"] = "Reference file not found"
        return document

    try:
        content = _portable_skill_content(reference_path.read_text(encoding="utf-8"))
    except OSError as exc:
        document["error"] = str(exc)
        return document

    frontmatter, body = parse_frontmatter_safe(content)
    document["content"] = content
    document["body"] = body
    if frontmatter:
        document["frontmatter"] = frontmatter
    return document


def _expanded_reference_documents(
    referenced_files: list[dict[str, str]],
    *,
    predicate: Callable[[str], bool],
) -> tuple[list[str], list[dict[str, object]]]:
    selected = [entry for entry in referenced_files if predicate(entry["path"])]
    return (
        [entry["path"] for entry in selected],
        [_load_reference_document(entry["path"], kind=entry["kind"]) for entry in selected],
    )


@mcp.tool()
def list_skills(category: str | None = None) -> dict:
    """List canonical GRD skills with optional category filter.

    Skills are organized by category: execution, planning, verification,
    debugging, research, paper, analysis, diagnostics, management, etc.

    Args:
        category: Optional category to filter by.
    """
    with grd_span("mcp.skills.list", category=category or ""):
        try:
            skills = [_public_skill(skill) for skill in _load_skill_index()]
            all_categories = sorted({s["category"] for s in skills})
            if category:
                skills = [s for s in skills if s["category"] == category]

            categories = all_categories
            return stable_mcp_response(
                {
                    "skills": skills,
                    "count": len(skills),
                    "categories": categories,
                }
            )
        except (GRDError, OSError, ValueError, TimeoutError) as e:
            return stable_mcp_error(e)
        except Exception as e:  # pragma: no cover - defensive envelope
            return stable_mcp_error(e)


@mcp.tool()
def get_skill(name: str) -> dict:
    """Get the full content of a canonical skill definition.

    Returns the skill prompt and metadata for injection into agent context.

    Args:
        name: Skill name (e.g., "grd-execute-phase", "grd-plan-phase").
    """
    with grd_span("mcp.skills.get", skill_name=name):
        try:
            skill = _resolve_skill(name)
            if skill is None:
                return stable_mcp_response(
                    {"available": [entry.name for entry in _load_skill_index()[:10]]},
                    error=f"Skill {name!r} not found",
                )

            content = _portable_skill_content(skill.content)
            referenced_files = _extract_referenced_files(content, source_path=Path(skill.path))
            template_references = [entry["path"] for entry in referenced_files if entry["kind"] == "template"]
            schema_references, schema_documents = _expanded_reference_documents(
                referenced_files,
                predicate=_is_schema_reference,
            )
            contract_references, contract_documents = _expanded_reference_documents(
                referenced_files,
                predicate=_is_contract_reference,
            )
            payload = {
                "name": skill.name,
                "category": skill.category,
                "content": content,
                "file_count": 1,
                "referenced_files": referenced_files,
                "reference_count": len(referenced_files),
                "template_references": template_references,
                "schema_references": schema_references,
                "schema_documents": schema_documents,
                "contract_references": contract_references,
                "contract_documents": contract_documents,
                "loading_hint": (
                    "schema_documents and contract_documents already include the expanded canonical bodies. Use referenced_files for any additional workflow/context docs."
                    if referenced_files
                    else "No external markdown dependencies detected in the canonical skill body."
                ),
            }
            if skill.source_kind == "command":
                command = content_registry.get_command(skill.registry_name)
                allowed_tools = _normalize_allowed_tools(command.allowed_tools)
                payload.update(
                    {
                        "context_mode": command.context_mode,
                        "argument_hint": command.argument_hint,
                        "review_contract": (
                            dataclasses.asdict(command.review_contract) if command.review_contract is not None else None
                        ),
                        "allowed_tools_surface": "command.allowed-tools",
                    }
                )
                payload["allowed_tools"] = allowed_tools
            elif skill.source_kind == "agent":
                agent = content_registry.get_agent(skill.registry_name)
                payload["allowed_tools"] = _normalize_allowed_tools(agent.tools)
                payload["allowed_tools_surface"] = "agent.tools"
            return stable_mcp_response(payload)
        except (GRDError, OSError, ValueError, TimeoutError) as e:
            return stable_mcp_error(e)
        except Exception as e:  # pragma: no cover - defensive envelope
            return stable_mcp_error(e)


@mcp.tool()
def route_skill(task_description: str) -> dict:
    """Auto-select the best GRD skill for a given task description.

    Uses keyword matching to suggest the most relevant skill(s) for
    the described task.

    Args:
        task_description: Natural language description of what needs to be done.
    """
    with grd_span("mcp.skills.route"):
        try:
            skills = _load_skill_index()
            if not skills:
                return stable_mcp_response({"suggestion": None}, error="No skills available")
            available_names = {skill.name for skill in skills}
            normalized_task = re.sub(r"[^a-z0-9\s-]", "", task_description.lower()).strip()

            if "grd-suggest-next" in available_names and any(
                phrase in normalized_task
                for phrase in (
                    "what should i do next",
                    "what do i do next",
                    "what next",
                    "next step",
                    "next steps",
                )
            ):
                return stable_mcp_response(
                    {
                        "suggestion": "grd-suggest-next",
                        "confidence": 0.95,
                        "alternatives": [
                            name for name in ("grd-progress", "grd-plan-phase") if name in available_names
                        ],
                        "task_description": task_description,
                    }
                )

            # Keyword scoring
            words = set(normalized_task.split())

            # Direct command mentions (e.g., "execute phase", "plan phase")
            command_keywords: dict[str, list[str]] = {
                "grd-execute-phase": ["execute", "run", "implement", "build", "code"],
                "grd-plan-phase": ["plan", "design", "architect", "strategy"],
                "grd-verify-work": ["verify", "check", "validate", "test"],
                "grd-debug": ["debug", "fix", "investigate", "error", "bug"],
                "grd-new-project": ["new", "create", "initialize", "start", "project"],
                "grd-write-paper": ["write", "paper", "draft", "manuscript"],
                "grd-peer-review": ["peer", "referee", "reviewer", "manuscript"],
                "grd-literature-review": ["literature", "review", "papers", "citations", "references"],
                "grd-progress": ["progress", "status", "where", "current"],
                "grd-derive-equation": ["derive", "equation", "calculate", "computation"],
                "grd-discover": ["discover", "explore", "survey", "methods"],
                "grd-health": ["health", "diagnostic", "doctor"],
                "grd-validate-conventions": ["convention", "conventions", "notation"],
                "grd-quick": ["quick", "fast", "simple"],
                "grd-resume-work": ["resume", "continue", "pick up"],
                "grd-pause-work": ["pause", "stop", "break"],
                "grd-export": ["export", "html", "latex", "zip"],
                "grd-slides": ["slides", "slide", "presentation", "deck", "talk", "seminar", "beamer", "pptx"],
                "grd-dimensional-analysis": ["dimensional", "dimensions", "units"],
                "grd-limiting-cases": ["limiting", "limit", "asymptotic"],
                "grd-sensitivity-analysis": ["sensitivity", "parameter", "uncertainty"],
                "grd-numerical-convergence": ["convergence", "numerical", "accuracy"],
            }

            scored: list[tuple[int, str]] = []
            for skill_name, keywords in command_keywords.items():
                if skill_name not in available_names:
                    continue
                score = 0
                for kw in keywords:
                    normalized_kw = re.sub(r"[^a-z0-9\s-]", "", kw.lower()).strip()
                    if not normalized_kw:
                        continue
                    if " " in normalized_kw:
                        if normalized_kw in normalized_task:
                            score += 2
                    elif normalized_kw in words:
                        score += 1
                if score > 0:
                    scored.append((score, skill_name))

            scored.sort(key=lambda x: -x[0])

            if scored:
                best = scored[0][1]
                alternatives = [s for _, s in scored[1:4]]
                return stable_mcp_response(
                    {
                        "suggestion": best,
                        "confidence": min(scored[0][0] / 3.0, 1.0),
                        "alternatives": alternatives,
                        "task_description": task_description,
                    }
                )

            fallback = "grd-help" if "grd-help" in available_names else skills[0].name

            return stable_mcp_response(
                {
                    "suggestion": fallback,
                    "confidence": 0.1,
                    "alternatives": [name for name in ("grd-progress", "grd-discover") if name in available_names],
                    "task_description": task_description,
                    "note": "No strong match found — try your runtime's GRD help command for available commands",
                }
            )
        except (GRDError, OSError, ValueError, TimeoutError) as e:
            return stable_mcp_error(e)
        except Exception as e:  # pragma: no cover - defensive envelope
            return stable_mcp_error(e)


@mcp.tool()
def get_skill_index() -> dict:
    """Return a formatted canonical skill index for actor prompt injection.

    Returns a compact summary suitable for injecting into LLM context
    to make it aware of available GRD capabilities.
    """
    with grd_span("mcp.skills.index"):
        try:
            skills = _load_skill_index()
            by_category: dict[str, list[str]] = {}
            for skill in skills:
                cat = skill.category
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(_skill_index_label(skill))

            lines = ["# Available GRD Skills", ""]
            for cat in sorted(by_category):
                lines.append(f"## {cat.title()}")
                for name in sorted(by_category[cat]):
                    lines.append(f"- {name}")
                lines.append("")

            return stable_mcp_response(
                {
                    "index_text": "\n".join(lines),
                    "total_skills": len(skills),
                    "categories": sorted(by_category),
                }
            )
        except (GRDError, OSError, ValueError, TimeoutError) as e:
            return stable_mcp_error(e)
        except Exception as e:  # pragma: no cover - defensive envelope
            return stable_mcp_error(e)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the grd-skills MCP server."""
    from grd.mcp.servers import run_mcp_server

    run_mcp_server(mcp, "GRD Skills MCP Server")


if __name__ == "__main__":
    main()
