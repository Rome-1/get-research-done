"""Diagnostic D: Gemma 2 2B — does manifold structure emerge at scale?

Hypothesis: GPT-2 Small (117M, 768-dim) is too small for nontrivial manifold
geometry. Gemma 2 2B (2.6B params, 2304-dim hidden) under more superposition
pressure may pack representations onto curved manifolds that k-means can't capture.

Test: Run attribution-only pipeline on Gemma 2 2B at layer 13.
Compare SMCE vs k-means MI gap to GPT-2 results.

Usage:
    modal run research/manifold_pipeline/modal_run_diag_d.py
"""

import modal

app = modal.App("manifold-diag-d")

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
    timeout=7200,
    volumes={"/root/data": vol},
    secrets=[modal.Secret.from_name("hf_token")],
)
def run_diag_d(n_tokens: int = 500, layers: list[int] = None):
    """Run attribution-only pipeline on Gemma 2 2B.

    Compares SMCE vs k-means MI at multiple layers.
    Default layers: [6, 13, 20] (early, mid, late of 26-layer network).
    """
    import sys
    sys.path.insert(0, "/root")

    import json
    from pathlib import Path

    from research.manifold_pipeline.config import PipelineConfig
    from research.manifold_pipeline.run_pipeline import run_attribution_only

    if layers is None:
        layers = [6, 13, 20]

    all_results = {}

    for layer in layers:
        print(f"\n{'=' * 70}")
        print(f"DIAGNOSTIC D — GEMMA 2 2B LAYER {layer}")
        print(f"{'=' * 70}")

        output_dir = Path(f"/root/data/manifold-pipeline/diag-d/layer{layer}")
        config = PipelineConfig.gemma2_2b(
            layer=layer,
            n_tokens_per_condition=n_tokens,
            output_dir=output_dir,
            cache_dir=output_dir / "cache",
        )

        try:
            result = run_attribution_only(config)
            all_results[f"layer_{layer}"] = result
        except Exception as e:
            print(f"ERROR at layer {layer}: {e}")
            all_results[f"layer_{layer}"] = {"error": str(e)}

    # --- Summary ---
    print(f"\n{'=' * 70}")
    print("DIAGNOSTIC D — GEMMA 2 SUMMARY")
    print(f"{'=' * 70}")

    summary = {"model": "gemma-2-2b", "n_tokens": n_tokens, "layers": []}

    for layer in layers:
        key = f"layer_{layer}"
        res = all_results.get(key, {})
        if "error" in res:
            print(f"  Layer {layer}: ERROR — {res['error']}")
            summary["layers"].append({"layer": layer, "error": res["error"]})
            continue

        gate = res.get("phase1_gate", {})
        attr = gate.get("attribution", {})
        manifold_counts = res.get("manifold_counts", {})

        n_sig = 0
        n_total = 0
        total_delta = 0.0
        best_tests = []

        for cond, tests in attr.items():
            for t in tests:
                smce = t["mi_observed"]
                km = t["mi_kmeans"]
                delta = smce - km
                total_delta += delta
                n_total += 1
                if t["significant"]:
                    n_sig += 1
                    delta_pct = (delta / km * 100) if km > 0 else float("inf")
                    best_tests.append(f"{cond}/{t['token_type']}({delta_pct:+.0f}%)")

        avg_delta = total_delta / n_total if n_total > 0 else 0
        proceed = gate.get("proceed", False)
        print(f"  Layer {layer}: k={manifold_counts}, gate={'PROCEED' if proceed else 'KILL'}, "
              f"significant={n_sig}/{n_total}, avg_delta={avg_delta:+.6f}")
        if best_tests:
            print(f"    Best: {', '.join(best_tests[:3])}")

        summary["layers"].append({
            "layer": layer,
            "proceed": proceed,
            "manifold_counts": manifold_counts,
            "n_significant": n_sig,
            "n_total": n_total,
            "avg_mi_delta": round(avg_delta, 6),
            "significant_tests": best_tests,
        })

    # Compare to GPT-2 baseline (from Diagnostic B: best layer had avg_delta=+0.028)
    gpt2_best_delta = 0.028  # layer 3, numeric condition
    gemma_best = max(
        [l for l in summary["layers"] if "error" not in l],
        key=lambda l: l.get("avg_mi_delta", -999),
        default=None,
    )
    if gemma_best:
        summary["best_layer"] = gemma_best["layer"]
        summary["best_avg_delta"] = gemma_best["avg_mi_delta"]
        print(f"\nBest Gemma 2 layer: {gemma_best['layer']} "
              f"(avg delta={gemma_best['avg_mi_delta']:+.6f} "
              f"vs GPT-2 best={gpt2_best_delta:+.3f})")

        if gemma_best["avg_mi_delta"] > gpt2_best_delta * 2:
            summary["verdict"] = "SCALE_HELPS_STRONGLY"
            print(">>> Scale hypothesis CONFIRMED: Gemma 2 shows much stronger SMCE advantage!")
        elif gemma_best["avg_mi_delta"] > gpt2_best_delta:
            summary["verdict"] = "SCALE_HELPS_MODESTLY"
            print(">>> Scale hypothesis PARTIALLY confirmed: Gemma 2 shows modestly more SMCE advantage.")
        elif gemma_best["avg_mi_delta"] > 0:
            summary["verdict"] = "SCALE_HELPS_WEAKLY"
            print(">>> Weak scale effect — Gemma 2 SMCE advantage present but modest vs GPT-2.")
        else:
            summary["verdict"] = "SCALE_DOES_NOT_HELP"
            print(">>> Scale hypothesis FAILED: Gemma 2 shows no more SMCE advantage than GPT-2.")

    # Save
    out_path = Path("/root/data/manifold-pipeline/diag-d/summary.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)

    vol.commit()
    return summary


@app.local_entrypoint()
def main(n_tokens: int = 500):
    import json
    print(f"Running Diagnostic D: Gemma 2 2B (N={n_tokens}, layers=[6,13,20])...")
    result = run_diag_d.remote(n_tokens=n_tokens)
    print("\n" + "=" * 70)
    print("DIAGNOSTIC D RESULTS")
    print("=" * 70)
    print(json.dumps(result, indent=2))
