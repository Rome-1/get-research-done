---
name: grd:prove
description: "Planned (Phase 3) — attempt a Lean 4 proof of a given statement via tactic search + APOLLO repair. See research/formal-proof-integration/STATUS.md."
argument-hint: "<statement> [--ctx path] [--timeout-s N]"
context_mode: project-aware
allowed-tools:
  - file_read
  - file_write
  - shell
---

<objective>
**This skill is not implemented yet.** It is a planned Phase 3 landing pad so
that `/grd:` autocomplete finds an explanatory page instead of a 404.

When shipped, `/grd:prove <statement>` will attempt to prove a Lean 4
statement, orchestrating:

1. Lean-auto / aesop tactic search (cheap, fast path).
2. LeanDojo-style tactic search with premise retrieval (when
   `--with-leandojo` was enabled at bootstrap).
3. APOLLO-style compile-repair loop (already shipped in
   `src/grd/core/lean/autoformalize/repair.py`) for repairing
   near-miss proofs.
4. Manual construction guided by the informal derivation when the previous
   steps exhaust their budget.

Thin wrapper around the shipped `grd lean prove` CLI, with skill-level
orchestration that retries with premise retrieval and writes successful
proofs back into the phase blueprint.
</objective>

<status>
- **Phase:** 3 (AI-Assisted Proving) — see
  [PITCH §Phase 3](../../../research/formal-proof-integration/PITCH.md#phase-3-ai-assisted-proving-4-6-weeks).
- **Depends on:** blueprint scaffolding from `/grd:init-blueprint` (Phase 2)
  for the "write it back" step; proving itself works standalone today.
- **Tracking bead:** file a new bead under ge-wisp-rnf6 when work starts.

See [STATUS.md](../../../research/formal-proof-integration/STATUS.md) for
the shipped/planned matrix.
</status>

<fallback>
`grd lean prove` is already shipped and callable today:

```bash
grd lean prove '<your statement>' --json
```

It returns the attempted proof (or the tactics tried and time elapsed) as
JSON. That's the same primitive this skill will wrap, so you can get the
proving result today — you just have to wire it into your blueprint by hand.
</fallback>
