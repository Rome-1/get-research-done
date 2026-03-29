# Rationality Assumption Errors

## Description
Misapplying rationality models to AI agents that optimize differently than
classical homo economicus.

## Symptoms
- AI agents behave "irrationally" by classical standards but consistently exploit the mechanism.
- Predictions based on utility maximization fail because AI agents have context-dependent objectives.
- Strategies that are theoretically suboptimal for rational agents succeed for AI agents
  (e.g., exploring more, exploiting computational speed, using memory of past interactions).

## Common Causes
- Assuming AI agents maximize a fixed, known utility function.
- Conflating computational power with rationality — AI agents are powerful optimizers
  but may not be "rational" in the sense of having consistent, transitive preferences.
- Ignoring that LLM-based agents have stochastic behavior that changes with prompt/context.
- Not accounting for mesa-optimization: AI agents optimizing for proxies of the intended objective.

## Prevention
- Model AI agents with explicit strategy spaces and computational budgets, not utility functions.
- Test results against multiple agent architectures (RL, LLM, rule-based).
- Distinguish between optimization power and preference consistency.
- Analyze worst-case agent behavior, not just equilibrium behavior.
