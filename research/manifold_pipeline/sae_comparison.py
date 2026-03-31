"""SAE feature comparison: do linear feature directions beat k-means at token routing?

Uses EleutherAI's sae-lens to load a pretrained SAE for GPT-2 Small layer 6.
Runs the same MI-attribution test that SMCE failed, applied to SAE feature labels.

Three labeling strategies:
1. top1_feature  — argmax of feature activations per token (dominant feature ID)
2. top3_bucket   — hash of top-3 active feature IDs (interaction patterns)
3. sae_kmeans    — k-means on the full sparse feature activation vector

If SAE features beat k-means where SMCE couldn't, the geometry is linear and
SAE directions are the correct abstraction for token routing.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class SAEResult:
    """MI result for one SAE labeling strategy."""
    strategy: str
    condition: str
    token_type: str
    mi_sae: float
    mi_kmeans: float
    nmi_sae: float
    nmi_kmeans: float
    p_value: float
    significant: bool   # SAE MI > permutation null AND > k-means MI
    delta_pct: float    # (mi_sae - mi_kmeans) / mi_kmeans * 100


def load_sae(layer: int = 6, device: str = "cpu"):
    """Load pretrained SAE for GPT-2 Small from sae-lens.

    Uses Joseph Bloom's GPT-2 Small residual stream SAEs.
    Returns (sae, cfg).
    """
    from sae_lens import SAE

    release = "gpt2-small-res-jb"
    sae_id = f"blocks.{layer}.hook_resid_post"

    print(f"Loading SAE: release={release}, sae_id={sae_id}")
    sae, cfg_dict, _ = SAE.from_pretrained(
        release=release,
        sae_id=sae_id,
        device=device,
    )
    sae.eval()
    n_features = sae.cfg.d_sae
    print(f"  SAE loaded: {n_features} features, "
          f"d_in={sae.cfg.d_in}, hook={sae_id}")
    return sae, cfg_dict


def encode_activations(
    sae,
    activations: np.ndarray,
    batch_size: int = 512,
    device: str = "cpu",
) -> np.ndarray:
    """Run activations through SAE encoder, return feature activation matrix.

    Args:
        sae: loaded SAE object
        activations: (N, d_model) float32 array
        batch_size: processing batch size
        device: torch device

    Returns:
        feature_acts: (N, n_features) float32 sparse matrix
    """
    import torch

    all_features = []
    X = torch.from_numpy(activations).to(device=device, dtype=torch.float32)

    with torch.no_grad():
        for i in range(0, len(X), batch_size):
            batch = X[i:i + batch_size]
            # sae.encode returns feature activations (post-ReLU, sparse)
            feat = sae.encode(batch)
            all_features.append(feat.cpu().numpy())

    return np.concatenate(all_features, axis=0)


def top1_feature_labels(feature_acts: np.ndarray) -> np.ndarray:
    """Label each token by its most active SAE feature (argmax).

    Tokens where the same feature dominates should form coherent groups.
    If SAE features are interpretable, this should track token semantics.
    """
    return feature_acts.argmax(axis=1).astype(np.int32)


def top3_bucket_labels(feature_acts: np.ndarray, n_buckets: int = 50) -> np.ndarray:
    """Label each token by hashing its top-3 active feature IDs.

    Captures interaction patterns (which features co-activate), not just
    the dominant feature. Buckets the hash space into n_buckets bins.
    """
    top3_idx = np.argsort(feature_acts, axis=1)[:, -3:]  # (N, 3)
    top3_sorted = np.sort(top3_idx, axis=1)               # order-invariant
    # Hash each (f1, f2, f3) triple into a bucket
    n_feat = feature_acts.shape[1]
    hashes = (top3_sorted[:, 0]
              + top3_sorted[:, 1] * n_feat
              + top3_sorted[:, 2] * n_feat * n_feat)
    # Bucket into n_buckets bins via modulo
    return (hashes % n_buckets).astype(np.int32)


def sae_kmeans_labels(feature_acts: np.ndarray, k: int, seed: int = 42) -> np.ndarray:
    """K-means on the full sparse SAE feature activation vector.

    This is k-means in *feature space* (not activation space). If SAE features
    are a better basis than raw PCA dimensions, this should show stronger MI.
    """
    from sklearn.cluster import KMeans
    return KMeans(n_clusters=k, random_state=seed, n_init=10).fit_predict(feature_acts)


def run_sae_attribution(
    feature_acts: np.ndarray,
    activations: np.ndarray,          # PCA-reduced, for k-means baseline
    token_ids: np.ndarray,
    positions: np.ndarray,
    tokenizer,
    condition: str,
    k: int,                           # number of clusters (from SMCE)
    n_permutations: int = 1000,
    p_threshold: float = 0.01,
    seed: int = 42,
) -> list[SAEResult]:
    """Run MI test for all SAE strategies vs k-means baseline.

    Compares three SAE labeling strategies against k-means on PCA activations,
    using the same token-type classifiers as Phase 1.
    """
    from .token_attribution import (
        classify_is_number, classify_position_bucket,
        classify_token_frequency, classify_bos_vs_content,
        classify_punctuation, mutual_information,
        normalized_mutual_information, kmeans_baseline_labels,
        permutation_mi_test,
    )

    # K-means baseline on PCA activations (same as Phase 1)
    print(f"  K-means baseline (k={k}) on PCA activations...")
    km_labels_pca = kmeans_baseline_labels(activations, k, seed)

    # SAE labeling strategies
    top1 = top1_feature_labels(feature_acts)
    top3 = top3_bucket_labels(feature_acts)
    sae_km = sae_kmeans_labels(feature_acts, k, seed)

    strategies = [
        ("top1_feature", top1),
        ("top3_bucket", top3),
        ("sae_kmeans", sae_km),
    ]

    # Token type classifiers
    token_types = [
        ("is_number", classify_is_number(token_ids, tokenizer)),
        ("position_bucket", classify_position_bucket(positions)),
        ("token_frequency", classify_token_frequency(token_ids)),
        ("bos_vs_content", classify_bos_vs_content(token_ids, positions)),
        ("punctuation", classify_punctuation(token_ids, tokenizer)),
    ]

    results = []

    for strategy_name, sae_lbls in strategies:
        # Skip degenerate strategies (all same label)
        n_unique = len(np.unique(sae_lbls))
        if n_unique < 2:
            print(f"  Skipping {strategy_name}: only {n_unique} unique label(s)")
            continue
        print(f"\n  Strategy: {strategy_name} ({n_unique} unique labels)")

        for tt_name, tt_labels in token_types:
            if len(np.unique(tt_labels)) < 2:
                continue

            # MI for SAE labels
            mi_sae, null_dist, p_val = permutation_mi_test(
                sae_lbls, tt_labels, n_permutations=n_permutations, seed=seed,
            )
            nmi_sae = normalized_mutual_information(sae_lbls, tt_labels)

            # MI for k-means baseline
            mi_km = mutual_information(km_labels_pca, tt_labels)
            nmi_km = normalized_mutual_information(km_labels_pca, tt_labels)

            beats_null = p_val < p_threshold
            beats_kmeans = mi_sae > mi_km
            significant = beats_null and beats_kmeans

            delta_pct = ((mi_sae - mi_km) / mi_km * 100) if mi_km > 0 else float("inf")

            result = SAEResult(
                strategy=strategy_name,
                condition=condition,
                token_type=tt_name,
                mi_sae=round(mi_sae, 6),
                mi_kmeans=round(mi_km, 6),
                nmi_sae=round(nmi_sae, 4),
                nmi_kmeans=round(nmi_km, 4),
                p_value=round(p_val, 4),
                significant=significant,
                delta_pct=round(delta_pct, 1),
            )
            results.append(result)

            status = "SAE WINS" if significant else "parity"
            print(f"    {tt_name}: SAE={mi_sae:.6f} km={mi_km:.6f} "
                  f"({delta_pct:+.1f}%) p={p_val:.4f} [{status}]")

    return results


def feature_type_breakdown(
    feature_acts: np.ndarray,
    token_type_labels: np.ndarray,
    token_type_name: str,
    top_n: int = 10,
) -> list[dict]:
    """Which SAE features are most selective for each token type category?

    For each category value, find features with highest mean activation.
    Returns the human-interpretable routing: "feature 42 fires for numbers."
    """
    categories = np.unique(token_type_labels)
    breakdown = []

    for cat in categories:
        mask = token_type_labels == cat
        mean_in = feature_acts[mask].mean(axis=0)   # (n_features,)
        mean_out = feature_acts[~mask].mean(axis=0)
        selectivity = mean_in - mean_out             # positive = selective for cat

        top_features = np.argsort(selectivity)[::-1][:top_n]
        breakdown.append({
            "category": int(cat),
            "n_tokens": int(mask.sum()),
            "top_features": [
                {
                    "feature_id": int(f),
                    "selectivity": round(float(selectivity[f]), 4),
                    "mean_act_in": round(float(mean_in[f]), 4),
                    "mean_act_out": round(float(mean_out[f]), 4),
                }
                for f in top_features
                if selectivity[f] > 0
            ],
        })

    return breakdown
