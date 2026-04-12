# Autoformalization for GRD: State of the Art and Recommended Pipeline

*Research report, April 2026. Target: integrating formal-proof support into GRD (Get Research Done), a Claude-Code-based research workflow tool that processes informal claims from research phases and converts them into type-checking Lean 4 statements with automated proofs.*

---

## 1. Executive summary

Autoformalization, the translation of informal mathematics (and increasingly physics) into machine-checkable Lean 4, has moved from "interesting research direction" in 2023 to "usable-but-brittle tooling" in early 2026. Three trends define the current frontier:

1. **Retrieval-grounded, dependency-graph pipelines** (Aria, ProofFlow, DDR) have replaced flat "NL-to-Lean" prompting as the default for statement- and proof-level autoformalization. They now achieve >90% compilation and ~60-70% *faithful* formalization on ProofNet.
2. **Whole-proof RL reasoning models** (Kimina-Prover-72B, DeepSeek-Prover-V2-671B, Goedel-Prover-V2, Seed-Prover 1.5) dominate proof-*search* for olympiad/undergrad mathematics, with miniF2F pass rates now >88-90%. On research-level and physics benchmarks (LeanPhysBench) they are far weaker (16-35%).
3. **The faithfulness gap remains the dominant unsolved problem.** Even on well-specified competition math, expert humans disagree with themselves up to 38.5% of the time on whether a formalization is semantically faithful ([ReForm, 2025](https://arxiv.org/abs/2510.24592)). For physics or research-level mathematics with context-dependent conventions, *no evaluation metric yet correlates well with expert judgment in the absence of a blueprint structure*.

For GRD specifically, the practical recommendation (elaborated in Section 8) is: do not attempt blind end-to-end autoformalization. Use a **Blueprint-style pipeline** ([Massot, used by Tao for PFR](https://terrytao.wordpress.com/2023/11/18/formalizing-the-proof-of-pfr-in-lean4-using-blueprint-a-short-tour/)) with DAG decomposition, retrieval grounding against Mathlib4/PhysLean, multi-candidate generation + back-translation ranking, and explicit "needs-human" gates on faithfulness.

---

## 2. Statement-level autoformalization: state of the art

### 2.1 Benchmarks and where they live

- **miniF2F** (olympiad-style): 244 problems, near-saturated. Goedel-Prover-V2-32B reaches 90.4% pass@32 with self-correction; Kimina-Prover-72B 80.7% pass@8192 ([Goedel-Prover-V2](https://arxiv.org/abs/2508.03613), [Kimina-Prover](https://arxiv.org/abs/2504.11354)). A recent review ([miniF2F-Lean Revisited](https://arxiv.org/html/2511.03108v1)) argues miniF2F is now too easy and has annotation issues.
- **ProofNet / ProofNet#**: 186 undergrad analysis/algebra problems. Core benchmark for statement-level autoformalization. Aria achieves 91.6% compile and 68.5% "final accuracy" ([Aria, 2025](https://arxiv.org/abs/2510.04520)). DDR-augmented models beat traditional RAG.
- **FormalMATH** ([SphereLab, 2025](https://arxiv.org/pdf/2505.02735)): 5,560 formally verified statements spanning algebra, geometry, calculus, number theory, discrete math, at HS-olympiad through undergraduate level. 22.8× larger than miniF2F.
- **PutnamBench**: Putnam competition problems. Seed-Prover 1.5 solves 88% of PutnamBench, including 11/12 of Putnam 2025 problems ([Seed-Prover 1.5, 2025](https://arxiv.org/abs/2512.17260)).
- **LeanPhysBench** (part of Lean4PHYS): 200 hand-crafted college-level physics theorems. Best LLM: Claude Sonnet 4 at 35%; DeepSeek-Prover-V2-7B at 16%. PhysLib-in-context boosts accuracy +11.75% ([Lean4Physics, 2025](https://arxiv.org/abs/2510.26094)).
- **IndiMathBench** ([Microsoft, 2025](https://arxiv.org/abs/2512.00997)): autoformalization benchmark focusing on statement-level faithfulness and hallucination detection.

### 2.2 Methods, from simplest to strongest

**Flat NL2Lean (baseline).** One-shot prompting an LLM to produce a Lean 4 statement. Works ~25-45% on ProofNet without retrieval ([An Evaluation Benchmark for Autoformalization in Lean4](https://arxiv.org/html/2406.06555v1)). Fails badly on hallucinated identifiers.

**Draft-Sketch-Prove (DSP).** Original method ([Jiang et al., 2022](https://arxiv.org/abs/2210.12283)): (a) LLM drafts an informal proof; (b) a sketch model autoformalizes the draft into a skeleton with explicit subgoals and named hypotheses; (c) a symbolic automated prover fills in the gaps. Improved competition pass from 20.9% to 39.3%. Revived in 2025 ([Reviving DSP, 2025](https://arxiv.org/pdf/2506.11487)) with modern reasoning LLMs as the "draft" model. DSP is the conceptual ancestor of ProofFlow.

**Process-driven autoformalization.** Adds reward on *intermediate* formalization steps, not just final output ([Lu et al., 2024](https://arxiv.org/html/2406.01940v1)). Process reward models make autoformalization trainable with RL over long trajectories.

**NL2Lean (multi-aspect RL).** Current SOTA-class for pure RL training on the NL-to-Lean objective. Defines four reward dimensions — semantic alignment, term-level alignment, global alignment, and compile-check — trains separate preference models, and combines them via PPO ([NL2Lean, EMNLP 2025](https://aclanthology.org/2025.emnlp-main.1586/)). Curriculum learning over difficulty matters.

**Aria (agent + dependency graph).** Two-phase Graph-of-Thought: recursively decomposes a statement into a dependency graph of sub-concepts, then constructs a grounded formalization bottom-up. AriaScorer retrieves Mathlib definitions for term-level grounding. 91.6% compile / 68.5% faithful on ProofNet ([Aria, 2025](https://arxiv.org/abs/2510.04520)).

**Direct Dependency Retrieval (DDR).** Rather than selecting candidate dependencies from a bank, *generate* them and verify existence via Suffix Array Check against Mathlib. Trained on 500k synthetic samples. Beats RAG-selection baselines substantially on both retrieval and downstream autoformalization ([DDR, 2025](https://arxiv.org/abs/2511.11990)).

**ReForm (reflective).** Integrates semantic consistency evaluation *inside* the generation loop via Prospective Bounded Sequence Optimization (PBSO), which applies different rewards at different sequence positions. +22.6 pp over strongest baselines across four benchmarks. Ships ConsistencyCheck, which shows human experts themselves disagree 38.5% of the time on autoformalization correctness ([ReForm, 2025](https://arxiv.org/abs/2510.24592)).

### 2.3 Dominant failure modes on research-level content

Verified across multiple evaluations ([ProofNet](https://arxiv.org/abs/2406.07222), [Aria](https://arxiv.org/pdf/2510.04520), [IndiMathBench](https://arxiv.org/html/2512.00997), [Autoformalization in the Wild](https://arxiv.org/pdf/2502.12065)):

- **Hallucinated Mathlib identifiers**: nonexistent types (e.g. `IrratNum`), predicates (`IsNil`), namespaces. Caught by compilation but expensive.
- **Lean 3 / Lean 4 syntax mixing**: models still emit `:=` where `:=` means something different, or use deprecated tactic names.
- **Wrong type universes**: silently compiles but uses the wrong universe polymorphism, creating downstream unification failures.
- **Implicit vs explicit argument confusion**: `@foo` vs `foo`, mishandling `{...}` vs `(...)` vs `[...]`.
- **Namespace resolution errors**: same concept defined in multiple files (e.g. `Nat.Prime` vs `_root_.Prime`), mis-resolved.
- **Conceptual polymorphism**: `neighborhood` in topology vs metric space. Triggers TypeClass synthesis errors at compile time, but semantically wrong even when it compiles in the "wrong" interpretation.
- **Hidden quantifier scoping**: informal "for all x there exists y" vs "there exists y for all x" swapped — compiles fine, semantically wrong. This is the class humans and back-translation most often miss.
- **Convention drift**: sign conventions, metric signatures, Fourier conventions in physics — no way to recover from context alone.

---

## 3. Proof-level autoformalization: state of the art

### 3.1 The two paradigms

**Step-wise (tactic-level):** ReProver ([LeanDojo, 2023](https://arxiv.org/abs/2306.15626)), COPRA ([Thakur et al., 2023](https://arxiv.org/abs/2310.04353)), InternLM2.5-StepProver ([HuggingFace](https://huggingface.co/internlm/internlm2_5-step-prover)). Model proposes one tactic at a time, search over trees via BFS or LLM-guided expansion.

- Pros: transparent, can recover from errors, works with best-first search over proof states.
- Cons: slow per proof; the search-tree blowup is the bottleneck.
- ReProver on miniF2F: ~51%. COPRA: competitive pass@1. InternLM2.5-StepProver: was SOTA on miniF2F+ProofNet+PutnamBench mid-2024.

**Whole-proof:** Kimina-Prover ([Moonshot, 2025](https://arxiv.org/abs/2504.11354)), DeepSeek-Prover-V2 ([DeepSeek, 2025](https://arxiv.org/abs/2504.21801)), Goedel-Prover-V2 ([Goedel-LM, 2025](https://arxiv.org/abs/2508.03613)), Seed-Prover 1.5 ([ByteDance, 2025](https://arxiv.org/abs/2512.17260)). One-shot whole proof generation, then filter/repair.

- Pros: leverages modern reasoning model capabilities; fast per candidate; no MCTS/value-function baggage.
- Cons: high pass@k budget (8192 for Kimina's headline number); can waste compute on doomed attempts.
- Kimina-Prover-72B: 80.7% miniF2F pass@8192. DeepSeek-Prover-V2-671B: 88.9% miniF2F, 49/658 PutnamBench. Goedel-Prover-V2-32B: 90.4% miniF2F with self-correction. Seed-Prover 1.5: 88% PutnamBench, 80% graduate-level Fate-H, 33% PhD-level Fate-X.

**Hybrid (best current choice):** APOLLO ([Ospanov et al., NeurIPS 2025](https://arxiv.org/abs/2505.05758)) is a repair-and-isolate loop: LLM generates, Lean compiles, agent isolates failing subgoals, dispatches small LLM budgets per subgoal, and recombines. Raises general-purpose o3-mini/o4-mini from 3-7% to 40%+ on miniF2F; raises Goedel-Prover-SFT from prior SOTA to 65.6% while cutting samples from 25,600 to a few hundred.

### 3.2 Structural / dependency-graph proof formalization

**ProofFlow** ([Zhang et al., 2025](https://arxiv.org/abs/2510.15981)) is the clearest architectural win for *proof-level* autoformalization. It:

1. Parses the informal proof into a DAG of logical dependencies.
2. Formalizes each step as an intermediate lemma, with explicit `premises_of_step_i ⊆ prior_lemmas`.
3. Enforces the DAG at generation time (the "DAG" variant; "noDAG" just gives all prior lemmas and does worse).

On its own 184-problem undergrad benchmark, ProofFlow achieves ProofScore 0.545 vs full-proof 0.123 and step-proof 0.072 — a 4-7× structural-fidelity improvement. ProofFlow's "intermediate lemma" output format is exactly what GRD's `research/` artifacts should produce because (a) it matches blueprint semantics, (b) each lemma is independently checkable, and (c) it localizes repair.

### 3.3 Premise retrieval

For step-wise proofs, retrieval-augmented tactic generation is the difference between 50% and "hopeless". ReProver uses LeanDojo's program-analysis pass to identify *accessible* premises (respects Lean's elaboration and import graph), with hard-negative mining over same-file premises. +3-5 pp over no-retrieval baseline.

For whole-proof models, retrieval shows up differently: rather than retrieve premises per tactic, retrieve *definitions and typing lemmas* relevant to the statement, and put them in the context before generation. DDR does this by generating likely dependency names and verifying existence.

### 3.4 Expert iteration and test-time RL

**Expert iteration** (DeepSeek-Prover-V2, InternLM-StepProver): current model generates many proofs, Lean verifies, successful proofs become next-round training data. Practical for base-model development, **not practical** for a per-phase research workflow because each iteration cycle takes hours-to-days.

**Test-time RL (AlphaProof-style)**: for each hard target, generate theorem *variations*, train on the successful ones on the fly, progressively solve the main problem ([AlphaProof, Nature 2025](https://www.nature.com/articles/s41586-025-09833-y)). Solved 3/5 IMO 2024 problems (silver medal, 28 points). Compute cost is enormous — orders of magnitude more than humans — and only justified for single high-value claims.

For GRD, test-time RL is available as a "pro mode" for a small number of flagship claims per milestone, not for routine phase verification.

---

## 4. Practical pipeline: what the field currently agrees on

### 4.1 Extracting precise mathematical content from informal LaTeX

The hard step is **context assembly** — making sure the Lean statement uses the same conventions, definitions, and variable types as the surrounding informal document.

Current best practice (synthesized from [Aria](https://arxiv.org/abs/2510.04520), [Blueprint](https://terrytao.wordpress.com/2023/11/18/formalizing-the-proof-of-pfr-in-lean4-using-blueprint-a-short-tour/), [NL2Lean](https://aclanthology.org/2025.emnlp-main.1586/)):

1. **Pre-parse the document for "local context"**: extract named definitions, conventions, prior formalized claims, and variable declarations into a structured context object.
2. **Decompose the target statement into a concept DAG**: Aria-style, recursively down to atoms ("prime", "integral over a compact set", "continuous") that can be grounded directly in Mathlib/PhysLean.
3. **For each atom, do grounded retrieval**: DDR-style generate-and-verify against the Mathlib4 index, with Lean 4 name resolution semantics.
4. **Generate candidate Lean statements bottom-up**: build each sub-formalization first, then compose.

### 4.2 Generating candidate Lean 4 statements

Three regimes by compute budget:

- **Cheap (~$0.01/claim)**: one shot via Claude Sonnet/Opus or GPT-4-class, with Mathlib index and local blueprint context in the prompt. Compile-check; keep if passes.
- **Medium (~$0.10/claim)**: 8-32 candidates, rank by (a) compiles, (b) back-translation semantic similarity to original, (c) type-signature sanity.
- **Expensive (~$1-10/claim)**: Aria-style agent with DAG decomposition + DDR retrieval + AriaScorer grounding, with reflective refinement (ReForm-style PBSO if using a trained model, or explicit self-critique if using a frontier model).

### 4.3 Validating faithfulness (the hard part)

This is the core open problem. "Faithfulness" is semi-decidable at best — there is no algorithm that decides whether Lean `∀ ε > 0, ∃ δ > 0, ...` correctly captures "f is continuous at x" without either a human or a stronger reference formalization.

Current mitigations, in order of practical value:

1. **Back-translation** ([Evaluating Autoformalization Robustness, 2025](https://arxiv.org/html/2511.12784)): Formal → informal via a second LLM; compare to original. SBERT cosine 62-78% on matched pairs. Coarse, but catches gross drift.
2. **Symbolic equivalence + semantic consistency** ([Liu et al., 2025](https://arxiv.org/html/2410.20936v1)): generate multiple candidates, use Z3/Prover9 to test logical equivalence between them, require cluster consensus. Catches quantifier-scoping bugs.
3. **Type-signature sanity checks**: is the free-variable universe sensible? Are units consistent (in physics)? Do the types match what the informal statement claims?
4. **Test-value substitution**: evaluate the Lean statement on concrete values the human knows the answer for. `#eval` and `decide` tactics check; if the informal claim is "for all n ≥ 1, P(n)", substitute 1, 2, 5 and check `decide`.
5. **Multiple-candidate + expert-judgment ranking metrics**: GTED ([Generalized Tree Edit Distance, 2025](https://arxiv.org/html/2507.07399v1)), ASSESS ([structural+semantic, 2025](https://arxiv.org/abs/2509.22246)), FormalAlign ([2024](https://arxiv.org/abs/2410.10135)). Each correlates moderately with expert judgment. None is a replacement for a human review on research-level claims.

**Consensus: there is no metric that replaces expert review for research-level autoformalization.** ReForm's ConsistencyCheck shows experts disagreeing 38.5% of the time on their own labels. Humans stay in the loop; the job of the pipeline is to minimize how many claims reach them and surface *specific* faithfulness concerns.

### 4.4 Iterating with typechecker feedback

The standard loop:

```
generate → lean compile → error? → repair agent (targeted, not full regen) → retry
```

APOLLO is the strongest published version. Goedel-Prover-V2's "self-correction" mode is similar in spirit. Key engineering detail: the repair prompt must include the Lean error message, the current proof state at the failing point, and the *local* context (not the full file). Repair budgets of 5-10 retries on focused subgoals are far more efficient than 1000+ samples on whole proofs.

### 4.5 PFR Blueprint / how humans actually do this

Tao's PFR project ([blog post](https://terrytao.wordpress.com/2023/11/18/formalizing-the-proof-of-pfr-in-lean4-using-blueprint-a-short-tour/), [follow-up](https://terrytao.wordpress.com/2023/12/05/a-slightly-longer-lean-4-proof-tour/)) established the template. Massot's [Blueprint](https://github.com/PatrickMassot/leanblueprint) tool:

- LaTeX source with macros `\lemma`, `\proof`, `\uses{...}` declaring dependency on other lemmas.
- Automatic dependency-graph HTML visualization with per-node Lean formalization status.
- Bidirectional links between informal LaTeX and Lean files.
- Enables asynchronous contributions from collaborators who don't know Lean, because they work on the informal blueprint while others formalize nodes.

**Human-in-loop is still essential.** Tao's workflow treats Lean as the ground truth for correctness and the blueprint as the coordination artifact. For GRD this maps cleanly: GRD already produces `research/phase-N/` artifacts with claims and dependencies — adding a Blueprint-style LaTeX output and an auto-generated DAG is a natural extension.

### 4.6 Grounded vs ungrounded

Ungrounded = model knows Mathlib from pretraining but has no live index. Grounded = model has a current Mathlib4 database, name resolution tooling, and type-checking feedback.

- Ungrounded degrades fast: Mathlib4 API changes quickly, pretrained knowledge goes stale in 3-6 months.
- Grounded is dramatically more reliable for statement-level autoformalization: hallucinated names drop from 40-60% of compile failures to <10%.
- **Always use grounded.** Lean Copilot ([Song et al., 2024](https://arxiv.org/abs/2404.12534)), LeanDojo tooling, or a bespoke Mathlib index are all acceptable. Lean Copilot's `suggest_tactics`, `search_proof`, and `select_premises` APIs automate 74.2% of proof steps on its benchmark.

---

## 5. The human-AI asymmetry problem

Core tension ([Tao, 2024 talks](https://terrytao.wordpress.com/tag/lean4/)): humans can read and verify an informal proof, but an AI cannot verify that its own formalization is semantically faithful. This makes autoformalization fundamentally *different* from automated proof search — the correctness oracle is missing on the formalization side.

Practical mitigation techniques, ranked by efficacy in the 2025 literature:

1. **Blueprint structure + DAG decomposition** (Tao, ProofFlow, Aria): localizes faithfulness review to individual small lemmas, where humans *can* reliably check. This is the biggest lever.
2. **Back-translation + paraphrase test** ([2025](https://arxiv.org/abs/2511.12784)): model back-translates Lean to English; compared to original via embedding similarity. Weak but useful filter.
3. **Symbolic equivalence clustering** ([2024](https://arxiv.org/abs/2410.20936)): generate N=16 formalizations, cluster by logical equivalence via Z3/tactic-proof, require large consensus cluster; escalate to human if clusters are balanced.
4. **Type-level sanity checks**: universes, implicit arguments, `#check` output inspection.
5. **Test-value substitution**: concrete checks using `decide`/`native_decide`.
6. **Cross-model ensemble**: three frontier models independently autoformalize; only auto-accept unanimous agreement.

Per [ReForm's ConsistencyCheck benchmark](https://arxiv.org/abs/2510.24592), expert-vs-expert agreement on autoformalization faithfulness is 61.5%. No metric published to date correlates above ~0.7 with expert judgment on held-out research-level claims. **Expect to need expert review on a measurable fraction (10-40%) of claims.**

---

## 6. Physics-specific autoformalization

### 6.1 Libraries

- **PhysLean** (formerly HepLean; now at [github.com/HEPLean/PhysLean](https://github.com/HEPLean/PhysLean), merging with leanprover-community as [PhysLib](https://github.com/leanprover-community/physlib)) aims to be "Mathlib for physics". Coverage includes: Maxwell's equations, quantum harmonic oscillator, two-state canonical ensemble, tight-binding model, twin paradox, two-Higgs doublet model, Wick's theorem ([Tooby-Smith, Comput. Phys. Commun. 2025](https://www.sciencedirect.com/science/article/abs/pii/S0010465524003801)). Index notation for tensors is formalized ([2411.07667](https://arxiv.org/html/2411.07667v1)).
- **Lean4PHYS / PhysLib repository** ([Lean4Physics, 2025](https://arxiv.org/abs/2510.26094)): unit systems, dimension transformations, fundamental constants, growing theorem collection. Shipped with LeanPhysBench (200 hand-crafted theorems).
- **SciLean** ([github.com/lecopivo/SciLean](https://github.com/lecopivo/SciLean)): scientific computing — differential equations, optimization, automatic differentiation, n-dim arrays. OpenBLAS-backed. Proof-of-concept, not production.
- **Dimensional analysis** ([Bhatt, 2025](https://arxiv.org/abs/2509.13142)): dimensions as mappings from base dims to exponents, proven to form an Abelian group; SI units and fundamental constants; Buckingham Pi theorem formalized. Applied to Lennard-Jones. This is the preferred current encoding over ad-hoc type-class parameters.
- **Generalized Quantum Stein's Lemma** ([2510.08672](https://arxiv.org/html/2510.08672v1)): "most technically demanding theorem in physics with a computer-verified proof to date". Demonstrates research-level physics formalization is feasible (though 18+ months of effort).

### 6.2 Encoding choices: dimensions, units, conventions

Three styles seen in the literature:

1. **Units as types** (e.g., `Meter`, `Kilogram × Meter / Second^2`): maximally safe, but Lean's elaboration gets slow and error messages become unreadable.
2. **Type class parameters** (`[Unit u]`): flexible, but can fail dimension-checks at runtime rather than type-check time.
3. **Dimensional tags as abelian-group elements**: [Bhatt's approach](https://arxiv.org/abs/2509.13142) — dimensions form `Dim := BaseDim → ℤ` with componentwise add. Dimensional homogeneity proven as a lemma, not baked into types. **This is now the preferred approach** and is what PhysLib adopts.

For GRD physics workflows, encode **convention parameters** (sign of metric signature, Fourier convention, gauge choice) as typeclasses or section variables so they can be swapped without rewriting downstream proofs. GRD's existing `grd-conventions` MCP tools should feed directly into this.

### 6.3 Success stories beyond textbook results

- **Quantum Stein's Lemma** ([2025](https://arxiv.org/html/2510.08672v1)): research-level, formalized.
- **Wick's theorem**: formalized in PhysLean.
- **Pati-Salam model** ([PhysLean file](https://github.com/HEPLean/PhysLean/blob/master/PhysLean/Particles/BeyondTheStandardModel/PatiSalam/Basic.lean)): BSM particle physics, formalized.
- **Chemical physics** ([Tooby-Smith et al., 2022 onwards](https://arxiv.org/html/2210.12150v5)): harmonic oscillator, molecular Hamiltonians.
- **Emergent gravity / information geometry** (preprint, [2024](https://www.academia.edu/146192044/Gravity_from_Information_Geometry_A_Lean_4_Formalization_of_Emergent_Spacetime_From_Coherence_Fields_to_Einsteins_Equations)): speculative but demonstrates research-level physics formalization is feasible with months of effort, not "never".

Bottom line: textbook physics is increasingly available. Research-level physics formalization is feasible but labor-intensive. LLMs alone are weak on LeanPhysBench (16-35%) because they don't know PhysLean/PhysLib well, and because physics conventions leak into every statement.

---

## 7. Failure-mode catalog

Ordered by frequency in the wild ([Autoformalization in the Wild, 2025](https://arxiv.org/pdf/2502.12065) + [IndiMathBench](https://arxiv.org/html/2512.00997)):

| Error class | Auto-detectable? | Mitigation |
|---|---|---|
| Hallucinated identifier (nonexistent Mathlib/PhysLean name) | Yes (compile fails) | DDR-style retrieval; grounded index |
| Lean 3 syntax bleed | Yes (compile fails) | Fine-tune on Lean 4 only; or explicit instruction |
| Wrong universe level | Partially (elaborate fails later) | Multiple candidates + pick simplest |
| Implicit/explicit arg swap | Yes (compile fails or wrong unif) | Type-signature comparison |
| Swapped quantifier order | No (compiles + semantically wrong) | Back-translation + symbolic equiv |
| Convention drift (sign, Fourier, metric) | No | Encode conventions explicitly; grd-conventions MCP |
| Off-by-one in indexing | Partially (test-value subst catches some) | Concrete `#eval` / `decide` |
| Domain-of-validity missing (e.g. n ≥ 1 unstated) | No | Back-translation surfaces the missing hypothesis |
| Conceptual polymorphism (wrong abstraction level) | Sometimes (typeclass synth failure) | Aria-style DAG decomp, definition retrieval |
| Wrong namespace (`Prime` vs `Nat.Prime`) | Yes (compile fails or wrong import) | Name resolution before generation |
| Missing typeclass instance | Yes (compile fails) | Repair agent |
| Hidden assumption in informal statement | No | Human review |

The bolded observation: roughly half of high-impact errors are not auto-detectable. A pipeline that doesn't surface these to humans will silently ship wrong formalizations.

---

## 8. Recommended pipeline for GRD

### 8.1 Pipeline architecture

```
┌───────────────────────────────────────────────────────────────┐
│  Phase artifacts (informal LaTeX + conventions + deps)        │
│  from grd-state, grd-conventions, grd-patterns                │
└──────────────────────────┬────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────┐
│ STAGE 1 — Blueprint extraction             │
│ Parse claims, conventions, dependency DAG  │
│ Output: blueprint.tex + deps.json          │
└──────────────────────────┬─────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────┐
│ STAGE 2 — Concept decomposition (per claim)│
│ Aria-style recursive DAG to atoms          │
│ DDR retrieval against Mathlib4 + PhysLean  │
│ Output: grounded concept graph             │
└──────────────────────────┬─────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────┐
│ STAGE 3 — Candidate generation (N=8-16)    │
│ Claude / frontier model, grounded context  │
│ Retry with Lean compile feedback           │
│ Output: N candidate Lean statements        │
└──────────────────────────┬─────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────┐
│ STAGE 4 — Faithfulness gate                │
│ 4a. Compile all candidates (drop fails)    │
│ 4b. Back-translate each to English         │
│ 4c. Symbolic equivalence clustering        │
│ 4d. Test-value substitution                │
│ 4e. Rank by GTED / ASSESS                  │
│ Output: ranked candidates + confidence     │
└──────────────────────────┬─────────────────┘
                           │
              ┌────────────┴──────────┐
              ▼                       ▼
   confidence ≥ threshold      confidence < threshold
              │                       │
              ▼                       ▼
     auto-accept                ESCALATE to human
                                (bd new -l human)
```

### 8.2 Minimum viable pipeline (MVP)

For an initial GRD release, target ~40-60% of claims being auto-formalized correctly (comparable to published SOTA on undergraduate math), with the rest flagged for human review:

- **Stage 1**: Extend GRD's phase artifact format to emit a Blueprint LaTeX file per phase. Add `\lemma{...}\uses{...}` macros, render a DAG. Use existing [leanblueprint](https://github.com/PatrickMassot/leanblueprint) tooling.
- **Stage 2** (skip concept decomposition initially): Just put the full phase context + a Mathlib4 name index in the prompt. Grep the local Mathlib4 snapshot for each identifier the model uses; if not found, reject.
- **Stage 3**: Claude Sonnet 4.5 with (a) phase LaTeX, (b) conventions from `grd-conventions`, (c) Mathlib4 name index, (d) PhysLean index if physics. N=4 candidates.
- **Stage 4**: Compile all; back-translate survivor to English with a second Claude call; simple SBERT similarity with original. If <0.7 → escalate; if ≥0.85 → auto-accept; else symbolic-equiv cluster.
- **Proof search** on statements: use APOLLO-style repair loop around a frontier model, budget 10-20 Lean compiles per claim.

Cost per claim at current pricing: ~$0.10-0.50 for statement, ~$0.50-5 for proof, so ~$10-100 for a 50-claim phase. Acceptable.

### 8.3 Pro pipeline

For flagship milestones where faithfulness is critical:

- **Stage 2**: Full Aria-style DAG decomposition with AriaScorer grounding. DDR retrieval with Suffix Array Check.
- **Stage 3**: Ensemble of 3 models (Claude Opus, GPT-5-class, DeepSeek-Prover-V2), N=16 each, cross-model consensus required.
- **Stage 4**: Full symbolic-equivalence clustering + back-translation + test-value + GTED + ASSESS; require at least 3 of 5 signals to agree on the same cluster.
- **Proof search**: Kimina-Prover-72B or Goedel-Prover-V2-32B as the core prover, with APOLLO repair, budget 100-1000 compiles per claim. Test-time RL (AlphaProof-style) reserved for a handful of "bet the project" claims.
- **Human review gate**: every claim that passes automated gates still gets a 5-minute human spot-check on the back-translation + Lean statement side-by-side.

Cost per claim: ~$5-50 for statement, ~$10-100 for proof, plus test-time-RL can run into the thousands per claim. Reserve for critical phases.

### 8.4 Concrete GRD integration points

GRD already has the right scaffolding. The following MCP tools become the interface for formalization:

- `grd-state`: track formalization status per claim (`unformalized / candidate / verified-faithful / verified-proven`).
- `grd-conventions`: feed convention lock state into the formalization context — this is the single biggest lever for avoiding convention-drift errors.
- `grd-verification`: extend with a `lean_check` action that compiles and reports.
- `grd-patterns`: accumulate project-specific autoformalization patterns (e.g., "this project uses `(-,+,+,+)` metric signature — always include it in statements about spacetime intervals").
- `grd-errors`: hook in the failure-mode catalog from §7; classify each autoformalization failure so the error-pattern database helps future claims.
- New: `grd-lean` MCP that wraps Lean Copilot, LeanDojo, and/or a Lean server for compile + proof-state queries.
- New: `grd-blueprint` MCP that emits and updates Blueprint LaTeX from phase artifacts.

For the `bd` workflow: every claim that enters autoformalization is a bead. If confidence < threshold, the bead gets `-l human` with the specific ambiguity surfaced (e.g., "quantifier-order uncertain between candidates A and B"). If formalization succeeds but proof search fails after the pro-pipeline budget, a `needs-proof` bead stays open.

### 8.5 Priorities and pitfalls

**Do first:**
- Blueprint LaTeX output from phase artifacts (low effort, high leverage).
- Grounded Mathlib4 / PhysLean name index with type-signature retrieval.
- Compile-in-loop repair agent. Even 5-step APOLLO-style repair is huge.

**Do second:**
- Back-translation faithfulness gate. Cheap and catches obvious drift.
- Cross-model ensemble for high-stakes claims.
- DAG decomposition for multi-lemma claims.

**Don't do (yet):**
- Training your own autoformalization model. Frontier models with grounded retrieval beat small fine-tuned models on research content.
- Test-time RL at scale. Wait until AlphaProof-style techniques are a commodity or your single-claim value justifies thousands of dollars.
- Attempting research-level physics formalization without a working PhysLean/PhysLib snapshot. The library coverage gap is real.

**Known gotchas:**
- Mathlib4 changes weekly. Pin a snapshot per project and upgrade deliberately.
- PhysLean is less stable than Mathlib4. Expect API breakage.
- Lean 4 elaboration is slow. A 500-claim phase with full proof search can run overnight. Parallelize aggressively.
- Frontier models still emit Lean 3 syntax occasionally. Explicit Lean-4-only instructions in the system prompt help materially.
- Convention drift is silent. `grd-conventions` must surface active convention at every autoformalization call.

---

## 9. Key references

Core methods:
- [Draft, Sketch, and Prove (Jiang et al., 2022)](https://arxiv.org/abs/2210.12283) — DSP method.
- [Reviving DSP (2025)](https://arxiv.org/pdf/2506.11487) — modern reasoning-model revival.
- [LeanDojo (Yang et al., 2023)](https://arxiv.org/abs/2306.15626) — ReProver, premise retrieval.
- [COPRA (Thakur et al., 2023)](https://arxiv.org/abs/2310.04353) — in-context step-wise agent.
- [Lean Copilot (Song et al., 2024)](https://arxiv.org/abs/2404.12534) — LLMs natively in Lean.
- [Process-Driven Autoformalization (Lu et al., 2024)](https://arxiv.org/html/2406.01940v1).
- [Kimina-Prover (Moonshot, 2025)](https://arxiv.org/abs/2504.11354).
- [DeepSeek-Prover-V2 (2025)](https://arxiv.org/abs/2504.21801).
- [APOLLO (Ospanov et al., NeurIPS 2025)](https://arxiv.org/abs/2505.05758).
- [Goedel-Prover-V2 (2025)](https://arxiv.org/abs/2508.03613).
- [ProofFlow (2025)](https://arxiv.org/abs/2510.15981) — dependency-DAG proof formalization.
- [Aria (2025)](https://arxiv.org/abs/2510.04520) — retrieval agent.
- [ReForm (2025)](https://arxiv.org/abs/2510.24592) — reflective autoformalization + ConsistencyCheck.
- [Direct Dependency Retrieval (2025)](https://arxiv.org/abs/2511.11990).
- [NL2Lean (EMNLP 2025)](https://aclanthology.org/2025.emnlp-main.1586/) — multi-aspect RL.
- [Seed-Prover 1.5 (2025)](https://arxiv.org/abs/2512.17260).
- [AlphaProof (Nature 2025)](https://www.nature.com/articles/s41586-025-09833-y).

Benchmarks:
- [ProofNet evaluation (2024)](https://arxiv.org/abs/2406.07222).
- [FormalMATH (2025)](https://arxiv.org/pdf/2505.02735).
- [Autoformalization in the Wild (2025)](https://arxiv.org/pdf/2502.12065).
- [IndiMathBench (2025)](https://arxiv.org/html/2512.00997).
- [LeanPhysBench / Lean4Physics (2025)](https://arxiv.org/abs/2510.26094).

Evaluation metrics:
- [FormalAlign (2024)](https://arxiv.org/abs/2410.10135).
- [Symbolic Equivalence + Semantic Consistency (2024)](https://arxiv.org/html/2410.20936v1).
- [GTED (2025)](https://arxiv.org/html/2507.07399v1).
- [ASSESS (2025)](https://arxiv.org/abs/2509.22246).
- [Paraphrase-robustness evaluation (2025)](https://arxiv.org/html/2511.12784).

Physics libraries:
- [PhysLean (HEPLean/PhysLean GitHub)](https://github.com/HEPLean/PhysLean).
- [PhysLib (leanprover-community)](https://github.com/leanprover-community/physlib).
- [SciLean (lecopivo/SciLean)](https://github.com/lecopivo/SciLean).
- [HepLean paper (Tooby-Smith, CPC 2025)](https://www.sciencedirect.com/science/article/abs/pii/S0010465524003801).
- [Physics index notation in Lean 4](https://arxiv.org/html/2411.07667v1).
- [Dimensional analysis in Lean (Bhatt, 2025)](https://arxiv.org/abs/2509.13142).
- [Quantum Stein's Lemma formalization (2025)](https://arxiv.org/html/2510.08672v1).

Workflow / human-in-loop:
- [PFR Blueprint tour (Tao, 2023)](https://terrytao.wordpress.com/2023/11/18/formalizing-the-proof-of-pfr-in-lean4-using-blueprint-a-short-tour/).
- [Lean 4 proof tour (Tao, 2023)](https://terrytao.wordpress.com/2023/12/05/a-slightly-longer-lean-4-proof-tour/).
- [leanblueprint tool (Massot)](https://github.com/PatrickMassot/leanblueprint).

---

*End of report.*
