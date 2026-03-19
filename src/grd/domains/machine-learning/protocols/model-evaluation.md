# Model Evaluation Protocol

## Purpose
Rigorous and fair evaluation of model performance.

## Steps

1. **Define metrics** — Choose primary and secondary metrics. Justify choices.
2. **Prepare test data** — Ensure test set is representative and unseen during training.
3. **Run inference** — Use final model checkpoint. Record inference settings.
4. **Compute metrics** — Report with confidence intervals across multiple seeds.
5. **Compare baselines** — Use identical evaluation setup for all methods.
6. **Statistical testing** — Apply appropriate significance tests when claiming improvement.

## Common Pitfalls
- Cherry-picking the best run instead of reporting mean across seeds.
- Using different preprocessing for model vs baselines.
- Reporting metric on a non-representative test set.
- Claiming improvement without statistical significance testing.
- Comparing with outdated or improperly reproduced baselines.

## Convention Lock Fields
- `evaluation_metric`, `data_split_strategy`, `precision_format`
