"""Grounded name-index over Mathlib4 + PhysLean snapshots.

The pipeline's §2 retrieval stage uses this to:

1. Seed the candidate-generation prompt with a sample of known identifier
   names (so the model is biased toward real names, not hallucinated ones).
2. Run a Suffix Array Check on each identifier the generated Lean source uses
   — if it isn't in the index, we flag the candidate as hallucinated without
   even asking Lean. This is the DDR trick from [DDR, 2025]: generate-and-check
   beats retrieve-and-select on downstream autoformalization.

For the MVP we accept newline-delimited identifier files rather than a full
Mathlib checkout: a pre-computed snapshot is far cheaper to carry in-tree
(bead ``ge-cch`` tracks ingestion tooling) and keeps CI green without cloning
10 GB of Lean olean caches.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from grd.core.constants import PLANNING_DIR_NAME
from grd.core.lean.autoformalize.config import AutoformalizeConfig

__all__ = [
    "MATHLIB_NAMES_FILE",
    "PHYSLEAN_NAMES_FILE",
    "NameIndex",
    "extract_identifiers",
    "load_default_index",
]


MATHLIB_NAMES_FILE = "mathlib4-names.txt"
PHYSLEAN_NAMES_FILE = "physlean-names.txt"


_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.\u2081-\u2089']*")
"""Match a Lean identifier token.

Lean 4 identifiers can contain Unicode, dots (for namespaces), subscripts, and
primes. We over-match slightly — the Suffix Array Check will reject anything
that isn't a real identifier without downstream harm. Keeping the regex
permissive avoids quietly dropping valid names containing e.g. subscripts like
`Nat.Prime₁`.
"""


_LEAN_BUILTINS: frozenset[str] = frozenset(
    {
        # Core prelude types.
        "Nat",
        "Int",
        "Real",
        "Rat",
        "Bool",
        "String",
        "Char",
        "Unit",
        "Prop",
        "Type",
        "Sort",
        "Empty",
        "PUnit",
        "PEmpty",
        # Prop/bool constants.
        "True",
        "False",
        # Generic containers.
        "List",
        "Array",
        "Option",
        "Some",
        "None",
        "Sum",
        "Prod",
        # Common constructors / helpers.
        "Eq",
        "Ne",
        "Iff",
        "And",
        "Or",
        "Not",
        "Exists",
        "Forall",
        # Tactics blocks / macros that look like identifiers.
        "Mathlib",
        "PhysLean",
    }
)
"""Lean 4 prelude names we recognise without needing them in the snapshot.

If a candidate uses a bare ``Nat`` we don't want the DDR check to reject it
just because the snapshot only contains the qualified ``Nat.Prime`` entry —
the prelude is always available. Custom projects can still shadow these via
their index; the allowlist is a lower bound, not a hard override.
"""


@dataclass(frozen=True)
class NameIndex:
    """In-memory set of known Lean identifiers.

    ``source`` annotates where the names came from (for logging / diagnostics).
    Contains checks are O(1); sampling is deterministic via the sorted order,
    so prompts don't drift between runs.
    """

    names: frozenset[str]
    source: str = ""
    _sorted_sample: tuple[str, ...] = field(default_factory=tuple, repr=False)

    @classmethod
    def from_iterable(cls, raw: list[str] | tuple[str, ...] | frozenset[str], source: str = "") -> NameIndex:
        cleaned = {n.strip() for n in raw if n.strip()}
        return cls(names=frozenset(cleaned), source=source, _sorted_sample=tuple(sorted(cleaned)))

    @classmethod
    def empty(cls) -> NameIndex:
        return cls(names=frozenset(), source="", _sorted_sample=())

    @property
    def size(self) -> int:
        return len(self.names)

    def contains(self, identifier: str) -> bool:
        """Strict Suffix Array Check: exact identifier membership.

        We do NOT fall back to fuzzy matching — the whole point of the §2
        check is to reject hallucinated names loudly.
        """
        return identifier in self.names

    def sample(self, k: int) -> list[str]:
        """First ``k`` names in sorted order. Deterministic across processes.

        ``k <= 0`` returns an empty list rather than raising — the caller may
        legitimately ask for no sample (empty index, or prompting strategy
        disabled).
        """
        if k <= 0:
            return []
        return list(self._sorted_sample[:k])

    def unknown_identifiers(self, lean_source: str) -> list[str]:
        """Return identifiers in ``lean_source`` not present in the index.

        Only identifiers that look like Mathlib-style qualified or CamelCase
        names are checked — lowercase single-word identifiers are treated as
        local bindings and always considered "known" to avoid false positives.
        If the index is empty (no snapshot loaded), the result is empty too —
        we can't flag what we don't have data for.
        """
        if not self.names:
            return []
        unknown: list[str] = []
        seen: set[str] = set()
        for tok in _IDENT_RE.findall(lean_source):
            if tok in seen:
                continue
            seen.add(tok)
            if not _looks_like_library_name(tok):
                continue
            if tok in _LEAN_BUILTINS:
                continue
            if tok not in self.names:
                unknown.append(tok)
        return unknown


def _looks_like_library_name(tok: str) -> bool:
    """Heuristic: is this token plausibly a Mathlib/PhysLean identifier?

    We check for qualified names (contain a dot) or CamelCase heads. Pure
    lowercase tokens like `n`, `x`, `h` are local bindings — checking them
    against the index produces noise, not signal.
    """
    if "." in tok:
        return True
    if tok[:1].isupper() and any(c.islower() for c in tok[1:]):
        return True
    return False


def extract_identifiers(lean_source: str) -> list[str]:
    """Return every token from ``lean_source`` that matches the identifier regex.

    Exposed so repair prompts can show the model exactly which names were
    flagged, not just the rejected ones.
    """
    return _IDENT_RE.findall(lean_source)


def load_default_index(project_root: Path, config: AutoformalizeConfig) -> NameIndex:
    """Load Mathlib4 + PhysLean name files from the project's ``.grd`` dir.

    If both are absent we return an empty index — the pipeline still runs, it
    just can't DDR-check hallucinations. ``ge-cch`` tracks the upstream tooling
    for snapshot generation; until it lands, users can hand-drop a
    ``mathlib4-names.txt`` into ``.grd/`` and the index picks it up without code
    changes.
    """
    names: set[str] = set()
    sources: list[str] = []

    for configured, default in (
        (config.mathlib_names_path, MATHLIB_NAMES_FILE),
        (config.physlean_names_path, PHYSLEAN_NAMES_FILE),
    ):
        path = _resolve_index_path(project_root, configured, default)
        if path is None or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        loaded = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
        names.update(loaded)
        sources.append(f"{path.name}({len(loaded)})")

    return NameIndex.from_iterable(names, source=", ".join(sources))


def _resolve_index_path(project_root: Path, configured: str | None, default_name: str) -> Path | None:
    if configured:
        p = Path(configured)
        return p if p.is_absolute() else project_root / p
    return project_root / PLANNING_DIR_NAME / default_name
