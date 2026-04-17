# GRD / GPD Divergence Log

GRD (Get Research Done) is a fork of
[GPD (Get Physics Done)](https://github.com/psi-oss/get-physics-done).
This document lists **intentional** differences so that future upstream
merges can preserve them.

Last reconciled: 2026-04-15 (857 upstream commits merged).

---

## 1. Namespace rename: `gpd` -> `grd`

| Surface | GPD | GRD |
|---------|-----|-----|
| Python package | `src/gpd/` | `src/grd/` |
| Imports | `from gpd.*` | `from grd.*` |
| CLI binary | `gpd` | `grd` |
| Metadata dir | `.gpd` | `.grd` |
| Env vars | `ENV_GPD_*` | `ENV_GRD_*` |
| Package name | `get-physics-done` | `get-research-done` |
| Display name | "Get Physics Done" | "Get Research Done" |

All renames are mechanical (`s/gpd/grd/g`, `s/GPD/GRD/g`) except where
domain-specific language differs (see below).

## 2. Domain framing: research vs physics

GRD generalises GPD's physics-specific framing to domain-agnostic research:

- `src/grd/domains/` includes economics, machine-learning, mech-interp,
  philosophy-of-math, and physics (upstream: physics only).
- Constants use `RESEARCH_SUFFIX` (`-RESEARCH.md`), `RESEARCH_MAP_DIR_NAME`
  (`research-map`).
- Paper models use "Generated with Get Research Done" footer.

## 3. Lean 4 / formal proof integration (GRD-only)

Entirely absent from upstream. Key additions:

- **`src/grd/core/lean/`** -- protocol types, subprocess backend, Unix-socket
  daemon, Pantograph backend, tactic-search prover, diagnostic hints,
  verification-evidence bridge, autoformalization pipeline (6-stage).
- **`src/grd/cli/lean.py`** -- `grd lean` subcommands: `check`, `prove`,
  `verify-claim`, `blueprint-status`, `typecheck-file`, `serve-repl`,
  `stop-repl`.
- **`src/grd/agents/grd-prover.md`** -- prover agent definition.
- **`src/grd/agents/grd-check-proof.md`** -- proof-checking agent.
- **Stub skills** (planned, not yet implemented):
  `lean-check`, `init-blueprint`, `blueprint-status`, `formalize-claim`, `prove`.
- **`research/formal-proof-integration/`** -- PITCH.md, STATUS.md, UX study.

## 4. Circular-import guard in adapters

`src/grd/adapters/__init__.py` guards the `RuntimeAdapter` import behind
`TYPE_CHECKING` and provides a `__getattr__` lazy accessor. Upstream does a
top-level `from gpd.adapters.base import RuntimeAdapter`. The lazy pattern is
necessary in GRD because the import chain
`registry -> command_labels -> adapters.__init__ -> adapters.base -> registry`
would otherwise cycle.

Similarly, `src/grd/registry.py` lazy-imports `expand_at_includes` inside
`_inline_model_visible_includes()` instead of at module level.

## 5. `--json` global alias

GRD adds `--json` as a primary alias for the `--raw` flag across the CLI.
Both `--json` and `--raw` are hoisted by `_split_global_cli_options` so they
work in any argv position. Upstream only has `--raw`.

## 6. Repository metadata

- `pyproject.toml`: name, description, homepage point to GRD.
- `CITATION.cff`: references upstream GPD as inspiration.
- `bin/install.js`: uses `grdHomeDir` / `grdHome` (upstream: `gpdHomeDir`).

---

## Merge strategy

When merging upstream:

1. Apply `s/gpd/grd/g` and `s/GPD/GRD/g` to incoming code.
2. Preserve items 3-5 above -- they are GRD-only additions with no upstream
   counterpart.
3. Watch for new top-level imports in `adapters/__init__.py` or `registry.py`
   that may re-introduce circular imports; use lazy/TYPE_CHECKING patterns.
4. Run `python -m compileall src/grd/ tests/ -q` to catch syntax from
   conflict resolution before committing.
