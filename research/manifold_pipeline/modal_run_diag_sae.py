"""Diagnostic SAE: Do SAE feature directions beat k-means at token routing?

Tests whether linear SAE features (from a pretrained GPT-2 Small layer 6 SAE)
capture token-type routing better than k-means on PCA activations.

This is the key question after SMCE failed: is the geometry linear (SAE wins)
or is there simply no routing structure in the residual stream (both fail)?

Usage:
    modal run research/manifold_pipeline/modal_run_diag_sae.py
"""

import modal

app = modal.App("manifold-diag-sae")

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install(
        "torch",
        "numpy",
        "scipy",
        "scikit-learn",
        "matplotlib",
        "transformer-lens",
        "giotto-tda",
        "joblib",
        "sae-lens",
    )
    .add_local_dir(
        "research/manifold_pipeline",
        remote_path="/root/research/manifold_pipeline",
    )
)

vol = modal.Volume.from_name("research")


@app.function(
    image=image,
    gpu="T4",
    timeout=3600,
    volumes={"/root/data": vol},
)
def run_diag_sae(n_tokens: int = 500, layer: int = 6):
    """Run SAE feature MI test against k-means baseline.

    Loads pretrained SAE, extracts feature activations, runs the same
    MI-attribution test that SMCE failed (Phase 1 diagnostics A-E).
    """
    import sys
    sys.path.insert(0, "/root")

    import json
    import time
    import numpy as np
    from pathlib import Path

    from research.manifold_pipeline.config import PipelineConfig
    from research.manifold_pipeline.activation_extraction import (
        load_model, extract_and_reduce_with_tokens,
    )
    from research.manifold_pipeline.token_attribution import (
        classify_is_number, classify_position_bucket,
        classify_token_frequency, classify_bos_vs_content,
        classify_punctuation,
    )
    from research.manifold_pipeline.sae_comparison import (
        load_sae, encode_activations, run_sae_attribution, feature_type_breakdown,
    )

    output_dir = Path(f"/root/data/manifold-pipeline/diag-sae/layer{layer}")
    output_dir.mkdir(parents=True, exist_ok=True)

    config = PipelineConfig.gpt2(
        layer=layer,
        hook_point=f"blocks.{layer}.hook_resid_post",
        n_tokens_per_condition=n_tokens,
        output_dir=output_dir,
        cache_dir=output_dir / "cache",
    )

    t0 = time.time()

    # --- Extract activations ---
    print("=" * 70)
    print(f"DIAGNOSTIC SAE — GPT-2 SMALL LAYER {layer}")
    print("=" * 70)

    import torch
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    model = load_model(config.model_name)
    extraction_results = extract_and_reduce_with_tokens(config, model=model)

    # --- Load SAE ---
    print("\n" + "=" * 70)
    print("LOADING SAE")
    print("=" * 70)
    sae, sae_cfg = load_sae(layer=layer, device=device)

    # --- Extract SAE features and run attribution ---
    print("\n" + "=" * 70)
    print("SAE FEATURE ATTRIBUTION")
    print("=" * 70)

    tokenizer = model.tokenizer
    all_results = []
    condition_summaries = {}

    for condition, er in extraction_results.items():
        print(f"\n--- Condition: {condition} ({er.activations.shape[0]} tokens) ---")

        # SAE was trained on hook_resid_pre, not hook_resid_post.
        # Re-extract raw activations from the correct hook point.
        from research.manifold_pipeline.activation_extraction import (
            generate_condition_texts, extract_activations_with_tokens,
        )
        sae_hook = f"blocks.{layer}.hook_resid_pre"
        n_texts = max(n_tokens // (config.max_seq_len // 2), 20)
        texts = generate_condition_texts(condition, n_texts, config.max_seq_len)
        raw_acts, _, _ = extract_activations_with_tokens(
            model, texts, sae_hook,
            config.max_seq_len, config.batch_size,
        )
        # Subsample to match PCA extraction
        if raw_acts.shape[0] > n_tokens:
            rng = np.random.RandomState(config.random_seed)
            idx = rng.choice(raw_acts.shape[0], n_tokens, replace=False)
            raw_acts = raw_acts[idx]

        print(f"  Raw activations: {raw_acts.shape}")

        # SAE encode
        print(f"  Encoding through SAE ({sae.cfg.d_sae} features)...")
        feature_acts = encode_activations(sae, raw_acts, device=device)
        sparsity = (feature_acts > 0).mean()
        print(f"  Feature activations: {feature_acts.shape}, "
              f"sparsity={sparsity:.3f} ({sparsity * sae.cfg.d_sae:.1f} active/token)")

        # k from SMCE diagnostics for this condition (use 3 as default)
        # We pick k=3 as a reasonable default matching previous runs
        k = 3

        results = run_sae_attribution(
            feature_acts=feature_acts,
            activations=er.activations,   # PCA-reduced, for k-means baseline
            token_ids=er.token_ids,
            positions=er.positions,
            tokenizer=tokenizer,
            condition=condition,
            k=k,
            n_permutations=config.n_permutations,
            seed=config.random_seed,
        )
        all_results.extend(results)

        # Per-condition summary
        n_sig = sum(1 for r in results if r.significant)
        n_total = len(results)
        condition_summaries[condition] = {
            "n_significant": n_sig,
            "n_total": n_total,
            "by_strategy": {},
        }
        for strat in ["top1_feature", "top3_bucket", "sae_kmeans"]:
            strat_results = [r for r in results if r.strategy == strat]
            n_strat_sig = sum(1 for r in strat_results if r.significant)
            condition_summaries[condition]["by_strategy"][strat] = {
                "significant": n_strat_sig,
                "total": len(strat_results),
                "avg_delta": (
                    round(np.mean([r.delta_pct for r in strat_results]), 1)
                    if strat_results else 0
                ),
            }

        # Feature breakdown for is_number (numeric condition only)
        if condition == "numeric":
            print("\n  Feature breakdown for is_number classifier:")
            number_labels = classify_is_number(er.token_ids, tokenizer)
            if len(np.unique(number_labels)) >= 2:
                breakdown = feature_type_breakdown(
                    feature_acts, number_labels, "is_number", top_n=5,
                )
                condition_summaries[condition]["is_number_breakdown"] = breakdown
                for cat_info in breakdown:
                    cat = cat_info["category"]
                    label = "number" if cat == 1 else "non-number"
                    top = cat_info["top_features"][:3]
                    if top:
                        feat_str = ", ".join(
                            f"feat{t['feature_id']}(sel={t['selectivity']:+.3f})"
                            for t in top
                        )
                        print(f"    {label}: {feat_str}")

    t1 = time.time()

    # --- Global summary ---
    print("\n" + "=" * 70)
    print("DIAGNOSTIC SAE — SUMMARY")
    print("=" * 70)

    total_sig = sum(1 for r in all_results if r.significant)
    total_tests = len(all_results)

    print(f"\nTotal significant (SAE beats k-means): {total_sig}/{total_tests}")

    strategy_totals = {}
    for strat in ["top1_feature", "top3_bucket", "sae_kmeans"]:
        strat_res = [r for r in all_results if r.strategy == strat]
        n_sig = sum(1 for r in strat_res if r.significant)
        avg_delta = np.mean([r.delta_pct for r in strat_res]) if strat_res else 0
        strategy_totals[strat] = {
            "significant": n_sig,
            "total": len(strat_res),
            "avg_delta_pct": round(avg_delta, 1),
        }
        print(f"  {strat}: {n_sig}/{len(strat_res)} significant, "
              f"avg delta={avg_delta:+.1f}%")

    # Significant tests detail
    sig_results = [r for r in all_results if r.significant]
    if sig_results:
        print("\n  Significant tests:")
        for r in sig_results:
            print(f"    {r.strategy}/{r.condition}/{r.token_type}: "
                  f"SAE={r.mi_sae:.6f} km={r.mi_kmeans:.6f} ({r.delta_pct:+.1f}%)")

    # Compare to SMCE baseline (from Diag A/B: avg_delta=+0.028, 3/12 significant)
    smce_best_sig = 3
    smce_best_total = 12
    smce_avg_delta = 0.028

    best_strat = max(
        strategy_totals.items(),
        key=lambda x: x[1]["avg_delta_pct"],
    )

    print(f"\n{'=' * 70}")
    print(f"SMCE baseline: {smce_best_sig}/{smce_best_total} significant, "
          f"avg_delta={smce_avg_delta:+.3f}")
    print(f"SAE best ({best_strat[0]}): "
          f"{best_strat[1]['significant']}/{best_strat[1]['total']} significant, "
          f"avg_delta={best_strat[1]['avg_delta_pct']:+.1f}%")

    sae_best_delta = best_strat[1]["avg_delta_pct"]

    if sae_best_delta > smce_avg_delta * 100 * 2:  # factor of 2
        verdict = "SAE_STRONGLY_BEATS_SMCE"
        print(">>> SAE features strongly outperform SMCE manifolds!")
        print(">>> Linear geometry is confirmed. SAE directions are the right abstraction.")
    elif sae_best_delta > smce_avg_delta * 100:
        verdict = "SAE_BEATS_SMCE"
        print(">>> SAE features outperform SMCE manifolds.")
        print(">>> Linear geometry hypothesis supported.")
    elif sae_best_delta > 0:
        verdict = "SAE_SLIGHTLY_BETTER"
        print(">>> SAE marginally better than SMCE, both modest.")
    elif total_sig > 0:
        verdict = "SAE_COMPARABLE_TO_SMCE"
        print(">>> SAE and SMCE show similar MI advantage over k-means.")
    else:
        verdict = "NO_ROUTING_STRUCTURE_FOUND"
        print(">>> Neither SAE features nor SMCE manifolds beat k-means.")
        print(">>> The MI test may not be sensitive to routing structure at layer 6.")

    # Save results
    output = {
        "layer": layer,
        "n_tokens": n_tokens,
        "sae_n_features": sae.cfg.d_sae,
        "total_time_seconds": round(t1 - t0, 1),
        "verdict": verdict,
        "strategy_totals": strategy_totals,
        "condition_summaries": condition_summaries,
        "smce_baseline": {
            "significant": smce_best_sig,
            "total": smce_best_total,
            "avg_delta": smce_avg_delta,
        },
        "all_results": [
            {
                "strategy": r.strategy,
                "condition": r.condition,
                "token_type": r.token_type,
                "mi_sae": r.mi_sae,
                "mi_kmeans": r.mi_kmeans,
                "nmi_sae": r.nmi_sae,
                "nmi_kmeans": r.nmi_kmeans,
                "p_value": r.p_value,
                "significant": r.significant,
                "delta_pct": r.delta_pct,
            }
            for r in all_results
        ],
    }

    class _NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.bool_):
                return bool(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    results_path = output_dir / "sae_results.json"
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2, cls=_NumpyEncoder)

    vol.commit()
    return output


@app.local_entrypoint()
def main(n_tokens: int = 500, layer: int = 6):
    import json
    print(f"Running SAE diagnostic (N={n_tokens}, layer={layer})...")
    result = run_diag_sae.remote(n_tokens=n_tokens, layer=layer)
    print("\n" + "=" * 70)
    print("DIAGNOSTIC SAE RESULTS")
    print("=" * 70)
    print(json.dumps(result, indent=2))
