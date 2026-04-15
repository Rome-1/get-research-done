# Mathematician Workflows with Lean in GRD

**Parent beads:** ge-7ah (UX study), ge-plk (formal proof integration)
**Companion documents:** [`PITCH.md`](PITCH.md), [`AUTOFORMALIZATION.md`](AUTOFORMALIZATION.md), [`UX-STUDY.md`](UX-STUDY.md)
**Author:** bob (getresearch/crew) · **Date:** 2026-04-15
**Status:** Living design memo. Updated as flows ship.

---

## 0. Purpose

This document answers three questions left open after the UX study:

1. **Who is the mathematician using GRD's Lean surface, and what are they actually trying to do?** The UX study diagnosed *what is broken* in the shipped surface; this document specifies *what it needs to feel like when it works*.
2. **How does Lean fit into the larger GRD picture?** Formal proof is one of several verification modalities (dimensional analysis, limiting cases, numerical spot-checks, symmetry). This document defines the seams.
3. **What does "utterly effortless cold onboarding" mean, operationally?** We convert that phrase into a Day-0 script, a set of invariants, and a checklist of beads that must land for the claim to be honest.

The north-star goal is unambiguous and is taken directly from Rome's directive:

> A mathematician (or a physicist, or the maintainer of this repo opening it cold after three weeks away) must be able to go from *"I have an informal claim I'd like Lean to check"* to *"Lean has accepted a formal statement of it (or told me exactly what is preventing that, in one screen)"* without reading source code, without hunting for documentation, and without seeing a Python traceback.

Everything below serves that single target.

---

## 1. The Invariant: **Mathematicians write mathematics. Agents handle the schema.**

The single most important design principle that falls out of the UX study is this: the shipped surface is fine for agents that know the `LeanCheckResult` / `VerifyClaimResult` / `LeanEnvStatus` dataclasses and the exact flag matrix of `grd lean`. It is not fine for a human. Rather than push the human up the learning curve, GRD's job is to keep them at the level of *mathematical* input — an informal statement, a named concept, a reference to a prior phase — and let the grd-prover agent translate that into the structured schema that the CLI, daemon, and faithfulness gate consume.

The invariant is:

**A mathematician should never need to know:**

- The names or shape of `LeanCheckResult`, `LeanEnvStatus`, or `VerifyClaimResult` fields.
- The difference between `grd lean check` (typecheck), `grd lean prove` (search), and `grd lean verify-claim` (autoformalize + check + faithfulness).
- The difference between `--raw` and `--json`, between stdout JSON and bead escalation JSON, or between the daemon socket path and the CLI exit code.
- Any flag to `grd lean` other than the subcommand name and a `--help`.

**A mathematician should always be able to:**

- Open a GRD project and, within 60 seconds of `grd lean bootstrap` completing, run one command that checks their first claim — with the agent (`grd-prover` or a slash command) choosing the right subcommand and flags.
- Read any error message and know three things: (a) what Lean saw, (b) why it rejected it, (c) the concrete next action, with at least one clickable reference.
- Write a claim in mathematical English in a phase artifact (`RESULTS.md`, `STATE.md`, `paper.md`) and have GRD propose a Lean formalization with the faithfulness gate's rationale shown as a human-readable diff, not a similarity scalar.
- Close the loop — accept, reject, or amend the proposal — in one interactive step, without editing a JSON blob.

This invariant is not aspirational: it is the acceptance criterion for every P0 and P1 bead filed in the UX study. When a bead fails to advance the invariant, it is mis-scoped.

---

## 2. Personas

Three personas cover the onboarding surface. They are constructed so that any UX decision that works for all three is safe, and any decision that fails one of them is a regression.

### 2.1 Mina — working mathematician, week 1 with GRD

- PhD in algebra, fluent in LaTeX, has read the first chapter of *Mathematics in Lean* but never typed a tactic in anger.
- Comes to GRD with a preprint in progress. Wants Lean to confirm a specific combinatorial identity she suspects she used incorrectly in a lemma.
- Terminal comfort: high. Python comfort: medium. Lean comfort: beginner.
- **What she needs:** a path from "here is the lemma" to a Lean-accepted statement in under 30 minutes, without leaving the terminal, without installing anything she does not understand, and without learning tactic syntax. If Lean cannot prove it yet, she accepts that — she wants the statement on the board.
- **What she does not need:** Mathlib onboarding, tactic cheat sheets, Blueprint internals. If GRD hands her those up front, she closes the tab.

### 2.2 Priya — computational physicist, week 1 with GRD

- Postdoc in condensed matter. Uses Mathematica and Julia daily. Has heard of Lean but considers it "a math thing."
- Has a conservation-law claim in a GRD physics project (SI units, named-tensor conventions locked in an earlier phase). Wants to add `Theorem energy_conserved : ...` as a verified line next to her numerical check.
- Terminal comfort: very high. Python comfort: medium. Lean comfort: zero.
- **What she needs:** the convention-lock to "just appear" in her Lean preamble. She is not willing to redeclare units or rebind tensor indices. She wants the demo loop (UX-STUDY §Section 4) to *actually work end-to-end* on her project, because she will judge the whole tool on whether that one loop lands.
- **What she does not need:** to know that the preamble comes from `conventions.json`, or that the faithfulness gate scores similarity. If the claim is rejected, she needs the *physics* reason (wrong domain? missing hypothesis about thermal equilibrium?), not a similarity number.

### 2.3 Rome — GRD maintainer, week 3 after a compaction

- Has written every piece of this stack (CLI, daemon, pipeline, gate, coverage metrics, prover agent) across four phases.
- Comes back cold three weeks later, post-compaction, to demo the end-to-end story to a collaborator.
- Terminal comfort: maximum. Python comfort: maximum. Lean comfort: intermediate-by-implementation.
- **What he needs:** a single `/grd:lean-demo` or `grd lean demo` path that runs the whole loop (bootstrap → stub-claim → verify → display result) on a canned physics example, producing a terminal transcript he can screen-share in under 5 minutes with zero mid-demo debugging.
- **What he does not need:** to remember which flags go where, whether the daemon auto-spawns, or whether the physicist preamble is shipped. If it is not shipped, the demo path must clearly say "not shipped yet — this is the mocked version" rather than silently producing a plausible-looking lie.

**Invariant check:** every P0 and P1 bead should be gated by "does this improve Day-0 for all three?" A change that helps Mina but makes Priya's conventions flow worse is a regression.

---

## 3. How Lean Fits Into the GRD Picture

GRD has four verification tiers today. Formal proof slots in as the fifth, and the integration is not flat — each tier promotes to the next under specific triggers. The picture:

```
Tier 0 — Assertion          (human writes it in RESULTS.md)
  ↓ promoted by: any claim in a phase artifact
Tier 1 — Dimensional check  (heuristic: units & rank balance)
  ↓ promoted by: dimensional pass + named-tensor claim
Tier 2 — Limiting cases     (heuristic: known-limit re-derivation)
  ↓ promoted by: limit pass + convention lock
Tier 3 — Numerical check    (heuristic: spot evaluation vs. tolerance)
  ↓ promoted by: numerical pass + symbolic form
Tier 4 — Symmetry / contract(heuristic: invariance under group action)
  ↓ promoted by: symmetry pass + "warrants formal" flag
Tier 5 — Formal proof       (Lean 4: typecheck ≥ proof-search ≥ verify-claim)
```

Promotion rules are the seams. A claim does not need to pass every tier, but tiers below the target must either pass or be explicitly waived. The P1 bead **ge-8g5** (Blueprint MVP) is what makes this graph visible — the Blueprint dashboard surfaces one row per claim with a column per tier, and `\leanok` annotations come for free when Tier 5 lands.

Three implications follow.

1. **Lean is not the primary verification path.** Most claims should never reach Tier 5; heuristic checks are cheaper and sufficient. The *point* of the escalation pattern is that the expensive tier is spent only where warranted — exactly the GRD "contract check" philosophy.
2. **Formal proof inherits conventions from earlier phases.** If Phase 2 establishes "velocity is in SI m/s and is a section of the tangent bundle," a Lean verification in Phase 7 consumes that lock via a generated preamble (**ge-j8k**, the convention bridge). The mathematician never re-declares. This is the single biggest structural differentiator between GRD-Lean and freestanding Lean; it is also the biggest current implementation gap (chrome audit dimension 10).
3. **The phase task graph and the Blueprint DAG are the same object.** GRD already computes phase dependencies via STATE.md and bead graphs. The Blueprint DAG is a rendering of that graph annotated with proof status. Nothing new needs to be modeled — only rendered. (**ge-8g5**.)

This framing is what the UX study called "disproportionate leverage point 3" (UX-STUDY §4.3). It is also the thing Tao, Buzzard, and Massot independently identified as the most-praised UX surface they would want to see.

---

## 4. The Three Flows

Everything the mathematician does breaks into three loops. Naming them explicitly lets us assign beads to loops and check coverage.

### Flow A — *State a claim* (autoformalization path)

**Intent:** "I have this in LaTeX / prose; I want a Lean statement on the board."
**Primary command (target):** `grd lean stub-claim "∀ n ∈ ℕ, n² ≥ n"` or a slash command `/grd:formalize-claim`.
**Pipeline:** claim → retrieval (Loogle + LeanExplore) → candidate skeleton → faithfulness gate → one of {accept, escalate, reject-with-reason}.
**Success:** Mina pastes a lemma from her preprint, gets back a Lean statement that typechecks *at the signature level* and a bulleted list of the 1–3 Mathlib lemmas that matched. Total time: < 90 s.

**Blocking beads:**
- **ge-ln7** (`grd lean stub-claim`, currently unshipped) — the primary entry point.
- **ge-cla** (structured faithfulness diff, replaces similarity scalar) — without this, rejection rationale is "0.71" and nobody can act on it.
- **ge-13w** (error-explanation layer) — converts typecheck failures on the skeleton into one-line hints.
- **ge-1hr** (bd-missing escalation visibility) — without this, the escalate path silently fails when `bd` is off PATH.

### Flow B — *Prove a claim* (interactive proof path)

**Intent:** "Lean has the statement; now I want it proved, or to know what's blocking a proof."
**Primary command (target):** `grd lean prove <file>:<theorem>` + future `grd lean try-prove` (hammer) + optional `/grd:prove`.
**Pipeline:** open statement → ladder of built-in tactics → AI-assisted proof-search (future: **ge-k8s** sledgehammer, P2) → kernel-verified snippet or structured failure.
**Success:** Priya's energy-conservation theorem is discharged by `ring` composed with a PhysLean lemma after `apply?` suggested the lemma; the exact tactic is returned for her to paste into her file. Total time: < 3 min per easy case; structured failure with 2–3 candidate next tactics on hard cases.

**Blocking beads:**
- **ge-sk4** (tactic-ladder single source of truth) — the agent doc and shipped ladder currently disagree (rust PR2); `polyrith` is promised but absent.
- **ge-13w** (error-explanation layer) — same as Flow A; Lean's "failed to synthesize instance" is opaque to a beginner.
- **ge-2zu** (goal-state echo in JSON) — lets the user see "what Lean is looking at" without opening VS Code; Macbeth's "free your working memory" primitive.
- **ge-coq** (streaming progress events) — `prove` is currently silent for 10–60 s; without streaming the user assumes a hang.

### Flow C — *Integrate a claim into a phase* (verify-claim path, GRD-native)

**Intent:** "This claim belongs to Phase N of project X. I want the formal verification linked back, the Blueprint node marked `\leanok`, and any faithfulness escalation filed as a bead."
**Primary command (target):** `grd lean verify-claim --phase <N> --artifact RESULTS.md` or `/grd:verify-claim`.
**Pipeline:** extract claim from artifact → convention preamble (from phase lock) → autoformalize → typecheck → faithfulness gate → {bead-escalate | write-back to RESULTS.md with status} → update Blueprint node.
**Success:** Priya runs `/grd:verify-claim` after finishing Phase 4; the tool produces a diff on RESULTS.md that adds `[Lean ✓ verified 2026-04-15 at a1b2c3d]` next to her conservation claim, a file under `phases/4/lean/energy.lean` with the proof, and a Blueprint entry. If rejected, the reason is structured (missing hypothesis, changed domain, convention mismatch), not a scalar.

**Blocking beads:**
- **ge-j8k** (convention bridge preamble generator, P2) — the single biggest agent-claim-vs-code mismatch; without it, Priya's conventions don't flow.
- **ge-cla** (structured faithfulness diff) — without it, the escalation bead is illegible.
- **ge-nub** (doc-truth alignment STATUS.md) — without it, Mina can't distinguish which sub-flow is shipped.
- **ge-8g5** (Blueprint MVP) — without it, there is no "Blueprint node" to mark `\leanok`.

### 4.1 Flow coverage map

| Flow | Fully shipped | Shipped but gated by P0 | Not yet shipped |
|---|---|---|---|
| A. State a claim | — | `verify-claim` pipeline (ge-48t) for the check half | Retrieval stub entry point (ge-ln7), structured diff (ge-cla) |
| B. Prove a claim | `prove` ladder MVP (ge-8cn) | Error-explanation, goal-echo, tactic SSOT | Hammer / try-prove (ge-k8s, P2) |
| C. Integrate into phase | Verification-coverage metrics (ge-wbs) | `verify-claim` CLI (ge-48t) + bead escalation | Convention preamble, Blueprint MVP |

No flow is fully shipped today. All three become shippable after the P0 wave + two specific P1/P2 items (ge-ln7 for Flow A, ge-8g5 for Flow C). This is the minimum bar for the north-star goal in §0.

---

## 5. Day-0 Onboarding — The "Utterly Effortless" Path

This is the script. When GRD's Lean integration is "shipped" in the sense Rome demanded, a cold user can execute exactly this and hit the green path.

```
# (assumes grd is installed and PATH has bd)

$ cd my-project
$ grd init --domain math               # or --domain physics, for Priya
$ /grd:lean-bootstrap                  # installs elan, toolchain, Mathlib cache
   ▸ [1/4] elan detected
   ▸ [2/4] toolchain ready: leanprover/lean4:v4.12.0
   ▸ [3/4] mathlib4 cache: hit (1.9 GB, 12 s)
   ▸ [4/4] daemon running on .grd/lean/repl.sock
   ✓ Ready. Try: /grd:formalize-claim "your claim"

$ /grd:formalize-claim "every nonempty compact subset of ℝ has a maximum"
   ▸ Retrieval: IsCompact.exists_isMaxOn_of_isClosed — 3 hits in Mathlib
   ▸ Skeleton:
       theorem claim_01 {S : Set ℝ} (hne : S.Nonempty) (hc : IsCompact S) :
         ∃ x ∈ S, ∀ y ∈ S, y ≤ x := by sorry
   ▸ Typecheck (signature): ✓
   ▸ Faithfulness: ACCEPT (matched quantifiers, matched domain, matched conclusion)
   ✓ Wrote phases/1/lean/claim_01.lean. Prove it with /grd:prove claim_01.

$ /grd:prove claim_01
   ▸ Trying rfl … no
   ▸ Trying exact? … match: IsCompact.exists_isMaxOn_of_isClosed
   ▸ Closing with: exact hc.exists_isMaxOn_of_isClosed hne
   ✓ Proved in 1.2 s. Blueprint node: ✓ \leanok.
```

Every step above has three properties:

1. **Single command per step.** No flags. Every flag is chosen by grd-prover from the phase context.
2. **Named, streaming progress.** Every multi-second operation emits named events ("elan detected", "Retrieval: …"), so silence is a red flag, not the default.
3. **Actionable failure.** Every possible failure at every step maps to a hint with (a) what happened, (b) why, (c) next action, (d) clickable reference.

The beads that must land for this script to be honest and not mocked are: the P0 wave (8 beads), plus **ge-ln7**, **ge-cla**, **ge-coq**, **ge-2zu**, and **ge-8g5**. That is the Day-0 ship list.

Anything less, and the script lies.

---

## 6. Day-N Workflow — Inside a GRD Project

Once onboarded, the mathematician's day looks like this. The GRD-specific elements (phase graph, conventions, coverage) distinguish it from freestanding Lean work.

1. **Open the project.** `grd progress` shows the phase graph with proof-coverage annotations per phase: `Phase 4: 7 claims · 5 Lean-verified · 2 heuristic-only`.
2. **Pick a claim to lift.** They run `/grd:suggest-next` or filter `bd ready` for `label:needs-formalization`. GRD ranks candidates by "warrants-formal" heuristics (appears in theorem environment, cross-cited by ≥2 phases, claims ∀ or equality, used in abstract).
3. **Lift it.** `/grd:verify-claim --phase 4 --claim "claim-name"` runs the whole pipeline. The convention preamble for Phase 4 is assembled automatically from the convention lock.
4. **Review the result.** Either (a) green: coverage metric ticks up, Blueprint node marked, RESULTS.md annotated, or (b) structured-rejection: bead filed with `faithfulness_diff: {missing_hypotheses: [...], changed_domain: ..., changed_convention_terms: [...]}`. They either accept the diff and re-run, or mark "heuristic-sufficient" and move on.
5. **Close the loop.** When the phase ships, `grd phase complete` refuses to close if any `needs-formalization` claim is still at Tier 0. This is the forcing function — Lean verification is optional per-claim but accountable per-phase.

Day-N invariants to preserve:

- The user never sees a traceback (ge-4yl).
- The user never sees a silent 60-second wait (ge-coq).
- The user never types a tactic in anger in the terminal — tactics appear only inside `.lean` files they open in their editor, or as suggestions the agent applies.

---

## 7. The Demo — "Physics Phase → Lean-checked Lemma"

This is the second "For:" goal from Rome's message. The demo is what convinces collaborators, reviewers, and funders that GRD's formal layer is real.

**Canonical demo — "1D harmonic oscillator energy conservation, formally verified."**

```
$ grd new-project demo-sho --domain physics --template simple-mechanics
$ cd demo-sho
$ /grd:lean-bootstrap --for physicist                  # ge-5o8 P1-8

# Phase 1 is pre-populated by the template:
#   - SI convention lock (ge-tau preamble will read this)
#   - H(q,p) = ½ p² / m + ½ m ω² q²
#   - dH/dt = 0 as a derived claim with heuristic dim-check passing

$ /grd:progress
   Phase 1: derived-energy-conservation
     [✓] Tier 1: dimensional check
     [✓] Tier 2: limit ω→0 (free particle) recovered
     [✓] Tier 4: symmetry under time translation
     [ ] Tier 5: formal proof              ← available

$ /grd:verify-claim --phase 1 --claim derived-energy-conservation
   ▸ Convention preamble: imported SI units + Mechanics.Hamiltonian
   ▸ Skeleton:
       theorem energy_conserved (m ω : ℝ) (hm : 0 < m) (hω : 0 < ω) :
         ∀ t, H q(t) p(t) = H q(0) p(0) := by sorry
   ▸ Faithfulness: ACCEPT (domain ℝ matches; hypotheses match; conclusion quantifier matches)
   ▸ Proof search: closed by `symm_energy_conservation` composed with `time_translation_symmetry`
   ✓ Verified in 4.1 s.

$ /grd:progress
   Phase 1: derived-energy-conservation
     [✓] Tier 1 … Tier 5 (Lean, 4.1 s)
   Blueprint: https://rome-1.github.io/demo-sho/blueprint/  ← \leanok on energy_conserved
```

For this demo to run end-to-end, the following must be shipped, in order:

1. **P0 wave** (8 beads) — makes every intermediate message and exit code honest.
2. **ge-5o8 (P1-8, physicist-persona bootstrap)** — `--for physicist` flow with PhysLean + SI unit scaffolding.
3. **ge-j8k / ge-tau (P2, convention bridge preamble)** — the "imported SI units + Mechanics.Hamiltonian" line is not a mock.
4. **ge-ln7 (P1, stub-claim / skeleton generator)** — the skeleton is real.
5. **ge-cla (P1-6, structured faithfulness diff)** — the ACCEPT/REJECT reasons are structured.
6. **ge-8g5 (P1-2, Blueprint MVP)** — the final Blueprint URL is real.
7. **A template `simple-mechanics`** — currently unfiled; this doc files it below.

This is a ~6-week burn-down at the current pace (P0 in one week, three P1 items over three weeks, two items that overlap, template in one week). It is ship-able, not aspirational.

---

## 8. Success Metrics — How We Know It's Shipped

The test is not "did the beads close." The test is whether three specific transcripts run green on a fresh machine, with no human editing, no manual retries, and no unexplained Python tracebacks.

1. **Mina transcript (Flow A):** §5 script, substituting `--domain math`. Must complete in < 5 min wall-clock on a fresh Linux VM with only `curl` and `git` preinstalled. Exits cleanly; produces a `.lean` file that typechecks.
2. **Priya transcript (Flow C + demo):** §7 demo. Must complete in < 10 min on a fresh VM. Produces a Blueprint page with exactly one green `\leanok` node.
3. **Rome transcript (cold-re-onboarding):** three weeks after no contact, Rome runs only `/grd:lean-demo` and gets a screen-shareable transcript in under 5 min with zero debugging.

Secondary metrics (UX study linked these explicitly to the invariant; they are not subjective):

- **Zero Python tracebacks** across all three transcripts (measured: `grd lean … 2>&1 | grep -E 'Traceback|File ".*\.py"'` returns no results). Enforced by ge-4yl.
- **Every failure carries a hint** (measured: any `"ok": false` JSON output has a non-empty `error.hint` or `error.next_action`). Enforced by ge-13w.
- **Doc-truth parity** (measured: every `/grd:*` skill named in PITCH exists or has a "coming in Phase N" stub; no traceback on any slash command). Enforced by ge-nub.
- **Exit-code discipline** (measured: shell callers can route on 0/1/2/3/4 and each is documented). Enforced by ge-oc0.

When all three transcripts run green and all four secondary metrics hold, the integration is shipped in the sense Rome meant.

---

## 9. What This Document Commits To (new beads)

The workflow thinking above surfaces four items that were not in the UX study's filed list. They are filed now.

1. **Ship-both meta-bead** (tracks §5 Day-0 script + §7 demo as one shippable unit; blocks on P0 wave + ge-5o8, ge-ln7, ge-cla, ge-coq, ge-2zu, ge-8g5, ge-j8k). Not an implementation bead — a gate bead.
2. **Canonical physicist-demo template** (`grd new-project --template simple-mechanics`). The §7 demo currently has no backing template. P1.
3. **`grd lean demo`** / `/grd:lean-demo` — the Rome persona's single entry point. Runs §7 end-to-end against `simple-mechanics`, with a `--dry-run` that clearly labels mocked stages until all dependencies ship. P1.
4. **`phase complete` refuses to close on outstanding `needs-formalization`** claims (the §6 forcing function). P2. This is a policy decision, not just code — Rome should weigh in before it ships.

All four are filed with `discovered-from: ge-7ah` and linked to this document.

---

## 10. What This Document Does Not Cover

- **Proof-style choices** (tactic vs. term, structured vs. imperative, Isar rendering). Covered by ge-epra (P3 aspirational).
- **AI proving modality selection** (Ollama vs. hosted, LLMLean vs. ReProver). Covered by nitro Q10 in external-research.md; deferred until Flow B hammer (ge-k8s) lands.
- **Counterexample finding** (ge-16j, P2). Orthogonal to the three core flows; picked up after ship-both.
- **Cross-project Lean sharing** (how a lemma proved in Project A becomes a `require`-able dependency of Project B). Important eventually; not in the north-star.

---

*End of MATHEMATICIAN-WORKFLOWS.md. Updated with each P0/P1 bead that lands — if a flow changes, this doc is the first thing to update.*
