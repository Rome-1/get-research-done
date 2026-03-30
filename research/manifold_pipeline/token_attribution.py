"""Token-manifold attribution: map manifold assignments back to source tokens.

Bridges the gap between "manifolds exist" and "manifolds mean something"
by tracking which tokens land on which manifolds and computing semantic
statistics per manifold.
"""

import numpy as np
from collections import Counter
from dataclasses import dataclass, field

from .activation_extraction import TokenMetadata


@dataclass
class ManifoldTokenProfile:
    """Semantic profile of a single manifold based on its constituent tokens."""
    condition: str
    manifold_id: int
    n_tokens: int

    # Token distributions
    token_counts: Counter           # token_string -> count
    token_id_counts: Counter        # token_id -> count

    # Positional statistics
    mean_position: float            # average position in sequence
    position_std: float             # spread of positions
    position_histogram: np.ndarray  # binned position distribution

    # Top tokens (sorted by frequency)
    top_tokens: list[tuple[str, int, float]]  # (token_str, count, fraction)

    # Entropy of token distribution (higher = more diverse)
    token_entropy: float

    # Uniqueness ratio: unique_tokens / total_tokens
    uniqueness_ratio: float


@dataclass
class AttributionResult:
    """Full attribution result mapping manifolds to tokens across conditions."""
    condition_profiles: dict[str, list[ManifoldTokenProfile]]
    # (condition, manifold_id) -> ManifoldTokenProfile
    cross_condition_summary: dict[str, dict]  # condition -> summary stats


def _compute_entropy(counts: Counter) -> float:
    """Shannon entropy of a count distribution."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    probs = np.array(list(counts.values()), dtype=np.float64) / total
    probs = probs[probs > 0]
    return -np.sum(probs * np.log2(probs))


def profile_manifold_tokens(
    condition: str,
    manifold_id: int,
    metadata: TokenMetadata,
    mask: np.ndarray,
    n_position_bins: int = 16,
    top_k: int = 20,
) -> ManifoldTokenProfile:
    """Compute token statistics for a single manifold.

    Args:
        condition: condition name
        manifold_id: manifold cluster index
        metadata: TokenMetadata for this condition
        mask: boolean mask selecting tokens assigned to this manifold
        n_position_bins: number of bins for position histogram
        top_k: number of top tokens to report
    """
    token_strings = [metadata.token_strings[i] for i in np.where(mask)[0]]
    token_ids = metadata.token_ids[mask]
    positions = metadata.positions[mask]
    n_tokens = int(mask.sum())

    # Token frequency distributions
    token_counts = Counter(token_strings)
    token_id_counts = Counter(token_ids.tolist())

    # Positional statistics
    mean_pos = float(positions.mean()) if n_tokens > 0 else 0.0
    pos_std = float(positions.std()) if n_tokens > 1 else 0.0
    max_pos = int(positions.max()) + 1 if n_tokens > 0 else 1
    pos_hist, _ = np.histogram(
        positions, bins=min(n_position_bins, max_pos),
        range=(0, max_pos),
    )

    # Top tokens by frequency
    top = token_counts.most_common(top_k)
    top_tokens = [
        (tok, count, count / n_tokens if n_tokens > 0 else 0.0)
        for tok, count in top
    ]

    # Entropy and uniqueness
    entropy = _compute_entropy(token_counts)
    n_unique = len(token_counts)
    uniqueness = n_unique / n_tokens if n_tokens > 0 else 0.0

    return ManifoldTokenProfile(
        condition=condition,
        manifold_id=manifold_id,
        n_tokens=n_tokens,
        token_counts=token_counts,
        token_id_counts=token_id_counts,
        mean_position=mean_pos,
        position_std=pos_std,
        position_histogram=pos_hist,
        top_tokens=top_tokens,
        token_entropy=entropy,
        uniqueness_ratio=uniqueness,
    )


def attribute_tokens_to_manifolds(
    decompositions: dict[str, tuple],
    token_metadata: dict[str, TokenMetadata],
    top_k_tokens: int = 20,
) -> AttributionResult:
    """Map manifold assignments back to source tokens for all conditions.

    Args:
        decompositions: {condition: (DecompositionResult, X)} from Stage 1
        token_metadata: {condition: TokenMetadata} from extraction
        top_k_tokens: how many top tokens to report per manifold

    Returns:
        AttributionResult with per-manifold token profiles
    """
    condition_profiles: dict[str, list[ManifoldTokenProfile]] = {}
    cross_condition_summary: dict[str, dict] = {}

    for condition in decompositions:
        decomp, X = decompositions[condition]
        meta = token_metadata[condition]
        labels = decomp.labels
        k = decomp.k

        profiles = []
        for mid in range(k):
            mask = labels == mid
            if mask.sum() == 0:
                continue
            profile = profile_manifold_tokens(
                condition, mid, meta, mask,
                top_k=top_k_tokens,
            )
            profiles.append(profile)

        condition_profiles[condition] = profiles

        # Cross-condition summary
        cross_condition_summary[condition] = {
            "n_manifolds": k,
            "n_total_tokens": len(labels),
            "manifold_sizes": [p.n_tokens for p in profiles],
            "manifold_entropies": [round(p.token_entropy, 2) for p in profiles],
            "manifold_uniqueness": [round(p.uniqueness_ratio, 3) for p in profiles],
        }

    return AttributionResult(
        condition_profiles=condition_profiles,
        cross_condition_summary=cross_condition_summary,
    )


def format_attribution_report(result: AttributionResult) -> str:
    """Format attribution results as a human-readable report."""
    lines = []
    lines.append("=" * 60)
    lines.append("TOKEN-MANIFOLD ATTRIBUTION REPORT")
    lines.append("=" * 60)

    for condition, profiles in result.condition_profiles.items():
        lines.append(f"\n{'─' * 40}")
        lines.append(f"Condition: {condition}")
        lines.append(f"{'─' * 40}")
        summary = result.cross_condition_summary[condition]
        lines.append(f"  Manifolds: {summary['n_manifolds']}, "
                      f"Total tokens: {summary['n_total_tokens']}")

        for profile in profiles:
            lines.append(f"\n  M{profile.manifold_id} ({profile.n_tokens} tokens):")
            lines.append(f"    Entropy: {profile.token_entropy:.2f} bits, "
                          f"Uniqueness: {profile.uniqueness_ratio:.3f}")
            lines.append(f"    Mean position: {profile.mean_position:.1f} "
                          f"(std={profile.position_std:.1f})")
            lines.append(f"    Top tokens:")
            for tok, count, frac in profile.top_tokens[:10]:
                tok_display = repr(tok)
                lines.append(f"      {tok_display:>20s}  {count:5d}  ({frac:.1%})")

    return "\n".join(lines)
