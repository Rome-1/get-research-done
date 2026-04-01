"""Main geometry analysis runner.

Runs all geometry characterization experiments on GPT-2 Small layer 6:
1. Intrinsic dimensionality estimation (Two-NN, local PCA, correlation dim)
2. SAE feature activation region geometry (convexity, codimension, linearity)
3. Feature intersection analysis (independence, angles, arrangement structure)
4. Sparsity pattern analysis (polytope enumeration)

Can run locally or on Modal with GPU.
"""

import json
import time
import numpy as np
from pathlib import Path


def run_geometry_analysis(
    n_tokens: int = 500,
    layer: int = 6,
    output_dir: str = "research/geometry_analysis/outputs",
    use_raw: bool = False,
) -> dict:
    """Run the full geometry analysis pipeline.

    Args:
        n_tokens: tokens per condition
        layer: transformer layer to analyze
        output_dir: where to save results
        use_raw: if True, use raw 768-dim activations (no PCA)
    """
    import torch
    from transformer_lens import HookedTransformer

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = {"meta": {
        "n_tokens": n_tokens,
        "layer": layer,
        "model": "gpt2",
        "use_raw": use_raw,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }}

    # --- Load model and SAE ---
    print("=" * 60)
    print("PHASE 2: GEOMETRY ANALYSIS")
    print("=" * 60)

    print("\n[1/6] Loading GPT-2 Small...")
    model = HookedTransformer.from_pretrained("gpt2", dtype=torch.float32)
    model.eval()

    print("[2/6] Loading SAE...")
    from sae_lens import SAE
    sae, cfg_dict, _ = SAE.from_pretrained(
        release="gpt2-small-res-jb",
        sae_id=f"blocks.{layer}.hook_resid_pre",
        device="cpu",
    )
    sae.eval()
    n_features = sae.cfg.d_sae
    print(f"  SAE: {n_features} features, d_in={sae.cfg.d_in}")

    # Extract SAE encoder weights for direction analysis
    sae_W = sae.W_enc.detach().cpu().numpy()  # (d_in, n_features) or (n_features, d_in)
    if sae_W.shape[0] == sae.cfg.d_in:
        sae_W = sae_W.T  # Ensure (n_features, d_in)
    print(f"  SAE weights shape: {sae_W.shape}")

    # --- Extract activations ---
    print("\n[3/6] Extracting activations...")
    hook_point = f"blocks.{layer}.hook_resid_pre"

    # Generate text conditions
    conditions = ["positional", "numeric", "syntactic"]
    all_activations = []
    all_condition_labels = []

    for condition in conditions:
        texts = _generate_texts(condition, n_tokens)
        tokens = model.to_tokens(texts, prepend_bos=True)
        if tokens.shape[1] > 128:
            tokens = tokens[:, :128]

        with torch.no_grad():
            _, cache = model.run_with_cache(tokens, names_filter=[hook_point])

        acts = cache[hook_point].cpu().float().numpy()
        acts = acts.reshape(-1, acts.shape[-1])

        # Subsample to n_tokens
        if acts.shape[0] > n_tokens:
            rng = np.random.RandomState(42)
            idx = rng.choice(acts.shape[0], n_tokens, replace=False)
            acts = acts[idx]

        all_activations.append(acts)
        all_condition_labels.extend([condition] * acts.shape[0])
        print(f"  {condition}: {acts.shape[0]} tokens, dim={acts.shape[1]}")

    # Combine all conditions
    X_raw = np.concatenate(all_activations, axis=0)
    print(f"  Total: {X_raw.shape[0]} tokens, {X_raw.shape[1]} dims")

    # Optionally apply PCA
    if use_raw:
        X = X_raw
        print("  Using raw 768-dim activations")
    else:
        from sklearn.decomposition import PCA
        pca = PCA(n_components=100, random_state=42)
        X = pca.fit_transform(X_raw)
        results["meta"]["pca_explained_variance"] = float(pca.explained_variance_ratio_.sum())
        print(f"  PCA: {X_raw.shape[1]} -> {X.shape[1]} (var={pca.explained_variance_ratio_.sum():.3f})")

    # --- SAE feature activations ---
    print("\n[4/6] Computing SAE feature activations...")
    with torch.no_grad():
        X_torch = torch.from_numpy(X_raw).float()
        feature_acts_list = []
        for i in range(0, len(X_torch), 512):
            batch = X_torch[i:i + 512]
            feat = sae.encode(batch)
            feature_acts_list.append(feat.cpu().numpy())
    feature_acts = np.concatenate(feature_acts_list, axis=0)

    sparsity = (feature_acts > 0).mean()
    active_per_token = (feature_acts > 0).sum(axis=1)
    print(f"  Feature activations: {feature_acts.shape}")
    print(f"  Sparsity: {sparsity:.4f} ({(feature_acts > 0).sum(axis=1).mean():.1f} active/token)")

    # Free model memory
    del model, cache
    import gc; gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # ============================================================
    # EXPERIMENT 1: Intrinsic Dimensionality
    # ============================================================
    print("\n[5/6] Running geometry experiments...")
    print("\n--- Experiment 1: Intrinsic Dimensionality ---")

    from .intrinsic_dimension import (
        two_nn_dimension,
        local_pca_dimension,
        correlation_dimension,
        dimension_by_feature_region,
    )

    # 1a. Two-NN global estimate
    print("  Two-NN estimator...")
    twonn = two_nn_dimension(X)
    print(f"    Global ID (Two-NN): {twonn.global_dim:.1f} +/- {twonn.std:.1f}")

    # 1b. Local PCA (spatially varying dimension)
    print("  Local PCA estimator...")
    lpca = local_pca_dimension(X, k_neighbors=50)
    print(f"    Median local dim: {lpca.global_dim:.1f} +/- {lpca.std:.1f}")

    # 1c. Correlation dimension
    print("  Correlation dimension...")
    corr = correlation_dimension(X, n_points=min(1000, len(X)))
    print(f"    Correlation dim: {corr.global_dim:.1f}")

    # 1d. Dimension conditioned on SAE feature
    print("  Dimension by feature region...")
    feat_dim = dimension_by_feature_region(X, feature_acts, top_k_features=20)

    results["intrinsic_dimension"] = {
        "two_nn": {"dim": twonn.global_dim, "std": twonn.std, **twonn.metadata},
        "local_pca": {
            "median_dim": lpca.global_dim,
            "std": lpca.std,
            "dim_percentiles": {
                "p10": float(np.percentile(lpca.local_dims, 10)),
                "p25": float(np.percentile(lpca.local_dims, 25)),
                "p50": float(np.percentile(lpca.local_dims, 50)),
                "p75": float(np.percentile(lpca.local_dims, 75)),
                "p90": float(np.percentile(lpca.local_dims, 90)),
            },
            **lpca.metadata,
        },
        "correlation": {"dim": corr.global_dim, **corr.metadata},
        "by_feature_region": feat_dim,
    }

    # ============================================================
    # EXPERIMENT 2: Feature Region Geometry
    # ============================================================
    print("\n--- Experiment 2: Feature Activation Region Geometry ---")

    from .feature_geometry import (
        analyze_feature_regions,
        analyze_intersections,
        sparsity_pattern_analysis,
    )

    print("  Analyzing feature regions (convexity, codimension, linearity)...")
    # Use PCA-reduced activations for geometry analysis but raw for SAE
    regions = analyze_feature_regions(
        X, feature_acts, sae_W=sae_W, top_k=30, min_active=20,
    )
    print(f"    Analyzed {len(regions)} features")

    # Summary statistics
    convexities = [r.convexity_score for r in regions if not np.isnan(r.convexity_score)]
    codimensions = [r.codimension for r in regions if not np.isnan(r.codimension)]
    linearities = [r.boundary_linearity for r in regions if not np.isnan(r.boundary_linearity)]

    if convexities:
        print(f"    Convexity: mean={np.mean(convexities):.3f}, "
              f"min={np.min(convexities):.3f}, max={np.max(convexities):.3f}")
    if codimensions:
        print(f"    Codimension: mean={np.mean(codimensions):.1f}, "
              f"median={np.median(codimensions):.1f}")
    if linearities:
        print(f"    Boundary linearity: mean={np.mean(linearities):.3f}")

    results["feature_regions"] = {
        "n_analyzed": len(regions),
        "regions": [
            {
                "feature_id": r.feature_id,
                "n_active": r.n_active,
                "activation_rate": r.activation_rate,
                "convexity_score": r.convexity_score,
                "codimension": r.codimension,
                "angular_spread": r.angular_spread,
                "boundary_linearity": r.boundary_linearity,
            }
            for r in regions
        ],
        "summary": {
            "mean_convexity": float(np.mean(convexities)) if convexities else None,
            "mean_codimension": float(np.mean(codimensions)) if codimensions else None,
            "mean_boundary_linearity": float(np.mean(linearities)) if linearities else None,
        },
    }

    # ============================================================
    # EXPERIMENT 3: Feature Intersection Geometry
    # ============================================================
    print("\n--- Experiment 3: Feature Intersection Analysis ---")

    print("  Analyzing pairwise intersections...")
    intersections = analyze_intersections(
        X, feature_acts, sae_W=sae_W, top_k=15, min_active=20,
    )
    print(f"    Analyzed {len(intersections)} pairs")

    indep_ratios = [ig.independence_ratio for ig in intersections
                    if not np.isnan(ig.independence_ratio) and ig.independence_ratio < 100]
    angles = [ig.direction_angle for ig in intersections
              if not np.isnan(ig.direction_angle)]

    if indep_ratios:
        print(f"    Independence ratio: mean={np.mean(indep_ratios):.2f}, "
              f"median={np.median(indep_ratios):.2f}")
        print(f"      (1.0 = independent, >1 = positive correlation)")
    if angles:
        print(f"    Feature direction angles: mean={np.mean(angles):.2f} rad "
              f"({np.degrees(np.mean(angles)):.1f} deg)")

    results["intersections"] = {
        "n_pairs": len(intersections),
        "pairs": [
            {
                "feature_a": ig.feature_a,
                "feature_b": ig.feature_b,
                "n_both_active": ig.n_both_active,
                "jaccard": ig.jaccard,
                "independence_ratio": ig.independence_ratio,
                "direction_angle_rad": ig.direction_angle,
                "intersection_convexity": ig.intersection_convexity,
            }
            for ig in intersections[:50]  # cap output size
        ],
        "summary": {
            "mean_independence_ratio": float(np.mean(indep_ratios)) if indep_ratios else None,
            "median_independence_ratio": float(np.median(indep_ratios)) if indep_ratios else None,
            "mean_direction_angle_deg": float(np.degrees(np.mean(angles))) if angles else None,
        },
    }

    # ============================================================
    # EXPERIMENT 4: Sparsity Pattern Analysis
    # ============================================================
    print("\n--- Experiment 4: Sparsity Pattern Structure ---")

    print("  Analyzing binary activation patterns...")
    patterns = sparsity_pattern_analysis(feature_acts, top_k=30, min_active=10)
    print(f"    Unique patterns: {patterns['n_unique_patterns']} / "
          f"{patterns['n_tokens']} tokens")
    print(f"    Features/token: {patterns['features_per_token_mean']:.1f} "
          f"+/- {patterns['features_per_token_std']:.1f}")
    print(f"    Co-activation density: {patterns['coactivation_density']:.3f}")

    # Remove the large coactivation matrix from saved results
    patterns_save = {k: v for k, v in patterns.items() if k != "coactivation_matrix"}
    results["sparsity_patterns"] = patterns_save

    # ============================================================
    # Save results
    # ============================================================
    print("\n[6/6] Saving results...")
    results_path = output_path / "geometry_results.json"

    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, (np.floating, np.float32, np.float64)):
                return float(obj)
            if isinstance(obj, (np.integer, np.int32, np.int64)):
                return int(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, np.bool_):
                return bool(obj)
            return super().default(obj)

    with open(results_path, "w") as f:
        json.dump(results, f, indent=2, cls=NumpyEncoder)
    print(f"  Results saved to {results_path}")

    # Print synthesis
    _print_synthesis(results)

    return results


def _generate_texts(condition: str, n_tokens: int) -> list[str]:
    """Generate text for a condition (simplified from activation_extraction.py)."""
    import random
    seq_len = 128
    n_texts = max(n_tokens // (seq_len // 2), 20)

    if condition == "positional":
        return [("the " * (seq_len // 2)).strip() for _ in range(n_texts)]
    elif condition == "numeric":
        rng = random.Random(42)
        texts = []
        for _ in range(n_texts):
            parts = []
            while len(" ".join(parts)) < seq_len * 3:
                a, b = rng.randint(1, 9999), rng.randint(1, 9999)
                parts.append(f"{a} plus {b} equals {a + b}.")
            texts.append(" ".join(parts))
        return texts
    elif condition == "syntactic":
        rng = random.Random(43)
        subjects = ["The cat", "A researcher", "My friend", "The system"]
        verbs = ["discovered", "analyzed", "created", "observed"]
        objects = ["a new approach", "the hidden pattern", "an elegant solution"]
        texts = []
        for _ in range(n_texts):
            parts = []
            while len(" ".join(parts)) < seq_len * 3:
                s, v, o = rng.choice(subjects), rng.choice(verbs), rng.choice(objects)
                parts.append(f"{s} {v} {o}.")
            texts.append(" ".join(parts))
        return texts
    else:
        raise ValueError(f"Unknown condition: {condition}")


def _print_synthesis(results: dict):
    """Print a synthesis of the geometry analysis results."""
    print("\n" + "=" * 60)
    print("SYNTHESIS: GEOMETRY OF THE RESIDUAL STREAM")
    print("=" * 60)

    id_results = results.get("intrinsic_dimension", {})
    fr_results = results.get("feature_regions", {})
    int_results = results.get("intersections", {})
    sp_results = results.get("sparsity_patterns", {})

    # Intrinsic dimension
    twonn_dim = id_results.get("two_nn", {}).get("dim", "?")
    lpca_dim = id_results.get("local_pca", {}).get("median_dim", "?")
    corr_dim = id_results.get("correlation", {}).get("dim", "?")
    print(f"\n1. INTRINSIC DIMENSION:")
    print(f"   Two-NN: {twonn_dim}")
    print(f"   Local PCA (median): {lpca_dim}")
    print(f"   Correlation: {corr_dim}")

    percs = id_results.get("local_pca", {}).get("dim_percentiles", {})
    if percs:
        p10, p90 = percs.get("p10", "?"), percs.get("p90", "?")
        print(f"   Local dim range (p10-p90): {p10} - {p90}")
        if isinstance(p10, (int, float)) and isinstance(p90, (int, float)):
            ratio = p90 / p10 if p10 > 0 else float("inf")
            if ratio > 2:
                print(f"   -> VARYING dimension (ratio {ratio:.1f}x) "
                      "suggests non-trivial geometric structure")
            else:
                print(f"   -> UNIFORM dimension (ratio {ratio:.1f}x) "
                      "suggests simple manifold")

    # Feature region geometry
    summary = fr_results.get("summary", {})
    convex = summary.get("mean_convexity")
    codim = summary.get("mean_codimension")
    linearity = summary.get("mean_boundary_linearity")
    print(f"\n2. FEATURE REGION GEOMETRY:")
    if convex is not None:
        print(f"   Mean convexity: {convex:.3f} {'(CONVEX - half-spaces!)' if convex > 0.9 else ''}")
    if codim is not None:
        print(f"   Mean codimension: {codim:.1f} {'(~1 = hyperplane boundary!)' if abs(codim - 1) < 5 else ''}")
    if linearity is not None:
        print(f"   Boundary linearity: {linearity:.3f} {'(LINEAR boundaries!)' if linearity > 0.9 else ''}")

    # Intersections
    int_summary = int_results.get("summary", {})
    indep = int_summary.get("mean_independence_ratio")
    angle = int_summary.get("mean_direction_angle_deg")
    print(f"\n3. INTERSECTION STRUCTURE:")
    if indep is not None:
        print(f"   Independence ratio: {indep:.2f} "
              f"{'(~independent = general position)' if 0.5 < indep < 2 else '(correlated!)'}")
    if angle is not None:
        print(f"   Mean direction angle: {angle:.1f} deg "
              f"{'(near-orthogonal!)' if angle > 70 else ''}")

    # Sparsity patterns
    n_patterns = sp_results.get("n_unique_patterns", "?")
    n_tokens = sp_results.get("n_tokens", "?")
    fpt_mean = sp_results.get("features_per_token_mean", "?")
    print(f"\n4. SPARSITY PATTERN STRUCTURE:")
    print(f"   Unique patterns: {n_patterns} / {n_tokens} tokens")
    print(f"   Features/token: {fpt_mean}")

    print("\n" + "=" * 60)
    verdict_parts = []
    if convex is not None and convex > 0.85:
        verdict_parts.append("feature regions are convex (half-spaces)")
    if linearity is not None and linearity > 0.85:
        verdict_parts.append("boundaries are linear (hyperplanes)")
    if indep is not None and 0.5 < indep < 2:
        verdict_parts.append("features intersect near-independently")

    if len(verdict_parts) >= 2:
        print("VERDICT: The geometry IS a hyperplane arrangement.")
        for v in verdict_parts:
            print(f"  - {v}")
        print("The residual stream is partitioned into convex polytopes")
        print("by SAE feature boundaries. This is NOT a curved manifold")
        print("structure — it is piecewise-linear, as predicted by ReLU theory.")
    else:
        print("VERDICT: Mixed evidence. Further analysis needed.")
        if verdict_parts:
            print("Supporting:")
            for v in verdict_parts:
                print(f"  + {v}")

    print("=" * 60)


if __name__ == "__main__":
    run_geometry_analysis(n_tokens=500, layer=6)
