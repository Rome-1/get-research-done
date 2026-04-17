---
name: grd:init-blueprint
description: "Scaffold a leanblueprint-compatible blueprint/ directory inside the given phase."
argument-hint: "<phase> [--force]"
context_mode: project-required
requires:
  files: [".grd/PROJECT.md"]
allowed-tools:
  - file_read
  - file_write
  - shell
---

<objective>
Generate a leanblueprint-compatible directory under the specified phase.
Maps GRD plan entries to blueprint nodes (`\begin{lemma}`/`\begin{theorem}`),
plan `depends_on` edges to `\uses{...}`, and creates stub `.lean` proof
files under `Proofs/`.

The output directory is `phases/{N}/blueprint/` with:

```
phases/{N}/
  blueprint/
    content.tex        # Informal statements + \lean{} refs
    lakefile.lean      # Lake project config (pinned toolchain)
    lean-toolchain     # Toolchain version pin
    Proofs/            # Formal proof files go here
    Blueprint.lean     # Module root importing Proofs/
```

The CLI primitive is:

```bash
grd lean init-blueprint <phase> [--force] [--json]
```
</objective>

<status>
- **Phase:** 2 (Blueprint Integration) — **shipped**.
- See [STATUS.md](../../../research/formal-proof-integration/STATUS.md) for
  the full shipped/planned matrix.
</status>
