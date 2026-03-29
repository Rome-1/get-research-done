---
name: gpd:start
description: Choose the right first GPD action for this folder and route into the real workflow
argument-hint: "[optional short goal]"
context_mode: projectless
allowed-tools:
  - file_read
  - shell
  - ask_user
---

<!-- Tool names and @ includes are platform-specific. The installer translates paths for your runtime. -->
<!-- Allowed-tools are runtime-specific. Other platforms may use different tool interfaces. -->

<objective>
Provide a beginner-friendly first-run entry point for GPD.

Inspect the current folder, explain what GPD can do here in plain language, and
route into the correct existing workflow. Do not invent a parallel onboarding
state machine and do not silently assume the user already knows which command to
run.
</objective>

<execution_context>
@{GPD_INSTALL_DIR}/workflows/start.md
</execution_context>

<inline_guidance>

- `/gpd:start` is the first-stop chooser
- `/gpd:tour` is the read-only walkthrough when the user wants orientation before choosing a path
- `/gpd:new-project` and `/gpd:new-project --minimal` remain the real project-creation workflows
- `/gpd:map-research` remains the existing-work importer
- `/gpd:resume-work` remains the in-runtime return path for an existing GPD project
- `gpd resume --recent` remains the normal-terminal cross-project recovery path
- `/gpd:suggest-next`, `/gpd:quick`, `/gpd:explain`, and `/gpd:help` remain separate downstream entry points

</inline_guidance>

<process>
Follow the start workflow from `@{GPD_INSTALL_DIR}/workflows/start.md` end-to-end.
Preserve the routing-first rule: detect the folder state, show plain-language
choices, then hand off to the real existing workflow instead of duplicating its
logic here.
</process>
