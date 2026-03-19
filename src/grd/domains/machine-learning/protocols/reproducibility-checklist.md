# Reproducibility Checklist Protocol

## Purpose
Ensure ML experiments can be reproduced by others.

## Checklist

### Code and Environment
- [ ] Pin all dependency versions (requirements.txt or lock file)
- [ ] Record Python/CUDA/cuDNN versions
- [ ] Version control all code (including scripts and configs)
- [ ] Document hardware (GPU model, memory, number of devices)

### Data
- [ ] Document data source, version, and download procedure
- [ ] Record preprocessing steps with exact parameters
- [ ] Save train/val/test split indices or random seed used to generate them
- [ ] Document any data filtering or cleaning applied

### Training
- [ ] Set and record all random seeds
- [ ] Log full hyperparameter configuration
- [ ] Save training curves (loss, metrics per epoch)
- [ ] Record wall-clock training time and compute cost

### Evaluation
- [ ] Report results with confidence intervals or standard deviations
- [ ] Run multiple seeds (minimum 3, ideally 5+)
- [ ] Use identical evaluation protocol for all baselines
- [ ] Save model checkpoints for best and final models

## Convention Lock Fields
- `random_seed_policy`, `precision_format`, `evaluation_metric`
