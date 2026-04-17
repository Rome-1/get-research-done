---
load_when:
  - "publication round artifacts"
  - "referee response"
  - "revision round"
  - "round suffix"
type: publication-review-round-artifacts
tier: 2
context_cost: low
---

# Publication Review Round Artifacts

Canonical round-suffix and sibling-artifact contract for publication review rounds.

## Suffix Rule

- Round 1 uses `round_suffix=""`.
- Round `N` for `N >= 2` uses `round_suffix="-R{N}"`.
- Keep one suffix shared across every artifact emitted for that review or response round.

## Required Artifact Family

- Stage-review artifacts: `GRD/review/CLAIMS{round_suffix}.json`, `GRD/review/STAGE-reader{round_suffix}.json`, `GRD/review/STAGE-literature{round_suffix}.json`, `GRD/review/STAGE-math{round_suffix}.json`, `GRD/review/STAGE-physics{round_suffix}.json`, and `GRD/review/STAGE-interestingness{round_suffix}.json`.
- Final adjudication artifacts: `GRD/review/REVIEW-LEDGER{round_suffix}.json`, `GRD/review/REFEREE-DECISION{round_suffix}.json`, `GRD/REFEREE-REPORT{round_suffix}.md`, and `GRD/REFEREE-REPORT{round_suffix}.tex`.
- Response artifacts: `GRD/AUTHOR-RESPONSE{round_suffix}.md` and `GRD/review/REFEREE_RESPONSE{round_suffix}.md`.
- Proof artifact when theorem review requires it: `GRD/review/PROOF-REDTEAM{round_suffix}.md`.

## Consistency Rules

- `GRD/REFEREE-REPORT{round_suffix}.md` is the canonical source for round-scoped `REF-*` issue IDs.
- Do not mix suffixes from different rounds in one workflow run, ledger pair, or response set.
- Downstream response or packaging work stays fail-closed until the latest round's required artifact family is complete for the active manuscript.
