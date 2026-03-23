# Phase 2 Research: Geometric & Topological Methods

## Research Summary

This research covers non-spectral methods for manifold detection: geometric methods (local PCA, ISOMAP, LLE) and topological methods (persistent homology, Mapper algorithm).

## 1. Geometric Methods

### 1.1 ISOMAP (Tenenbaum, de Silva, Langford 2000)

**Core idea:** Approximate geodesic distances via shortest paths on a neighborhood graph, then apply classical MDS to the geodesic distance matrix.

**Algorithm:**
1. Construct k-NN graph from N points in R^D
2. Compute shortest-path (geodesic) distances between all pairs via Dijkstra/Floyd-Warshall
3. Apply classical multidimensional scaling (MDS) to the geodesic distance matrix
4. Embed into d dimensions using top d eigenvectors

**Theoretical guarantees:**
- Asymptotically recovers true geodesic distances and dimensionality for a class of convex manifolds
- For sufficiently dense sampling, graph distances converge to true geodesic distances
- Guarantee requires manifold to be convex (no holes) — short-circuit errors otherwise
- Global optimality of embedding (MDS step)

**Computational complexity:**
- Graph construction: O(N log N · D) with k-d trees
- All-pairs shortest paths: O(N² log N + N²k) with Dijkstra from each node
- MDS eigendecomposition: O(N²d) for top d eigenvectors
- Total: O(N² log N · D) dominated by shortest paths
- Memory: O(N²) for full distance matrix

**Limitations:**
- Requires convex manifolds (no holes/concavities)
- Short-circuit vulnerability when k too large or manifold has narrow bottlenecks
- O(N²) memory makes it impractical for large N
- Sensitive to noise (can create short-circuits)

**Key reference:** Tenenbaum JB, de Silva V, Langford JC (2000). A Global Geometric Framework for Nonlinear Dimensionality Reduction. Science 290(5500):2319-2323.

### 1.2 Locally Linear Embedding (LLE) (Roweis & Saul 2000)

**Core idea:** Preserve local linear reconstruction weights in a lower-dimensional embedding. Each point is approximated as a linear combination of its neighbors; the embedding preserves these weights.

**Algorithm:**
1. Find k nearest neighbors for each point x_i
2. Compute reconstruction weights W_ij by minimizing ||x_i - Σ_j W_ij x_j||² subject to Σ_j W_ij = 1
3. Find d-dimensional embedding Y by minimizing ||y_i - Σ_j W_ij y_j||² — solve eigenvalue problem (I-W)^T(I-W) Y = λY
4. Use bottom d+1 eigenvectors (excluding constant)

**Theoretical guarantees:**
- No local minima in optimization (eigenvalue problems are convex)
- Preserves local linear structure by construction
- Can detect disconnected manifolds via connected components of adjacency matrix
- NO formal convergence guarantee to manifold geometry (unlike Laplacian eigenmaps)

**Computational complexity:**
- Neighbor search: O(N log N · D) with k-d trees
- Weight computation: O(N k³ D) (k×k linear systems per point)
- Eigendecomposition: O(N d²) for sparse (I-W)^T(I-W)
- Total: O(N log N · D + N k³ D + N d²)

**Limitations:**
- Sensitive to neighborhood size k
- Fails on non-uniformly sampled manifolds
- No density correction (unlike diffusion maps α-normalization)
- Regularization needed when k > D

**Key reference:** Roweis ST, Saul LK (2000). Nonlinear Dimensionality Reduction by Locally Linear Embedding. Science 290(5500):2323-2326.

### 1.3 Local PCA and Tangent Space Estimation

**Core idea:** Estimate tangent spaces at each point via local PCA, use tangent space alignment for embedding or dimension estimation.

**Methods:**
- **Local PCA:** Perform PCA on k-NN of each point; eigenvalue gap gives local dimension estimate
- **LTSA (Local Tangent Space Alignment):** Zhang & Zha (2004) — align local tangent spaces into global coordinates
- **CA-PCA (Curvature-Adjusted PCA):** 2024 — corrects for manifold curvature using quadratic model

**Theoretical guarantees:**
- Rigorous bounds on sample size needed to estimate dimension and tangent spaces with high confidence (Aamari & Levrard 2019)
- Uses matrix concentration inequalities for covariance estimation
- Wasserstein distance bound quantifies nonlinearity effect
- CA-PCA corrects linear bias from curvature

**Computational complexity:**
- Per-point local PCA: O(k D d) per point → O(N k D d) total
- Dimension estimation: O(N k D) for eigenvalue gaps
- LTSA alignment: O(N d²) additional

**Limitations:**
- Fails with high curvature or sparse/non-uniform sampling
- Local dimension estimates can vary across manifold
- Choice of neighborhood size k is critical

## 2. Topological Methods

### 2.1 Persistent Homology

**Core idea:** Track topological features (connected components, loops, voids) across multiple scales using filtrations. Features that persist across many scales are likely real manifold features.

**Algorithm:**
1. Build filtration: nested sequence of simplicial complexes (e.g., Vietoris-Rips or Cech) at increasing scale parameter ε
2. Compute homology groups H_k at each scale
3. Track birth and death of homological features → persistence diagram
4. Features with high persistence = robust topological structure

**Theoretical guarantees:**
- **Stability theorem** (Cohen-Steiner, Edelsbrunner, Harer 2007): Small perturbations of input → small perturbations of persistence diagrams (bottleneck distance bounded by Hausdorff distance)
- **Consistency** (Niyogi, Smale, Weinberger 2008): For sufficient sample density, persistent homology recovers the true homology of the underlying manifold
- **Confidence sets** (Fasy et al. 2014): Statistical confidence regions for persistence diagrams

**Computational complexity:**
- Vietoris-Rips complex: up to O(N^{k+1}) simplices for k-dimensional homology
- Standard algorithm: O(n³) where n = number of simplices (matrix reduction)
- In practice: O(N³) for H_0, H_1 on moderate-sized datasets
- Ripser (2021): optimized implementation, ~10-100× faster than naive, but still fundamentally cubic
- Memory: O(N²) minimum for distance matrix

**Scalability approaches:**
- Sparse Rips filtrations (Cavanna, Jahanseir, Sheehy 2015): O(N) simplices for (1+ε)-approximation
- Witness complexes: subsample landmark points
- GPU-accelerated persistent homology (2024)

**Limitations:**
- Computational cost limits to ~10⁴-10⁵ points for full computation
- Detects topology (holes, voids) rather than metric geometry
- Choice of filtration type affects results
- Does not directly produce coordinates/embeddings

**Key references:**
- Edelsbrunner H, Harer J (2010). Computational Topology. AMS.
- Carlsson G (2009). Topology and Data. Bulletin of the AMS 46(2):255-308.

### 2.2 Mapper Algorithm (Singh, Memoli, Carlsson 2007)

**Core idea:** Produce a simplicial complex (usually a graph) that approximates the Reeb graph of the data. Combines a filter function, covering, and clustering to create a topological summary.

**Algorithm:**
1. Choose filter function f: X → R (e.g., first PCA component, eccentricity, density)
2. Cover the range of f with overlapping intervals
3. For each interval, cluster the preimage points
4. Build nerve complex: nodes = clusters, edges = shared points between clusters

**Theoretical foundation:**
- Based on the **nerve theorem**: nerve of a good cover is homotopy equivalent to the space
- Approximates the **Reeb graph** of the filter function restricted to the data
- Statistical guarantees for certain parameter choices (Carrière & Oudot 2018), but depend on assumptions about the underlying space

**Computational complexity:**
- Filter function: depends on choice, typically O(N D) to O(N² D)
- Clustering: O(N k) per interval for k-means, or O(N² / number_of_intervals) for hierarchical
- Nerve construction: O(number_of_clusters²)
- Total: typically O(N² D) dominated by filter/clustering

**Limitations:**
- Highly parameter-dependent (filter function, interval count, overlap, clustering method)
- No convergence guarantee to true manifold topology in general
- Output depends heavily on filter function choice
- Not designed for embedding — produces topological summary only

**Key reference:** Singh G, Memoli F, Carlsson G (2007). Topological Methods for the Analysis of High Dimensional Data Sets and 3D Object Recognition. SPBG.

## 3. Comparative Notes (vs Phase 1 Spectral Methods)

| Property | Spectral | Geometric | Topological |
|----------|----------|-----------|-------------|
| Produces embedding | Yes | Yes | No (summary only) |
| Bi-Lipschitz guarantee | JMS only | No | N/A |
| Density independence | Diffusion maps (α=1) | No (except LTSA) | Yes |
| Handles non-convex | Yes | ISOMAP: No | Yes |
| Scalability | O(Nkd) sparse | O(N² log N) ISOMAP | O(N³) PH |
| Multiscale | Diffusion maps | No | Yes (filtration) |
| Noise robustness | Moderate-Strong | Weak-Moderate | Strong (stability) |

## RESEARCH COMPLETE
