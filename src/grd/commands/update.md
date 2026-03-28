---
name: grd:update
description: Update GRD to latest version with changelog display
context_mode: global
allowed-tools:
  - shell
  - ask_user
---

<!-- Tool names and @ includes are platform-specific. The installer translates paths for your runtime. -->
<!-- Allowed-tools are runtime-specific. Other platforms may use different tool interfaces. -->

<objective>
Check for GRD updates, install if available, and display what changed.

Routes to the update workflow which handles:

- Version detection (local vs global installation)
- Explicit-target installs that require `--target-dir <path>`
- Package version checking
- Changelog fetching and display
- User confirmation with clean install warning
- Update execution and cache clearing
- Restart reminder
  </objective>

<execution_context>
@{GRD_INSTALL_DIR}/workflows/update.md
</execution_context>

<process>
**Follow the update workflow** from `@{GRD_INSTALL_DIR}/workflows/update.md`.

The workflow handles all logic including:

1. Installed version detection (local/global)
2. Explicit-target detection and `--target-dir` handling
3. Latest version checking via package registry
4. Version comparison
5. Changelog fetching and extraction
6. Clean install warning display
7. User confirmation
8. Update execution
9. Cache clearing
   </process>
