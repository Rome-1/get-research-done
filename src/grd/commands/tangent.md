---
name: grd:tangent
description: Choose how to handle a possible side investigation without silently widening scope
argument-hint: "[optional description]"
context_mode: project-required
allowed-tools:
  - file_read
  - file_write
  - file_edit
  - find_files
  - search_files
  - shell
  - task
  - ask_user
---


<objective>
Decide what to do with an unexpected but non-blocking tangent, side investigation, or alternative path.

Use this when GRD or the researcher notices something interesting that may deserve follow-up, but it is not yet clear whether that follow-up should happen now, be deferred, or become a git-backed hypothesis branch.

The tangent chooser is proposal-first. It should not silently widen scope.

Available outcomes:

- Stay on the main path
- Run a bounded quick check now
- Capture and defer as a todo
- Open an explicit hypothesis branch
</objective>

<execution_context>
@GRD/STATE.md
@{GRD_INSTALL_DIR}/workflows/tangent.md
</execution_context>

<inline_guidance>

## Tangent Taxonomy

- `grd:tangent` is the chooser
- `grd:quick` is the bounded side-investigation path
- `grd:add-todo` is the defer-and-continue path
- `grd:branch-hypothesis` is the explicit git-backed alternative path

Use `branch-hypothesis` only after you have explicitly decided the tangent deserves isolated branch state.

</inline_guidance>

<process>
Follow the tangent workflow from `@{GRD_INSTALL_DIR}/workflows/tangent.md` end-to-end.
Preserve the proposal-first rule: do not silently widen scope, auto-branch, or invent a persistent tangent state machine.
</process>
