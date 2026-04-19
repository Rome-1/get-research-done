# Formal-Proof Integration — Status

**Last updated:** 2026-04-17 (bead ge-2zu)
**Pitch:** [PITCH.md](./PITCH.md)
**Epic:** ge-wisp-rnf6 (mol-polecat-work)

This page reconciles every `/grd:*` skill and `grd lean …` CLI command that PITCH.md
promises against what actually exists in the codebase today. If a user types a
slash command from PITCH and hits a 404, this table is wrong — fix it.

Legend:

- **shipped** — code + tests in main, routable from the CLI or skill registry.
- **planned** — landing pad exists (stub skill or tracking bead), not yet functional.
- **n/a** — not net-new; PITCH.md references an existing GRD surface or a future-only item.

---

## `/grd:*` skills

| Skill | Status | Phase | Landing |
|---|---|---|---|
| `/grd:lean-bootstrap` | shipped | 1 | [`src/grd/commands/lean-bootstrap.md`](../../src/grd/commands/lean-bootstrap.md) |
| `/grd:lean-check` | planned | 1 | [`src/grd/commands/lean-check.md`](../../src/grd/commands/lean-check.md) (stub) |
| `/grd:init-blueprint` | shipped | 2 | [`src/grd/commands/init-blueprint.md`](../../src/grd/commands/init-blueprint.md) |
| `/grd:blueprint-status` | shipped | 2 | [`src/grd/commands/blueprint-status.md`](../../src/grd/commands/blueprint-status.md) |
| `/grd:formalize-claim` | planned | 3 | [`src/grd/commands/formalize-claim.md`](../../src/grd/commands/formalize-claim.md) (stub) |
| `/grd:prove` | planned | 3 | [`src/grd/commands/prove.md`](../../src/grd/commands/prove.md) (stub) |
| `/grd:plan-phase` | n/a | — | existing GRD skill; reused by the formal-proof workflow. |
| `/grd:execute-phase` | n/a | — | existing GRD skill; reused by the formal-proof workflow. |
| `/grd:verify-work` | n/a | — | existing GRD skill; integration via checks 5.20 / 5.21. |
| `/grd:progress` | n/a | — | existing GRD skill; formal coverage surfaced inside. |

Each planned stub exists so `/grd:` autocomplete lands on an explanatory page
instead of 404-ing. Bodies point back to this file and to the tracking bead for
the phase that will ship them.

## `grd lean …` CLI subcommands

| Command | Status | Phase | Evidence |
|---|---|---|---|
| `grd lean check` | shipped | 1 | `src/grd/cli/lean.py` (`@lean_app.command("check")`) |
| `grd lean typecheck-file` | shipped | 1 | `src/grd/cli/lean.py` (`@lean_app.command("typecheck-file")`) |
| `grd lean serve-repl` | shipped | 1 | `src/grd/cli/lean.py` (`@lean_app.command("serve-repl")`) |
| `grd lean stop-repl` | shipped | 1 | `src/grd/cli/lean.py` (`@lean_app.command("stop-repl")`) |
| `grd lean bootstrap` | shipped | 1 | `src/grd/cli/lean.py` (`@lean_app.command("bootstrap")`) |
| `grd lean env` | shipped | 1 | `src/grd/cli/lean.py` (`@lean_app.command("env")`) — not in PITCH, surfaced by bootstrap work. |
| `grd lean ping` | shipped | 1 | `src/grd/cli/lean.py` (`@lean_app.command("ping")`) — not in PITCH, daemon health check. |
| `grd lean prove` | shipped | 3 | `src/grd/cli/lean.py` (`@lean_app.command("prove")`) |
| `grd lean verify-claim` | shipped | 3 | `src/grd/cli/lean.py` (`@lean_app.command("verify-claim")`); drives the 6-stage autoformalization pipeline. |
| `grd lean init-blueprint` | shipped | 2 | `src/grd/cli/lean.py` (`@lean_app.command("init-blueprint")`) |
| `grd lean blueprint-status` | shipped | 2 | `src/grd/cli/lean.py` (`@lean_app.command("blueprint-status")`) |
| `grd lean sync` | planned | 3 | Rebuilds grounded retrieval index against pinned Mathlib4 + PhysLean snapshot (PITCH §Phase 3 §3.2). |

### JSON-output flag

All `grd` subcommands accept `--json` (canonical) or `--raw` (legacy alias)
as a global flag for machine-readable output. Both are hoisted to the root
parser regardless of position, so `grd lean check '...' --json` and
`grd --json lean check '...'` behave identically. Prefer `--json` in new
documentation — `--raw` is kept for backwards compatibility with existing
skill bodies and agent plumbing. Wired in `src/grd/cli/_helpers.py`
(`@app.callback` + `_split_global_cli_options`).

### JSON schema: goal-state fields (ge-2zu)

As of ge-2zu, the following goal-state fields are present in CLI JSON output:

- **`LeanCheckResult`** (wire format): `goals_before: list[str] | null`, `goals_after: list[str] | null`
- **`ProofAttempt`** (prove output): `goal_before: str | null`, `goal_after: list[str] | null`
- **`VerifyClaimResult`** (verify-claim output): `chosen_goals: list[str] | null`
- **`RepairOutcome`** (repair trace): `goals_after: list[str] | null`

Semantics: `[]` = all goals closed (success), `null` = goal state unavailable
(syntax error, non-tactic mode), `["⊢ …", …]` = unsolved goals remain.
Human-readable CLI uses `--show-goal` to display goals below diagnostics.

## Agents

| Agent | Status | Landing |
|---|---|---|
| `grd-prover` | shipped | [`src/grd/agents/grd-prover.md`](../../src/grd/agents/grd-prover.md) |

## Verification checks

| Check | Status | Landing |
|---|---|---|
| 5.20 `universal.formal_statement` | shipped | `src/grd/core/verification_checks.py:283` |
| 5.21 `universal.formal_proof` | shipped | `src/grd/core/verification_checks.py:304` |

## Autoformalization pipeline (PITCH §Phase 3)

| Stage | Status |
|---|---|
| 1. Extract (claim + conventions + deps from phase artifacts) | shipped |
| 2. Retrieve (grounded against pinned Mathlib4 + PhysLean snapshot) | shipped |
| 3. Generate (N candidate Lean statements, DRAFT-SKETCH-PROVE) | shipped |
| 4. Compile-repair (APOLLO-style loop) | shipped |
| 5. Faithfulness (back-translate, SBERT sim, symbolic-equiv cluster) | shipped |
| 6. Gate (auto-accept / cluster / escalate via `bd new -l human`) | shipped |

Wiring lives under `src/grd/core/lean/autoformalize/`. Pantograph REPL reuse
via the per-project Unix socket is in `src/grd/core/lean/daemon.py`.

## Phase-level surfaces (not yet landed)

| Item | Status | Phase |
|---|---|---|
| `blueprint/` phase artifact directory (`content.tex`, `lakefile.lean`, `Proofs/`, `Blueprint.lean`) | shipped | 2 |
| Convention bridge — Lean type classes generated from the 18-field convention lock | planned | 2 |
| `formal-verification` domain pack | planned | 4 |
| Kimina Lean Server batch backend | planned | 4 |
| Multi-backend (Coq, Isabelle) | planned | 5 |

## Beads

| Bead | Scope |
|---|---|
| ge-plk | PITCH proposal (parent) |
| ge-wisp-rnf6 | Molecule epic (mol-polecat-work) |
| ge-48t | 6-stage autoformalization pipeline + `verify-claim` CLI |
| ge-nsd | Pantograph REPL reuse inside Lean daemon |
| ge-wbs | Formal-proof coverage metrics |
| ge-d8s | `grd-prover` agent definition |
| ge-nub | This status page + planned-skill stubs |
| ge-8g5 | Blueprint MVP — init-blueprint + blueprint-status with auto-leanok |
| ge-cch | Running list of upstream tooling friction (Leanblueprint, Pantograph, LeanDojo, Kimina) |
| ge-h0j | Testing strategy / test matrix |

## Keeping this honest

When you ship a planned item:

1. Remove its stub skill file (if any).
2. Move its row from **planned** to **shipped** and link the landing file or CLI command.
3. Bump the "Last updated" date and attach the bead id.

When you find a `/grd:*` invocation in PITCH that isn't on this page, add it —
otherwise the doc-truth gap re-opens.
