"""Modal runner for geometry analysis experiments.

Usage:
    modal run research/geometry_analysis/modal_run.py
    modal run research/geometry_analysis/modal_run.py --n-tokens 1000
"""

import modal

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.0",
        "transformer-lens>=2.0",
        "sae-lens>=4.0",
        "numpy>=1.24",
        "scipy>=1.10",
        "scikit-learn>=1.3",
    )
    .add_local_dir(
        "research/geometry_analysis",
        remote_path="/root/research/geometry_analysis",
    )
)

app = modal.App("geometry-analysis", image=image)


@app.function(gpu="T4", timeout=3600, memory=16384)
def run_geometry(n_tokens: int = 500, layer: int = 6, use_raw: bool = False):
    """Run geometry analysis on Modal GPU."""
    import sys
    sys.path.insert(0, "/root")

    from research.geometry_analysis.run_analysis import run_geometry_analysis

    results = run_geometry_analysis(
        n_tokens=n_tokens,
        layer=layer,
        output_dir="/root/outputs",
        use_raw=use_raw,
    )

    return results


@app.local_entrypoint()
def main(n_tokens: int = 500, layer: int = 6, use_raw: bool = False):
    """Run geometry analysis and save results locally."""
    import json
    from pathlib import Path

    results = run_geometry.remote(n_tokens=n_tokens, layer=layer, use_raw=use_raw)

    output_dir = Path("research/geometry_analysis/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "geometry_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to {output_dir / 'geometry_results.json'}")
