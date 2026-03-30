"""Modal deployment for GPU-accelerated pipeline execution.

Usage:
    modal run research/manifold_pipeline/modal_run.py                    # GPT-2
    modal run research/manifold_pipeline/modal_run.py --model gemma2-2b  # Gemma 2 2B

This runs the full pipeline on a Modal GPU instance with all dependencies
pre-installed. Results are saved to a Modal Volume and downloaded locally.
"""

import modal

# GPT-2 app — no secrets needed
gpt2_app = modal.App("manifold-pipeline-gpt2")

# Gemma 2 app — needs HF secret for gated model access
gemma2_app = modal.App("manifold-pipeline-gemma2")

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

# Shared research volume
vol = modal.Volume.from_name("research")


@gpt2_app.function(
    image=image,
    gpu="T4",
    timeout=3600,
    volumes={"/root/data": vol},
)
def run_pipeline_gpt2(n_tokens: int = 2000):
    """Run the manifold detection pipeline on GPT-2 Small."""
    import sys
    sys.path.insert(0, "/root")

    from research.manifold_pipeline.config import PipelineConfig
    from research.manifold_pipeline.run_pipeline import run_gpt2
    from pathlib import Path

    output_dir = Path("/root/data/manifold-pipeline/outputs")
    config = PipelineConfig.gpt2(
        n_tokens_per_condition=n_tokens,
        output_dir=output_dir,
        cache_dir=output_dir / "cache",
    )

    results = run_gpt2(config)
    vol.commit()
    return results


@gemma2_app.function(
    image=image,
    gpu="T4",
    timeout=7200,
    volumes={"/root/data": vol},
    secrets=[modal.Secret.from_name("huggingface")],
)
def run_pipeline_gemma2(n_tokens: int = 2000, layer: int = 13):
    """Run the manifold detection pipeline on Gemma 2 2B."""
    import sys
    sys.path.insert(0, "/root")

    from research.manifold_pipeline.config import PipelineConfig
    from research.manifold_pipeline.run_pipeline import run_gemma2
    from pathlib import Path

    output_dir = Path("/root/data/manifold-pipeline/gemma2-2b/outputs")
    config = PipelineConfig.gemma2_2b(
        layer=layer,
        n_tokens_per_condition=n_tokens,
        output_dir=output_dir,
        cache_dir=output_dir / "cache",
    )

    results = run_gemma2(config)
    vol.commit()
    return results


# Use GPT-2 app as the default entrypoint
app = gpt2_app


@gpt2_app.local_entrypoint()
def main(
    n_tokens: int = 2000,
    synthetic: bool = False,
):
    """GPT-2 pipeline entry point.

    For Gemma 2, use: modal run research/manifold_pipeline/modal_run_gemma2.py
    """
    import json

    if synthetic:
        print("Running synthetic validation on Modal GPU...")
        from research.manifold_pipeline.config import PipelineConfig
        from research.manifold_pipeline.run_pipeline import run_synthetic
        # Synthetic runs locally (no GPU needed for small data)
        results = run_pipeline_gpt2.remote(n_tokens=500)
    else:
        print(f"Running GPT-2 pipeline on Modal GPU (n_tokens={n_tokens})...")
        results = run_pipeline_gpt2.remote(n_tokens=n_tokens)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(json.dumps(results, indent=2))
