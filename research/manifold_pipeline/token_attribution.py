"""Phase 1: Token-manifold attribution with go/kill gate.

Computes mutual information between manifold assignment and token type
(is-number, POS category, position bucket). If MI does not exceed
permutation baseline at p<0.01, manifolds are not semantically selective
and the entire manifold surgery program is falsified.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class TokenType:
    """Token type classification for MI computation."""
    name: str
    labels: np.ndarray  # (N,) integer category per token


@dataclass
class AttributionResult:
    """Result of MI test for one token type."""
    token_type: str
    mi_observed: float          # observed mutual information (nats)
    mi_null_mean: float         # mean MI under permutation null
    mi_null_std: float          # std MI under permutation null
    p_value: float              # fraction of null >= observed
    n_permutations: int
    significant: bool           # p < threshold
    contingency: np.ndarray     # (n_manifolds, n_categories) count matrix


@dataclass
class Phase1Result:
    """Aggregate Phase 1 result: proceed or kill."""
    proceed: bool               # True if at least one type passes gate
    results_by_condition: dict  # condition -> list[AttributionResult]
    kill_reason: str | None = None


# --- Token type classifiers ---

def classify_is_number(token_ids: np.ndarray, tokenizer) -> np.ndarray:
    """Binary: 1 if token decodes to a number, 0 otherwise."""
    labels = np.zeros(len(token_ids), dtype=np.int32)
    for i, tid in enumerate(token_ids):
        text = tokenizer.decode([int(tid)]).strip()
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            labels[i] = 1
        elif text.replace(",", "").replace(".", "").isdigit():
            labels[i] = 1
    return labels


def classify_position_bucket(positions: np.ndarray, n_buckets: int = 8) -> np.ndarray:
    """Bucket positions into n_buckets equal-width bins."""
    max_pos = positions.max() + 1
    bucket_size = max(1, max_pos // n_buckets)
    return np.minimum(positions // bucket_size, n_buckets - 1).astype(np.int32)


def classify_token_frequency(token_ids: np.ndarray, n_buckets: int = 5) -> np.ndarray:
    """Classify tokens by their frequency rank within the sample.

    High-frequency tokens (common words) vs rare tokens often map to
    different computational pathways.
    """
    unique, counts = np.unique(token_ids, return_counts=True)
    freq_map = dict(zip(unique, counts))
    freqs = np.array([freq_map[tid] for tid in token_ids])
    # Quantile-based bucketing
    percentiles = np.percentile(freqs, np.linspace(0, 100, n_buckets + 1)[1:-1])
    return np.digitize(freqs, percentiles).astype(np.int32)


def classify_bos_vs_content(token_ids: np.ndarray, positions: np.ndarray) -> np.ndarray:
    """Binary: 0 = BOS/early position (0-1), 1 = content tokens."""
    return (positions >= 2).astype(np.int32)


def classify_punctuation(token_ids: np.ndarray, tokenizer) -> np.ndarray:
    """Ternary: 0 = punctuation, 1 = whitespace-only, 2 = content."""
    import string
    labels = np.zeros(len(token_ids), dtype=np.int32)
    for i, tid in enumerate(token_ids):
        text = tokenizer.decode([int(tid)])
        stripped = text.strip()
        if not stripped:
            labels[i] = 1  # whitespace
        elif all(c in string.punctuation for c in stripped):
            labels[i] = 0  # punctuation
        else:
            labels[i] = 2  # content
    return labels


# --- Mutual information ---

def mutual_information(labels_x: np.ndarray, labels_y: np.ndarray) -> float:
    """Compute MI(X; Y) in nats from discrete label arrays.

    Uses the plug-in estimator: MI = H(X) + H(Y) - H(X, Y)
    where H is Shannon entropy.
    """
    N = len(labels_x)
    assert len(labels_y) == N

    # Joint distribution
    # Encode joint labels as single integers
    ux = np.unique(labels_x)
    uy = np.unique(labels_y)
    x_map = {v: i for i, v in enumerate(ux)}
    y_map = {v: i for i, v in enumerate(uy)}

    nx, ny = len(ux), len(uy)
    contingency = np.zeros((nx, ny), dtype=np.float64)
    for xi, yi in zip(labels_x, labels_y):
        contingency[x_map[xi], y_map[yi]] += 1

    # Normalize
    p_xy = contingency / N
    p_x = p_xy.sum(axis=1)
    p_y = p_xy.sum(axis=0)

    # MI = sum p(x,y) * log(p(x,y) / (p(x)*p(y)))
    mi = 0.0
    for i in range(nx):
        for j in range(ny):
            if p_xy[i, j] > 0:
                mi += p_xy[i, j] * np.log(p_xy[i, j] / (p_x[i] * p_y[j]))

    return mi


def permutation_mi_test(
    manifold_labels: np.ndarray,
    token_type_labels: np.ndarray,
    n_permutations: int = 1000,
    seed: int = 42,
) -> tuple[float, np.ndarray, float]:
    """Permutation test for MI significance.

    Returns:
        mi_observed: observed MI
        null_distribution: (n_permutations,) MI under random permutation
        p_value: fraction of null >= observed
    """
    mi_observed = mutual_information(manifold_labels, token_type_labels)

    rng = np.random.RandomState(seed)
    null_dist = np.zeros(n_permutations)

    for i in range(n_permutations):
        perm = rng.permutation(len(manifold_labels))
        null_dist[i] = mutual_information(manifold_labels[perm], token_type_labels)

    p_value = (null_dist >= mi_observed).mean()
    return mi_observed, null_dist, p_value


# --- Main attribution function ---

def compute_token_attribution(
    manifold_labels: np.ndarray,
    token_ids: np.ndarray,
    positions: np.ndarray,
    tokenizer,
    n_permutations: int = 1000,
    p_threshold: float = 0.01,
    seed: int = 42,
) -> list[AttributionResult]:
    """Compute MI between manifold assignment and multiple token types.

    Args:
        manifold_labels: (N,) manifold cluster assignment per token
        token_ids: (N,) vocab token ID per activation
        positions: (N,) sequence position per activation
        tokenizer: HuggingFace-style tokenizer for decoding
        n_permutations: permutation count for significance test
        p_threshold: significance threshold (default 0.01)
        seed: random seed

    Returns:
        List of AttributionResult, one per token type tested.
    """
    # Build token type classifiers
    token_types = [
        TokenType("is_number", classify_is_number(token_ids, tokenizer)),
        TokenType("position_bucket", classify_position_bucket(positions)),
        TokenType("token_frequency", classify_token_frequency(token_ids)),
        TokenType("bos_vs_content", classify_bos_vs_content(token_ids, positions)),
        TokenType("punctuation", classify_punctuation(token_ids, tokenizer)),
    ]

    results = []
    for tt in token_types:
        # Skip degenerate cases (all same label)
        if len(np.unique(tt.labels)) < 2:
            print(f"  Skipping {tt.name}: all tokens have same label")
            continue

        print(f"  Testing MI(manifold, {tt.name})...")
        mi_obs, null_dist, p_val = permutation_mi_test(
            manifold_labels, tt.labels,
            n_permutations=n_permutations, seed=seed,
        )

        # Build contingency table for reporting
        n_man = len(np.unique(manifold_labels))
        n_cat = len(np.unique(tt.labels))
        man_map = {v: i for i, v in enumerate(np.unique(manifold_labels))}
        cat_map = {v: i for i, v in enumerate(np.unique(tt.labels))}
        contingency = np.zeros((n_man, n_cat), dtype=np.int32)
        for ml, cl in zip(manifold_labels, tt.labels):
            contingency[man_map[ml], cat_map[cl]] += 1

        result = AttributionResult(
            token_type=tt.name,
            mi_observed=mi_obs,
            mi_null_mean=null_dist.mean(),
            mi_null_std=null_dist.std(),
            p_value=p_val,
            n_permutations=n_permutations,
            significant=p_val < p_threshold,
            contingency=contingency,
        )
        results.append(result)

        status = "SIGNIFICANT" if result.significant else "not significant"
        print(f"    MI={mi_obs:.6f}, null={null_dist.mean():.6f}±{null_dist.std():.6f}, "
              f"p={p_val:.4f} [{status}]")

    return results


def run_phase1_gate(
    condition_results: dict[str, list[AttributionResult]],
    p_threshold: float = 0.01,
) -> Phase1Result:
    """Evaluate go/kill gate across all conditions.

    PROCEED if: at least one condition has at least one significant MI
    (manifolds are token-selective somewhere).

    KILL if: no condition shows any significant MI — manifolds are not
    semantically selective, falsifying the central claim.
    """
    any_significant = False
    for cond, results in condition_results.items():
        for r in results:
            if r.significant:
                any_significant = True
                break
        if any_significant:
            break

    if any_significant:
        return Phase1Result(
            proceed=True,
            results_by_condition=condition_results,
        )
    else:
        return Phase1Result(
            proceed=False,
            results_by_condition=condition_results,
            kill_reason=(
                f"No token type showed significant MI with manifold assignment "
                f"at p<{p_threshold} across any condition. Manifolds are not "
                f"semantically selective — central claim falsified."
            ),
        )
