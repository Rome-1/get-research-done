"""Visualization functions for the manifold pipeline."""

import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
from pathlib import Path


def plot_eigengap(
    eigenvalues: np.ndarray,
    k: int,
    condition: str,
    output_dir: Path,
):
    """Plot Laplacian eigenvalues and eigengap for k determination."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    n_show = min(20, len(eigenvalues))
    ax1.plot(range(n_show), eigenvalues[:n_show], "o-")
    ax1.axvline(x=k, color="r", linestyle="--", label=f"k={k}")
    ax1.set_xlabel("Index")
    ax1.set_ylabel("Eigenvalue")
    ax1.set_title(f"Laplacian Eigenvalues ({condition})")
    ax1.legend()

    gaps = np.diff(eigenvalues[1:n_show])
    ax2.bar(range(len(gaps)), gaps)
    ax2.set_xlabel("Index")
    ax2.set_ylabel("Gap")
    ax2.set_title("Eigengap")

    plt.tight_layout()
    plt.savefig(output_dir / f"eigengap_{condition}.png", dpi=150)
    plt.close()


def plot_clusters_2d(
    X: np.ndarray,
    labels: np.ndarray,
    condition: str,
    output_dir: Path,
):
    """Plot manifold clusters in 2D (first two PCA components)."""
    fig, ax = plt.subplots(figsize=(8, 6))

    k = len(np.unique(labels))
    cmap = plt.cm.get_cmap("tab10", k)

    for j in range(k):
        mask = labels == j
        ax.scatter(X[mask, 0], X[mask, 1], c=[cmap(j)], s=5, alpha=0.5,
                   label=f"M{j} (n={mask.sum()})")

    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title(f"SMCE Clusters ({condition})")
    ax.legend(markerscale=3)

    plt.tight_layout()
    plt.savefig(output_dir / f"clusters_{condition}.png", dpi=150)
    plt.close()


def plot_persistence_diagram(
    diagrams: list[np.ndarray],
    betti: list[int],
    condition: str,
    manifold_id: int,
    output_dir: Path,
):
    """Plot persistence diagram for a manifold."""
    fig, ax = plt.subplots(figsize=(6, 6))

    colors = ["blue", "orange", "green"]
    dim_names = ["H₀", "H₁", "H₂"]

    max_val = 0
    for dim, bd in enumerate(diagrams):
        if len(bd) == 0:
            continue
        ax.scatter(bd[:, 0], bd[:, 1], c=colors[dim % 3], s=20, alpha=0.7,
                   label=f"{dim_names[dim]} (β={betti[dim]})")
        max_val = max(max_val, bd.max())

    if max_val > 0:
        ax.plot([0, max_val * 1.1], [0, max_val * 1.1], "k--", alpha=0.3)

    ax.set_xlabel("Birth")
    ax.set_ylabel("Death")
    ax.set_title(f"Persistence Diagram ({condition}/M{manifold_id})")
    ax.legend()
    ax.set_aspect("equal")

    plt.tight_layout()
    plt.savefig(output_dir / f"persistence_{condition}_M{manifold_id}.png", dpi=150)
    plt.close()


def plot_variation_heatmap(
    scores: list,
    output_dir: Path,
):
    """Plot variation score heatmap across condition pairs."""
    # Collect unique conditions and build matrix
    conditions = sorted(set(
        [s.condition_a for s in scores] + [s.condition_b for s in scores]
    ))
    n = len(conditions)
    if n < 2:
        return

    matrix = np.zeros((n, n))
    for s in scores:
        i = conditions.index(s.condition_a)
        j = conditions.index(s.condition_b)
        # Accumulate max combined score for each condition pair
        matrix[i, j] = max(matrix[i, j], s.v_combined)
        matrix[j, i] = matrix[i, j]

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(matrix, cmap="YlOrRd")
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(conditions, rotation=45, ha="right")
    ax.set_yticklabels(conditions)

    for i in range(n):
        for j in range(n):
            ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=9)

    plt.colorbar(im, label="Max V_combined")
    ax.set_title("Cross-Condition Manifold Variation")

    plt.tight_layout()
    plt.savefig(output_dir / "variation_heatmap.png", dpi=150)
    plt.close()


def plot_diffusion_coordinates(
    coords: np.ndarray,
    condition: str,
    manifold_id: int,
    output_dir: Path,
):
    """Plot first 2-3 diffusion map coordinates."""
    n_comp = min(3, coords.shape[1])

    if n_comp >= 3:
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection="3d")
        sc = ax.scatter(coords[:, 0], coords[:, 1], coords[:, 2],
                        c=np.arange(len(coords)), cmap="viridis", s=10, alpha=0.7)
        ax.set_xlabel("ψ₁")
        ax.set_ylabel("ψ₂")
        ax.set_zlabel("ψ₃")
    else:
        fig, ax = plt.subplots(figsize=(8, 6))
        sc = ax.scatter(coords[:, 0], coords[:, 1] if n_comp > 1 else np.zeros(len(coords)),
                        c=np.arange(len(coords)), cmap="viridis", s=10, alpha=0.7)
        ax.set_xlabel("ψ₁")
        ax.set_ylabel("ψ₂" if n_comp > 1 else "")

    plt.colorbar(sc, label="Point index")
    ax.set_title(f"Diffusion Coordinates ({condition}/M{manifold_id})")

    plt.tight_layout()
    plt.savefig(output_dir / f"diffusion_{condition}_M{manifold_id}.png", dpi=150)
    plt.close()


def plot_token_distribution(
    profile,  # ManifoldTokenProfile
    output_dir: Path,
):
    """Plot token frequency and position distributions for a manifold."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Panel 1: Top tokens bar chart
    top = profile.top_tokens[:15]
    if top:
        labels = [repr(t[0]).strip("'") for t in top]
        counts = [t[1] for t in top]
        y_pos = range(len(labels))
        ax1.barh(y_pos, counts, color="steelblue")
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(labels, fontsize=8)
        ax1.invert_yaxis()
        ax1.set_xlabel("Count")
        ax1.set_title(f"Top Tokens — {profile.condition}/M{profile.manifold_id}\n"
                       f"(entropy={profile.token_entropy:.2f} bits, "
                       f"unique={profile.uniqueness_ratio:.3f})")

    # Panel 2: Position distribution
    ax2.bar(range(len(profile.position_histogram)), profile.position_histogram,
            color="coral")
    ax2.set_xlabel("Position bin")
    ax2.set_ylabel("Count")
    ax2.set_title(f"Position Distribution\n"
                   f"(mean={profile.mean_position:.1f}, "
                   f"std={profile.position_std:.1f})")

    plt.tight_layout()
    plt.savefig(
        output_dir / f"tokens_{profile.condition}_M{profile.manifold_id}.png",
        dpi=150,
    )
    plt.close()


def plot_attribution_summary(
    attribution_result,  # AttributionResult
    output_dir: Path,
):
    """Plot summary of token-manifold attribution across all conditions."""
    profiles_flat = []
    for profiles in attribution_result.condition_profiles.values():
        profiles_flat.extend(profiles)

    if not profiles_flat:
        return

    n = len(profiles_flat)
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Panel 1: Manifold sizes
    ax = axes[0]
    labels = [f"{p.condition[:4]}/M{p.manifold_id}" for p in profiles_flat]
    sizes = [p.n_tokens for p in profiles_flat]
    ax.bar(range(n), sizes, color="steelblue")
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Tokens")
    ax.set_title("Manifold Sizes (token count)")

    # Panel 2: Token entropy per manifold
    ax = axes[1]
    entropies = [p.token_entropy for p in profiles_flat]
    ax.bar(range(n), entropies, color="coral")
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Entropy (bits)")
    ax.set_title("Token Diversity (Shannon entropy)")

    # Panel 3: Mean position per manifold
    ax = axes[2]
    positions = [p.mean_position for p in profiles_flat]
    stds = [p.position_std for p in profiles_flat]
    ax.bar(range(n), positions, yerr=stds, color="seagreen", capsize=3)
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Mean position")
    ax.set_title("Positional Bias per Manifold")

    plt.suptitle("Token-Manifold Attribution Summary", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "attribution_summary.png", dpi=150)
    plt.close()
    print(f"  Attribution summary saved to {output_dir / 'attribution_summary.png'}")


def plot_summary_report(
    decompositions: dict,
    scores: list,
    characterizations: list,
    output_dir: Path,
):
    """Generate a summary figure with key results."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel 1: Manifold counts per condition
    ax = axes[0, 0]
    conditions = list(decompositions.keys())
    ks = [decompositions[c][0].k for c in conditions]
    ax.bar(range(len(conditions)), ks, color="steelblue")
    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels(conditions, rotation=30)
    ax.set_ylabel("Number of manifolds (k)")
    ax.set_title("Manifold Count per Condition")

    # Panel 2: Top variation scores
    ax = axes[0, 1]
    if scores:
        top_n = min(8, len(scores))
        labels = [f"{s.condition_a[:4]}/M{s.manifold_a_id}↔\n{s.condition_b[:4]}/M{s.manifold_b_id}"
                  for s in scores[:top_n]]
        values = [s.v_combined for s in scores[:top_n]]
        colors = ["red" if s.p_value < 0.05 else "gray" for s in scores[:top_n]]
        ax.barh(range(top_n), values, color=colors)
        ax.set_yticks(range(top_n))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("V_combined")
        ax.set_title("Top Variation Scores (red = p<0.05)")
        ax.invert_yaxis()

    # Panel 3: Eigenvalue decay comparison
    ax = axes[1, 0]
    for cond in conditions:
        decomp = decompositions[cond][0]
        n_show = min(15, len(decomp.eigenvalues))
        ax.plot(range(n_show), decomp.eigenvalues[:n_show], "o-", label=cond, markersize=3)
    ax.set_xlabel("Index")
    ax.set_ylabel("Eigenvalue")
    ax.set_title("Laplacian Eigenvalue Decay")
    ax.legend()

    # Panel 4: Diffusion eigenvalue decay for characterized manifolds
    ax = axes[1, 1]
    for char in characterizations:
        eigs = char.diffusion_map.eigenvalues
        ax.plot(range(len(eigs)), eigs, "o-",
                label=f"{char.condition[:4]}/M{char.manifold_id}", markersize=3)
    ax.set_xlabel("Index")
    ax.set_ylabel("Eigenvalue")
    ax.set_title("Diffusion Map Eigenvalue Decay")
    if characterizations:
        ax.legend()

    plt.suptitle("Multi-Manifold Detection Pipeline — Summary", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_dir / "summary_report.png", dpi=150)
    plt.close()
    print(f"  Summary report saved to {output_dir / 'summary_report.png'}")
