"""Modal deployment for Gemma 2 2B pipeline.

Usage:
    modal run research/manifold_pipeline/modal_run_gemma2.py
    modal run research/manifold_pipeline/modal_run_gemma2.py --layer 13 --n-tokens 2000

Requires: modal secret create huggingface HF_TOKEN=hf_xxxxx
"""

from .modal_run import gemma2_app, run_pipeline_gemma2

app = gemma2_app


@gemma2_app.local_entrypoint()
def main(
    n_tokens: int = 2000,
    layer: int = 13,
):
    """Run Gemma 2 2B manifold pipeline on Modal GPU."""
    import json

    print(f"Running Gemma 2 2B pipeline on Modal GPU (layer={layer}, n_tokens={n_tokens})...")
    results = run_pipeline_gemma2.remote(n_tokens=n_tokens, layer=layer)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(json.dumps(results, indent=2))
