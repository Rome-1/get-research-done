<purpose>
Safely rollback the last GRD-related git commit. Creates a safety checkpoint tag before reverting so the operation itself is reversible. Use when a plan, execution, or verification produced incorrect results and you want to undo cleanly.
</purpose>

<required_reading>
Read all files referenced by the invoking prompt's execution_context before starting.
</required_reading>

<process>

<step name="find_last_gpd_commit">
**Search recent git log for the last GRD-related commit:**

```bash
git log --oneline -20
```

Identify commits with GRD message patterns. GRD commits use conventional commit prefixes with a GRD scope:

- `docs(grd):` or `docs(phase-NN):` -- research output, plans, reports, documentation
- `fix(grd):` or `fix(phase-NN):` -- corrections to existing work
- `feat(grd):` or `feat(phase-NN):` -- new capabilities or phases
- `chore(grd):` or `chore(phase-NN):` -- metadata, state updates, maintenance
- `test(grd):` -- test additions or updates
- `undo:` -- previous undo operations

Match commits where the message starts with one of these prefixes, OR contains `(grd)` or `(phase-` in the scope (e.g., `docs(phase-03): complete execution`).

**If no GRD commit found in recent history:**

```
╔══════════════════════════════════════════════════════════════╗
║  ERROR                                                       ║
╚══════════════════════════════════════════════════════════════╝

No GRD commits found in the last 20 commits.

Recent commits:
{last 5 commits from git log}

Nothing to undo.
```

Exit.

Store the identified commit hash and message:

```bash
TARGET_HASH={hash}
TARGET_MSG={message}
```

</step>

<step name="check_merge_commit">
**Verify the target is not a merge commit:**

```bash
git cat-file -p ${TARGET_HASH} | grep -c "^parent"
```

**If more than 1 parent (merge commit):**

```
╔══════════════════════════════════════════════════════════════╗
║  ERROR                                                       ║
╚══════════════════════════════════════════════════════════════╝

Cannot undo merge commits. The last GRD commit is a merge:

  {TARGET_HASH} {TARGET_MSG}

To undo a merge, use git revert -m 1 {hash} manually after careful review.
```

Exit.
</step>

<step name="show_impact">
**Display what would be undone:**

```bash
git show --stat ${TARGET_HASH}
git diff ${TARGET_HASH}^..${TARGET_HASH} --stat
```

Present:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GRD > UNDO PREVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Commit:** {TARGET_HASH}
**Message:** {TARGET_MSG}
**Date:** {commit date}

**Files changed:**
{file list from git show --stat}

**Summary:**
- {N} files modified
- {additions} insertions, {deletions} deletions
```

If the commit modified `.grd/STATE.md`, note this:

```
⚠ This commit modified STATE.md -- the undo will also roll back state tracking.
```

</step>

<step name="confirm">
**Ask for user confirmation:**

```
╔══════════════════════════════════════════════════════════════╗
║  CHECKPOINT: Decision Required                               ║
╚══════════════════════════════════════════════════════════════╝

Undo this commit?

  {TARGET_HASH} {TARGET_MSG}

A safety checkpoint will be created first so this undo can itself be reversed.

──────────────────────────────────────────────────────────────
→ Type "yes" to proceed or "no" to cancel
──────────────────────────────────────────────────────────────
```

**If user declines:** "Undo cancelled. No changes made." Exit.
</step>

<step name="create_checkpoint">
**Create safety checkpoint tag:**

```bash
CHECKPOINT_TAG="grd-checkpoint/$(date +%Y%m%d-%H%M%S)"
git tag "${CHECKPOINT_TAG}"
```

Confirm:

```
✓ Safety checkpoint created: ${CHECKPOINT_TAG}
  To restore if needed: git reset --hard ${CHECKPOINT_TAG}
```

</step>

<step name="revert_commit">
**Perform the revert:**

```bash
git revert --no-commit ${TARGET_HASH}
```

**If revert conflicts:**

```
╔══════════════════════════════════════════════════════════════╗
║  CHECKPOINT: Action Required                                 ║
╚══════════════════════════════════════════════════════════════╝

Revert produced conflicts in:
{list of conflicted files}

The safety checkpoint is at: ${CHECKPOINT_TAG}

──────────────────────────────────────────────────────────────
→ Resolve conflicts, then type "done" -- or type "abort" to cancel
──────────────────────────────────────────────────────────────
```

**If abort:**

```bash
git revert --abort
```

"Undo aborted. Repository restored to pre-undo state." Exit.

**If done (conflicts resolved or no conflicts):**

Commit the revert:

```bash
PRE_CHECK=$(grd pre-commit-check --files .grd/STATE.md .grd/state.json 2>&1) || true
echo "$PRE_CHECK"

git commit -m "$(cat <<'EOF'
undo: revert {TARGET_MSG}
EOF
)"
```

</step>

<step name="update_state">
**If the reverted commit modified STATE.md:**

Read `.grd/STATE.md` and check if it needs adjustment:

1. If the reverted commit added a phase completion marker, restore the affected field(s) with `grd state update` / `grd state patch`
2. If the reverted commit advanced the current phase, roll back the position with `grd state update` / `grd state patch` rather than direct `file_edit` so `STATE.md` and `state.json` stay aligned
3. Record the rollback decision:

```bash
grd state add-decision --phase "undo" --summary "Rolled back: ${TARGET_MSG}" --rationale "User requested undo (checkpoint: ${CHECKPOINT_TAG})"
```

4. Commit:

```bash
PRE_CHECK=$(grd pre-commit-check --files .grd/STATE.md .grd/state.json 2>&1) || true
echo "$PRE_CHECK"

grd commit "docs: update state after undo" --files .grd/STATE.md .grd/state.json
```

**If STATE.md was not affected:** Skip this step.
</step>

<step name="completion">
**Present completion summary:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 GRD > UNDO COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Reverted:** {TARGET_HASH} {TARGET_MSG}
**Checkpoint:** {CHECKPOINT_TAG}
**State updated:** {yes/no}

To reverse this undo:
  git reset --hard {CHECKPOINT_TAG}

───────────────────────────────────────────────────────────────

**Also available:**
- `/grd:progress` -- check current research state
- `/grd:undo` -- undo another commit
- `/grd:verify-work` -- re-verify after rollback

───────────────────────────────────────────────────────────────
```

</step>

</process>

<anti_patterns>

- NEVER undo merge commits -- they require manual `git revert -m` with parent selection
- NEVER force-push after undo -- the revert commit is the safe way to undo
- NEVER skip the safety checkpoint tag -- it makes the undo itself reversible
- NEVER undo without user confirmation -- always show what will change first
- Don't undo non-GRD commits -- only target commits matching GRD prefixes
- Don't chain undos automatically -- each undo is a separate user-confirmed operation
  </anti_patterns>

<success_criteria>
Undo is complete when:

- [ ] Last GRD commit identified correctly
- [ ] Merge commits rejected with explanation
- [ ] User shown full impact (files changed, diff summary)
- [ ] User confirmed before any changes
- [ ] Safety checkpoint tag created
- [ ] Clean revert via `git revert` (no force operations)
- [ ] Revert committed with descriptive `undo:` prefix message
- [ ] STATE.md updated if it was affected by the reverted commit
- [ ] User informed of checkpoint tag for reversal

</success_criteria>
