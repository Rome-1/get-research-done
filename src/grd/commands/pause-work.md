---
name: grd:pause-work
description: Create context handoff when pausing research mid-phase
context_mode: project-required
allowed-tools:
  - file_read
  - file_write
  - shell
---


<objective>
Create the canonical `.continue-here.md` continuation handoff artifact to preserve complete research state across sessions.

Routes to the pause-work workflow which handles:

- Current phase detection from recent files
- Complete state gathering (current derivation state, parameter values, intermediate results, completed work, remaining work, decisions, blockers)
- Canonical continuation handoff artifact creation using the shared continue-here template
- Git commit as WIP
- Return instructions for `grd resume`, `grd resume --recent`, `grd:resume-work`, and `grd:suggest-next` so the recovery ladder stays explicit
  </objective>

<execution_context>
@.grd/STATE.md
@{GRD_INSTALL_DIR}/workflows/pause-work.md
</execution_context>

<process>
**Follow the pause-work workflow** from `@{GRD_INSTALL_DIR}/workflows/pause-work.md`.

The workflow handles all logic including:

1. Phase directory detection
2. State gathering with user clarifications, including:
   - Current position in derivation or calculation
   - Parameter values and assumptions in effect
   - Intermediate results obtained so far
   - Approximations made and their justifications
   - Next steps that were planned before pausing
3. Canonical `.continue-here.md` continuation handoff writing with timestamp and session continuity pointer
4. Git commit
5. Confirmation with `grd resume`, `grd resume --recent`, runtime `grd:resume-work`, and `grd:suggest-next`
   </process>
