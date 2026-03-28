"""Stage 3: Variation scoring with statistical significance.

For each matched manifold, compute topological, geometric, and dimensional
variation across conditions. Permutation test for significance.
"""

import numpy as np
from dataclasses import dataclass

from .topology import wasserstein_distance_diagrams
from .stage2_match import ManifoldDescriptor, ManifoldMatch


@dataclass
class VariationScore:
    """Variation score for a matched manifold pair."""
    manifold_a_id: int
    manifold_b_id: int
    condition_a: str
    condition_b: str
    v_topo: float       # topological variation
    v_geom: float       # geometric variation (eigenvalue spectrum)
    v_dim: float         # dimensional variation
    v_combined: float    # weighted combination
    p_value: float       # permutation test p-value


def topological_variation(
    desc_a: ManifoldDescriptor,
    desc_b: ManifoldDescriptor,
) -> float:
    """Compute topological variation between two manifolds.

    Uses Wasserstein distance on persistence diagrams across all homology dims.
    """
    total = 0.0
    for dim in range(min(len(desc_a.persistence.diagrams), len(desc_b.persistence.diagrams))):
        d = wasserstein_distance_diagrams(
            desc_a.persistence.diagrams[dim],
            desc_b.persistence.diagrams[dim],
        )
        total += d
    return total


def geometric_variation(
    desc_a: ManifoldDescriptor,
    desc_b: ManifoldDescriptor,
) -> float:
    """Compute geometric variation via eigenvalue spectrum divergence.

    Uses Jensen-Shannon-like divergence on normalized eigenvalue spectra.
    """
    # Normalize eigenvalue spectra to distributions
    max_len = max(len(desc_a.eigenvalues), len(desc_b.eigenvalues))
    ea = np.zeros(max_len)
    eb = np.zeros(max_len)
    ea[:len(desc_a.eigenvalues)] = desc_a.eigenvalues
    eb[:len(desc_b.eigenvalues)] = desc_b.eigenvalues

    # Normalize to probability distributions
    ea_sum, eb_sum = ea.sum(), eb.sum()
    if ea_sum < 1e-10 or eb_sum < 1e-10:
        return 0.0

    pa = ea / ea_sum
    pb = eb / eb_sum

    # Jensen-Shannon divergence
    m = 0.5 * (pa + pb)
    # Avoid log(0)
    mask = m > 0
    jsd = 0.0
    if np.any(pa[mask] > 0):
        jsd += 0.5 * np.sum(pa[mask] * np.log(pa[mask] / m[mask]))
    if np.any(pb[mask] > 0):
        jsd += 0.5 * np.sum(pb[mask] * np.log(pb[mask] / m[mask]))

    return float(np.sqrt(max(jsd, 0)))  # sqrt for metric property


def dimensional_variation(
    desc_a: ManifoldDescriptor,
    desc_b: ManifoldDescriptor,
) -> float:
    """Absolute difference in estimated intrinsic dimension."""
    return abs(desc_a.intrinsic_dim - desc_b.intrinsic_dim)


def combined_score(
    v_topo: float,
    v_geom: float,
    v_dim: float,
    w_topo: float = 1.0,
    w_geom: float = 1.0,
    w_dim: float = 0.5,
) -> float:
    """Weighted combination of variation scores."""
    return w_topo * v_topo + w_geom * v_geom + w_dim * v_dim


def permutation_test(
    points_a: np.ndarray,
    points_b: np.ndarray,
    observed_score: float,
    n_permutations: int = 1000,
    seed: int = 42,
) -> float:
    """Permutation test for manifold variation significance.

    Pool points from both manifolds, randomly re-partition,
    compute variation score on permuted partitions.
    """
    rng = np.random.RandomState(seed)
    pooled = np.concatenate([points_a, points_b], axis=0)
    n_a = points_a.shape[0]

    null_scores = []
    for _ in range(n_permutations):
        perm = rng.permutation(len(pooled))
        perm_a = pooled[perm[:n_a]]
        perm_b = pooled[perm[n_a:]]

        # Quick geometric variation only (topology too expensive per permutation)
        cov_a = np.cov(perm_a.T) if perm_a.shape[0] > 2 else np.eye(perm_a.shape[1])
        cov_b = np.cov(perm_b.T) if perm_b.shape[0] > 2 else np.eye(perm_b.shape[1])
        eigs_a = np.maximum(np.linalg.eigvalsh(cov_a)[::-1], 0)
        eigs_b = np.maximum(np.linalg.eigvalsh(cov_b)[::-1], 0)

        # Normalized spectrum distance
        max_len = max(len(eigs_a), len(eigs_b))
        ea, eb = np.zeros(max_len), np.zeros(max_len)
        ea[:len(eigs_a)] = eigs_a
        eb[:len(eigs_b)] = eigs_b
        pa = ea / (ea.sum() + 1e-10)
        pb = eb / (eb.sum() + 1e-10)
        null_scores.append(float(np.sqrt(np.sum((pa - pb) ** 2))))

    p_value = float(np.mean(np.array(null_scores) >= observed_score))
    return max(p_value, 1.0 / (n_permutations + 1))  # avoid exact 0


def score_all_matches(
    all_descriptors: dict[str, list[ManifoldDescriptor]],
    all_matches: dict[tuple[str, str], list],
    decompositions: dict[str, tuple],
    n_permutations: int = 1000,
) -> list[VariationScore]:
    """Score all matched manifold pairs across conditions.

    Returns list of VariationScore sorted by combined score (descending).
    """
    scores = []

    for (ca, cb), matches in all_matches.items():
        descs_a = {d.manifold_id: d for d in all_descriptors[ca]}
        descs_b = {d.manifold_id: d for d in all_descriptors[cb]}
        decomp_a, X_a = decompositions[ca]
        decomp_b, X_b = decompositions[cb]

        for match in matches:
            if match.manifold_b < 0:
                continue  # null match, skip

            da = descs_a.get(match.manifold_a)
            db = descs_b.get(match.manifold_b)
            if da is None or db is None:
                continue

            # Compute variation scores
            vt = topological_variation(da, db)
            vg = geometric_variation(da, db)
            vd = dimensional_variation(da, db)
            vc = combined_score(vt, vg, vd)

            # Permutation test
            pts_a = X_a[decomp_a.labels == match.manifold_a]
            pts_b = X_b[decomp_b.labels == match.manifold_b]
            pval = permutation_test(pts_a, pts_b, vg, n_permutations)

            scores.append(VariationScore(
                manifold_a_id=match.manifold_a,
                manifold_b_id=match.manifold_b,
                condition_a=ca,
                condition_b=cb,
                v_topo=vt,
                v_geom=vg,
                v_dim=vd,
                v_combined=vc,
                p_value=pval,
            ))

            print(f"  {ca}/M{match.manifold_a} ↔ {cb}/M{match.manifold_b}: "
                  f"V_topo={vt:.3f} V_geom={vg:.3f} V_dim={vd:.1f} "
                  f"V_combined={vc:.3f} p={pval:.4f}")

    # Sort by combined score descending
    scores.sort(key=lambda s: s.v_combined, reverse=True)
    return scores
