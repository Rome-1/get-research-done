# Mechanism Analysis Protocol

## Purpose
Systematic analysis of mechanism properties (incentive compatibility, efficiency,
individual rationality) under varying identity and rationality assumptions,
with particular attention to AI-agent attack surfaces.

## Steps

1. **State the mechanism** — Formally define the allocation rule and payment rule.
   Specify the type space and action space.
2. **State assumptions** — Lock `identity_model`, `agent_rationality`,
   `equilibrium_concept`, `information_structure`. Be explicit about what
   agents know and can do.
3. **Prove/verify classical properties** — Check IC, IR, efficiency, budget balance
   under standard assumptions. Reference existing results where applicable.
4. **Sybil stress test** — Analyze what happens when a single agent can:
   (a) appear as k agents, (b) coordinate bids across identities,
   (c) control a fraction f of all participants. Find the critical k or f
   where properties break.
5. **Computational agent test** — Analyze what happens when agents have:
   (a) unbounded strategy evaluation, (b) perfect memory of prior interactions,
   (c) access to market-wide statistics in real time.
6. **Adversarial robustness** — Test against the strongest attacker model
   consistent with the setting. Report minimum assumptions needed for
   mechanism properties to hold.
7. **Remediation** — If properties break, propose modifications (identity costs,
   rate limits, deposit requirements) and re-analyze.

## Common Pitfalls
- Proving IC under unique identity, then deploying where sybils are cheap.
- Assuming agents can't collude when they share an API provider.
- Treating the revelation principle as applicable without verifying type stability.
- Analyzing only the intended equilibrium, ignoring profitable deviations by AI agents.

## Convention Lock Fields
- `identity_model`, `agent_rationality`, `equilibrium_concept`,
  `information_structure`, `price_mechanism`, `welfare_criterion`
