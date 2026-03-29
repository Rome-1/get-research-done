# Composition Fallacy Errors

## Description
Incorrectly assuming that aggregate (macro) behavior follows directly from
individual (micro) behavior, ignoring interaction effects, feedback loops,
and emergent phenomena.

## Symptoms
- Micro-level analysis predicts stability but aggregate system crashes.
- Individual agent rationality produces collectively irrational outcomes.
- Models miss herding, cascading failures, or liquidity spirals that only emerge from interaction.
- Representative agent results don't match heterogeneous agent simulations.

## Common Causes
- Using a representative agent to model populations where heterogeneity is the point.
- Summing individual welfare without accounting for interaction externalities.
- Ignoring that AI agents trained on similar data exhibit correlated behavior,
  amplifying systematic risk even without explicit coordination.
- Assuming market resilience scales linearly with number of participants.

## Prevention
- Always model interactions explicitly when agent behavior may be correlated.
- Use ABM to check whether micro-level predictions survive to the macro level.
- Test for emergent phenomena by gradually scaling population size.
- Report both individual and aggregate outcomes; flag any divergence.
