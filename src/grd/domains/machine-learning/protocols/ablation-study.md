# Ablation Study Protocol

## Purpose
Isolate the contribution of individual components to overall model performance.

## Steps

1. **Identify components** — List all architectural choices, loss terms, augmentations, etc.
2. **Define baseline** — Full model with all components enabled.
3. **Design ablations** — Remove or replace one component at a time.
4. **Control variables** — Keep hyperparameters, seeds, and data identical across runs.
5. **Run experiments** — Train each ablation with multiple seeds.
6. **Report results** — Table with mean and std for each ablation.

## Common Pitfalls
- Ablating multiple components simultaneously (confounds contributions).
- Not re-tuning hyperparameters when removing a component.
- Ignoring interaction effects between ablated components.
- Insufficient seeds to distinguish signal from noise.

## Convention Lock Fields
- `random_seed_policy`, `evaluation_metric`, `data_split_strategy`
