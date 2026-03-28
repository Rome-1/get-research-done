"""Stage 2: Cross-sample manifold correspondence.

Compute manifold descriptors (dimension, topology, eigenvalue spectrum, centroid)
and match manifolds across conditions via Hungarian algorithm.
"""

import numpy as np
from dataclasses import dataclass
from scipy.optimize import linear_sum_assignment

from .topology import compute_persistence, PersistenceResult
from .stage1_decompose import DecompositionResult


@dataclass
class ManifoldDescriptor:
    """Summary descriptor for a single manifold."""
    condition: str
    manifold_id: int
    n_points: int
    intrinsic_dim: float
    betti: list[int]
    eigenvalues: np.ndarray  # top-k eigenvalues of local covariance
    centroid: np.ndarray
    persistence: PersistenceResult


@dataclass
class ManifoldMatch:
    """A matched pair of manifolds across two conditions."""
    condition_a: str
    condition_b: str
    manifold_a: int
    manifold_b: int  # -1 if no match (null assignment)
    cost: float


def estimate_intrinsic_dimension(eigenvalues: np.ndarray) -> float:
    """Estimate intrinsic dimension from eigenvalue decay.

    Uses the participation ratio: (Σ λ_i)² / Σ λ_i²
    This gives ~d for a d-dimensional manifold with comparable eigenvalues.
    """
    eigs = eigenvalues[eigenvalues > 0]
    if len(eigs) == 0:
        return 1.0
    pr = (eigs.sum() ** 2) / (eigs ** 2).sum()
    return float(pr)


def compute_manifold_descriptor(
    points: np.ndarray,
    condition: str,
    manifold_id: int,
    max_ph_points: int = 500,
) -> ManifoldDescriptor:
    """Compute descriptor for a single manifold's point cloud."""
    # Eigenvalue spectrum from covariance
    if points.shape[0] < 3:
        eigenvalues = np.ones(1)
    else:
        cov = np.cov(points.T)
        eigenvalues = np.linalg.eigvalsh(cov)[::-1]  # descending
        eigenvalues = np.maximum(eigenvalues, 0)

    # Intrinsic dimension
    dim = estimate_intrinsic_dimension(eigenvalues)

    # Persistent homology
    persistence = compute_persistence(
        points,
        max_dim=2,
        max_points=max_ph_points,
    )

    # Centroid
    centroid = points.mean(axis=0)

    return ManifoldDescriptor(
        condition=condition,
        manifold_id=manifold_id,
        n_points=points.shape[0],
        intrinsic_dim=dim,
        betti=persistence.betti,
        eigenvalues=eigenvalues[:20],  # keep top 20
        centroid=centroid,
        persistence=persistence,
    )


def compute_all_descriptors(
    decompositions: dict[str, tuple[DecompositionResult, np.ndarray]],
    max_ph_points: int = 500,
) -> dict[str, list[ManifoldDescriptor]]:
    """Compute descriptors for all manifolds in all conditions.

    Args:
        decompositions: {condition: (DecompositionResult, X_pca)}

    Returns:
        {condition: [ManifoldDescriptor, ...]}
    """
    all_descriptors = {}

    for condition, (decomp, X) in decompositions.items():
        print(f"  Computing descriptors for {condition} ({decomp.k} manifolds)")
        descriptors = []
        for j in range(decomp.k):
            mask = decomp.labels == j
            points = X[mask]
            if points.shape[0] < 3:
                continue
            desc = compute_manifold_descriptor(
                points, condition, j, max_ph_points
            )
            descriptors.append(desc)
            print(f"    Manifold {j}: n={desc.n_points}, dim≈{desc.intrinsic_dim:.1f}, "
                  f"β={desc.betti}")
        all_descriptors[condition] = descriptors

    return all_descriptors


def descriptor_distance(a: ManifoldDescriptor, b: ManifoldDescriptor) -> float:
    """Compute distance between two manifold descriptors.

    Combines dimension, topology, eigenvalue spectrum, and centroid.
    """
    # Dimension distance (weight: 2.0)
    dim_dist = abs(a.intrinsic_dim - b.intrinsic_dim)

    # Topological distance: L1 on Betti numbers (weight: 3.0)
    max_len = max(len(a.betti), len(b.betti))
    betti_a = list(a.betti) + [0] * (max_len - len(a.betti))
    betti_b = list(b.betti) + [0] * (max_len - len(b.betti))
    topo_dist = sum(abs(ba - bb) for ba, bb in zip(betti_a, betti_b))

    # Eigenvalue spectrum distance (weight: 1.0)
    # Normalize and compare
    max_len = max(len(a.eigenvalues), len(b.eigenvalues))
    ea = np.zeros(max_len)
    eb = np.zeros(max_len)
    ea[:len(a.eigenvalues)] = a.eigenvalues
    eb[:len(b.eigenvalues)] = b.eigenvalues
    # Normalize
    ea_norm = ea / (ea.sum() + 1e-10)
    eb_norm = eb / (eb.sum() + 1e-10)
    spec_dist = float(np.sqrt(np.sum((ea_norm - eb_norm) ** 2)))

    # Centroid distance (weight: 0.5)
    min_len = min(len(a.centroid), len(b.centroid))
    cent_dist = float(np.linalg.norm(a.centroid[:min_len] - b.centroid[:min_len]))
    # Normalize by typical scale
    cent_dist /= (np.linalg.norm(a.centroid) + np.linalg.norm(b.centroid) + 1e-10)

    return 2.0 * dim_dist + 3.0 * topo_dist + 1.0 * spec_dist + 0.5 * cent_dist


def match_manifolds(
    descriptors_a: list[ManifoldDescriptor],
    descriptors_b: list[ManifoldDescriptor],
    null_cost: float = 20.0,
) -> list[ManifoldMatch]:
    """Match manifolds between two conditions via Hungarian algorithm.

    Args:
        descriptors_a: manifold descriptors from condition A
        descriptors_b: manifold descriptors from condition B
        null_cost: cost of assigning a manifold to null (no match)

    Returns:
        List of ManifoldMatch objects
    """
    ka, kb = len(descriptors_a), len(descriptors_b)
    if ka == 0 or kb == 0:
        return []

    # Build cost matrix with null padding
    max_k = max(ka, kb)
    cost_matrix = np.full((max_k, max_k), null_cost)

    for i in range(ka):
        for j in range(kb):
            # Dimension filter: skip pairs with very different dimensions
            if abs(descriptors_a[i].intrinsic_dim - descriptors_b[j].intrinsic_dim) > 5:
                cost_matrix[i, j] = null_cost * 2  # strongly discourage
            else:
                cost_matrix[i, j] = descriptor_distance(descriptors_a[i], descriptors_b[j])

    # Hungarian algorithm
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    matches = []
    for r, c in zip(row_ind, col_ind):
        if r < ka:
            cond_a = descriptors_a[r].condition
            mid_a = descriptors_a[r].manifold_id
        else:
            continue  # padding row, skip

        mid_b = -1
        cond_b = descriptors_b[0].condition if kb > 0 else ""
        if c < kb:
            mid_b = descriptors_b[c].manifold_id
            cond_b = descriptors_b[c].condition

        matches.append(ManifoldMatch(
            condition_a=cond_a,
            condition_b=cond_b,
            manifold_a=mid_a,
            manifold_b=mid_b,
            cost=float(cost_matrix[r, c]),
        ))

    return matches


def match_all_conditions(
    all_descriptors: dict[str, list[ManifoldDescriptor]],
) -> dict[tuple[str, str], list[ManifoldMatch]]:
    """Match manifolds across all pairs of conditions.

    Returns:
        {(cond_a, cond_b): [ManifoldMatch, ...]}
    """
    conditions = list(all_descriptors.keys())
    all_matches = {}

    for i in range(len(conditions)):
        for j in range(i + 1, len(conditions)):
            ca, cb = conditions[i], conditions[j]
            print(f"  Matching {ca} ↔ {cb}")
            matches = match_manifolds(
                all_descriptors[ca],
                all_descriptors[cb],
            )
            all_matches[(ca, cb)] = matches
            for m in matches:
                status = f"M{m.manifold_a}↔M{m.manifold_b}" if m.manifold_b >= 0 else f"M{m.manifold_a}↔∅"
                print(f"    {status} (cost={m.cost:.2f})")

    return all_matches
