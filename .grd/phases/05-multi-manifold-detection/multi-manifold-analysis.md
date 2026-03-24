# Multi-Manifold Detection and Cross-Sample Variation Analysis

## Problem Statement

Given activation vectors from a neural network layer across multiple input conditions (samples), we want to:

1. **Decompose** each sample's activation space into constituent manifold substructures
2. **Match** manifolds across samples (which manifold in sample A corresponds to which in sample B?)
3. **Score variation** to identify which manifolds change most across conditions
4. **Characterize** the varying manifolds in detail

The key constraint: this must work with N ~ 10²-10⁴ points per sample, in ambient dimension D ~ 10²-10⁴, with unknown number of manifolds k and unknown intrinsic dimensions d₁, ..., d_k that may differ across manifolds.

---

## Stage 1: Multi-Manifold Decomposition

### 1.1 Why SMCE Is the Right Starting Point

The core problem is: given a point cloud X = {x₁, ..., x_N} ⊂ ℝ^D that lies on a **union** of manifolds M₁ ∪ ... ∪ M_k, assign each point to its manifold.

**SMCE (Elhamifar & Vidal 2011)** solves this by exploiting a geometric insight: if x_i lies on a d-dimensional manifold, its **sparsest** reconstruction from other points will use ~d+1 neighbors, and those neighbors will come from the **same manifold** — because using points from a different manifold requires more coefficients (the combined space has higher dimension).

**The optimization problem:**

For each point x_i, solve:

    minimize ‖c_i‖₁ + λ‖e_i‖₁
    subject to x_i = Σ_{j≠i} c_{ij} x_j + e_i

where c_i is the sparse coefficient vector and e_i captures noise. The diagonal constraint c_{ii} = 0 prevents the trivial solution.

In matrix form for all points simultaneously:

    minimize ‖Z‖₁ + λ‖E‖₁
    subject to X = XZ + E, diag(Z) = 0

where Z is the N×N coefficient matrix.

**Why sparsity separates manifolds:**

Consider two manifolds M₁ (dimension d₁) and M₂ (dimension d₂) in ℝ^D. A point x on M₁ can be reconstructed from d₁+1 nearby points on M₁ (they span the local tangent space). To reconstruct x using points from M₂ instead, you'd need points that span a subspace containing x — but since M₂ has different geometry, this requires more points (the reconstruction is less sparse). The ℓ₁ penalty naturally selects the sparser (same-manifold) reconstruction.

**Recovery guarantee:** Under the "subspace independence condition" (manifolds' tangent spaces at nearby points are sufficiently separated in principal angles), the ℓ₁ relaxation provably recovers same-manifold neighbors. The coefficient matrix Z has **block-diagonal structure**: Z_{ij} ≠ 0 only when x_i and x_j are on the same manifold.

**Automatic dimension estimation:** The number of nonzero entries in c_i reflects the local dimension at x_i. A point on a 2D manifold typically gets ~3 nonzero coefficients; a point on a 30D manifold gets ~31. This is a critical feature — we don't need to specify dimensions in advance.

### 1.2 From Coefficients to Clusters

After solving for Z:

1. **Build affinity matrix:** W = |Z| + |Zᵀ| (symmetrize)
2. **Compute graph Laplacian:** L = D - W, where D = diag(Σ_j W_{ij})
3. **Spectral clustering:** Compute the bottom k eigenvectors of L, apply k-means
4. **Determine k:** The eigengap (largest jump in eigenvalues λ₁ ≤ λ₂ ≤ ...) indicates the number of manifolds. k = argmax_i (λ_{i+1} - λ_i) for the first significant gap.

### 1.3 Computational Cost for Mech Interp Regime

For N ~ 10⁴ points in D ~ 10³ dimensions:

| Step | Cost | Notes |
|------|------|-------|
| LASSO per point | O(N·D) per point | Coordinate descent with warm starts |
| All N points | O(N²·D) total | Parallelizable; N² ≈ 10⁸ at N=10⁴ |
| Affinity matrix | O(N²) | Sparse — most Z_{ij} = 0 |
| Spectral clustering | O(N·k²) | k eigenvectors of sparse Laplacian |
| **Total** | **O(N²D)** | ~10¹¹ ops for N=10⁴, D=10³ |

This is feasible on a single GPU in minutes. For N=10³ it's trivial (seconds).

**Practical speedup:** Pre-reduce D to D' ~ 50-100 via PCA before running SMCE. This preserves manifold structure (Johnson-Lindenstrauss) and reduces the LASSO cost to O(N²D').

### 1.4 Failure Modes and Mitigations

| Failure | When it happens | Mitigation |
|---------|----------------|------------|
| Under-segmentation | Manifolds too close (small principal angles) | Increase λ (stricter sparsity) |
| Over-segmentation | Noise or insufficient sampling | Decrease λ; merge clusters with similar local dimension |
| Intersection confusion | Manifolds cross | Use angle-constrained SMCE variant; flag intersection points by checking if they have neighbors in multiple clusters |
| Wrong k | Eigengap ambiguous | Use stability analysis: run for k, k±1, k±2 and check cluster consistency |

### 1.5 What SMCE Gives Us

For each sample, SMCE outputs:
- **Cluster assignment** σ: {1,...,N} → {1,...,k} mapping each point to its manifold
- **Local dimension** d̂_i for each point (from sparsity of c_i)
- **Manifold-specific point clouds** M̂_j = {x_i : σ(i) = j} for j = 1,...,k
- **Number of manifolds** k (from eigengap)

---

## Stage 2: Cross-Sample Manifold Matching

This is the hardest part. Given SMCE decompositions of two samples:
- Sample A: manifolds M_A1, ..., M_Ak with dimensions d_A1, ..., d_Ak
- Sample B: manifolds M_B1, ..., M_Bm with dimensions d_B1, ..., d_Bm

We need to determine: which M_Ai corresponds to which M_Bj? Note k may not equal m (a manifold might appear in one sample but not the other, or might split/merge).

### 2.1 The Descriptor Approach (Fast, Scalable)

Rather than directly comparing point clouds (expensive), summarize each manifold by a **descriptor vector** and match in descriptor space.

**Manifold descriptor v(M):**

For each manifold M̂_j, compute:

    v(M̂_j) = [d̂_j, β₀, β₁, β₂, σ₁², ..., σ_d², κ̄, vol, μ_center]

where:
- d̂_j = estimated intrinsic dimension (from SMCE sparsity)
- β₀, β₁, β₂ = Betti numbers from persistent homology (captures topology)
- σ₁², ..., σ_d² = eigenvalues of local covariance (captures shape)
- κ̄ = mean curvature estimate (from CA-PCA)
- vol = estimated manifold volume (sum of local volumes)
- μ_center = centroid in ambient space (captures location)

**Matching cost:** For manifolds from different samples, define:

    cost(M_Ai, M_Bj) = w_dim · |d_Ai - d_Bj| + w_topo · d_W(PD_Ai, PD_Bj) + w_spec · ‖σ_A - σ_B‖₂ + w_loc · ‖μ_A - μ_B‖₂

where d_W is the Wasserstein distance between persistence diagrams.

**Dimension filtering:** Immediately filter out pairs where |d_Ai - d_Bj| > 1. Manifolds of very different dimensions are unlikely to correspond.

**Assignment:** Build cost matrix C[i,j] = cost(M_Ai, M_Bj) and solve with the Hungarian algorithm (O(max(k,m)³) — trivial for k,m ~ 10-100).

**For k ≠ m:** Pad the smaller set with "null manifolds" at a fixed penalty cost c_null. If the optimal assignment matches M_Ai to a null manifold, that manifold has no counterpart in the other sample — it appeared or disappeared.

### 2.2 The Gromov-Wasserstein Approach (Rigorous, Expensive)

For manifolds that pass the descriptor filter but need precise comparison, use **Gromov-Wasserstein (GW) distance** — the gold standard for comparing metric spaces.

**GW distance between M_Ai and M_Bj:**

    GW(M_A, M_B) = min_π Σ_{x,x'∈M_A} Σ_{y,y'∈M_B} |d_A(x,x') - d_B(y,y')|² π(x,y) π(x',y')

where π is a coupling (joint distribution) with marginals matching the point distributions on M_A and M_B.

Intuitively: GW measures how different the **internal distance structures** are. Two manifolds are GW-close if you can find a correspondence that approximately preserves pairwise distances.

**Key property:** GW doesn't require the manifolds to live in the same ambient space. It compares intrinsic geometry only.

**Computational cost:** Exact GW is NP-hard. Practical approaches:
- **Entropic regularization (Sinkhorn):** O(N_A · N_B) per iteration, ~100 iterations. For N_A = N_B = 500 (subsample), this is fast.
- **Sliced GW:** O(m · N log N) via random 1D projections. Much faster but less precise.

**When to use GW vs descriptors:** GW is the refinement step. Use descriptors for initial matching (fast), then GW for the top-k candidates or ambiguous cases.

### 2.3 The Functional Maps Approach (Elegant, for Smooth Manifolds)

If manifolds are smooth and well-sampled, **functional maps** (Ovsjanikov et al.) provide an elegant correspondence:

1. Compute Laplace-Beltrami eigenfunctions φ₁, ..., φ_p on each manifold
2. Represent the correspondence as a p×p matrix C in eigenfunction space
3. C maps functions on M_A to functions on M_B: if f = Σ aᵢφᵢ^A, then the corresponding function on M_B is g = Σ (Ca)ᵢφᵢ^B

**For manifold matching (not point matching):** Compare eigenvalue spectra. Two manifolds with similar Laplacian eigenvalue sequences λ₁ ≤ λ₂ ≤ ... have similar intrinsic geometry. The spectrum is an isometry invariant.

**Cost:** O(Nkd) for eigenfunction computation (same as diffusion maps from Phase 1).

### 2.4 Recommended Matching Pipeline

```
For each pair of samples (A, B):
  1. Run SMCE on each → get manifolds M_A1..M_Ak, M_B1..M_Bm
  2. Compute descriptors v(M) for each manifold        [O(N²D) per manifold for PH]
  3. Dimension filter: eliminate pairs with |d_Ai - d_Bj| > 1
  4. Build cost matrix from descriptor distances         [O(k·m) — trivial]
  5. Hungarian algorithm for optimal assignment           [O(max(k,m)³) — trivial]
  6. For ambiguous matches (cost_best / cost_second < 1.5):
     refine with entropic GW on subsampled manifolds    [O(l² · iterations) per pair]
  7. Output: matching σ: {1..k} → {1..m} ∪ {∅}
```

---

## Stage 3: Variation Scoring

### 3.1 The Variation Score

Given S samples and a manifold correspondence across all of them, we want to score each manifold by how much it varies.

Let M_j^{(s)} denote manifold j in sample s (using the matching from Stage 2). Define:

**Topological variation:**

    V_topo(j) = (1/S²) Σ_{s,s'} d_W(PD_j^{(s)}, PD_j^{(s')})

where d_W is the Wasserstein distance between persistence diagrams. This captures changes in topology (holes appearing/disappearing, loops forming/breaking).

**Geometric variation:**

    V_geom(j) = (1/S²) Σ_{s,s'} ‖σ_j^{(s)} - σ_j^{(s')}‖₂ / ‖σ_j^{(s)}‖₂

where σ_j^{(s)} is the eigenvalue spectrum of the local covariance of manifold j in sample s. This captures changes in shape (stretching, compression, curvature changes).

**Dimensional variation:**

    V_dim(j) = Var_s(d̂_j^{(s)})

This captures whether the manifold's intrinsic dimension changes across samples (a strong signal).

**Combined variation score:**

    V(j) = w₁ V_topo(j) + w₂ V_geom(j) + w₃ V_dim(j)

Rank manifolds by V(j). The top-scoring manifolds are the ones that vary most across conditions.

### 3.2 Statistical Significance

To determine if a manifold's variation is significant (not just noise):

**Permutation test:** For each manifold j:
1. Pool all sample points assigned to manifold j across all samples
2. Randomly re-partition into S groups of the same sizes
3. Compute V(j) on the permuted partition
4. Repeat B = 1000 times
5. p-value = fraction of permutations where V_perm ≥ V_observed

**Persistence landscape approach (Bubenik 2015):** Vectorize persistence diagrams as persistence landscapes, then apply standard multivariate statistics:

    λ_j^{(s)}(t) = persistence landscape of manifold j in sample s

These live in L² (a Hilbert space), so we can compute means, variances, and apply Hotelling's T² test:

    T² = S · (λ̄_A - λ̄_B)ᵀ Σ̂⁻¹ (λ̄_A - λ̄_B)

This has a known null distribution, giving principled p-values.

### 3.3 Computational Cost of Variation Scoring

For S samples, k manifolds per sample, N_j points per manifold:

| Step | Cost | Notes |
|------|------|-------|
| PH per manifold | O(N_j³) or O(N_j² log N_j) with Ripser | Run on subsampled manifolds if N_j > 10³ |
| Wasserstein distance per pair | O(n² log n) where n = diagram size | n typically 10-100 features |
| All pairs across S samples | O(S² · k · n² log n) | For S=10, k=20, n=50: trivial |
| Eigenvalue spectra | O(k · N_j · D · d) | From local PCA, already have this |
| Permutation test | O(B · S² · k · n² log n) | B=1000, parallelizable |

**Bottleneck:** Persistent homology on individual manifolds. Mitigate by subsampling to N_j ~ 500 per manifold (preserves topology with high probability per Niyogi-Smale-Weinberger).

---

## Stage 4: Targeted Characterization

For the top-V manifolds identified in Stage 3, do deep analysis.

### 4.1 Parametrization

Apply diffusion maps (α=1) to each high-variation manifold individually:

1. Build k-NN graph on M̂_j (the manifold's point cloud)
2. α-normalize to remove density effects
3. Compute d_j eigenvectors → embedding coordinates
4. Diffusion distance captures intrinsic geometry independent of activation frequency

**Why diffusion maps here:** The density independence (α=1) is critical. In neural network activations, some feature values are activated far more often than others (common words vs rare words). Without density correction, the "geometry" you see is really the "geometry of the training distribution." Diffusion maps separate these.

### 4.2 JMS Heat Triangulation for Rigorous Local Coordinates

For manifolds where distance guarantees matter:

1. Select d reference points via local PCA directions
2. Set time parameter t = c · R² (R = local scale from k-NN distances)
3. Compute heat kernel map: x → (R^d K_t(x, y₁), ..., R^d K_t(x, y_d))
4. This is bi-Lipschitz on local patches — distances are provably preserved

### 4.3 Cross-Sample Alignment

For a manifold that exists in both sample A and sample B, align the parametrizations:

1. Compute functional maps (Laplacian eigenfunctions) on both copies
2. Find the correspondence matrix C that maps eigenfunctions across samples
3. Use C to transfer coordinates: "this point in sample A corresponds to that point in sample B"
4. Visualize what changed: which regions of the manifold moved, stretched, or deformed?

### 4.4 Interpretation

For each high-variation manifold, produce:

1. **Dimension report:** d̂ across samples, whether it changes
2. **Topology report:** Betti numbers, persistence diagrams across samples
3. **Geometry report:** Diffusion map embedding colored by sample, showing how the manifold deforms
4. **Feature identification:** Which input features (tokens, pixels, etc.) activate points on this manifold? This connects the geometric analysis back to interpretable features.

---

## Full Pipeline Summary

```
INPUT: S samples of activation vectors, each N ~ 10²-10⁴ in ℝ^D

[PREPROCESSING]
  PCA reduce D → D' ~ 50-100                              O(N·D·D')

[STAGE 1: DECOMPOSE]                                       O(N²D') per sample
  For each sample s = 1..S:
    Run SMCE → k_s manifolds with dimensions d̂₁..d̂_{k_s}
    Determine k_s from eigengap

[STAGE 2: MATCH]                                            O(k²·N_j³) total
  Compute manifold descriptors (dim, topology, spectrum)
  Build cost matrices between all sample pairs
  Hungarian assignment → manifold correspondence across samples
  Refine ambiguous matches with entropic GW

[STAGE 3: SCORE]                                            O(S²·k·n²log n)
  For each matched manifold j:
    Compute V(j) = variation score (topological + geometric + dimensional)
    Permutation test → p-value
  Rank by V(j), select top-K

[STAGE 4: CHARACTERIZE]                                     O(N_j·k_j·d_j) per manifold
  For each top-K manifold:
    Diffusion maps (α=1) → density-independent coordinates
    JMS heat triangulation → bi-Lipschitz local coordinates (if rigorous bounds needed)
    Cross-sample functional map alignment → visualize deformations
    Feature identification → connect to interpretable inputs

OUTPUT:
  - Ranked list of manifolds by variation score with p-values
  - For each top manifold: dimension, topology, aligned parametrizations, feature IDs
```

---

## Complexity Summary for the Full Pipeline

For S = 10 samples, N = 10⁴ points each, D = 10³ ambient, D' = 100 reduced, k ~ 20 manifolds, N_j ~ 500 per manifold:

| Stage | Operation | Cost | Wall time estimate |
|-------|-----------|------|-------------------|
| Preprocess | PCA | 10 × O(10⁴ · 10³ · 100) | < 1 min |
| Stage 1 | SMCE × 10 samples | 10 × O(10⁸ · 100) | ~10 min (GPU) |
| Stage 2 | PH per manifold (200 manifolds) | 200 × O(500³) | ~5 min |
| Stage 2 | Descriptors + Hungarian | trivial | < 1 sec |
| Stage 3 | Wasserstein distances | O(10² · 20 · 50² · log 50) | < 1 sec |
| Stage 3 | Permutation tests | O(1000 × above) | ~10 sec |
| Stage 4 | Diffusion maps on top-10 | 10 × O(500 · 20 · 5) | < 1 sec |
| **Total** | | | **~15-20 min** |

This is entirely tractable. The bottleneck is SMCE (Stage 1), and it's parallelizable across samples.

---

## What's New Here

The individual components (SMCE, persistence diagrams, Wasserstein distance, diffusion maps, functional maps) all exist. What's new is the **combination into a pipeline specifically designed for the multi-manifold mech interp problem**, with:

1. **SMCE as the decomposition engine** — automatic dimension estimation + manifold separation, solving the "we don't know how many manifolds there are or what dimensions they have" problem

2. **Multi-level descriptors for matching** — combining dimension, topology, and spectrum into a single cost function, with dimension filtering as a fast pre-screen and GW as a rigorous refinement

3. **Persistence-landscape-based variation scoring** — principled statistical testing (Hotelling's T²) on vectorized topological summaries, giving actual p-values for "this manifold varies significantly"

4. **The density-independence insight for Stage 4** — using α=1 diffusion maps specifically because neural network activation frequencies are non-uniform, ensuring the geometry we measure is the feature geometry, not the training distribution geometry

### Open Questions Remaining

1. **SMCE stability across samples:** If manifold structure is similar across samples, SMCE should find similar k with similar dimensions — but there's no formal guarantee of this. Cluster correspondence may be fragile.

2. **Intersection handling:** If two feature manifolds intersect (share some activation patterns), SMCE may misassign intersection points. The angle-constrained variant helps but isn't proven for the neural network activation regime.

3. **Choosing λ in SMCE:** The sparsity parameter λ controls the granularity of decomposition. Too small → one big manifold. Too large → every point is its own cluster. There's no principled way to set λ for neural activations specifically.

4. **Manifold birth/death across samples:** When a manifold exists in some samples but not others, the matching (Stage 2) handles this via null assignment. But detecting a **partially present** manifold (exists in 7 of 10 samples) requires a softer framework.

5. **Scale of variation:** The combined variation score V(j) has arbitrary weighting (w₁, w₂, w₃). What's the right balance of topological vs geometric vs dimensional variation for mech interp applications? This likely needs empirical calibration.
