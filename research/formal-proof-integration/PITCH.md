# Pitch: Native Formal Proof Support in GRD

**Author:** bob (getresearch/crew)
**Date:** 2026-04-11
**Bead:** ge-plk
**Status:** Proposal for Rome's review
**Shipped vs. planned:** [STATUS.md](./STATUS.md) — canonical matrix of every `/grd:*` skill and `grd lean …` CLI command this pitch promises, tagged `shipped / planned / n/a`. Check it before assuming something exists.

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

### Design constraint: CLI + skills, not MCP

**Context cost matters.** MCP server tool schemas get injected into every agent turn's context window. A new `grd-lean` server with 6 tools could add ~2–4k tokens per turn — a tax paid on every prompt, for every project, whether formal proofs are in use or not. For a feature that most phases won't touch, that's too expensive.

**GRD already has the right primitive:** the `grd` CLI and the slash-command skill system. Skills are loaded lazily (only when invoked), and CLI output is consumed only when an agent chooses to read it. This is the right surface for an opt-in verification backend.

### New Components

#### 1. `grd lean` CLI subcommands (new)

Rather than an MCP server, formal-proof operations live as subcommands of the existing `grd` CLI, backed by a Python module (`grd.lean`) that manages the Pantograph/Kimina connection:

```bash
grd lean check <file-or-inline>          # Type-check Lean 4 code → {success, errors[], goals[]}
grd lean prove <stmt> [--ctx path]       # Attempt automated proof → {proof, tactics_tried, elapsed}
grd lean verify-claim <claim-id>         # Bind claim → typechecked Lean theorem → evidence
grd lean blueprint-status [--phase N]    # Dep-graph status: formalized / ready / blocked / total
grd lean typecheck-file <path>           # Full file typecheck via Lake
grd lean serve-repl                      # Start persistent REPL daemon (per-project)
grd lean stop-repl                       # Shut it down
```

All commands emit JSON with `--raw` for agent consumption. Human-readable output by default for interactive use.

**Exit codes.** Every `grd lean` subcommand uses a split exit code so shell callers and CI can route without parsing JSON:

| Code | Meaning | Examples |
|------|---------|---------|
| 0 | Success | Clean typecheck, proof found, env ready |
| 1 | Soft-fail | Lean elaboration error, no tactic closed the goal, faithfulness rejection |
| 2 | User input error | Bad flag combo, missing required argument, file not found |
| 3 | Environment / bootstrap error | `lean` not found, Mathlib cache stale, consent required |
| 4 | Internal / daemon error | Backend crashed, socket failure, unexpected exception |

**Daemon model for speed.** A first `grd lean check` starts a Pantograph REPL subprocess and keeps it alive via a per-project Unix socket (`.grd/lean-repl.sock`). Subsequent calls reuse it (~50 ms round-trip vs. ~3 s cold start). Idle timeout (default 10 min) shuts it down. The daemon is managed transparently — users never need to invoke `serve-repl` / `stop-repl` manually; they exist only for debugging.

**Skills wrap the CLI.** User-facing invocations are skills that orchestrate the right CLI calls:

```
/grd:formalize-claim <claim-id>   → calls grd lean verify-claim, writes blueprint stub
/grd:prove <statement>            → calls grd lean prove, retries with premise retrieval
/grd:blueprint-status             → calls grd lean blueprint-status, renders graph
/grd:init-blueprint               → scaffolds blueprint/ directory in current phase
/grd:lean-bootstrap               → runs the lazy install flow (see Bootstrap below)
```

Skills only enter context when the user invokes them. No per-turn tax.

**Backend:** Pantograph (Python ↔ Lean REPL with JSON protocol) by default. Kimina Lean Server as optional parallel backend when batch verifying a whole phase.

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
tools: file_read, file_write, shell, search_files, find_files
role_family: verification
surface: internal
```

The agent invokes `grd lean ...` subcommands via the shell tool. No MCP tool injection needed.

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

- Implement lazy bootstrap skill (`/grd:lean-bootstrap`) that installs elan, Lean toolchain, Pantograph on demand
- Implement `grd lean check` and `grd lean typecheck-file` CLI subcommands
- Implement persistent REPL daemon with Unix-socket reuse
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

**Goal:** GRD agents can attempt proofs autonomously. Pipeline grounded in the SOTA survey at `AUTOFORMALIZATION.md` (polecat research).

**3.1 Autoformalization pipeline** (inside `grd lean prove` / `grd lean verify-claim`, not a new MCP):

| Stage | What it does | Method (SOTA anchor) |
|---|---|---|
| 1. Extract | Pull claim + conventions + deps from phase artifacts | leanblueprint `\lemma{}\uses{}` |
| 2. Retrieve | Ground against pinned Mathlib4 + PhysLean snapshot | DDR-style name-index + Suffix Array Check |
| 3. Generate | N=4 (MVP) / N=16 (pro) candidate Lean statements | Claude Sonnet 4.5, DRAFT-SKETCH-PROVE framing |
| 4. Compile-repair | APOLLO-style loop: compile → classify error → repair | 10-20 compiles/claim budget |
| 5. Faithfulness | Back-translate to English; SBERT sim; symbolic-equiv cluster | ConsistencyCheck + GTED/ASSESS ranking |
| 6. Gate | ≥0.85 auto-accept, 0.7-0.85 symbolic cluster, <0.7 `bd new -l human` | Escalation surfaces specific ambiguity |

**3.2 Concrete deliverables:**

- `grd lean prove` with Pantograph-backed tactic search and APOLLO repair loop
- `grd lean verify-claim` running stages 1-6 above
- `grd-prover` agent definition (uses CLI + skills only — no new MCPs)
- Grounded retrieval index over pinned Mathlib4 + PhysLean snapshot (rebuilt on `grd lean sync`)
- Back-translation faithfulness gate with configurable thresholds in `.grd/lean-env.json`
- `/grd:formalize-claim` and `/grd:prove` skills
- ProofFlow-style dependency-DAG decomposition for multi-lemma claims
- End-to-end test on real GRD phase: formalize one result from the geometry analysis research

**3.3 Budget targets:** MVP ~$10-100 per 50-claim phase at current API pricing; ≥40-60% of simple claims auto-accepted; remainder escalated with the specific ambiguity attached to the bead.

**3.4 Deferred to later phase:** ensemble-of-3 model voting, Kimina-Prover-72B / DeepSeek-Prover-V2 as the core prover, test-time RL (AlphaProof-style). These land in Phase 4+ or flagship-milestone opt-in.

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

---

## System Requirements & Bootstrap (Lazy, Non-Blocking)

**Principle:** No user pays cost for features they don't use. Bootstrap happens **on first invocation of a formal-proof skill**, not at GRD install time. Blocking prompts are minimized: if we can auto-install without root/sudo, we do. If we need sudo or the user's judgment, we offer the feature in a degraded mode and continue.

### Bootstrap Skill: `/grd:lean-bootstrap`

Idempotent. Detects existing install, skips what's present, installs the rest. Stages:

| Stage | Action | Blocks user? |
|---|---|---|
| 0 | Check `.grd/lean-env.json` — if up-to-date, exit | No |
| 1 | Install `elan` (user-local, ~15 MB) via official installer | No — writes to `~/.elan/` only |
| 2 | Install project Lean toolchain (~400 MB–1 GB, pinned via `lean-toolchain` file) | No — background download with progress |
| 3 | `pip install pantograph leanblueprint plastex` into GRD venv (~100 MB) | No |
| 4 | Install `graphviz` (system package, ~10 MB) | **Auto-install if we can** — detect apt/brew/pacman, run without sudo if user-package manager, fall back to degraded-mode message only if root required. Never prompt. |
| 5 | Install `tectonic` for LaTeX (single binary, ~50 MB, downloads packages on demand) | No — prefer tectonic over TeX Live (95% smaller). Skip if any working LaTeX compiler (`pdflatex`, `xelatex`, `lualatex`, `tectonic`) already present. |
| 6 | (Optional) Download Mathlib olean cache via `lake exe cache get` (~8–12 GB) | **Ask once, remember.** Only triggered when user first writes Lean code that imports Mathlib. |
| 7 | (Optional) LeanDojo + premise index (~3–5 GB) | **Ask once, remember.** Only triggered when premise retrieval is enabled for proving. |

Write `.grd/lean-env.json` after each stage — crash-safe, resumable.

### Non-Blocking Dependency Handling

**Graphviz.** Needed for rendering Blueprint dependency graphs as SVG/PNG.
- Auto-install via user-local package manager (`brew`, `apt` with user-available packages, `pacman` for `yay`/`paru` users, `nix-env`).
- If system-level install would need root: render an **ASCII dep graph** to the terminal (no graphviz needed) and note that `SVG rendering requires graphviz — run 'sudo apt install graphviz' or set GRD_GRAPHVIZ_PATH`. User gets the dependency information; just not the pretty picture.
- Don't install unless actually needed (first call to `grd lean blueprint-status --svg` or equivalent).

**TeX / LaTeX.** Needed for PDF rendering of Blueprint (HTML rendering works without).
- Detect in order: `tectonic` → `pdflatex`/`xelatex`/`lualatex` (TeX Live or MikTeX) → `pandoc` with `--pdf-engine=wkhtmltopdf` or HTML-only output.
- If none: default to HTML-only Blueprint output. LaTeX PDF is a nice-to-have, not a blocker.
- If the user explicitly asks for PDF: install `tectonic` (single binary, user-local, ~50 MB). Tectonic downloads required TeX packages on demand — no multi-GB TeX Live install ever.
- Never install full TeX Live unless user explicitly requests it.

**Visualization generally.** Ad hoc, not shipped by default. Offer it when the user's task benefits (e.g., "show me the dependency graph"), install the minimal tool for that task only, cache the install for later.

### Storage Requirements (revised with tectonic)

| Component | Location | Size | When |
|---|---|---|---|
| elan + Lean toolchain | `~/.elan/` | **~400 MB–1 GB** per toolchain | First bootstrap |
| Pantograph + Python deps | GRD venv | ~100 MB | First bootstrap |
| graphviz (system) | OS package dir | ~10 MB | First blueprint render, if graph requested |
| tectonic (system) | `~/.local/bin/` or user bindir | ~50 MB | First PDF request, if needed |
| tectonic on-demand TeX cache | `~/.cache/Tectonic/` | ~200 MB steady-state | As needed per document |
| Project `.lake/` build cache | `{project}/blueprint/.lake/` | ~200–500 MB per phase using Lean | First `lake build` |
| Mathlib4 olean cache (optional) | Project Lake cache | **~8–12 GB** | On opt-in via `lake exe cache get` |
| LeanDojo premise index (optional) | `~/.cache/leandojo/` | **~3–5 GB** | On opt-in for premise retrieval |

**Minimum viable install (Phase 1, no Mathlib):** ~1.5 GB.
**Typical install (Phase 2 blueprints, HTML only):** ~1.7 GB.
**Full install (Mathlib + LeanDojo + tectonic PDFs):** ~18–22 GB.

### Generic Agent Bootstrap Instructions (Skill Body)

When an agent encounters a formal-proof workflow, it:

```
1. Read .grd/lean-env.json
   - If present and up-to-date → proceed
   - If missing or stale → invoke /grd:lean-bootstrap

2. /grd:lean-bootstrap logic:
   a. Inspect host: which package managers are available? which Lean toolchain is pinned?
   b. Run stages 1–3 unconditionally (no user confirmation — these are user-local, reversible)
   c. Run stage 4 (graphviz) only on first call that requires graph rendering.
      - If user-package manager works: install silently.
      - Else: proceed in degraded mode (ASCII graphs), note the limitation in output.
   d. Run stage 5 (tectonic) only if PDF requested and no working LaTeX engine exists.
   e. Stages 6 and 7 are opt-in. On first trigger, the skill asks:
      "This will download ~10 GB of Mathlib cache. Proceed? [y/N/never]"
      Response is recorded in .grd/lean-env.json. "never" means skip forever until manually re-enabled.

3. On any stage failure:
   - Log the failure to .grd/lean-env.json with diagnostic.
   - Continue with available functionality — do not abort the overall workflow.
   - Surface the degradation to the user so they can decide whether to address it.

4. Teardown: /grd:lean-bootstrap --uninstall
   - Removes ~/.elan/, .lake/ caches, ~/.cache/leandojo/, ~/.cache/Tectonic/
   - Does not remove system-installed graphviz or tectonic (user might use them elsewhere)
```

**Cross-agent compatibility.** The bootstrap skill is self-contained — any agent (grd-executor, grd-prover, user's own agents) can invoke it. It doesn't assume the caller is a specific agent type. Bootstrap output is structured JSON so callers can parse it.

---

## Parallel Work: Tracking External Improvements

As implementation proceeds, we'll inevitably find friction points in upstream tooling (Leanblueprint, Pantograph, LeanDojo, Kimina server, etc.). These get captured in bead `ge-cch` as a running list:

- Target repository + issue/PR link if applicable
- GRD commit that surfaced the friction
- Severity: bug / feature / developer-experience
- Blocking for GRD? (If non-blocking, continue; if blocking, escalate to user for PR-approval decision)

**Default behavior:** Work around the friction locally. **Do not submit upstream PRs without explicit approval from Rome.** When we have a batch of improvements worth pitching, surface them for review.

---

## Testing Strategy

Captured in bead `ge-h0j`. The test matrix covers:

1. **Bootstrap from a clean machine** — fresh VM / docker container → `/grd:lean-bootstrap` → Lean works
2. **Typechecking tiers** — trivial (`1 + 1 = 2`), moderate (Cauchy-Schwarz in ℝⁿ), hard (a real lemma requiring Mathlib import)
3. **Blueprint rendering** — dep graph renders correctly with colors matching formalization status
4. **Autoformalization round-trip** — take a real claim from the geometry analysis research, translate to Lean, check faithfulness
5. **Proof attempt** — grd-prover produces a proof for at least one non-trivial claim without human-written Lean
6. **Convention bridge completeness** — all 18 convention fields generate valid Lean type class instances
7. **Verification coverage report** — formal status correctly surfaced in `/grd:progress`
8. **State persistence** — formal evidence recorded in `state.json` `intermediate_results[].verification_records[]` and survives session restart
9. **Context cost measurement** — skill-based invocation does not measurably bloat agent context vs. the pre-formal-proofs baseline (the whole reason we rejected MCP)
10. **Teardown** — `/grd:lean-bootstrap --uninstall` cleanly removes all GRD-added artifacts

Each test row: pass/fail, commit SHA, evidence path. No phase is "done" until its tests are green.

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
