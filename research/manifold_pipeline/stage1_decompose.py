"""Stage 1: Multi-manifold decomposition via SMCE.

Sparse Manifold Clustering and Embedding (Elhamifar & Vidal, 2011).
For each point x_i, solve L1-regularized reconstruction from other points.
Sparsity pattern reveals same-manifold neighbors.
"""

import numpy as np
from sklearn.linear_model import Lasso
from sklearn.cluster import SpectralClustering
from joblib import Parallel, delayed
from dataclasses import dataclass


@dataclass
class DecompositionResult:
    """Result of SMCE decomposition for one sample."""
    labels: np.ndarray          # (N,) cluster assignment per point
    k: int                      # number of manifolds found
    affinity: np.ndarray        # (N, N) affinity matrix W
    eigenvalues: np.ndarray     # Laplacian eigenvalues (for eigengap plot)
    local_dims: np.ndarray      # (N,) estimated local dimension per point


def _solve_one_point(i: int, X: np.ndarray, alpha: float, max_iter: int) -> np.ndarray:
    """Solve Lasso for one point: x_i = X_{-i}.T @ c_i."""
    N, D = X.shape
    mask = np.ones(N, dtype=bool)
    mask[i] = False
    X_others = X[mask]  # (N-1, D)

    # Lasso: minimize ||x_i - X_others.T @ c||^2 / (2*D) + alpha * ||c||_1
    # sklearn expects (n_samples, n_features) = (D, N-1)
    lasso = Lasso(
        alpha=alpha,
        max_iter=max_iter,
        tol=1e-4,
        warm_start=False,
        fit_intercept=False,
    )
    lasso.fit(X_others.T, X[i])
    return lasso.coef_  # (N-1,)


def smce(
    X: np.ndarray,
    alpha: float = 0.05,
    max_iter: int = 2000,
    n_jobs: int = -1,
) -> np.ndarray:
    """Sparse Manifold Clustering and Embedding.

    Args:
        X: (N, D) point cloud
        alpha: L1 penalty (higher = sparser = fewer neighbors)
        max_iter: max Lasso iterations
        n_jobs: parallel jobs (-1 = all cores)

    Returns:
        W: (N, N) symmetric affinity matrix
    """
    N = X.shape[0]

    # Normalize columns to unit variance for stable Lasso
    from sklearn.preprocessing import StandardScaler
    X = StandardScaler().fit_transform(X)

    print(f"  SMCE: solving {N} Lasso problems (alpha={alpha})...")

    # Solve all points in parallel
    coeffs = Parallel(n_jobs=n_jobs, verbose=1)(
        delayed(_solve_one_point)(i, X, alpha, max_iter)
        for i in range(N)
    )

    # Build coefficient matrix Z
    Z = np.zeros((N, N))
    for i, c in enumerate(coeffs):
        mask = np.ones(N, dtype=bool)
        mask[i] = False
        Z[i, mask] = c

    # Symmetric affinity
    W = np.abs(Z) + np.abs(Z.T)
    return W


def estimate_local_dims(Z: np.ndarray) -> np.ndarray:
    """Estimate local dimension per point from SMCE coefficient sparsity.

    A point on a d-dimensional manifold typically has ~d+1 nonzero coefficients.
    """
    nnz_per_point = np.count_nonzero(Z, axis=1)
    # local dim ≈ nnz - 1 (d+1 neighbors for d-dim manifold)
    local_dims = np.maximum(nnz_per_point - 1, 1)
    return local_dims


def determine_k(W: np.ndarray, max_k: int = 15) -> tuple[int, np.ndarray]:
    """Determine number of manifolds from eigengap of the graph Laplacian.

    Returns (k, eigenvalues).
    """
    from scipy.sparse.csgraph import laplacian
    from scipy.linalg import eigvalsh

    # Normalized Laplacian eigenvalues
    D = np.diag(W.sum(axis=1))
    L = D - W

    # Add small regularization for numerical stability
    D_reg = D + 1e-10 * np.eye(len(D))

    # Compute smallest eigenvalues of generalized problem L v = lambda D v
    eigenvalues = eigvalsh(L, D_reg)
    eigenvalues = np.sort(np.real(eigenvalues))

    # Find eigengap: largest relative jump in first max_k eigenvalues
    eigs_subset = eigenvalues[1:max_k + 1]  # skip λ_0 ≈ 0
    if len(eigs_subset) < 2:
        return 2, eigenvalues

    gaps = np.diff(eigs_subset)
    # Use relative gap (ratio of consecutive eigenvalues) for robustness
    # Avoid division by zero
    relative_gaps = gaps / (eigs_subset[:-1] + 1e-10)

    k = np.argmax(relative_gaps) + 2  # +2: +1 for diff, +1 for skipping λ_0
    k = max(k, 2)  # at least 2 manifolds
    k = min(k, max_k)

    return k, eigenvalues


def decompose(
    X: np.ndarray,
    alpha: float = 0.05,
    max_k: int = 15,
    max_iter: int = 2000,
    n_jobs: int = -1,
) -> DecompositionResult:
    """Full Stage 1: SMCE decomposition of a point cloud.

    Args:
        X: (N, D) point cloud (PCA-reduced activations)
        alpha: SMCE L1 penalty
        max_k: upper bound on number of manifolds
        max_iter: Lasso max iterations
        n_jobs: parallel jobs

    Returns:
        DecompositionResult with labels, k, affinity, eigenvalues, local_dims
    """
    # Step 1: SMCE
    W = smce(X, alpha=alpha, max_iter=max_iter, n_jobs=n_jobs)

    # Step 2: Determine k from eigengap
    k, eigenvalues = determine_k(W, max_k=max_k)
    print(f"  Eigengap analysis: k={k} manifolds")

    # Step 3: Spectral clustering
    # Use precomputed affinity
    clustering = SpectralClustering(
        n_clusters=k,
        affinity="precomputed",
        random_state=42,
        assign_labels="kmeans",
        n_init=10,
    )
    labels = clustering.fit_predict(W)

    # Step 4: Local dimension estimates
    # Build Z from W (W = |Z| + |Z^T|, so Z ≈ W/2 as approximation)
    local_dims = estimate_local_dims(W / 2)

    # Report
    for j in range(k):
        mask = labels == j
        n_pts = mask.sum()
        med_dim = np.median(local_dims[mask])
        print(f"  Manifold {j}: {n_pts} points, median local dim ≈ {med_dim:.0f}")

    return DecompositionResult(
        labels=labels,
        k=k,
        affinity=W,
        eigenvalues=eigenvalues,
        local_dims=local_dims,
    )
