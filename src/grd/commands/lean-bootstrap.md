---
name: grd:lean-bootstrap
description: Lazily install the Lean 4 toolchain, Pantograph, and optional formal-proof dependencies. Idempotent and non-blocking.
argument-hint: "[--with-graphviz] [--with-tectonic] [--with-mathlib-cache] [--with-leandojo] [--force] [--dry-run] [--uninstall]"
context_mode: project-aware
allowed-tools:
  - file_read
  - shell
  - ask_user
---

<!-- Tool names and @ includes are platform-specific. The installer translates paths for your runtime. -->
<!-- Allowed-tools are runtime-specific. Other platforms may use different tool interfaces. -->

<objective>
Install the Lean 4 toolchain and Python-side formal-proof helpers on demand.

This skill is the **entry point for every formal-proof workflow in GRD.** Other skills (`/grd:prove`, `/grd:blueprint-status`, autoformalization, etc.) call this one when they detect a stale or missing `.grd/lean-env.json`.

**Non-blocking by design.** Stages 1–3 (elan, toolchain, Pantograph) run without any confirmation — they're user-local and reversible. Stages 4–5 (graphviz, tectonic) only run when the caller needs them. Stages 6–7 (Mathlib cache, LeanDojo premise index) are multi-gigabyte downloads and **always** require explicit consent.

Every stage's outcome is recorded to `.grd/lean-env.json` so partial runs resume cleanly and consent answers are remembered.
</objective>

<context>
Arguments: $ARGUMENTS

Current environment:

```bash
grd --raw lean env
```

Prior bootstrap state (if any):

```bash
cat .grd/lean-env.json 2>/dev/null | head -200
```
</context>

<process>

## Step 1: Parse arguments

Recognised flags:

| Flag | Effect |
|------|--------|
| `--with-graphviz` | Try user-local graphviz install for SVG dep graphs. Falls back to ASCII silently if no user package manager. |
| `--with-tectonic` | Install tectonic via cargo when no LaTeX compiler is present. HTML Blueprint works without. |
| `--with-mathlib-cache` | Opt-in: `lake exe cache get` (~10 GB). Requires user consent. |
| `--with-leandojo` | Opt-in: premise retrieval index (~3–5 GB). Requires user consent. |
| `--force` | Re-attempt every stage, ignoring cached "already installed" and prior "never" consent answers. |
| `--dry-run` | Report what would happen without touching anything. |
| `--uninstall` | Remove GRD-added Lean artifacts (`~/.elan`, caches, project `.lake`). |

If `--uninstall` is present, skip to Step 5.

## Step 2: Handle opt-in consent

For `--with-mathlib-cache`: check `.grd/lean-env.json` under `consent.mathlib_cache`.
- If `"never"` and no `--force`: record intent and continue without the stage.
- If `"yes"`: proceed.
- If absent or `"no"`: ask the user using `AskUserQuestion`:
  > "This will download ~10 GB of Mathlib olean cache to speed up Lean elaboration. Proceed? [yes / no / never]"

Record the answer to `consent.mathlib_cache` before running the stage:

```bash
grd --raw lean bootstrap --with-mathlib-cache --yes
```

Same protocol for `--with-leandojo` (~3–5 GB, premise retrieval).

If the user answered "no" or "never", **do not pass `--yes`** — let the stage record `skipped_user_declined` and move on. "never" persists across runs; "no" is a one-shot decline.

## Step 3: Run the bootstrap

```bash
REPORT=$(grd --raw lean bootstrap $FLAGS)
```

where `$FLAGS` is the subset of flags the user passed plus any consent-gated `--yes` we've earned in Step 2.

The command writes `.grd/lean-env.json` after every stage, so even if it's killed mid-way the next invocation will pick up where we left off.

## Step 4: Present the report

Parse the JSON report and show:

```
## Lean Bootstrap

| Stage | Status | Detail |
|-------|--------|--------|
| elan | {status} | {detail} |
| toolchain | {status} | {detail (include version if ok)} |
| pantograph | {status} | {detail} |
| graphviz | {status} | {detail} |
| tectonic | {status} | {detail} |
| mathlib_cache | {status} | {detail} |
| leandojo | {status} | {detail} |

---

**Required stages:** {ok|failed}
**Degradations:** {list from degraded_notes, or "none"}
**Elapsed:** {elapsed_ms} ms
```

Status legend:
- `ok` — installed or already running
- `skipped_already_installed` — green, nothing to do
- `skipped_not_requested` — optional stage the caller didn't enable
- `skipped_user_declined` — consent-gated stage the user said no/never to
- `degraded` — couldn't install cleanly; documented fallback is active
- `failed` — unexpected error, subsequent stages still ran

**If any required stage failed**, the overall command exits 1. Tell the user which stage failed, show the `detail` string, and list the degraded-mode features that still work. Do NOT re-run automatically — the user may need to address something (e.g. corporate proxy blocking the elan download) before the next try.

## Step 5: Uninstall flow (when --uninstall present)

```bash
grd --raw lean bootstrap --uninstall $DRY
```

where `$DRY` is `--dry-run` if the user passed it too.

Present the returned path list:

```
## Uninstall

| Path | Action |
|------|--------|
| ~/.elan | {removed|absent|would_remove|failed} |
| ~/.cache/leandojo | ... |
| ~/.cache/Tectonic | ... |
| {project}/.lake | ... |
| {project}/blueprint/.lake | ... |
```

Note that system-installed `graphviz` and `tectonic` are NOT removed — the user might rely on them outside GRD.

</process>

<success_criteria>

- [ ] `grd lean bootstrap` invoked with the correct flag subset.
- [ ] Consent answers for mathlib_cache / leandojo recorded to `.grd/lean-env.json` before their stages run.
- [ ] Report presented with per-stage status and any degraded-mode notes.
- [ ] On failure, the specific failing stage and its detail are surfaced so the user can fix root cause.
- [ ] `--uninstall` removes only GRD-added artifacts; system packages left alone.
      </success_criteria>
