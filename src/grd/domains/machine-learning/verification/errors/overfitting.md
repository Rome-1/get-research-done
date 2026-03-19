# Overfitting Errors

## Description
Model memorizes training data instead of learning generalizable patterns.

## Symptoms
- Training loss continues decreasing while validation loss increases.
- Large gap between training and validation metrics.
- Model performs well on training data but poorly on unseen data.

## Common Causes
- Insufficient training data relative to model capacity.
- Training for too many epochs without early stopping.
- Missing or insufficient regularization.
- Model architecture too complex for the task.

## Prevention
- Use early stopping based on validation metric.
- Apply regularization (dropout, weight decay, data augmentation).
- Monitor train/val gap throughout training.
- Consider simpler architectures or pre-trained models.
