# Pythia Training Dynamics: SAE Hyperplane Arrangement Evolution

**Experiment:** ge-plx  
**Date:** 2026-04-01  
**Model:** Pythia-70m-deduped (154 checkpoints, steps 0–143,000)  
**SAE probe:** `pythia-70m-deduped-res-sm`, layer 3 `hook_resid_post` (32,768 features, d_in=512)  
**Approach:** Fixed final SAE as geometric reference frame applied to each training checkpoint

---

## Key Findings

### Finding 1: Phase transition at step ~113,000 — SAE alignment

`var_explained` first turns positive at **step 113,000** (+0.41), after being negative for all prior steps. This is a sharp transition: step 112,000 = -0.124, step 113,000 = +0.413. The SAE probe goes from explaining *less* than the mean to explaining *more*.

**Interpretation:** The model's activation geometry first aligns with the trained SAE's feature structure at step 113,000 (~79% of training). Prior to this, activations exist in a structurally incompatible space.

Var_explained trajectory (selected):
| Step | var_exp | L0 |
|---|---|---|
| 0 | -10,577 | 27,808 |
| 8 | -6,489 | 25,386 |
| 32 | **-2.7** | **96** ← anomaly |
| 128 | -6,284 | 12,718 |
| 2,000 | -124 | 6,563 |
| 80,000 | -173 | 4,535 |
| 100,000 | -1.8 | 385 |
| 113,000 | **+0.41** | 163 ← **first positive** |
| 143,000 | +0.65 | 94 |

### Finding 2: Anomalous step-32 spike

At step 32, `var_explained` collapses from -6489 (step 8) to **-2.7** (near-zero) and L0 drops from 25,386 to **96** — then rebounds to -6,284 at step 128. This non-monotonic behavior suggests a transient "pseudo-sparse" phase during early training where the model briefly organizes into near-SAE structure before reorganizing.

Steps 32 and 64 also have ~96% dead features (31,594/32,768), much higher than surrounding steps.

### Finding 3: Convexity and linearity are stable throughout training

**This is the most striking finding.** Across all 154 checkpoints:

- **Convexity:** mean=0.896, std=0.018, range [0.860, 0.952]  
- **Boundary linearity:** mean=0.976, std=0.011, range [0.945, 0.996]

The polyhedral cone structure (convex feature regions, linear boundaries = hyperplanes) is present from the earliest steps where it can be measured (~step 16), and remains stable throughout training. The *alignment* between activations and specific features changes dramatically; the *geometric form* does not.

**Implication for the polyhedral cone hypothesis:** Hyperplane arrangement structure is not *learned* during training — it is a structural property of the ReLU SAE architecture. The geometry is always polyhedral; what training produces is the *specific assignment* of directions.

### Finding 4: Intrinsic dimension increases during training

Two-NN intrinsic dimension of activation space:
- Early (steps 0–64): **3.4** (low-dimensional)
- Mid (steps 1,000–10,000): **5.4–5.6**
- Late (steps 80,000–143,000): **5.8–6.4**

The activation space expands in intrinsic dimension as training progresses, consistent with the model developing richer, more varied representations. This correlates with the SAE alignment phase transition.

### Finding 5: L0 trajectory reveals three regimes

1. **Chaos (steps 0–8):** L0 ≈ 25,000–28,000 (nearly all 32k features fire per token)
2. **Transient collapse (steps 32–64):** L0 ≈ 96–159 (anomalous sparsity)
3. **Dense mid-training (steps 128–80,000):** L0 ≈ 5,000–15,000
4. **Convergence (steps 80,000–143,000):** L0 monotonically decreasing from 4,535 → 94

---

## Limitations

1. **Fixed SAE probe bias:** The SAE was trained on the final model. Negative `var_explained` at early steps doesn't mean no structure — it means the structure differs from the final model's. A proper per-checkpoint SAE would separate "SAE quality" from "activation alignment."

2. **Layer 3 only:** We measured one layer. Training dynamics may differ significantly across layers.

3. **Single model size:** Pythia-70m is small. Phase transitions at different scales are unknown.

---

## Next Steps (ge-plx continues)

1. **Per-checkpoint SAEs (ideal):** Train fresh SAEs on a subset of checkpoints (steps 0, 32, 64, 1000, 10000, 50000, 113000, 143000) to separate architecture-driven geometry from alignment.

2. **Capability emergence correlation:** Overlay published Pythia-70m capability benchmarks (arithmetic, ICL) against the step-113,000 alignment transition. Does capability emerge at the same time the SAE alignment happens?

3. **Multiple layers:** Run the same pipeline on layers 0, 1, 2, 4, 5 to see if the step-113,000 transition is layer-specific or global.

4. **Step-32 anomaly investigation:** What happens at step 32? Is this a known training artifact for Pythia-70m?

---

## Methods

- Modal parallel execution: 154 T4 GPU containers run simultaneously (~5 min wall time)
- 1,000 tokens per checkpoint from a mixed corpus (positional, numeric, syntactic text)
- Metrics: SAE reconstruction variance explained, L0 sparsity, dead feature count, Two-NN intrinsic dimension, feature region convexity (top-20 features), boundary linearity
- Code: `research/geometry_analysis/modal_pythia_dynamics.py`
- Raw results: `outputs/pythia_dynamics/full_results.json`
