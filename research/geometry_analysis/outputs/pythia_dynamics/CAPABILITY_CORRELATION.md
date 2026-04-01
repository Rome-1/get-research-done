# Capability-Geometry Correlation: Pythia-70m-deduped

**Experiment:** ge-97d  
**Date:** 2026-04-01  
**Data sources:**  
- Geometry: 154-checkpoint SAE probe (ge-plx, this repo)  
- Capabilities: EleutherAI/pythia official zero-shot evals (20 checkpoints)  
- Benchmarks: LAMBADA, PIQA, ARC-Easy, ARC-Challenge, SciQ, WinoGrande, LogiQA, WSC  

---

## Key Finding: Geometry and Capability are Dissociated

The SAE alignment phase transition at step 113,000 does **not** correspond to
capability emergence. Instead, capabilities emerge much earlier (steps 1k-23k,
first 15% of training) while the geometric alignment transition occurs in the
final 21% of training, during a period of slight capability *degradation*.

### Correlation statistics (steps >= 1000, n=16):

| Metric pair | Pearson r | p-value | Direction |
|---|---|---|---|
| var_explained vs aggregate capability | **-0.451** | 0.079 | Negative |
| var_explained vs LAMBADA acc | -0.442 | 0.087 | Negative |
| var_explained vs SciQ acc | -0.448 | 0.082 | Negative |
| var_explained vs L0 | **-0.846** | <0.001 | Negative |

The **negative** correlation between SAE alignment and capability performance
means that as the model's representations become more geometrically compatible
with the final-model SAE, benchmark performance actually declines.

---

## Three-Phase Model of Training

### Phase 1: Capability Acquisition (steps 1k-23k, 1-16% of training)

- Capabilities rise rapidly: aggregate acc 0.25 -> 0.49
- LAMBADA: 0.00 -> 0.26, SciQ: 0.19 -> 0.68
- LAMBADA PPL: 3M -> 91 (massive improvement)
- var_explained stays deeply negative (-93 to -2600)
- L0 stays high (6,500-15,000)
- SAE sees the model as "geometrically incompatible"

### Phase 2: Capability Plateau & Geometric Divergence (steps 23k-99k, 16-69% of training)

- Capabilities plateau or slightly decline
- Best aggregate performance at step 43k (0.495)
- var_explained worsens from -2600 to -3.5 (slowly approaching zero)
- L0 decreases: 12,500 -> 539
- Dead features explode: 73 -> 25,911 (79%)
- Epoch boundary at ~step 99k (deduped Pile = 207B tokens)

### Phase 3: Geometric Consolidation (steps 99k-143k, 69-100% of training)

- var_explained crosses zero at step 113k (the "alignment transition")
- Capabilities continue slight decline: aggregate 0.45 -> 0.44
- LAMBADA PPL worsens: 121 -> 138
- L0 drops: 514 -> 94 (near-final sparsity)
- Dead features reach 91.2%
- Convexity improves: 0.897 -> 0.952

---

## Timeline: When Things Happen

| Event | Step | % Training | Epoch | var_exp | Agg acc |
|---|---|---|---|---|---|
| Random weights | 0 | 0% | 0.00 | -10,577 | 0.248 |
| Step-32 anomaly (transient sparsity) | 32 | 0% | 0.00 | -2.7 | 0.254 |
| First meaningful capabilities | 1,000 | 0.7% | 0.01 | -1,108 | 0.349 |
| Rapid capability growth | 3,000 | 2.1% | 0.03 | -93 | 0.434 |
| Peak LAMBADA acc | 23,000 | 16.1% | 0.23 | -2,600 | 0.490 |
| Peak aggregate capability | 43,000 | 30.1% | 0.44 | -2,414 | 0.495 |
| Peak SciQ acc | 53,000 | 37.1% | 0.54 | -1,709 | 0.491 |
| Rapid sparsification begins | 80,000 | 55.9% | 0.81 | -173 | 0.463 |
| **Epoch boundary** | **~99,000** | **69.0%** | **1.00** | -3.2 | 0.462 |
| **SAE alignment transition** | **113,000** | **79.0%** | **1.15** | **+0.41** | 0.448 |
| Final model | 143,000 | 100% | 1.45 | +0.65 | 0.445 |

---

## Interpretation

### 1. Capability acquisition is a rapid early event

The model acquires 90%+ of its final capability within the first 16% of training
(23k/143k steps). This is consistent with prior observations that language model
capabilities emerge during the initial rapid loss decrease phase.

### 2. The SAE alignment transition is a geometric consolidation event

The step-113k transition where var_explained first turns positive does NOT mark
capability emergence. Instead, it marks when the model's activation geometry
has *settled* into its final form sufficiently that a SAE trained on the final
model can reconstruct it. This is a statement about representational form, not
representational content.

### 3. Late training is dominated by geometric reorganization, not capability gain

Between step 23k and 143k (84% of total compute), the model gains <1% aggregate
accuracy while its geometric properties change dramatically:
- L0 drops from 12,500 to 94 (133x reduction)
- Dead features go from 0.3% to 91.2%
- var_explained goes from -2,600 to +0.65

The model spends most of training reorganizing HOW it represents information,
not WHAT information it represents.

### 4. Epoch boundary as a possible trigger

The epoch boundary (step ~99k) falls in the middle of the sparsification
window (steps 80k-113k). Seeing data for the second time may trigger
representation consolidation — the model can now "finalize" its feature
assignments because new information is no longer arriving.

### 5. Convexity is architectural, not learned (reinforced)

Convexity (0.877-0.952) and linearity (0.949-0.990) are stable across all
three phases. The polyhedral cone structure is a property of the ReLU SAE
architecture, present even when the SAE-model alignment is terrible
(var_explained = -10,577). Training does not create the hyperplane arrangement;
it selects which hyperplanes matter.

---

## Implications for the Paper

1. **Reframe the training dynamics narrative**: The paper should NOT claim that
   geometric structure "emerges" during training. Instead: the hyperplane
   arrangement is always present (architectural), but the model's representations
   gradually align with the specific arrangement of the final-model SAE.

2. **The stronger claim**: Capabilities are acquired in a geometrically unstable
   regime (Phase 1), then training spends 84% of compute consolidating
   representations without capability gain. This connects to the broader
   question of training efficiency.

3. **Epoch boundary as a natural experiment**: The deduped Pile's single-epoch
   + partial-second-epoch structure provides a natural experiment: does repeated
   data exposure trigger geometric consolidation?

4. **Caveat**: The negative correlation has p=0.079 (marginal). With only 16
   matched checkpoints, this should be reported as suggestive, not conclusive.
   Higher-resolution capability evals would strengthen the claim.

---

## Data

- Combined dataset: `capability_geometry_correlation.json` (20 matched checkpoints)
- Full geometry: `full_results.json` (154 checkpoints)
- Raw evals: EleutherAI/pythia repo, `evals/pythia-v1/pythia-70m-deduped/zero-shot/`
