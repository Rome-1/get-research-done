"""Intrinsic dimensionality estimation for transformer activations.

Implements multiple estimators to characterize the local and global
dimensionality of the activation manifold:

1. Two-NN (Facco et al. 2017) — ratio of nearest neighbor distances
2. Local PCA — participation ratio of local covariance eigenvalues
3. Correlation dimension — Grassberger-Procaccia scaling
4. Per-feature-region dimension — ID conditioned on SAE feature activation

The key question: is the intrinsic dimension uniform (flat manifold) or
does it vary spatially (polytope boundary structure)?
"""

import numpy as np
from dataclasses import dataclass, field
from scipy.spatial import KDTree


@dataclass
class DimensionEstimate:
    """Result of intrinsic dimension estimation."""
    method: str
    global_dim: float
    local_dims: np.ndarray  # per-point or per-region estimates
    std: float
    metadata: dict = field(default_factory=dict)


def two_nn_dimension(X: np.ndarray, fraction: float = 0.9) -> DimensionEstimate:
    """Two-NN intrinsic dimension estimator (Facco et al. 2017).

    Uses the ratio μ = r₂/r₁ of second to first nearest neighbor distances.
    Under the assumption that points are locally uniform on a d-dimensional
    manifold, P(μ > t) = t^(-d), so d = -1/slope of log-log empirical CDF.

    The estimator is:
        d = N / Σᵢ log(μᵢ)

    where μᵢ = r₂ᵢ/r₁ᵢ and we trim the top (1-fraction) of μ values
    to reduce sensitivity to outliers.
    """
    N, D = X.shape
    tree = KDTree(X)
    # k=3: self + 2 nearest neighbors
    dists, _ = tree.query(X, k=3)
    r1 = dists[:, 1]  # distance to 1st NN (skip self at 0)
    r2 = dists[:, 2]  # distance to 2nd NN

    # Avoid division by zero
    valid = r1 > 1e-12
    mu = r2[valid] / r1[valid]

    # Trim outliers
    mu_sorted = np.sort(mu)
    n_keep = int(len(mu_sorted) * fraction)
    mu_trimmed = mu_sorted[:n_keep]

    # MLE estimate: d = n / sum(log(mu))
    log_mu = np.log(mu_trimmed)
    d_global = n_keep / log_mu.sum()

    # Bootstrap confidence interval
    rng = np.random.RandomState(42)
    d_boots = []
    for _ in range(100):
        idx = rng.choice(n_keep, n_keep, replace=True)
        d_boots.append(len(idx) / log_mu[idx].sum())
    d_std = np.std(d_boots)

    return DimensionEstimate(
        method="two_nn",
        global_dim=float(d_global),
        local_dims=np.full(N, d_global),  # Two-NN is a global estimator
        std=float(d_std),
        metadata={"n_valid": int(valid.sum()), "fraction": fraction},
    )


def local_pca_dimension(
    X: np.ndarray,
    k_neighbors: int = 50,
    threshold: float = 0.95,
) -> DimensionEstimate:
    """Local PCA intrinsic dimension via participation ratio.

    For each point, compute PCA on its k nearest neighbors. The intrinsic
    dimension is estimated via the participation ratio:
        d = (Σ λᵢ)² / Σ λᵢ²

    This gives a smooth estimate that equals the number of significant
    dimensions. Alternative: count eigenvalues capturing `threshold` variance.

    Returns per-point dimension estimates — crucial for detecting whether
    the activation space has spatially varying dimension (polytope boundaries
    vs interiors).
    """
    N, D = X.shape
    tree = KDTree(X)
    _, indices = tree.query(X, k=k_neighbors + 1)
    # Drop self
    indices = indices[:, 1:]

    local_dims = np.zeros(N)
    local_dims_threshold = np.zeros(N)

    for i in range(N):
        neighbors = X[indices[i]]
        centered = neighbors - neighbors.mean(axis=0)
        # Use SVD for numerical stability
        _, s, _ = np.linalg.svd(centered, full_matrices=False)
        eigenvalues = s ** 2 / (k_neighbors - 1)

        # Participation ratio
        total = eigenvalues.sum()
        if total > 0:
            local_dims[i] = total ** 2 / (eigenvalues ** 2).sum()

        # Threshold-based (how many components for 95% variance)
        cumvar = np.cumsum(eigenvalues) / total if total > 0 else np.zeros_like(eigenvalues)
        local_dims_threshold[i] = np.searchsorted(cumvar, threshold) + 1

    return DimensionEstimate(
        method="local_pca",
        global_dim=float(np.median(local_dims)),
        local_dims=local_dims,
        std=float(np.std(local_dims)),
        metadata={
            "k_neighbors": k_neighbors,
            "threshold_dim_median": float(np.median(local_dims_threshold)),
            "threshold_dim_std": float(np.std(local_dims_threshold)),
            "dim_histogram": np.histogram(local_dims, bins=50)[0].tolist(),
        },
    )


def correlation_dimension(
    X: np.ndarray,
    n_points: int = 1000,
    n_radii: int = 30,
    seed: int = 42,
) -> DimensionEstimate:
    """Grassberger-Procaccia correlation dimension.

    Counts the fraction of point pairs within radius r:
        C(r) = (2 / N(N-1)) Σ_{i<j} 1[||x_i - x_j|| < r]

    The correlation dimension d_c is the slope of log C(r) vs log r
    in the scaling regime. Uses linear regression on the middle portion
    of the log-log curve.
    """
    N, D = X.shape
    if N > n_points:
        rng = np.random.RandomState(seed)
        idx = rng.choice(N, n_points, replace=False)
        X_sub = X[idx]
    else:
        X_sub = X
    N_sub = X_sub.shape[0]

    # Pairwise distances (upper triangle)
    from scipy.spatial.distance import pdist
    distances = pdist(X_sub, metric="euclidean")

    # Radius range: from 10th to 90th percentile of distances
    r_min = np.percentile(distances, 5)
    r_max = np.percentile(distances, 80)
    radii = np.geomspace(max(r_min, 1e-10), r_max, n_radii)

    # Correlation integral
    n_pairs = len(distances)
    C = np.array([np.sum(distances < r) / n_pairs for r in radii])

    # Filter out zeros for log
    valid = C > 0
    log_r = np.log(radii[valid])
    log_C = np.log(C[valid])

    # Linear fit on middle 60% of the valid range
    n_valid = len(log_r)
    start = n_valid // 5
    end = 4 * n_valid // 5
    if end - start < 3:
        start, end = 0, n_valid

    from numpy.polynomial import polynomial as P
    coeffs = np.polyfit(log_r[start:end], log_C[start:end], 1)
    d_corr = coeffs[0]

    return DimensionEstimate(
        method="correlation",
        global_dim=float(d_corr),
        local_dims=np.full(N, d_corr),
        std=0.0,  # single estimate
        metadata={
            "n_points_used": N_sub,
            "n_radii": n_radii,
            "r_range": [float(r_min), float(r_max)],
            "log_r": log_r.tolist(),
            "log_C": log_C.tolist(),
        },
    )


def dimension_by_feature_region(
    X: np.ndarray,
    feature_acts: np.ndarray,
    top_k_features: int = 20,
    k_neighbors: int = 30,
    min_region_size: int = 30,
) -> dict:
    """Estimate intrinsic dimension conditioned on SAE feature activation.

    For each of the top-k most active features, partition points into
    "feature active" (f_k > 0) and "feature inactive" (f_k = 0) and
    estimate local dimension in each region.

    Key hypothesis: if the geometry is a hyperplane arrangement, the
    dimension should DROP at feature boundaries (where ReLU transitions
    from 0 to active), because the boundary is a codimension-1 face.
    """
    N, n_features = feature_acts.shape

    # Find top-k features by frequency of activation
    active_counts = (feature_acts > 0).sum(axis=0)
    # Filter to features active on at least min_region_size tokens
    eligible = np.where(active_counts >= min_region_size)[0]
    if len(eligible) == 0:
        return {"error": "No features with enough active tokens"}

    # Sort by activation count, take top-k
    sorted_eligible = eligible[np.argsort(active_counts[eligible])[::-1]]
    selected = sorted_eligible[:top_k_features]

    results = []
    for feat_id in selected:
        mask_active = feature_acts[:, feat_id] > 0
        mask_inactive = ~mask_active

        n_active = mask_active.sum()
        n_inactive = mask_inactive.sum()

        entry = {
            "feature_id": int(feat_id),
            "n_active": int(n_active),
            "n_inactive": int(n_inactive),
            "activation_rate": float(n_active / N),
        }

        # Dimension in active region
        if n_active >= min_region_size:
            k = min(k_neighbors, n_active - 1)
            if k >= 3:
                dim_active = _local_dim_subset(X[mask_active], k)
                entry["dim_active"] = float(dim_active)

        # Dimension in inactive region
        if n_inactive >= min_region_size:
            k = min(k_neighbors, n_inactive - 1)
            if k >= 3:
                dim_inactive = _local_dim_subset(X[mask_inactive], k)
                entry["dim_inactive"] = float(dim_inactive)

        # Dimension near the boundary (points close to threshold)
        acts_feat = feature_acts[:, feat_id]
        threshold = np.percentile(acts_feat[acts_feat > 0], 10)
        near_boundary = (acts_feat > 0) & (acts_feat < threshold)
        n_boundary = near_boundary.sum()
        entry["n_boundary"] = int(n_boundary)
        if n_boundary >= min_region_size:
            k = min(k_neighbors, n_boundary - 1)
            if k >= 3:
                dim_boundary = _local_dim_subset(X[near_boundary], k)
                entry["dim_boundary"] = float(dim_boundary)

        results.append(entry)

    return {
        "n_features_analyzed": len(results),
        "features": results,
    }


def _local_dim_subset(X_sub: np.ndarray, k: int) -> float:
    """Compute median local PCA dimension for a subset of points."""
    tree = KDTree(X_sub)
    _, indices = tree.query(X_sub, k=k + 1)
    indices = indices[:, 1:]

    dims = []
    for i in range(len(X_sub)):
        neighbors = X_sub[indices[i]]
        centered = neighbors - neighbors.mean(axis=0)
        _, s, _ = np.linalg.svd(centered, full_matrices=False)
        eig = s ** 2 / (k - 1)
        total = eig.sum()
        if total > 0:
            dims.append(total ** 2 / (eig ** 2).sum())

    return float(np.median(dims)) if dims else 0.0
