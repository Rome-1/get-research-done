"""Diagnostic A: PCA linearization test — SMCE on raw 768-dim activations.

Hypothesis: PCA 768→100 destroys curved geometry, making SMCE equivalent
to k-means. Test by running SMCE on raw activations with smaller N (500)
for computational feasibility.

Usage:
    modal run research/manifold_pipeline/modal_run_diag_a.py
"""

import modal

app = modal.App("manifold-diag-a")

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
)
def run_diag_a(n_tokens: int = 500):
    """Run Diagnostic A: compare SMCE vs k-means on raw vs PCA activations.

    Runs two pipelines:
    1. PCA 768→100 (current approach, N=500)
    2. Raw 768-dim (no PCA, N=500)

    Returns comparative results.
    """
    import sys
    sys.path.insert(0, "/root")

    import json
    import numpy as np
    from pathlib import Path

    from research.manifold_pipeline.config import PipelineConfig
    from research.manifold_pipeline.run_pipeline import run_gpt2

    results = {}

    # --- Run 1: PCA (control) ---
    print("\n" + "=" * 70)
    print("DIAGNOSTIC A — RUN 1: PCA 768→100 (control)")
    print("=" * 70)
    output_pca = Path("/root/data/manifold-pipeline/diag-a/pca")
    config_pca = PipelineConfig.gpt2(
        n_tokens_per_condition=n_tokens,
        pca_dim=100,
        output_dir=output_pca,
        cache_dir=output_pca / "cache",
    )
    results["pca"] = run_gpt2(config_pca)

    # --- Run 2: No PCA (test) ---
    print("\n" + "=" * 70)
    print("DIAGNOSTIC A — RUN 2: RAW 768-dim (no PCA)")
    print("=" * 70)
    output_raw = Path("/root/data/manifold-pipeline/diag-a/raw")
    config_raw = PipelineConfig.gpt2(
        n_tokens_per_condition=n_tokens,
        pca_dim=None,
        output_dir=output_raw,
        cache_dir=output_raw / "cache",
    )
    results["raw"] = run_gpt2(config_raw)

    # --- Comparison ---
    print("\n" + "=" * 70)
    print("DIAGNOSTIC A — COMPARISON")
    print("=" * 70)

    comparison = {"n_tokens": n_tokens, "tests": []}

    for label, res in results.items():
        gate = res.get("phase1_gate", {})
        attribution = gate.get("attribution", {})
        dim_label = "PCA→100" if label == "pca" else "Raw 768"
        print(f"\n--- {dim_label} ---")
        print(f"  Gate: {'PROCEED' if gate.get('proceed') else 'KILL'}")
        print(f"  Manifold counts: {res.get('manifold_counts')}")

        for cond, attrs in attribution.items():
            for a in attrs:
                smce_mi = a["mi_observed"]
                km_mi = a["mi_kmeans"]
                delta = (smce_mi - km_mi) / km_mi * 100 if km_mi > 0 else float("inf")
                entry = {
                    "dim": dim_label,
                    "condition": cond,
                    "token_type": a["token_type"],
                    "mi_smce": smce_mi,
                    "mi_kmeans": km_mi,
                    "nmi_smce": a["nmi_observed"],
                    "nmi_kmeans": a["nmi_kmeans"],
                    "delta_pct": round(delta, 1),
                    "significant": a["significant"],
                }
                comparison["tests"].append(entry)
                status = "SMCE WINS" if a["significant"] else "parity"
                print(f"  {cond}/{a['token_type']}: "
                      f"SMCE={smce_mi:.6f} km={km_mi:.6f} "
                      f"({delta:+.1f}%) [{status}]")

    # Check if raw activations show SMCE advantage where PCA doesn't
    pca_tests = [t for t in comparison["tests"] if t["dim"] == "PCA→100"]
    raw_tests = [t for t in comparison["tests"] if t["dim"] == "Raw 768"]

    pca_wins = sum(1 for t in pca_tests if t["significant"])
    raw_wins = sum(1 for t in raw_tests if t["significant"])

    print(f"\n{'=' * 70}")
    print(f"VERDICT: PCA significant tests: {pca_wins}/{len(pca_tests)}, "
          f"Raw significant tests: {raw_wins}/{len(raw_tests)}")

    if raw_wins > pca_wins:
        comparison["verdict"] = "PCA_IS_THE_PROBLEM"
        print(">>> SMCE beats k-means on RAW but not PCA!")
        print(">>> PCA linearization destroys manifold geometry.")
        print(">>> RECOMMENDATION: Switch to nonlinear dim reduction (UMAP/diffusion maps).")
    elif raw_wins == 0 and pca_wins == 0:
        comparison["verdict"] = "SMCE_NEVER_BEATS_KMEANS"
        print(">>> SMCE never beats k-means in either setting.")
        print(">>> Manifold decomposition adds no value at layer 6 / GPT-2.")
    elif raw_wins == pca_wins:
        comparison["verdict"] = "PCA_NOT_THE_PROBLEM"
        print(">>> Same SMCE advantage with and without PCA.")
        print(">>> PCA is not destroying manifold structure.")
    else:
        comparison["verdict"] = "PCA_HELPS"
        print(">>> PCA actually helps SMCE! Raw space too noisy.")

    # Save comparison
    comp_path = Path("/root/data/manifold-pipeline/diag-a/comparison.json")
    comp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(comp_path, "w") as f:
        json.dump(comparison, f, indent=2)

    vol.commit()
    return comparison


@app.local_entrypoint()
def main(n_tokens: int = 500):
    import json
    print(f"Running Diagnostic A (N={n_tokens} tokens/condition)...")
    result = run_diag_a.remote(n_tokens=n_tokens)
    print("\n" + "=" * 70)
    print("DIAGNOSTIC A RESULTS")
    print("=" * 70)
    print(json.dumps(result, indent=2))
