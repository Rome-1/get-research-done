---
load_when:
  - "circuit analysis project"
  - "circuit discovery project"
  - "circuit tracing project"
  - "reverse engineering project"
tier: 2
context_cost: medium
---

# Project Template: Circuit Analysis Project

A template for structuring a mechanistic interpretability project focused on discovering and understanding circuits in neural networks.

## Project Structure

```
circuit-analysis/
├── README.md                    # Project overview, task definition, key results
├── .grd/
│   └── conventions.yaml         # Locked conventions for this project
├── configs/
│   └── experiment_config.yaml   # Model, task, and patching configuration
├── data/
│   ├── clean_prompts.jsonl      # Clean input dataset
│   ├── corrupted_prompts.jsonl  # Corrupted input dataset (paired with clean)
│   └── test_prompts.jsonl       # Held-out test set
├── src/
│   ├── dataset.py               # Dataset construction and validation
│   ├── patching.py              # Activation patching infrastructure
│   ├── path_patching.py         # Path patching for edge discovery
│   ├── circuit.py               # Circuit representation and evaluation
│   ├── interpret.py             # Component interpretation
│   └── visualize.py             # Circuit visualization
├── notebooks/
│   ├── 01_task_validation.ipynb # Verify model performs the task
│   ├── 02_coarse_scan.ipynb     # Layer-level importance scan
│   ├── 03_fine_scan.ipynb       # Component-level patching
│   ├── 04_circuit.ipynb         # Circuit assembly and faithfulness
│   └── 05_interpretation.ipynb  # Mechanistic interpretation
├── results/
│   ├── patching/                # Patching result tensors
│   ├── circuits/                # Circuit specifications
│   └── figures/                 # Visualizations
└── docs/
    ├── task_spec.md             # Formal task specification
    └── circuit_report.md        # Final circuit description
```

## Conventions to Lock

```yaml
# .grd/conventions.yaml
model_family: transformer
patching_method: resample-ablation       # or denoising, zero-ablation
ablation_baseline: resample-ablation
logit_attribution_direction: logit-difference
hook_point_convention: transformer-lens
layer_indexing: zero-indexed
circuit_completeness_criterion: "recovers 90% of logit difference"
```

## Phase 1: Task Definition and Validation

**Goal:** Define the task precisely and verify the model performs it.

### Checklist

- [ ] Write a formal task specification (input format, expected output, metric).
- [ ] Define the metric: logit difference, probability, KL divergence.
- [ ] Construct clean dataset (≥100 examples where model succeeds).
- [ ] Construct corrupted dataset (paired with clean, differing only in task-relevant variable).
- [ ] Verify model accuracy on clean dataset (>90%).
- [ ] Verify model fails on corrupted dataset (metric near zero/chance).
- [ ] Split into train (80%) and test (20%) sets.

### Task Specification Template

```markdown
## Task: [Name]
**Input format:** [Template with variables]
**Expected output:** [What the model should predict]
**Metric:** [Logit difference between correct and incorrect token]
**Clean example:** [Specific example]
**Corrupted example:** [Same example with task variable changed]
**Model accuracy:** [X% on N examples]
```

## Phase 2: Coarse Localization

**Goal:** Identify which layers contain the circuit.

### Checklist

- [ ] Activation patching by entire layer (all heads + MLP at each layer).
- [ ] Plot layer importance heatmap (denoising and noising directions).
- [ ] Identify the 3-5 most important layers.
- [ ] Causal tracing: sweep (layer, position) pairs for restoration effect.
- [ ] Visualize causal trace heatmap.

## Phase 3: Component-Level Discovery

**Goal:** Identify individual heads and MLPs in the circuit.

### Checklist

- [ ] Patch individual attention heads within important layers (both directions).
- [ ] Patch individual MLPs within important layers (both directions).
- [ ] Rank components by effect size with confidence intervals.
- [ ] Test top-10 components: denoising AND noising effects.
- [ ] Test for interaction effects between top components.
- [ ] Path patching: identify edges between important components.
- [ ] (Optional) Decompose into SAE features for finer resolution.

### Component Importance Table

| Component | Denoising Effect | Noising Effect | Necessary? | Sufficient? |
|-----------|-----------------|----------------|------------|-------------|
| head L.H  | X ± Y           | X ± Y          | yes/no     | yes/no      |
| MLP L     | X ± Y           | X ± Y          | yes/no     | yes/no      |

## Phase 4: Circuit Assembly

**Goal:** Define the minimal faithful circuit.

### Checklist

- [ ] Assemble candidate circuit from Phase 3 components.
- [ ] Measure faithfulness: ablate everything outside the circuit.
- [ ] Report: circuit recovers X% of metric on train set, Y% on test set.
- [ ] Minimality check: remove each component one at a time, measure faithfulness drop.
- [ ] Remove components whose removal doesn't significantly reduce faithfulness.
- [ ] Report final circuit: N components out of M total (X% of model).
- [ ] Test for backup circuits: does ablating the circuit degrade to chance?

## Phase 5: Mechanistic Interpretation

**Goal:** Understand what each circuit component computes.

### Checklist

- [ ] For each attention head: What does it attend to? What does its OV circuit compute?
- [ ] For each MLP: What transformation does it apply? Feature analysis.
- [ ] Trace the information flow: which component produces what output and who reads it.
- [ ] Write a narrative: "The model performs this task by..."
- [ ] Verify the narrative with targeted interventions (if we change X, Y should change).

## Deliverables

1. **Circuit specification**: component list, edges, faithfulness metrics.
2. **Mechanistic narrative**: how the circuit implements the task.
3. **Visualization**: circuit diagram showing components and information flow.
4. **Faithfulness report**: train/test metrics, minimality analysis, backup circuits.
5. **Reproducibility package**: code, datasets, configs to reproduce all results.
