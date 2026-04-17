---
load_when:
  - "verification child-return"
  - "artifact gate"
  - "checkpoint and restart"
  - "canonical verification report"
  - "grd_return.files_written"
tier: 1
context_cost: medium
---

# Verification Child-Return Contract

This reference captures the reusable handoff seam for verification workflows that spawn or supervise proof-bearing verification runs. It keeps the generic control flow in one place so the workflow files can stay focused on report/schema/proof authority.

## Ownership Boundaries

The orchestrator owns the fresh continuation. The child runs once. If the child needs user input, it returns `status: checkpoint` and stops. Human-readable headings are presentation only; route on the structured return envelope.

This reference does not define the verification-report schema, proof-redteam schema, or contract-ledger shape. The workflow that owns the verification phase must still validate those artifacts explicitly before accepting success.

## Artifact Gate

A reported success is provisional until the expected canonical artifact exists on disk.

- Verify the expected artifact path exists and is readable.
- Verify the child return names the same path in `grd_return.files_written`.
- If the artifact pre-existed before the run, do not treat it as fresh output unless the child return explicitly names it.
- If the artifact is missing, unreadable, stale, or absent from `grd_return.files_written`, treat the handoff as incomplete even when the runtime says it finished cleanly.

## Checkpoint Handling

A checkpoint is not a paused child. The child stops and returns; the orchestrator presents the checkpoint and starts a fresh continuation after the user responds. Do not wait inside the same run.

## Verification-Specific Notes

When the canonical artifact is a verification report, the workflow must still run its own schema and contract validation before downstream routing. For proof-bearing work, the sibling proof-redteam artifact remains a separate mandatory gate owned by the workflow, not by this reference.
