"""Diagnostic E: Nonlinear dim reduction — UMAP and diffusion maps as SMCE preprocessing.

Hypothesis: PCA linearizes activation space, erasing curved manifold geometry.
UMAP and diffusion maps preserve local neighborhood structure, giving SMCE
a fair chance to find non-linear manifolds.

Test: Run attribution-only pipeline with three preprocessing methods:
1. PCA→100 (current baseline)
2. UMAP→50
3. Diffusion maps→5

Usage:
    modal run research/manifold_pipeline/modal_run_diag_e.py
"""

import modal

app = modal.App("manifold-diag-e")

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
        "umap-learn",
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
)
def run_diag_e(n_tokens: int = 500):
    """Compare SMCE vs k-means across three preprocessing methods."""
    import sys
    sys.path.insert(0, "/root")

    import json
    from pathlib import Path

    from research.manifold_pipeline.config import PipelineConfig
    from research.manifold_pipeline.run_pipeline import run_attribution_only

    methods = [
        {
            "name": "PCA→100",
            "overrides": {"dim_reduction": "pca", "pca_dim": 100},
        },
        {
            "name": "UMAP→50",
            "overrides": {
                "dim_reduction": "umap",
                "pca_dim": None,
                "umap_n_components": 50,
                "umap_n_neighbors": 30,
            },
        },
        {
            "name": "Diffusion→5",
            "overrides": {
                "dim_reduction": "diffusion",
                "pca_dim": None,
                "diffusion_n_components": 5,
            },
        },
    ]

    all_results = {}

    for m in methods:
        label = m["name"]
        print(f"\n{'=' * 70}")
        print(f"DIAGNOSTIC E — {label}")
        print(f"{'=' * 70}")

        output_dir = Path(f"/root/data/manifold-pipeline/diag-e/{label.replace('→', '-').replace(' ', '_')}")
        config = PipelineConfig.gpt2(
            n_tokens_per_condition=n_tokens,
            output_dir=output_dir,
            cache_dir=output_dir / "cache",
            **m["overrides"],
        )

        try:
            result = run_attribution_only(config)
            all_results[label] = result
        except Exception as e:
            print(f"ERROR with {label}: {e}")
            import traceback
            traceback.print_exc()
            all_results[label] = {"error": str(e)}

    # --- Comparison ---
    print(f"\n{'=' * 70}")
    print("DIAGNOSTIC E — COMPARISON")
    print(f"{'=' * 70}")

    comparison = {"n_tokens": n_tokens, "methods": []}

    for label, res in all_results.items():
        if "error" in res:
            print(f"\n{label}: ERROR — {res['error']}")
            comparison["methods"].append({"method": label, "error": res["error"]})
            continue

        gate = res.get("phase1_gate", {})
        attr = gate.get("attribution", {})
        manifold_counts = res.get("manifold_counts", {})

        n_sig = 0
        n_total = 0
        total_delta = 0.0
        test_details = []

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
                test_details.append({
                    "condition": cond,
                    "token_type": t["token_type"],
                    "mi_smce": smce,
                    "mi_kmeans": km,
                    "delta_pct": round(delta_pct, 1),
                    "significant": t["significant"],
                })

        avg_delta = total_delta / n_total if n_total > 0 else 0
        proceed = gate.get("proceed", False)

        print(f"\n{label}: k={manifold_counts}, gate={'PROCEED' if proceed else 'KILL'}")
        print(f"  significant={n_sig}/{n_total}, avg_delta={avg_delta:+.6f}")

        sig_tests = [t for t in test_details if t["significant"]]
        for t in sig_tests:
            print(f"  * {t['condition']}/{t['token_type']}: "
                  f"SMCE={t['mi_smce']:.6f} km={t['mi_kmeans']:.6f} ({t['delta_pct']:+.1f}%)")

        comparison["methods"].append({
            "method": label,
            "proceed": proceed,
            "manifold_counts": manifold_counts,
            "n_significant": n_sig,
            "n_total": n_total,
            "avg_mi_delta": round(avg_delta, 6),
            "tests": test_details,
        })

    # Verdict: which method gives the best SMCE advantage?
    valid = [m for m in comparison["methods"] if "error" not in m]
    if valid:
        best = max(valid, key=lambda m: m.get("avg_mi_delta", -999))
        comparison["best_method"] = best["method"]
        comparison["best_avg_delta"] = best["avg_mi_delta"]

        pca_delta = next(
            (m["avg_mi_delta"] for m in valid if m["method"] == "PCA→100"), 0
        )

        print(f"\n{'=' * 70}")
        print(f"BEST METHOD: {best['method']} (avg delta={best['avg_mi_delta']:+.6f})")
        print(f"PCA baseline avg delta: {pca_delta:+.6f}")

        if best["method"] != "PCA→100" and best["avg_mi_delta"] > pca_delta * 1.5:
            comparison["verdict"] = "NONLINEAR_WINS"
            print(">>> Nonlinear preprocessing REVEALS manifold structure!")
            print(">>> PCA was bottleneck — switch to " + best["method"])
        elif best["method"] != "PCA→100" and best["avg_mi_delta"] > pca_delta:
            comparison["verdict"] = "NONLINEAR_HELPS"
            print(">>> Nonlinear preprocessing modestly improves SMCE advantage.")
        elif best["avg_mi_delta"] <= 0:
            comparison["verdict"] = "PREPROCESSING_IRRELEVANT"
            print(">>> No preprocessing gives SMCE advantage over k-means.")
            print(">>> Activation space is linearly separable — manifold thesis may be wrong.")
        else:
            comparison["verdict"] = "PCA_IS_FINE"
            print(">>> PCA performs as well as nonlinear methods.")

    # Save
    out_path = Path("/root/data/manifold-pipeline/diag-e/comparison.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(comparison, f, indent=2)

    vol.commit()
    return comparison


@app.local_entrypoint()
def main(n_tokens: int = 500):
    import json
    print(f"Running Diagnostic E: UMAP/diffusion/PCA comparison (N={n_tokens})...")
    result = run_diag_e.remote(n_tokens=n_tokens)
    print("\n" + "=" * 70)
    print("DIAGNOSTIC E RESULTS")
    print("=" * 70)
    print(json.dumps(result, indent=2))
