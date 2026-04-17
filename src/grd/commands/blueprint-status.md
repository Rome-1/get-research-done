---
name: grd:blueprint-status
description: "Show blueprint dependency graph and formalization progress for a phase."
argument-hint: "<phase> [--no-typecheck] [--svg] [--json]"
context_mode: project-required
requires:
  files: [".grd/PROJECT.md"]
allowed-tools:
  - file_read
  - shell
---

<objective>
Walk a phase's blueprint and report formalization status. Cross-references
each `\lean{...}` in `content.tex` against actual Lean type-checks and
auto-marks `\leanok` for proofs that pass.

Renders the dependency graph colour-coded by status:

| Symbol | Colour | Meaning |
|--------|--------|---------|
| `[OK]` | green  | `\leanok` — formal proof typechecks |
| `[--]` | yellow | statement formalized, proof outstanding |
| `[  ]` | grey   | informal only — no Lean counterpart yet |
| `[!!]` | red    | proof attempt failed |

Default output is an ASCII DAG (no graphviz required). `--svg` invokes
graphviz if available (falls back to ASCII). `--json` emits the full
node/edge list for agents.

The CLI primitive is:

```bash
grd lean blueprint-status <phase> [--no-typecheck] [--svg] [--json]
```
</objective>

<status>
- **Phase:** 2 (Blueprint Integration) — **shipped**.
- See [STATUS.md](../../../research/formal-proof-integration/STATUS.md) for
  the full shipped/planned matrix.
</status>
