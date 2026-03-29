# Argument Analysis Protocol

## Purpose
Systematic analysis of philosophical arguments about mathematics — their logical
structure, hidden premises, dialectical context, and relation to live positions
in the field.

## Steps

1. **Identify the argument's target** — What philosophical thesis is being
   defended or attacked? State it precisely. Lock `ontological_commitment`,
   `foundational_framework`, and `logic_system` to fix the context.
2. **Reconstruct the argument** — Extract the explicit premises and conclusion.
   Identify the logical form (deductive, abductive, transcendental, reductio).
   Lock `argument_style`.
3. **Surface hidden premises** — Check for unstated assumptions about logic
   (excluded middle? bivalence?), ontology (mathematical objects exist?),
   or epistemology (we have access to mathematical truths?). These are
   frequently the most philosophically loaded parts of the argument.
4. **Evaluate each premise** — For each explicit and hidden premise, assess:
   (a) Is it shared across positions, or does it beg the question?
   (b) What is the strongest objection to it?
   (c) Is there a weaker premise that would suffice?
5. **Check the inference** — Verify that the conclusion follows from the
   premises in the relevant logic. If the argument is abductive, assess
   whether the conclusion is indeed the best explanation. If transcendental,
   verify the necessity claim.
6. **Dialectical positioning** — Place the argument in the broader debate.
   Who is the intended opponent? Does the argument engage the strongest
   version of the opposing view (principle of charity)? What is the most
   compelling reply?
7. **Assess philosophical significance** — Even if the argument is valid,
   does it advance the debate? Does it depend on premises more controversial
   than the conclusion?

## Common Pitfalls
- Evaluating arguments from a rival tradition using assumptions from your own.
- Confusing formal validity (logic) with philosophical soundness (true premises).
- Treating thought experiments as decisive when they rely on contested intuitions.
- Missing that the argument's logic presupposes the very position being argued for.
- Ignoring the historical context that makes certain premises seem obvious.

## Convention Lock Fields
- `ontological_commitment`, `logic_system`, `argument_style`,
  `foundational_framework`, `philosophical_tradition`
