# Plan 03-01 Summary: Comparative Analysis

## Status: COMPLETE

## Key Results

### ANAL-01: Complexity Table
- Sparse spectral methods (LE, DM, JMS): O(N log N · D + Nkd) — best scaling
- LLE: O(N log N · D + Nk³D) — comparable but k³ term can dominate
- ISOMAP: O(N² log N) — O(N²) memory makes it impractical for N > 10⁴
- Persistent homology: O(N³) — fundamentally expensive but answers different question

### ANAL-02: Guarantee Comparison
- JMS heat triangulation: **only method with bi-Lipschitz guarantee**, constants depend on intrinsic geometry only
- Diffusion maps (α=1): operator convergence to Δ_M + density independence
- Persistent homology: stability theorem (different kind of guarantee — topological)
- ISOMAP: requires convexity, no lower bound; LLE: no convergence guarantee at all

### ANAL-03: Efficient Approximations
- Sparse k-NN + Lanczos: O(Nkd), preserves operator convergence, scales to N ~ 10⁵-10⁶
- Nyström: O(Nl²+l³), partially preserves convergence, scales to N ~ 10⁶-10⁷
- No known subquadratic approximation fully preserves bi-Lipschitz guarantees
- Sparse Rips: (1+ε)-approximation of persistence diagrams

### Regime Recommendations
- Small N (<10⁴): JMS heat triangulation (full guarantees)
- Medium N (10⁴-10⁶): Sparse diffusion maps
- Large N (>10⁶): Nyström diffusion maps (degraded guarantees)

## Critical Finding: Pareto Frontier
Only 3 methods on the guarantee-vs-cost Pareto frontier:
1. JMS (strongest geometric), 2. Diffusion maps (best practical), 3. Persistent homology (topological)

## Deliverables
- [x] `.grd/phases/03-comparative-analysis/comparative-analysis.md`
