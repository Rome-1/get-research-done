"""Persistent homology computation via giotto-tda or fallback scipy."""

import numpy as np
from dataclasses import dataclass


@dataclass
class PersistenceResult:
    """Persistence diagram and derived quantities."""
    diagrams: list[np.ndarray]   # list of (n_features, 2) per homology dim
    betti: list[int]             # Betti numbers [β₀, β₁, β₂]
    max_persistence: list[float] # max persistence per dimension


def compute_persistence(
    points: np.ndarray,
    max_dim: int = 2,
    max_points: int = 500,
    persistence_threshold: float = 0.1,
) -> PersistenceResult:
    """Compute persistent homology of a point cloud.

    Args:
        points: (N, D) point cloud
        max_dim: maximum homology dimension
        max_points: subsample if N exceeds this (PH is O(N^3))
        persistence_threshold: minimum persistence to count as a real feature

    Returns:
        PersistenceResult with diagrams, Betti numbers, max persistence
    """
    # Subsample if needed
    if points.shape[0] > max_points:
        rng = np.random.RandomState(42)
        idx = rng.choice(points.shape[0], max_points, replace=False)
        points = points[idx]

    try:
        return _compute_with_giotto(points, max_dim, persistence_threshold)
    except ImportError:
        return _compute_fallback(points, max_dim, persistence_threshold)


def _compute_with_giotto(
    points: np.ndarray,
    max_dim: int,
    threshold: float,
) -> PersistenceResult:
    """Compute PH using giotto-tda."""
    from gtda.homology import VietorisRipsPersistence

    vr = VietorisRipsPersistence(
        homology_dimensions=list(range(max_dim + 1)),
        max_edge_length=np.inf,
        n_jobs=-1,
    )
    # giotto expects (n_samples, n_points, n_dims) — add batch dim
    diagrams_raw = vr.fit_transform(points[np.newaxis, :, :])[0]
    # diagrams_raw shape: (n_features, 3) where col 2 is homology dim

    diagrams = []
    betti = []
    max_pers = []
    for dim in range(max_dim + 1):
        mask = diagrams_raw[:, 2] == dim
        bd = diagrams_raw[mask, :2]  # (birth, death)

        # Filter infinite features and compute persistence
        finite_mask = np.isfinite(bd[:, 1])
        bd_finite = bd[finite_mask]
        persistence = bd_finite[:, 1] - bd_finite[:, 0] if len(bd_finite) > 0 else np.array([])

        # Count significant features
        n_sig = np.sum(persistence > threshold) if len(persistence) > 0 else 0
        # β₀ should count the infinite feature (connected component)
        if dim == 0:
            n_sig = max(n_sig, 1)  # at least one connected component

        diagrams.append(bd_finite)
        betti.append(int(n_sig))
        max_pers.append(float(persistence.max()) if len(persistence) > 0 else 0.0)

    return PersistenceResult(diagrams=diagrams, betti=betti, max_persistence=max_pers)


def _compute_fallback(
    points: np.ndarray,
    max_dim: int,
    threshold: float,
) -> PersistenceResult:
    """Minimal fallback: compute pairwise distances and estimate H0 only.

    This is a bare-bones fallback when giotto-tda is not available.
    Only computes β₀ via single-linkage clustering.
    """
    from scipy.spatial.distance import pdist, squareform
    from scipy.cluster.hierarchy import fcluster, linkage

    dists = pdist(points)
    Z = linkage(dists, method="single")

    # H0: count clusters at the median distance scale
    median_dist = np.median(dists)
    labels = fcluster(Z, t=median_dist, criterion="distance")
    beta_0 = len(np.unique(labels))

    # H0 persistence diagram: each feature born at 0, dies at merge distance
    # Z has shape (n-1, 4) where column 2 is the merge distance
    h0_diagram = np.column_stack([np.zeros(len(Z)), Z[:, 2]])
    diagrams = [h0_diagram]
    betti = [beta_0] + [0] * max_dim
    max_pers = [float(median_dist)] + [0.0] * max_dim

    return PersistenceResult(diagrams=diagrams, betti=betti, max_persistence=max_pers)


def wasserstein_distance_diagrams(
    diag1: np.ndarray,
    diag2: np.ndarray,
) -> float:
    """Wasserstein distance between two persistence diagrams.

    Each diagram is (n_features, 2) with (birth, death) pairs.
    """
    if len(diag1) == 0 and len(diag2) == 0:
        return 0.0
    if len(diag1) == 0 or len(diag2) == 0:
        # Distance from empty diagram = sum of persistences
        nonempty = diag1 if len(diag1) > 0 else diag2
        return float(np.sum(nonempty[:, 1] - nonempty[:, 0]) / 2)

    try:
        from gtda.diagrams import PairwiseDistance
        # giotto expects (n_samples, n_features, 3) with homology dim
        d1 = np.column_stack([diag1, np.zeros(len(diag1))])[np.newaxis]
        d2 = np.column_stack([diag2, np.zeros(len(diag2))])[np.newaxis]
        # Pad to same number of features
        max_feat = max(d1.shape[1], d2.shape[1])
        if d1.shape[1] < max_feat:
            pad = np.zeros((1, max_feat - d1.shape[1], 3))
            d1 = np.concatenate([d1, pad], axis=1)
        if d2.shape[1] < max_feat:
            pad = np.zeros((1, max_feat - d2.shape[1], 3))
            d2 = np.concatenate([d2, pad], axis=1)
        combined = np.concatenate([d1, d2], axis=0)
        dist_calc = PairwiseDistance(metric="wasserstein")
        dists = dist_calc.fit_transform(combined)
        return float(dists[0, 1])
    except (ImportError, Exception):
        # Fallback: simple bottleneck approximation
        from scipy.spatial.distance import cdist
        pers1 = diag1[:, 1] - diag1[:, 0]
        pers2 = diag2[:, 1] - diag2[:, 0]
        # Pad shorter to match
        max_n = max(len(pers1), len(pers2))
        p1 = np.zeros(max_n)
        p2 = np.zeros(max_n)
        p1[:len(pers1)] = np.sort(pers1)[::-1]
        p2[:len(pers2)] = np.sort(pers2)[::-1]
        return float(np.sum(np.abs(p1 - p2)))
