---
name: grd:blueprint-status
description: "Planned (Phase 2) — show blueprint dependency graph and formalization progress. See research/formal-proof-integration/STATUS.md."
argument-hint: "[--phase N] [--svg] [--json]"
context_mode: project-required
requires:
  files: [".grd/PROJECT.md"]
allowed-tools:
  - file_read
  - shell
---

<objective>
**This skill is not implemented yet.** It is a planned Phase 2 landing pad so
that `/grd:` autocomplete finds an explanatory page instead of a 404.

When shipped, `/grd:blueprint-status` will render the blueprint dependency
graph for the current (or specified) phase, colour-coded by formalization
status:

| Node colour | Meaning |
|---|---|
| green  | `\leanok` — formal proof typechecks (check 5.21 passed) |
| yellow | statement formalized (check 5.20 passed), proof outstanding |
| grey   | informal only — no Lean counterpart yet |
| red    | proof attempt failed (compile-repair loop exhausted) |

Default output is an ASCII DAG (no graphviz required). `--svg` invokes
graphviz if available (falls back to ASCII with a note, per the bootstrap
non-blocking policy). `--json` emits the full node/edge list for agents and
downstream tooling.

Thin wrapper around `grd lean blueprint-status` (planned CLI, Phase 2).
</objective>

<status>
- **Phase:** 2 (Blueprint Integration) — see
  [PITCH §Phase 2](../../../research/formal-proof-integration/PITCH.md#phase-2-blueprint-integration-3-4-weeks).
- **Depends on:** `/grd:init-blueprint` scaffolding; Leanblueprint Python
  dependency; the `grd lean blueprint-status` CLI command (planned).
- **Tracking bead:** file a new bead under ge-wisp-rnf6 when work starts.

See [STATUS.md](../../../research/formal-proof-integration/STATUS.md) for
the shipped/planned matrix.
</status>

<fallback>
Formal-proof coverage at the check level (5.20 / 5.21) already lands in
`/grd:progress` once `ge-wbs` metrics are populated. Run that for a
phase-level number today; the dependency graph is what this skill will add
once blueprints exist.
</fallback>
