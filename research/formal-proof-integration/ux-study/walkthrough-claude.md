# `grd lean` Heuristic UX Walkthrough — Claude

**Author:** polecat rust (Claude, Opus 4.6), on behalf of getresearch/crew/bob
**Date:** 2026-04-14
**Bead:** ge-0b5 (parent ge-7ah — Lean UX design study)
**Scope:** Read-only heuristic walkthrough of the `grd lean` surface from two first-time-user personas. Nothing fixed here. Issues handed back for scheduling against `ge-plk` phase children.

**Surface audited** (as of commit `2e1c1fb9` on `main`):
- CLI: `grd lean {bootstrap, env, ping, check, typecheck-file, prove, verify-claim, serve-repl, stop-repl}` (`src/grd/cli/lean.py`)
- Skill: `/grd:lean-bootstrap` (`src/grd/commands/lean-bootstrap.md`) — **the only formal-proof skill currently shipped**
- Agent: `grd-prover` (`src/grd/agents/grd-prover.md`)
- Design docs: `research/formal-proof-integration/PITCH.md`, `research/formal-proof-integration/AUTOFORMALIZATION.md`

---

## 1. Personas

### Mina — Working Mathematician

Postdoc in analytic number theory. Reads and writes Lean 4 daily. Keeps a personal Mathlib4 fork updated. Published a leanblueprint-backed formalization last year. Comes to GRD because a collaborator mentioned that `grd lean verify-claim` claims to autoformalize claims from a phase SUMMARY. Her mental model is *Blueprint + Pantograph + AI assist*. She expects everything to work end-to-end; when something is half-implemented she wants it labeled as such in `--help` output, not discovered by grepping the source. Her patience threshold for install steps is maybe 15 minutes; her patience threshold for being confused about *what the system just did* is about 30 seconds.

### Priya — Working Physicist

Lattice-QCD postdoc. Has never written Lean. Knows `python`, `mathematica`, `bash`; knows physics conventions cold (metric signature, ℏ=c=1, Fourier convention, gauge choices). Came to GRD because her phase has a polyhedral-cone bound she wants to formally verify — the claim is "∀ configurations in cone C, bound B holds." Her mental model is *Mathematica NSolve / Wolfram Alpha but with proofs*. She has no intuition for Lean error messages or the Mathlib namespace. She will give up and file a bead titled "this failed" the second time an error message mentions `Elab.Term` or `TypeClass synthesis`.

Both personas are first-time GRD-formal-proof users. Both have the `grd` CLI installed and a GRD project initialized. Neither has yet invoked `/grd:lean-bootstrap`.

---

## 2. Heuristic Framework

Scored 1 (critical friction) to 5 (no meaningful friction) per Nielsen heuristic per command. Scoring is the max of Mina's and Priya's expected score — if *either* persona is blocked, the command is blocked.

Heuristics:
1. **Status visibility** — does the user know what the system is doing?
2. **Match real world** — does terminology match the domain (Lean / math / physics), not GRD internals?
3. **User control** — can the user cancel, back out, tweak?
4. **Consistency** — same concept, same name, everywhere
5. **Error prevention** — avoidable mistakes get caught up front
6. **Recognition not recall** — the user sees the options rather than having to remember them
7. **Efficiency / accelerators** — an expert can skip past the beginner scaffolding
8. **Minimalist aesthetic** — the output is the thing they need, nothing more
9. **Error recovery** — errors explain the problem and suggest a fix
10. **Help / docs** — `--help`, skill bodies, and external docs agree

---

## 3. Per-Command Friction Inventory

Severity legend: **C** = critical (blocks the workflow or produces wrong results silently), **M** = major (slows or confuses a first-timer), **m** = minor (polish). Persona tag shows who first trips on it (math / phys / both).

### 3.1 `grd lean bootstrap` + `/grd:lean-bootstrap` skill

| # | Heuristic | Score | Finding | Severity | Persona |
|---|---|---|---|---|---|
| B1 | Status visibility | 3 | Mina runs `/grd:lean-bootstrap` with no flags and sees `tectonic: skipped_not_requested`, `mathlib_cache: skipped_not_requested`, etc. She cannot tell from one line whether "not requested" means "you opted out" or "you forgot a flag." | M | math |
| B2 | Match real world | 5 | Stage names (`elan`, `toolchain`, `pantograph`, `mathlib_cache`) are the actual tool names. Good. | — | both |
| B3 | User control | 4 | `--dry-run` exists; `--force` exists; `--uninstall` exists. Good. But consent state is recorded as `"never"` for mathlib_cache — there is no explicit "I changed my mind" path documented in `--help`. The user has to know to pass `--force`. | m | math |
| B4 | Consistency | 2 | Skill name is `/grd:lean-bootstrap`; CLI name is `grd lean bootstrap`. The skill file lives under `src/grd/commands/` but the backing logic is `grd.core.lean.bootstrap` (different namespace). PITCH promises `/grd:init-blueprint`, `/grd:prove`, `/grd:formalize-claim`, `/grd:blueprint-status`, `/grd:lean-check` — **only `/grd:lean-bootstrap` exists today.** Priya will `grep -r grd: src/grd/commands` and discover the gap. Mina will simply type `/grd:` and autocomplete will tell her. | **C** | both |
| B5 | Error prevention | 4 | Stage 6 / 7 opt-in with consent recorded. Good design. | — | — |
| B6 | Recognition not recall | 3 | The flag set for bootstrap is large (`--with-graphviz`, `--with-tectonic`, `--with-mathlib-cache`, `--with-leandojo`, `--yes`, `--force`, `--dry-run`, `--uninstall`). The skill body explains them but a first-timer invoking `grd lean bootstrap --help` sees a flat list with no grouping between "always runs", "on request", "needs consent". | M | both |
| B7 | Efficiency | 3 | No `--all` shortcut for "give me everything a mathematician needs" (elan + toolchain + pantograph + mathlib cache). Mina has to compose: `grd lean bootstrap --with-mathlib-cache --yes`. Priya wants the HTML blueprint and physics cache; there's no `--physics` preset. | M | both |
| B8 | Minimalist | 4 | Report table is compact. OK. | — | — |
| B9 | Error recovery | 3 | "If any required stage failed, the overall command exits 1. Tell the user which stage failed." The skill body says so but does not show an example failure with a suggested next action. On a real `elan download blocked by corp proxy`, the message Priya sees will be whatever `elan` printed — which is fine for Mina, catastrophic for Priya. | M | phys |
| B10 | Help / docs | 4 | `--help` is rich. But it never mentions that bootstrap is invoked lazily by other commands — Priya will keep re-running it. | m | phys |

**Walkthrough note** — the skill opens with `grd --raw lean env` and `cat .grd/lean-env.json` as context blocks. Priya will not recognize `--raw` (it means "machine-readable, no pretty printer") and may read the `env` output literally, thinking it's shell env vars. This is the first place where GRD-internal jargon leaks into a user-facing skill.

### 3.2 `grd lean env`

| # | Heuristic | Score | Finding | Severity | Persona |
|---|---|---|---|---|---|
| E1 | Status visibility | 4 | Emits `LeanEnvStatus`: lean found/path/version, elan, lake, pantograph, env-file path, daemon running/pid, socket path. Comprehensive. | — | — |
| E2 | Match real world | 4 | Field names match tool names. Good. | — | — |
| E3 | Consistency | 3 | PITCH §Architecture says "grd lean ping / env" as if they were synonyms. In reality: `ping` = daemon liveness; `env` = toolchain + pantograph + daemon. A first-timer reading the pitch will think `ping` gives the toolchain summary. | M | both |
| E4 | Recognition not recall | 2 | `LeanEnvStatus` has **no `needs_bootstrap` or `ready` boolean**. The user / agent must synthesize readiness from 4–5 fields (`lean_found && lake_found && pantograph_available && env_file_exists`). The `grd-prover` agent instructions include "If env reports 'needs_bootstrap': run the bootstrap skill" — but `compute_env_status` never emits `needs_bootstrap`. Critical agent-onboarding bug. | **C** | math |
| E5 | Error recovery | 3 | When `lean_found=False`, there's no suggested next step in the output — the user sees `lean_found: false` and has to infer "oh, run bootstrap." | M | phys |
| E6 | Help / docs | 4 | `--help` is a one-liner: "Show detected Lean toolchain, env file status, and daemon state." Priya won't know what "daemon state" means. | m | phys |

### 3.3 `grd lean ping`

| # | Heuristic | Score | Finding | Severity | Persona |
|---|---|---|---|---|---|
| P1 | Naming / match | 2 | `ping` suggests "is the service up?" — but users conflate "Lean up" with "daemon up." This command checks *only* the socket daemon. If the daemon isn't running, Priya sees `{"ok": false, "alive": false}` and concludes Lean is broken, when in fact the next `grd lean check` will auto-spawn a daemon. False-alarm class friction. | M | phys |
| P2 | Minimalist | 5 | One-line JSON output. Good. | — | — |
| P3 | Help / docs | 3 | Help line says "daemon is alive on this project's socket" — doesn't say "you don't normally need to call this; `grd lean check` auto-spawns." | m | both |

### 3.4 `grd lean check` (inline / file / stdin)

| # | Heuristic | Score | Finding | Severity | Persona |
|---|---|---|---|---|---|
| C1 | Status visibility | 4 | `LeanCheckResult` carries `ok`, `diagnostics[]`, `stdout`, `stderr`, `exit_code`, `elapsed_ms`, `error`, `error_detail`, `backend`. Mina sees what backend actually ran. Good. | — | — |
| C2 | Match real world | 3 | Mina expects to paste `theorem foo : 1 + 1 = 2 := by norm_num` and be done. She'll get `ok: true`. Priya has no idea what syntax to type. The help string says "inline Lean 4 source" with no example. | M | phys |
| C3 | User control | 5 | Three input modes (inline / `--file` / stdin) — flexible. `--no-daemon` / `--no-spawn` for debugging. | — | — |
| C4 | Consistency | 3 | `--import` (repeatable, adds `import <module>` lines) is clean. But: no `--import-mathlib` shortcut despite Mathlib being the overwhelmingly common case. | m | math |
| C5 | Error prevention | 4 | Mutual exclusion check: "Pass only one of inline code or --file, not both." Good. | — | — |
| C6 | Efficiency | 3 | Timeout default 30s. For a cold daemon on a fresh project doing first Mathlib elaboration, ~15s is typical — but a mistakenly-deferred `--with-mathlib-cache` makes the first Mathlib import take several minutes and blow the timeout. The error will be `"timeout"` which does not hint "try `lake exe cache get`." | M | both |
| C7 | Recognition | 3 | Priya does not know that imports live under `Mathlib.Tactic`, `Mathlib.Analysis.Calculus.Deriv.Basic`, etc. There is no `grd lean search <name>` or `grd lean imports-for <concept>` discovery surface. | M | phys |
| C8 | Error recovery | 3 | `LeanDiagnostic` passes Lean's raw message through. For Mina this is correct. For Priya, `error: typeclass instance problem is stuck, it is often due to metavariables` is untranslatable. There's no "translate Lean jargon" layer. | M | phys |
| C9 | Help / docs | 4 | `--help` is rich. No example block, though. | m | phys |
| C10 | Backend leakage | 3 | `backend: subprocess|daemon|pantograph` leaks into every result. Useful for Mina debugging daemon issues; noise for Priya who just wants to know if the theorem checks. | m | phys |

### 3.5 `grd lean typecheck-file`

| # | Heuristic | Score | Finding | Severity | Persona |
|---|---|---|---|---|---|
| TF1 | Consistency | 2 | Docstring says "alias for `check --file`." Having both commands dilutes discoverability: Mina has to guess which to use. Either drop it or make `check --file` a section in the help of `typecheck-file` (or vice versa). | M | math |
| TF2 | Efficiency | 4 | Timeout default 60s (double `check`'s 30s). Reasonable for whole-file. | — | — |
| TF3 | Aesthetic | 4 | OK. | — | — |

### 3.6 `grd lean prove`

| # | Heuristic | Score | Finding | Severity | Persona |
|---|---|---|---|---|---|
| PR1 | Status visibility | 4 | `ProveResult` exposes every `ProofAttempt` with tactic, ok, elapsed_ms, error_summary. Excellent for Mina's debugging loop. | — | — |
| PR2 | Match real world | 3 | Docstring lists the fixed ladder: `rfl, decide, norm_num, ring, linarith, omega, simp, aesop`. Mina expects also `polyrith, nlinarith, positivity, field_simp, push_neg, gcongr` — and notices `grd-prover.md` line 121 advertises `polyrith` in the ladder, but `DEFAULT_TACTIC_LADDER` in `prove.py` does NOT include it. **Doc drift.** | **C** | math |
| PR3 | User control | 4 | `--tactic` is repeatable and overrides the ladder. Good. | — | — |
| PR4 | Error prevention | 3 | A bare proposition like `1 + 1 = 2` gets wrapped as `example : 1 + 1 = 2 := by <tactic>`. Fine for Mina. Priya tries `F = m * a` and gets "unknown identifier 'F'" — she doesn't know she needs to declare the variables or use Mathlib's names. No "open issues with your statement" diagnostic. | M | phys |
| PR5 | Efficiency | 3 | No caching: a second identical `prove` invocation re-runs the whole ladder. For a mathematician doing TDD on a proof, this adds latency. | m | math |
| PR6 | Recognition | 2 | Priya has no idea which tactic names are Lean 4 vs Lean 3 vs something she'll have to learn. Help does not link to Mathlib's tactic index. | M | phys |
| PR7 | Minimalist | 4 | Output is compact. JSON mode is clean. | — | — |
| PR8 | Error recovery | 3 | On failure, the user gets the residual goal (great) but **no "try this" suggestion** — e.g., "all 8 tactics failed; the goal involves exponents — consider `nlinarith` or extracting a helper lemma." The `grd-prover` agent exists to do this but *the CLI alone gives the user nothing*. | M | both |
| PR9 | AI-assisted proving | 2 | PITCH Phase 3 promises LeanDojo-style premise retrieval, APOLLO repair loop, N=16 candidate generation. None of that is in `prove.py` today — it's the tactic-ladder MVP. Mina who read the pitch will be surprised when `grd lean prove` fails on a medium-difficulty inequality she expected AI to attempt. Needs `--help` epilogue: "tactic ladder only; AI-assisted proving lands in Phase 3." | **C** | math |
| PR10 | Help / docs | 4 | `--help` is accurate about what it *does* do. | — | — |

### 3.7 `grd lean verify-claim`

| # | Heuristic | Score | Finding | Severity | Persona |
|---|---|---|---|---|---|
| VC1 | Status visibility | 4 | `VerifyClaimResult` serializes the whole 6-stage trace: extract → retrieve → generate → compile-repair → faithfulness → decide. Excellent for audit. | — | — |
| VC2 | Match real world | 3 | Claim string free-form (no grammar constraints). Priya types `energy is conserved in closed systems` — will the extractor parse "closed system" as a predicate? Not documented. The extract stage fails silently on vague input and emits a low-similarity result that escalates — Priya will not understand *why* the bead was filed. | M | phys |
| VC3 | User control | 4 | `--physics` / `--no-physics` override. `--import`. `--no-llm` dry-run. `--timeout`. All useful. | — | — |
| VC4 | Consistency | 3 | `--physics` auto-detection is undocumented in `--help` — Priya has no idea what triggers "physics mode." Does it look at file extension? Phase metadata? The word "derivative" in the claim? | M | phys |
| VC5 | Error prevention | 3 | Mutual exclusion `--physics` vs `--no-physics` enforced. Good. But: no check that `ANTHROPIC_API_KEY` is set until the LLM call fails mid-pipeline. Should fail fast before stage 1 consumes compute. | M | both |
| VC6 | Efficiency | 3 | Per-compile timeout applied across stages 3–4; one timeout may need to be longer than another. Currently one value. | m | math |
| VC7 | Recognition | 3 | Escalation bead title is auto-generated from the similarity reason string. Mina sees `"similarity 0.71 in ambiguous band; cluster of 1"` in her queue and has to open the bead to understand the actual ambiguity. The title should surface the *nature* of the ambiguity (e.g., "autoformalize-claim: quantifier scope uncertain — p→1 vs 1→p") — which is promised in AUTOFORMALIZATION §8.4 but not implemented in `escalate.py` based on what I saw. | **C** | math |
| VC8 | Minimalist | 3 | Output is a full serialization of the result dataclass. For the human reading the terminal that's overwhelming; Priya needs a 3-line summary. JSON-first output without a pretty printer is a cost paid in every human-facing command. | M | phys |
| VC9 | Error recovery | 3 | On ESCALATE, the bead is filed via `bd create -l human`. If `bd` is missing from `PATH`, `BeadEscalationResult(attempted=False, error="bd CLI not found...")` is returned — but the CLI still exits 1 and the user sees `outcome=escalate` with no bead. Priya will be confused: "did it escalate or not?" The CLI output needs a prominent warning block when escalation is requested but not actually filed. | **C** | both |
| VC10 | `--no-llm` stub | 2 | Dry-run emits `theorem autoformalize_dry_run : True := sorry` as every candidate. The pipeline then reports low similarity → escalate. This is correct for plumbing tests but **completely opaque to a first-timer** who passes `--no-llm` hoping to see what the flow *looks like* without paying for API calls. Should print a prominent "DRY RUN MODE — stub candidates; no real inference happened" banner. | M | phys |

### 3.8 `grd lean serve-repl` / `stop-repl`

| # | Heuristic | Score | Finding | Severity | Persona |
|---|---|---|---|---|---|
| D1 | Visibility | 4 | Explicit docstring: "Normally users don't invoke this directly — the client auto-spawns a daemon on the first `grd lean check`. Exposed for debugging and for integration tests." Great disclaimer. | — | — |
| D2 | Consistency | 4 | Naming pair is symmetric and conventional. | — | — |
| D3 | Error recovery | 3 | `stop-repl` with no daemon running: what happens? Help doesn't say. | m | math |

### 3.9 Blueprint Methodology Integration

| # | Heuristic | Score | Finding | Severity | Persona |
|---|---|---|---|---|---|
| BP1 | Discoverability | 1 | **PITCH §Blueprint promises** `/grd:init-blueprint`, `/grd:blueprint-status`, and `grd lean blueprint-status` CLI. NONE of these exist today — verified via `grep` on `src/grd/commands/` and inspection of `src/grd/cli/lean.py`. A mathematician following the pitch cannot initialize a blueprint. | **C** | math |
| BP2 | Match real world | 4 | PITCH maps leanblueprint concepts (`\lemma`, `\uses`, `\leanok`) to GRD concepts (phase claim, `depends_on[]`, check 5.21) — conceptually clean. | — | math |
| BP3 | Help / docs | 2 | There is no help page that says "blueprint is not yet implemented" — Mina will go looking and bounce between PITCH, source tree, and search for 20+ minutes. | **C** | math |

### 3.10 `grd-prover` agent

| # | Heuristic | Score | Finding | Severity | Persona |
|---|---|---|---|---|---|
| AG1 | Discoverability | 2 | Mina / Priya would not know the agent exists. There is no `/grd:prove` skill that spawns it, no `grd lean agent` CLI, nothing in `--help`. It's only reachable from within `execute-phase` orchestration or through someone having read the agent registry. | M | both |
| AG2 | Match real world | 4 | Agent docstring is well-written and surfaces the triage policy + failure mode taxonomy. If you find it. | — | — |
| AG3 | Consistency | 2 | Agent workflow step 1 says "If env reports 'needs_bootstrap': run the bootstrap skill." But `compute_env_status` never emits that key (see E4). Agent will either never bootstrap or always bootstrap depending on how the shell code is written. **Latent bug.** | **C** | math |
| AG4 | Recognition | 3 | Agent triage "Strong / Weak / Reject" is subjective — no automated pre-flight that tells a user "your claim is in the 'reject' category before you spend compute on it." | m | math |

---

## 4. Top 10 Issues, Ranked

Phase targets reference the PITCH "Implementation Phases" (Phase 1 Foundation, Phase 2 Blueprint, Phase 3 AI Proving, Phase 4 Domain Packs/Polish).

| # | Issue | Severity | Phase | One-line fix direction |
|---|---|---|---|---|
| 1 | **Promised skills don't exist.** Only `/grd:lean-bootstrap` ships. Missing: `/grd:prove`, `/grd:formalize-claim`, `/grd:blueprint-status`, `/grd:init-blueprint`, `/grd:lean-check`. (B4, BP1) | **C** | 2 / 3 | Either implement minimal skill bodies that call the CLI, OR add a "not yet implemented" stub skill so the autocomplete discoverability path lands somewhere. |
| 2 | **`LeanEnvStatus` has no `needs_bootstrap` / `ready` boolean.** `grd-prover` agent references it but it does not exist. (E4, AG3) | **C** | 1 | Add `ready: bool` + `blocked_by: list[str]` to `LeanEnvStatus`, computed in `compute_env_status`. Update `grd-prover.md` once shipped. |
| 3 | **Tactic-ladder doc drift between `grd-prover.md` (lists `polyrith`) and `prove.py` (does not).** (PR2) | **C** | 1 | Single source of truth: expose `DEFAULT_TACTIC_LADDER` in `grd lean prove --list-tactics` and reference it from the agent. |
| 4 | **`verify-claim` escalation bead title is uninformative.** Says "similarity X in ambiguous band" instead of the *nature* of the ambiguity. AUTOFORMALIZATION §8.4 explicitly promises the opposite. (VC7) | **C** | 3 | Compose bead title from top-ranked cluster's semantic-difference analysis (quantifier-scope, missing-hypothesis, convention-drift). |
| 5 | **`verify-claim` silent-failure on missing `bd`.** When escalation can't be filed, the CLI still exits 1 with `outcome=escalate`. User has no bead and no clear warning. (VC9) | **C** | 3 | Promote `BeadEscalationResult.attempted=False` to a top-level warning in the human-facing output and a distinct `outcome=escalate_unfiled` in JSON. |
| 6 | **Blueprint methodology undiscoverable.** Pitch says `init-blueprint`, `blueprint-status` exist; they don't. No "coming soon" signpost. (BP1, BP3) | **C** | 2 | Stub `grd lean blueprint-status` with an error that names the bead tracking Phase 2 progress. |
| 7 | **AI-assisted proving surface mismatched with pitch expectations.** `grd lean prove` is tactic-ladder-only but the pitch promises LeanDojo retrieval + APOLLO repair + N=16 candidates. (PR9) | M | 3 | Add `--help` epilogue clarifying MVP scope and link to Phase 3 tracking bead (ge-bat). |
| 8 | **Physics auto-detection in `verify-claim` is opaque.** Priya has no way to know what triggers `--physics`. (VC4) | M | 3 | Document auto-detection heuristic in help; add `--explain-physics` dry-mode flag that logs the decision. |
| 9 | **`grd lean env` / `grd lean ping` naming confusion.** PITCH treats them as aliases; they are distinct. `ping` is misleading for first-timers. (E3, P1) | M | 1 | Rename `ping` → `daemon-status` or fold it into `env --daemon-only`. Remove "ping / env" language from PITCH. |
| 10 | **`typecheck-file` is a pure alias for `check --file`.** Discoverability tax. (TF1) | m | 1 | Deprecate `typecheck-file` with a one-line notice, or merge the two help pages. |

**Borderline #11** — `--no-llm` dry-run is silently opaque (VC10). Add a banner. 20 minutes of work.

**Borderline #12** — import-Mathlib is onerous. `--with-mathlib` convenience flag on `check`/`prove`/`verify-claim` would save typing. Easy win for Mina.

---

## 5. Surprising Quotes (from the personas' POV)

These are the moments that made me, as Claude wearing the persona, pause.

> **Priya, first invocation of `grd lean env`:** "What's a pantograph?"
> *Why surprising*: the output exposes `pantograph_available: false`, which for a physicist reads like "the drafting instrument is missing." The component name is accurate but domain-colliding — physics has the Pantograph Experiment for lepton moments. A short help gloss ("Pantograph: Python ↔ Lean bridge") would fix it.

> **Mina, reading `grd lean prove`'s fixed ladder:** "Where's `polyrith`? Where's `nlinarith`? These are my bread and butter for inequalities."
> *Why surprising*: the `grd-prover.md` agent doc *mentions* `polyrith` in its tactic list (line 121) but the actual `DEFAULT_TACTIC_LADDER` in `prove.py` doesn't include it. Mina will assume bug.

> **Priya, after `grd lean verify-claim 'energy is conserved in closed systems'` fails:** "Why did this file a bead with title `[autoformalize] similarity 0.68 in ambiguous band` — what ambiguity?"
> *Why surprising*: the similarity score is a diagnostic artifact, not a description of the problem. Expecting Priya to reverse-engineer "ambiguous band = candidates disagreed on quantifier order or hypothesis" is a UX failure for the exact audience the escalation flow is supposed to serve.

> **Mina, trying to initialize a blueprint:** "`/grd:init-blueprint` doesn't exist? But the pitch says it does."
> *Why surprising*: the pitch is 500 lines of thoroughly-argued design. Discovering mid-walkthrough that half of it is aspirational requires re-reading with a "what's actually shipped" filter. A `STATUS.md` in `research/formal-proof-integration/` listing which items are merged vs planned would save every future first-timer the same 20 minutes I spent.

> **Priya, reading `grd lean check` help:** "Where is the example?"
> *Why surprising*: every other CLI I've used for a proof system (Coq's `coqc`, Isabelle's `isabelle`, Lean's own `lake build`) prints an example in `--help`. This one doesn't. Mina skips the help and types the obvious thing; Priya stares at it.

> **Mina, reading `grd lean bootstrap --help`:** "Why is `--with-mathlib-cache` separate from `--yes`? Why do I need both?"
> *Why surprising*: the two-flag consent pattern (`--with-X` + `--yes`) is non-obvious — "yes to what?" is the immediate question. Consent is a good design principle; its surface presentation should say "consent required for this 10 GB download: pass `--yes` to accept."

---

## 6. Additional Methodological Notes

- **What I did not test**: live invocation of any `grd lean` command against a real Lean toolchain. The polecat sandbox does not have `grd` on `PATH`, and this audit was read-only per the bead contract. All friction findings above are derived from reading the CLI definitions, error-taxonomy, skill bodies, and agent docs — not from actually running the commands. If a follow-on bead wants empirical timing or real error-message capture, that's a different (integration-test) task.
- **Personas were not consulted.** Mina and Priya are synthetic. The findings reflect my inference about what each type of researcher would trip on. A real user study with, say, 3 mathematicians and 3 physicists would surface issues I missed — particularly in the "mental model of how Lean errors map to fixable actions" zone.
- **Scope boundary**: I did not audit `/grd:lean-bootstrap`'s install logic for correctness (the bootstrap integration tests live elsewhere). I only audited its UX.
- **What I'd prioritize next for this study**: capture real-world latency of first `grd lean check` on a cold project (bootstrap → Mathlib cache → first `norm_num`). That's the one-shot experience that shapes whether a new user abandons after 90 seconds or sticks around.

---

## 7. Handoff

- Parent bead: **ge-7ah** (Lean UX design study)
- Child A (this walkthrough): **ge-0b5** — to be closed after this report merges
- Sibling child B: the complementary walkthrough from the other persona angle (see parent bead for scope)
- Top-10 issues should be filed as `discovered-from: ge-0b5` children of **ge-plk** (the formal-proof-integration epic) so they land on the Phase 1–4 schedule.

For any of the "C" severity items where the fix is not obvious from this doc, leave a comment on the filed child bead and tag **getresearch/crew/bob**.
