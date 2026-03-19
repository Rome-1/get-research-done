# Data Leakage Errors

## Description
Information from outside the training set improperly influences model training.

## Symptoms
- Suspiciously high validation/test performance.
- Model performs much worse on truly unseen data in production.
- Features that shouldn't be predictive show high importance.

## Common Causes
- Preprocessing fitted on full dataset before train/test split.
- Temporal leakage: future data used to predict past events.
- Target leakage: features derived from or correlated with the label.
- Duplicate samples appearing in both train and test sets.

## Prevention
- Always split before preprocessing.
- Use pipeline abstractions that enforce fit-on-train-only.
- Audit feature engineering for target leakage.
- Deduplicate data before splitting.
