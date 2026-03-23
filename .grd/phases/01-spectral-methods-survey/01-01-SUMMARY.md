# Plan 01-01 Summary: Spectral Methods Survey

## Status: COMPLETE

## Key Results

### 1. Laplacian Eigenmaps (Belkin & Niyogi 2003)
- Algorithm: k-NN/ε-ball graph → Gaussian weights → graph Laplacian L = D - W → generalized eigenvalue problem Lf = λDf
- Convergence: graph Laplacian → Laplace-Beltrami Δ_M as N → ∞
- Rate: O(N^{-2/(d+4)}) for eigenvalues (Calder et al. 2022)
- Complexity: O(N log N · D + Nkd) for sparse k-NN graphs
- Limitations: density-dependent, parameter-sensitive, boundary effects

### 2. Diffusion Maps (Coifman & Lafon 2006)
- Key innovation: α-normalization separates geometry from sampling density
- α = 1 recovers Laplace-Beltrami (density-independent Riemannian geometry)
- Diffusion distance d_t(x,y) approximates geodesic distance at scale √t
- Multiscale structure via time parameter t
- Same computational complexity as Laplacian eigenmaps

### 3. JMS Heat Triangulation Theorem (Jones-Maggioni-Schul 2008)
- **Theorem 1** (Euclidean): d eigenfunctions provide bi-Lipschitz map on B_{c₁R_z}(z) with bounds (c₂/R_z)‖x₁−x₂‖ ≤ ‖Φ(x₁)−Φ(x₂)‖ ≤ (c₃/R_z)‖x₁−x₂‖
- **Theorem 2** (C^α manifolds): extends to compact Riemannian manifolds with C^α metric
- **Theorem 3** (Heat triangulation): d reference points + heat kernel → bi-Lipschitz local coordinates without global eigendecomposition
- **Strongest known guarantee**: bi-Lipschitz (both upper AND lower bounds), dimension-optimal (only d eigenfunctions/probes needed), constants depend only on intrinsic geometry

### 4. Convergence Landscape (2022-2025)
- Bungert et al. (2025): optimal eigenvalue convergence on Poisson point clouds
- Wormell & Reich (2024): bi-stochastic normalization robust to outliers
- Lu & Bhatt (2025): spectral convergence on manifolds with boundary
- Theory-practice gap: proven rates assume idealized settings; practical performance often better

### 5. Scalability
| Method | Complexity | Max practical N |
|--------|-----------|----------------|
| Full eigendecomp | O(N³) | ~10⁴ |
| Sparse Lanczos | O(Nkd) | ~10⁵-10⁶ |
| Nyström | O(Nl²+l³) | ~10⁶-10⁷ |
| Random features | O(NmD) | ~10⁷+ |

**Critical finding:** All scalable approximations weaken or lose bi-Lipschitz guarantees.

## Deliverables
- [x] `.grd/phases/01-spectral-methods-survey/spectral-methods-analysis.md` — Complete 6-section analysis

## Verification
- [x] All three spectral methods covered with algorithm + guarantees + complexity
- [x] JMS Theorems 1-3 stated precisely with assumptions
- [x] Convergence rate comparison table present
- [x] Scalability comparison table present
- [x] Bi-Lipschitz vs upper-bound-only distinction made explicit

## Open Questions (propagated)
- Automatic reference point selection for heat triangulation (Theorem 3)
- Practical convergence rates in high-noise regimes vs theoretical bounds
- Whether any scalable method can partially preserve bi-Lipschitz guarantees
