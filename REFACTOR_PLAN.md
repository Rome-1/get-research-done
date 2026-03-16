# Domain-Agnostic Refactoring Plan

**Goal:** Transform GPD ("Get Physics Done") from a physics-specific research copilot
into a domain-agnostic research copilot that can be configured for *any* research domain
(physics, biology, chemistry, economics, CS, mathematics, engineering, social sciences, etc.).

**Guiding principles:**
- The *engine* (phases, contracts, state, verification framework, MCP servers, adapters) stays
- The *domain knowledge* (conventions, subfields, protocols, error catalogs, review stages) becomes pluggable
- Zero physics references should remain in core code paths — physics becomes one bundled domain pack
- Existing physics users experience no regression: `--domain physics` (or a domain config) restores full current behavior

---

## 1. Rename: GPD → GRD ("Get Research Done")

### 1.1 Package & project identity

| Current | New |
|---------|-----|
| `get-physics-done` (pyproject.toml name, npm name) | `get-research-done` |
| `gpd` (Python package, CLI entrypoint, env vars) | `grd` |
| `GPD_*` env vars | `GRD_*` |
| `.gpd/` project metadata dir | `.grd/` |
| `gpd:*` command names | `grd:*` |
| `gpd-*` agent/skill names | `grd-*` |
| `gpd-mcp-*` MCP server entrypoints | `grd-mcp-*` |
| `_GPD_DISPLAY_NAME = "Get Physics Done"` | `_GRD_DISPLAY_NAME = "Get Research Done"` |
| All infra JSON files `gpd-*.json` | `grd-*.json` |

**Files affected:**
- `pyproject.toml` — name, description, keywords, classifiers, scripts, URLs
- `package.json` — name (npm)
- `README.md` — all branding, install commands
- `bin/install.js` — package references
- `src/gpd/` → `src/grd/` — entire package directory rename
- `src/grd/core/constants.py` — `PLANNING_DIR_NAME = ".grd"`, all `ENV_GPD_*` → `ENV_GRD_*`
- `src/grd/cli.py` — display name, help strings, `_GPD_DISPLAY_NAME`
- `src/grd/version.py`
- `src/grd/runtime_cli.py`
- All `*.md` command/agent files — `gpd:` → `grd:`, `gpd-` → `grd-`
- `infra/*.json` — filenames and content
- `tests/` — all import paths

**Migration note:** Provide a one-time migration script that renames `.gpd/` → `.grd/` in
existing projects and updates `state.json` references.

### 1.2 Backward compatibility (optional, time-limited)

- Keep `gpd` as a CLI alias that prints a deprecation warning and delegates to `grd`
- Keep `.gpd/` detection with auto-migration prompt
- Remove after 2 major versions

---

## 2. Domain Pack Architecture

This is the core architectural change. All domain-specific content becomes a **domain pack** —
a structured directory of markdown/YAML files that the engine loads at runtime.

### 2.1 Domain pack structure

```
domains/
├── physics/                      # Bundled domain pack (current content)
│   ├── domain.yaml               # Domain metadata & configuration
│   ├── conventions/              # Convention definitions
│   │   ├── convention-fields.yaml
│   │   ├── convention-defaults.yaml
│   │   ├── value-aliases.yaml
│   │   └── quick-reference.md
│   ├── subfields/                # Subfield reference material
│   │   ├── qft.md
│   │   ├── condensed-matter.md
│   │   └── ...
│   ├── protocols/                # Verification protocols
│   │   ├── perturbation-theory.md
│   │   ├── dimensional-analysis.md
│   │   └── ...
│   ├── errors/                   # LLM error catalog
│   │   ├── llm-errors-core.md
│   │   ├── llm-errors-field-theory.md
│   │   └── ...
│   ├── verification/             # Verification checklists
│   │   └── ...
│   ├── publication/              # Journal templates, review stages
│   │   ├── journal-templates.yaml
│   │   └── review-stages.yaml
│   └── profiles/                 # Model profile overrides
│       └── model-profiles.yaml
├── biology/                      # Example future domain pack
│   ├── domain.yaml
│   ├── conventions/
│   │   └── convention-fields.yaml  # e.g., nomenclature_system, sequence_format, ...
│   ├── protocols/
│   │   └── experimental-validation.md
│   └── ...
└── _template/                    # Empty template for creating new domain packs
    ├── domain.yaml
    └── README.md
```

### 2.2 `domain.yaml` schema

```yaml
name: physics
display_name: Physics
description: "Physics research: QFT, condensed matter, GR, ..."
version: 1

# Convention fields this domain defines (replaces hardcoded ConventionLock)
conventions_file: conventions/convention-fields.yaml

# Subfields (for routing protocols and context)
subfields_dir: subfields/

# Verification protocols
protocols_dir: protocols/

# LLM error catalog
errors_dir: errors/

# Publication venues
publication:
  journal_templates: publication/journal-templates.yaml
  review_stages: publication/review-stages.yaml

# Model profile adjustments (optional)
profiles_file: profiles/model-profiles.yaml

# Domain-specific agents (optional — additional agents beyond the core set)
agents_dir: agents/

# Domain-specific commands (optional)
commands_dir: commands/

# Display customization
branding:
  tagline: "Built by physicists, for physicists"
  color: blue
```

### 2.3 `convention-fields.yaml` schema

```yaml
# Replaces the hardcoded 18-field ConventionLock
fields:
  - name: metric_signature
    label: "Metric signature"
    description: "Spacetime metric sign convention"
    aliases: ["metric"]
    value_aliases:
      "(+,-,-,-)": "mostly-minus"
      "(-,+,+,+)": "mostly-plus"
      # ...

  - name: natural_units
    label: "Natural units"
    aliases: ["units"]
    # ...

# For biology, this might be:
# fields:
#   - name: nomenclature_system
#     label: "Nomenclature system"
#     aliases: ["nomenclature"]
#   - name: sequence_format
#     label: "Sequence format"
#     aliases: ["seq_format"]
#   - name: statistical_framework
#     label: "Statistical framework"
```

---

## 3. Core Engine Changes

### 3.1 ConventionLock → DomainConventionLock (dynamic)

**Current:** `ConventionLock` is a Pydantic model with 18 hardcoded physics fields.

**New:** `DomainConventionLock` is a dynamic model built from `convention-fields.yaml`.

```python
# contracts.py
class DomainConventionLock(BaseModel):
    """Convention lock with fields defined by the active domain pack."""
    model_config = ConfigDict(validate_assignment=True, extra="allow")
    custom_conventions: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_domain(cls, domain_fields: list[ConventionFieldDef]) -> type["DomainConventionLock"]:
        """Create a ConventionLock subclass with domain-specific fields."""
        field_definitions = {
            f.name: (str | None, Field(default=None))
            for f in domain_fields
        }
        return create_model("DomainConventionLock", __base__=cls, **field_definitions)
```

**Alternatively (simpler):** Keep `ConventionLock` as a thin wrapper around a dict,
with `custom_conventions` being the primary storage and domain packs defining the
"known" keys:

```python
class ConventionLock(BaseModel):
    conventions: dict[str, str | None] = Field(default_factory=dict)
    custom_conventions: dict[str, str] = Field(default_factory=dict)
```

The simpler approach is recommended — it avoids dynamic model generation and keeps
serialization straightforward. The domain pack defines which keys are "canonical"
vs "custom" at the application layer, not the data model layer.

**Migration:** Existing `state.json` files with the 18 physics fields need a migration
that moves them into the dict-based format.

### 3.2 conventions.py — domain-aware

**Current:** `KNOWN_CONVENTIONS`, `CONVENTION_LABELS`, `KEY_ALIASES`, `VALUE_ALIASES`
are all module-level constants derived from the hardcoded `ConventionLock`.

**New:** These become functions that read from the active domain pack:

```python
def get_known_conventions(domain: DomainPack) -> list[str]: ...
def get_convention_labels(domain: DomainPack) -> dict[str, str]: ...
def get_key_aliases(domain: DomainPack) -> dict[str, str]: ...
def get_value_aliases(domain: DomainPack) -> dict[str, dict[str, str]]: ...
```

All convention operations (`convention_set`, `convention_list`, etc.) gain a `domain`
parameter or read from a project-level domain context.

### 3.3 config.py — domain-aware profiles

**Current:** `MODEL_PROFILES` and `AGENT_DEFAULT_TIERS` are hardcoded dicts keyed by
`gpd-*` agent names.

**New:**
- Core profiles define base tiers for domain-agnostic agents (`grd-planner`, `grd-executor`, etc.)
- Domain packs can override/extend with domain-specific agent profiles
- `ModelProfile` enum becomes extensible (domains can add profiles like `"wet-lab"`, `"field-study"`)

### 3.4 registry.py — domain-aware commands & agents

**Current:** Commands from `src/gpd/commands/`, agents from `src/gpd/agents/`.

**New:**
- Core commands/agents from `src/grd/commands/` and `src/grd/agents/`
- Domain packs can contribute additional commands and agents
- Registry merges core + domain sources
- Physics-specific agents (`gpd-review-physics`) move to the physics domain pack
- Domain-agnostic agents (`grd-planner`, `grd-executor`, `grd-verifier`) stay in core

### 3.5 Verification framework — domain-aware

**Current:** 47+ verification protocols hardcoded in `specs/references/protocols/`.
Error catalog with 104 physics-specific error classes in `specs/references/verification/errors/`.

**New:**
- Protocols move to domain packs
- Core keeps only domain-agnostic verification concepts (existence checks, schema validation,
  reproducibility, convergence testing framework)
- Each domain pack provides its own error catalog and protocols
- MCP servers (`grd-mcp-protocols`, `grd-mcp-errors`) load from active domain pack

### 3.6 Publication module — domain-aware

**Current:** Journal templates hardcoded for physics journals (APJ, JHEP, PRL, etc.).
Review stages include `physics` as a named stage.

**New:**
- Core publication framework (LaTeX compilation, bibliography, artifact manifest) stays
- Journal templates move to domain packs
- Review stages become configurable: domain packs define which review stages apply
  (e.g., physics has "math" + "physics" stages; biology might have "methods" + "statistical-analysis")
- `gpd-review-physics` agent → physics domain pack
- Core keeps `grd-review-reader`, `grd-review-literature`, `grd-review-math` (math is cross-domain)

---

## 4. Domain Resolution

### 4.1 How a project selects its domain

```json
// .grd/config.json
{
  "domain": "physics",
  "model_profile": "deep-theory",
  ...
}
```

- `domain` key references a domain pack name
- If absent, the tool operates in "generic research" mode with no domain-specific conventions,
  protocols, or error catalogs
- `grd:new-project` asks the user to select a domain (or skip)
- Domain can be changed mid-project (with a migration/warning)

### 4.2 Domain pack discovery

1. Bundled packs: `src/grd/domains/` (ships with the package)
2. User packs: `~/.grd/domains/` (user-installed)
3. Project packs: `.grd/domain/` (project-local overrides)

Priority: project > user > bundled.

### 4.3 Runtime context

A `DomainContext` object is resolved once at command startup and threaded through:

```python
@dataclass
class DomainContext:
    name: str
    pack_path: Path
    conventions: ConventionSchema  # parsed convention-fields.yaml
    protocols_dir: Path
    errors_dir: Path
    subfields_dir: Path
    publication: PublicationConfig
    agents: dict[str, AgentDef]  # domain-contributed agents
    commands: dict[str, CommandDef]  # domain-contributed commands
```

---

## 5. What Moves Where

### 5.1 Stays in core (domain-agnostic)

| Component | Rationale |
|-----------|-----------|
| CLI framework (`cli.py`, `runtime_cli.py`) | Entry point, routing |
| State management (`state.py`, `state.json`) | Domain-independent |
| Phase lifecycle (`phases.py`) | Domain-independent |
| Contract system (`contracts.py`) | Domain-independent structure |
| Health checks (`health.py`) | Domain-independent (minus convention completeness) |
| Observability (`observability.py`, traces) | Domain-independent |
| Pattern library (`patterns.py`) | Domain-independent framework |
| Git operations (`git_ops.py`) | Domain-independent |
| Config loading (`config.py`) | Domain-independent (loads domain config) |
| Runtime adapters (`adapters/`) | Domain-independent |
| MCP server framework (`mcp/`) | Domain-independent servers that load domain content |
| Core commands: `new-project`, `plan-phase`, `execute-phase`, `resume-work`, `pause-work`, `health`, `settings`, `help`, `compact-state`, `sync-state`, `progress`, `suggest-next`, `add-todo`, `check-todos`, `undo`, `update`, `export`, `graph`, `decisions`, `add-phase`, `insert-phase`, `remove-phase`, `new-milestone`, `complete-milestone`, `audit-milestone`, `branch-hypothesis`, `compare-branches`, `record-insight`, `discover`, `explain`, `slides`, `map-research`, `discuss-phase`, `quick`, `set-profile` | Core workflow |
| Core agents: `grd-planner`, `grd-executor`, `grd-roadmapper`, `grd-plan-checker`, `grd-debugger`, `grd-explainer`, `grd-research-mapper`, `grd-project-researcher`, `grd-phase-researcher`, `grd-research-synthesizer`, `grd-paper-writer`, `grd-literature-reviewer`, `grd-bibliographer`, `grd-review-reader`, `grd-review-literature`, `grd-review-significance`, `grd-referee`, `grd-experiment-designer` | Core research roles |
| Core verification commands: `verify-work`, `compare-results`, `compare-experiment`, `regression-check`, `debug` | Core verification framework |

### 5.2 Moves to physics domain pack

| Component | Current location |
|-----------|-----------------|
| 18 convention field definitions | `contracts.py` `ConventionLock` |
| Convention labels, aliases, value aliases | `conventions.py` |
| Subfield convention defaults | `specs/references/conventions/` |
| 16 subfield reference files | `specs/references/subfields/` |
| `physics-subfields.md` | `specs/references/` |
| 47+ verification protocols | `specs/references/protocols/` |
| LLM physics error catalog (104 classes) | `specs/references/verification/errors/` |
| Physics-specific verification checklists | `specs/references/verification/` |
| `gpd-review-physics` agent | `agents/` |
| `gpd-review-math` agent | `agents/` (math is arguably cross-domain but deeply physics-flavored here) |
| `gpd-notation-coordinator` agent | `agents/` |
| `gpd-consistency-checker` agent | `agents/` (physics consistency) |
| Physics journal templates | `mcp/paper/` |
| Physics-specific command descriptions (e.g., "physics consistency checks") | Various `*.md` files |
| `derive-equation` command | `commands/` (physics-specific) |
| `dimensional-analysis` command | `commands/` (physics-specific) |
| `limiting-cases` command | `commands/` (physics-specific) |
| `numerical-convergence` command | `commands/` |
| `error-propagation` command | `commands/` |
| `sensitivity-analysis` command | `commands/` |
| `parameter-sweep` command | `commands/` |
| `validate-conventions` command | `commands/` (stays in core but reads domain pack) |
| ArXiv MCP server config | `infra/gpd-arxiv.json` |
| `arxiv-submission` command | `commands/` (physics/academic-specific) |

### 5.3 Needs generalization (stays in core, but text changes)

| Component | Change needed |
|-----------|---------------|
| `new-project.md` | Remove "physics-questioning pass" → "domain-specific questioning pass" loaded from domain pack |
| `verify-work.md` | Remove "Physics verification is fundamentally different..." → generalize to "Domain-specific verification..." |
| Agent descriptions | Remove "physics" from descriptions where it should say "research" |
| `write-paper` command | Generalize journal references |
| `peer-review` command | Make review stages configurable (loaded from domain pack) |
| `README.md` | Complete rewrite for domain-agnostic framing |

---

## 6. Implementation Phases

### Phase 1: Domain pack infrastructure (no behavior change)
1. Create `DomainPack` loader and `DomainContext` dataclass
2. Create `domain.yaml` schema and parser
3. Create `convention-fields.yaml` schema and parser
4. Build domain pack discovery (bundled / user / project)
5. Add `domain` key to `GPDProjectConfig`
6. Tests for domain pack loading

### Phase 2: Extract physics content into domain pack
1. Create `src/grd/domains/physics/` directory structure
2. Move convention definitions to `convention-fields.yaml`
3. Move subfield references to domain pack
4. Move protocols to domain pack
5. Move error catalogs to domain pack
6. Move journal templates to domain pack
7. Tests: physics domain pack loads correctly and matches current behavior

### Phase 3: Make core engine domain-aware
1. Refactor `ConventionLock` to dict-based model
2. Refactor `conventions.py` to read from domain context
3. Refactor `config.py` `MODEL_PROFILES` to merge core + domain
4. Refactor `registry.py` to merge core + domain commands/agents
5. Refactor MCP servers to load domain content dynamically
6. Refactor verification framework to use domain protocols/errors
7. Refactor publication module to use domain journal templates
8. Add domain selection to `new-project` flow
9. Tests: all existing tests pass with `domain=physics`

### Phase 4: Rename GPD → GRD
1. Rename `src/gpd/` → `src/grd/`
2. Update all imports
3. Update `pyproject.toml`, `package.json`
4. Update all command/agent names (`gpd:` → `grd:`, `gpd-` → `grd-`)
5. Update env vars (`GPD_*` → `GRD_*`)
6. Update `.gpd/` → `.grd/` directory name
7. Update all infra JSON files
8. Update `README.md`
9. Update `bin/install.js`
10. Add backward-compat aliases
11. Create migration script for existing projects
12. Tests: all tests pass with new names

### Phase 5: Move physics-specific commands/agents to domain pack
1. Move `derive-equation`, `dimensional-analysis`, `limiting-cases`, etc. to physics domain pack
2. Move `gpd-review-physics`, `gpd-notation-coordinator`, etc. to physics domain pack
3. Move `arxiv-submission` to physics domain pack (or generalize to `submit-paper`)
4. Ensure core command set works without any domain pack loaded
5. Tests: domain-less operation works; physics domain pack restores full command set

### Phase 6: Create domain pack template and docs
1. Create `domains/_template/` with empty domain pack structure
2. Write domain pack authoring documentation
3. Create example minimal domain pack (e.g., `generic-science`)
4. Update README with domain pack instructions

---

## 7. Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing physics users | Phase 2 extracts without changing behavior; Phase 3 makes it dynamic but defaults to physics; comprehensive test coverage |
| Convention lock migration | Migration script + backward compat detection of old format |
| Scope creep in "what's domain-specific" | Clear rule: if it mentions a physics concept by name, it's domain-specific. If it's about research methodology in general, it stays in core |
| Dynamic model generation complexity | Use the simpler dict-based approach for ConventionLock instead of runtime Pydantic model generation |
| MCP server compatibility | MCP servers keep same tool interface, just load content from domain pack instead of hardcoded paths |
| npm/PyPI rename | Coordinate release; old package name can redirect to new |

---

## 8. Open Questions for Review

1. **Should `grd-review-math` stay in core?** Math review is cross-domain, but the current
   implementation is deeply physics-flavored. Options: (a) keep in core with generic math focus,
   (b) move to physics pack and let domains provide their own analytical review stage.

2. **Should some verification commands stay in core?** `dimensional-analysis` and `limiting-cases`
   are physics concepts. But analogues exist in other domains (unit analysis, edge-case testing).
   Options: (a) generalize names and keep in core, (b) move to physics pack.

3. **Domain pack versioning?** Should domain packs declare a minimum engine version? Probably yes
   for third-party packs.

4. **Multi-domain projects?** Should a project be able to use conventions from multiple domain
   packs (e.g., biophysics = biology + physics)? Probably not in v1 — use `custom_conventions`
   for cross-domain needs.

5. **Rename timing:** Should the GPD→GRD rename happen first (Phase 4) or last? Doing it last
   means all intermediate work uses old names. Doing it first means a big disruptive change
   before the domain architecture is in place. Recommendation: last, as shown above.

6. **Should we keep `arxiv-mcp-server` as a core dependency?** It's physics/academic-specific.
   Options: (a) make it an optional dependency, (b) move to physics domain pack's requirements.

---

## 9. Size Estimate

| Phase | Files changed | New files | Complexity |
|-------|--------------|-----------|------------|
| Phase 1: Domain pack infra | ~5 | ~8 | Medium |
| Phase 2: Extract physics | ~0 | ~70 | Low (file moves) |
| Phase 3: Core engine | ~15 | ~3 | High |
| Phase 4: Rename | ~200+ | ~0 | Low (mechanical) |
| Phase 5: Move commands/agents | ~20 | ~5 | Medium |
| Phase 6: Template & docs | ~2 | ~5 | Low |

**Total: ~240 files touched, ~90 new files**

This is a significant refactor but mechanically straightforward — the hard part is
Phase 3 (making the core engine domain-aware) and getting the domain pack loading right.
