# External User Research: How Lean/Mathlib/LeanDojo/PhysLean Users Actually Work Today

**Bead:** ge-m0m (Lean UX child C)
**Parent:** ge-7ah (Lean UX design study for math/physics users)
**Author:** getresearch/polecats/nitro
**Date:** 2026-04-14
**Scope:** External-facing user research — patterns to match, anti-patterns to beat.

---

## Executive Summary

We surveyed four cohorts of Lean 4 users: Mathlib contributors, AI-proving researchers
(LeanDojo / ReProver / Pantograph / DeepSeek-Prover / Kimina / BFS-Prover), the
Blueprint-methodology community (Tao's PFR, Buzzard's FLT, Equational Theories, Sphere
Eversion), and physics-leaning users (PhysLib/PhysLean, SciLean). Across ~70 sources —
Zulip threads, GitHub issues, arXiv papers, Mathstodon/Twitter posts, blog tours from
Tao, Buzzard, Massot, Macbeth, and outsider HN/Reddit commentary — the single most
important finding is this:

**Users don't stall at proving. They stall before and after.** Before: onboarding
(`lake exe cache get`, Windows toolchain, Mac `gmp`, VS Code Lean 3/4 extension
confusion) and "informal claim → typed Lean statement". After: error messages (esp.
`failed to synthesize instance`, typeclass resolution loops, heartbeat timeouts) and
premise retrieval (finding the Mathlib lemma that already exists). Proof search itself
is the *least* of their problems — automation like `exact?`, `simp`, `linarith`,
`aesop`, and the new `LeanHammer` can close a surprising fraction of routine steps.
GRD's leverage is therefore disproportionately on the *wrappers* around proof, not
proof synthesis itself.

### Five patterns we should steal

1. **Blueprint's dependency-graph view.** Unanimously named by Tao, Buzzard, and Massot
   as the single most-praised artifact. A proof is a graph, a project is a claim board,
   and a dashboard of green/yellow/red nodes doubles as a "what's ready to claim"
   surface. GRD already decomposes research into phase tasks — surface them the same way.
2. **Sledgehammer-style "Try this:" UX** (Isabelle/HOL). One button. Returns a
   clickable, human-readable tactic snippet. The invoked automation is transparent —
   no oracle, the resulting term re-checks in the kernel. LeanHammer (2025) is the first
   real Lean equivalent; `exact?`/`apply?` are the closest existing analogs. GRD
   should expose a single `grd lean try-prove` that returns a ranked, clickable list.
3. **Verbose tactic-state / infoview.** Macbeth: *"Lean's live-updating visual
   representation of the proof state frees you from needing to keep this in your working
   memory."* Every serious user names this as the reason they stuck with Lean. GRD's
   CLI should echo the current goal state in stdout/JSON after every operation — don't
   make users open the LSP to see what they're looking at.
4. **Atomization into named micro-lemmas** (PFR, FLT, Equational Theories). Tao:
   *"a significant step towards resolving the problem."* Buzzard: *"you do not have
   to understand the whole proof of FLT in order to contribute."* GRD phase decomposition
   already does this; surfacing it as a first-class CLI concept (`grd lean blueprint-status`)
   is strictly aligned.
5. **Lowest-friction on-ramp: Ollama + a tactic command** (LLMLean). The tool with the
   best grassroots day-to-day use. Not a Python framework, not a Docker container —
   a single lake package and `llmstep` / `llmqed`. GRD's `grd lean prove` should feel
   like this: one subcommand, JSON out, reuse the daemon.

### Five anti-patterns to avoid

1. **Error-message opacity as a default.** `failed to synthesize instance`, heartbeat
   timeouts with no actionable guidance, "Invalid Lake configuration" fired on network
   errors, "unknown exponent digit" when a theorem name starts with a digit. Every
   GRD error surface needs a one-line human cause and a suggested next action. *Never*
   ship a bare Lean error through the CLI without annotation.
2. **Research-code-as-product.** LeanDojo, Pantograph, COPRA, DeepSeek-Prover-V2
   checkpoints, AlphaProof (no code!), BFS-Prover-V2 — all require PhD-level plumbing
   to go from "I read the paper" to "it ran on my goal." The pattern: `git clone`,
   trace mathlib for hours, manage Python deps, wire up an RL harness. Nobody outside
   the authors actually uses these day-to-day. GRD's Lean integration must be the
   opposite: one install, one subcommand, working-by-default.
3. **Fragmented REPL / interaction layers.** Pantograph vs. official REPL vs.
   LeanInteract vs. Kimina Lean Server vs. LeanDojo's tactic injection. Every paper
   invents its own. GRD should pick one (the official `leanprover-community/repl`
   extended with a Pantograph-style `have`/`conv`/`calc` interaction model is the
   pragmatic choice) and never expose the choice to users.
4. **Benchmark-chasing over real work.** BFS-Prover-V2 hits 95% on miniF2F; the
   miniF2F-Lean Revisited paper (Nov 2025) found 16 unprovable statements, >50%
   informal/formal mismatches, and pipeline accuracy drops to ~35% on the original
   benchmark / ~70% on v2. LLM-judged autoformalization scores collapse 10–35
   percentage points under human review. GRD should not report benchmark numbers as
   the metric; the metric is "did this user ship a verified claim this week?"
5. **Assume your audience is a mathematician.** `Mathematics in Lean`, Natural Number
   Game, Mechanics of Proof — all mathematician-targeted. Coq kept mindshare among CS
   people via Software Foundations; Lean has no equivalent. Physicists have *literally
   no canonical on-ramp* — the June 2025 Padole blog describes being onboarded to
   PhysLean via a LinkedIn DM from the author. GRD's docs should explicitly handle
   two personas (working scientist, research ML engineer), not default to "you know
   `obtain` already."

---

## Persona Time Budgets

We modeled three personas. All times are medians from the cited sources; variance is
wide. Minutes unless marked.

### Persona A — "Mature Mathlib contributor" (baseline)

Working on a 1-page undergraduate theorem already within Mathlib's scope.

| Step | Median time | Source |
|---|---|---|
| Sketch informal proof | 5–15 min | internal |
| Write Lean statement (find typeclass, variables, naming) | 5–30 min | Mathlib PR norms |
| First `exact?` / `apply?` pass | <1 min (often succeeds) | emallson blog; searching-for-theorems post |
| Loogle / Moogle / LeanExplore search for missing lemma | 1–10 min | arXiv 2506.11085 |
| Full proof (tactics, rewrites) | 15–60 min | Tao's 15-min PFR proof; emallson |
| PR + reviewer round-trip | ~2 weeks (median) | arXiv 2508.21593, "Growing Mathlib" |
| **End-to-end: informal → merged Mathlib** | **~2–3 weeks** | (dominated by review queue) |

### Persona B — "New user, 2–8 weeks in"

Has read TPIL + started `Mathematics in Lean`. Wants to state and prove a lemma from their own paper/class.

| Step | Median time | Source |
|---|---|---|
| Install elan + open a Lake project (golden path, no bugs) | 20 min | Lean install docs |
| Install + cache mathlib for the first time | 30–90 min | Zulip "can't get olean cache" |
| First `import Mathlib` + VS Code green light | 5 min – hours | "Waiting for lean server to start…" |
| Translate informal claim to Lean statement | **hours to days** | Tao Mastodon: "1 hour per line" week 1 |
| First attempt at proof (tactic trial-and-error) | 30 min – several hours | emallson |
| Resolve first `failed to synthesize instance` error | 15 min – blocks for a day | lean4#2847 |
| **End-to-end: informal → typechecks** | **1–3 days** for a trivial lemma | triangulated |

### Persona C — "Physicist with a paper, never used Lean"

Has a 20-page paper with a derivation. Wants to express a main claim in Lean.

| Step | Median time | Source |
|---|---|---|
| Find PhysLib/PhysLean at all (rebrand/discoverability) | hours of searching | PhysLib homepage, no catalog |
| Install Lean + PhysLib deps | 1–4 hours | SciLean OpenBLAS, PhysLib `lake build` |
| Find a template example close to their domain | hours to days | no tutorial; clone the repo, read files |
| Write paper-claim as Lean statement | **days to weeks** | Tooby-Smith 2HDM took months, he's the author |
| Actually get the statement typechecking | days | library gaps (no tensor-index tactics, limited measure theory) |
| Prove anything non-trivial | **weeks to months** | Tao PFR week-1 ramp; AMS Notices "Anatomy" |
| **Realistic outcome** | **most abandon at step 2–4** | sample size n≈0 public independent users |

### Persona D — "AI-proving researcher"

Building on LeanDojo/Pantograph/LeanCopilot for an RL pipeline or benchmark eval.

| Step | Median time | Source |
|---|---|---|
| Set up LeanDojo/Pantograph (Python deps, toolchain pin) | 2–8 hours | LeanDojo README |
| Trace mathlib to extract (state, tactic, premise) tuples | 1–24 hours | LeanDojo benchmark construction |
| Plug into ReProver / MCTS / custom harness | days | research code quality |
| Run eval on miniF2F / ProofNet / LeanDojo Benchmark | 1–12 hours | GPU-bound |
| **Headline benchmark number** | ready in a week | |
| **Contribute anything to real Mathlib** | ~never (per Zulip consensus) | |

---

## The 10 Specific Questions, Answered

### Q1 — Median time from "I have an informal claim" to "I have a Lean statement"?

**Mature Mathlib contributor:** minutes to ~1 hour. Dominated by naming conventions and
typeclass assumption choice, not math. Copy-paste from similar Mathlib lemmas is the
standard technique.

**New user:** hours to days. Tao — an exceptional beginner — reported ~1 hour per *line*
during his week-1 PFR ramp: *"more tedious than expected… the bottleneck was my own
ignorance of the syntax and tools available in Lean."* A typical new user needs 2–4
weeks before they can reliably write a stated theorem that typechecks.

**Physicist:** days to weeks *if* they don't abandon. No canonical on-ramp exists.

There is no formal survey. This is qualitative consensus across Zulip "new members"
(`#113489-new-members`), the emallson beginner-companion blog, and the Mathlib Initiative
onboarding docs (arXiv 2508.21593, "Growing Mathlib"). The "Is there code for X?" Zulip
stream alone runs at ~300 messages/week — direct evidence that even experts regularly
stall on this step.

### Q2 — What % of attempted formalizations stall, and where?

Triangulating across benchmarks and real projects:

- **End-to-end pipeline (autoformalize + prove) on original miniF2F:** ~65% stall
  (35% success). (arXiv 2511.03108)
- **End-to-end on miniF2F-v2 (corrected benchmark):** ~30% stall (70% success).
- **Research-level autoformalization (INDIMATHBENCH / PutnamBench with GPT-5):**
  89–93% stall.
- **Undergraduate autoformalization:** ~55% stall.
- **Hidden stall rate** — LLM-judged passes that humans reject: Herald 97.5% → 62.7%;
  Kimina 98.4% → 90.6%. So ~10–35 points of "passing" outputs are actually
  semantically wrong.

**Where they stall** (in rough order):
1. Hallucinated Mathlib names, wrong imports, Lean 3 syntax bleeding into Lean 4.
2. Semantic drift — compiles but doesn't state what the NL said (flipped
   inequalities, missing hypotheses, weakened conclusions).
3. Tactic synthesis on long proofs — LLMs lose goal coherence past a few backtracks.
4. Missing definitions — problem needs concepts not in Mathlib; model can't recognize this.
5. Typeclass resolution loops / stuck metavariables (lean4#2847, #13063, #10055, #7988).
6. Proof-search budget — SoTA requires hundreds–thousands of samples; interactive use
   gets ~10.

### Q3 — Common bootstrap friction for new Lean users?

In order of severity:

1. **`lake exe cache get` failures.** Stale toolchain, corrupted cache, VS Code holding
   a lock, flaky downloads. Zulip-tribal workaround: `cp lake-packages/mathlib/lean-toolchain .`
   + `lake exe cache get!` (bang) + close VS Code. Not documented in Mathlib README.
2. **Windows-specific install.** curl/schannel errors, PowerShell `Start-BitsTransfer`
   missing, antivirus blocking cache download, users accidentally installing the Lean
   **3** VS Code extension. Lean 3 ↔ Lean 4 docs are still conflated on Google.
3. **macOS `gmp` dependency.** Undocumented `brew install gmp` required for some toolchain
   setups.
4. **RAM floor.** 8 GB makes a full Mathlib build impossible. Recommended floor 16–20 GB.
5. **VS Code "Waiting for lean server to start…" hang** — almost always because the user
   opened a single file instead of the project folder. Buzzard: *"you need to run it
   as part of a project."*
6. **Unicode typos** (`|` vs `\|`, `<-` vs `←`) producing wildly misleading errors.
7. **Project vs. single-file confusion** — `lean foo.lean` outside a Lake project
   produces `unknown package 'Mathlib'`.
8. **China / restricted networks** — GitHub blocks + Mathlib cache CDN access, undocumented
   proxies.

Elan itself is rarely the blocker. The chain *elan → lake update → cache → first import*
is where people quit.

### Q4 — UX features mature users (Tao, Buzzard, Massot, Macbeth) explicitly call out?

**Unanimous:**
- **`exact?` tactic** (Tao, emallson) — "will automatically search to see if the goal
  can already be deduced immediately from an existing lemma."
- **Blueprint dependency graph** (Tao, Buzzard, Massot) — *"One feature of the blueprint
  that I find particularly appealing is the dependency graph that is automatically
  generated from the blueprint."*
- **Live tactic-state / infoview** (Macbeth) — *"Lean's live-updating visual
  representation of the proof state frees you from needing to keep this in your working
  memory."*
- **Silent-success** (Macbeth) — *"the absence of errors is the proclamation that you
  have succeeded."*

**Tao-specific:** `calc` blocks, `field_simp`, `ring`, `gcongr`, `linarith`,
`have`/`suffices`, GitHub Copilot as autocomplete.

**Buzzard-specific:** tactics as "tricks the program already knows," Zulip as search
fallback, Natural Number Game as an on-ramp. But: *"mathlib is still missing literally
hundreds of the definitions used in modern day mathematics."*

**Commelin (Liquid Tensor) specific:** Blueprint atomization; `polyrith`, `field_simp`,
`norm_num`, `norm_cast`, `linarith`, `gcongr` as essentials.

**Massot-specific:** "verbose-lean4" natural-language tactics for pedagogy; tactic mode
over term mode for onboarding.

**The granularity principle** (Tao): *"Ideally, each step in a proof should be of the
natural size that a mathematician would interpret as a significant step towards resolving
the problem."* GRD's phase decomposition should aim for this granularity.

### Q5 — What does a LeanDojo / ReProver / Pantograph user actually do day-to-day?

Two very different user types, neither of which looks like "mathematician closing a hole":

**Research ML engineer (the real user):**
1. Clone LeanDojo/Pantograph, pin Lean toolchain, install Python deps.
2. **Trace a Lean project** — run the tool over mathlib4 or a target repo to extract
   `(proof state, tactic, premises)` tuples. Hours to days.
3. Load ReProver retriever + generator, or plug into Pantograph's MCTS harness.
4. Run evals against miniF2F / ProofNet / LeanDojo Benchmark 4 (258k tactics).
5. Iterate on training loops. Most effort is in Lean subprocess plumbing, not proofs.

**Mathematician dabbler (rarer):** Installs LeanCopilot (`require` in lakefile + `lake
exe LeanCopilot/download`), opens VS Code, types `suggest_tactics` or `search_proof`,
takes the best of ~8 suggestions, often falls back to hand-writing. OR installs LLMLean
+ Ollama, pulls Kimina/BFS/Goedel, tries `llmstep`/`llmqed`. Zulip reception: *"hit-or-miss,"
"fun but not very helpful,"* occasional genuine wins.

**Nobody in the public record uses LeanDojo or Pantograph directly as part of a day-to-day
proving workflow.** They are substrates for someone else's product. The only tools with
meaningful grassroots uptake are **LeanCopilot** (1.3k stars) and **LLMLean** (CMU-L3,
quiet practical success as the Ollama-backend shim).

### Q6 — Physicist bootstrap: paper → Lean statement. Real example traces?

There is no smooth path. A physicist with a paper today typically does one of:

1. **Give up at install.** SciLean OpenBLAS / Lake version mismatches / VS Code
   extension confusion.
2. **Read `Mathematics in Lean`.** Excellent for mathematicians; zero physics content.
3. **Clone PhysLib/PhysLean, pattern-match from examples.** The canonical "worked example"
   is Tooby-Smith's own 2HDM paper (arXiv 2603.08139, 2026), which is simultaneously
   a research paper AND the de-facto onboarding tutorial.
4. **Write a Blueprint first.** Assumes LaTeX familiarity.
5. **Bail to Copilot/Claude.** Tao's 33-minute one-page formalization via Copilot +
   `canonical` tactic (Mastodon, May 2025) is the emerging style: let the LLM draft,
   let Lean check.

**Real trace 1 (the only public one):** Joseph Tooby-Smith formalized the Maniatis et
al. (2006) 2HDM stability argument end-to-end in PhysLean, caught a genuine mathematical
error, and got it confirmed by the original authors. This is the marquee result:
*"Lean caught an error in a widely-cited physics paper."* Advanced Science 2025
(paywalled) is the perspective piece. Lean file was 27,258 chars vs 21,697 chars of
the original LaTeX — ~25% expansion ratio.

**Real trace 2 (illustrates the gap):** Parikshit Padole (Imperial undergrad, June 2025
blog) found PhysLean via a **LinkedIn post**, DM'd Tooby-Smith, got onboarded by direct
conversation. This is not a scalable bootstrap story — it's "know somebody." Sample size
for *independent-physicist-uses-PhysLean-cold* is essentially zero in public record.

**HepLean paper (Comp. Phys. Comm. 2025):** the Lean file for a main result was ~25%
longer than the LaTeX paper. Expect a formalization to bloat your artifact 25%+ relative
to the informal write-up.

### Q7 — Blueprint discovery: how do people find it?

The weak link. No central catalog of Blueprint projects exists. People discover Blueprint via:

1. **Tao's blog** — the foundational Nov 2023 post is the top Google result for "Lean
   blueprint."
2. **Buzzard's Xena blog + the FLT announcement** on the Lean community blog.
3. **Zulip streams** for specific projects (`#FLT`, `#PFR`, `#equational-theories`).
4. **Mathlib's `lean_projects.html` listing**, which does **not** tag which projects
   use Blueprint — users must click through each.
5. **Serendipity: Twitter/Mastodon posts from Massot, Commelin, Tao.**

The `leanprover-community/LeanProject` template is the idiomatic Blueprint scaffold (via
Monticone), but it's not surfaced at the top of the Lean install flow. The leanblueprint
README (Massot) is good but assumes you've already decided to use it.

**What's missing:** a `leanblueprint.io` (hypothetical) catalog page listing every
project using the methodology, with its dependency-graph thumbnail, status (active /
stalled / complete), and a "how to contribute" link. Zero such catalog today.

### Q8 — Tactic-search tools: loved / surprising / hated?

**Loved:**
- `exact?` — universally praised as the cheap first shot.
- `apply?` — same family, less used but valued.
- `simp?` — for generating `simp only [...]` hints (Mathlib style review requires this).
- `rw?` — narrower use, occasional big wins.
- **Loogle** — precise type-signature search; *"If you know specific things about what
  you're looking for, loogle can help"* (Thomas Murrills). Brittle on naming drift.
- `aesop` — white-box, extensible proof search; now powers `measurability` and
  `continuity`. Tao's aspirational "immediate" tactic substitute.
- `ring`, `field_simp`, `linarith`, `omega`, `gcongr`, `norm_num`, `norm_cast`.

**Surprising (mixed reputation):**
- **Moogle** — NL queries work but "somewhat outdated" per the community blog; effectively
  stale per Zulip reports.
- **LeanSearch / LeanExplore / Lean Finder** — 2025–26 semantic-search entrants that
  outperform older tools in head-to-head but haven't displaced `exact?` as the default.
  LeanExplore: ranked 1st most often vs. Loogle/Moogle. Lean Finder: 81.6% preference
  vs. 56.9% for LeanSearch on real user queries.
- **LeanCopilot** — 74.2% step automation on benchmarks (vs. `aesop`'s 40.1%) but
  Zulip: *"hit-or-miss, fun but not very helpful."*

**Hated / frustrating:**
- **`nlinarith`** — oracle runs outside the tactic monad; intermediate steps cannot
  be traced. Silent success/failure.
- **`polyrith`** — external Sage API call; network dependency + latency.
- **`decide`** — can time out silently; breaks on `Decidable` instances defined by
  well-founded recursion.
- **`exact?` / `apply?` at scale** — emallson: *"perform noticeably worse with large
  proof states, which makes the interactive experience worse."* Exactly when you need
  it most.
- **Typeclass inference loops** (lean4#13063, #10055, #7988) — can crash the LSP.

### Q9 — Error messages users complain about most?

Top 5 by volume across Zulip, GitHub issues, and blogs:

1. **`failed to synthesize instance`** — obscure; hard to debug without
   `set_option trace.Meta.synthInstance true` (an expert move). Often: missing `Decidable`,
   `Repr`, `DecidableEq`, or a circular instance chain. Lean docs now have an
   *About* page for this, but the in-editor message is unchanged.
2. **`type mismatch` printing identical-looking types** (lean4#333). Types differ only
   in elaboration metadata, instance args, or universe levels. Lean 4.14 partially
   improved this with type ascriptions and function-body diffs.
3. **`(deterministic) timeout at 'whnf', maximum number of heartbeats (200000)`** — the
   heartbeat abstraction is unexplained. Zulip "Running out of heartbeats" thread shows
   users just crank `set_option maxHeartbeats 400000` blindly. `count_heartbeats in` is
   the tribal band-aid.
4. **`deep recursion detected`** — actual stack overflow, often from circular instance
   chains. Sometimes crashes the LSP.
5. **Universe errors** (`invalid universe level`, `universe level 2 not ≤ 1`) — cryptic
   without type-theory background.

**Honorable mentions:**
- `unknown identifier ℕ` / `ℝ` (forgot `import Mathlib`).
- `unknown package 'Mathlib'` (ran Lean outside a Lake project).
- `"missing exponent digits in scientific literal"` when a theorem name starts with a
  digit (lean4#9450) — nowhere near the actual typo.
- `"Invalid Lake configuration"` fired on *network* errors (lean4#6827).
- `maximum class-instance resolution depth has been reached` — often masks a Unicode typo.

**Buzzard's summary:** *"the real error was some subtle syntax error (`|` instead of
`\|`) and Lean got completely confused; the error message was ultimately irrelevant."*

### Q10 — What do users wish existed?

Distilling across all sources:

1. **Sledgehammer-equivalent one-click hammer** with clickable-to-insert output.
   LeanHammer (2025) is the first real answer at 33% Mathlib coverage; not yet a UX.
2. **Plain-English error translation layer** — "what does `failed to synthesize instance
   Decidable` actually mean, and what do I do?"
3. **Blueprint ↔ Lean auto-sync** — close Tao's explicit friction: *"The current version
   of Blueprint does not automatically verify the proof, so we have to manually update
   the blueprint as well."*
4. **A browsable catalog of Blueprint projects** (Q7).
5. **Intent-aware premise retrieval** that understands informal math phrasing
   (Lean Finder's direction), handles naming drift, and tracks Mathlib nightly.
6. **Mathlib-freshness-aware copilot** that sees proof state + error messages. Zulip has
   asked for this since 2023; LeanCopilot does it narrowly, GitHub Copilot/Cursor don't
   see Lean's infoview.
7. **Canonical non-mathematician on-ramp** — Coq's Software Foundations equivalent.
   Specifically for physicists: a "Mechanics of Proof" for physics.
8. **Domain-specific tactics for physics** — tensor-index manipulation, dimensional
   analysis. Current `field_simp` works for fields; nothing for index gymnastics.
9. **Automatic `maxHeartbeats` tuning** when proofs time out.
10. **Counterexample-generation mode** — Boris Alexeev (Xena, Dec 2025) explicitly calls
    AI-as-counterexample-finder *more* valuable than AI-as-prover for research.
11. **Proof-as-prose rendering** — especially now that AI agents generate million-line
    proofs. Isabelle's Isar shows the way.
12. **Zero-install browser IDE for real projects** (not just NNG). Gitpod-style "spin
    up PhysLean + Copilot in one click."
13. **CLI-first, not Python-notebook-first** for model invocation. `prove --theorem
    thm.lean --model kimina` with a config.
14. **Traceable `nlinarith`/`polyrith`** — no external Sage; show the witness.
15. **Faster PR review cycle** (~2-week median) — structural, not GRD's problem, but
    Mathlib Initiative is explicitly targeting it.

---

## Top 10 Features GRD's Lean Integration Should Consider

Each tagged with a **phase target** (P0 = ships now, P1 = next 2 quarters, P2 = 2+
quarters out, P3 = aspirational). Numbered by our priority ranking, which is
severity-of-unmet-need × GRD's existing leverage.

### 1. **Error-explanation layer on top of `grd lean check`.** [P0]

Every Lean error in the CLI output gets an annotated "what this means + what to try"
line. Special-case the top 5 errors from Q9. A lookup table with ~30 entries will
cover ~80% of user-visible failures.

> *Leverage:* Lowest effort, highest user impact. GRD already parses Lean JSON errors
> in the existing `grd lean check` — we just attach a hint string.

### 2. **"Informal claim → Lean statement" assistant: `grd lean stub-claim`.** [P1]

CLI takes a natural-language claim (from a phase's VERIFICATION.md or a raw prompt),
returns a skeleton Lean statement with placeholder variables/hypotheses, plus Loogle /
Mathlib search results for the most relevant existing definitions. Addresses the
*single highest-leverage unmet need* — the "Is there code for X?" Zulip stream is
direct evidence this is unsolved.

> *Leverage:* Tao's week-1 bottleneck, every new user's wall. Time-to-statement is
> the right north-star metric.

### 3. **Blueprint-first scaffolding: `grd lean init-blueprint`.** [P1]

Generate a minimal leanblueprint-compatible LaTeX skeleton from GRD's phase task
graph. GRD phases → blueprint nodes, phase dependencies → `\uses` edges. Automate
the manual sync Tao complained about: `grd lean blueprint-status` auto-marks
`\leanok` on lemmas whose Lean counterpart typechecks.

> *Leverage:* Dependency graph is the unanimously most-praised artifact; GRD already
> has the underlying phase-graph data.

### 4. **Hoogle-style search wrapped by the CLI: `grd lean search "<query>"`.** [P1]

Dispatch intent-detection: if the query looks like a type signature, call Loogle;
if NL prose, call LeanExplore / Lean Finder; expose both results side-by-side with
source-URL annotations. Ships as a CLI + a skill, never asks the user to choose a
backend.

> *Leverage:* Premise retrieval is an active battleground with 2025 entrants; GRD can
> aggregate without picking a winner.

### 5. **"Try this:" hammer surface: `grd lean try-prove`.** [P2]

Run `exact?`, `apply?`, `aesop`, `LeanHammer`, `simp_all`, and (optionally) a
model-backed `llmqed` in parallel. Return a ranked, clickable list of tactic snippets
the user can paste. Each snippet is kernel-checked before being returned — follow
Isabelle's "never ship an oracle" discipline.

> *Leverage:* The Sledgehammer UX pattern is the single most-cited cross-pollination
> lesson. LeanHammer exists; GRD just orchestrates.

### 6. **LSP-aware daemon with JSON goal-state echo.** [P0 — extend existing daemon]

Every `grd lean check` / `grd lean prove` / `grd lean verify-claim` emits the
current goal state (before + after) in JSON, by default. Users don't have to open
VS Code to see what Lean is looking at.

> *Leverage:* Macbeth's "free your working memory" point. Already have a daemon
> per pitch; this is a JSON schema change.

### 7. **Persona-aware docs: `/grd:lean-bootstrap --for {mathematician,physicist,ml-researcher}`.** [P1]

Three distinct on-ramp flows:
- **Mathematician:** `Mathematics in Lean` + Mathlib patterns, starts with stating a lemma.
- **Physicist:** PhysLib integration, starts with "express a paper claim."
- **ML researcher:** Kimina / BFS-Prover / LLMLean setup, starts with "eval on miniF2F."

Each flow is a different skill with tailored prose, not a generic "here's Lean."
This is the Software-Foundations-style missing on-ramp.

> *Leverage:* No competitor does persona routing. Specifically, physicists are 100% un-served today.

### 8. **Automatic `maxHeartbeats` tuning on timeout.** [P2]

When a proof times out, GRD reruns with 2× heartbeats up to a configured ceiling, then
reports the winning value and suggests `set_option maxHeartbeats N` insertion.

> *Leverage:* Specific, small, highly-complained-about. Closes one Zulip thread.

### 9. **Counterexample-finding mode: `grd lean find-counterexample <statement>`.** [P2]

Use `decide`, `Polyrith` in reverse, Plausible (property-based), and/or LLM-proposed
concrete values. Alexeev (Dec 2025) names this as the highest-value AI-augmented
verification primitive. It also aligns with GRD's existing "limiting cases /
numerical spot checks" heuristics — formalize them as counterexample searches.

> *Leverage:* No existing Lean tool does this as a first-class feature. Major
> differentiation vector.

### 10. **Proof-as-prose rendering: `grd lean render-proof <file>`.** [P3]

Given a Lean proof, emit an Isar-like narrative rendering: `have … by …`,
`thus … from …`, `finally show …`. For AI-generated proofs (which will dominate in
the 2026+ horizon), this is table-stakes reviewability. Ship alongside the raw
tactic script.

> *Leverage:* Aspirational but durable. Addresses the million-line-proof review
> crisis that AlphaProof / Aristotle have already introduced.

### Phase mapping summary

- **Phase P0 (ship now):** #1 error layer, #6 JSON goal echo.
- **Phase P1 (next ~6 months):** #2 stub-claim, #3 blueprint init, #4 search, #7 personas.
- **Phase P2 (6–12 months):** #5 hammer, #8 heartbeat tuning, #9 counterexample mode.
- **Phase P3 (12+ months / research):** #10 proof-as-prose.

---

## Direct Quotes Worth Reproducing in Downstream Docs

**On learning curve (outsider, representative):**
> "The learning material was very choppy and difficult for us to work through. It had
> sparse exercises, and there was a sudden cliff of complexity … felt like the target
> audience (appropriately) was mathematicians, and we're decidedly not mathematicians."
> — Nicole Tietz, ntietz.com blog

**On time-to-first-proof (Tao, an exceptional user):**
> "More tedious than expected, with each line of proof taking about an hour to formalize.
> In the first week of the project, the bottleneck was my own ignorance of the syntax
> and tools available in Lean; but later the bottleneck became the tools themselves."
> — Tao, Mastodon Nov 2023

**On specifications (perennial outsider concern):**
> "It's surprisingly easy to write an incorrect spec and think it's correct, even under
> scrutiny, and so it turns out that you've proved the wrong thing." — HN thread
> id=47047027

**On the Blueprint dependency graph (Tao):**
> "One feature of the blueprint that I find particularly appealing is the dependency
> graph that is automatically generated from the blueprint."

**On Blueprint's sync gap (Tao):**
> "The current version of Blueprint does not automatically verify the proof (even though
> it does compile in Lean), so we have to manually update the blueprint as well."

**On atomization (Buzzard, FLT announcement):**
> "You do not have to understand the whole proof of FLT in order to contribute. The
> blueprint breaks down the proof into many many small lemmas."

**On Mathlib's ceiling (Buzzard):**
> "Mathlib is still missing literally hundreds of the definitions used in modern day
> mathematics."

**On the Rosetta Stone framing (Buzzard on Blueprint):**
> "Half of the Rosetta Stone that Patrick is creating, which will explain one story in
> two languages — a human language, and a computer language."

**On infoview (Macbeth):**
> "Lean's live-updating visual representation of the proof state frees you from needing
> to keep this in your working memory."

**On silent success (Macbeth, Anatomy of a Formal Proof):**
> "Lean checks the correctness of the proof and confirms it with its silence: the
> absence of errors is the proclamation that you have succeeded."

**On Mathlib search (emallson):**
> "The biggest early frustration was finding theorems to use. … mathlib documentation
> exists, it lacks hoogle-style search functionality."

**On error-message opacity (Buzzard):**
> "The real error was some subtle syntax error (`|` instead of `\|`) and Lean got
> completely confused; the error message was ultimately irrelevant."

**On AI shifting workflows (HN commenter):**
> "With agentic AI that can run lean via CLI my workflow changed completely and I
> rarely write full proofs anymore."

**On Massot's formalization manifesto:**
> "A proof assistant can handle complexity … mathematicians with no computer science
> training can become proficient users of a proof assistant in a relatively short
> period of time."

**On Sledgehammer (Paulson):**
> "Sledgehammer requires no user configuration and can be invoked with a single mouse
> gesture at any point in a proof. … It automatically finds relevant lemmas from all
> those currently available."

---

## Annotated Source List

### Mathlib / Zulip / community workflow (11)

1. [Searching for theorems in Mathlib (community blog)](https://leanprover-community.github.io/blog/posts/searching-for-theorems-in-mathlib/) — Canonical walkthrough of Mathlib search order: `exact?`/`apply?`/`rw?` → Loogle → Moogle/LeanSearch/LeanExplore.
2. [A beginner's companion to theorem proving in Lean (emallson)](https://emallson.net/blog/a-beginners-companion-to-theorem-proving-in-lean/) — Best outsider review; flags `exact?`/`apply?` degrading on large goals and the "no hoogle-style search" gap.
3. [Tao — formalizing PFR in Lean4 using Blueprint](https://terrytao.wordpress.com/2023/11/18/formalizing-the-proof-of-pfr-in-lean4-using-blueprint-a-short-tour/) — The foundational UX-story post; dependency graph, `exact?`, Copilot praise; manual-sync friction.
4. [Tao — slightly longer Lean 4 proof tour](https://terrytao.wordpress.com/2023/12/05/a-slightly-longer-lean-4-proof-tour/) — 15-minute-proof claim; granularity principle; `field_simp`, `ring`, `gcongr`.
5. [Tao — Equational Theories Project tour](https://terrytao.wordpress.com/2024/10/12/the-equational-theories-project-a-brief-tour/) — "Drastic improvement over PFR" with GitHub-Projects dashboard.
6. [Tao on Mastodon, 1hr/line](https://mathstodon.xyz/@tao/111305336701455719) — Direct quote on week-1 formalization velocity.
7. [leanprover-community/mathlib4](https://github.com/leanprover-community/mathlib4) — Canonical Mathlib repo; onboarding via README.
8. [lean4#2847 — "typeclass instance problem is stuck"](https://github.com/leanprover/lean4/issues/2847) — Canonical "not actionable / intimidating" error complaint.
9. [lean4#333 — type mismatch with identical types](https://github.com/leanprover/lean4/issues/333) — UX landmark bug; partially fixed in 4.14.
10. [lean4#6827, #9450, #13063](https://github.com/leanprover/lean4/issues/6827) — Representative error-location drift bugs.
11. ["Growing Mathlib" (arXiv 2508.21593)](https://arxiv.org/abs/2508.21593) — Mathlib Initiative data: ~1500 open PRs, ~2-week median review wait.

### Zulip threads (5)

12. [Zulip: can't get olean cache](https://leanprover-community.github.io/archive/stream/113489-new-members/topic/Can't.20get.20olean.20cache.html) — User reports "even the import line is taking forever to parse."
13. [Zulip: Lean 4 installation issues](https://leanprover-community.github.io/archive/stream/270676-lean4/topic/Lean.204.20installation.20issues.html) — Windows PowerShell / schannel / BitsTransfer errors.
14. [Zulip: Running out of heartbeats](https://leanprover-community.github.io/archive/stream/270676-lean4/topic/Running.20out.20of.20heartbeats.html) — Source of the `count_heartbeats` workflow.
15. [Zulip: Waiting for lean server to start](https://leanprover-community.github.io/archive/stream/113489-new-members/topic/Waiting.20for.20lean.20server.20to.20start.html) — Buzzard: "you need to run it as part of a project."
16. [Zulip: Machine Learning for Theorem Proving](https://leanprover-community.github.io/archive/stream/219941-Machine-Learning-for-Theorem-Proving/) — Active 2025–26 stream; LeanDojo v2 release, Pantograph concurrency.

### AI-proving ecosystem (14)

17. [LeanDojo (lean-dojo/LeanDojo)](https://github.com/lean-dojo/LeanDojo) — v1 deprecated; v2 is the new path; highest-friction research framework.
18. [ReProver (lean-dojo/ReProver)](https://github.com/lean-dojo/ReProver) — ByT5-based retriever + generator; research baseline.
19. [LeanCopilot (lean-dojo/LeanCopilot)](https://github.com/lean-dojo/LeanCopilot) — 1.3k stars; the *only* mainstream AI tool with real community use.
20. [Pantograph paper (arXiv 2410.16429)](https://arxiv.org/abs/2410.16429) — Pure Lean 4 REPL supporting `have`/`conv`/`calc` incrementally.
21. [DeepSeek-Prover-V2 (arXiv 2504.21801)](https://arxiv.org/abs/2504.21801) — Subgoal decomposition + RL; 88.9% miniF2F.
22. [Kimina-Prover-Preview (Moonshot)](https://github.com/MoonshotAI/Kimina-Prover-Preview) — Model weights + demo; requires separate Kimina Lean Server.
23. [BFS-Prover-V2 (ByteDance-Seed)](https://github.com/ByteDance-Seed/BFS-Prover-V2) — 95.08% miniF2F; redirects interactive users to LLMLean.
24. [AlphaProof Nature 2025](https://www.nature.com/articles/s41586-025-09833-y) — IMO silver; **no code released.**
25. [miniF2F-Lean Revisited (arXiv 2511.03108)](https://arxiv.org/abs/2511.03108) — Benchmark broken: 16 unprovable, ~35% pipeline accuracy on original.
26. [LLMLean (cmu-l3/llmlean)](https://github.com/cmu-l3/llmlean) — `llmstep`/`llmqed` over Ollama; the quiet day-to-day win.
27. [LeanInteract (v0.9.0)](https://github.com/augustepoiroux/LeanInteract) — Python handle with incremental + parallel elaboration.
28. [Kimina Lean Server (arXiv 2504.21230)](https://arxiv.org/html/2504.21230v1) — REST API over official REPL with LRU Mathlib cache.
29. [leanprover-community/repl](https://github.com/leanprover-community/repl) — Official JSON REPL; the piece everyone wraps.
30. [ProofFlow (arXiv 2510.15981)](https://arxiv.org/html/2510.15981v1) — DAG-based autoformalization; ProofScore 0.545 vs 0.123 for full-proof.

### Premise retrieval / search (4)

31. [LeanExplore (arXiv 2506.11085)](https://arxiv.org/abs/2506.11085) — Semantic + BM25 + PageRank; beats LeanSearch and Moogle.
32. [Lean Finder (arXiv 2510.15940)](https://arxiv.org/html/2510.15940v1) — Real user queries cluster into 5 intents; 81.6% preference rate.
33. [LeanHammer (arXiv 2506.07477 + GitHub)](https://github.com/JOSHCLUNE/LeanHammer) — First serious Sledgehammer-for-Lean; 33.3% Mathlib coverage.
34. [Loogle](https://loogle.lean-lang.org/) — Precision type-signature search; Breitner / Lean FRO.

### Blueprint / formalization projects (6)

35. [leanblueprint (Patrick Massot)](https://github.com/PatrickMassot/leanblueprint) — The tool; plasTeX plugin with `\lean{}`, `\leanok`, `\uses{}`.
36. [PFR project (teorth/pfr)](https://teorth.github.io/pfr/) — Canonical Blueprint + Lean reference implementation.
37. [FLT Blueprint](https://imperialcollegelondon.github.io/FLT/blueprint/) — 15-chapter mini-project structure; parallel contribution model.
38. [FLT announcement blog](https://leanprover-community.github.io/blog/posts/FLT-announcement/) — Buzzard's "you do not have to understand the whole proof" framing.
39. [Sphere Eversion Blueprint](https://leanprover-community.github.io/sphere-eversion/blueprint/) — The 2020 pioneer Blueprint project.
40. [Anatomy of a Formal Proof (arXiv 2411.11885)](https://arxiv.org/abs/2411.11885) — Macbeth/Avigad/Commelin/Topaz on what formalizers actually do.

### Physics + scientific computing (6)

41. [PhysLib homepage](https://physlib.io/) — Project homepage after rebrand from PhysLean/HEPLean.
42. [PhysLib GitHub](https://github.com/leanprover-community/physlib) — Repo stats: ~541 stars, 3070 commits, 59 open issues.
43. [Tooby-Smith 2HDM (arXiv 2603.08139)](https://arxiv.org/abs/2603.08139) — First formalization-caught error in a published physics paper.
44. [SciLean GitHub](https://github.com/lecopivo/SciLean) — AD + numerical computing; "early-stage proof of concept."
45. [Scientific Computing in Lean](https://lecopivo.github.io/scientific-computing-lean/) — WIP book; "Code might not work."
46. [Parikshit Padole blog](https://blogs.imperial.ac.uk/parikshit/2025/06/16/how-i-ended-up-talking-physics-with-a-theorem-prover/) — Physicist onboarding via LinkedIn DM; illustrates discovery gap.

### Coq / Isabelle / outsider perception (8)

47. [Paulson — Sledgehammer tips](https://lawrencecpaulson.github.io/2022/04/13/Sledgehammer.html) — "Configuration-free one-click" UX framing.
48. [Isabelle Sledgehammer manual (Isabelle2019)](https://isabelle.in.tum.de/website-Isabelle2019/dist/Isabelle2019/doc/sledgehammer.pdf) — Reference for what "good" ATP UX looks like.
49. [Tietz — first impressions of Lean and Coq](https://ntietz.com/blog/first-impressions-of-lean-and-coq/) — Best single outsider Lean-vs-Coq comparison.
50. [artagnon — Lean versus Coq: the cultural chasm](https://artagnon.com/computing/coq/leancoq) — Sharpest articulation of the mathematician-vs-type-theorist divide.
51. [Natural Number Game (NNG4)](https://adam.math.hhu.de/#/g/leanprover-community/NNG4) — Still the de facto first tutorial; zero-install browser delivery.
52. [Mechanics of Proof (Heather Macbeth)](https://hrmacbeth.github.io/math2001/) — Gentlest modern Lean textbook; Gradescope + Gitpod; best teaching infra.
53. [HN: Lean 4 and AI competitive edge](https://news.ycombinator.com/item?id=47047027) — Spec-correctness caveat; AI-workflow-shift commentary.
54. [HN: Ask HN on learning Lean 4](https://news.ycombinator.com/item?id=45925656) — Confirms users still can't find a canonical learning path.

### Formalization practice / research (5)

55. [LeanAgent (arXiv 2410.06209)](https://arxiv.org/abs/2410.06209) — 155 theorems proved across 23 repos; lifelong learning.
56. [APOLLO (arXiv 2505.05758)](https://arxiv.org/abs/2505.05758) — Compiler-guided repair: 25,600 samples → few hundred at 65.6%.
57. [Goedel-Prover-V2 (arXiv 2508.03613)](https://arxiv.org/abs/2508.03613) — 32B @ 88% miniF2F pass@32; self-correction adds 2.4 pts.
58. [DeepMind formal-conjectures repo](https://github.com/google-deepmind/formal-conjectures) — Open Erdős benchmark in Lean 4.
59. [Xena — Erdős formalization (Alexeev, Dec 2025)](https://xenaproject.wordpress.com/2025/12/05/formalization-of-erdos-problems/) — Three error classes; counterexample finding is AI's best role.
60. [Tao — story of Erdős #126](https://terrytao.wordpress.com/2025/12/08/the-story-of-erdos-problem-126/) — AI lit-search failure; human verification mandatory.

### Secondary references (3)

61. [Massot — Why formalize mathematics (2021)](https://www.imo.universite-paris-saclay.fr/~patrick.massot/files/exposition/why_formalize.pdf) — Foundational manifesto.
62. [Xena Project blog (Buzzard)](https://xenaproject.wordpress.com/) — Long-running Lean pedagogy/opinion source.
63. [leanprover-community/LeanProject template](https://github.com/leanprover-community/LeanProject) — Canonical Blueprint-friendly project scaffold.

---

## Closing Editorial: Where GRD Has Disproportionate Leverage

1. **Don't try to out-prove DeepSeek.** The bench numbers are saturating; real pipeline
   accuracy is 30–70 points lower than the headline. Proof synthesis is the *least* of
   users' problems.
2. **Do own the wrappers.** Error explanation, informal→stated-theorem assistance,
   Blueprint-aware search, persona-routed onboarding — each is a 1–2-week feature with
   clear user demand and no entrenched competitor.
3. **Physics is open territory.** PhysLib has ~540 stars and no independent public user
   in the record. A "`grd lean` for physicists" on-ramp is fully green-field.
4. **Model-backed proving should arrive via Ollama, not Docker.** LLMLean's design is
   the reference: `require` in lakefile, two tactics (`llmstep`, `llmqed`), pluggable
   models, works offline. Anything heavier loses.
5. **Surface the graph.** GRD's phase decomposition IS a blueprint in disguise. Render
   it, with colored nodes, and ship it. That one feature alone would be the most-praised
   Lean-adjacent UX surface of 2026.

---

*End of external-research.md. Feedback to getresearch/crew/bob.*
