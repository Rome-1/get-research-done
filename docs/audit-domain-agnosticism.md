# Domain-Agnosticism Audit: Is GRD Truly Domain-Agnostic?

**Date:** 2026-04-01
**Bead:** ge-2qg
**Requested by:** getresearch/crew/alice

## Verdict

**The core loop is domain-agnostic. The claim is honest but incomplete.**

GRD has a well-designed domain-pack plugin system and the kernel, CLI, phase
management, and contract validation are genuinely domain-independent. However,
physics-specific content leaks into core modules in ways that would make an
upstream GPD maintainer rightfully skeptical. The leaks are concentrated in three
areas: the publication pipeline, the convention system's core types, and prompt
templates.

A biology or ML researcher could use GRD's core workflow today. They could **not**
use paper-build, convention-lock, or the debugging prompts without hitting
physics assumptions.

---

## What Is Already Clean

| Component | Location | Notes |
|-----------|----------|-------|
| Verification kernel | `core/kernel.py` | Explicitly domain-independent; runs generic predicates over typed registries |
| Phase/roadmap engine | `core/phases.py` | Pure workflow management, no domain assumptions |
| Contract validation | `core/contract_validation.py` | Generic predicate framework |
| Domain pack loader | `domains/loader.py` | Three-tier discovery (project → user → bundled), lazy-loaded `DomainContext` |
| CLI commands | `cli/*.py` | All generic; physics appears only as the default `GRD_DOMAIN` value |
| Pattern library (framework) | `core/patterns.py` | Categories are generic; `VALID_DOMAINS` discovered dynamically from domain pack |
| Verification checks (framework) | `core/verification_checks.py` | 19 universal checks; error-class coverage loads from domain pack YAML |
| Multiple domain packs | `domains/{economics,machine-learning,mech-interp,philosophy-of-math}` | Non-physics domains exist and work |

**Bottom line:** The architectural claim is real. The plugin boundary exists and
functions. The kernel genuinely doesn't know what physics is.

---

## What Is Hardcoded to Physics

### Tier 1: Would Break for a Non-Physics User

**Convention system types** — `core/conventions.py`, `contracts.py`
- 18 hardcoded physics fields on `ConventionLock`: `metric_signature`,
  `fourier_convention`, `natural_units`, `gauge_choice`,
  `regularization_scheme`, `renormalization_scheme`, `spin_basis`,
  `levi_civita_sign`, `gamma_matrix_convention`, etc.
- A biologist hitting `grd convention lock` sees fields about metric signatures
  and gauge choices. There's a `custom_conventions` escape hatch, but the
  primary interface is physics-only.

**Publication pipeline** — `mcp/paper/`
- `PaperConfig.journal` is `Literal["prl", "apj", "mnras", "nature", "jhep", "jfm"]` — six physics journals, no extensibility point.
- `journal_map.py` maps 30+ physics subdomains to journals. Zero non-physics entries.
- All six LaTeX templates are physics journals.
- `template_registry.py` assumes `{journal}/{journal}_template.tex` naming.
- **Impact:** `grd paper build` is unusable outside physics without code changes.

**Referee policy** — `core/referee_policy.py`
- `_STRICT_STAGE_ARTIFACT_IDS` hardcodes `"physics"` as a review stage name.
- `_HIGH_IMPACT_JOURNALS` = `{"prl", "nature", "nature_physics"}`.
- The staged review pipeline assumes reader → literature → math → **physics** → interestingness.

**Paper quality** — `core/paper_quality.py`
- `physical_interpretation_present` field (should be `domain_interpretation_present`).
- `nature_physics` hardcoded as a journal key.

**Suggest module** — `core/suggest.py`
- `CORE_CONVENTIONS = ("metric_signature", "natural_units", "coordinate_system")` — meaningless outside physics.

### Tier 2: Would Confuse but Not Break

**Prompt templates** — `specs/templates/`
- `planner-subagent-prompt.md` has a `<physics_planning_requirements>` section with tensor structure, limiting cases, dimensional consistency.
- `debug-subagent-prompt.md` has a `<physics_context>` block and a physics-specific error taxonomy (ħ, commutator ordering, Einstein convention).
- `project.md` asks "What is the **physics question** being investigated?"
- `continue-here.md` references "**physics content**".
- These are prompts, not logic — but a biology user sees "physics question" on first use.

**MCP server descriptions** — `mcp/builtin_servers.py`
- Every server description says "physics": "physics conventions", "LLM physics error catalog", "physics error patterns", "physics verification checks".
- These are user-facing tool descriptions shown in MCP clients.

**Pattern domain enum** — `core/patterns.py`
- `PatternDomain` enum lists 13 physics subfields (QFT, condensed-matter, etc.).
- But `_get_valid_domains()` discovers additional subfields from domain packs dynamically, so this is a cosmetic issue.

**Convention defaults** — `mcp/servers/conventions_server.py`
- `SUBFIELD_DEFAULTS` maps 13 physics subfields to convention values.
- Zero non-physics subfield defaults.

### Tier 3: Physics Agent in Core

**`grd-review-physics` agent** — `core/config.py`, `agents/grd-review-physics.md`
- A physics-specific review agent is defined in core config, not in the physics domain pack.
- The agent file contains physics-specific evaluation criteria.
- Should be in `domains/physics/agents/`.

---

## What Would Genuinely Break for a Biology or ML User

1. **`grd paper build`** — fails immediately. No biology journal templates exist.
   The `Literal` type annotation rejects any journal not in the physics list.

2. **`grd convention lock`** — shows 18 physics fields. A biologist would need to
   ignore all named fields and use only `custom_conventions`. The `suggest` module
   would recommend setting `metric_signature` for any project.

3. **Referee review stages** — the "physics" review stage is a string constant in
   core, not loaded from domain pack. The review pipeline expects it.

4. **Debugging prompts** — an ML user's debugging session would receive physics
   error taxonomy (check ħ factors, check Einstein convention) regardless of domain.

5. **Paper quality scoring** — checks for `physical_interpretation_present`, which
   is nonsensical for an economics paper.

---

## What Would NOT Break

1. **Core workflow** — `grd init`, `grd phase`, `grd verify`, `grd checkpoint` all work fine.
2. **Contract system** — defining research contracts, running verification predicates.
3. **Pattern library** — recording and querying error patterns (framework is generic).
4. **Health checks** — project health monitoring.
5. **Domain switching** — `grd domain set machine-learning` works; ML domain pack loads correctly.

---

## Honest Assessment for Upstream GPD Maintainers

The claim that "the core loop is domain-agnostic and physics-specific pieces are
largely in prompts, terminology, and a few verification heuristics" is **mostly
true but undersells the problem**. The core loop genuinely is domain-agnostic.
But "a few verification heuristics" understates the situation:

- The **convention system's type definitions** are in core, not in the domain pack.
- The **publication pipeline** is not pluggable at all — it's hardcoded to 6 physics journals.
- The **referee policy** has physics string constants in core logic.
- The **paper quality model** has physics-specific field names.
- The **prompt templates** are physics-first, not domain-parameterized.

**What would make skeptics confident:**

1. Move `ConventionLock`'s 18 named fields into the physics domain pack; keep only `custom_conventions` in core.
2. Make `PaperConfig.journal` a `str` validated against domain-pack-provided journal specs, not a `Literal`.
3. Move journal templates, specs, and mappings into domain packs.
4. Replace hardcoded `"physics"` stage in referee policy with domain-configurable stages.
5. Rename `physical_interpretation_present` → `domain_interpretation_present`.
6. Parameterize prompt templates on domain (replace `<physics_planning_requirements>` with domain-loaded content).
7. Move `grd-review-physics` agent to `domains/physics/agents/`.
8. Update MCP server descriptions to say "research" not "physics".

**Estimated effort:** Items 4, 5, 7, 8 are trivial renames. Items 1-3 and 6 are
medium-effort refactors that touch the type system and template loading. None
require architectural changes — the plugin boundary already exists; the physics
content just needs to move behind it.

---

## File-Level Reference

| File | Physics Content | Severity |
|------|----------------|----------|
| `core/conventions.py` | 18 physics convention fields | HIGH |
| `contracts.py` (ConventionLock) | Same fields as model | HIGH |
| `mcp/paper/models.py` | `Literal["prl","apj",...]` | HIGH |
| `mcp/paper/journal_map.py` | 30+ physics subdomain mappings | HIGH |
| `mcp/paper/templates/` | 6 physics journal templates | HIGH |
| `core/referee_policy.py` | `"physics"` stage, physics journals | HIGH |
| `core/paper_quality.py` | `physical_interpretation_present` | MEDIUM |
| `core/suggest.py` | `CORE_CONVENTIONS` = physics fields | MEDIUM |
| `mcp/builtin_servers.py` | "physics" in all descriptions | MEDIUM |
| `mcp/servers/conventions_server.py` | 13 physics subfield defaults | MEDIUM |
| `specs/templates/*.md` | Physics prompts and error taxonomy | MEDIUM |
| `core/config.py` | `grd-review-physics` in core | LOW |
| `core/patterns.py` | Physics enum (but dynamic discovery works) | LOW |
| `cli/convention.py`, `cli/domain.py` | `"physics"` as default | LOW |
| `__init__.py` | "physics research orchestration" docstring | LOW |
