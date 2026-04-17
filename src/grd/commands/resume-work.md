---
name: grd:resume-work
description: Resume research from previous session with full context restoration
context_mode: project-required
project_reentry_capable: true
requires:
  files: [".grd/ROADMAP.md", ".grd/STATE.md"]
allowed-tools:
  - file_read
  - shell
  - file_write
  - ask_user
---


<objective>
Resume research from the selected project's canonical state.
</objective>

<execution_context>
@{GRD_INSTALL_DIR}/workflows/resume-work.md
</execution_context>

<process>
**Follow the resume-work workflow** from `@{GRD_INSTALL_DIR}/workflows/resume-work.md`.

The workflow handles all resumption logic including:

1. Project existence verification
2. STATE.md loading or reconstruction
3. Checkpoint and incomplete work detection
4. Restoration of research context:
   - Where the derivation or computation was paused
   - Parameter values and variable definitions in scope
   - Intermediate results and partial solutions
   - Approximations and assumptions active at pause time
   - Planned next steps from previous session
5. Visual status presentation
6. Context-aware option offering (checks CONTEXT.md before suggesting plan vs discuss)
7. Routing to appropriate next command
8. Session continuity updates
   </process>
