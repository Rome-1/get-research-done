---
name: grd:decisions
description: Display and search the cumulative decision log
argument-hint: "[phase number or keyword]"
context_mode: project-required
requires:
  files: [".grd/STATE.md"]
allowed-tools:
  - file_read
  - shell
  - search_files
  - find_files
---

<!-- Tool names and @ includes are platform-specific. The installer translates paths for your runtime. -->
<!-- Allowed-tools are runtime-specific. Other platforms may use different tool interfaces. -->

<objective>
Display the cumulative decision log from .grd/DECISIONS.md with optional filtering by phase number or keyword search.

Routes to the decisions workflow which handles:

- Loading and parsing the decision log table
- Filtering by phase number (e.g., `/grd:decisions 3`)
- Keyword search across all fields (e.g., `/grd:decisions regularization`)
- Formatted display with summary statistics
  </objective>

<execution_context>
@.grd/STATE.md
@{GRD_INSTALL_DIR}/workflows/decisions.md
</execution_context>

<process>
**Follow the decisions workflow** from `@{GRD_INSTALL_DIR}/workflows/decisions.md`.

The workflow handles all logic including:

1. Decision log existence checking
2. Argument parsing (phase number vs keyword)
3. Table filtering and display
4. Summary statistics
   </process>
