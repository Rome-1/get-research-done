# Multi-Layer Pythia Training Dynamics

**Experiment:** ge-341  
**Date:** 2026-04-01  
**Model:** Pythia-70m-deduped, layers 0, 3, 5 (pilot) / layers 0-5 (full)  
**SAEs:** `pythia-70m-deduped-res-sm`, one per layer (fixed, trained on final model)  
**Pilot:** 3 layers × 9 steps = 27 jobs on Modal T4  

---

## Key Finding: Alignment Transition is Layer-Dependent (and Non-Monotonic)

The SAE alignment transition follows a surprising, non-sequential order across layers:

| Layer | First positive var_exp | % of training | Notes |
|---|---|---|---|
| 1 | step 10,000 | **7%** | Earliest — then de-aligns! |
| 4 | step 99,000 | 69% | Near epoch boundary |
| 2 | step 103,000 | 72% | |
| 0 | step 113,000 | 79% | |
| 3 | step 113,000 | 79% | |
| 5 | step 143,000 | **100%** | Latest — barely aligns |

This is NOT a simple input→output wave. Layer 1 aligns 10x earlier than Layer 0.

### Layer-Specific Dynamics (Full 6-Layer Data)

**Layer 0 (embedding-adjacent):** Non-monotonic alignment.
- Near-zero at step 23k (-1.14), re-diverges to -209 at step 80k, re-aligns at step 113k.
- Convexity 0.886-0.931, ID 3.7→5.3.

**Layer 1:** Earliest alignment, then de-alignment.
- Aligns at step 10k (ve≈0.0) — far earlier than any other layer.
- Then LOSES alignment (ve goes to -10.6 at step 63k) before slowly re-aligning.
- Very high dead feature count throughout (21k-28k of 32k).
- Interpretation: Layer 1 develops basic token representations early that match the final SAE, but the rest of the network reorganizing around it causes de-alignment.

**Layer 2:** Standard late convergence.
- Deeply negative through mid-training, aligns at step 103k.
- Highest final convexity among inner layers (0.920).

**Layer 3 (middle):** Our original study target. Monotonic convergence.
- Deeply negative at step 23k (-2600). Steady approach to zero. Transitions at step 113k.

**Layer 4:** Most extreme initial divergence.
- var_exp starts at **-55,096** (step 0) — 5x worse than any other layer.
- This means Layer 4's initialization is maximally incompatible with its final SAE.
- Aligns at step 99k, near the epoch boundary.

**Layer 5 (output-adjacent):** Latest to align.
- var_exp WORSENS from -823 (step 23k) to -9000 (step 63k).
- Then rapidly improves: -1035 → -170 → -20 → +0.65.
- Does not align until the final checkpoint (step 143k).
- Interpretation: the output-adjacent layer is continuously reorganized throughout training.

---

## Cross-Layer Patterns

### Convexity is stable across ALL layers and training stages

| Layer | Convexity range | Final |
|---|---|---|
| 0 | 0.886 - 0.931 | 0.900 |
| 1 | 0.879 - 0.955 | 0.955 |
| 2 | 0.880 - 0.920 | 0.920 |
| 3 | 0.868 - 0.952 | 0.952 |
| 4 | 0.861 - 0.941 | 0.914 |
| 5 | 0.886 - 0.938 | 0.923 |

**Polyhedral structure is architectural, not learned or layer-specific.** Every layer, at every training stage, exhibits convex feature regions with linear boundaries. Convexity ranges 0.86-0.96 across all 120 (layer, step) pairs.

### Intrinsic dimension increases with depth

| Layer | Early ID | Late ID | Final ID |
|---|---|---|---|
| 0 | 3.7 | 5.3 | 5.1 |
| 1 | 3.6 | 5.9 | 5.4 |
| 2 | 3.4 | 7.0 | 6.4 |
| 3 | 3.4 | 6.4 | 5.8 |
| 4 | 3.4 | 6.8 | 6.7 |
| 5 | 3.3 | 7.4 | 6.9 |

Deeper layers develop progressively richer (higher-dimensional) representations. Layer 5 final ID (6.9) is 35% higher than Layer 0 (5.1).

### Step-32 anomaly across all layers

| Layer | Step-32 var_exp | Step-32 L0 | Dead % |
|---|---|---|---|
| 0 | -2249 | 5224 | 0.5% |
| 1 | -143 | 1322 | 15.6% |
| 2 | -4.1 | — | — |
| 3 | **-2.7** | **96** | **96.4%** |
| 4 | **-4.0** | **47** | **98.7%** |
| 5 | -8.9 | 273 | 94.7% |

The transient collapse is strongest in layers 3-4 (middle/deep) and weakest in layer 0. Layer 4 shows the most extreme collapse (L0=47, 98.7% dead). This suggests the collapse propagates from the middle outward, or that deeper layers are more sensitive during warmup.

---

## Interpretation: Non-Sequential Alignment Dynamics

The data reveals a richer picture than a simple wave:

1. **Layer 1 aligns earliest** (step 10k, 7%) — basic token representations match the final SAE very early, but this alignment is fragile and disrupted by network reorganization.

2. **Layers 2-4 align mid-to-late training** (steps 99k-113k, 69-79%) — these layers undergo the bulk of representational change during training.

3. **Layer 0 and Layer 5 align latest** (steps 113k-143k) — the "boundary" layers (closest to input/output) are most affected by ongoing reorganization of inner layers.

4. **Non-monotonic alignment is the norm**: Layers 0, 1, 4, and 5 all show periods where alignment improves then worsens before final convergence. Only layers 2 and 3 show approximately monotonic convergence.

5. **The epoch boundary (~step 99k) is a critical event**: 4 of 6 layers first go positive within 14k steps of the epoch boundary (steps 99k-113k). Second-pass exposure may trigger representational consolidation.

---

## Status

- [x] Pilot complete (3 layers × 9 steps)
- [x] Full run complete (6 layers × 20 steps = 120 GPU jobs)
- [x] Per-layer analysis
- [ ] Quantitative cross-layer correlation with capability data
