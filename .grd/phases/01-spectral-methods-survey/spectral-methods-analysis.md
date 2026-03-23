# Spectral Methods for Manifold Detection: Analysis and Comparison

## 1. Laplacian Eigenmaps

### 1.1 Algorithm

**Input:** N points {x₁, ..., x_N} ⊂ ℝ^D sampled from or near a d-dimensional manifold M.

**Step 1 — Graph construction:** Build a weighted graph G = (V, E) where V = {x₁, ..., x_N}.
- *k-NN variant:* Connect xᵢ to xⱼ if xⱼ is among xᵢ's k nearest neighbors (symmetrized).
- *ε-ball variant:* Connect xᵢ to xⱼ if ‖xᵢ − xⱼ‖ < ε.

**Step 2 — Weight matrix:** Assign edge weights via a Gaussian kernel:

W_ij = exp(−‖xᵢ − xⱼ‖² / σ²) if (i,j) ∈ E, else 0.

**Step 3 — Graph Laplacian:** Form the unnormalized graph Laplacian L = D − W, where D = diag(d₁, ..., d_N) with dᵢ = Σⱼ Wᵢⱼ.

**Step 4 — Generalized eigenvalue problem:** Solve Lf = λDf for the smallest non-trivial eigenvalues 0 = λ₀ < λ₁ ≤ λ₂ ≤ ... ≤ λ_{d}.

**Step 5 — Embedding:** Map xᵢ → (f₁(xᵢ), f₂(xᵢ), ..., f_d(xᵢ)) using the bottom d eigenvectors (excluding the trivial constant eigenvector f₀).

### 1.2 Theoretical Guarantees

**Convergence of graph Laplacian to Laplace-Beltrami operator:**

The foundational convergence result (Belkin & Niyogi, 2005; 2008) establishes that as N → ∞, the graph Laplacian Lₙ converges pointwise to a continuous operator on M. Specifically, for the normalized graph Laplacian with appropriate bandwidth scaling ε = ε(N):

lim_{N→∞} Lₙf(x) = Δ_M f(x) + ∇(log p) · ∇f(x)

where Δ_M is the Laplace-Beltrami operator and p is the sampling density. For uniform sampling (p = const), this reduces to Δ_M f(x).

**Eigenvalue convergence rates (Calder, García Trillos, Lewicka, 2022):**

For ε-graphs with N points on a d-dimensional manifold:
- Eigenvalue convergence: |λⱼ^(N) − λⱼ^(M)| = O(ε² + (log N / (Nεᵈ))^{1/2})
- Optimal bandwidth: ε ~ (log N / N)^{1/(d+4)} giving rate O((log N / N)^{2/(d+4)})

For k-NN graphs with k ~ N^{2/(d+4)}:
- Similar rate: O((log N / N)^{2/(d+4)}) for the first K eigenvalues

**Eigenvector convergence:** The eigenvectors of the graph Laplacian converge to the eigenfunctions of Δ_M in appropriate Sobolev norms, with rates depending on the spectral gap between consecutive eigenvalues.

### 1.3 Computational Complexity

| Step | Operation | Complexity |
|------|-----------|------------|
| Graph construction (brute-force) | All-pairs distances | O(N²D) |
| Graph construction (k-d tree) | Approximate NN | O(N log N · D) for D ≲ 20 |
| Graph construction (random proj.) | Approximate NN | O(N log N · D) for large D |
| Eigendecomposition (dense) | Full SVD of N×N matrix | O(N³) |
| Eigendecomposition (sparse, Lanczos) | d eigenpairs of sparse L | O(N · k · d · iters) |
| **Total (sparse, k-NN)** | **End-to-end** | **O(N log N · D + N · k · d)** |

Where k = neighbors per point, d = target dimension, iters = Lanczos iterations (typically O(1) for well-separated eigenvalues).

**Memory:** O(Nk) for sparse graph storage.

### 1.4 Limitations

1. **Density sensitivity:** The unnormalized Laplacian converges to Δ_M + ∇(log p)·∇, mixing geometry with density. Uniform sampling or density estimation is needed.
2. **Parameter selection:** Choice of k (or ε) and σ is critical and problem-dependent. Too small → disconnected graph; too large → lose local geometry.
3. **Boundary effects:** Near manifold boundaries, the graph Laplacian does not approximate the Laplace-Beltrami operator well without boundary-aware constructions.
4. **Curse of dimensionality:** The convergence rate O(N^{−2/(d+4)}) degrades with intrinsic dimension d, requiring exponentially more samples for higher-dimensional manifolds.
5. **Global eigenvectors:** Eigenvectors are global objects — a perturbation anywhere affects the embedding everywhere.

---

## 2. Diffusion Maps

### 2.1 Algorithm

**Input:** Same as Laplacian eigenmaps.

**Step 1 — Kernel matrix:** K(xᵢ, xⱼ) = exp(−‖xᵢ − xⱼ‖² / ε).

**Step 2 — α-normalization (key innovation):**
- Compute density estimate: qε(xᵢ) = Σⱼ K(xᵢ, xⱼ)
- Form normalized kernel: K^(α)(xᵢ, xⱼ) = K(xᵢ, xⱼ) / (qε(xᵢ)^α · qε(xⱼ)^α)

**Step 3 — Markov matrix:** Normalize rows to get row-stochastic matrix P:
- dα(xᵢ) = Σⱼ K^(α)(xᵢ, xⱼ)
- P(xᵢ, xⱼ) = K^(α)(xᵢ, xⱼ) / dα(xᵢ)

**Step 4 — Spectral decomposition:** Compute eigenvectors ψⱼ of P with eigenvalues 1 = μ₀ ≥ μ₁ ≥ μ₂ ≥ ...

**Step 5 — Diffusion map at time t:**
Ψₜ(x) = (μ₁ᵗ ψ₁(x), μ₂ᵗ ψ₂(x), ..., μ_dᵗ ψ_d(x))

### 2.2 The α-Normalization: Separating Geometry from Density

The parameter α controls what geometry the diffusion process recovers:

| α | Limit operator | Physical interpretation |
|---|----------------|----------------------|
| 0 | Δ_M + ∇(log p)·∇ | Graph Laplacian (density-dependent) |
| 1/2 | Fokker-Planck operator | Equilibrium dynamics weighted by density |
| **1** | **Δ_M (Laplace-Beltrami)** | **Pure Riemannian geometry, density-independent** |

**The α = 1 case is the critical innovation:** By normalizing by the density twice, the diffusion process recovers the intrinsic Riemannian geometry regardless of the sampling distribution. This means the embedding is the same whether points are uniformly distributed or clustered.

### 2.3 Theoretical Guarantees

**Convergence to Laplace-Beltrami (α = 1):**

As N → ∞ and ε → 0 with Nεᵈ⁺² → ∞:

(1/ε)(I − P^(α=1)) → (1/2)Δ_M

in the pointwise sense. The spectral convergence rates are the same order as for Laplacian eigenmaps (since both approximate Δ_M).

**Diffusion distance:** The diffusion distance at time t is:

d_t(x, y)² = Σⱼ≥1 μⱼ²ᵗ (ψⱼ(x) − ψⱼ(y))²

This captures geodesic-like distances at scale √(εt). For small t, d_t approximates local Euclidean distance; for large t, d_t captures global connectivity.

**Multiscale geometry:** The time parameter t acts as a scale selector. The eigenvalue weighting μⱼ²ᵗ naturally suppresses high-frequency components (small eigenvalues have μⱼ close to 1, decaying slowly; large eigenvalues decay fast). This provides built-in regularization.

**Recent results — spectral convergence with optimal rates:**
- Trillos & Slepčev (2018): Variational convergence framework for graph-based algorithms on manifolds.
- Calder et al. (2022): Optimal rates O(N^{−2/(d+4)}) for both ε-graphs and k-NN graphs.

### 2.4 Computational Complexity

Same order as Laplacian eigenmaps — the α-normalization adds only O(N·k) work:

| Step | Complexity |
|------|-----------|
| Kernel computation | O(N²D) or O(N log N · D) sparse |
| Density estimation (qε) | O(N·k) |
| α-normalization | O(N·k) |
| Row normalization (Markov) | O(N·k) |
| Eigendecomposition | O(N·k·d·iters) |
| **Total** | **O(N log N · D + N·k·d)** |

### 2.5 Advantages Over Laplacian Eigenmaps

1. **Density independence (α = 1):** Recovers intrinsic geometry regardless of sampling distribution.
2. **Multiscale analysis:** Time parameter t provides built-in scale selection.
3. **Diffusion distance metric:** A meaningful metric space structure, not just an embedding.
4. **Robustness:** The Markov normalization provides probabilistic interpretation and numerical stability.
5. **Spectral truncation is natural:** Eigenvalue decay provides a principled truncation criterion.

---

## 3. Jones-Maggioni-Schul Heat Triangulation Theorem

### 3.1 Overview

The JMS paper (PNAS, 2008) proves the strongest known theoretical result on spectral manifold parametrization: eigenfunctions of the Laplacian and heat kernels provide **bi-Lipschitz** local coordinate systems on manifolds. This is significantly stronger than the continuity or neighborhood-preservation guarantees of other methods.

### 3.2 Theorem 1 — Euclidean Domains

**Setting:** Let Ω ⊂ ℝᵈ be a bounded domain with |Ω| = 1, equipped with Dirichlet or Neumann boundary conditions. Let {φⱼ}_{j≥0} be the orthonormal eigenfunctions of the Laplacian Δ on Ω with eigenvalues 0 ≤ λ₀ ≤ λ₁ ≤ ...

**Weyl's law requirement:** There exists C_{Weyl,Ω} such that #{j : λⱼ ≤ T} ≤ C_{Weyl,Ω} · T^{d/2} |Ω| for all T > 0.

**Statement:** There exist constants c₁, ..., c₆ > 0 depending only on d and C_{Weyl,Ω} such that for any z ∈ Ω, letting R_z = dist(z, ∂Ω), there exist:
- Indices i₁, ..., i_d
- Scaling constants c₆ R_z^{d/2} ≤ γ₁ = γ₁(z), ..., γ_d = γ_d(z) ≤ 1

such that the map:

**Φ: B_{c₁R_z}(z) → ℝᵈ**
**x ↦ (γ₁ φ_{i₁}(x), ..., γ_d φ_{i_d}(x))**

satisfies for all x₁, x₂ ∈ B(z, c₁R_z):

**(c₂/R_z) ‖x₁ − x₂‖ ≤ ‖Φ(x₁) − Φ(x₂)‖ ≤ (c₃/R_z) ‖x₁ − x₂‖**

The associated eigenvalues satisfy: c₄ R_z⁻² ≤ λ_{i₁}, ..., λ_{i_d} ≤ c₅ R_z⁻².

**Key features:**
- Only **d** eigenfunctions are needed (dimension-optimal)
- Constants depend **only on geometry** (d and C_Weyl), not on the specific domain
- The map "blows up" the local ball to diameter ~1 (the 1/R_z factor)
- Eigenvalues are localized: they scale as R_z⁻² (heat diffusion time scale)

### 3.3 Theorem 2 — Compact Riemannian Manifolds with C^α Metric

**Setting:** Let (M, g) be a smooth, d-dimensional compact manifold with a C^α metric tensor g for some α ∧ 1 (meaning min(α,1)). Let (U, u) be a coordinate chart at z₀ with:
- g^{ij}(u(z₀)) = δ^{ij} (metric is identity at z₀)
- Ellipticity bounds: c_min ‖ξ‖² ≤ Σ g^{ij}(u(x)) ξᵢξⱼ ≤ c_max ‖ξ‖²

Let r_M(z₀) = sup{r > 0 : B_r(u(z₀)) ⊆ u(U)} be the inradius.

**Statement:** Same bi-Lipschitz conclusion as Theorem 1, but with:
- R_z = r_M(z) replacing dist(z, ∂Ω)
- Constants additionally depending on c_min, c_max, ‖g‖_{α∧1}, and C_{Weyl,M}

**Significance:**
- Works for **non-smooth manifolds** — C^α metric is sufficient, not C^∞
- The Laplace-Beltrami operator Δ_M is defined via: Δ_M f(x) = −(1/√det g) Σ ∂ᵢ(√det g · g^{ij}(u(x)) ∂ⱼf)(u(x))
- Covers a much broader class of manifolds than typically assumed in manifold learning

### 3.4 Theorem 3 — Heat Triangulation

**Setting:** Same as Theorem 2, but now |M| = +∞ is allowed (non-compact manifolds). Given d linearly independent directions p₁, ..., p_d at z ∈ M.

**Construction:** Choose reference points yᵢ such that yᵢ − z is in direction pᵢ with c₃R_z ≤ d_M(yᵢ, z) ≤ c₅R_z for each i = 1, ..., d. Set t_z = c₆ R_z².

**Statement:** The heat kernel map:

**Φ: B_{c₁R_z}(z) → ℝᵈ**
**x ↦ (R_z^d K_{t_z}(x, y₁), ..., R_z^d K_{t_z}(x, y_d))**

satisfies the bi-Lipschitz condition:

**(c₂/R_z) d_M(x₁, x₂) ≤ ‖Φ(x₁) − Φ(x₂)‖ ≤ (c₃/R_z) d_M(x₁, x₂)**

for all x₁, x₂ ∈ B_{c₁R_z}(z).

**This is the "Heat GPS" theorem:** d probe points at appropriately chosen locations, evaluated at the right time scale, provide a bi-Lipschitz local coordinate system.

### 3.5 Key Assumptions and Their Implications

| Assumption | Mathematical requirement | Practical implication |
|-----------|------------------------|---------------------|
| Weyl's law | #{λⱼ ≤ T} ≲ T^{d/2} | Ensures enough eigenvalues in the right frequency band; holds for all compact Riemannian manifolds |
| C^α metric | g ∈ C^α for α > 0 | Non-smooth manifolds OK, but metric must be Hölder continuous; fractal sets excluded |
| Locality | Bi-Lipschitz on B_{c₁R_z}(z) | NOT a global guarantee; radius shrinks near boundaries or high-curvature regions |
| Eigenvalue localization | λ_{iⱼ} ~ R_z⁻² | The relevant eigenfunctions have wavelength ~ R_z; must find them from the full spectrum |
| Reference point selection | d linearly independent directions | Theorem 3 requires choosing probe points that span the tangent space; automation is non-trivial |

### 3.6 Why JMS Guarantees Are Strongest

**Comparison with other spectral methods:**

| Method | Guarantee type | What is proven |
|--------|---------------|---------------|
| Laplacian eigenmaps | Asymptotic convergence | Graph Laplacian → Δ_M as N → ∞ |
| Diffusion maps | Asymptotic convergence | Diffusion operator → Δ_M as N → ∞, ε → 0 |
| ISOMAP | Isometric embedding | Recovers geodesic distances if manifold is convex |
| LLE | Local linearity | Preserves local linear structure |
| **JMS eigenfunctions** | **Bi-Lipschitz embedding** | **Both upper AND lower distance bounds with explicit constants** |
| **JMS heat kernels** | **Bi-Lipschitz embedding** | **Same, plus locality + no global eigendecomp needed** |

The critical distinction: most methods provide only **upper bounds** (continuity, neighborhood preservation) or **asymptotic** guarantees. JMS provides **bi-Lipschitz bounds** — the embedding faithfully represents distances in both directions, with explicit, computable constants.

### 3.7 Practical Implications for Manifold Detection

1. **Dimension detection:** The fact that exactly d eigenfunctions suffice provides a principled way to estimate intrinsic dimension — look for the number of eigenfunctions needed for bi-Lipschitz embedding.

2. **Scale selection:** The eigenvalue localization λ_{iⱼ} ~ R_z⁻² links the time parameter t to the spatial scale R_z. This provides principled scale selection for heat kernel methods.

3. **Heat kernels vs eigenfunctions:** Theorem 3 shows that heat kernels (local objects) can replace eigenfunctions (global objects), gaining:
   - Locality (perturbations elsewhere don't affect local coordinates)
   - No need for global eigendecomposition
   - Natural multiscale analysis via the time parameter t

4. **Limitation — reference point selection:** The main practical gap is automating the choice of d linearly independent reference points (Theorem 3). This requires local tangent space estimation, which itself is a manifold learning problem.

---

## 4. Graph Laplacian Convergence: Classical and Recent Results

### 4.1 Classical Results (2005-2010)

**Pointwise convergence (Belkin & Niyogi, 2005):**
The graph Laplacian Lₙ,ε applied to a smooth function f converges pointwise to Δ_M f as N → ∞ and ε → 0, provided Nεᵈ⁺² / log N → ∞.

**Consistency results (Hein, Audibert, von Luxburg, 2005):**
"From graphs to manifolds" — established both weak and strong pointwise consistency of graph Laplacians to weighted Laplace operators, including the case where data lies on a submanifold.

**Spectral convergence (von Luxburg, Belkin, Bousquet, 2008):**
Established the consistency of spectral clustering methods based on graph Laplacians. Eigenvalues and eigenvectors of the graph Laplacian converge to those of the Laplace-Beltrami operator.

### 4.2 Modern Optimal Rates (2022-2025)

**Improved spectral convergence (Calder, García Trillos, Lewicka, 2022):**
Improved error bounds for eigenvalue convergence using:
- Spatially localized compact embedding estimates on Hardy spaces
- Treating the graph Laplacian as a perturbation of Δ_M
- Result: eigenvalue convergence rate O(ε² + (log N / (Nεᵈ))^{1/2}) for ε-graphs
- Matches long-standing pointwise error bounds for operator discretization

**Bi-stochastic normalization (Wormell & Reich, 2024):**
Key innovation: proves convergence of bi-stochastically normalized graph Laplacian to manifold (weighted-)Laplacian with rates, when points are i.i.d. sampled from a d-dimensional manifold embedded in high-dimensional space.
- **Critical advantage: ROBUST TO OUTLIER NOISE** — the bi-stochastic normalization automatically downweights outliers
- Converges even with moderate outlier contamination

**Optimal rates on Poisson point clouds (Bungert, Calder, Roith, 2025):**
Proves optimal convergence rates for eigenvalues and eigenvectors of the graph Laplacian on Poisson point clouds.
- Results valid down to the critical percolation threshold
- Yields error estimates for relatively sparse graphs (smaller k or ε)
- Optimal in the minimax sense

**Manifolds with boundary (Lu & Bhatt, 2025):**
Addresses the important case of manifolds with boundary:
- Spectral convergence of symmetrized graph Laplacian to Laplace-Beltrami
- Covers both Neumann and Dirichlet boundary conditions
- Convergence rates for eigenpairs established

### 4.3 Convergence Rate Comparison Table

| Method / Normalization | Target operator | Eigenvalue rate | Conditions | Noise robustness |
|----------------------|----------------|-----------------|------------|-----------------|
| Unnormalized graph Laplacian | Δ_M + ∇(log p)·∇ | O(N^{−2/(d+4)}) | Uniform sampling | Low (density-sensitive) |
| Normalized (random walk) | Δ_M + ∇(log p)·∇ | O(N^{−2/(d+4)}) | Arbitrary density | Moderate |
| α-normalized (α=1, diffusion maps) | Δ_M | O(N^{−2/(d+4)}) | Arbitrary density | Moderate |
| Bi-stochastic (Wormell & Reich) | Weighted Δ_M | Optimal rates | Arbitrary density | **Strong** (outlier-robust) |
| Optimal (Bungert et al.) | Δ_M | O(N^{−2/(d+2)}) | Poisson point cloud | Standard |

### 4.4 Theory-Practice Gap

The theoretical convergence rates O(N^{−2/(d+4)}) suggest that manifold learning should fail in moderate-to-high intrinsic dimensions. In practice:

1. **Methods work better than theory predicts:** Real data often has additional structure (low effective dimensionality, clustering, smooth density) that makes convergence faster.
2. **Spectral gap matters more than rate:** The practical performance depends critically on the spectral gap λ_{d+1} − λ_d, not just the convergence rate per eigenvalue.
3. **Finite-sample behavior:** The O(·) constants in convergence rates are typically unknown and may be large, making the asymptotic rates unreliable guides for practical sample sizes.

---

## 5. Scalable Approximations for Spectral Methods

### 5.1 Nyström Approximation

**Core idea:** Instead of computing the full N×N kernel matrix K, sample l ≪ N landmark points and compute only the N×l kernel submatrix.

**Algorithm:**
1. Sample l landmark points (uniformly or via k-means)
2. Compute K_{nl} (N×l submatrix) and K_{ll} (l×l submatrix among landmarks)
3. Approximate full matrix: K̃ ≈ K_{nl} K_{ll}⁻¹ K_{nl}ᵀ
4. Compute eigendecomposition of the l×l matrix
5. Extend eigenvectors to all N points via the Nyström formula

**Complexity:** O(Nl² + l³) — compared to O(N³) for full eigendecomposition.

**Accuracy-efficiency tradeoff:**
- l = O(√N): Good approximation for well-separated eigenvalues
- l = O(N^{2/3}): Near-optimal for most kernels
- Quality degrades when the spectral gap is small or the kernel has slow eigenvalue decay

**Limitations:**
- Premature rank reduction can discard critical spectral information
- Landmark selection strategy affects quality significantly
- Recent work (Pourkamali-Anaraki et al., 2020) shows that random landmark selection can lose important structure

### 5.2 Random Fourier Features (Rahimi & Recht, 2007)

**Core idea:** For shift-invariant kernels K(x,y) = k(x−y), approximate via random feature maps:

z(x) = √(2/m) [cos(ω₁ᵀx + b₁), ..., cos(ωₘᵀx + bₘ)]ᵀ

where ωⱼ ~ p(ω) (spectral density of the kernel) and bⱼ ~ Uniform[0, 2π].

**Result:** K(x,y) ≈ z(x)ᵀz(y) with |K(x,y) − z(x)ᵀz(y)| = O(1/√m) uniformly.

**Complexity:** O(N·D·m) for computing features + O(N·m·d) for eigendecomposition in feature space.

**Applicability:** Works for Gaussian RBF kernel (the standard in manifold learning). Does not directly apply to non-stationary kernels or heat kernels on discrete graphs.

### 5.3 Sparse Graph Construction

**k-NN graphs with fast nearest neighbor search:**
- k-d trees: O(N log N · D) for D ≲ 20
- Random projection trees: O(N log N · D) for moderate D
- Locality-sensitive hashing (LSH): O(N · D · poly(log N)) for very high D
- Ball trees: O(N log N · D) with better constants for metric spaces

**Result:** Sparse graph with O(Nk) edges, enabling sparse eigendecomposition.

### 5.4 Scalability Comparison Table

| Method | Time complexity | Memory | Practical max N | Guarantee preservation |
|--------|----------------|--------|----------------|----------------------|
| Full eigendecomp | O(N³) | O(N²) | ~10⁴ | Exact (up to numerical precision) |
| Sparse Laplacian + Lanczos | O(N·k·d·iters) | O(N·k) | ~10⁵–10⁶ | Graph Laplacian convergence preserved |
| Nyström | O(N·l² + l³) | O(N·l) | ~10⁶–10⁷ | Approximate — depends on l and spectral gap |
| Random features | O(N·m·D) | O(N·m) | ~10⁷+ | Kernel approximation — no direct manifold guarantee |
| Subsampling + interpolation | O(N·s + s³) | O(s²) | ~10⁸+ | Depends on interpolation quality |

### 5.5 Guarantee Preservation Under Approximation

**Critical observation:** All scalable approximations weaken the theoretical guarantees to some degree.

- **Sparse graph Laplacian:** Preserves graph Laplacian convergence (same theory applies with k or ε as graph parameters), but the effective convergence rate depends on k.
- **Nyström:** Approximates the kernel matrix, not the Laplacian. The spectral error ||K − K̃||_op depends on l and the eigenvalue decay, but the connection to manifold Laplacian convergence is indirect.
- **Random features:** Approximates the kernel function, which is one step further removed from the Laplacian. No direct convergence-to-Δ_M result exists for random-feature-based Laplacians.

**The JMS bi-Lipschitz guarantee is particularly fragile under approximation:** It requires exact eigenfunctions at the right frequencies (λ ~ R_z⁻²). Nyström or random feature approximations that miss these eigenvalues would destroy the bi-Lipschitz property entirely.

**Practical implication:** For applications requiring guaranteed manifold parametrization (not just visualization), sparse graph methods with Lanczos eigendecomposition are the safest scalable option, as they directly compute graph Laplacian eigenvectors.

---

## 6. Summary and Key Takeaways

### Method Comparison Summary

| Method | Guarantee | Complexity (sparse) | Density-independent | Multiscale | Bi-Lipschitz |
|--------|-----------|--------------------|--------------------|-----------|-------------|
| Laplacian eigenmaps | Asymptotic convergence to Δ_M | O(N log N · D + Nkd) | No (needs uniform sampling) | No | No |
| Diffusion maps (α=1) | Convergence to Δ_M | O(N log N · D + Nkd) | **Yes** | **Yes** (time t) | No |
| JMS eigenfunctions | **Bi-Lipschitz** local coords | O(N log N · D + Nkd) | Yes (intrinsic) | Via eigenvalue selection | **Yes** (local) |
| JMS heat kernels | **Bi-Lipschitz** local coords | O(reference point evaluation) | Yes (intrinsic) | **Yes** (time t) | **Yes** (local) |

### The Central Tradeoff

**Theoretical strength vs practical scalability:**
- JMS heat triangulation provides the strongest guarantees (bi-Lipschitz with explicit constants)
- But it requires: (a) finding the right eigenfunctions/reference points, (b) estimating the inradius R_z, (c) choosing the time scale t = O(R_z²)
- Diffusion maps provide a practical, scalable framework with weaker but sufficient guarantees for most applications
- The gap between JMS theory and practical algorithms is the key open problem

### Open Questions for Phase 3

1. How do the theoretical guarantees compare with geometric and topological methods (Phase 2)?
2. Can the JMS bi-Lipschitz bounds be made practical via efficient reference point selection?
3. What is the quantitative gap between guaranteed methods and heuristic methods (t-SNE, UMAP) for real datasets?
