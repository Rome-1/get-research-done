# Review: Domain-Agnostic Refactoring Plan (REFACTOR_PLAN.md)

**Reviewer:** polecat/rust
**Bead:** ge-q5w
**Date:** 2026-03-15

---

## Overall Assessment

The plan is well-structured and covers the major surface area. The phased approach
is sensible and the "extract first, then generalize" ordering (Phase 2 before 3)
reduces risk. That said, there are several missing coupling points, architectural
concerns, and risks that need addressing before implementation begins.

---

## 1. Missing Domain Coupling Points

### 1.1 `SUBFIELD_DEFAULTS` in `conventions_server.py` (lines 77-170)

The plan identifies convention constants in `conventions.py` but misses the large
`SUBFIELD_DEFAULTS` dict in `mcp/servers/conventions_server.py`. This maps 11
physics subfields (qft, condensed_matter, statistical_mechanics, etc.) to their
recommended convention values. This is ~100 lines of pure physics content that
must move to the domain pack but isn't mentioned in Section 5.2.

### 1.2 `verification_checks.py` — hardcoded physics check registry

The plan mentions moving protocols and error catalogs but doesn't call out
`core/verification_checks.py`. This file is the "single executable source of
truth" for verification checks and contains physics-specific domain tags like
`"qft"`, `"mathematical_physics"`. The `VerificationCheckDef` has a `domains`
field with hardcoded physics subdomain values. This file needs either:
- Moving domain-specific checks to the domain pack, or
- Making the `domains` field reference domain-pack-defined values.

### 1.3 `journal_map.py` — physics journal routing

`mcp/paper/journal_map.py` has a 40+ entry `_DOMAIN_TO_JOURNAL` dict mapping
physics subdomains to journals (particle_physics → prl, astrophysics → apj, etc.)
plus `_JOURNAL_DEFAULTS` with templates for 16 physics journals. This is pure domain
content not mentioned in the plan.

### 1.4 `patterns_server.py` — physics patterns

The patterns MCP server contains 6 references to physics in its pattern categories
and domain-specific pattern descriptions. The cross-project pattern library in
`specs/references/shared/` also contains physics-specific patterns.

### 1.5 `health.py` — convention completeness checks

`health.py` imports `KNOWN_CONVENTIONS` directly and runs convention completeness
checks. The plan's Section 5.1 lists Health checks as "domain-independent (minus
convention completeness)" but doesn't specify how health checks become domain-aware.
This needs explicit treatment — health.py needs to receive the domain context to
know which conventions are "expected."

### 1.6 Agent system prompts with embedded physics knowledge

The 23 agent `.md` files contain system prompts. Several of these (not just the
4 identified in Section 5.2) embed physics terminology, examples, and domain
assumptions in their prose. For example, `gpd-verifier.md` likely references
physics verification patterns, `gpd-executor.md` may reference physics workflows.
A systematic audit of all agent prompts is needed — the plan should include a
"scrub agent prompts" substep in Phase 3.

### 1.7 `core/extras.py`, `core/referee_policy.py`, `core/paper_quality.py`

All contain physics references (grep found hits). These aren't mentioned in the plan.

---

## 2. Architectural Concerns

### 2.1 Dict-based ConventionLock loses type safety at the wrong layer

The plan recommends the "simpler" dict-based approach:
```python
class ConventionLock(BaseModel):
    conventions: dict[str, str | None] = Field(default_factory=dict)
    custom_conventions: dict[str, str] = Field(default_factory=dict)
```

**Problem:** This collapses the distinction between "canonical" and "custom"
conventions into a runtime check rather than a structural one. Currently,
`ConventionLock.model_fields` programmatically drives `KNOWN_CONVENTIONS` in
`conventions.py`. With a dict, you lose:
- IDE autocompletion on convention names
- Pydantic validation that field names are valid
- The ability to distinguish "this field is None" (explicitly unset) from
  "this field doesn't exist" (not applicable to this domain)

**Recommendation:** Use `create_model()` (the dynamic Pydantic approach shown
first in the plan). The complexity is contained in one factory function, and you
preserve type safety downstream. The serialization concern is manageable — Pydantic
`model_dump()` works fine on dynamic models.

### 2.2 `DomainContext` as a dataclass is too static

The proposed `DomainContext` dataclass resolves everything at startup. But some
domain content is large (104 error classes, 47 protocols) and may not be needed
for every command. Consider lazy-loading:

```python
@dataclass
class DomainContext:
    name: str
    pack_path: Path
    # Lazy-loaded, cached properties instead of eagerly-resolved fields
    @cached_property
    def conventions(self) -> ConventionSchema: ...
    @cached_property
    def protocols(self) -> list[Protocol]: ...
```

This matters because `grd:health` shouldn't pay the cost of loading 47 protocol
definitions, and `grd:verify-work` shouldn't load journal templates.

### 2.3 Three-tier discovery (bundled > user > project) creates merge ambiguity

The plan says "Priority: project > user > bundled" for domain pack discovery.
But what does this mean concretely? If a project has `.grd/domain/` with a partial
domain pack (just a conventions override), does it:
- (a) Replace the entire bundled physics pack? (dangerous — you lose protocols)
- (b) Merge/overlay on top of the bundled pack? (complex — what are the merge rules?)
- (c) Only override files that exist in the project pack? (file-level granularity)

This needs a clear specification. I recommend option (c) with explicit file-level
override — it's the most predictable and requires no deep merge logic.

### 2.4 Missing: how does `DomainContext` get threaded through?

The plan says DomainContext is "resolved once at command startup and threaded
through." But the current architecture uses module-level constants (e.g.,
`KNOWN_CONVENTIONS` imported at module scope in `health.py`). The plan doesn't
address the threading mechanism:
- Dependency injection via function parameters? (clean but touches many signatures)
- Global/contextvar? (less clean but minimally invasive)
- Registry pattern? (the existing pattern uses module-level caches)

This is the hardest part of Phase 3 and deserves explicit design treatment.

---

## 3. Risk Areas in Migration

### 3.1 Phase 4 (rename GPD→GRD) is the highest-risk phase, not Phase 3

The plan rates Phase 4 as "Low (mechanical)" but this is misleading:
- 200+ files changed in one commit is a merge nightmare
- Every open branch/PR becomes unbased
- External references (docs, bookmarks, configs) all break
- The rename intersects with every other phase's work

**Recommendation:** Do Phase 4 FIRST (contrary to the plan's suggestion in Q5).
Yes, it's disruptive. But doing it last means all of Phases 1-3 and 5 use the old
`gpd` naming, and then Phase 4 rewrites everything again. Doing it first means
Phases 1-5 work in the final namespace. The plan even acknowledges this tradeoff
in Q5 but makes the wrong call. A single big rename commit is easier to review
and less error-prone than interleaving rename with architectural changes.

### 3.2 State migration is under-specified

The plan mentions "Migration script + backward compat detection of old format"
but doesn't detail:
- What happens to in-progress projects during the migration?
- Is migration automatic on first run, or explicit?
- What if migration fails partway (crash recovery)?
- How does `state.json` schema versioning work? (No `schema_version` field exists today)

This needs a dedicated migration design, not a one-liner in the risk table.

### 3.3 MCP server interface stability

The plan says "MCP servers keep same tool interface." But if conventions change
from named fields to a dict, the MCP tool schemas change. Clients calling
`convention_set(metric_signature="mostly-minus")` would need to call
`convention_set(key="metric_signature", value="mostly-minus")`. This is a
breaking change to the MCP API surface. The plan should explicitly document
MCP API compatibility guarantees.

---

## 4. Better Alternatives

### 4.1 Convention validation via JSON Schema instead of Pydantic dynamic models

Instead of either the dict approach or `create_model()`, consider having
`convention-fields.yaml` compile to a JSON Schema that Pydantic validates against.
This gives you:
- External tooling can validate conventions without Python
- Schema can be shipped with the domain pack
- Pydantic's `model_validate_json()` works with JSON Schema natively

### 4.2 Domain pack as a Python package (for third-party packs)

For bundled packs, the directory approach works. But for third-party domain packs,
a Python package (installable via pip) would be more robust:
- Dependency management (a biology pack might need BioPython)
- Versioning via PyPI
- Entry points for discovery (`grd.domains` entry point group)

The plan should at least mention this as a future direction, even if v1 uses
directory-only discovery.

### 4.3 `numerical-convergence`, `parameter-sweep`, `sensitivity-analysis` should stay in core

The plan moves these to the physics domain pack, but convergence testing, parameter
sweeps, and sensitivity analysis are universal computational research tools used in
biology (population dynamics), economics (Monte Carlo), chemistry (molecular dynamics),
and engineering (FEA). Only `derive-equation`, `dimensional-analysis`, and
`limiting-cases` are genuinely physics-specific.

---

## 5. Opinions on Open Questions (Section 8)

### Q1: Should `grd-review-math` stay in core?

**Keep in core, but refactor.** Math review IS cross-domain. The current physics
flavor is a content problem, not an architectural one. Strip physics-specific
examples from the system prompt and load domain-specific math examples from the
domain pack. The agent's structure (check derivations, verify algebra, validate
limits) is universal.

### Q2: Should some verification commands stay in core?

**Split:** Keep `numerical-convergence`, `parameter-sweep`, `sensitivity-analysis`,
and `error-propagation` in core (they're universal computational methods). Move
`derive-equation`, `dimensional-analysis`, and `limiting-cases` to the physics
pack. Rename `dimensional-analysis` to `unit-analysis` if you want a more generic
framing, but honestly it belongs in physics.

### Q3: Domain pack versioning?

**Yes, required from day one.** Without it, a domain pack update can silently break
projects. Minimum viable: `engine_version: ">=1.0"` in `domain.yaml`, checked at
load time. Don't over-engineer (no semver range solving needed), but do fail loudly
on mismatch.

### Q4: Multi-domain projects?

**Correct to defer.** Multi-domain introduces convention conflicts (biology and
chemistry may define `nomenclature_system` differently). The `custom_conventions`
escape hatch is sufficient for v1. But design the convention namespace so it
doesn't preclude future multi-domain support (e.g., don't flatten domain-pack
conventions into a single global dict without a domain prefix).

### Q5: Rename timing?

**Do it FIRST.** See Section 3.1 above. The plan's recommendation to do it last
optimizes for incremental development but creates a massive rename diff that
touches code already modified in Phases 1-5. Doing it first means you take the
pain once and all subsequent work is in the final namespace.

### Q6: Should arxiv-mcp-server stay as core dependency?

**Move to optional dependency.** `pip install get-research-done[physics]` installs
the physics domain pack plus arxiv-mcp-server. Core package should not require
arxiv-specific dependencies. This also sets the pattern for future domain packs
with their own dependencies.

---

## 6. Additional Recommendations

### 6.1 Add a "domain: none" integration test

Phase 5 mentions "Ensure core command set works without any domain pack loaded"
but this should be a CI gate from Phase 1 onward. Create a test that boots the
system with no domain pack and verifies core commands work. This prevents
accidental domain coupling from creeping back in.

### 6.2 Audit `specs/references/` more carefully

The plan's Section 5 doesn't fully audit `specs/references/`. The subdirectories
`execution/`, `planning/`, `orchestration/`, `research/`, `methods/` may contain
physics-flavored prose in otherwise domain-agnostic files. A grep for physics terms
across all specs would catch these.

### 6.3 Consider a `domain lint` command

After the refactor, add `grd:domain-lint` that scans core code paths for
domain-specific references. This prevents regression — if someone adds a physics
term to a core file, CI catches it.

### 6.4 The size estimate is optimistic for Phase 3

Phase 3 lists "~15 files changed, ~3 new files" but the threading of DomainContext
through conventions.py, health.py, config.py, verification_checks.py, all MCP
servers, and cli.py will touch significantly more files. A more realistic estimate
is 30-40 files changed.
