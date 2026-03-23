# Comparative Analysis of Manifold Detection Methods

## 1. Computational Complexity Comparison (ANAL-01)

### 1.1 Full Complexity Table

All complexities expressed as functions of: N (sample size), D (ambient dimension), d (intrinsic dimension), k (neighborhood size).

| Method | Time Complexity | Memory | Bottleneck Step |
|--------|----------------|--------|----------------|
| **Spectral Methods** | | | |
| Laplacian Eigenmaps | O(N log N · D + Nkd) | O(Nk) | k-NN graph construction |
| Diffusion Maps | O(N log N · D + Nkd) | O(Nk) | k-NN graph construction |
| JMS Heat Triangulation | O(N log N · D + Nkd) | O(Nk) | k-NN graph + heat kernel eval |
| Full eigendecomposition | O(N²D + N³) | O(N²) | Dense eigenvalue problem |
| **Geometric Methods** | | | |
| ISOMAP | O(N² log N + N²D) | O(N²) | All-pairs shortest paths |
| Landmark ISOMAP | O(Nl log l + NlD) | O(Nl) | Landmark shortest paths |
| LLE | O(N log N · D + Nk³D) | O(Nk) | Weight computation |
| LTSA | O(NkDd + Nd²) | O(Nk) | Local PCA + alignment |
| Local PCA (dim est.) | O(NkD) | O(Nk) | Local covariance computation |
| **Topological Methods** | | | |
| Persistent Homology (Rips) | O(N² D + n³) | O(N² + n) | Matrix reduction (n = simplices) |
| Persistent Homology (sparse Rips) | O(N²D + N³) | O(N) | Approximation with ε-nets |
| Mapper | O(N²D + N²/n_int) | O(N²) | Filter + clustering |

### 1.2 Scaling Behavior by Regime

**Small N (< 10⁴):**
All methods are practical. Choose based on theoretical guarantees, not computational cost.

| Method | Wall time @ N=10³, D=100, d=3 | Feasible? |
|--------|-------------------------------|-----------|
| Laplacian Eigenmaps | < 1s | Yes |
| Diffusion Maps | < 1s | Yes |
| ISOMAP | ~1s | Yes |
| LLE | < 1s | Yes |
| Persistent Homology (H₁) | ~10s | Yes |

**Medium N (10⁴ - 10⁶):**
O(N²) methods become bottleneck. Sparse spectral methods still efficient.

| Method | N=10⁵ feasible? | Limiting factor |
|--------|-----------------|-----------------|
| Sparse spectral (LE, DM, JMS) | **Yes** | k-NN construction |
| ISOMAP | No (10¹⁰ memory) | O(N²) distance matrix |
| Landmark ISOMAP (l=10³) | Yes | Landmark computation |
| LLE | Yes | Weight computation |
| Persistent Homology | No | O(N³) reduction |

**Large N (> 10⁶):**
Only sparse methods + approximations survive.

| Method | Scalable variant | Complexity | Guarantee preserved? |
|--------|-----------------|-----------|---------------------|
| Diffusion Maps + Nyström | O(Nl² + l³) | Yes | Approximate convergence |
| Random Fourier Features | O(NmD) | Yes | Kernel approximation only |
| Sparse Rips PH | O(N²D + N) simplices | Yes | (1+ε)-approximation |

### 1.3 Dependence on Ambient Dimension D

High ambient dimension D affects methods differently:

| Method | D-dependence | Impact |
|--------|-------------|--------|
| k-NN construction | O(D) per distance, but k-d trees degrade for D > ~20 | Need approximate NN (LSH, random projection trees) |
| ISOMAP | O(D) per distance | Moderate |
| Persistent Homology | O(D) per distance | Moderate |
| JMS Heat Triangulation | O(d) eigenfunctions needed, **independent of D** | **Best** |
| LLE | O(k³D) weights | Grows linearly with D |

**Key finding:** JMS heat triangulation's guarantee constants depend only on intrinsic dimension d, not ambient dimension D. This is a fundamental advantage for high-dimensional data (the typical case in neural network activation analysis, where D ~ 10²-10⁴).

---

## 2. Theoretical Guarantee Comparison (ANAL-02)

### 2.1 Guarantee Taxonomy

We classify guarantees into five properties:

1. **Bi-Lipschitz:** Both upper AND lower bounds on distance distortion
2. **Continuity:** Only upper bound (Lipschitz, not bi-Lipschitz)
3. **Convergence:** Approximation converges to true geometric quantity as N → ∞
4. **Stability:** Small input perturbation → small output perturbation
5. **Density independence:** Result independent of sampling density

### 2.2 Detailed Guarantee Comparison

| Method | Bi-Lipschitz | Convergence | Rate | Density-indep. | Noise robust | What is preserved |
|--------|-------------|-------------|------|---------------|-------------|-------------------|
| **JMS Heat Triang.** | **LOCAL YES** | **Deterministic** | N/A (exact bounds) | **Yes** | Moderate | Local Euclidean distances |
| Laplacian Eigenmaps | No | Yes | O(N^{-2/(d+4)}) | No | Moderate | Spectral geometry (Δ_M) |
| Diffusion Maps (α=1) | No | Yes | O(N^{-2/(d+4)}) | **Yes** | Moderate | Riemannian geometry (Δ_M) |
| Bi-stochastic normalization | No | Yes | Optimal rates | **Partial** | **Strong** | Weighted Δ_M |
| ISOMAP | No | Yes (convex only) | None formal | No | Weak | Geodesic distances |
| LLE | No | **No** | N/A | No | Weak | Local linearity |
| LTSA | No | Asymptotic | N/A | No | Moderate | Tangent space alignment |
| Local PCA | N/A | Yes | O(ε/τ + σ/ε) | N/A | Moderate | Tangent spaces, dimension |
| Persistent Homology | N/A (topological) | Yes | N/A | **Yes** | **Strong** | Topology (Betti numbers) |
| Mapper | N/A | Conditional | N/A | No | Weak | Reeb graph approximation |

### 2.3 The JMS Advantage: Quantified

The JMS heat triangulation theorem (Phase 1, Section 3) provides guarantees that no other method matches:

**Unique properties:**
1. **Bi-Lipschitz with explicit constants:** (c₂/R_z)‖x₁−x₂‖ ≤ ‖Φ(x₁)−Φ(x₂)‖ ≤ (c₃/R_z)‖x₁−x₂‖
2. **Dimension-optimal:** Only d eigenfunctions (or d reference points) needed
3. **Constants depend only on intrinsic geometry:** d, C_Weyl, metric smoothness — NOT on N, D
4. **Two equivalent realizations:** Eigenfunction map (Thm 1-2) or heat kernel map (Thm 3)
5. **No global eigendecomposition needed** for the heat kernel variant

**What other methods lack:**
- ISOMAP: Upper bound only (geodesic approximation), requires convexity, no lower bound
- Diffusion maps: Operator convergence but no explicit distance bounds between embedded points
- LLE: No geometric convergence at all
- Persistent homology: Topological, not metric — different kind of guarantee entirely

**Practical caveat:** JMS guarantees are LOCAL (on balls of radius O(R_z)). For global embedding, multiple local patches must be combined. This is analogous to how an atlas of charts covers a manifold — each chart is well-behaved, but the atlas construction adds complexity.

### 2.4 Noise Robustness Ranking

| Rank | Method | Mechanism |
|------|--------|-----------|
| 1 | Persistent Homology | Stability theorem; noise = short-lived features near diagonal |
| 2 | Bi-stochastic norm. | Explicit outlier robustness via doubly-stochastic normalization |
| 3 | Diffusion Maps (α=1) | Density normalization absorbs sampling noise |
| 4 | Laplacian Eigenmaps | Averaging in graph Laplacian provides moderate smoothing |
| 5 | JMS Heat Triangulation | Heat kernel is local average, but bounds may degrade near noise |
| 6 | Local PCA / LTSA | Noise inflates apparent dimension; requires noise level estimate |
| 7 | LLE | Noise disrupts local linear structure |
| 8 | ISOMAP | Single noisy edge can create short-circuit, corrupting global structure |
| 9 | Mapper | Clustering step sensitive to noise; filter function can amplify |

---

## 3. Efficient Approximations and Guarantee Preservation (ANAL-03)

### 3.1 Approximation Methods

| Approximation | Applicable to | Complexity | Memory |
|---------------|--------------|-----------|--------|
| Nyström method | Spectral methods | O(Nl² + l³) | O(Nl) |
| Random Fourier features | Shift-invariant kernels | O(NmD) | O(Nm) |
| Sparse k-NN graph | Graph-based methods | O(N log N · D) | O(Nk) |
| Approximate NN (LSH) | All k-NN-based | O(N^{1+1/c} D) | O(N) |
| Landmark ISOMAP | ISOMAP | O(Nl log l) | O(Nl) |
| Sparse Rips filtration | Persistent homology | O(N²D + Nε) | O(N) |
| Witness complexes | Persistent homology | O(l^{k+1}) | O(l²) |

### 3.2 Guarantee Preservation Under Approximation

**Critical question:** When we use scalable approximations, which theoretical guarantees survive?

| Method + Approximation | Original guarantee | Preserved? | What is lost? |
|----------------------|-------------------|-----------|---------------|
| Diffusion maps + Nyström | Convergence to Δ_M | **Partially** | Eigenvalue accuracy limited by l landmarks; convergence rate degrades |
| Spectral + Random features | Kernel approximation | **Partially** | Only Gaussian kernel approximated; eigenfunction relationship weakened |
| Spectral + Sparse k-NN | Convergence to Δ_M | **Yes** (if k sufficient) | Convergence rate may be slower than ε-graphs |
| JMS + Approximate NN | Bi-Lipschitz local coords | **Unknown** | Reference point accuracy affects bounds; no published analysis |
| ISOMAP + Landmarks | Geodesic approximation | **Partially** | Triangulation from landmarks introduces additional error |
| PH + Sparse Rips | Stability | **Yes** ((1+ε)-approx) | Persistence values approximate within multiplicative (1+ε) |
| PH + Witness complex | Stability | **Partially** | Dependent on landmark selection quality |

### 3.3 The Fundamental Tradeoff

**Theorem (informal):** No known scalable approximation (subquadratic in N) fully preserves bi-Lipschitz guarantees for spectral manifold embeddings.

This follows from:
1. Bi-Lipschitz requires precise local distance information
2. Subsampling (Nyström, landmarks) introduces O(ε_subsample) error that directly weakens the lower Lipschitz bound
3. Random features approximate the kernel but not the eigenfunction structure
4. Only sparse graph construction (k-NN) preserves the underlying operator convergence, but this is already the standard approach

**Implication for practice:** The best strategy is sparse k-NN graph construction (O(N log N · D)) which preserves operator convergence, combined with iterative eigensolvers (ARPACK/Lanczos) that compute only the needed d eigenvectors in O(Nkd) time. This combination scales to N ~ 10⁵-10⁶ without fundamentally compromising guarantees.

For N > 10⁶, Nyström approximation is the practical choice, accepting degraded (but still useful) spectral convergence.

---

## 4. Regime-Specific Recommendations (Decision Matrix)

### 4.1 By Problem Size (N)

| Regime | N range | Recommended method | Rationale |
|--------|---------|-------------------|-----------|
| Small | < 10⁴ | JMS heat triangulation or diffusion maps | Full guarantees affordable |
| Medium | 10⁴ - 10⁶ | Sparse diffusion maps (k-NN + Lanczos) | O(Nkd) with operator convergence |
| Large | 10⁶ - 10⁸ | Nyström diffusion maps | Degraded but practical |
| Very large | > 10⁸ | Random features + local PCA | Sacrifice guarantees for feasibility |

### 4.2 By Ambient Dimension (D)

| Regime | D range | Consideration | Recommended adjustment |
|--------|---------|--------------|----------------------|
| Low | D < 20 | k-d trees efficient | Standard sparse spectral methods |
| Moderate | 20 < D < 100 | k-d trees degrade | Use approximate NN (random projection trees) |
| High | 100 < D < 10⁴ | NN search dominates cost | LSH or random projection for neighbor search |
| Very high | D > 10⁴ | Random feature methods competitive | Random Fourier features for kernel approximation |

### 4.3 By Task Type

| Task | Primary method | Secondary/verification |
|------|---------------|----------------------|
| "Is there a manifold?" | Local PCA (dimension) + persistent homology | Diffusion maps eigenvalue decay |
| "What dimension is it?" | Local PCA (eigenvalue gap) | CA-PCA if high curvature suspected |
| "Give me coordinates" | JMS heat triangulation / diffusion maps | LTSA as comparison |
| "What is the topology?" | Persistent homology | Mapper for visualization |
| "What shape is it?" | Persistent homology + diffusion maps | Mapper for exploratory view |
| "Efficiently at scale" | Sparse diffusion maps + Nyström | Local PCA for dimension pre-screening |

### 4.4 For Mechanistic Interpretability Specifically

Neural network activation spaces have characteristic properties:
- **D ~ 10² - 10⁴** (hidden layer width)
- **d ~ 1 - 50** (expected feature manifold dimension, based on recent work)
- **N ~ 10³ - 10⁶** (number of activation vectors from input samples)
- **Multiple manifolds** may coexist in the same space
- **Noise** from training dynamics and input variation

**Recommended pipeline:**
1. **Dimension screening:** Local PCA on random subsets → estimate d, check for manifold structure
2. **Manifold parametrization:** Diffusion maps with α=1 (density-independent, handles non-uniform activation density)
3. **Topological validation:** Persistent homology on the embedding to verify manifold topology
4. **Scale exploration:** Vary diffusion time t to identify structure at different scales (coarse features vs fine structure)
5. **If theoretical rigor needed:** JMS heat triangulation for bi-Lipschitz local coordinate systems

---

## 5. Summary of Key Findings

### Finding 1: Spectral Methods Win for Parametrization
Among all surveyed methods, spectral methods (diffusion maps, JMS heat triangulation) provide the best combination of theoretical guarantees and computational efficiency for manifold parametrization. No geometric method approaches the JMS bi-Lipschitz guarantee.

### Finding 2: The Efficiency Frontier
The Pareto frontier of guarantee strength vs. computational cost contains exactly three methods:
1. **JMS heat triangulation** — strongest guarantees (bi-Lipschitz), same cost as other spectral methods
2. **Diffusion maps (α=1)** — operator convergence + density independence, same O(Nkd) cost
3. **Persistent homology** — strongest topological guarantee (stability), higher cost O(N³) but answers a different question

All other methods are dominated: ISOMAP by spectral methods (weaker guarantees, higher cost), LLE by Laplacian eigenmaps (no convergence, same cost), Mapper by persistent homology (weaker guarantees, similar cost).

### Finding 3: Scalability is Solved for Medium N
Sparse graph construction + iterative eigensolvers scale spectral methods to N ~ 10⁵-10⁶ without compromising operator convergence. The real scalability challenge is N > 10⁶, where Nyström approximation is the practical choice at the cost of weakened guarantees.

### Finding 4: Optimal Pipeline = Local PCA → Spectral → Topological
The theoretically grounded pipeline for manifold analysis is:
1. Local PCA for dimension estimation and manifold hypothesis testing
2. Spectral methods (diffusion maps/JMS) for parametrization with guarantees
3. Persistent homology for topological verification

This pipeline is computationally efficient (dominated by the O(Nkd) spectral step) and provides complementary information at each stage.
