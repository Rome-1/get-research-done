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

## 7. Supporting Literature

### Intrinsic Dimensionality in Transformers

Valeriani et al. (2023, arXiv 2302.00294) measured ID across transformer layers
using Two-NN. Key finding: **ID expands in early layers, contracts sharply in
middle layers, then plateaus.** Layer 6 of GPT-2 (mid-network) likely sits at
this compression point, which would explain why the geometry is low-dimensional
and linearly structured.

Song et al. (2025, arXiv 2503.22547) confirm effective models compress tokens
onto ~10-dimensional submanifolds. Viswanathan et al. (2025, arXiv 2501.10573)
show ID correlates with next-token prediction loss — higher-loss prompts occupy
higher-dimensional regions.

### SAE Feature Geometry at Scale

Li, Michaud, Baek et al. (2024, arXiv 2410.19750) "The Geometry of Concepts"
analyzed SAE features at three scales: (a) atomic parallelogram "crystals"
(man-woman-king-queen generalized), (b) spatial modularity (math/code features
form lobes), (c) global power-law eigenvalue spectrum steepest in middle layers.
This directly supports our polyhedral view — features have discrete, structured
spatial relationships.

Prieto et al. (2026, arXiv 2603.09972) show correlated features arrange by
co-activation patterns, creating semantic clusters and cyclical structures.
This explains our P3 result (independence ratio 2.29 — features are correlated,
not independent).

### Topology and Polyhedral Structure

Naitzat, Zhitnikov & Lim (2020, arXiv 2004.06093) showed networks simplify
topology layer-by-layer (Betti numbers → trivial). ReLU simplifies faster
than tanh. Trivial topology at layer 6 would confirm the cone/subspace
hypothesis: contractible point clouds = convex cones.

Liu et al. (2023, arXiv 2306.17418) connected ReLU polyhedral decomposition
to persistent homology — the dual graph of the polyhedral complex retains
enough structure for TDA despite being a coarse quantization.

Brandenburg, Loho & Montúfar (2024, arXiv 2403.11871) refined the tropical
geometry connection: the "activation polytope" normal fan captures classification
combinatorics. The classification fan's sublevel sets are subfans.

### Subspace Clustering in Activations

Vielhaben et al. (2022, arXiv 2203.06043) applied SSC directly to hidden
layer activations for concept discovery — defined concepts as low-dimensional
subspaces. When activations are already linearly structured (as ours are),
raw SSC should work without deep transformation.

---

## References

1. Elhage et al. (2022). "Toy Models of Superposition." Anthropic. arXiv 2209.10652.
2. Facco et al. (2017). "Estimating the intrinsic dimension of datasets by a minimal neighborhood information." Scientific Reports.
3. Montúfar et al. (2014). "On the Number of Linear Regions of Deep Neural Networks." NeurIPS. arXiv 1402.1869.
4. Zhang, Naitzat & Lim (2018). "Tropical Geometry of Deep Neural Networks." ICML. arXiv 1805.07091.
5. Elhamifar & Vidal (2013). "Sparse Manifold Clustering and Embedding." NeurIPS.
6. Valeriani et al. (2023). "Geometry of transformer representations." arXiv 2302.00294.
7. Song et al. (2025). "Dimensional reduction in transformers." arXiv 2503.22547.
8. Li, Michaud, Baek et al. (2024). "The Geometry of Concepts." arXiv 2410.19750.
9. Naitzat, Zhitnikov & Lim (2020). "Topology and geometry of deep ReLU networks." arXiv 2004.06093.
10. Liu et al. (2023). "ReLU polyhedral decomposition and persistent homology." arXiv 2306.17418.
11. Brandenburg, Loho & Montúfar (2024). "Real tropical geometry of neural networks." arXiv 2403.11871.
12. Prieto et al. (2026). "From Data Statistics to Feature Geometry." arXiv 2603.09972.
13. Vielhaben et al. (2022). "SSC for concept discovery." arXiv 2203.06043.
14. Chanin et al. (2024). "A is for Absorption." arXiv 2409.14507.
15. Viswanathan et al. (2025). "Geometry of tokens." arXiv 2501.10573.
16. Bereska et al. (2025). "Superposition as lossy compression." arXiv 2512.13568.
17. **Black et al. (2022). "Interpreting Neural Networks through the Polytope Lens." arXiv 2211.12312.** [MOST DIRECT PREDECESSOR — polytopes in GPT-2 MLPs, does NOT connect to SAEs]
18. **Hindupur et al. (2025). "Projecting Assumptions: The Duality Between SAEs and Concept Geometry." NeurIPS 2025. arXiv 2503.01822.** [Explicitly states ReLU/JumpReLU SAE receptive fields are half-spaces; TopK SAEs produce hyperpyramids; does NOT develop hyperplane arrangement composition]
19. **Balestriero & Baraniuk (2018). "A Spline Theory of Deep Networks." ICML 2018.** [Proves deep ReLU networks are spline operators tessellating input space via hyperplane arrangements — general theory, does NOT discuss transformers/SAEs]
20. Inglis (2024). "Sparse Features Through Time." [Pythia-70M, 20 checkpoints, feature matching]
21. Xu et al. (2024). "Tracking Feature Dynamics in LLM Training." [SAE-Track, semantic evolution]
22. Engels et al. (2025). "Feature manifolds and intrinsic dimension." [Feature manifold geometry]
23. Biderman et al. (2023). "Pythia: A Suite for Analyzing Large Language Models Across Training and Scaling." ICML 2023. arXiv 2304.01373.
