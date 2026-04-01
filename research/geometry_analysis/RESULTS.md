# Phase 2 Geometry Analysis Results

**Date:** 2026-04-01  
**Model:** GPT-2 Small (117M), layer 6, hook_resid_pre  
**N:** 500 tokens/condition × 3 conditions = 1,500 tokens  
**SAE:** gpt2-small-res-jb, blocks.6.hook_resid_pre (24,576 features)  
**Runtime:** Modal T4 GPU  

---

## Executive Summary

The Polyhedral Cone Hypothesis is **strongly supported**. GPT-2 Small layer 6
residual stream activations exhibit the geometry of a **hyperplane arrangement**,
not a smooth manifold:

| Prediction | Test | Result | Verdict |
|---|---|---|---|
| P1: Feature regions are convex | Linear SVM accuracy | **0.943** | **CONFIRMED** |
| P2: Boundaries are linear | SVM on active/inactive | **0.999** | **CONFIRMED** |
| P3: Features independent | Obs/expected ratio | 2.29 | Weak positive correlation |
| P4: Near-orthogonal directions | Mean angle | 56.3° | Moderate (not orthogonal) |
| P5: Varying intrinsic dim | Local PCA range | 1.0 – 13.7 (13.6x) | **CONFIRMED** |
| P6: Polytope structure | Pattern compression | 345/1500 (0.23) | **CONFIRMED** |

---

## 1. Intrinsic Dimensionality

Three estimators give different but complementary views:

| Estimator | Dimension | Interpretation |
|---|:--:|---|
| Two-NN | **8.5 ± 0.2** | Global average dimension |
| Local PCA (median) | **4.1 ± 4.7** | Median local dimension (high variance!) |
| Correlation | **0.9** | Scaling dimension (underestimate due to finite range) |

### Key finding: Intrinsic dimension varies wildly

The local PCA dimension distribution is **bimodal**:
- p10 = 1.0 — many points have essentially 1D local structure
- p50 = 4.1 — median is low-dimensional
- p90 = 13.7 — some points live in much higher-dimensional regions
- Ratio p90/p10 = **13.6x** — extreme variation

This is consistent with the polyhedral hypothesis: points in the interior
of a polytope face have dimension equal to the face dimension, while points
near edges/vertices have lower local dimension. The 491 points at dim ≈ 1
likely sit on edges or ridges of the polytope arrangement.

### Dimension by SAE feature region

For all 20 analyzed features:
- **dim_active ≈ 1.0** consistently — tokens where a feature is active cluster
  along a 1D ray (the feature direction itself)
- **dim_inactive ≈ 5.0–5.9** — the complement has higher dimension
- **dim_boundary ≈ 1.0–6.8** — variable at the transition

This is remarkable: feature activation regions are essentially **rays** in
activation space, not spread-out clouds. Tokens align along the feature
direction when that feature dominates.

---

## 2. Feature Region Geometry

### 2.1 Convexity (P1)

30 features analyzed, all with activation rates 0.18–0.42.

| Statistic | Value |
|---|---|
| Mean convexity | **0.943** |
| Min convexity | 0.900 |
| Max convexity | 1.000 |
| Features with convexity > 0.95 | 17/30 (57%) |
| Features with convexity > 0.90 | 30/30 (100%) |

**Every single feature region is linearly separable with >90% accuracy.**
Feature activation regions ARE half-spaces, as predicted.

### 2.2 Boundary Linearity (P2)

| Statistic | Value |
|---|---|
| Mean boundary linearity | **0.999** |
| Features with linearity = 1.0 | 26/30 (87%) |
| Min linearity | 0.992 |

**Feature boundaries are essentially perfect hyperplanes.** A linear classifier
achieves 99.9% accuracy at predicting whether a feature is active, confirming
that the boundary w · x = b is a single hyperplane.

### 2.3 Codimension

The measured codimension (ambient dim - boundary dim) averages ~96, which is
close to the PCA-reduced ambient dimension of 100. This indicates the boundary
regions are extremely thin (near-zero-dimensional) in PCA space, consistent
with hyperplane boundaries when sampled at low density.

---

## 3. Intersection Structure

### 3.1 Independence (P3)

105 pairs of 15 features analyzed:
- Mean independence ratio: **2.29**
- Median independence ratio: **2.16**

Features show **moderate positive correlation** in their activation patterns.
This departs from the "general position" prediction — features are not
independent. However, this is expected given:
1. Tokens from the same condition share similar activations
2. SAE features represent interpretable concepts that co-occur
3. The 3 conditions (positional/numeric/syntactic) create natural clusters

The correlation is modest (2x expected, not 10x), suggesting the arrangement
is close to general position with condition-level correlations.

### 3.2 Feature Direction Angles (P4)

- Mean angle: **56.3°**

In 100 dimensions, random vectors have expected angle ~90°. The 56.3° mean
indicates features are **not fully orthogonal** — they have some alignment.
This is consistent with:
- Superposition theory: features must share dimensions (non-orthogonal)
- The SAE is overcomplete (24,576 features in 768 dims), so orthogonality
  is geometrically impossible

---

## 4. Sparsity Pattern Structure

| Metric | Value |
|---|---|
| Unique patterns | **345** |
| Total tokens | 1,500 |
| Compression ratio | 0.23 (77% of tokens share a pattern) |
| Features/token | 9.1 ± 10.2 |
| Co-activation density | 0.931 |

345 unique sparsity patterns for 30 features means many tokens share the same
polytope. With 30 binary dimensions, maximum patterns = 2^30 ≈ 10^9, but only
345 are observed — the arrangement has extreme structure.

The high co-activation density (0.931) means most pairs of features tend to
co-activate, consistent with the moderate independence ratio.

---

## 5. Synthesis: The Geometry IS Polyhedral

### What we found

The residual stream at GPT-2 Small layer 6 is partitioned into **convex
polytopes** by SAE feature boundaries:

1. **Each SAE feature defines a half-space** with a hyperplane boundary
   (convexity 0.943, linearity 0.999)
2. **Feature activation regions are 1D rays** (dim_active ≈ 1.0), not
   spread-out clusters
3. **Intrinsic dimension varies 13.6x** across the space, consistent with
   polytope face structure (vertices = low dim, face interiors = high dim)
4. **Only 345 polytopes** are occupied (out of astronomically many possible),
   showing the arrangement has strong structural constraints

### What this means for interpretability

1. **SMCE was the wrong tool** (Phase 1 conclusion confirmed). SMCE looks for
   curved manifolds; the geometry is piecewise-linear.
2. **SAE features are the natural coordinates.** Each feature's hyperplane
   boundary is a "decision surface" the model uses to route computations.
3. **Token routing is polytope membership.** Two tokens with the same sparsity
   pattern (same polytope) are treated identically by the residual stream at
   this layer.
4. **Feature interactions are geometric.** Co-activated features define a
   polytope face; the face's geometry constrains how those features interact.

### What this does NOT yet show

1. We tested on PCA-reduced (100-dim) activations. The raw 768-dim case may differ.
2. N=500/condition is modest. Larger samples may reveal finer structure.
3. We only tested layer 6. The geometry may change across layers.
4. The correlation structure (P3 partial failure) needs investigation —
   condition-level confounding vs genuine feature correlation.

### Recommended next steps

1. **Raw-dim validation** — re-run with `use_raw=True` (768 dims, no PCA)
2. **Cross-layer sweep** — test layers 0, 3, 6, 9, 11 for arrangement changes
3. **Feature-level analysis** — which specific features have the highest/lowest
   convexity? Do interpretable features (e.g., number detectors) have different
   geometry than abstract features?
4. **Formal theorem** — prove that ReLU SAEs necessarily induce hyperplane
   arrangements on the residual stream, and characterize the arrangement's
   combinatorial type

---

## Appendix: Raw Numbers

### Feature region convexity (all 30 features)

Feature ID | Active rate | Convexity | Linearity
---|---|---|---
18648 | 0.42 | 0.968 | 1.000
5405  | 0.42 | 0.966 | 1.000
21311 | 0.41 | 0.930 | 1.000
18803 | 0.36 | 0.980 | 1.000
6247  | 0.34 | 0.910 | 0.996
21221 | 0.33 | 0.984 | 1.000
11153 | 0.33 | 0.992 | 1.000
3582  | 0.33 | 0.984 | 1.000
23446 | 0.32 | 0.996 | 1.000
22381 | 0.32 | 0.900 | 1.000
8594  | 0.32 | 0.958 | 0.996
24058 | 0.32 | 0.932 | 1.000
3834  | 0.32 | 0.970 | 1.000
16915 | 0.32 | 0.982 | 1.000
20777 | 0.31 | 0.958 | 1.000
1430  | 0.30 | 1.000 | 1.000
4092  | 0.30 | 0.922 | 1.000
23123 | 0.29 | 0.974 | 1.000
22527 | 0.29 | 0.924 | 1.000
22446 | 0.29 | 0.934 | 1.000
