---
name: grd:init-blueprint
description: "Planned (Phase 2) — scaffold blueprint/ directory inside the current phase. See research/formal-proof-integration/STATUS.md."
argument-hint: "[--phase N] [--force]"
context_mode: project-required
requires:
  files: [".grd/PROJECT.md"]
allowed-tools:
  - file_read
  - file_write
  - shell
---

<objective>
**This skill is not implemented yet.** It is a planned Phase 2 landing pad so
that `/grd:` autocomplete finds an explanatory page instead of a 404.

When shipped, `/grd:init-blueprint` will create the Leanblueprint-compatible
directory under the current phase:

```
phases/{N}/
  blueprint/
    content.tex        # Informal statements + \lean{} refs
    lakefile.lean      # Lake project config (pinned toolchain)
    lean-toolchain     # Toolchain version pin
    Proofs/            # Formal proof files go here
    Blueprint.lean     # Module root importing Proofs/
```

Additionally, it will:

- Pin the Lean toolchain (from `.grd/lean-env.json` written by
  `/grd:lean-bootstrap`).
- Generate a convention preamble Lean file from `state.json` convention
  locks (Convention Bridge, see PITCH §Convention Bridge).
- Register the blueprint directory with the phase's `VERIFICATION.md` so
  checks 5.20 / 5.21 (`universal.formal_statement` / `universal.formal_proof`,
  already shipped) know where to look.
</objective>

<status>
- **Phase:** 2 (Blueprint Integration) — see
  [PITCH §Phase 2](../../../research/formal-proof-integration/PITCH.md#phase-2-blueprint-integration-3-4-weeks).
- **Depends on:** Phase 1 bootstrap shipped; convention-bridge Lean template
  not yet written; Leanblueprint integrated as a Python dependency.
- **Tracking bead:** file a new bead under ge-wisp-rnf6 when work starts.

See [STATUS.md](../../../research/formal-proof-integration/STATUS.md) for
current status across formal-proof skills and CLI commands.
</status>

<fallback>
No CLI fallback ships today. If you need a blueprint right now, follow the
manual scaffold Patrick Massot documents at
<https://github.com/PatrickMassot/leanblueprint> and drop it under
`phases/{N}/blueprint/`. When `/grd:init-blueprint` ships, existing manual
scaffolds will be detected and upgraded, not overwritten.
</fallback>
