---
load_when:
  - "SAE project"
  - "sparse autoencoder project"
  - "dictionary learning project"
  - "feature dictionary project"
tier: 2
context_cost: medium
---

# Project Template: Sparse Autoencoder (SAE) Project

A template for structuring a mechanistic interpretability project centered on training and analyzing sparse autoencoders.

## Project Structure

```
sae-project/
├── README.md                    # Project overview, conventions, key results
├── .grd/
│   └── conventions.yaml         # Locked conventions for this project
├── configs/
│   ├── sae_config.yaml          # SAE architecture and training hyperparameters
│   └── eval_config.yaml         # Evaluation settings
├── data/
│   ├── activations/             # Cached model activations (generated)
│   └── datasets/                # Evaluation datasets
├── src/
│   ├── collect_activations.py   # Activation collection from target model
│   ├── train_sae.py             # SAE training loop
│   ├── evaluate_sae.py          # Compute fidelity, sparsity, dead features
│   ├── interpret_features.py    # Feature analysis pipeline
│   └── steer.py                 # Feature steering experiments
├── notebooks/
│   ├── 01_exploration.ipynb     # Initial activation statistics
│   ├── 02_training.ipynb        # Training monitoring and Pareto frontiers
│   ├── 03_interpretation.ipynb  # Feature analysis results
│   └── 04_steering.ipynb        # Causal validation via steering
├── results/
│   ├── checkpoints/             # SAE model checkpoints
│   ├── metrics/                 # Training and evaluation metrics
│   └── feature_cards/           # Per-feature interpretation cards
└── docs/
    └── decisions.md             # Architecture and hyperparameter decisions
```

## Conventions to Lock

```yaml
# .grd/conventions.yaml
model_family: transformer
activation_space: residual-stream        # or learned-basis after SAE
hook_point_convention: transformer-lens  # or nnsight
layer_indexing: zero-indexed
sae_architecture: topk-sae              # or relu-sae, gated-sae, jumprelu-sae
sae_normalization: centered             # or none, layer-norm
feature_density_metric: firing-rate
```

## Phase 1: Setup and Activation Collection

**Goal:** Collect activations from the target model for SAE training.

### Checklist

- [ ] Select target model and hook point. Document rationale.
- [ ] Choose activation dataset (corpus, token count, diversity).
- [ ] Collect activations and save to disk.
- [ ] Compute activation statistics: mean, std, distribution shape.
- [ ] Verify activation dimensions match expected model architecture.

### Key Decisions

| Decision | Options | Considerations |
|----------|---------|----------------|
| Hook point | resid_pre, resid_post, mlp_out, attn_out | resid_post is most common; mlp_out isolates MLP computation |
| Layer | early, mid, late, all | Start with one mid layer; scale to all layers later |
| Dataset | OpenWebText, Pile, domain-specific | Diverse corpus for general SAE; domain corpus for specialized |
| Token count | 10M (experimental), 100M (standard), 1B+ (production) | More tokens = more reliable features but longer collection |

## Phase 2: SAE Training

**Goal:** Train SAEs with good sparsity-fidelity tradeoff.

### Checklist

- [ ] Select SAE architecture and expansion factor.
- [ ] Set initial hyperparameters (LR, L1/k, batch size).
- [ ] Train with monitoring: MSE, L0, dead features, explained variance.
- [ ] Address dead features (resampling, architecture change, lower L1).
- [ ] Train 3-5 SAEs at different sparsity levels for Pareto frontier.
- [ ] Select operating point on Pareto frontier. Document rationale.
- [ ] Compute loss recovered metric for selected SAE.

### Key Metrics

| Metric | Target | Red Flag |
|--------|--------|----------|
| Explained variance (R²) | >0.95 | <0.90 |
| Dead feature fraction | <10% | >30% |
| Loss recovered | >85% | <70% |
| L0 (active features/token) | 20-100 for 16x expansion | >200 (not sparse) or <5 (too sparse) |

## Phase 3: Feature Interpretation

**Goal:** Understand what the SAE features represent.

### Checklist

- [ ] Sample 50 random active features for quality assessment.
- [ ] For each: collect top-20 max-activating and 20 random-activating examples.
- [ ] Assign labels with confidence scores (high/medium/low).
- [ ] Run control: check for polysemanticity in each feature.
- [ ] Compute automated interpretability scores (if using auto-interp).
- [ ] Generate feature cards for all analyzed features.
- [ ] Report aggregate statistics: fraction monosemantic, interpretable, polysemantic.

## Phase 4: Causal Validation

**Goal:** Verify features have causal roles, not just correlational patterns.

### Checklist

- [ ] Select 10-20 features with clear interpretations for steering.
- [ ] Amplification: add k× decoder direction, observe behavioral change.
- [ ] Suppression: clamp feature to zero, observe behavioral change.
- [ ] Compare: does steering effect match the interpretation?
- [ ] Use features in activation patching to validate importance for specific tasks.
- [ ] Report steering success rate (fraction of features where steering matches interpretation).

## Deliverables

1. **Trained SAE checkpoint** with metadata (architecture, hyperparameters, training data).
2. **Feature catalog**: interpretations for sampled features with confidence scores.
3. **Pareto frontier plot**: L0 vs loss recovered for all trained SAEs.
4. **Steering results**: causal validation for top features.
5. **Project report**: decisions, methodology, results, limitations.
