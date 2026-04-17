---
name: grd:start
description: Choose the right first GRD action for this folder and route into the real workflow
argument-hint: "[optional short goal]"
context_mode: projectless
allowed-tools:
  - file_read
  - shell
  - ask_user
---


<objective>
Provide a beginner-friendly first-run entry point for GRD.

Inspect the current folder, show the safest next step first, then explain the
broader options in plain language. Keep the language novice-friendly, and
explain official terms the first time they appear instead of assuming prior
CLI, Git, or workflow knowledge. Do not invent a parallel onboarding state
machine and do not silently assume the user already knows which command to run.
</objective>

<execution_context>
@{GRD_INSTALL_DIR}/workflows/start.md
</execution_context>

<inline_guidance>

@{GRD_INSTALL_DIR}/references/onboarding/beginner-command-taxonomy.md

- `grd resume` remains the local read-only current-workspace recovery snapshot
- `grd resume --recent` remains the normal-terminal advisory recent-project picker; choose the workspace there, then `grd:resume-work` reloads canonical state in the reopened project
- `grd:suggest-next` is the fastest post-resume next command when you only need the next action
- `grd:suggest-next`, `grd:quick`, `grd:explain`, and `grd:help` remain separate downstream entry points

</inline_guidance>

<process>
Follow the start workflow from `@{GRD_INSTALL_DIR}/workflows/start.md` end-to-end.
Preserve the routing-first rule: detect the folder state, show plain-language
choices, then hand off to the real existing workflow instead of duplicating its
logic here.
</process>
