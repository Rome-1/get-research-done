# The Polyhedral Cone Hypothesis: A Theory of Residual Stream Geometry

**Status:** Hypothesis + experimental framework  
**Context:** Phase 1 falsified SMCE manifold decomposition; SAE features beat k-means +783%  
**Claim:** Transformer residual stream activations live on a union of polyhedral cones, not smooth manifolds

---

## 1. Background

Phase 1 diagnostics (ge-y3a parent) established:
- SMCE manifold decomposition performs no better than k-means for token routing
- SAE linear feature directions capture token-type structure that k-means misses (12/12 significant, +783%)
- This holds across layers (3-11), models (GPT-2, Gemma 2), and preprocessing (PCA, UMAP, diffusion maps)

The question: **why** is the geometry linear? And what *exactly* is its structure?

## 2. The Polyhedral Cone Hypothesis

### 2.1 Theorem (informal): ReLU SAEs induce a hyperplane arrangement

A Sparse Autoencoder with ReLU activation defines a function:

    f(x) = ReLU(W_enc · x + b_enc)

where W_enc ∈ R^{m×d} and b_enc ∈ R^m, with m >> d (overcomplete basis).

Each feature k defines a **half-space**:

    H_k^+ = {x ∈ R^d : w_k · x + b_k > 0}    (feature k active)
    H_k^- = {x ∈ R^d : w_k · x + b_k ≤ 0}     (feature k inactive)

The collection of hyperplanes {H_k = ∂H_k^+}_{k=1}^m partitions R^d into
at most Σ_{i=0}^d C(m,i) convex polytopes (regions), where each region
corresponds to a unique binary **sparsity pattern** σ ∈ {0,1}^m.

### 2.2 Consequences

**C1 (Feature regions are convex).** The set S_k = {x : f_k(x) > 0} = H_k^+ is a half-space, hence convex. Any intersection of feature support sets is also convex (intersection of half-spaces = polytope).

**C2 (Codimension-1 boundaries).** The boundary of each feature region is the hyperplane H_k, which has codimension 1 in R^d. Points near the boundary have one fewer "effective" dimension locally.

**C3 (Linear separability).** Any partition induced by a subset of features is linearly separable (it's a Boolean function of half-space indicators). This explains why k-means (which finds convex regions) can approximate SMCE: the regions ARE convex.

**C4 (Sparsity patterns as polytope faces).** Each token's SAE activation pattern σ = (1[f_1 > 0], ..., 1[f_m > 0]) identifies which polytope it lies in. The top1_feature label (argmax) is a coarsening: it groups all polytopes sharing the same dominant feature.

### 2.3 Why SMCE fails

SMCE (Sparse Manifold Clustering & Embedding) seeks curved manifold structure by solving sparse representation problems. In a polyhedral arrangement:

1. **Each polytope is locally flat** — SMCE's sparse codes reduce to the standard Lasso on a linear subspace, equivalent to what k-means finds.
2. **Polytope boundaries are sharp** (non-differentiable) — SMCE assumes smooth manifold transitions, so it treats boundaries as noise.
3. **The "manifolds" SMCE finds are unions of adjacent polytopes** — these have the same MI with token types as k-means clusters because they capture the same convex structure.

### 2.4 Why SAE features work

SAE feature labels are the **natural coordinates** of this arrangement:
- top1_feature identifies the face/region of the arrangement
- top3_bucket identifies a finer polytope classification
- These are discrete labels for a fundamentally discrete structure

The +783% improvement over k-means reflects that k-means in PCA space is an arbitrary clustering of a polytope arrangement, while SAE features ARE the arrangement's defining hyperplanes.

## 3. Experimental Predictions

The hypothesis makes testable predictions:

| Prediction | Test | Expected result |
|---|---|---|
| P1: Feature regions are half-spaces | Linear SVM on active/inactive | Accuracy ≈ 1.0 |
| P2: Boundaries have codimension 1 | Local PCA at boundary | ambient_dim - boundary_dim ≈ 1 |
| P3: Features intersect independently | Observed/expected intersection ratio | ≈ 1.0 |
| P4: Feature directions are near-orthogonal | Angle between encoder weights | >> 0 (in high dim, expect ~π/2) |
| P5: Intrinsic dimension varies spatially | Local PCA dimension map | Lower near polytope boundaries |
| P6: Sparsity patterns have polytope structure | Count unique patterns | << 2^k (constrained by d) |

## 4. Connection to Superposition Theory

Anthropic's "Toy Models of Superposition" (Elhage et al. 2022) showed that neural networks represent more features than dimensions by encoding features as non-orthogonal directions with interference managed by ReLU-like sparsity.

Our polyhedral hypothesis is the geometric dual of superposition:
- **Superposition view (feature space):** Features are overcomplete directions; sparsity ensures low interference
- **Polyhedral view (activation space):** The arrangement of feature hyperplanes partitions activation space into polytopes; each polytope is a "computational regime" where a specific sparse subset of features is active

The two views are equivalent: a point in polytope σ has features {k : σ_k = 1} active, which is exactly the sparse representation in the overcomplete basis.

### 4.1 Implications for interpretability

If the polyhedral hypothesis is correct:
1. **Feature activation boundaries are meaningful.** The transition w_k · x = b_k is where the model's "decision" about feature k is made. This is a linear decision surface in activation space.
2. **Feature interactions are geometric.** Two features that co-activate define a polytope face of codimension 2. The geometry of this face constrains how the features interact.
3. **Superposition resolution = polytope identification.** Finding the right SAE is finding the right hyperplane arrangement. Over/under-complete SAEs give too many/few hyperplanes.

## 5. What This Does NOT Explain

The polyhedral hypothesis describes the **SAE-level** geometry. It does not address:
1. **Why these particular hyperplanes?** The SAE training objective selects hyperplanes; the hypothesis doesn't predict which ones.
2. **Dynamics across layers.** Each layer has a different arrangement. The hypothesis doesn't describe how arrangements transform across layers.
3. **Non-ReLU structure.** Attention patterns, layer norms, and softmax introduce non-polyhedral geometry that the SAE basis may miss.
4. **The reconstruction gap.** SAEs have nonzero reconstruction error. The actual activation geometry includes a residual component not captured by the polyhedral arrangement.

## 6. Relationship to Tropical Geometry

The piecewise-linear structure of ReLU networks has a known connection to tropical geometry (Zhang et al. 2018, Montúfar et al. 2014). In this framework:

- ReLU networks compute tropical rational functions
- Decision boundaries are tropical hypersurfaces
- The number of linear regions grows polynomially with depth and exponentially with width

Our SAE hyperplane arrangement is a specific instance: the SAE encoder is a single-layer ReLU network, so it computes a tropical polynomial. The arrangement's polytopes are the linear regions of this tropical polynomial.

The key insight is that the **residual stream itself** may have tropical structure inherited from the transformer's computation. If each layer applies a piecewise-linear transformation (attention + MLP with ReLU/GELU), the residual stream at any point is a tropical rational function of the input embeddings. The SAE arrangement partially recovers this tropical structure.

---

## References

1. Elhage et al. (2022). "Toy Models of Superposition." Anthropic.
2. Facco et al. (2017). "Estimating the intrinsic dimension of datasets by a minimal neighborhood information." Scientific Reports.
3. Montúfar et al. (2014). "On the Number of Linear Regions of Deep Neural Networks." NeurIPS.
4. Zhang et al. (2018). "Tropical Geometry of Deep Neural Networks." ICML.
5. Elhamifar & Vidal (2013). "Sparse Manifold Clustering and Embedding." NeurIPS.
