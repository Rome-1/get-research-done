"""Project template discovery and stamping.

Templates live under ``src/grd/specs/templates/project-templates/<name>/``.
Each template directory contains a ``template.json`` manifest and a set of
files (PROJECT.md, CONVENTIONS.md, ROADMAP.md, state.json) that are copied
into the target project's ``.grd/`` planning directory.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from grd.core.constants import PLANNING_DIR_NAME
from grd.specs import SPECS_DIR

_TEMPLATES_DIR = SPECS_DIR / "templates" / "project-templates"


@dataclass(frozen=True)
class ProjectTemplate:
    """Metadata for a project template."""

    name: str
    description: str
    domain: str
    project_type: str
    phases: int
    claims: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    path: Path = field(default=Path("."))

    @classmethod
    def from_dir(cls, template_dir: Path) -> ProjectTemplate:
        """Load a template from its directory."""
        manifest_path = template_dir / "template.json"
        if not manifest_path.exists():
            raise FileNotFoundError(
                f"Template directory {template_dir} has no template.json"
            )
        with open(manifest_path) as f:
            data = json.load(f)
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            domain=data.get("domain", ""),
            project_type=data.get("project_type", ""),
            phases=data.get("phases", 1),
            claims=data.get("claims", []),
            files=data.get("files", []),
            path=template_dir,
        )


def list_project_templates() -> list[ProjectTemplate]:
    """Return all available project templates."""
    if not _TEMPLATES_DIR.is_dir():
        return []
    templates = []
    for entry in sorted(_TEMPLATES_DIR.iterdir()):
        if entry.is_dir() and (entry / "template.json").exists():
            templates.append(ProjectTemplate.from_dir(entry))
    return templates


def get_project_template(name: str) -> ProjectTemplate:
    """Look up a project template by name.

    Raises ``KeyError`` if no template with that name exists.
    """
    template_dir = _TEMPLATES_DIR / name
    if not template_dir.is_dir() or not (template_dir / "template.json").exists():
        available = [t.name for t in list_project_templates()]
        hint = f" Available: {', '.join(available)}" if available else ""
        raise KeyError(f"Unknown project template {name!r}.{hint}")
    return ProjectTemplate.from_dir(template_dir)


@dataclass(frozen=True)
class StampResult:
    """Result of stamping a project template."""

    template: str
    files_written: list[str]
    planning_dir: str
    skipped: list[str] = field(default_factory=list)


def stamp_project_template(
    cwd: Path,
    template_name: str,
    *,
    force: bool = False,
) -> StampResult:
    """Copy a project template's files into the target project's .grd/ directory.

    Parameters
    ----------
    cwd:
        Target project root directory.
    template_name:
        Name of the template to stamp (must exist under project-templates/).
    force:
        If True, overwrite existing files. Otherwise skip files that already exist.

    Returns
    -------
    StampResult with the list of files written and any skipped.
    """
    template = get_project_template(template_name)
    planning_dir = cwd / PLANNING_DIR_NAME
    planning_dir.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    files_written: list[str] = []
    skipped: list[str] = []

    for filename in template.files:
        src = template.path / filename
        if not src.exists():
            continue
        dst = planning_dir / filename
        if dst.exists() and not force:
            skipped.append(filename)
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)

        if filename.endswith(".md"):
            content = src.read_text(encoding="utf-8")
            content = content.replace("{{created_date}}", today)
            dst.write_text(content, encoding="utf-8")
        else:
            shutil.copy2(src, dst)

        files_written.append(filename)

    return StampResult(
        template=template_name,
        files_written=files_written,
        planning_dir=str(planning_dir),
        skipped=skipped,
    )
