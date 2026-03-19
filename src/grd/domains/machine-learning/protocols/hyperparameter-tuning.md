# Hyperparameter Tuning Protocol

## Purpose
Systematic hyperparameter optimization with proper experimental controls.

## Steps

1. **Define search space** — List all hyperparameters, their ranges, and scale (linear/log).
2. **Choose search strategy** — Grid, random, Bayesian, or population-based.
3. **Fix evaluation protocol** — Use consistent validation set/metric throughout.
4. **Run search** — Log all configurations and results. Track compute budget.
5. **Analyze sensitivity** — Identify which parameters matter most.
6. **Validate** — Evaluate best configuration on held-out test set exactly once.

## Common Pitfalls
- Tuning on test set (use validation set only).
- Ignoring interaction effects between hyperparameters.
- Reporting best validation score rather than test score.
- Not accounting for variance across random seeds.

## Convention Lock Fields
- `optimizer`, `lr_schedule`, `regularization`, `evaluation_metric`
