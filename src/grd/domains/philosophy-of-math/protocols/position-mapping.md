# Position Mapping Protocol

## Purpose
Systematically map the landscape of philosophical positions on a question in
philosophy of mathematics, identifying the logical space, live options, and
relationships between positions.

## Steps

1. **State the question precisely** — Formulate the philosophical question
   with sufficient precision to distinguish genuine disagreement from
   terminological variance. Example: "Do mathematical objects exist?" is too
   vague; "Are there abstract mathematical objects that exist independently
   of human minds and mathematical practice?" is better.
2. **Identify the dimensions of variation** — Most philosophical questions
   admit variation along multiple independent axes. For ontological questions,
   distinguish: existence (yes/no/deflationary), nature (abstract/structural/
   fictional), necessity (necessary/contingent/conventional), and access
   (causal/rational/stipulative).
3. **Populate the space** — For each major position, record:
   (a) Canonical formulation and primary advocates.
   (b) Core commitments — what the position must accept.
   (c) Core denials — what the position must reject.
   (d) Convention settings: lock `ontological_commitment`, `epistemic_stance`,
       `logic_system`, and other relevant fields.
4. **Map logical relationships** — Identify which positions are:
   (a) Mutually exclusive (cannot both be true).
   (b) Compatible (can be held together).
   (c) Related by entailment (one implies another).
   (d) Related by motivation (one historically led to another).
5. **Identify the dialectical pressure points** — What are the strongest
   objections to each position? Where does each position face its hardest
   problem? (Benacerraf's dilemma for platonism, indispensability for
   nominalism, identity problems for structuralism, etc.)
6. **Check for unstated assumptions** — Verify that the space is not
   artificially constrained by shared assumptions across positions. Example:
   the platonism-nominalism debate often assumes that the relevant notion of
   existence is univocal.
7. **Assess the state of the debate** — Is there convergence, stalemate, or
   active movement? Are new positions emerging? Is the question itself being
   dissolved or reformulated?

## Common Pitfalls
- Treating the space as exhausted by the most famous positions.
- Conflating positions that differ only terminologically with genuinely distinct views.
- Missing that some positions occupy the same logical space but differ in motivation.
- Letting one tradition's framing of the question exclude positions from other traditions.
- Failing to distinguish between what a position says and what its advocates happen to believe.

## Convention Lock Fields
- `ontological_commitment`, `epistemic_stance`, `logic_system`,
  `philosophical_tradition`, `historical_context`
