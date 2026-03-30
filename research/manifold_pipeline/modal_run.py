"""Modal deployment for GPU-accelerated pipeline execution.

Usage:
    modal run research/manifold_pipeline/modal_run.py                    # GPT-2
    modal run research/manifold_pipeline/modal_run.py --model gemma2-2b  # Gemma 2 2B

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


@app.function(
    image=image,
    gpu="T4",  # Gemma 2 2B fits on T4 (~4.5GB bf16 + overhead)
    timeout=7200,
    volumes={"/root/data": vol},
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


@app.function(
    image=image,
    gpu="T4",
    timeout=1800,
    volumes={"/root/data": vol},
)
def run_synthetic_validation():
    """Quick synthetic validation on GPU."""
    return run_pipeline_gpt2.local(n_tokens=500)


@app.local_entrypoint()
def main(
    model: str = "gpt2",
    synthetic: bool = False,
    n_tokens: int = 2000,
    layer: int = 13,
):
    """Entry point for `modal run`.

    Args:
        model: Model to run — 'gpt2' or 'gemma2-2b'
        synthetic: Run synthetic validation only
        n_tokens: Tokens per condition
        layer: Transformer layer (default: 13 for Gemma, 6 for GPT-2)
    """
    import json

    if synthetic:
        print("Running synthetic validation on Modal GPU...")
        results = run_synthetic_validation.remote()
    elif model == "gemma2-2b":
        print(f"Running Gemma 2 2B pipeline on Modal GPU (layer={layer}, n_tokens={n_tokens})...")
        results = run_pipeline_gemma2.remote(n_tokens=n_tokens, layer=layer)
    else:
        print(f"Running GPT-2 pipeline on Modal GPU (n_tokens={n_tokens})...")
        results = run_pipeline_gpt2.remote(n_tokens=n_tokens)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(json.dumps(results, indent=2))
