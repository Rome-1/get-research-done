---
name: grd:tour
description: Show a guided beginner walkthrough of the core GRD commands without taking action
argument-hint: "[optional short goal]"
context_mode: projectless
allowed-tools:
  - file_read
---


<objective>
Provide a safe beginner walkthrough of the core GRD command paths.

Explain what the main commands are for, when to use each one, and how they fit
together in plain language for a first-time user. Explain advanced terms the
first time they appear instead of assuming GRD terminology, CLI familiarity, or
prior workflow knowledge. Do not create project artifacts, do not create files,
and do not silently route into another workflow.
</objective>

<execution_context>
@{GRD_INSTALL_DIR}/workflows/tour.md
</execution_context>

<inline_guidance>

@{GRD_INSTALL_DIR}/references/onboarding/beginner-command-taxonomy.md

- `grd:tour` is a teaching surface, not a chooser
- `grd:progress`, `grd:suggest-next`, `grd:explain`, `grd:quick`, `grd:set-tier-models`, `grd:settings`, and `grd:help` are the common follow-up commands

</inline_guidance>

<process>
Follow the tour workflow from `@{GRD_INSTALL_DIR}/workflows/tour.md` end-to-end.
Keep the response instructional and self-contained. Show the main command paths
and the situations they fit, but do not hand off to another workflow or create
any artifacts.
</process>
