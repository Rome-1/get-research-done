---
name: gpd:tour
description: Show a guided beginner walkthrough of the core GPD commands without taking action
argument-hint: "[optional short goal]"
context_mode: projectless
allowed-tools:
  - file_read
  - shell
---

<!-- Tool names and @ includes are platform-specific. The installer translates paths for your runtime. -->
<!-- Allowed-tools are runtime-specific. Other platforms may use different tool interfaces. -->

<objective>
Provide a safe beginner walkthrough of the core GPD command paths.

Explain what the main commands are for, when to use each one, and how they fit
together. Do not create project files, do not silently route into another
workflow, and do not assume the user already knows GPD terminology.
</objective>

<execution_context>
@{GPD_INSTALL_DIR}/workflows/tour.md
</execution_context>

<inline_guidance>

- `/gpd:tour` is a teaching surface, not a chooser
- `/gpd:start` is the actual first-run router when the user wants the right next action
- `/gpd:new-project` and `/gpd:new-project --minimal` are for creating a new project
- `/gpd:map-research` is for bringing an existing folder into GPD
- `/gpd:resume-work` is for returning to an existing GPD project
- `/gpd:progress`, `/gpd:suggest-next`, `/gpd:explain`, `/gpd:quick`, and `/gpd:help` are the common follow-up commands

</inline_guidance>

<process>
Follow the tour workflow from `@{GPD_INSTALL_DIR}/workflows/tour.md` end-to-end.
Keep the response instructional and self-contained. Show the main command paths
and the situations they fit, but do not hand off to another workflow or create
any artifacts.
</process>
