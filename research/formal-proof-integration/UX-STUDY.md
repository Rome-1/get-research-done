# UX Study: Lean Integration for Math / Physics Users

**Parent bead:** ge-7ah
**Source handoff:** hq-n6j17 (bob → bob, 2026-04-14)
**Scope:** UI/UX analysis of the shipped `grd lean` surface (Phases 1–4 of ge-plk, commits 8f369df..2e1c1fb on `main`).
**Method:** three parallel polecats — one Claude heuristic walkthrough, one Codex code-level audit, one external user research pass — synthesized here.

Sub-artifacts (read these for detail):
- [`ux-study/walkthrough-claude.md`](ux-study/walkthrough-claude.md) — polecat `rust` (Claude Opus 4.6). Persona-driven (mathematician Mina, physicist Priya). Nielsen-10 scored per subcommand. 10 prioritized issues with severity tags.
- [`ux-study/audit-codex.md`](ux-study/audit-codex.md) — polecat `chrome` (OpenAI Codex, gpt-5.4). Alternate-runtime read of `src/grd/cli/lean.py`, `src/grd/core/lean/**`, `src/grd/agents/grd-prover.md`. File:line-referenced table across 10 audit dimensions.
- [`ux-study/external-research.md`](ux-study/external-research.md) — polecat `nitro` (Claude Opus 4.6). 63 sources across Mathlib, LeanDojo, Blueprint, PhysLean, Sledgehammer/Isabelle, outsider reviews. Persona time budgets + 10 feature proposals.

---

## 1. Headline Finding

**The shipped surface works — for an expert agent that already knows the schema.** For a human mathematician or physicist coming in cold, the gap between the pitch (`research/formal-proof-integration/PITCH.md`) and what actually ships is the single largest source of friction, followed by error-message opacity, then missing discovery scaffolding.

Quantitatively: three categories account for 23 of the 30 issues surfaced by the polecats.

| Category | % of flagged issues | Primary source |
|---|---|---|
| Doc / implementation drift | 37% | rust + chrome converged |
| Error surface opacity | 33% | rust + chrome + nitro converged |
| Missing discovery scaffolding | 23% | rust + nitro converged |
| Implementation quality (daemon, idempotency) | 7% | chrome only |

All three polecats independently flagged the *same* top class of issue as P0: the `grd lean` CLI exists, but the user cannot tell what is real vs aspirational, and the errors it emits do not tell the user what to do next.

---

## 2. What All Three Agreed On

These are the issues that appear in ≥2 polecat reports and are therefore least likely to be an artifact of any single reviewer's perspective:

1. **Skills promised, skills missing.** PITCH §Blueprint promises `/grd:prove`, `/grd:formalize-claim`, `/grd:blueprint-status`, `/grd:init-blueprint`, `/grd:lean-check`. Only `/grd:lean-bootstrap` ships. `grd-prover.md` references `--json` flags that don't exist (it's global `--raw`). *(rust B4 / BP1 + chrome dimension 3 + 7 + nitro Q10 #1, #3)*
2. **Errors leak as tracebacks or raw Lean diagnostics.** The core `LeanCheckResult` schema is rich, but the CLI surfaces it by dumping the dataclass; unexpected exceptions in `verify-claim`/`bootstrap`/daemon become Python tracebacks (chrome dimension 1). New users see `failed to synthesize instance` with no hint (rust C8 + nitro Q9). *(rust C8 + chrome dimension 1 + nitro Q9, proposed fix #1)*
3. **`LeanEnvStatus` has no `ready` / `needs_bootstrap` signal.** `grd-prover.md` tells the agent to branch on `needs_bootstrap`; `compute_env_status` never emits it. `env` reports daemon state by pid+socket, not by responsiveness (rust E4 + AG3 + chrome dimension 9). *(rust E4 + chrome dimension 9)*
4. **verify-claim escalation is under-specified.** Escalation bead titles say "similarity 0.71 in ambiguous band" instead of the *nature* of the ambiguity; when `bd` is missing, outcome=escalate but no bead is filed. Rejection rationale is a scalar similarity, not a structured diff of quantifiers / hypotheses / convention terms (rust VC7 + VC9 + chrome dimension 8 + nitro anti-pattern #1).

The three independent vantage points disagree on emphasis but converge on the diagnosis. That convergence is the strongest signal in the study.

---

## 3. Prioritized Improvements

Priorities are **P0** (ship in Phase 1 polish, ≤1 week each), **P1** (Phase 2–3 proper, ~2–4 weeks each), **P2** (Phase 3–4 stretch, >1 month each). Phase targets reference PITCH §Implementation Phases. Each improvement listed below has a filed bead and a phase target.

### P0 — Phase 1 stabilization (close the pitch-vs-ship gap)

| # | Improvement | Source evidence |
|---|---|---|
| P0-1 | **Error-explanation layer** — Every Lean diagnostic emitted by `grd lean check/prove/verify-claim` gets a one-line `hint` field with human cause + suggested next action. Seed with the top 5 errors from nitro's Q9 (synthInstance, type-mismatch, heartbeats, deep-recursion, universe levels). ~30-entry lookup table covers ~80% of user-visible failures. | nitro feature #1; rust C8, PR8; chrome dim 1, 8 |
| P0-2 | **Doc-truth alignment** — Add `docs/formal-proofs/STATUS.md` listing every pitched `/grd:*` skill and CLI command with a "shipped / planned / n/a" tag, linked from PITCH. Stub the six planned skills with a "coming in Phase N" message so `/grd:` autocomplete lands somewhere. | rust #1, #6 (Mina quote); nitro Q10 #3 |
| P0-3 | **`LeanEnvStatus.ready` + `blocked_by[]`** — Single boolean + list of missing components. grd-prover.md updated to branch on it. Also expose in `grd lean env --check` with a single-line human summary. | rust E4, AG3; chrome dim 9 |
| P0-4 | **`--json` alias for `--raw` OR unify docs** — Agent doc says `--json`; CLI has root `--raw`. Add alias + update `grd-prover.md`. | chrome dim 3, 7 |
| P0-5 | **Command-level exception wrapping for verify-claim / bootstrap / daemon** — No more raw Python tracebacks. Unknown failures become structured `{"ok": false, "error": {...}}` JSON. Typer's `_GRDTyper` currently catches selected internal exceptions only. | chrome dim 1 |
| P0-6 | **Split exit codes** — 0 ok, 1 soft-fail (Lean rejection / faithfulness reject / no-proof-found), 2 user input error, 3 environment/bootstrap failure, 4 daemon/internal error. Shell callers can route by code. Preserve existing JSON detail. | chrome dim 2 |
| P0-7 | **Tactic-ladder single source of truth** — Expose `DEFAULT_TACTIC_LADDER` via `grd lean prove --list-tactics` and reference from `grd-prover.md`. Resolves `polyrith` doc drift. | rust PR2 |
| P0-8 | **Escalation visibility when `bd` is missing** — When `BeadEscalationResult.attempted=False`, promote to a top-level warning block in human-facing output and a distinct `outcome=escalate_unfiled` in JSON. Current silent-fail is a trust-breaker. | rust VC9; chrome dim 8 |

### P1 — Phase 2–3 (new user-facing surface)

| # | Improvement | Source evidence |
|---|---|---|
| P1-1 | **`grd lean stub-claim`** — Natural-language claim → skeleton Lean statement + retrieval hits (Loogle/LeanExplore/Lean Finder). Addresses the single highest-leverage unmet need in the Lean ecosystem per nitro (Tao's 1-hour-per-line week-1 bottleneck). Flows into `verify-claim`. | nitro feature #2 |
| P1-2 | **Blueprint MVP — `grd lean init-blueprint` + `blueprint-status`** — Generate leanblueprint-compatible LaTeX skeleton from the phase task graph. Auto-mark `\leanok` on lemmas whose Lean counterpart typechecks. Closes Tao's explicit manual-sync friction and Buzzard's "Rosetta Stone" framing. | rust #6; nitro feature #3; Tao quote in nitro §Direct Quotes |
| P1-3 | **`grd lean search`** — Dispatching wrapper over Loogle (type-signature queries) + LeanExplore / Lean Finder (NL queries). Surface-disambiguated results with source URLs. Ships as CLI + skill. | nitro feature #4; rust C7 |
| P1-4 | **Stream progress for long-running ops** — Bootstrap stages, prove attempts, verify-claim stages emit JSONL events (`--events jsonl`). Preserve final aggregate JSON. Fixes silent 90s first-import experience. | chrome dim 4; rust C6 |
| P1-5 | **Daemon auto-spawn waits for successful `ping`, not just socket existence** — Plus include daemon startup diagnostics in a readable log path instead of discarding stderr. Closes the flaky "daemon spawned but `check` hangs" class. | chrome dim 9 |
| P1-6 | **Faithfulness rationale structured diff** — Replace similarity scalar with `{changed_quantifiers, changed_domains, missing_hypotheses, changed_convention_terms}`. Use in CLI output AND escalation bead titles/bodies. Promised in AUTOFORMALIZATION §8.4, not yet shipped. | rust VC7; chrome dim 8; nitro anti-pattern #1 |
| P1-7 | **JSON goal-state echo in every Lean operation** — Before/after goal state in the standard result JSON. Users can see what Lean is looking at without opening VS Code LSP. Macbeth's "free your working memory" primitive at the CLI level. | nitro feature #6 |
| P1-8 | **Persona-aware bootstrap — `/grd:lean-bootstrap --for {mathematician,physicist,ml-researcher}`** — Three tailored on-ramp flows. Physicist flow is greenfield (nitro: zero public independent PhysLean users found). | nitro feature #7; rust persona spread |

### P2 — Phase 3–4 (differentiation)

| # | Improvement | Source evidence |
|---|---|---|
| P2-1 | **`grd lean try-prove`** — Sledgehammer-style orchestrator over `exact?`, `apply?`, `aesop`, LeanHammer, `simp_all`, and optional LLM-backed `llmqed`. Parallel runs. Ranked clickable list. Kernel-checked snippets only (no oracle). | nitro feature #5; rust PR9 (pitch-promised AI proving) |
| P2-2 | **Convention bridge preamble generator (ge-tau)** — Generate Lean imports + instances from the GRD convention lock. Today's path only prompt-injects; `grd-prover.md` claims a preamble file. Single biggest agent-claim-vs-code mismatch. | chrome dim 10; rust not surfaced |
| P2-3 | **`grd lean find-counterexample`** — First-class primitive: decide/Plausible/LLM-proposed-values in parallel. Alexeev (Xena, Dec 2025) names this the highest-value AI primitive in research formalization. Aligns with GRD's "limiting cases" heuristic. | nitro feature #9 |
| P2-4 | **Auto-`maxHeartbeats` tuning on timeout** — Rerun with 2× heartbeats to a ceiling; report winning value + suggest `set_option`. Specific, small, heavily-complained-about. | nitro feature #8 |
| P2-5 | **Read-only audit mode** — `--no-daemon --no-spawn --dry-run` preset. Commands are labeled with side effects (filesystem writes, process spawns, bead creation, dependency install). Enables CI use and unprivileged audits. | chrome dim 5 |

### P3 — Aspirational (research bets)

| # | Improvement | Source evidence |
|---|---|---|
| P3-1 | **`grd lean render-proof`** — Isar-style narrative rendering of Lean proofs. As AI-generated proofs dominate 2026+, reviewability of million-line artifacts becomes table stakes. | nitro feature #10 |

---

## 4. What GRD Has Disproportionate Leverage On

Distilling nitro's external research findings against rust's in-surface observations:

1. **Wrappers, not synthesis.** Benchmark numbers saturate; real pipeline accuracy is 30–70 points below headline. Users stall before and after proving, not in it. GRD's leverage: error explanation, informal→stated-theorem assistance, Blueprint-aware search, persona onboarding. Each is a 1–2 week feature with clear demand and no entrenched competitor.
2. **Physics is open territory.** PhysLib has ~540 stars and **zero independent public users** in nitro's record. The June 2025 Padole blog describes being onboarded to PhysLean via a LinkedIn DM from the author. A persona-aware physicist on-ramp is fully greenfield.
3. **Surface the phase graph as a Blueprint dashboard.** GRD already decomposes research into phase tasks with dependency metadata. Rendering it with green/yellow/red proof status would be the most-praised Lean-adjacent UX surface of 2026 (Tao / Buzzard / Massot unanimous on dependency-graph importance).
4. **Local-first AI via Ollama, not Docker.** LLMLean (CMU-L3) is the quiet grassroots success: `require` in lakefile, two tactics, pluggable models, works offline. Anything heavier loses. Inform `grd lean prove`'s future AI modality selection.

---

## 5. What We Did NOT Test

Honest scope limits to flag for any follow-on study:

- **Empirical latency.** No polecat ran a live `grd lean check` cold on a fresh project. First-Mathlib-import time is the abandonment moment; not measured here.
- **Real users.** Mina and Priya are synthetic personas. A 3×3 mathematician/physicist user study would surface friction classes we missed — especially around "how do Lean errors map to fixable actions in your head?"
- **Blueprint methodology end-to-end.** Only reviewed the PITCH promise; did not build a GRD-project Blueprint with actual lemma nodes.
- **Integration health.** ge-h0j (thorough testing matrix) is the right container for empirical correctness. This study is UX, not correctness.

---

## 6. Filed Beads

All 22 improvements are filed with `discovered-from: ge-7ah`. Bead IDs below — run `bd show <id>` for the full brief including file:line evidence, deliverables, and phase targets.

### P0 — Phase 1 stabilization (pick up immediately)

| Bead | Title |
|---|---|
| ge-13w | Error-explanation layer on grd lean check/prove/verify-claim |
| ge-nub | Doc-truth alignment — STATUS.md + stubbed /grd: skills |
| ge-r11 | Add `LeanEnvStatus.ready` and `blocked_by[]`; rewire grd-prover |
| ge-e9l | Align `--json` / `--raw` flag naming across docs and CLI |
| ge-4yl | Command-level exception wrapping for verify-claim / bootstrap / daemon |
| ge-oc0 | Split exit codes — 0 ok / 1 soft / 2 input / 3 env / 4 internal |
| ge-sk4 | Tactic-ladder single source of truth — `--list-tactics` |
| ge-1hr | Escalation visibility when bd is missing — `outcome=escalate_unfiled` |

### P1 — Phase 2–3 (new user-facing surface)

| Bead | Title |
|---|---|
| ge-ln7 | `grd lean stub-claim` — NL claim → skeleton Lean statement |
| ge-8g5 | Blueprint MVP — `init-blueprint` + `blueprint-status` with auto-`\leanok` |
| ge-1r1 | `grd lean search` — wrap Loogle + LeanExplore + Lean Finder |
| ge-coq | Stream progress events for bootstrap / prove / verify-claim |
| ge-f9i | Daemon auto-spawn waits for ping success + readable startup log |
| ge-cla | Faithfulness rationale as structured diff (not scalar similarity) |
| ge-2zu | JSON goal-state echo in every Lean operation |
| ge-5o8 | Persona-aware bootstrap — `--for {math,phys,ml}` |

### P2 — Phase 3–4 (differentiation)

| Bead | Title |
|---|---|
| ge-k8s | `grd lean try-prove` — Sledgehammer-style hammer, kernel-checked |
| ge-j8k | Convention bridge — generate Lean preamble from convention lock (reinforces ge-tau) |
| ge-16j | `grd lean find-counterexample` — first-class primitive |
| ge-l9cz | Automatic `maxHeartbeats` tuning on timeout |
| ge-xvaw | Read-only audit mode — `--audit-mode` + side-effect labels |

### P3 — Aspirational

| Bead | Title |
|---|---|
| ge-epra | `grd lean render-proof` — Isar-style narrative rendering |

---

## 7. Residual

- **Parent bead ge-7ah** closes with this memo. P0–P3 beads remain open for scheduling.
- **Stale hook ge-y3a** (geometry research Phase 2 complete) was set aside to execute this handoff. Revisit after at least the P0 wave ships.
- **Nudge infra bug discovered during this study:** `gt sling` initial startup nudge to Codex polecats can race with Codex TUI init and deliver to a stale tmux window ID. Chrome sat idle for 90 min until manually kicked. Worth filing against gastown infra — not filed here because it's out of scope for getresearch.

---

*End of UX-STUDY.md. For per-polecat detail read the three sub-artifacts in `ux-study/`.*
