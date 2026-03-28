"""Stage 4: Deep characterization of top-varying manifolds.

Diffusion maps (alpha=1) for density-independent coordinates,
feature identification connecting back to input tokens.
"""

import numpy as np
from dataclasses import dataclass
from scipy.spatial.distance import cdist


@dataclass
class DiffusionMapResult:
    """Result of diffusion map embedding."""
    coordinates: np.ndarray     # (N, n_components) embedding
    eigenvalues: np.ndarray     # eigenvalues of Markov matrix
    eigenvectors: np.ndarray    # eigenvectors


@dataclass
class ManifoldCharacterization:
    """Full characterization of a manifold."""
    condition: str
    manifold_id: int
    n_points: int
    intrinsic_dim: float
    betti: list[int]
    diffusion_map: DiffusionMapResult
    token_associations: dict | None  # token -> activation count


def diffusion_map(
    X: np.ndarray,
    n_components: int = 5,
    alpha: float = 1.0,
    epsilon: str | float = "auto",
) -> DiffusionMapResult:
    """Compute diffusion map embedding with alpha-normalization.

    Args:
        X: (N, D) point cloud
        n_components: number of diffusion coordinates
        alpha: density normalization exponent (1.0 = density-independent)
        epsilon: kernel bandwidth ("auto" = median of pairwise distances)

    Returns:
        DiffusionMapResult with coordinates and spectrum
    """
    N = X.shape[0]

    # Step 1: Pairwise distances
    dists = cdist(X, X, metric="euclidean")

    # Step 2: Kernel bandwidth
    if epsilon == "auto":
        # Use median of k-nearest-neighbor distances
        k = min(20, N // 5)
        knn_dists = np.sort(dists, axis=1)[:, 1:k + 1]  # exclude self
        epsilon_val = float(np.median(knn_dists)) ** 2
    else:
        epsilon_val = float(epsilon)

    # Step 3: Gaussian kernel
    K = np.exp(-dists ** 2 / (2 * epsilon_val))

    # Step 4: Alpha-normalization (density correction)
    # q(x) = sum_y K(x, y) ≈ density at x
    q = K.sum(axis=1)
    q[q < 1e-10] = 1e-10

    # K^(alpha)(x, y) = K(x, y) / (q(x)^alpha * q(y)^alpha)
    K_alpha = K / np.outer(q ** alpha, q ** alpha)

    # Step 5: Row-normalize to Markov matrix
    row_sums = K_alpha.sum(axis=1)
    row_sums[row_sums < 1e-10] = 1e-10
    P = K_alpha / row_sums[:, np.newaxis]

    # Step 6: Eigendecomposition
    # P is not symmetric, but P_sym = D^{1/2} P D^{-1/2} is
    # For simplicity, use eigendecomposition of P directly
    eigenvalues, eigenvectors = np.linalg.eigh(
        0.5 * (P + P.T)  # symmetrize for numerical stability
    )

    # Sort descending (eigh returns ascending)
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]

    # Skip trivial eigenvalue/vector (λ_0 = 1, ψ_0 = const)
    coords = eigenvectors[:, 1:n_components + 1]
    # Scale by eigenvalues (diffusion map at t=1)
    eig_scale = eigenvalues[1:n_components + 1]
    coords = coords * eig_scale[np.newaxis, :]

    return DiffusionMapResult(
        coordinates=coords,
        eigenvalues=eigenvalues[:n_components + 1],
        eigenvectors=eigenvectors[:, :n_components + 1],
    )


def characterize_manifold(
    points: np.ndarray,
    condition: str,
    manifold_id: int,
    intrinsic_dim: float,
    betti: list[int],
    n_components: int = 5,
    alpha: float = 1.0,
) -> ManifoldCharacterization:
    """Full characterization of a single manifold.

    Args:
        points: (N, D) manifold point cloud
        condition: condition name
        manifold_id: manifold index
        intrinsic_dim: estimated intrinsic dimension
        betti: Betti numbers
        n_components: diffusion map components
        alpha: diffusion map density normalization

    Returns:
        ManifoldCharacterization
    """
    # Compute diffusion map
    n_comp = min(n_components, points.shape[0] - 2)
    dm = diffusion_map(points, n_components=n_comp, alpha=alpha)

    return ManifoldCharacterization(
        condition=condition,
        manifold_id=manifold_id,
        n_points=points.shape[0],
        intrinsic_dim=intrinsic_dim,
        betti=betti,
        diffusion_map=dm,
        token_associations=None,
    )


def characterize_top_manifolds(
    scores: list,
    all_descriptors: dict[str, list],
    decompositions: dict[str, tuple],
    top_k: int = 3,
    n_components: int = 5,
) -> list[ManifoldCharacterization]:
    """Characterize the top-k most varying manifolds.

    Returns list of ManifoldCharacterization for the highest-variation manifolds.
    """
    characterizations = []
    seen = set()

    for score in scores[:top_k * 2]:  # extra to handle deduplication
        if len(characterizations) >= top_k:
            break

        for cond, mid in [
            (score.condition_a, score.manifold_a_id),
            (score.condition_b, score.manifold_b_id),
        ]:
            key = (cond, mid)
            if key in seen:
                continue
            seen.add(key)

            decomp, X = decompositions[cond]
            points = X[decomp.labels == mid]
            if points.shape[0] < 5:
                continue

            # Find descriptor
            desc = None
            for d in all_descriptors[cond]:
                if d.manifold_id == mid:
                    desc = d
                    break

            if desc is None:
                continue

            print(f"  Characterizing {cond}/M{mid} ({points.shape[0]} points)")
            char = characterize_manifold(
                points, cond, mid,
                desc.intrinsic_dim, desc.betti,
                n_components=n_components,
            )
            characterizations.append(char)
            print(f"    Diffusion eigenvalues: {char.diffusion_map.eigenvalues[:5]}")

            if len(characterizations) >= top_k:
                break

    return characterizations
