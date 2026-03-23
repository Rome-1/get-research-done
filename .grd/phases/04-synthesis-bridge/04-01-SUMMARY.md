# Plan 04-01 Summary: Synthesis & Bridge

## Status: COMPLETE

## Key Results

### SYNT-01: Structured Survey Report
- Method taxonomy: 3 families (spectral, geometric, topological), 8 specific methods
- Complexity comparison: Sparse spectral O(Nkd) dominates; ISOMAP/PH limited by O(N²)/O(N³)
- Guarantee ranking: JMS (bi-Lipschitz) > Diffusion Maps (operator convergence) > PH (stability) > rest
- Method selection guide by (N, D, d) regime and task type

### SYNT-02: Interpretability Bridge Note (3 specific connections)
1. **JMS heat kernel probing:** Apply Theorem 3 to activation spaces for provably bi-Lipschitz feature coordinates — concrete protocol provided
2. **Diffusion maps (α=1) for density-independent feature geometry:** Separate manifold geometry from activation frequency — solves a fundamental conflation in current analysis
3. **Persistent homology for feature topology classification:** Classify features by manifold topology (circular = periodic, spherical = doubly periodic, etc.)

### SYNT-03: Open Problems (6 identified)
1. Automatic reference point selection for JMS in activation spaces
2. Multi-manifold detection in shared activation spaces
3. Scalable bi-Lipschitz embeddings (subquadratic)
4. Feature manifold evolution during training
5. Manifold curvature ↔ model capacity relationship
6. SAE features ↔ manifold geometry correspondence

## Deliverables
- [x] `.grd/phases/04-synthesis-bridge/survey-report.md`
- [x] `.grd/phases/04-synthesis-bridge/interpretability-bridge.md`
