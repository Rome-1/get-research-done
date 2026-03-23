# Plan 02-01 Summary: Geometric & Topological Methods

## Status: COMPLETE

## Key Results

### 1. ISOMAP
- Geodesic distance preservation via shortest paths + MDS
- Requires convex manifolds — fails catastrophically with holes
- Complexity: O(N² log N), Memory: O(N²) — poor scalability
- No bi-Lipschitz guarantee, no formal convergence rate

### 2. LLE
- Preserves local linear reconstruction weights
- No convergence to manifold geometry (unlike Laplacian eigenmaps)
- No density correction (unlike diffusion maps α=1)
- Complexity: O(N log N · D + Nk³D) — comparable to spectral

### 3. Local PCA / Tangent Space Estimation
- Standard tool for intrinsic dimension estimation via eigenvalue gap
- Rigorous sample complexity bounds (Aamari & Levrard 2019): sin∠(T̂, T) ≤ C(ε/τ + σ/ε)
- CA-PCA (2024) corrects curvature-induced overestimation
- Complementary to spectral methods (preprocessing, not competing)

### 4. Persistent Homology
- Stability theorem: d_B(Dgm(f), Dgm(g)) ≤ ‖f−g‖_∞
- Manifold homology recovery guarantee (Niyogi, Smale, Weinberger 2008)
- Complexity: O(N³) standard — limits to ~10⁴-10⁵ points
- Answers "what topology?" not "what coordinates?" — complementary to spectral

### 5. Mapper
- Approximates Reeb graph via filter + cover + cluster + nerve
- Theoretical foundation: nerve theorem
- Highly parameter-dependent, weak formal guarantees
- Exploratory visualization tool, not rigorous manifold detector

## Critical Finding

**Spectral methods dominate for parametrization.** No geometric method matches JMS bi-Lipschitz guarantees. The optimal pipeline combines:
1. Local PCA (dimension estimation) → Diffusion maps/JMS (parametrization) → Persistent homology (topological verification)

## Deliverables
- [x] `.grd/phases/02-geometric-topological-methods/geometric-topological-analysis.md`

## Verification
- [x] All five methods (ISOMAP, LLE, local PCA, PH, Mapper) with algorithm + guarantees + complexity
- [x] Comparison to spectral methods from Phase 1
- [x] Comprehensive comparison table across all methods
- [x] Method selection guide by use case
