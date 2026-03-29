# Equilibrium Assumption Errors

## Description
Applying equilibrium-based reasoning to systems that may not have equilibria,
have multiple equilibria, or never converge.

## Symptoms
- Model predictions diverge sharply from simulation outcomes.
- Results depend heavily on which equilibrium is "selected" but selection isn't justified.
- ACE simulations show cycling, chaos, or path-dependent outcomes where model predicts a point.
- Welfare calculations assume a steady state that doesn't exist.

## Common Causes
- Using DSGE models for inherently non-equilibrium phenomena (market crashes, innovation waves).
- Assuming convergence of learning algorithms without verifying convergence conditions.
- Applying Nash equilibrium when agents have unbounded strategy spaces or evolving objectives.
- Representative agent models that assume away the interaction effects that drive the phenomenon.

## Prevention
- Test for convergence explicitly in simulations before applying equilibrium analysis.
- Report transient dynamics and distributional outcomes.
- Use ergodic theory or time-average analysis for non-convergent systems.
- State convergence assumptions and test their sensitivity.
