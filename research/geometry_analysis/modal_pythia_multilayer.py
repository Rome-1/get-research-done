"""Modal pipeline: Multi-layer Pythia training dynamics.

Research question: Is the SAE alignment phase transition at step ~113k
layer-specific or global? Does it propagate layer-by-layer?

Approach:
  - Run the same fixed-SAE probe pipeline from modal_pythia_dynamics.py
  - Apply to ALL 6 residual stream layers (0-5) of Pythia-70m-deduped
  - Use a subset of checkpoints (20 key steps) to keep compute tractable
  - Compare alignment transition timing across layers

Usage:
    # Pilot: 3 layers × 10 steps (30 jobs)
    modal run research/geometry_analysis/modal_pythia_multilayer.py::app.pilot

    # Full: 6 layers × 20 steps (120 jobs)
    modal run research/geometry_analysis/modal_pythia_multilayer.py::app.full_run
"""

import modal

# ---------------------------------------------------------------------------
# Image
# ---------------------------------------------------------------------------

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install(
        "torch>=2.0",
        "transformer-lens>=2.0",
        "sae-lens>=4.0",
        "numpy>=1.24",
        "scipy>=1.10",
        "scikit-learn>=1.3",
        "huggingface-hub>=0.20",
    )
    .add_local_dir(
        "research/geometry_analysis",
        remote_path="/root/research/geometry_analysis",
    )
)

app = modal.App("pythia-multilayer", image=image)
vol = modal.Volume.from_name("research")
hf_secret = modal.Secret.from_name("hf_token")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_ID = "EleutherAI/pythia-70m-deduped"
SAE_RELEASE = "pythia-70m-deduped-res-sm"
OUTPUT_BASE = "/root/data/geometry-analysis/pythia-multilayer"

# All 6 residual stream layers
LAYERS = [0, 1, 2, 3, 4, 5]
LAYER_CONFIG = {
    layer: {
        "sae_id": f"blocks.{layer}.hook_resid_post",
        "hook_point": f"blocks.{layer}.hook_resid_post",
    }
    for layer in LAYERS
}

# Key checkpoints: early (geometric), around transitions, and late
# 20 steps chosen to cover the three phases identified in ge-97d
FULL_STEPS = [
    0, 8, 32, 64, 128, 512,           # Early/initialization
    1000, 3000, 10000, 23000,          # Phase 1: capability acquisition
    43000, 63000, 80000,               # Phase 2: plateau
    93000, 99000, 103000,              # Around epoch boundary
    107000, 113000, 123000, 143000,    # Phase 3: consolidation
]

PILOT_STEPS = [0, 32, 1000, 23000, 80000, 99000, 113000, 133000, 143000]
PILOT_LAYERS = [0, 3, 5]  # First, middle, last


# ---------------------------------------------------------------------------
# Core metric computation (per layer, per step)
# ---------------------------------------------------------------------------


def compute_layer_step_metrics(
    layer: int,
    step: int,
    n_tokens: int = 1000,
) -> dict:
    """Load Pythia at a checkpoint and compute geometric metrics for one layer."""
    import sys
    import time

    import numpy as np
    import torch
    from transformer_lens import HookedTransformer

    sys.path.insert(0, "/root")

    t0 = time.time()
    cfg = LAYER_CONFIG[layer]
    hook_point = cfg["hook_point"]
    sae_id = cfg["sae_id"]

    print(f"\n[L{layer} step={step}] Starting...")

    # Load model at checkpoint
    model = HookedTransformer.from_pretrained(
        "pythia-70m-deduped",
        checkpoint_value=step,
        dtype=torch.float32,
    )
    model.eval()
    print(f"[L{layer} step={step}] Model loaded ({time.time() - t0:.1f}s)")

    # Load SAE for this layer
    from sae_lens import SAE

    sae = SAE.from_pretrained(
        release=SAE_RELEASE,
        sae_id=sae_id,
        device="cpu",
    )
    sae.eval()
    n_features = sae.cfg.d_sae
    d_in = sae.cfg.d_in
    print(f"[L{layer} step={step}] SAE: {n_features} features, d_in={d_in}")

    sae_W = sae.W_enc.detach().cpu().numpy()
    if sae_W.shape[0] == d_in:
        sae_W = sae_W.T

    # Generate activations
    texts = _generate_texts(n_tokens)
    tokens = model.to_tokens(texts, prepend_bos=True)
    if tokens.shape[1] > 128:
        tokens = tokens[:, :128]

    with torch.no_grad():
        _, cache = model.run_with_cache(tokens, names_filter=[hook_point])

    acts_raw = cache[hook_point].cpu().float().numpy()
    acts_raw = acts_raw.reshape(-1, acts_raw.shape[-1])

    if acts_raw.shape[0] > n_tokens:
        rng = np.random.RandomState(42)
        idx = rng.choice(acts_raw.shape[0], n_tokens, replace=False)
        acts_raw = acts_raw[idx]

    del model, cache
    import gc
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # --- Metric 1: SAE reconstruction quality ---
    X = torch.from_numpy(acts_raw).float()
    with torch.no_grad():
        feature_acts = sae.encode(X).cpu().numpy()
        X_recon = sae.decode(torch.from_numpy(feature_acts)).cpu().numpy()

    ss_res = np.sum((acts_raw - X_recon) ** 2)
    ss_tot = np.sum((acts_raw - acts_raw.mean(0)) ** 2)
    var_explained = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    mse = float(np.mean((acts_raw - X_recon) ** 2))

    # --- Metric 2: Feature activation statistics ---
    active_mask = feature_acts > 0
    sparsity = float(active_mask.mean())
    active_per_token = active_mask.sum(axis=1).astype(float)
    l0_mean = float(active_per_token.mean())
    l0_std = float(active_per_token.std())
    feature_rates = active_mask.mean(axis=0)
    n_dead = int((feature_rates == 0).sum())
    n_active_features = int((feature_rates > 0).sum())
    mean_rate = float(feature_rates[feature_rates > 0].mean()) if n_active_features > 0 else 0.0

    # --- Metric 3: Intrinsic dimension ---
    from sklearn.decomposition import PCA

    n_components = min(50, acts_raw.shape[0] - 1, acts_raw.shape[1])
    pca = PCA(n_components=n_components, random_state=42)
    acts_pca = pca.fit_transform(acts_raw)
    var_50 = float(pca.explained_variance_ratio_.sum())

    try:
        from research.geometry_analysis.intrinsic_dimension import two_nn_dimension
        twonn = two_nn_dimension(acts_pca)
        intrinsic_dim = float(twonn.global_dim)
    except Exception as e:
        print(f"[L{layer} step={step}] Two-NN failed: {e}")
        intrinsic_dim = float("nan")

    # --- Metric 4: Feature region geometry ---
    try:
        from research.geometry_analysis.feature_geometry import analyze_feature_regions

        regions = analyze_feature_regions(
            acts_pca, feature_acts, sae_W=sae_W, top_k=20, min_active=15,
        )
        convexities = [r.convexity_score for r in regions
                       if not np.isnan(r.convexity_score)]
        linearities = [r.boundary_linearity for r in regions
                       if not np.isnan(r.boundary_linearity)]
        mean_convexity = float(np.mean(convexities)) if convexities else float("nan")
        mean_linearity = float(np.mean(linearities)) if linearities else float("nan")
        n_regions_analyzed = len(regions)
    except Exception as e:
        print(f"[L{layer} step={step}] Feature geometry failed: {e}")
        mean_convexity = float("nan")
        mean_linearity = float("nan")
        n_regions_analyzed = 0

    elapsed = time.time() - t0
    print(f"[L{layer} step={step}] Done in {elapsed:.1f}s: "
          f"var_exp={var_explained:.4f}, l0={l0_mean:.1f}, "
          f"convex={mean_convexity:.3f}, linear={mean_linearity:.3f}")

    return {
        "layer": layer,
        "step": step,
        "elapsed_s": elapsed,
        "n_tokens": acts_raw.shape[0],
        "sae_quality": {"var_explained": var_explained, "mse": mse},
        "feature_stats": {
            "sparsity": sparsity,
            "l0_mean": l0_mean,
            "l0_std": l0_std,
            "n_dead_features": n_dead,
            "n_active_features": n_active_features,
            "mean_activation_rate": mean_rate,
        },
        "intrinsic_dimension": {"two_nn": intrinsic_dim, "pca_var_50": var_50},
        "feature_geometry": {
            "mean_convexity": mean_convexity,
            "mean_boundary_linearity": mean_linearity,
            "n_regions_analyzed": n_regions_analyzed,
        },
    }


def _generate_texts(n_tokens: int) -> list:
    """Generate a varied text corpus for activation extraction."""
    import random

    rng = random.Random(42)
    seq_len = 128
    n_texts = max(n_tokens // (seq_len // 4), 30)

    subjects = ["The cat", "A researcher", "My friend", "The system", "Scientists"]
    verbs = ["discovered", "analyzed", "created", "observed", "reported"]
    objects = ["a new approach", "the hidden pattern", "an elegant solution"]

    texts = []
    for _ in range(n_texts):
        parts = []
        while len(" ".join(parts)) < seq_len * 3:
            if rng.random() < 0.3:
                a, b = rng.randint(1, 999), rng.randint(1, 999)
                parts.append(f"{a} plus {b} equals {a + b}.")
            elif rng.random() < 0.5:
                s, v, o = rng.choice(subjects), rng.choice(verbs), rng.choice(objects)
                parts.append(f"{s} {v} {o}.")
            else:
                parts.append("the " * rng.randint(4, 12))
        texts.append(" ".join(parts))
    return texts


# ---------------------------------------------------------------------------
# Modal functions
# ---------------------------------------------------------------------------


@app.function(
    gpu="T4",
    timeout=600,
    volumes={"/root/data": vol},
    secrets=[hf_secret],
)
def run_layer_step(layer: int, step: int, n_tokens: int = 1000):
    """Compute geometry metrics for a single (layer, step) pair."""
    import json
    from pathlib import Path

    metrics = compute_layer_step_metrics(layer=layer, step=step, n_tokens=n_tokens)

    output_path = Path(OUTPUT_BASE)
    output_path.mkdir(parents=True, exist_ok=True)
    out_file = output_path / f"L{layer}_step_{step:07d}.json"
    with open(out_file, "w") as f:
        json.dump(metrics, f, indent=2)
    vol.commit()
    return metrics


@app.local_entrypoint()
def pilot(n_tokens: int = 1000):
    """Pilot: 3 layers × 9 steps = 27 jobs."""
    import json
    from pathlib import Path

    jobs = [(layer, step) for layer in PILOT_LAYERS for step in PILOT_STEPS]
    print(f"=== Multi-Layer PILOT ({len(jobs)} jobs: {len(PILOT_LAYERS)} layers × {len(PILOT_STEPS)} steps) ===")
    print(f"Layers: {PILOT_LAYERS}")
    print(f"Steps: {PILOT_STEPS}")

    results = list(
        run_layer_step.starmap(
            [(layer, step) for layer, step in jobs],
            kwargs={"n_tokens": n_tokens},
            order_outputs=False,
        )
    )

    output_dir = Path("research/geometry_analysis/outputs/pythia_multilayer")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Organize by layer
    by_layer = {}
    for r in results:
        layer = r["layer"]
        step = r["step"]
        by_layer.setdefault(layer, {})[step] = r

    with open(output_dir / "pilot_results.json", "w") as f:
        json.dump(by_layer, f, indent=2)

    print(f"\nPilot complete. {len(results)} results saved.")
    _print_summary(results)
    return by_layer


@app.local_entrypoint()
def full_run(n_tokens: int = 1000):
    """Full run: 6 layers × 20 steps = 120 jobs."""
    import json
    from pathlib import Path

    jobs = [(layer, step) for layer in LAYERS for step in FULL_STEPS]
    print(f"=== Multi-Layer FULL RUN ({len(jobs)} jobs: {len(LAYERS)} layers × {len(FULL_STEPS)} steps) ===")
    print(f"Layers: {LAYERS}")
    print(f"Steps: {FULL_STEPS}")
    print("NOTE: ~120 GPU-hours on T4.")

    results = list(
        run_layer_step.starmap(
            [(layer, step) for layer, step in jobs],
            kwargs={"n_tokens": n_tokens},
            order_outputs=False,
        )
    )

    output_dir = Path("research/geometry_analysis/outputs/pythia_multilayer")
    output_dir.mkdir(parents=True, exist_ok=True)

    by_layer = {}
    for r in results:
        layer = r["layer"]
        step = r["step"]
        by_layer.setdefault(layer, {})[step] = r

    with open(output_dir / "full_results.json", "w") as f:
        json.dump(by_layer, f, indent=2)

    print(f"\nFull run complete. {len(results)} results.")
    _print_summary(results)
    return by_layer


def _print_summary(results: list):
    """Print summary table grouped by layer."""
    import numpy as np

    by_layer = {}
    for r in results:
        by_layer.setdefault(r["layer"], []).append(r)

    for layer in sorted(by_layer.keys()):
        print(f"\n{'=' * 80}")
        print(f"LAYER {layer}")
        print(f"{'=' * 80}")
        print(f"{'step':>8}  {'var_exp':>8}  {'l0':>7}  {'dead':>6}  "
              f"{'id_2nn':>7}  {'convex':>7}  {'linear':>7}")
        print("-" * 70)
        for r in sorted(by_layer[layer], key=lambda x: x["step"]):
            ve = r["sae_quality"]["var_explained"]
            l0 = r["feature_stats"]["l0_mean"]
            nd = r["feature_stats"]["n_dead_features"]
            idd = r["intrinsic_dimension"]["two_nn"]
            cv = r["feature_geometry"]["mean_convexity"]
            ln = r["feature_geometry"]["mean_boundary_linearity"]
            print(f"{r['step']:>8}  {ve:>8.4f}  {l0:>7.1f}  {nd:>6}  "
                  f"{idd:>7.1f}  {cv:>7.3f}  {ln:>7.3f}")

    # Cross-layer comparison: when does var_explained first go positive?
    print(f"\n{'=' * 80}")
    print("CROSS-LAYER: First positive var_explained")
    print(f"{'=' * 80}")
    for layer in sorted(by_layer.keys()):
        layer_results = sorted(by_layer[layer], key=lambda x: x["step"])
        first_positive = None
        for r in layer_results:
            if r["sae_quality"]["var_explained"] > 0:
                first_positive = r["step"]
                break
        if first_positive:
            print(f"  Layer {layer}: step {first_positive} ({100*first_positive/143000:.1f}% of training)")
        else:
            print(f"  Layer {layer}: never positive in sampled steps")
