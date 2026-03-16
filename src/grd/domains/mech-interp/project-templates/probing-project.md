---
load_when:
  - "probing project"
  - "probe project"
  - "representation analysis project"
  - "diagnostic classifier project"
tier: 2
context_cost: medium
---

# Project Template: Probing Project

A template for structuring a mechanistic interpretability project focused on probing neural network representations to understand what information is encoded at different layers.

## Project Structure

```
probing-project/
├── README.md                    # Project overview, hypotheses, key results
├── .grd/
│   └── conventions.yaml         # Locked conventions for this project
├── configs/
│   └── probe_config.yaml        # Probe architecture, layers, hyperparameters
├── data/
│   ├── labeled_data/            # Input text with target labels
│   ├── activations/             # Cached activations per layer (generated)
│   └── splits/                  # Train/val/test splits
├── src/
│   ├── collect_activations.py   # Extract activations at all layers
│   ├── probes.py                # Probe architectures (linear, MLP)
│   ├── train_probe.py           # Training loop with cross-validation
│   ├── controls.py              # Random-label and selectivity controls
│   ├── causal_validation.py     # Ablation experiments to validate probing
│   └── visualize.py             # Accuracy-by-layer plots
├── notebooks/
│   ├── 01_dataset.ipynb         # Dataset construction and statistics
│   ├── 02_probing.ipynb         # Main probing results
│   ├── 03_controls.ipynb        # Control experiments
│   └── 04_causal.ipynb          # Causal validation
├── results/
│   ├── probes/                  # Trained probe checkpoints
│   ├── metrics/                 # Accuracy, selectivity per layer
│   └── figures/                 # Visualization outputs
└── docs/
    ├── hypotheses.md            # What we expect to find and why
    └── report.md                # Final results and interpretation
```

## Conventions to Lock

```yaml
# .grd/conventions.yaml
model_family: transformer
activation_space: residual-stream
hook_point_convention: transformer-lens
layer_indexing: zero-indexed
tokenizer: gpt2-bpe                     # or sentencepiece, tiktoken
```

## Phase 1: Dataset Construction

**Goal:** Create a high-quality labeled dataset for probing.

### Checklist

- [ ] Define the target property precisely (what information are we probing for?).
- [ ] Define the label set (binary, multi-class, regression).
- [ ] Collect ≥2000 labeled examples (1000 train, 500 val, 500 test).
- [ ] Balance classes (within 2:1 ratio).
- [ ] Ensure diversity: varied sentence structures, vocabularies, domains.
- [ ] Ensure disjointness: test examples share no task-relevant tokens with train.
- [ ] Document: how labels were derived, any ambiguous cases, inter-annotator agreement.

### Dataset Quality Checks

| Check | Criterion | Action if Failed |
|-------|-----------|-----------------|
| Class balance | No class >60% of data | Undersample or collect more of minority class |
| Diversity | ≥5 distinct sentence templates | Add more templates |
| Disjointness | No test word appears in train | Re-split by word |
| Difficulty | Model accuracy on task >80% | Choose easier property or verify model knows this |

## Phase 2: Activation Collection

**Goal:** Extract and cache activations for all layers.

### Checklist

- [ ] Select layer positions to probe (all layers recommended).
- [ ] Select token position(s) to probe (subject token, last token, or all).
- [ ] Extract activations for all examples at all layers.
- [ ] Verify shapes: (n_examples, d_model) per layer.
- [ ] Save to disk with metadata (model, layer, position, dataset version).

## Phase 3: Probe Training

**Goal:** Train probes at all layers and evaluate accuracy.

### Checklist

- [ ] Choose probe architecture (linear recommended as default).
- [ ] Set training hyperparameters (optimizer, LR, regularization, epochs).
- [ ] Train one probe per layer using 5-fold cross-validation on train set.
- [ ] Evaluate on held-out test set.
- [ ] Record: accuracy ± standard error, balanced accuracy, per-class accuracy.

### Probe Architecture Selection

| Architecture | When to Use | Capacity Risk |
|-------------|-------------|---------------|
| Linear (logistic regression) | Default. Information is linearly readable. | Low — hard to overfit |
| MLP (1 hidden layer, 256 units) | When linear probe fails but information is expected | Medium — can memorize small datasets |
| MLP (2+ hidden layers) | Rarely justified for probing | High — likely measuring probe capacity |

## Phase 4: Control Experiments

**Goal:** Establish that probing results reflect representation quality, not probe capacity.

### Checklist

- [ ] **Selectivity control**: train probes on randomly permuted labels at each layer.
- [ ] Report selectivity = (real accuracy) - (random accuracy) per layer.
- [ ] **Complexity control**: compare linear vs MLP probe accuracy.
- [ ] If MLP >> linear: information is nonlinearly encoded (document this).
- [ ] If MLP ≈ linear: information is linearly readable (use linear results).
- [ ] **Minimum description length (MDL) probe** (optional): information-theoretic measure.

### Control Results Template

| Layer | Real Accuracy | Random Accuracy | Selectivity | Linear Acc | MLP Acc |
|-------|--------------|-----------------|-------------|------------|---------|
| 0     | X ± Y        | X ± Y           | X           | X          | X       |
| 1     | X ± Y        | X ± Y           | X           | X          | X       |
| ...   | ...          | ...             | ...         | ...        | ...     |

## Phase 5: Causal Validation

**Goal:** Verify that probed information is causally used by the model.

### Checklist

- [ ] Identify the layer with peak probing accuracy (the "emergence" layer).
- [ ] Mean-ablation experiment: ablate the peak layer and measure behavioral change.
- [ ] Does ablation impair the model's use of the probed information?
- [ ] If probing succeeds but ablation doesn't matter: information is present but unused.
- [ ] (Optional) Activation patching: patch the probed information specifically.
- [ ] Report: causal evidence agrees/disagrees with probing results at layer X.

### Interpretation Guide

| Probing Result | Causal Result | Interpretation |
|---------------|---------------|----------------|
| High accuracy | Ablation degrades behavior | Information is represented AND used |
| High accuracy | Ablation doesn't matter | Information is present but not used (byproduct) |
| Low accuracy | Ablation degrades behavior | Information is used but not linearly readable |
| Low accuracy | Ablation doesn't matter | Information is neither present nor used |

## Phase 6: Generalization Testing

**Goal:** Verify the probe generalizes beyond the training distribution.

### Checklist

- [ ] Test the trained probe on a held-out test set (Phase 3 test set).
- [ ] Test on a distribution-shifted test set (different domain, register, or style).
- [ ] Report both in-distribution and out-of-distribution accuracy.
- [ ] If OOD accuracy drops >20%: the probe learned distribution-specific features.

## Deliverables

1. **Accuracy-by-layer plot** with selectivity controls.
2. **Emergence analysis**: at which layer does the information first appear?
3. **Causal validation**: does the model use this information?
4. **Generalization report**: in-distribution vs out-of-distribution accuracy.
5. **Dataset and probes**: released for reproducibility.
