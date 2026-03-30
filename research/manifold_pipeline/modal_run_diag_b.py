"""Diagnostic B: Multi-layer sweep — SMCE vs k-means gap across layers.

Hypothesis: Layer 6 is linearly separable but other layers have curved
manifold structure. Run SMCE + k-means at layers 0, 3, 6, 9, 11.

Usage:
    modal run research/manifold_pipeline/modal_run_diag_b.py
"""

import modal

app = modal.App("manifold-diag-b")

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
    timeout=10800,  # 3 hours for 5 layers
    volumes={"/root/data": vol},
)
def run_diag_b(n_tokens: int = 500, layers: list[int] = None):
    """Run Diagnostic B: SMCE vs k-means across multiple layers.

    For each layer, compute MI(SMCE) - MI(k-means) for all classifiers.
    """
    import sys
    sys.path.insert(0, "/root")

    import json
    import numpy as np
    from pathlib import Path

    from research.manifold_pipeline.config import PipelineConfig
    from research.manifold_pipeline.run_pipeline import run_gpt2

    if layers is None:
        layers = [0, 3, 6, 9, 11]

    all_results = {}

    for layer in layers:
        print(f"\n{'=' * 70}")
        print(f"DIAGNOSTIC B — LAYER {layer}")
        print(f"{'=' * 70}")

        output_dir = Path(f"/root/data/manifold-pipeline/diag-b/layer{layer}")
        config = PipelineConfig.gpt2(
            n_tokens_per_condition=n_tokens,
            layer=layer,
            hook_point=f"blocks.{layer}.hook_resid_post",
            output_dir=output_dir,
            cache_dir=output_dir / "cache",
        )
        try:
            result = run_gpt2(config)
            all_results[f"layer_{layer}"] = result
        except Exception as e:
            print(f"ERROR at layer {layer}: {e}")
            all_results[f"layer_{layer}"] = {"error": str(e)}

    # --- Build sweep summary ---
    print(f"\n{'=' * 70}")
    print("DIAGNOSTIC B — LAYER SWEEP SUMMARY")
    print(f"{'=' * 70}")

    sweep = {"n_tokens": n_tokens, "layers": [], "layer_details": {}}

    for layer in layers:
        key = f"layer_{layer}"
        res = all_results.get(key, {})
        if "error" in res:
            print(f"  Layer {layer}: ERROR — {res['error']}")
            sweep["layers"].append({"layer": layer, "error": res["error"]})
            continue

        gate = res.get("phase1_gate", {})
        attribution = gate.get("attribution", {})
        manifold_counts = res.get("manifold_counts", {})

        layer_summary = {
            "layer": layer,
            "proceed": gate.get("proceed", False),
            "manifold_counts": manifold_counts,
            "tests": [],
        }

        print(f"\n  Layer {layer}: k={manifold_counts}, "
              f"gate={'PROCEED' if gate.get('proceed') else 'KILL'}")

        total_delta = 0
        n_tests = 0
        for cond, attrs in attribution.items():
            for a in attrs:
                smce_mi = a["mi_observed"]
                km_mi = a["mi_kmeans"]
                delta = smce_mi - km_mi
                delta_pct = (delta / km_mi * 100) if km_mi > 0 else float("inf")
                layer_summary["tests"].append({
                    "condition": cond,
                    "token_type": a["token_type"],
                    "mi_smce": smce_mi,
                    "mi_kmeans": km_mi,
                    "mi_delta": round(delta, 6),
                    "delta_pct": round(delta_pct, 1),
                    "significant": a["significant"],
                })
                total_delta += delta
                n_tests += 1
                sig = "*" if a["significant"] else " "
                print(f"    {sig} {cond}/{a['token_type']}: "
                      f"SMCE-km={delta:+.6f} ({delta_pct:+.1f}%)")

        avg_delta = total_delta / n_tests if n_tests > 0 else 0
        layer_summary["avg_mi_delta"] = round(avg_delta, 6)
        layer_summary["n_significant"] = sum(
            1 for t in layer_summary["tests"] if t["significant"]
        )
        sweep["layers"].append(layer_summary)
        print(f"  Layer {layer} avg SMCE-km delta: {avg_delta:+.6f}, "
              f"significant: {layer_summary['n_significant']}/{n_tests}")

    # Find the layer with max SMCE advantage
    valid_layers = [l for l in sweep["layers"] if "error" not in l]
    if valid_layers:
        best = max(valid_layers, key=lambda l: l.get("avg_mi_delta", 0))
        sweep["best_layer"] = best["layer"]
        sweep["best_avg_delta"] = best.get("avg_mi_delta", 0)

        print(f"\n{'=' * 70}")
        print(f"BEST LAYER: {best['layer']} (avg delta={best.get('avg_mi_delta', 0):+.6f})")

        if best.get("avg_mi_delta", 0) > 0:
            print(">>> SMCE advantage found — manifold structure is layer-dependent!")
        else:
            print(">>> No SMCE advantage at any layer — GPT-2 may lack manifold structure.")

    # Save results
    sweep_path = Path("/root/data/manifold-pipeline/diag-b/sweep_summary.json")
    sweep_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sweep_path, "w") as f:
        json.dump(sweep, f, indent=2)

    vol.commit()
    return sweep


@app.local_entrypoint()
def main(n_tokens: int = 500):
    import json
    print(f"Running Diagnostic B (N={n_tokens}, layers=[0,3,6,9,11])...")
    result = run_diag_b.remote(n_tokens=n_tokens)
    print("\n" + "=" * 70)
    print("DIAGNOSTIC B RESULTS")
    print("=" * 70)
    print(json.dumps(result, indent=2))
