---
name: grd:lean-check
description: "Planned (Phase 1) — typecheck all Lean files in the current phase. See research/formal-proof-integration/STATUS.md."
argument-hint: "[--phase N] [--json]"
context_mode: project-aware
allowed-tools:
  - file_read
  - shell
---

<objective>
**This skill is not implemented yet.** It is a planned Phase 1 landing pad so
that `/grd:` autocomplete finds an explanatory page instead of a 404.

When shipped, `/grd:lean-check` will typecheck every Lean file inside the
current phase's `blueprint/` directory (or across all phases with `--all`)
and report which statements elaborate cleanly, which fail, and which have
no proof yet.

Under the hood it calls `grd lean typecheck-file` (already shipped) against
each file in the phase's blueprint. The daemon model in
`src/grd/core/lean/daemon.py` keeps the Pantograph REPL warm between files.
</objective>

<status>
- **Phase:** 1 (Foundation) — see [PITCH §Phase 1](../../../research/formal-proof-integration/PITCH.md#phase-1-foundation-4-6-weeks).
- **Tracking bead:** file a new bead or link from ge-wisp-rnf6 when work starts.
- **Current state:** `grd lean typecheck-file <path>` is already available as a
  CLI (see `src/grd/cli/lean.py`). This skill wraps it phase-wide; writing the
  wrapper is the whole task.
- **Blueprint artifact (Phase 2)** needs to exist before this skill is
  generally useful — without a phase `blueprint/` directory there is nothing
  to iterate over. Until then, call `grd lean typecheck-file <path>` directly.

See [STATUS.md](../../../research/formal-proof-integration/STATUS.md) for the
current shipped/planned matrix across all `/grd:` formal-proof skills and
`grd lean` CLI commands.
</status>

<fallback>
If you landed here because you need to typecheck a single Lean file right now,
use the shipped CLI directly:

```bash
grd lean typecheck-file path/to/File.lean
```

For an ad-hoc snippet:

```bash
grd lean check 'theorem t : 1 + 1 = 2 := by norm_num'
```

Both commands JSON-format with `--json` for agent consumption.
</fallback>
