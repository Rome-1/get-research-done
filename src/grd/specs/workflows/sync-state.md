<purpose>
Reconcile diverged `STATE.md` and `state.json`. These two files represent the same project state in different formats: `state.json` is the machine-readable authoritative store for structured state, while `STATE.md` is the human-readable markdown view that the CLI keeps in sync and can also use as a controlled recovery input when `state.json` is missing or corrupt. They can diverge when a tool crashes mid-update, when one file is edited directly, or when a manual markdown edit needs to be merged back into the structured state.
</purpose>

<required_reading>
Read all files referenced by the invoking prompt's execution_context before starting.

**Schema reference:** `{GRD_INSTALL_DIR}/templates/state-json-schema.md` — Canonical schema for state.json fields, types, defaults, and authoritative-vs-derived status. Consult when resolving conflicts between STATE.md and state.json.
Before deciding any merge or repair, read `{GRD_INSTALL_DIR}/templates/state-json-schema.md` itself and use its authoritative-vs-derived rules as the reconciliation contract rather than guessing from the current file contents.
</required_reading>

<process>

<step name="init" priority="first">
**Check both state files exist:**

```bash
STATE_MD=".grd/STATE.md"
STATE_JSON=".grd/state.json"

MD_EXISTS=$(test -f "$STATE_MD" && echo true || echo false)
JSON_EXISTS=$(test -f "$STATE_JSON" && echo true || echo false)
```

**If neither exists:**

```
No state files found. Run /grd:new-project to initialize project state.
```

Exit.

**If only STATE.md exists (state.json missing):**

Use the loader's controlled fallback path to recover `state.json` from the current markdown while preserving any backup if one exists:

```bash
if [ -f .grd/state.json ]; then
  mv .grd/state.json .grd/state.json.bak
fi

grd --raw state snapshot > /dev/null
if [ $? -ne 0 ]; then
  echo "WARNING: grd state snapshot failed — restoring backup"
  if [ -f .grd/state.json.bak ]; then
    mv .grd/state.json.bak .grd/state.json
  fi
else
  rm -f .grd/state.json.bak
fi
```

Report: "state.json recovered from STATE.md via fallback sync." Exit (no divergence to reconcile).

**If only state.json exists (STATE.md missing):**

`state.json` is the authoritative copy. Rebuild `STATE.md` directly from it:

```bash
uv run python - <<'PY'
import json
from pathlib import Path
from grd.core.state import save_state_json

cwd = Path(".")
state = json.loads((cwd / ".grd" / "state.json").read_text(encoding="utf-8"))
save_state_json(cwd, state)
PY
```

If state.json is also corrupt or empty, re-initialize the project.

Exit.

**If both exist:** Continue to comparison.
</step>

<step name="read_both">
**Read both state representations:**

```bash
# Read STATE.md
cat .grd/STATE.md

# Read state.json
cat .grd/state.json
```

**Parse STATE.md into comparable fields:**

Extract from STATE.md (using text parsing):
- Current Phase (number and name)
- Current Plan
- Status
- Last Activity
- Core research question
- Current focus
- Decisions list
- Blockers list
- Session info (last date, stopped at, resume file)

**Parse state.json fields:**

Extract from state.json:
- `position.current_phase`, `position.current_phase_name`
- `position.current_plan`
- `position.status`
- `position.last_activity`
- `project_reference.core_research_question`
- `project_reference.current_focus`
- `decisions[]`
- `blockers[]`
- `session.last_date`, `session.stopped_at`
- `convention_lock` (JSON-only field)
- `intermediate_results` (JSON-only field)
- `approximations` (JSON-only field)
- `propagated_uncertainties` (JSON-only field)
</step>

<step name="compare_fields">
**Compare shared fields between STATE.md and state.json:**

For each shared field, check if values match:

| Field | STATE.md | state.json | Match |
|-------|----------|------------|-------|
| current_phase | {md_value} | {json_value} | {YES/NO} |
| current_plan | {md_value} | {json_value} | {YES/NO} |
| status | {md_value} | {json_value} | {YES/NO} |
| last_activity | {md_value} | {json_value} | {YES/NO} |
| core_research_question | {md_value} | {json_value} | {YES/NO} |
| current_focus | {md_value} | {json_value} | {YES/NO} |
| decision_count | {md_count} | {json_count} | {YES/NO} |
| blocker_count | {md_count} | {json_count} | {YES/NO} |

**If all fields match:**

```
STATE.md and state.json are in sync. No reconciliation needed.
```

Optionally run `grd state validate` and exit.

**If divergences found:** Continue to resolution.
</step>

<step name="determine_recency">
**For each divergent field, determine which source is more recent:**

```bash
# File modification times
MD_MOD=$(stat -f %m .grd/STATE.md 2>/dev/null || stat -c %Y .grd/STATE.md 2>/dev/null || echo 0)
JSON_MOD=$(stat -f %m .grd/state.json 2>/dev/null || stat -c %Y .grd/state.json 2>/dev/null || echo 0)

# Git history for more precise tracking
MD_LAST_COMMIT=$(git log -1 --format="%H %ai" -- .grd/STATE.md 2>/dev/null)
JSON_LAST_COMMIT=$(git log -1 --format="%H %ai" -- .grd/state.json 2>/dev/null)
```

**Recency rules:**

1. **state.json is authoritative** for structured state, including the shared machine-parsed fields mirrored into `STATE.md`.
2. **STATE.md can still be the intended newer source** when a recent manual markdown edit was made to schema-backed fields and has not yet been merged back.
3. **Preserve JSON-only fields from state.json** (`convention_lock`, `intermediate_results`, `approximations`, `propagated_uncertainties`) in every reconciliation path.
4. If timestamps are equal or ambiguous and there is no clear evidence of an intentional markdown edit, prefer `state.json`.
</step>

<step name="present_divergences">
**Present divergences to user for confirmation:**

```
## State Divergence Detected

| Field | STATE.md | state.json | Preferred | Reason |
|-------|----------|------------|-----------|--------|
| current_phase | 5 | 4 | STATE.md | Intentional markdown edit after last structured write |
| status | "Executing" | "Ready to plan" | STATE.md | Same manual edit as current_phase |
| decision_count | 12 | 10 | state.json | No matching markdown-only decision should override structured state |

### JSON-only fields (no divergence possible):
- convention_lock: {count} fields locked
- intermediate_results: {count} results
- approximations: {count} entries

### Proposed resolution:
- Merge the intentional markdown-backed fields into state.json
- Preserve state.json-only fields as-is
- Re-run state validation

Proceed with reconciliation? (y/n)
```

Wait for user confirmation.
</step>

<step name="reconcile">
**Merge into consistent state:**

**Strategy:** Apply the preferred value for each divergent field, then sync both files.

**For STATE.md-preferred fields:**

Regenerate state.json from STATE.md by backing it up and triggering a state read (which merges parsed markdown fields INTO existing JSON backup, preserving `convention_lock`, `intermediate_results`, `approximations`, and `propagated_uncertainties`):

```bash
if [ -f .grd/state.json ]; then
  mv .grd/state.json .grd/state.json.bak
fi

grd --raw state snapshot > /dev/null
if [ $? -ne 0 ]; then
  echo "WARNING: grd state snapshot failed — restoring backup"
  if [ -f .grd/state.json.bak ]; then
    mv .grd/state.json.bak .grd/state.json
  fi
else
  rm -f .grd/state.json.bak
fi
```

**For state.json-preferred fields (including the common case where JSON is newer):**

Regenerate `STATE.md` from `state.json`:

```bash
uv run python - <<'PY'
import json
from pathlib import Path
from grd.core.state import save_state_json

cwd = Path(".")
state = json.loads((cwd / ".grd" / "state.json").read_text(encoding="utf-8"))
save_state_json(cwd, state)
PY
```

**Verify sync result:**

```bash
# Re-read both files and confirm no remaining divergences
grd --raw state validate
```
</step>

<step name="commit">
**Commit reconciled state:**

```bash
PRE_CHECK=$(grd pre-commit-check --files .grd/STATE.md .grd/state.json 2>&1) || true
echo "$PRE_CHECK"

grd commit \
  "fix: reconcile STATE.md and state.json divergence" \
  --files .grd/STATE.md .grd/state.json
```
</step>

<step name="report">
**Report what was reconciled:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GRD > STATE SYNCHRONIZED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Divergences resolved:** {count}

| Field | Old (diverged) | New (reconciled) | Source |
|-------|----------------|------------------|--------|
| current_phase | 4 (json) -> 5 (md) | 5 | STATE.md |
| status | "Ready to plan" -> "Executing" | "Executing" | STATE.md |

**JSON-only fields preserved:**
- convention_lock: {count} fields
- intermediate_results: {count} results

**Validation status:** {healthy / warning / degraded}

Both files are now consistent.
```
</step>

</process>

<failure_handling>

- **STATE.md corrupt (unparseable):** If STATE.md cannot be parsed, check if state.json is valid and regenerate STATE.md from it. If both are corrupt, suggest restoring from git: `git checkout HEAD~1 -- .grd/STATE.md .grd/state.json`
- **state.json corrupt (invalid JSON):** Move it aside to `.grd/state.json.bak`, then use the fallback recovery path from `STATE.md`. Do not delete it without keeping a backup first.
- **Regeneration still fails:** Fall back to manual reconciliation — read STATE.md, write state.json directly using `grd state` subcommands.
- **Both files very old (neither recently committed):** Warn user that both files may be stale. Suggest checking git log for the most recent good state.

</failure_handling>

<success_criteria>

- [ ] Both state files checked for existence
- [ ] Missing file regenerated from the other (if applicable)
- [ ] All shared fields compared between STATE.md and state.json
- [ ] Divergences identified with recency analysis
- [ ] User confirmed reconciliation plan
- [ ] Preferred values applied to both files
- [ ] JSON-only fields preserved during sync
- [ ] Both files verified as consistent after reconciliation
- [ ] Changes committed
- [ ] Report presented with what was reconciled
</success_criteria>
