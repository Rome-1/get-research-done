---
name: grd:formalize-claim
description: "Planned (Phase 3) — translate a contract claim into a Lean 4 statement + blueprint stub. See research/formal-proof-integration/STATUS.md."
argument-hint: "<claim-id> [--phase N] [--n-candidates N]"
context_mode: project-required
requires:
  files: [".grd/PROJECT.md"]
allowed-tools:
  - file_read
  - file_write
  - shell
---

<objective>
**This skill is not implemented yet.** It is a planned Phase 3 landing pad so
that `/grd:` autocomplete finds an explanatory page instead of a 404.

When shipped, `/grd:formalize-claim <claim-id>` will run the shipped 6-stage
autoformalization pipeline (extract → retrieve → generate → compile-repair →
faithfulness → gate, already in `src/grd/core/lean/autoformalize/`) against
a single contract claim and write the accepted Lean statement into the
phase blueprint as a stub lemma.

The CLI primitive (`grd lean verify-claim <claim-id>`) is already shipped
and does most of the work. The missing piece this skill adds is:

- Routing the accepted statement into `phases/{N}/blueprint/Proofs/*.lean`
  instead of just recording the verification evidence.
- Updating `content.tex` with the `\lemma{}…\lean{}` binding.
- On gate-escalation (faithfulness < 0.7), filing a `bd new -l human` bead
  with the specific ambiguity attached, per the Phase 3 policy.
</objective>

<status>
- **Phase:** 3 (AI-Assisted Proving) — see
  [PITCH §Phase 3](../../../research/formal-proof-integration/PITCH.md#phase-3-ai-assisted-proving-4-6-weeks).
- **Depends on:** blueprint scaffolding from `/grd:init-blueprint` (Phase 2).
- **Tracking bead:** file a new bead under ge-wisp-rnf6 when work starts.

See [STATUS.md](../../../research/formal-proof-integration/STATUS.md) for
the shipped/planned matrix.
</status>

<fallback>
The CLI primitive is usable today if you already have a Lean project:

```bash
grd lean verify-claim <claim-id> --json
```

It returns the accepted Lean statement (or the escalation reason) as JSON.
Dropping that into a Lean file manually gets you most of what this skill
will automate.
</fallback>
