# Phase 1 Diagnostic Results: SMCE vs K-Means Parity Investigation

**Date:** 2026-03-30 | **Model:** GPT-2 Small (117M) | **N:** 500 tokens/condition
**Runtime:** All diagnostics on Modal T4 GPU | **Code:** `modal_run_diag_{a,b,c}.py`

---

## Background

Phase 1 token-manifold attribution showed SMCE manifold labels had significant MI with token types, passing the go/kill gate. However, the hardened gate (adding k-means baseline + NMI) revealed that **SMCE finds clusters with near-identical MI to k-means** at layer 6. Three diagnostics were run to determine where (if anywhere) SMCE outperforms naive clustering.

---

## Diagnostic A: PCA Linearization Test

**Question:** Does PCA 768→100 destroy curved manifold geometry, making SMCE equivalent to k-means?

**Method:** Run SMCE + k-means on PCA-reduced (100-dim) vs raw (768-dim) activations at layer 6.

### Results

| Condition | Token Type | PCA SMCE | PCA k-means | PCA Δ | Raw SMCE | Raw k-means | Raw Δ |
|---|---|:--:|:--:|:--:|:--:|:--:|:--:|
| positional | position_bucket | 0.037 | 0.037 | 0% | 0.566 | 0.586 | -3% |
| positional | token_frequency | 0.067 | 0.067 | 0% | 0.004 | 0.089 | -95% |
| numeric | is_number | 0.036 | **0.003** | **+1058%** | 0.039 | 0.039 | 0% |
| numeric | position_bucket | 0.196 | **0.017** | **+1075%** | 0.212 | 0.212 | 0% |
| numeric | token_frequency | 0.157 | **0.013** | **+1132%** | 0.174 | 0.174 | 0% |
| syntactic | position_bucket | 0.247 | 0.247 | 0% | 0.231 | **0.017** | **+1275%** |
| syntactic | token_frequency | 0.168 | 0.168 | 0% | 0.154 | **0.010** | **+1385%** |
| syntactic | punctuation | 0.016 | 0.016 | 0% | 0.015 | **0.001** | **+1301%** |

**PCA significant:** 3/12 (all numeric) | **Raw significant:** 4/12 (mostly syntactic)

### Verdict: PCA_IS_THE_PROBLEM (partially)

PCA doesn't simply destroy manifold structure — it **relocates** the SMCE advantage. With PCA, SMCE beats k-means on numeric text. Without PCA, SMCE beats k-means on syntactic text. This suggests:

1. PCA linearization preserves the geometric structure of numeric processing (number tokens) but flattens syntactic structure
2. Raw-dim preserves syntactic geometry but flattens the numeric advantage (possibly because k-means improves on high-dim numeric data)
3. Neither setting shows universal SMCE advantage — the advantage is condition-specific and dimension-dependent

**Implication:** The SMCE advantage is real but fragile. It depends on the preprocessing choice. This argues for nonlinear dimensionality reduction (UMAP, diffusion maps) that could preserve geometry across conditions.

---

## Diagnostic B: Multi-Layer Sweep

**Question:** Is the SMCE/k-means parity specific to layer 6, or universal across layers?

**Method:** Run SMCE + k-means at layers 0, 3, 6, 9, 11.

### Results

| Layer | k (pos/num/syn) | Significant | Avg MI(SMCE-km) | Best Condition |
|:--:|---|:--:|:--:|---|
| 0 | — | ERROR | — | Eigenvalue convergence failure |
| 3 | 2/2/2 | 3/12 | +0.028 | Numeric (+1050-1132%) |
| 6 | 2/2/3 | 3/12 | +0.028 | Numeric (+1050-1132%) |
| 9 | 2/3/3 | 2/12 | -0.031 | Positional (+58%) |
| 11 | 2/3/4 | 5/12 | -0.053 | Numeric (+8-462%) |

### Key Observations

1. **Manifold count increases with depth:** k grows monotonically for syntactic (2→2→3→3→4) and numeric (2→2→2→3→3). Positional stays at k=2. Deeper layers have more computational specialization.

2. **SMCE advantage peaks at early-mid layers (3/6) and diminishes at depth.** At layers 9 and 11, k-means often beats SMCE (negative avg delta). The manifold geometry that SMCE captures exists in early-mid network, not in late layers.

3. **Layers 3 and 6 show identical MI values.** Same numeric SMCE advantage, same exact values. This is suspicious — could indicate genuine partition stability or a subtle bug (filed as ge-XXX). Explained variance differs (0.999 vs 0.997).

4. **Late layers (11) have more significant tests (5/12) but negative average delta.** K-means improves faster than SMCE at deeper layers, possibly because late-layer activations are more linearly separable (pre-logit space).

5. **Layer 0 is degenerate** — raw embeddings don't have enough structure for spectral clustering.

### Verdict: SMCE advantage is layer-dependent and concentrated in early-mid network

---

## Diagnostic C: Computational Classifiers

**Question:** Do manifolds group tokens by computational state (what the model is DOING), not just input properties?

**Method:** Add three computational classifiers — logit entropy, attention entropy, prediction accuracy — on arithmetic, cloze, and syntactic text.

### Results

| Condition | Classifier | Type | MI(SMCE) | MI(km) | Δ | Significant |
|---|---|---|:--:|:--:|:--:|:--:|
| arithmetic | is_number | standard | 0.004 | 0.004 | 0% | No |
| arithmetic | position_bucket | standard | 0.014 | 0.014 | 0% | No |
| arithmetic | logit_entropy | **comp** | 0.003 | 0.003 | 0% | No |
| arithmetic | attention_entropy | **comp** | 0.006 | 0.006 | 0% | No |
| arithmetic | prediction_correct | **comp** | 0.001 | 0.001 | 0% | No |
| cloze | position_bucket | standard | **0.287** | 0.023 | **+1145%** | **Yes** |
| cloze | token_frequency | standard | **0.219** | 0.014 | **+1452%** | **Yes** |
| cloze | punctuation | standard | 0.012 | 0.001 | +1313% | **Yes** |
| cloze | logit_entropy | **comp** | 0.005 | 0.003 | +79% | No |
| cloze | attention_entropy | **comp** | 0.000 | 0.003 | -91% | No |
| cloze | prediction_correct | **comp** | 0.000 | 0.001 | -98% | No |
| syntactic | all tests | both | — | — | 0% | No |

**Standard:** 3/13 significant | **Computational:** 0/9 significant

### Verdict: Computational classifiers add nothing

1. **Computational classifiers (logit entropy, attention entropy, prediction accuracy) show zero SMCE advantage anywhere.** K-means captures computational state as well as or better than SMCE.

2. **Arithmetic text shows perfect SMCE/k-means parity** on all 8 classifiers (standard + computational). This is the most predictable text type — the model finds one dominant processing mode.

3. **Cloze text shows strong SMCE advantage on standard classifiers** (+1145-1452%) but not computational ones. SMCE captures how tokens *look* (position, frequency) differently from k-means, but not what the model *does* with them.

4. **Syntactic text shows total parity** — consistent with Diagnostic A (PCA setting).

---

## Synthesis: What the Diagnostics Tell Us

### The manifold hypothesis is not falsified, but it's on life support

| Finding | Implication |
|---|---|
| SMCE advantage is real but relocates with PCA | Geometry is there, but standard preprocessing obscures it |
| SMCE advantage concentrated in early-mid layers | Late layers are linearly separable; manifold structure exists in mid-network |
| Computational classifiers show no SMCE advantage | Manifolds don't capture computational routing better than k-means |
| SMCE advantage is condition-specific | Not a universal property of transformer activations |

### Three possible conclusions

1. **Manifold structure exists but SMCE is the wrong tool.** The sparse reconstruction approach may not distinguish manifold geometry from cluster geometry. A method that directly estimates curvature (e.g., UMAP graph, diffusion maps) might show a clearer signal.

2. **GPT-2 Small is too small.** 768-dim, 12 layers, 117M params — this model may not have enough superposition pressure to create curved manifolds. Gemma 2 2B (2304-dim, 26 layers) is a better test.

3. **The thesis is wrong at this level.** Transformer activations may organize into linearly separable clusters, not curved manifolds. K-means captures the structure because the structure IS linear.

### Recommended next step for ge-9df (Phase 1 rethink)

Before declaring the thesis alive or dead:
1. **Try nonlinear dim reduction:** Replace PCA with UMAP or diffusion maps as preprocessing, then re-run SMCE vs k-means.
2. **Run on Gemma 2 2B:** Test whether larger model with more superposition pressure shows clearer manifold structure.
3. **Direct curvature estimation:** Instead of SMCE→k-means MI comparison, directly measure local curvature of activation space and test whether high-curvature regions correspond to meaningful token-type boundaries.

---

## Appendix: Technical Notes

- **N=500** was used for computational feasibility. The N=2000 main results use PCA and show the same parity at layer 6.
- **Attribution-only pipeline** (`run_attribution_only`) was used for Diagnostic A to avoid O(N³) persistent homology on 768-dim data.
- **Layer 0 failure** is expected — token embeddings before any transformer block are too uniform for spectral clustering.
- **Layers 3/6 identical results** need investigation (bead filed).
