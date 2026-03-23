# Roadmap: Manifold Detection and Parametrization in High-Dimensional Spaces

## Overview

This project surveys and systematizes methods for detecting low-dimensional manifold substructures in high-dimensional point clouds, anchored by the Jones-Maggioni-Schul heat triangulation theorem. The investigation covers spectral, geometric, and topological method families, characterizes their computational complexity and theoretical guarantees, and bridges to mechanistic interpretability applications.

## Phases

- [x] **Phase 1: Spectral Methods Survey** - Survey spectral manifold detection methods (Laplacian eigenmaps, diffusion maps, heat kernel embeddings) and analyze the JMS heat triangulation theorem
- [x] **Phase 2: Geometric & Topological Methods** - Survey geometric (local PCA, ISOMAP, LLE) and topological (persistent homology, Mapper) methods
- [x] **Phase 3: Comparative Analysis** - Construct complexity comparison table, compare theoretical guarantees, identify efficient approximations
- [x] **Phase 4: Synthesis & Bridge** - Produce final survey report and mechanistic interpretability bridge note

## Phase Details

### Phase 1: Spectral Methods Survey

**Goal:** Survey spectral methods for manifold detection and deeply analyze the JMS heat triangulation theorem
**Depends on:** Nothing (first phase)
**Requirements:** [SURV-01, SURV-04]
**Success Criteria** (what must be TRUE):

1. Laplacian eigenmaps, diffusion maps, and heat kernel embeddings covered with theoretical guarantees and complexity
2. JMS heat triangulation theorem (Theorems 1-3) analyzed with key assumptions and practical implications stated
3. Relationship between graph Laplacian convergence and manifold Laplacian established

Plans:

- [ ] 01-01: [TBD — created during /grd:plan-phase]

### Phase 2: Geometric & Topological Methods

**Goal:** Survey non-spectral manifold detection methods
**Depends on:** Phase 1 (for comparison baseline)
**Requirements:** [SURV-02, SURV-03]
**Success Criteria** (what must be TRUE):

1. Local PCA, ISOMAP, LLE, and tangent space estimation covered with guarantees and complexity
2. Persistent homology and Mapper covered for manifold detection
3. Strengths and weaknesses relative to spectral methods identified

Plans:

- [ ] 02-01: [TBD — created during /grd:plan-phase]

### Phase 3: Comparative Analysis

**Goal:** Construct quantitative comparison of all methods
**Depends on:** Phase 1, Phase 2
**Requirements:** [ANAL-01, ANAL-02, ANAL-03]
**Success Criteria** (what must be TRUE):

1. Complexity comparison table: cost as f(D, d, N) for each method
2. Theoretical guarantee comparison: bi-Lipschitz, distortion, convergence, noise robustness
3. Efficient approximations (Nyström, random features, sparse graphs) characterized

Plans:

- [ ] 03-01: [TBD — created during /grd:plan-phase]

### Phase 4: Synthesis & Bridge

**Goal:** Produce final deliverables: survey report and interpretability bridge note
**Depends on:** Phase 3
**Requirements:** [SYNT-01, SYNT-02, SYNT-03]
**Success Criteria** (what must be TRUE):

1. Structured survey report with method taxonomy, complexity table, and guarantee summary
2. Bridge note with ≥2 specific, actionable connections to mechanistic interpretability
3. Open problems identified at the intersection

Plans:

- [ ] 04-01: [TBD — created during /grd:plan-phase]

## Progress

| Phase | Plans Complete | Status | Completed |
| ----- | ------------- | ------ | --------- |
| 1. Spectral Methods Survey | 1/1 | Complete | 2026-03-23 |
| 2. Geometric & Topological Methods | 1/1 | Complete | 2026-03-23 |
| 3. Comparative Analysis | 1/1 | Complete | 2026-03-23 |
| 4. Synthesis & Bridge | 1/1 | Complete | 2026-03-23 |
