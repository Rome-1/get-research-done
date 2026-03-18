"""Convention lock management for GRD research projects.

Provides the convention lock system: set/list/diff/check operations,
ASSERT_CONVENTION parsing from LaTeX/Python/Markdown files, key alias
normalization, and value sanitization.

Supports domain-aware conventions via DomainContext (optional).  When a
DomainContext is provided, convention fields, aliases, and labels are resolved
from the domain pack.  When omitted, the built-in physics defaults are used
for backward compatibility.

Key features:
- Key aliases: short aliases (e.g., "metric" -> "metric_signature")
  for CLI ergonomics, loaded from domain packs.
- Value aliases: Normalizes variant notations (e.g., "+---" -> "mostly-minus").
- ASSERT_CONVENTION parsing: Scans file content for convention assertions in
  Markdown/LaTeX/Python comments.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from grd.contracts import ConventionLock
from grd.core.errors import ConventionError
from grd.core.observability import instrument_grd_function

logger = logging.getLogger(__name__)

__all__ = [
    "KNOWN_CONVENTIONS",
    "CONVENTION_LABELS",
    "KEY_ALIASES",
    "VALUE_ALIASES",
    "ConventionSetResult",
    "ConventionEntry",
    "ConventionListResult",
    "ConventionDiff",
    "ConventionDiffResult",
    "ConventionCheckResult",
    "AssertionMismatch",
    "normalize_key",
    "normalize_value",
    "is_bogus_value",
    "sanitize_value",
    "convention_set",
    "convention_list",
    "convention_diff",
    "convention_diff_phases",
    "convention_check",
    "parse_assert_conventions",
    "validate_assertions",
]


# ─── Backward-Compatible Physics Defaults ─────────────────────────────────────
# These are kept for code that imports them directly.  New code should use
# DomainContext instead.

def _load_physics_defaults() -> "DomainContext | None":
    """Lazy-load the bundled physics domain pack for backward compatibility."""
    try:
        from grd.domains.loader import load_domain
        return load_domain("physics")
    except Exception:
        return None


class _LazyPhysicsProxy:
    """Lazy proxy that loads physics domain defaults on first access."""

    def __init__(self) -> None:
        self._ctx: DomainContext | None = None
        self._loaded = False

    def _ensure(self) -> object | None:
        if not self._loaded:
            self._ctx = _load_physics_defaults()
            self._loaded = True
        return self._ctx

    @property
    def known_conventions(self) -> list[str]:
        ctx = self._ensure()
        return ctx.known_convention_names if ctx else []

    @property
    def labels(self) -> dict[str, str]:
        ctx = self._ensure()
        return ctx.convention_labels if ctx else {}

    @property
    def key_aliases(self) -> dict[str, str]:
        ctx = self._ensure()
        return ctx.key_aliases if ctx else {}

    @property
    def value_aliases(self) -> dict[str, dict[str, str]]:
        ctx = self._ensure()
        return ctx.value_aliases if ctx else {}


_PHYSICS = _LazyPhysicsProxy()

# Module-level constants — lazy-evaluated on first access for backward compat.
# These are descriptor-like properties on a module, but since Python doesn't
# support that natively, we use a simple class wrapper.


class _KnownConventions(list):
    """List subclass that lazy-loads from physics domain on first iteration."""

    def __init__(self) -> None:
        super().__init__()
        self._loaded = False

    def _ensure(self) -> None:
        if not self._loaded:
            self.extend(_PHYSICS.known_conventions)
            self._loaded = True

    def __iter__(self):
        self._ensure()
        return super().__iter__()

    def __len__(self):
        self._ensure()
        return super().__len__()

    def __contains__(self, item):
        self._ensure()
        return super().__contains__(item)

    def __getitem__(self, index):
        self._ensure()
        return super().__getitem__(index)

    def __eq__(self, other):
        self._ensure()
        return super().__eq__(other)

    def __repr__(self):
        self._ensure()
        return super().__repr__()

    def copy(self):
        self._ensure()
        return list(self)

    def __bool__(self):
        self._ensure()
        return len(self) > 0

    def __add__(self, other):
        self._ensure()
        return super().__add__(other)


KNOWN_CONVENTIONS: list[str] = _KnownConventions()


class _LazyDict(dict):
    """Dict subclass that lazy-loads from a source on first access."""

    def __init__(self, source_attr: str) -> None:
        super().__init__()
        self._source_attr = source_attr
        self._loaded = False

    def _ensure(self) -> None:
        if not self._loaded:
            self.update(getattr(_PHYSICS, self._source_attr))
            self._loaded = True

    def __getitem__(self, key):
        self._ensure()
        return super().__getitem__(key)

    def get(self, key, default=None):
        self._ensure()
        return super().get(key, default)

    def __contains__(self, key):
        self._ensure()
        return super().__contains__(key)

    def __iter__(self):
        self._ensure()
        return super().__iter__()

    def __len__(self):
        self._ensure()
        return super().__len__()

    def items(self):
        self._ensure()
        return super().items()

    def keys(self):
        self._ensure()
        return super().keys()

    def values(self):
        self._ensure()
        return super().values()

    def __eq__(self, other):
        self._ensure()
        return super().__eq__(other)

    def __repr__(self):
        self._ensure()
        return super().__repr__()

    def copy(self):
        self._ensure()
        return dict(self)

    def __bool__(self):
        self._ensure()
        return len(self) > 0


CONVENTION_LABELS: dict[str, str] = _LazyDict("labels")
KEY_ALIASES: dict[str, str] = _LazyDict("key_aliases")
VALUE_ALIASES: dict[str, dict[str, str]] = _LazyDict("value_aliases")


# Values that should be treated as "unset" (prevent string-vs-null confusion)
_BOGUS_VALUES = frozenset({"", "null", "undefined", "none"})


# ─── Domain-Aware Resolution Helpers ─────────────────────────────────────────


def _resolve_known_conventions(domain_ctx: object | None = None) -> list[str]:
    """Return canonical convention names for the active domain."""
    if domain_ctx is not None:
        return domain_ctx.known_convention_names
    return KNOWN_CONVENTIONS


def _resolve_labels(domain_ctx: object | None = None) -> dict[str, str]:
    """Return convention labels for the active domain."""
    if domain_ctx is not None:
        return domain_ctx.convention_labels
    return CONVENTION_LABELS


def _resolve_key_aliases(domain_ctx: object | None = None) -> dict[str, str]:
    """Return key alias mapping for the active domain."""
    if domain_ctx is not None:
        return domain_ctx.key_aliases
    return KEY_ALIASES


def _resolve_value_aliases(domain_ctx: object | None = None) -> dict[str, dict[str, str]]:
    """Return value alias mapping for the active domain."""
    if domain_ctx is not None:
        return domain_ctx.value_aliases
    return VALUE_ALIASES

# Regex for ASSERT_CONVENTION lines:
#   <!-- ASSERT_CONVENTION: key=value, key=value -->  (Markdown)
#   % ASSERT_CONVENTION: key=value, key=value         (LaTeX)
#   # ASSERT_CONVENTION: key=value, key=value         (Python)
_ASSERT_LINE_RE = re.compile(
    r"^\s*(?:<!--|[%#])\s*ASSERT_CONVENTION[:\s]+(.+?)(?:\s*-->)?\s*$",
    re.MULTILINE,
)
_KV_PAIR_RE = re.compile(r"^(\w+)\s*=\s*(.+)$")


# --- Result Types ---


class ConventionSetResult(BaseModel):
    """Result of setting a convention."""

    model_config = ConfigDict(frozen=True)

    updated: bool
    key: str
    value: str | None = None
    previous: str | None = None
    custom: bool = False
    reason: str | None = None
    hint: str | None = None


class ConventionEntry(BaseModel):
    """A single convention entry in a check result."""

    model_config = ConfigDict(frozen=True)

    key: str
    label: str = ""
    value: str | None = None
    is_set: bool = False
    canonical: bool = True


class ConventionListResult(BaseModel):
    """Result of listing all conventions."""

    model_config = ConfigDict(frozen=True)

    conventions: dict[str, ConventionEntry]
    total: int
    set_count: int
    unset_count: int
    canonical_total: int


class ConventionDiff(BaseModel):
    """A single difference between two convention locks."""

    model_config = ConfigDict(frozen=True)

    key: str
    from_value: str | None = None
    to_value: str | None = None


class ConventionDiffResult(BaseModel):
    """Result of diffing two convention locks."""

    model_config = ConfigDict(frozen=True)

    changed: list[ConventionDiff] = Field(default_factory=list)
    added: list[ConventionDiff] = Field(default_factory=list)
    removed: list[ConventionDiff] = Field(default_factory=list)
    note: str | None = None


class ConventionCheckResult(BaseModel):
    """Result of checking convention completeness."""

    model_config = ConfigDict(frozen=True)

    complete: bool
    missing: list[ConventionEntry]
    set_conventions: list[ConventionEntry]
    custom: list[ConventionEntry]
    total: int
    set_count: int
    missing_count: int
    custom_count: int


class AssertionMismatch(BaseModel):
    """A convention assertion that doesn't match the lock."""

    model_config = ConfigDict(frozen=True)

    file: str
    key: str
    file_value: str
    lock_value: str


# --- Key/Value Normalization ---


def normalize_key(key: str, *, domain_ctx: object | None = None) -> str:
    """Resolve a short/alias key to the canonical convention_lock field name."""
    aliases = _resolve_key_aliases(domain_ctx)
    return aliases.get(key, key)


def normalize_value(canonical_key: str, value: str, *, domain_ctx: object | None = None) -> str:
    """Normalize a convention value for comparison using field-specific aliases."""
    all_aliases = _resolve_value_aliases(domain_ctx)
    aliases = all_aliases.get(canonical_key)
    if not aliases:
        return value
    return aliases.get(value, value)


def is_bogus_value(value: object) -> bool:
    """Return True if the value should be treated as unset."""
    if value is None:
        return True
    return str(value).strip().lower() in _BOGUS_VALUES


def sanitize_value(value: str) -> str:
    """Sanitize a convention value: collapse newlines, strip whitespace.

    Raises ConventionError for empty or bogus values.
    """
    cleaned = re.sub(r"[\r\n]+", " ", value).strip()
    if cleaned.lower() in _BOGUS_VALUES:
        raise ConventionError(
            f"Convention value cannot be empty or bogus ({cleaned!r}). "
            "To clear a convention, set the field to None directly."
        )
    return cleaned


# --- Convention Operations ---


@instrument_grd_function("conventions.set")
def convention_set(
    lock: ConventionLock,
    key: str,
    value: str,
    *,
    force: bool = False,
    domain_ctx: object | None = None,
) -> ConventionSetResult:
    """Set a convention value on the lock.

    If the convention is already set to a different value, requires force=True
    to overwrite (immutability gate).

    When *domain_ctx* is provided, aliases and known fields are resolved from
    the domain pack instead of the built-in physics defaults.

    Returns a ConventionSetResult indicating what happened.

    Raises ConventionError for empty/bogus values.
    """
    cleaned = sanitize_value(value)
    canonical_key = normalize_key(key, domain_ctx=domain_ctx)
    cleaned = normalize_value(canonical_key, cleaned, domain_ctx=domain_ctx)
    known = _resolve_known_conventions(domain_ctx)
    is_custom = canonical_key not in known

    previous = lock.conventions.get(canonical_key)

    # Immutability gate: require force to overwrite existing non-null convention
    if previous is not None and not is_bogus_value(previous) and previous != cleaned and not force:
        return ConventionSetResult(
            updated=False,
            key=canonical_key,
            value=cleaned,
            previous=previous,
            custom=is_custom,
            reason="convention_already_set",
            hint="Use force=True to overwrite an existing convention",
        )

    lock.conventions[canonical_key] = cleaned

    return ConventionSetResult(
        updated=True,
        key=canonical_key,
        value=cleaned,
        previous=previous,
        custom=is_custom,
    )


def convention_list(lock: ConventionLock, *, domain_ctx: object | None = None) -> ConventionListResult:
    """List all conventions with their set/unset status."""
    known = _resolve_known_conventions(domain_ctx)
    labels = _resolve_labels(domain_ctx)
    conventions: dict[str, ConventionEntry] = {}

    # Canonical conventions
    for key in known:
        val = lock.conventions.get(key)
        conventions[key] = ConventionEntry(
            key=key,
            label=labels.get(key, key.replace("_", " ").title()),
            value=val,
            is_set=not is_bogus_value(val),
            canonical=True,
        )

    # Extra conventions (keys in lock.conventions not in the known set)
    for key, val in lock.conventions.items():
        if key in conventions:
            continue
        label = key.replace("_", " ").title()
        conventions[key] = ConventionEntry(
            key=key,
            label=label,
            value=val,
            is_set=not is_bogus_value(val),
            canonical=False,
        )

    set_count = sum(1 for c in conventions.values() if c.is_set)
    total = len(conventions)
    return ConventionListResult(
        conventions=conventions,
        total=total,
        set_count=set_count,
        unset_count=total - set_count,
        canonical_total=len(known),
    )


@instrument_grd_function("conventions.diff")
def convention_diff(lock_a: ConventionLock, lock_b: ConventionLock) -> ConventionDiffResult:
    """Compare two convention locks and return differences."""
    changed: list[ConventionDiff] = []
    added: list[ConventionDiff] = []
    removed: list[ConventionDiff] = []

    all_keys = sorted(set(lock_a.conventions) | set(lock_b.conventions))
    for key in all_keys:
        val_a = lock_a.conventions.get(key)
        val_b = lock_b.conventions.get(key)
        norm_a = normalize_value(key, val_a) if val_a is not None else None
        norm_b = normalize_value(key, val_b) if val_b is not None else None
        if norm_a is None and norm_b is not None:
            added.append(ConventionDiff(key=key, to_value=norm_b))
        elif norm_a is not None and norm_b is None:
            removed.append(ConventionDiff(key=key, from_value=norm_a))
        elif norm_a is not None and norm_b is not None and norm_a != norm_b:
            changed.append(ConventionDiff(key=key, from_value=norm_a, to_value=norm_b))

    return ConventionDiffResult(changed=changed, added=added, removed=removed)


def _extract_phase_conventions(cwd: Path, phase_id: str) -> dict[str, str] | None:
    """Extract convention mentions from a phase's SUMMARY frontmatter and body."""
    from grd.core.frontmatter import FrontmatterParseError, extract_frontmatter
    from grd.core.phases import find_phase

    info = find_phase(cwd, phase_id)
    if not info:
        return None

    phase_dir = cwd / info.directory
    conventions: dict[str, str] = {}

    for summary_name in info.summaries:
        summary_path = phase_dir / summary_name
        if not summary_path.is_file():
            continue

        try:
            content = summary_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        try:
            fm, _body = extract_frontmatter(content)
        except FrontmatterParseError:
            fm = {}

        # Check frontmatter for convention-related fields
        fm_conventions = fm.get("conventions")
        if isinstance(fm_conventions, dict):
            conventions.update({k: str(v) for k, v in fm_conventions.items() if v is not None})
        elif isinstance(fm_conventions, list):
            for conv in fm_conventions:
                match = re.match(r"^([^=:]+?)\s*[=:]\s*(.+)$", str(conv))
                if match:
                    conventions[match.group(1).strip()] = match.group(2).strip()

        fm_lock = fm.get("convention_lock")
        if isinstance(fm_lock, dict):
            # New format: conventions dict
            conv_data = fm_lock.get("conventions")
            if isinstance(conv_data, dict):
                conventions.update({k: str(v) for k, v in conv_data.items() if v is not None})
            # Legacy: flat physics fields
            for k, v in fm_lock.items():
                if k not in ("conventions", "custom_conventions"):
                    if v is not None:
                        conventions[k] = str(v)
            custom = fm_lock.get("custom_conventions")
            if isinstance(custom, dict):
                conventions.update({k: str(v) for k, v in custom.items() if v is not None})

        # Scan body for "Convention Label: value" patterns
        known = _resolve_known_conventions()
        labels = _resolve_labels()
        for key in known:
            label = labels.get(key, key.replace("_", " ").title())
            escaped = re.escape(label)
            pattern = re.compile(
                rf"(?:^|\n)\s*[-*]?\s*{escaped}:\s*(.+?)\s*$",
                re.IGNORECASE | re.MULTILINE,
            )
            match = pattern.search(content)
            if match and key not in conventions:
                conventions[key] = match.group(1).strip()

    return conventions if conventions else None


@instrument_grd_function("conventions.diff_phases")
def convention_diff_phases(
    cwd: Path,
    phase1: str | None = None,
    phase2: str | None = None,
) -> ConventionDiffResult:
    """Diff convention mentions across two phase SUMMARYs."""
    import json

    from grd.core.state import load_state_json

    if not phase1 or not phase2:
        state_data = load_state_json(cwd) or {}
        lock_data = state_data.get("convention_lock", {})
        return ConventionDiffResult(
            note=(
                f"Two phase identifiers required for convention diff. Current convention_lock: {json.dumps(lock_data)}"
            ),
        )

    conv1 = _extract_phase_conventions(cwd, phase1)
    conv2 = _extract_phase_conventions(cwd, phase2)

    conv1_empty = not conv1 or len(conv1) == 0
    conv2_empty = not conv2 or len(conv2) == 0

    if conv1_empty and conv2_empty:
        state_data = load_state_json(cwd) or {}
        lock_data = state_data.get("convention_lock", {})
        return ConventionDiffResult(
            note=(
                f"Could not find convention data for phases {phase1} and {phase2}. "
                f"Current convention_lock: {json.dumps(lock_data)}"
            ),
        )

    changed: list[ConventionDiff] = []
    added: list[ConventionDiff] = []
    removed: list[ConventionDiff] = []

    # Normalize keys before comparison
    norm_conv1 = {normalize_key(k): v for k, v in (conv1 or {}).items()}
    norm_conv2 = {normalize_key(k): v for k, v in (conv2 or {}).items()}
    all_keys = set(norm_conv1) | set(norm_conv2)

    for key in sorted(all_keys):
        val1 = norm_conv1.get(key)
        val2 = norm_conv2.get(key)
        norm1 = normalize_value(key, str(val1)) if val1 is not None else None
        norm2 = normalize_value(key, str(val2)) if val2 is not None else None
        if norm1 is None and norm2 is not None:
            added.append(ConventionDiff(key=key, to_value=norm2))
        elif norm1 is not None and norm2 is None:
            removed.append(ConventionDiff(key=key, from_value=norm1))
        elif norm1 is not None and norm2 is not None and norm1 != norm2:
            changed.append(ConventionDiff(key=key, from_value=norm1, to_value=norm2))

    note = None
    if not conv1:
        note = f"No convention data found in phase {phase1} summaries."
    elif not conv2:
        note = f"No convention data found in phase {phase2} summaries."

    return ConventionDiffResult(changed=changed, added=added, removed=removed, note=note)


@instrument_grd_function("conventions.check")
def convention_check(lock: ConventionLock, *, domain_ctx: object | None = None) -> ConventionCheckResult:
    """Check convention completeness: which canonical fields are set vs missing."""
    known = _resolve_known_conventions(domain_ctx)
    labels = _resolve_labels(domain_ctx)
    missing: list[ConventionEntry] = []
    set_conventions: list[ConventionEntry] = []
    custom: list[ConventionEntry] = []

    for key in known:
        val = lock.conventions.get(key)
        label = labels.get(key, key.replace("_", " ").title())
        if is_bogus_value(val):
            missing.append(ConventionEntry(key=key, label=label, is_set=False, canonical=True))
        else:
            set_conventions.append(ConventionEntry(key=key, label=label, value=val, is_set=True, canonical=True))

    for key, val in lock.conventions.items():
        if key in known:
            continue  # already counted above
        if val is not None and not is_bogus_value(val):
            custom.append(ConventionEntry(key=key, value=val, is_set=True, canonical=False))

    return ConventionCheckResult(
        complete=len(missing) == 0,
        missing=missing,
        set_conventions=set_conventions,
        custom=custom,
        total=len(known),
        set_count=len(set_conventions),
        missing_count=len(missing),
        custom_count=len(custom),
    )


# --- ASSERT_CONVENTION Parsing ---


def parse_assert_conventions(content: str) -> list[tuple[str, str]]:
    """Parse ASSERT_CONVENTION directives from file content."""
    pairs: list[tuple[str, str]] = []
    for match in _ASSERT_LINE_RE.finditer(content):
        payload = match.group(1)
        raw_pairs = re.split(r",\s*(?=\w+=)", payload)
        for raw in raw_pairs:
            raw = raw.strip()
            kv = _KV_PAIR_RE.match(raw)
            if not kv:
                continue
            key = normalize_key(kv.group(1).strip())
            val = kv.group(2).strip()
            pairs.append((key, val))
    return pairs


@instrument_grd_function("conventions.validate_assertions")
def validate_assertions(
    content: str,
    lock: ConventionLock,
    *,
    filename: str = "<unknown>",
) -> list[AssertionMismatch]:
    """Validate ASSERT_CONVENTION directives in file content against a lock."""
    mismatches: list[AssertionMismatch] = []
    assertions = parse_assert_conventions(content)

    for key, asserted_value in assertions:
        lock_value = lock.conventions.get(key)

        if lock_value is None:
            continue

        norm_lock = normalize_value(key, str(lock_value).strip())
        norm_asserted = normalize_value(key, asserted_value)

        if norm_lock != norm_asserted:
            mismatches.append(
                AssertionMismatch(
                    file=filename,
                    key=key,
                    file_value=asserted_value,
                    lock_value=str(lock_value),
                )
            )

    return mismatches
