---
name: grd:settings
description: Configure GRD workflow toggles, runtime-specific tier model overrides, review cadence, and git preferences
context_mode: projectless
allowed-tools:
  - file_read
  - file_write
  - shell
  - ask_user
---


<objective>
Interactive configuration of GRD workflow agents, runtime-specific tier model overrides, `execution.review_cadence`, and workflow/git preferences via multi-question prompt.

Keep this wrapper thin: follow the workflow and let it own option vocabulary,
user-facing explanations, and confirmation copy.
</objective>

<execution_context>
@{GRD_INSTALL_DIR}/workflows/settings.md
</execution_context>

<process>
**Follow the settings workflow** from `@{GRD_INSTALL_DIR}/workflows/settings.md`.

The workflow handles all logic including:

1. Config file creation with defaults if missing
2. Current config reading
3. Interactive settings presentation with pre-selection, covering:
   - **Research profile**: deep-theory / numerical / exploratory / review / paper-writing
   - **Tier models for the active runtime**: leave unchanged / use runtime defaults / configure explicit tier-1, tier-2, tier-3 model strings
   - **Plan researcher**: on / off
   - **Plan checker**: on / off
   - **Execution verifier**: on / off
   - **Review cadence** (`execution.review_cadence`): dense / adaptive / sparse
   - **Parallel execution**: on / off
   - **Git branching**: none / per-phase / per-milestone
4. Runtime-aware model guidance when explicit tier models are requested:
   - Ask for the exact model string the active runtime accepts
   - Preserve provider prefixes, slash-delimited ids, brackets, and alias syntax already used by that runtime
   - Prefer runtime defaults unless the user explicitly wants pinned tier overrides
   - When the runtime routes through multiple providers, confirm the provider before suggesting provider-native ids
5. Answer parsing and config merging
6. File writing
7. Confirmation display with current settings summary and quick command references

Project conventions are managed separately in `.grd/CONVENTIONS.md` and `.grd/state.json` (`convention_lock`). The settings workflow must not invent a `physics` block in `.grd/config.json`; use `grd convention set` or `/grd:validate-conventions` for convention work.
   </process>
