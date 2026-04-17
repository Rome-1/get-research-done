<purpose>
Thin wrapper around `grd-consistency-checker` for convention validation.

This workflow resolves the requested scope, delegates the physics policy to the checker, and accepts success only when the typed `grd_return.status` and the expected consistency report artifact both check out. The checker owns the convention logic; this workflow only gates scope, artifact presence, and post-return routing.
</purpose>

<required_reading>
Read all files referenced by the invoking prompt's execution_context before starting.
</required_reading>

@{GRD_INSTALL_DIR}/references/orchestration/runtime-delegation-note.md

<process>

<step name="initialize" priority="first">
Load project context and scope:

```bash
INIT=$(grd init progress --include state,roadmap,config)
if [ $? -ne 0 ]; then
  echo "ERROR: grd initialization failed: $INIT"
  # STOP — display the error to the user and do not proceed.
fi
```

Parse JSON for: `state_exists`, `roadmap_exists`, `phases`, `current_phase`, `derived_convention_lock`, and when phase-scoped `phase_found`, `phase_dir`, `phase_number`.

Read mode settings:

```bash
AUTONOMY=$(grd --raw config get autonomy 2>/dev/null | grd json get .value --default balanced 2>/dev/null || echo "balanced")
```

Run centralized context preflight before continuing:

```bash
CONTEXT=$(grd --raw validate command-context validate-conventions "$ARGUMENTS")
if [ $? -ne 0 ]; then
  echo "$CONTEXT"
  exit 1
fi
```

If `state_exists` is false:

```
No project state found. Run /grd:new-project first.
```

Exit.

Resolve scope immediately after preflight:

- If `$PHASE_ARG` is set, require `phase_found: true` from `init phase-op` and derive a single-phase scope from `phase_dir`.
- If `$PHASE_ARG` is empty, scan all completed phases from `grd --raw roadmap analyze`.
- If the requested phase cannot be resolved, fail closed with `ERROR: Phase not found: ${PHASE_ARG}`.

Capture the selected phase directory and roadmap view for the downstream scan:

```bash
ROADMAP=$(grd --raw roadmap analyze)
```

Load the convention ledger:

```bash
CONVENTIONS=$(grd convention list)
```

Read `GRD/CONVENTIONS.md` when present so the checker can compare the human-readable convention record against the structured lock. If the file is missing, continue with the structured lock and report the missing artifact as a limitation rather than inventing a fallback policy.
</step>

<step name="delegate_checker">
Spawn `grd-consistency-checker` once and let it own convention policy.

Use the requested scope to choose checker mode:

- `PHASE_ARG` present -> `rapid`
- no phase argument -> `full`

For the checker prompt, provide only the scope, expected artifact path, and the required project files. Do not restate the checker's severity taxonomy or convention policy here.

Derive the routed scope explicitly:

```bash
cat .grd/CONVENTIONS.md 2>/dev/null
```

Expected artifact:

- phase-scoped run: `GRD/phases/${PHASE_DIR}/CONSISTENCY-CHECK.md`
- project-wide run: `GRD/CONSISTENCY-CHECK.md`

For each field in the convention lock:

1. Find the corresponding entry in CONVENTIONS.md
2. Compare values

| Field | Convention Lock | CONVENTIONS.md | Status |
|-------|----------------|----------------|--------|
| metric_signature | (-,+,+,+) | (-,+,+,+) | OK |
| fourier_convention | physics | mathematical | DRIFT |

**DRIFT** means the documents disagree. This is a CRITICAL issue — one must be wrong.

For each drift:

```
CRITICAL: Convention drift detected

Field: {field}
Convention lock (state.json): {lock_value}
CONVENTIONS.md: {conventions_value}

The convention lock is authoritative. If CONVENTIONS.md is correct,
update the lock: grd convention set {field} "{value}"
```
</step>

<step name="scan_phase_conventions">
**Scan all completed phases for convention declarations:**

```bash
ROADMAP=$(grd roadmap analyze)
```

Use the selected scope to gather summary artifacts:

```bash
# Extract conventions from summary-artifact frontmatter
for SUMMARY in .grd/phases/${PHASE_DIR}/*SUMMARY.md; do
  grd summary-extract "$SUMMARY" --field conventions --field affects
done
```

Build a convention map:

```
phase_conventions = {
  "Phase 1": { metric_signature: "(-,+,+,+)", fourier: "physics", ... },
  "Phase 2": { metric_signature: "(-,+,+,+)", hbar: "1", ... },
  "Phase 3": { metric_signature: "(+,-,-,-)", ... },  // MISMATCH
}
```
</step>

<step name="cross_reference">
**Cross-reference: do all phase conventions match the project convention lock?**

For each phase and each convention field declared:

1. Look up the field in the convention lock
2. Compare values

Build a findings list with severity levels:

**CRITICAL (sign-affecting, metric, units):**
- Metric signature mismatch (`(-,+,+,+)` vs `(+,-,-,-)`)
- Sign convention mismatch (e.g., `e^{-ikx}` vs `e^{+ikx}` Fourier)
- Unit system mismatch (natural vs SI vs Gaussian)
- Factors of `2*pi` in Fourier convention
- Time-ordering sign convention
- Coupling constant sign

**WARNING (notation inconsistency, non-propagating):**
- Variable naming drift (same quantity, different symbol)
- Index placement conventions (up vs down)
- Normalization convention differences
- Coordinate labeling differences

**INFO (cosmetic, no physics impact):**
- Formatting differences in convention declaration
- Redundant convention re-declarations matching the lock
</step>

<step name="check_unlocked_conventions">
**Identify conventions used across phases but NOT locked:**

Some conventions may appear in phase summaries but never got added to the convention lock. These are vulnerable to drift.

For each convention field found in any phase summary that is NOT in the convention lock:

```
WARNING: Unlocked convention used across phases

Field: {field}
Used in: Phase {X}, Phase {Y}
Values: {X_value}, {Y_value}

This convention is not locked. If phases agree, lock it:
  grd convention set {field} "{value}"

If phases disagree, this is a potential error source.
```
</step>

<step name="spawn_consistency_checker">
**For thorough validation, spawn grd-consistency-checker in rapid mode:**

```bash
CONSISTENCY_MODEL=$(grd resolve-model grd-consistency-checker)
```

```
task(
  subagent_type="grd-consistency-checker",
  model="{consistency_model}",
  readonly=false,
  prompt="First, read {GRD_AGENTS_DIR}/grd-consistency-checker.md for your role and instructions.

<mode>{CHECKER_MODE}</mode>
<scope>{CHECK_SCOPE}</scope>
<expected_artifacts>
- {EXPECTED_ARTIFACT}
</expected_artifacts>

    Validate convention consistency across the entire project.
    Read conventions from state.json via: grd convention list
    Read all summary artifacts (`SUMMARY.md` and `*-SUMMARY.md`) from all completed phases.
    file_read: .grd/STATE.md, .grd/state.json, .grd/CONVENTIONS.md

    Focus on:
    1. Sign conventions propagating correctly across phase boundaries
    2. Metric signature consistency in all tensor expressions
    3. Fourier transform convention (factors of 2*pi) consistency
    4. Unit system consistency (natural units, hbar=1, c=1 implications)
    5. Normalization conventions for wavefunctions, propagators, amplitudes

    Return consistency_status with detailed issue list.
  ",
  description="Validate conventions across all phases"
)
```

**If the consistency checker agent fails to spawn or returns an error:** Proceed without automated consistency checking. Note in the validation report that cross-phase consistency verification was skipped. The convention lock fields and CONVENTIONS.md can still be inspected manually. The user should run `/grd:validate-conventions` again or inspect conventions manually.

1. The expected artifact exists on disk.
2. The same path appears in `grd_return.files_written`.

If either check fails, treat the handoff as incomplete and do not accept success.
</step>

<step name="route_return">
Route only on the canonical `grd_return.status`:

- `grd_return.status: completed` means the checker finished for the selected scope. Surface any advisory items from `grd_return.issues`, but do not reinterpret the status text.
- `grd_return.status: checkpoint` means the checker needs user input. Present the checkpoint, offer the user the next action, and stop. Present options, checkpoint, and return.
- `grd_return.status: blocked` or `grd_return.status: failed` means the checker could not complete. Surface `grd_return.issues`, keep the run fail-closed, and stop.

Do not route on checker-local text markers or headings. Those are presentation only; route only on the canonical `grd_return.status`.

If the checker's `next_actions` call for notation repair, spawn `grd-notation-coordinator` with the checker report and the same scope. Keep that handoff thin: the coordinator owns the repair policy, not this workflow.

Verify that `GRD/CONVENTIONS.md` exists and that `grd convention list` reflects the resolved fields before accepting the update. Convention artifact and lock re-verified after notation resolution before success is accepted.
</step>

<step name="report">
Present a concise convention report:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GRD > CONVENTION VALIDATION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before accepting any repaired result from the notation coordinator, re-check that `GRD/CONVENTIONS.md` exists and that `grd convention list` reflects the resolved fields.

### Convention Lock vs CONVENTIONS.md

| Field | Lock | Doc | Status |
|-------|------|-----|--------|
| metric_signature | (-,+,+,+) | (-,+,+,+) | OK |
| fourier_convention | physics | physics | OK |

### Phase-by-Phase Consistency

| Phase | Field | Expected | Actual | Severity |
|-------|-------|----------|--------|----------|
| 3 | metric_signature | (-,+,+,+) | (+,-,-,-) | CRITICAL |
| 5 | fourier | physics | mathematical | CRITICAL |

### Unlocked Conventions

| Field | Phases | Values | Risk |
|-------|--------|--------|------|
| hbar_convention | 2, 4, 6 | all "1" | Low (consistent) |
| coupling_def | 3, 5 | "g^2/4pi", "g" | HIGH (inconsistent) |

### Summary

- CRITICAL: {count} (sign-affecting mismatches — must fix)
- WARNING: {count} (notation inconsistencies — should fix)
- INFO: {count} (cosmetic — can ignore)
```

**If CRITICAL issues found:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRITICAL convention violations detected. Results in affected phases
may be incorrect.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Spawn grd-notation-coordinator to resolve conflicts:**

```bash
NOTATION_MODEL=$(grd resolve-model grd-notation-coordinator)
```
> **Runtime delegation:** Spawn a subagent for the task below. Adapt the `task()` call to your runtime's agent spawning mechanism. If `model` resolves to `null` or an empty string, omit it so the runtime uses its default model. Always pass `readonly=false` for file-producing agents. If subagent spawning is unavailable, execute these steps sequentially in the main context.

```
task(
  subagent_type="grd-notation-coordinator",
  model="{notation_model}",
  readonly=false,
  prompt="First, read {GRD_AGENTS_DIR}/grd-notation-coordinator.md for your role and instructions.

<task>
Resolve convention conflicts detected by validation.
</task>

<conflicts>
{structured_issues_from_consistency_checker}
</conflicts>

<project_context>
file_read: .grd/CONVENTIONS.md, .grd/STATE.md, .grd/state.json
file_read affected phase summary artifacts.
</project_context>

<instructions>
1. For each CRITICAL conflict, determine which convention is correct
2. Generate conversion tables for affected quantities
3. Update CONVENTIONS.md with resolved conventions
4. Lock resolved conventions via grd convention set
5. Return CONVENTION UPDATE with list of affected phases that need re-execution
</instructions>
",
  description="Resolve convention conflicts"
)
```

**If the notation coordinator agent fails to spawn or returns an error:** Report the failure. The CRITICAL convention conflicts still need resolution. Offer: 1) Retry notation coordinator, 2) Resolve conflicts manually by editing CONVENTIONS.md and running `grd convention set` for each field, 3) Abort and leave conflicts unresolved (not recommended — downstream phases will inherit inconsistencies).

**Handle notation-coordinator return:**

- **`CONVENTION UPDATE`:** Display resolved conventions and affected phases. Commit updated CONVENTIONS.md.
- **`CONVENTION CONFLICT`:** Conflicts require user decision. Present options and wait.

**After resolution, recommend follow-up actions:**

```
Recommended actions:
1. /grd:regression-check {affected_phases} -- re-scan affected phases
2. /grd:debug -- investigate specific discrepancies
3. Re-execute affected plans with corrected conventions
```

**If WARNING issues only:**

```
No critical issues. {count} warnings found — review and fix at your discretion.

Lock consistent conventions:
  grd convention set {field} "{value}"
```

**If CONSISTENT:**

```
All conventions consistent across {count} phases. No issues found.
```
</step>

</process>

<failure_handling>

- **No convention lock:** Report that no conventions are locked. Suggest running `/grd:execute-phase` which locks conventions before parallel execution.
- **No summary artifacts:** Cannot validate — no phase data to check. Report and exit.
- **Consistency checker agent fails:** Fall back to the static analysis from steps 2-4 (convention lock drift + phase scan + cross-reference). Report that deep consistency check was skipped.
- **CONVENTIONS.md missing:** Skip the drift check (step 2). Rely on convention lock in state.json as sole authority.

</failure_handling>

<success_criteria>

- [ ] Convention lock loaded from state.json
- [ ] CONVENTIONS.md compared against lock (if exists)
- [ ] All completed phase summary artifacts scanned for convention fields
- [ ] Cross-reference performed: each phase convention vs project lock
- [ ] Unlocked but used conventions identified
- [ ] grd-consistency-checker spawned for deep validation
- [ ] Issues classified by severity (CRITICAL / WARNING / INFO)
- [ ] grd-notation-coordinator spawned for CRITICAL issues (convention conflict resolution)
- [ ] Report presented with actionable next steps
- [ ] Critical issues flagged for immediate attention
</success_criteria>
