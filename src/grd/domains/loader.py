"""Domain pack discovery, loading, and context management.

Domain packs provide domain-specific content (conventions, protocols, error catalogs,
subfield references, publication config) that the core engine uses at runtime.

Discovery order (last wins):
  1. Bundled packs: src/grd/domains/<name>/
  2. User packs: ~/.grd/domains/<name>/
  3. Project packs: .grd/domain/ (project-local, always wins)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

__all__ = [
    "ContentHealthError",
    "ConventionFieldDef",
    "DomainPack",
    "DomainContext",
    "check_content_health",
    "load_domain",
    "list_available_domains",
    "resolve_domain_pack_path",
]

# ─── Domain Pack Paths ────────────────────────────────────────────────────────

_PKG_DOMAINS_DIR = Path(__file__).resolve().parent
_USER_DOMAINS_DIR = Path.home() / ".grd" / "domains"


def _bundled_domains_dir() -> Path:
    return _PKG_DOMAINS_DIR


def _user_domains_dir() -> Path:
    return _USER_DOMAINS_DIR


def _project_domain_dir(project_root: Path) -> Path:
    return project_root / ".grd" / "domain"


# ─── Data Classes ─────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ConventionFieldDef:
    """A single convention field definition from a domain pack."""

    name: str
    label: str
    description: str = ""
    critical: bool = False
    aliases: tuple[str, ...] = ()
    options: tuple[str, ...] = ()
    value_aliases: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DomainPack:
    """Parsed domain pack metadata from domain.yaml."""

    name: str
    display_name: str
    description: str
    version: int
    pack_path: Path
    conventions_file: str = "conventions/convention-fields.yaml"
    content_dirs: dict[str, str] = field(default_factory=dict)
    publication_config: dict[str, str] = field(default_factory=dict)
    branding: dict[str, str] = field(default_factory=dict)


class DomainContext:
    """Lazily-resolved domain context for a project.

    All domain-specific content is resolved on first access via cached_property,
    keeping startup cheap when domain features aren't used.
    """

    def __init__(self, pack: DomainPack) -> None:
        self._pack = pack

    @property
    def name(self) -> str:
        return self._pack.name

    @property
    def display_name(self) -> str:
        return self._pack.display_name

    @property
    def pack_path(self) -> Path:
        return self._pack.pack_path

    @cached_property
    def convention_fields(self) -> list[ConventionFieldDef]:
        """Load convention field definitions from the domain pack."""
        conv_path = self._pack.pack_path / self._pack.conventions_file
        if not conv_path.is_file():
            return []
        try:
            data = yaml.safe_load(conv_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            logger.warning("Failed to load convention fields from %s: %s", conv_path, exc)
            return []
        if not isinstance(data, dict):
            return []
        raw_fields = data.get("fields", [])
        if not isinstance(raw_fields, list):
            return []
        result = []
        for entry in raw_fields:
            if not isinstance(entry, dict) or "name" not in entry:
                continue
            aliases = entry.get("aliases", [])
            if isinstance(aliases, str):
                aliases = [aliases]
            value_aliases = entry.get("value_aliases", {})
            if not isinstance(value_aliases, dict):
                value_aliases = {}
            options = entry.get("options", [])
            if isinstance(options, str):
                options = [options]
            result.append(
                ConventionFieldDef(
                    name=entry["name"],
                    label=entry.get("label", entry["name"].replace("_", " ").title()),
                    description=entry.get("description", ""),
                    critical=bool(entry.get("critical", False)),
                    aliases=tuple(aliases),
                    options=tuple(options) if isinstance(options, list) else (),
                    value_aliases=value_aliases,
                )
            )
        return result

    @cached_property
    def known_convention_names(self) -> list[str]:
        """Return canonical convention field names for this domain."""
        return [f.name for f in self.convention_fields]

    @cached_property
    def convention_labels(self) -> dict[str, str]:
        """Return field name → display label mapping."""
        return {f.name: f.label for f in self.convention_fields}

    @cached_property
    def key_aliases(self) -> dict[str, str]:
        """Return alias → canonical key mapping for convention fields."""
        result: dict[str, str] = {}
        for f in self.convention_fields:
            for alias in f.aliases:
                result[alias] = f.name
        return result

    @cached_property
    def value_aliases(self) -> dict[str, dict[str, str]]:
        """Return field → {variant: canonical} value alias mapping."""
        return {f.name: f.value_aliases for f in self.convention_fields if f.value_aliases}

    @cached_property
    def critical_fields(self) -> list[str]:
        """Return convention field names marked as critical."""
        return [f.name for f in self.convention_fields if f.critical]

    @cached_property
    def convention_options(self) -> dict[str, list[str]]:
        """Return field → list of suggested values."""
        return {f.name: list(f.options) for f in self.convention_fields if f.options}

    @cached_property
    def subfield_defaults(self) -> dict[str, dict[str, str]]:
        """Load subfield default conventions from the domain pack."""
        defaults_path = self._pack.pack_path / "conventions" / "subfield-defaults.yaml"
        if not defaults_path.is_file():
            return {}
        try:
            data = yaml.safe_load(defaults_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            logger.warning("Failed to load subfield defaults from %s: %s", defaults_path, exc)
            return {}
        if not isinstance(data, dict):
            return {}
        raw = data.get("subfields", {})
        if not isinstance(raw, dict):
            return {}
        return {str(k): {str(kk): str(vv) for kk, vv in v.items()} for k, v in raw.items() if isinstance(v, dict)}

    def content_dir(self, content_type: str) -> Path | None:
        """Return the resolved path for a declared content type, or None."""
        rel = self._pack.content_dirs.get(content_type)
        if rel is None:
            return None
        return self._pack.pack_path / rel

    @property
    def content_types(self) -> list[str]:
        """Return the list of declared content types."""
        return list(self._pack.content_dirs)

    # Backward-compatible convenience properties for common content types.
    @cached_property
    def protocols_dir(self) -> Path:
        return self.content_dir("protocols") or self._pack.pack_path / "protocols"

    @cached_property
    def errors_dir(self) -> Path:
        return self.content_dir("errors") or self._pack.pack_path / "errors"

    @cached_property
    def error_class_coverage_defs(self) -> list[dict]:
        """Load error class coverage definitions from the domain pack.

        Returns a list of dicts with keys: error_class_id, name, primary_checks, domains.
        Empty list if no coverage file exists (non-physics domains default to empty).
        """
        verification_dir = self.content_dir("verification")
        if verification_dir is None:
            verification_dir = self._pack.pack_path / "verification"
        coverage_path = verification_dir / "error-class-coverage.yaml"
        if not coverage_path.is_file():
            return []
        try:
            data = yaml.safe_load(coverage_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            logger.warning("Failed to load error class coverage from %s: %s", coverage_path, exc)
            return []
        if not isinstance(data, dict):
            return []
        raw = data.get("error_classes", [])
        if not isinstance(raw, list):
            return []
        result = []
        for entry in raw:
            if not isinstance(entry, dict) or "error_class_id" not in entry:
                continue
            result.append({
                "error_class_id": int(entry["error_class_id"]),
                "name": str(entry.get("name", "")),
                "primary_checks": list(entry.get("primary_checks", [])),
                "domains": list(entry.get("domains", [])),
            })
        return result

    @cached_property
    def seed_patterns(self) -> list[dict]:
        """Load bootstrap seed patterns from the domain pack.

        Returns a list of dicts matching the bootstrap pattern schema.
        Empty list if no seed file exists.
        """
        seed_path = self._pack.pack_path / "patterns" / "seed-patterns.yaml"
        if not seed_path.is_file():
            return []
        try:
            data = yaml.safe_load(seed_path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError) as exc:
            logger.warning("Failed to load seed patterns from %s: %s", seed_path, exc)
            return []
        if not isinstance(data, dict):
            return []
        raw = data.get("patterns", [])
        if not isinstance(raw, list):
            return []
        return [entry for entry in raw if isinstance(entry, dict)]

    @cached_property
    def subfields_dir(self) -> Path:
        return self.content_dir("subfields") or self._pack.pack_path / "subfields"


# ─── Health Check ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ContentHealthError:
    """A single content directory health-check failure."""

    content_type: str
    expected_path: Path
    message: str


def check_content_health(ctx: DomainContext) -> list[ContentHealthError]:
    """Validate that all declared content directories exist.

    Returns a list of errors (empty list means healthy).
    """
    errors: list[ContentHealthError] = []
    for ctype in ctx.content_types:
        path = ctx.content_dir(ctype)
        if path is None:
            continue
        if not path.is_dir():
            errors.append(
                ContentHealthError(
                    content_type=ctype,
                    expected_path=path,
                    message=f"Declared content directory '{ctype}' not found: {path}",
                )
            )
    return errors


# ─── Loading ──────────────────────────────────────────────────────────────────


_LEGACY_DIR_FIELDS = {
    "subfields_dir": "subfields",
    "protocols_dir": "protocols",
    "errors_dir": "errors",
}


def _parse_content_dirs(data: dict) -> dict[str, str]:
    """Build content_dirs from the ``content`` section or legacy ``*_dir`` fields.

    Prefers the new ``content`` mapping when present.  Falls back to legacy
    per-type ``subfields_dir`` / ``protocols_dir`` / ``errors_dir`` keys for
    backward compatibility with older domain.yaml files.
    """
    content_section = data.get("content")
    if isinstance(content_section, dict):
        return {str(k): str(v) for k, v in content_section.items()}

    # Legacy: individual *_dir fields
    dirs: dict[str, str] = {}
    for legacy_key, content_type in _LEGACY_DIR_FIELDS.items():
        if legacy_key in data:
            dirs[content_type] = str(data[legacy_key])
    return dirs


def _parse_domain_yaml(pack_path: Path) -> DomainPack:
    """Parse domain.yaml from a pack directory."""
    domain_yaml = pack_path / "domain.yaml"
    if not domain_yaml.is_file():
        raise FileNotFoundError(f"No domain.yaml found in {pack_path}")
    data = yaml.safe_load(domain_yaml.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"domain.yaml in {pack_path} must be a YAML mapping")
    pub = data.get("publication", {})
    if not isinstance(pub, dict):
        pub = {}
    branding = data.get("branding", {})
    if not isinstance(branding, dict):
        branding = {}
    return DomainPack(
        name=str(data.get("name", pack_path.name)),
        display_name=str(data.get("display_name", data.get("name", pack_path.name))),
        description=str(data.get("description", "")),
        version=int(data.get("version", 1)),
        pack_path=pack_path,
        conventions_file=str(data.get("conventions_file", "conventions/convention-fields.yaml")),
        content_dirs=_parse_content_dirs(data),
        publication_config=pub,
        branding=branding,
    )


def resolve_domain_pack_path(domain_name: str, project_root: Path | None = None) -> Path | None:
    """Find the path to a named domain pack, using discovery order."""
    # Project-local override
    if project_root:
        project_domain = _project_domain_dir(project_root)
        if project_domain.is_dir() and (project_domain / "domain.yaml").is_file():
            return project_domain

    # User domains
    user_pack = _user_domains_dir() / domain_name
    if user_pack.is_dir() and (user_pack / "domain.yaml").is_file():
        return user_pack

    # Bundled domains
    bundled_pack = _bundled_domains_dir() / domain_name
    if bundled_pack.is_dir() and (bundled_pack / "domain.yaml").is_file():
        return bundled_pack

    return None


def load_domain(domain_name: str, project_root: Path | None = None) -> DomainContext | None:
    """Load a domain pack by name, returning a lazy DomainContext.

    Returns None if the domain pack is not found.
    """
    pack_path = resolve_domain_pack_path(domain_name, project_root)
    if pack_path is None:
        return None
    try:
        pack = _parse_domain_yaml(pack_path)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        logger.warning("Failed to load domain pack '%s' from %s: %s", domain_name, pack_path, exc)
        return None
    return DomainContext(pack)


def list_available_domains() -> list[str]:
    """List all available domain pack names (bundled + user)."""
    names: set[str] = set()
    for search_dir in (_bundled_domains_dir(), _user_domains_dir()):
        if not search_dir.is_dir():
            continue
        for child in search_dir.iterdir():
            if child.is_dir() and (child / "domain.yaml").is_file():
                names.add(child.name)
    return sorted(names)
