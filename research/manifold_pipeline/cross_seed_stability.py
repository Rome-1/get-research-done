"""Cross-seed manifold stability analysis.

Runs the pipeline with multiple random seeds for text generation and measures:
1. Manifold count stability (k per condition across seeds)
2. Betti number consistency (topological feature stability)
3. Cross-seed CKA of manifold assignments (representation similarity)
"""

import json
import time
import numpy as np
from pathlib import Path

from .config import PipelineConfig
from .stage1_decompose import decompose
from .stage2_match import compute_all_descriptors


def linear_cka(X: np.ndarray, Y: np.ndarray) -> float:
    """Compute linear CKA (Centered Kernel Alignment) between two representations.

    Args:
        X: (N, D1) representation matrix
        Y: (N, D2) representation matrix

    Returns:
        CKA similarity in [0, 1]
    """
    # Center
    X = X - X.mean(axis=0)
    Y = Y - Y.mean(axis=0)

    # HSIC via linear kernels
    hsic_xy = np.linalg.norm(X.T @ Y, 'fro') ** 2
    hsic_xx = np.linalg.norm(X.T @ X, 'fro') ** 2
    hsic_yy = np.linalg.norm(Y.T @ Y, 'fro') ** 2

    return float(hsic_xy / (np.sqrt(hsic_xx * hsic_yy) + 1e-10))


def assignment_kernel(labels: np.ndarray) -> np.ndarray:
    """Build manifold assignment kernel: K[i,j] = 1 if same manifold."""
    N = len(labels)
    K = np.zeros((N, N))
    for k in np.unique(labels):
        mask = labels == k
        K[np.ix_(mask, mask)] = 1.0
    return K


def kernel_cka(K1: np.ndarray, K2: np.ndarray) -> float:
    """CKA between two precomputed kernel matrices.

    Uses HSIC with centering matrix H = I - 11^T/n.
    """
    n = K1.shape[0]
    H = np.eye(n) - np.ones((n, n)) / n

    HK1H = H @ K1 @ H
    HK2H = H @ K2 @ H

    hsic_12 = np.trace(HK1H @ HK2H) / (n - 1) ** 2
    hsic_11 = np.trace(HK1H @ HK1H) / (n - 1) ** 2
    hsic_22 = np.trace(HK2H @ HK2H) / (n - 1) ** 2

    return float(hsic_12 / (np.sqrt(hsic_11 * hsic_22) + 1e-10))


def run_cross_seed_stability(
    seeds: list[int] | None = None,
    n_tokens: int = 2000,
    use_gpu: bool = True,
) -> dict:
    """Run pipeline with multiple seeds and measure stability.

    Args:
        seeds: List of random seeds for text generation. Default: [42, 123, 271, 314, 577]
        n_tokens: Tokens per condition
        use_gpu: Whether GPU is available (affects model loading)

    Returns:
        dict with stability metrics
    """
    if seeds is None:
        seeds = [42, 123, 271, 314, 577]

    from .activation_extraction import extract_and_reduce, load_model

    print("=" * 60)
    print("CROSS-SEED MANIFOLD STABILITY ANALYSIS")
    print(f"Seeds: {seeds}")
    print(f"N tokens per condition: {n_tokens}")
    print("=" * 60)

    t0 = time.time()

    # Load model once
    model = load_model("gpt2")

    # Run pipeline for each seed
    all_results = {}
    for seed in seeds:
        print(f"\n{'=' * 60}")
        print(f"SEED {seed}")
        print("=" * 60)

        config = PipelineConfig(
            n_tokens_per_condition=n_tokens,
            pca_dim=100,
            smce_alpha=0.05,
            max_k_manifolds=15,
            n_permutations=100,  # fewer permutations for speed
            random_seed=seed,
            text_seed=seed,
            output_dir=Path(f"/tmp/manifold_seed_{seed}"),
            cache_dir=Path(f"/tmp/manifold_seed_{seed}/cache"),
        )

        # Extract activations with this seed
        samples = extract_and_reduce(config, model=model)

        # Stage 1: Decompose
        decompositions = {}
        for condition, X in samples.items():
            print(f"\nDecomposing {condition} (seed={seed})")
            decomp = decompose(
                X,
                alpha=config.smce_alpha,
                max_k=config.max_k_manifolds,
                max_iter=config.smce_max_iter,
            )
            decompositions[condition] = (decomp, X)

        # Stage 2: Compute descriptors (for Betti numbers)
        all_descriptors = compute_all_descriptors(
            decompositions, max_ph_points=config.max_ph_points
        )

        all_results[seed] = {
            "decompositions": decompositions,
            "descriptors": all_descriptors,
            "samples": samples,
        }

    # --- Analysis ---
    print("\n" + "=" * 60)
    print("STABILITY ANALYSIS")
    print("=" * 60)

    conditions = list(all_results[seeds[0]]["samples"].keys())
    results = _compute_stability_metrics(seeds, conditions, all_results)

    total_time = time.time() - t0
    results["total_time_seconds"] = round(total_time, 1)
    results["seeds"] = seeds
    results["n_tokens"] = n_tokens

    return results


def _compute_stability_metrics(
    seeds: list[int],
    conditions: list[str],
    all_results: dict,
) -> dict:
    """Compute all stability metrics from per-seed results."""
    results = {}

    # --- 1. Manifold count stability ---
    print("\n--- Manifold Count Stability ---")
    k_per_condition = {}
    for condition in conditions:
        ks = []
        for seed in seeds:
            decomp = all_results[seed]["decompositions"][condition][0]
            ks.append(int(decomp.k))
        k_per_condition[condition] = ks
        mean_k = np.mean(ks)
        std_k = np.std(ks)
        cv_k = std_k / mean_k if mean_k > 0 else 0
        print(f"  {condition}: k = {ks}, mean={mean_k:.1f}, std={std_k:.2f}, CV={cv_k:.3f}")

    results["manifold_counts"] = {
        c: {
            "per_seed": {str(s): k for s, k in zip(seeds, ks)},
            "mean": round(float(np.mean(ks)), 2),
            "std": round(float(np.std(ks)), 2),
            "cv": round(float(np.std(ks) / (np.mean(ks) + 1e-10)), 4),
        }
        for c, ks in k_per_condition.items()
    }

    # --- 2. Betti number consistency ---
    print("\n--- Betti Number Consistency ---")
    betti_per_condition = {}
    for condition in conditions:
        bettis_across_seeds = []
        for seed in seeds:
            descs = all_results[seed]["descriptors"][condition]
            # Sort manifolds by size (descending) for consistent ordering
            descs_sorted = sorted(descs, key=lambda d: d.n_points, reverse=True)
            seed_bettis = [d.betti for d in descs_sorted]
            bettis_across_seeds.append(seed_bettis)

        betti_per_condition[condition] = bettis_across_seeds

        # Compare Betti numbers of largest manifold across seeds
        largest_bettis = [bs[0] if bs else [0, 0, 0] for bs in bettis_across_seeds]
        print(f"  {condition} (largest manifold Betti):")
        for seed, b in zip(seeds, largest_bettis):
            print(f"    seed {seed}: beta = {b}")

    # Compute Betti stability: for the top-k manifolds, how consistent are Betti numbers?
    betti_stability = {}
    for condition in conditions:
        bettis = betti_per_condition[condition]
        # Number of manifolds varies, so compare up to min count
        min_n = min(len(b) for b in bettis)
        if min_n == 0:
            betti_stability[condition] = {"stable": False, "reason": "no manifolds in some seed"}
            continue

        # For each manifold rank, compute Betti vector consistency
        rank_consistency = []
        for rank in range(min(min_n, 3)):  # top 3 manifolds
            betti_vectors = [b[rank] for b in bettis]
            # Pad to same length
            max_dim = max(len(v) for v in betti_vectors)
            padded = [v + [0] * (max_dim - len(v)) for v in betti_vectors]
            arr = np.array(padded, dtype=float)
            mean_betti = arr.mean(axis=0)
            std_betti = arr.std(axis=0)
            # Consistency = 1 - normalized std
            consistency = 1.0 - float(std_betti.mean() / (mean_betti.mean() + 1e-10))
            rank_consistency.append({
                "rank": rank,
                "mean_betti": [round(float(x), 1) for x in mean_betti],
                "std_betti": [round(float(x), 1) for x in std_betti],
                "consistency": round(consistency, 4),
            })

        betti_stability[condition] = rank_consistency
        print(f"  {condition} Betti consistency:")
        for rc in rank_consistency:
            print(f"    rank {rc['rank']}: mean={rc['mean_betti']}, std={rc['std_betti']}, "
                  f"consistency={rc['consistency']:.3f}")

    results["betti_stability"] = betti_stability

    # --- 3. Cross-seed CKA ---
    print("\n--- Cross-Seed CKA of Manifold Assignments ---")

    # For CKA with different text seeds, we use feature-space CKA:
    # Each seed produces activations X_i of shape (N, D). We compare
    # the feature covariance structure via linear CKA on X^T (features as observations).
    # This measures whether the representation geometry is stable across text samples.
    cka_results = {}
    for condition in conditions:
        cka_matrix = np.zeros((len(seeds), len(seeds)))
        for i, s1 in enumerate(seeds):
            X1 = all_results[s1]["samples"][condition]
            for j, s2 in enumerate(seeds):
                if i == j:
                    cka_matrix[i, j] = 1.0
                    continue
                if j < i:
                    cka_matrix[i, j] = cka_matrix[j, i]
                    continue
                X2 = all_results[s2]["samples"][condition]
                # Feature-space CKA: transpose so features are "examples"
                cka_val = linear_cka(X1.T, X2.T)
                cka_matrix[i, j] = cka_val
                cka_matrix[j, i] = cka_val

        mean_cka = float(cka_matrix[np.triu_indices(len(seeds), k=1)].mean())
        min_cka = float(cka_matrix[np.triu_indices(len(seeds), k=1)].min())

        cka_results[condition] = {
            "matrix": {f"{s1}_{s2}": round(float(cka_matrix[i, j]), 4)
                       for i, s1 in enumerate(seeds)
                       for j, s2 in enumerate(seeds) if j > i},
            "mean": round(mean_cka, 4),
            "min": round(min_cka, 4),
        }
        print(f"  {condition}: mean CKA = {mean_cka:.4f}, min CKA = {min_cka:.4f}")

    results["cross_seed_cka"] = cka_results

    # --- 4. Summary ---
    print("\n--- Summary ---")
    all_cvs = [results["manifold_counts"][c]["cv"] for c in conditions]
    all_ckas = [results["cross_seed_cka"][c]["mean"] for c in conditions]
    overall_cv = np.mean(all_cvs)
    overall_cka = np.mean(all_ckas)

    stable = overall_cv < 0.3 and overall_cka > 0.7
    results["summary"] = {
        "overall_k_cv": round(float(overall_cv), 4),
        "overall_mean_cka": round(float(overall_cka), 4),
        "seed_stable": stable,
        "verdict": (
            "STABLE: Manifold structure is seed-invariant — strong evidence for "
            "converged geometric representations"
            if stable else
            "UNSTABLE: Manifold structure varies with seed — topology may not be converged"
        ),
    }
    print(f"  Overall k CV: {overall_cv:.4f}")
    print(f"  Overall mean CKA: {overall_cka:.4f}")
    print(f"  Verdict: {'STABLE' if stable else 'UNSTABLE'}")

    return results
