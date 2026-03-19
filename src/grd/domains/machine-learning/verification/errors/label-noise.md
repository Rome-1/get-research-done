# Label Noise Errors

## Description
Incorrect or inconsistent labels in training data corrupt model learning.

## Symptoms
- Model confidence is low even on "easy" examples.
- Loss plateaus at a higher-than-expected value.
- Manual inspection reveals mislabeled training examples.

## Common Causes
- Crowdsourced annotations without quality control.
- Automated labeling with imperfect heuristics.
- Ambiguous labeling guidelines leading to inconsistent annotations.
- Data pipeline bugs that shuffle or misalign labels.

## Prevention
- Use label smoothing to reduce sensitivity to noise.
- Implement confident learning to identify and correct mislabeled data.
- Measure inter-annotator agreement.
- Audit random samples from each class regularly.
