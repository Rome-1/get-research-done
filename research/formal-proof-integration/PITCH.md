# Pitch: Native Formal Proof Support in GRD

**Author:** bob (getresearch/crew)
**Date:** 2026-04-11
**Bead:** ge-plk
**Status:** Proposal for Rome's review

---

## Executive Summary

GRD currently verifies research through LLM-driven heuristic checks: dimensional analysis, limiting cases, numerical spot-checks, and symmetry verification. These are powerful but fundamentally *probabilistic* — they catch errors with high confidence but cannot guarantee correctness.

Formal proof languages (Lean 4, Coq, Isabelle) offer *machine-checked certainty*. A theorem verified in Lean is correct — period. The proposal is to integrate formal proof capabilities into GRD as a **new verification backend** alongside the existing heuristic system, using the **Blueprint methodology** to bridge informal research derivations and formal proofs.

This is not about replacing GRD's current verification. It's about adding a higher tier of certainty for claims that warrant it.

---

## The Opportunity

### Why now?

1. **Lean 4 ecosystem maturity.** Mathlib4 has 1.9M lines covering undergraduate and graduate mathematics. PhysLib/PhysLean is formalizing physics. SciLean provides scientific computing primitives. The infrastructure exists.

2. **AI-assisted proving works.** AlphaProof reached IMO silver-medal level. LeanDojo + ReProver achieve 50%+ on miniF2F. BFS-Prover-V2 hits 95% on miniF2F. COPRA demonstrates in-context LLM proving. The gap between "informal math" and "formal proof" is shrinking fast.

3. **Blueprint methodology is proven.** Terence Tao's PFR formalization demonstrated that large collaborative proofs can be organized via dependency graphs linking informal statements to Lean declarations. Leanblueprint (Patrick Massot) provides mature tooling.

4. **ProofFlow (2025) bridges the gap.** The ProofFlow pipeline constructs dependency DAGs from informal proofs and systematically formalizes each step as an intermediate lemma — exactly what GRD's phase-based workflow already does informally.

5. **GRD's architecture is ready.** The MCP server system, domain packs, protocol bundles, and contract-aware verification provide clean extension points. A formal proof backend is a natural addition, not an architectural stretch.

### What GRD gains

| Current State | With Formal Proofs |
|---|---|
| "Dimensional analysis passed" (heuristic) | "Theorem dim_consistent : ..." (proved) |
| "Limiting case recovered numerically" (±ε) | "Theorem limit_recovery : lim x→0 f(x) = g" (exact) |
| "Conservation law checked at 5 test points" | "Theorem energy_conserved : ∀ t, E(t) = E(0)" (universal) |
| Verification confidence: high | Verification confidence: certain |
| Reproducible by re-running checks | Reproducible by type-checking |

---

## Architecture Design

### Integration Model: Blueprint-First

The design mirrors how Leanblueprint works, adapted to GRD's phase structure:

```
GRD Phase Derivation          Blueprint Layer              Lean 4
─────────────────────    ─────────────────────────    ──────────────
                         
  PLAN.md task 1    ──→   blueprint/stmt_1.tex    ──→   Thm stmt_1
  PLAN.md task 2    ──→   blueprint/stmt_2.tex    ──→   Thm stmt_2  
  ...                      dependency graph              ...
  SUMMARY.md        ──→   blueprint/main_thm.tex  ──→   Thm main
                         
  VERIFICATION.md   ←──   proof status tracker    ←──   Lean check
```

**Key insight:** GRD phases already decompose research into atomic steps with dependency tracking. A Blueprint is essentially the same structure but with formal statement targets instead of informal verification checks.

### New Components

#### 1. `grd-lean` MCP Server (new)

A new MCP server exposing formal proof tools:

```python
# Tools exposed:
lean_check(code: str) -> LeanCheckResult
    # Type-check Lean 4 code, return errors/goals
    
lean_prove(statement: str, context: str) -> ProofResult  
    # Attempt automated proof via tactic search
    # Uses Pantograph REPL under the hood
    
lean_verify_claim(claim_id: str, lean_file: str) -> VerificationEvidence
    # Verify a contract claim maps to a checked Lean theorem
    
blueprint_status(phase: str) -> BlueprintStatus
    # Parse blueprint dependency graph, return formalization progress
    
lean_typecheck_file(path: str) -> TypecheckResult
    # Full file typecheck via Lake
```

**Backend:** Communicates with Lean 4 via Pantograph (Python ↔ Lean REPL with JSON protocol) or Kimina Lean Server (REST API for parallel verification). No subprocess spawning per check — persistent server connection.

#### 2. Blueprint Phase Artifact

New optional artifact in phase directories:

```
phases/03/
  PLAN.md
  CONTEXT.md
  SUMMARY.md
  VERIFICATION.md
  blueprint/                  ← NEW
    content.tex               # Informal statements + \lean{} refs
    lakefile.lean             # Lean project config
    Proofs/
      Stmt1.lean              # Formal proof files
      Stmt2.lean
    Blueprint.lean            # Module root
```

The blueprint is *optional*. Phases without formal proof targets work exactly as today.

#### 3. `grd-prover` Agent (new)

A new specialized agent, analogous to `grd-verifier` but for formal proofs:

```yaml
name: grd-prover
description: Translates informal claims into formal Lean 4 statements and 
  attempts proof via tactic search, AI-assisted proving, and manual guidance.
tools: file_read, file_write, shell, search_files, find_files, 
       mcp__grd-lean__lean_check, mcp__grd-lean__lean_prove,
       mcp__grd-lean__lean_verify_claim, mcp__grd-lean__blueprint_status
role_family: verification
surface: internal
```

**Workflow:**
1. Reads phase SUMMARY.md and contract claims
2. Translates key claims into Lean 4 theorem statements (autoformalization)
3. Attempts proof via: (a) Lean-auto/aesop tactics, (b) LeanDojo-style tactic search, (c) manual construction guided by the informal derivation
4. Records proof status back to blueprint dependency graph
5. Returns formal verification evidence to grd-verifier

#### 4. Verification Check Extensions

New verification checks in the registry:

```python
VerificationCheckDef(
    check_id="5.20",
    check_key="universal.formal_statement",
    name="Formal statement",
    description="Key claim has a corresponding formal Lean 4 statement that typechecks",
    tier=3,
    catches="Informal claims with no precise formal counterpart",
    evidence_kind="structural",
),
VerificationCheckDef(
    check_id="5.21", 
    check_key="universal.formal_proof",
    name="Formal proof",
    description="Formal Lean 4 statement has a machine-checked proof",
    tier=4,
    catches="Claims believed true but not formally verified",
    evidence_kind="computational",
),
```

These integrate with existing contract-aware verification — a claim can be bound to both heuristic checks (5.1-5.19) AND formal checks (5.20-5.21).

#### 5. Convention Bridge

GRD's 18-field convention lock maps naturally to Lean type classes:

```lean
-- GRD convention: metric_signature = "mostly-minus"
class MetricSignature where
  signature : Fin 4 → SignChoice  -- (+,-,-,-)

-- GRD convention: natural_units = "natural"  
class NaturalUnits where
  c_eq_one : c = 1
  hbar_eq_one : ℏ = 1

-- Convention assertions become type class instances
instance : MetricSignature := ⟨fun i => match i with | 0 => .plus | _ => .minus⟩
```

The `grd-lean` server can auto-generate convention preambles from `state.json` convention locks, ensuring formal proofs inherit the same conventions as informal derivations.

### Integration with Existing Workflow

```
/grd:plan-phase
  └─ grd-planner identifies claims suitable for formalization
  └─ Adds blueprint targets to PLAN.md (optional flag: --formal-targets)

/grd:execute-phase  
  └─ grd-executor produces informal derivation (as today)
  └─ grd-prover translates key claims → Lean statements
  └─ grd-prover attempts proofs

/grd:verify-work
  └─ grd-verifier runs heuristic checks (5.1-5.19, as today)
  └─ grd-verifier also checks formal status (5.20-5.21)
  └─ Blueprint status feeds into verification coverage report

/grd:progress
  └─ Shows both informal completion % and formal proof %
  └─ Blueprint dependency graph rendered in terminal
```

---

## Language Recommendation: Lean 4 Primary, Others Optional

### Why Lean 4 as primary

| Factor | Lean 4 | Coq/Rocq | Isabelle | Agda |
|---|---|---|---|---|
| **AI integration** | Best (LeanDojo, Pantograph, AlphaProof) | Good (SerAPI, CoqHammer) | Good (Sledgehammer) | Limited |
| **Math library** | Mathlib4 (1.9M lines) | MathComp, stdlib | AFP (large) | agda-stdlib |
| **Physics libraries** | PhysLib, SciLean, HepLean | Limited | Limited | None |
| **Programmatic API** | Pantograph (Python↔Lean), Kimina Server | SerAPI | Isabelle/PIDE | None mature |
| **Language ergonomics** | Modern, fast, compiled to C | Mature but dated | Good | Clean but niche |
| **Community momentum** | Fastest growing (2024-2026) | Stable | Stable | Small |
| **Blueprint tooling** | Leanblueprint (mature) | None equivalent | None equivalent | None |

**Lean 4 wins on every axis that matters for GRD integration:** AI-assisted proving, programmatic access, physics libraries, and Blueprint tooling.

### Multi-backend option (future)

The MCP server architecture allows adding Coq/Isabelle backends later:

```json
// .mcp.json (future)
{
  "grd-lean": { ... },      // Primary
  "grd-coq": { ... },       // Optional backend
  "grd-isabelle": { ... }   // Optional backend
}
```

Each backend would expose the same tool interface (`verify_claim`, `check`, `prove`), allowing the verification system to be backend-agnostic. But Lean 4 should be the first and primary target.

---

## Blueprint Methodology Integration

### How Blueprint maps to GRD

| Blueprint Concept | GRD Equivalent |
|---|---|
| Informal statement (LaTeX) | Phase claim / contract claim |
| Dependency graph edge | Phase dependency / `depends_on[]` |
| `\lean{TheoremName}` | Lean file in `blueprint/Proofs/` |
| `\leanok` (formalized) | Verification check 5.21 passed |
| `\uses{dep1, dep2}` | `intermediate_results[].depends_on[]` |
| Color-coded graph (green=done) | `/grd:progress` formal coverage % |

### New GRD commands

```bash
/grd:init-blueprint          # Initialize blueprint structure in current phase
/grd:blueprint-status        # Show dependency graph + formalization progress  
/grd:formalize-claim <id>    # Translate a contract claim → Lean statement
/grd:prove <statement>       # Attempt to prove a Lean statement
/grd:lean-check              # Typecheck all Lean files in current phase
```

---

## Risk Assessment

### Technical risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Autoformalization failure rate.** LLMs still struggle with complex formalizations. | High | Start with simple claims (inequalities, conservation laws). Build difficulty gradually. Human-in-the-loop for hard cases. |
| **Lean 4 breaking changes.** Lean 4 is still evolving. | Medium | Pin Lean toolchain version per project. Lake manages dependencies. |
| **Mathlib/PhysLib gaps.** Many physics concepts lack formal library support. | High | Use SciLean for numerical, PhysLib for physics. Accept that some claims cannot be formalized yet — that's information, not failure. |
| **Performance.** Lean typechecking can be slow for large proofs. | Medium | Kimina Lean Server provides parallelization + caching. Incremental checking via Lake. |
| **Complexity overhead.** Adding Lean to every phase is too heavy. | Low | Blueprint is *optional*. Most phases use heuristic verification only. Formal proofs target high-value claims. |

### Adoption risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Learning curve.** Researchers need Lean 4 literacy. | Medium | GRD agents do the translation. Researcher reviews, doesn't write Lean. |
| **Diminishing returns.** Formalizing obvious results wastes effort. | Low | Formalize selectively: novel claims, surprising results, cornerstone lemmas. |
| **Ecosystem fragmentation.** Multiple proof languages split effort. | Low | Lean 4 primary. Others only if specific project demands it. |

---

## Implementation Phases

### Phase 1: Foundation (4-6 weeks)

**Goal:** Lean 4 ↔ GRD communication works. Can typecheck Lean files from within a GRD workflow.

- Install Lean 4 toolchain management (elan)
- Implement `grd-lean` MCP server with `lean_check` and `lean_typecheck_file` tools
- Use Pantograph REPL as backend
- Add Lean project scaffolding to phase init (`lakefile.lean` template)
- Add verification checks 5.20 (formal statement) and 5.21 (formal proof) to registry
- Test on simple mathematical identity (e.g., Cauchy-Schwarz)

### Phase 2: Blueprint Integration (3-4 weeks)

**Goal:** Blueprint structure lives inside GRD phases. Dependency graphs rendered.

- Integrate Leanblueprint as Python dependency
- Create `blueprint/` artifact template for phases
- Implement `blueprint_status` MCP tool
- Map GRD contract claims to Blueprint LaTeX statements
- Implement `/grd:init-blueprint` and `/grd:blueprint-status` commands
- Convention bridge: auto-generate Lean preamble from convention lock

### Phase 3: AI-Assisted Proving (4-6 weeks)

**Goal:** GRD agents can attempt proofs autonomously.

- Implement `lean_prove` MCP tool using Pantograph tactic search
- Create `grd-prover` agent definition
- Integrate with LeanDojo for premise retrieval
- Implement `/grd:formalize-claim` and `/grd:prove` commands
- Implement ProofFlow-style dependency DAG → lemma decomposition
- Test on real GRD phase: formalize a geometry analysis result

### Phase 4: Domain Packs and Polish (3-4 weeks)

**Goal:** Physics-specific formal proof support. Production quality.

- Create `formal-verification` domain pack with physics-specific tactics
- Convention type class library (metric signature, units, etc.)
- Integration with PhysLib/HepLean for physics formalizations
- Verification coverage report includes formal proof status
- Documentation and user guide
- Performance optimization (Kimina server for batch checking)

### Phase 5: Multi-Backend (Future, Optional)

**Goal:** Support Coq/Isabelle as alternative backends.

- Abstract proof-backend interface
- Implement Coq backend via SerAPI
- Implement Isabelle backend via Isabelle/PIDE
- Cross-backend statement translation (where possible)

---

## Effort Estimate

| Phase | Effort | Dependencies |
|---|---|---|
| Phase 1: Foundation | 4-6 weeks | Lean 4 toolchain, Pantograph |
| Phase 2: Blueprint | 3-4 weeks | Phase 1, Leanblueprint |
| Phase 3: AI Proving | 4-6 weeks | Phase 2, LeanDojo |
| Phase 4: Domain Packs | 3-4 weeks | Phase 3, PhysLib |
| Phase 5: Multi-Backend | Future | Phase 4 |
| **Total (Phases 1-4)** | **14-20 weeks** | |

---

## Success Criteria

1. **Phase 1 gate:** `lean_check("theorem test : 1 + 1 = 2 := by norm_num")` returns `{success: true}` from within a GRD verification workflow.

2. **Phase 2 gate:** A GRD phase has a rendered Blueprint dependency graph with ≥3 nodes linked to Lean declarations.

3. **Phase 3 gate:** `grd-prover` autonomously proves ≥1 non-trivial claim from a real GRD research phase without human Lean code.

4. **Phase 4 gate:** A complete GRD research phase (e.g., polyhedral cone hypothesis from geometry analysis) has formal proofs for its top 3 claims, with verification evidence recorded in `state.json`.

---

## References

- [Leanblueprint](https://github.com/PatrickMassot/leanblueprint) — Patrick Massot's plasTeX plugin for formalization blueprints
- [Terence Tao's PFR Formalization Tour](https://terrytao.wordpress.com/2023/11/18/formalizing-the-proof-of-pfr-in-lean4-using-blueprint-a-short-tour/)
- [LeanDojo](https://leandojo.org/) — AI-driven theorem proving infrastructure for Lean
- [Pantograph](https://link.springer.com/chapter/10.1007/978-3-031-90643-5_6) — Machine-to-machine interaction interface for Lean 4
- [Kimina Lean Server](https://arxiv.org/html/2504.21230v1) — Fast REST API for Lean interaction
- [ProofFlow](https://arxiv.org/abs/2510.15981) — Dependency graph approach to proof autoformalization
- [AlphaProof](https://www.emergentmind.com/topics/alphaproof) — DeepMind's RL-based formal math system
- [COPRA](https://arxiv.org/pdf/2310.04353) — In-context learning agent for theorem proving
- [PhysLib](https://physlib.io/) — Physics formalization library for Lean 4
- [HepLean](https://arxiv.org/html/2411.07667v1) — High energy physics index notation in Lean 4
- [SciLean](https://github.com/lecopivo/SciLean) — Scientific computing in Lean 4
- [Lean4Physics](https://arxiv.org/html/2510.26094v1) — College-level physics reasoning framework
- [APOLLO](https://arxiv.org/html/2505.05758v1) — Automated LLM and Lean collaboration
- [Lean-Auto](https://link.springer.com/chapter/10.1007/978-3-031-98682-6_10) — ATP-based proof automation in Lean 4
