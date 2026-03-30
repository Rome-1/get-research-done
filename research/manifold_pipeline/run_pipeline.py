#!/usr/bin/env python3
"""Main orchestrator for the multi-manifold detection pipeline.

Usage:
    python -m research.manifold_pipeline.run_pipeline [--synthetic] [--gpu]

Validates the Phase 5 pipeline from the manifold detection research survey
on GPT-2 Small activations (or synthetic data for quick validation).
"""

import argparse
import json
import time
import numpy as np
from pathlib import Path

from .config import PipelineConfig
from .stage1_decompose import decompose
from .stage2_match import compute_all_descriptors, match_all_conditions
from .stage3_score import score_all_matches
from .stage4_characterize import characterize_top_manifolds
from .token_attribution import (
    compute_token_attribution,
    run_phase1_gate,
)
from .visualization import (
    plot_eigengap,
    plot_clusters_2d,
    plot_persistence_diagram,
    plot_variation_heatmap,
    plot_diffusion_coordinates,
    plot_summary_report,
)


def run_synthetic(config: PipelineConfig) -> dict:
    """Run pipeline on synthetic manifolds for validation."""
    from sklearn.datasets import make_moons, make_blobs

    print("=" * 60)
    print("SYNTHETIC VALIDATION")
    print("=" * 60)

    np.random.seed(config.random_seed)

    # Generate synthetic data: two moons embedded in R^100
    n_per = 500
    D = config.pca_dim

    # Condition 1: two moons
    X_moons, y_moons = make_moons(n_samples=n_per * 2, noise=0.05, random_state=42)
    # Embed in R^D
    embedding = np.random.RandomState(42).randn(2, D) * 0.1
    X_moons_hd = X_moons @ embedding + np.random.RandomState(42).randn(n_per * 2, D) * 0.01

    # Condition 2: three blobs
    X_blobs, y_blobs = make_blobs(n_samples=n_per * 3, centers=3, n_features=2,
                                   random_state=43)
    embedding2 = np.random.RandomState(43).randn(2, D) * 0.1
    X_blobs_hd = X_blobs @ embedding2 + np.random.RandomState(43).randn(n_per * 3, D) * 0.01

    # Condition 3: circle (should show β₁ = 1)
    theta = np.linspace(0, 2 * np.pi, n_per * 2, endpoint=False)
    X_circle = np.column_stack([np.cos(theta), np.sin(theta)])
    embedding3 = np.random.RandomState(44).randn(2, D) * 0.1
    X_circle_hd = X_circle @ embedding3 + np.random.RandomState(44).randn(n_per * 2, D) * 0.01

    samples = {
        "two_moons": X_moons_hd,
        "three_blobs": X_blobs_hd,
        "circle": X_circle_hd,
    }

    return _run_pipeline(samples, config)


def run_gpt2(config: PipelineConfig) -> dict:
    """Run pipeline on GPT-2 Small activations with token attribution."""
    from .activation_extraction import extract_and_reduce_with_tokens

    print("=" * 60)
    print("GPT-2 SMALL VALIDATION")
    print("=" * 60)

    extraction_results = extract_and_reduce_with_tokens(config)
    samples = {cond: er.activations for cond, er in extraction_results.items()}
    return _run_pipeline(samples, config, extraction_results=extraction_results)


def run_gemma2(config: PipelineConfig = None) -> dict:
    """Run pipeline on Gemma 2 2B activations with token attribution.

    Uses Gemma Scope-compatible layer (default: 13 of 26).
    """
    from .activation_extraction import extract_and_reduce_with_tokens

    if config is None:
        config = PipelineConfig.gemma2_2b()

    print("=" * 60)
    print(f"GEMMA 2 2B — Layer {config.layer}")
    print("=" * 60)

    extraction_results = extract_and_reduce_with_tokens(config)
    samples = {cond: er.activations for cond, er in extraction_results.items()}
    return _run_pipeline(samples, config, extraction_results=extraction_results)


def _run_pipeline(
    samples: dict[str, np.ndarray],
    config: PipelineConfig,
    extraction_results=None,
) -> dict:
    """Core pipeline execution on pre-extracted samples.

    Args:
        samples: condition -> (N, D) activation arrays
        config: pipeline configuration
        extraction_results: optional dict of ExtractionResult with token metadata
    """
    results = {}
    t0 = time.time()

    # --- Stage 1: Decompose ---
    print("\n" + "=" * 60)
    print("STAGE 1: DECOMPOSE (SMCE)")
    print("=" * 60)

    decompositions = {}
    for condition, X in samples.items():
        print(f"\nDecomposing {condition} ({X.shape[0]} points, dim={X.shape[1]})")
        decomp = decompose(
            X,
            alpha=config.smce_alpha,
            max_k=config.max_k_manifolds,
            max_iter=config.smce_max_iter,
        )
        decompositions[condition] = (decomp, X)

        # Visualize
        plot_eigengap(decomp.eigenvalues, decomp.k, condition, config.output_dir)
        plot_clusters_2d(X, decomp.labels, condition, config.output_dir)

    t1 = time.time()
    print(f"\nStage 1 complete in {t1 - t0:.1f}s")

    # --- Stage 2: Match ---
    print("\n" + "=" * 60)
    print("STAGE 2: MATCH MANIFOLDS")
    print("=" * 60)

    all_descriptors = compute_all_descriptors(
        decompositions, max_ph_points=config.max_ph_points
    )
    all_matches = match_all_conditions(all_descriptors)

    # Visualize persistence diagrams
    for condition, descs in all_descriptors.items():
        for desc in descs:
            plot_persistence_diagram(
                desc.persistence.diagrams,
                desc.betti,
                condition,
                desc.manifold_id,
                config.output_dir,
            )

    t2 = time.time()
    print(f"\nStage 2 complete in {t2 - t1:.1f}s")

    # --- Stage 3: Score ---
    print("\n" + "=" * 60)
    print("STAGE 3: VARIATION SCORING")
    print("=" * 60)

    scores = score_all_matches(
        all_descriptors,
        all_matches,
        decompositions,
        n_permutations=config.n_permutations,
    )

    plot_variation_heatmap(scores, config.output_dir)

    t3 = time.time()
    print(f"\nStage 3 complete in {t3 - t2:.1f}s")

    # --- Stage 4: Characterize ---
    print("\n" + "=" * 60)
    print("STAGE 4: CHARACTERIZE TOP MANIFOLDS")
    print("=" * 60)

    characterizations = characterize_top_manifolds(
        scores,
        all_descriptors,
        decompositions,
        top_k=config.top_k_variation,
        n_components=config.diffusion_n_components,
    )

    for char in characterizations:
        plot_diffusion_coordinates(
            char.diffusion_map.coordinates,
            char.condition,
            char.manifold_id,
            config.output_dir,
        )

    t4 = time.time()
    print(f"\nStage 4 complete in {t4 - t3:.1f}s")

    # --- Stage 5: Token-Manifold Attribution (Phase 1 go/kill gate) ---
    phase1_result = None
    if extraction_results is not None:
        print("\n" + "=" * 60)
        print("STAGE 5: TOKEN-MANIFOLD ATTRIBUTION (PHASE 1 GATE)")
        print("=" * 60)

        from .activation_extraction import load_model
        model = load_model(config.model_name)
        tokenizer = model.tokenizer

        condition_attr_results = {}
        for condition in samples:
            er = extraction_results[condition]
            decomp, _ = decompositions[condition]
            print(f"\nCondition: {condition} (k={decomp.k} manifolds)")
            attr_results = compute_token_attribution(
                manifold_labels=decomp.labels,
                token_ids=er.token_ids,
                positions=er.positions,
                tokenizer=tokenizer,
                n_permutations=config.n_permutations,
                seed=config.random_seed,
            )
            condition_attr_results[condition] = attr_results

        phase1_result = run_phase1_gate(condition_attr_results)

        t5 = time.time()
        print(f"\nStage 5 complete in {t5 - t4:.1f}s")

        if phase1_result.proceed:
            print("\n" + "=" * 60)
            print("PHASE 1 GATE: *** PROCEED ***")
            print("Manifolds show significant token selectivity.")
            print("=" * 60)
            # Report which types were significant
            for cond, results_list in phase1_result.results_by_condition.items():
                sig = [r for r in results_list if r.significant]
                if sig:
                    types_str = ", ".join(f"{r.token_type}(p={r.p_value:.4f})" for r in sig)
                    print(f"  {cond}: {types_str}")
        else:
            print("\n" + "=" * 60)
            print("PHASE 1 GATE: *** KILL ***")
            print(phase1_result.kill_reason)
            print("=" * 60)

        t4 = t5  # update for total time calculation

    # --- Summary ---
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    plot_summary_report(decompositions, scores, characterizations, config.output_dir)

    total_time = t4 - t0
    print(f"\nTotal pipeline time: {total_time:.1f}s ({total_time / 60:.1f} min)")

    # Build results dict
    results = {
        "conditions": list(samples.keys()),
        "manifold_counts": {c: int(decomp.k) for c, (decomp, _) in decompositions.items()},
        "total_scores": len(scores),
        "significant_scores": sum(1 for s in scores if s.p_value < 0.05),
        "top_scores": [
            {
                "pair": f"{s.condition_a}/M{s.manifold_a_id} ↔ {s.condition_b}/M{s.manifold_b_id}",
                "v_combined": round(s.v_combined, 4),
                "v_topo": round(s.v_topo, 4),
                "v_geom": round(s.v_geom, 4),
                "v_dim": round(s.v_dim, 4),
                "p_value": round(s.p_value, 4),
            }
            for s in scores[:5]
        ],
        "characterizations": [
            {
                "condition": c.condition,
                "manifold_id": int(c.manifold_id),
                "n_points": int(c.n_points),
                "intrinsic_dim": round(c.intrinsic_dim, 2),
                "betti": [int(b) for b in c.betti],
                "diffusion_eigenvalues": [round(float(e), 4) for e in c.diffusion_map.eigenvalues],
            }
            for c in characterizations
        ],
        "total_time_seconds": round(total_time, 1),
    }

    # Add Phase 1 gate results if available
    if phase1_result is not None:
        results["phase1_gate"] = {
            "proceed": phase1_result.proceed,
            "kill_reason": phase1_result.kill_reason,
            "attribution": {
                cond: [
                    {
                        "token_type": r.token_type,
                        "mi_observed": round(float(r.mi_observed), 6),
                        "mi_null_mean": round(float(r.mi_null_mean), 6),
                        "mi_null_std": round(float(r.mi_null_std), 6),
                        "p_value": round(float(r.p_value), 4),
                        "significant": bool(r.significant),
                    }
                    for r in results_list
                ]
                for cond, results_list in phase1_result.results_by_condition.items()
            },
        }

    # Save results
    results_path = config.output_dir / "results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {results_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Multi-manifold detection pipeline")
    parser.add_argument("--synthetic", action="store_true",
                        help="Run on synthetic data only (quick validation)")
    parser.add_argument("--model", type=str, default="gpt2",
                        choices=["gpt2", "gemma2-2b"],
                        help="Model to run (default: gpt2)")
    parser.add_argument("--n-tokens", type=int, default=2000,
                        help="Tokens per condition (default: 2000)")
    parser.add_argument("--pca-dim", type=int, default=100,
                        help="PCA reduction dimension (default: 100)")
    parser.add_argument("--smce-alpha", type=float, default=0.05,
                        help="SMCE L1 penalty (default: 0.05)")
    parser.add_argument("--layer", type=int, default=None,
                        help="Transformer layer (default: model-specific)")
    parser.add_argument("--permutations", type=int, default=1000,
                        help="Number of permutations for significance test")

    args = parser.parse_args()

    overrides = dict(
        n_tokens_per_condition=args.n_tokens,
        pca_dim=args.pca_dim,
        smce_alpha=args.smce_alpha,
        n_permutations=args.permutations,
    )
    if args.layer is not None:
        overrides["layer"] = args.layer
        overrides["hook_point"] = f"blocks.{args.layer}.hook_resid_post"

    if args.model == "gemma2-2b":
        config = PipelineConfig.gemma2_2b(**overrides)
    else:
        config = PipelineConfig.gpt2(**overrides)

    if args.synthetic:
        results = run_synthetic(config)
    elif args.model == "gemma2-2b":
        results = run_gemma2(config)
    else:
        results = run_gpt2(config)

    print("\n" + "=" * 60)
    print("DONE")
    print("=" * 60)
    print(f"Manifold counts: {results['manifold_counts']}")
    print(f"Significant variations: {results['significant_scores']}/{results['total_scores']}")
    print(f"Output dir: {config.output_dir}")

    return results


if __name__ == "__main__":
    main()
