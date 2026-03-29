"""Modal deployment for GPU-accelerated pipeline execution.

Usage:
    modal run research/manifold_pipeline/modal_run.py

This runs the full pipeline on a Modal GPU instance with all dependencies
pre-installed. Results are saved to a Modal Volume and downloaded locally.
"""

import modal

app = modal.App("manifold-pipeline")

# Image with all dependencies
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

# Shared research volume — our data lives under /root/data/manifold-pipeline/
vol = modal.Volume.from_name("research")


@app.function(
    image=image,
    gpu="T4",  # T4 is cheapest, sufficient for GPT-2 Small
    timeout=3600,
    volumes={"/root/data": vol},
)
def run_pipeline(synthetic: bool = False, n_tokens: int = 2000):
    """Run the manifold detection pipeline on Modal GPU."""
    import sys
    sys.path.insert(0, "/root")

    from research.manifold_pipeline.config import PipelineConfig
    from research.manifold_pipeline.run_pipeline import run_synthetic, run_gpt2
    from pathlib import Path

    output_dir = Path("/root/data/manifold-pipeline/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    config = PipelineConfig(
        n_tokens_per_condition=n_tokens,
        pca_dim=100,
        smce_alpha=0.05,
        max_k_manifolds=15,
        n_permutations=1000,
        output_dir=output_dir,
        cache_dir=output_dir / "cache",
    )

    if synthetic:
        results = run_synthetic(config)
    else:
        results = run_gpt2(config)

    vol.commit()
    return results


@app.function(
    image=image,
    gpu="T4",
    timeout=1800,
    volumes={"/root/data": vol},
)
def run_synthetic_validation():
    """Quick synthetic validation on GPU."""
    return run_pipeline.local(synthetic=True, n_tokens=500)


@app.local_entrypoint()
def main(
    synthetic: bool = False,
    n_tokens: int = 2000,
):
    """Entry point for `modal run`.

    Args:
        synthetic: Run synthetic validation only
        n_tokens: Tokens per condition for GPT-2 run
    """
    import json

    if synthetic:
        print("Running synthetic validation on Modal GPU...")
        results = run_synthetic_validation.remote()
    else:
        print(f"Running GPT-2 pipeline on Modal GPU (n_tokens={n_tokens})...")
        results = run_pipeline.remote(synthetic=False, n_tokens=n_tokens)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(json.dumps(results, indent=2))

    # Download outputs
    print("\nDownloading outputs from Modal Volume...")
    # Note: use `modal volume get research /manifold-pipeline/outputs ./outputs` to download
    print("Run: modal volume get research /manifold-pipeline/outputs research/manifold_pipeline/outputs/")
