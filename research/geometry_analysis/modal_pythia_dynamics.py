"""Modal pipeline: Pythia training dynamics — SAE hyperplane arrangement evolution.

Research question: Do phase transitions in the SAE hyperplane arrangement during
Pythia-70m training correspond to capability emergence events?

Approach:
  - Load Pythia-70m-deduped at each of 154 training checkpoints
  - Apply the final SAE (pythia-70m-deduped-res-sm, layer 3 resid_post) as a fixed probe
  - Compute geometric metrics at each checkpoint:
      * SAE reconstruction quality (variance explained)
      * Feature activation sparsity and rates
      * Convexity of feature activation regions
      * Boundary linearity (hyperplane structure)
      * Intrinsic dimension of activation space
  - Detect phase transitions (discontinuous jumps in metrics)

Usage:
    # Discover: list checkpoints and verify SAE loads (no GPU needed)
    modal run research/geometry_analysis/modal_pythia_dynamics.py::app.discover

    # Pilot: run 10 sampled checkpoints on T4
    modal run research/geometry_analysis/modal_pythia_dynamics.py::app.pilot

    # Full run: all 154 checkpoints in parallel
    modal run research/geometry_analysis/modal_pythia_dynamics.py::app.full_run

    # Download results
    modal volume get research /geometry-analysis/pythia-dynamics/ ./research/geometry_analysis/outputs/
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

app = modal.App("pythia-dynamics", image=image)
vol = modal.Volume.from_name("research")
hf_secret = modal.Secret.from_name("hf_token")

# ---------------------------------------------------------------------------
# Pythia checkpoint schedule
# ---------------------------------------------------------------------------

# Pythia-70m has 154 checkpoints:
# Geometrically spaced early training: 0,1,2,4,8,16,32,64,128,256,512
# Then every 1000 from 1000 to 143000
EARLY_STEPS = [0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512]
LATE_STEPS = list(range(1000, 144000, 1000))
ALL_STEPS = EARLY_STEPS + LATE_STEPS  # 154 total

# Pilot subset: geometrically spaced + a few late steps
PILOT_STEPS = [0, 2, 8, 32, 128, 512, 2000, 8000, 32000, 64000, 143000]

MODEL_ID = "EleutherAI/pythia-70m-deduped"
SAE_RELEASE = "pythia-70m-deduped-res-sm"
SAE_ID = "blocks.3.hook_resid_post"  # Layer 3 residual stream post
HOOK_POINT = "blocks.3.hook_resid_post"
OUTPUT_BASE = "/root/data/geometry-analysis/pythia-dynamics"


# ---------------------------------------------------------------------------
# Core metric computation
# ---------------------------------------------------------------------------


def compute_checkpoint_metrics(
    step: int,
    n_tokens: int = 1000,
) -> dict:
    """Load Pythia at a checkpoint and compute geometric metrics."""
    import json
    import sys
    import time

    import numpy as np
    import torch
    from transformer_lens import HookedTransformer

    sys.path.insert(0, "/root")

    t0 = time.time()
    print(f"\n[step={step}] Starting...")

    # Load model at checkpoint
    revision = f"step{step}" if step > 0 else "step0"
    print(f"[step={step}] Loading model at revision={revision}...")
    model = HookedTransformer.from_pretrained(
        "pythia-70m-deduped",
        checkpoint_value=step,
        dtype=torch.float32,
    )
    model.eval()
    print(f"[step={step}] Model loaded ({time.time() - t0:.1f}s)")

    # Load SAE (only once, it's the same for all checkpoints)
    print(f"[step={step}] Loading SAE...")
    from sae_lens import SAE

    sae = SAE.from_pretrained(
        release=SAE_RELEASE,
        sae_id=SAE_ID,
        device="cpu",
    )
    sae.eval()
    n_features = sae.cfg.d_sae
    d_in = sae.cfg.d_in
    print(f"[step={step}] SAE loaded: {n_features} features, d_in={d_in}")

    # Extract encoder weights for direction analysis
    sae_W = sae.W_enc.detach().cpu().numpy()
    if sae_W.shape[0] == d_in:
        sae_W = sae_W.T  # Ensure (n_features, d_in)

    # -------------------------------------------------------------------
    # Generate activations
    # -------------------------------------------------------------------
    print(f"[step={step}] Extracting activations...")

    texts = _generate_texts(n_tokens)
    tokens = model.to_tokens(texts, prepend_bos=True)
    if tokens.shape[1] > 128:
        tokens = tokens[:, :128]

    with torch.no_grad():
        _, cache = model.run_with_cache(tokens, names_filter=[HOOK_POINT])

    acts_raw = cache[HOOK_POINT].cpu().float().numpy()
    acts_raw = acts_raw.reshape(-1, acts_raw.shape[-1])

    # Subsample
    if acts_raw.shape[0] > n_tokens:
        rng = np.random.RandomState(42)
        idx = rng.choice(acts_raw.shape[0], n_tokens, replace=False)
        acts_raw = acts_raw[idx]

    print(f"[step={step}] Activations: {acts_raw.shape}")

    # Free model memory
    del model, cache
    import gc
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # -------------------------------------------------------------------
    # Metric 1: SAE reconstruction quality
    # -------------------------------------------------------------------
    print(f"[step={step}] Computing SAE reconstruction metrics...")
    X = torch.from_numpy(acts_raw).float()
    with torch.no_grad():
        feature_acts = sae.encode(X).cpu().numpy()
        X_recon = sae.decode(torch.from_numpy(feature_acts)).cpu().numpy()

    # Variance explained
    ss_res = np.sum((acts_raw - X_recon) ** 2)
    ss_tot = np.sum((acts_raw - acts_raw.mean(0)) ** 2)
    var_explained = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    # MSE
    mse = float(np.mean((acts_raw - X_recon) ** 2))

    # -------------------------------------------------------------------
    # Metric 2: Feature activation statistics
    # -------------------------------------------------------------------
    active_mask = feature_acts > 0
    sparsity = float(active_mask.mean())  # fraction of (token, feature) pairs active
    active_per_token = active_mask.sum(axis=1).astype(float)
    l0_mean = float(active_per_token.mean())
    l0_std = float(active_per_token.std())

    # Feature activation rates (how often each feature fires)
    feature_rates = active_mask.mean(axis=0)  # (n_features,)
    n_dead = int((feature_rates == 0).sum())
    n_active_features = int((feature_rates > 0).sum())
    mean_rate = float(feature_rates[feature_rates > 0].mean()) if n_active_features > 0 else 0.0

    # -------------------------------------------------------------------
    # Metric 3: Geometry of activation space (intrinsic dimension)
    # -------------------------------------------------------------------
    print(f"[step={step}] Computing intrinsic dimension...")
    from sklearn.decomposition import PCA

    pca = PCA(n_components=50, random_state=42)
    acts_pca = pca.fit_transform(acts_raw)
    var_50 = float(pca.explained_variance_ratio_.sum())

    # Two-NN intrinsic dimension on PCA-reduced data
    try:
        from research.geometry_analysis.intrinsic_dimension import two_nn_dimension
        twonn = two_nn_dimension(acts_pca)
        intrinsic_dim = float(twonn.global_dim)
    except Exception as e:
        print(f"[step={step}] Two-NN failed: {e}")
        intrinsic_dim = float("nan")

    # -------------------------------------------------------------------
    # Metric 4: Feature region geometry (convexity, linearity)
    # on top-K active features
    # -------------------------------------------------------------------
    print(f"[step={step}] Computing feature region geometry...")
    try:
        from research.geometry_analysis.feature_geometry import analyze_feature_regions

        regions = analyze_feature_regions(
            acts_pca,
            feature_acts,
            sae_W=sae_W,
            top_k=20,
            min_active=15,
        )
        convexities = [r.convexity_score for r in regions
                       if not np.isnan(r.convexity_score)]
        linearities = [r.boundary_linearity for r in regions
                       if not np.isnan(r.boundary_linearity)]
        mean_convexity = float(np.mean(convexities)) if convexities else float("nan")
        mean_linearity = float(np.mean(linearities)) if linearities else float("nan")
        n_regions_analyzed = len(regions)
    except Exception as e:
        print(f"[step={step}] Feature geometry failed: {e}")
        mean_convexity = float("nan")
        mean_linearity = float("nan")
        n_regions_analyzed = 0

    # -------------------------------------------------------------------
    # Metric 5: Hyperplane direction spread
    # (angular std of encoder weight vectors for active features)
    # -------------------------------------------------------------------
    active_feature_idx = np.where(feature_rates > 0.01)[0]
    if len(active_feature_idx) > 1:
        W_active = sae_W[active_feature_idx]  # (k, d_in)
        norms = np.linalg.norm(W_active, axis=1, keepdims=True)
        W_norm = W_active / (norms + 1e-8)
        # Mean pairwise cosine similarity (measure of how clustered directions are)
        # Sample at most 200 features for speed
        if len(W_norm) > 200:
            rng = np.random.RandomState(42)
            idx = rng.choice(len(W_norm), 200, replace=False)
            W_sample = W_norm[idx]
        else:
            W_sample = W_norm
        cosine_sims = W_sample @ W_sample.T
        triu = cosine_sims[np.triu_indices(len(W_sample), k=1)]
        mean_cos_sim = float(np.mean(np.abs(triu)))
        direction_spread = float(np.std(np.abs(triu)))
    else:
        mean_cos_sim = float("nan")
        direction_spread = float("nan")

    elapsed = time.time() - t0
    print(f"[step={step}] Done in {elapsed:.1f}s")
    print(f"  var_explained={var_explained:.4f}, l0={l0_mean:.1f}, "
          f"n_dead={n_dead}, intrinsic_dim={intrinsic_dim:.1f}, "
          f"convexity={mean_convexity:.3f}, linearity={mean_linearity:.3f}")

    return {
        "step": step,
        "elapsed_s": elapsed,
        "n_tokens": acts_raw.shape[0],
        "sae_quality": {
            "var_explained": var_explained,
            "mse": mse,
        },
        "feature_stats": {
            "sparsity": sparsity,
            "l0_mean": l0_mean,
            "l0_std": l0_std,
            "n_dead_features": n_dead,
            "n_active_features": n_active_features,
            "mean_activation_rate": mean_rate,
        },
        "intrinsic_dimension": {
            "two_nn": intrinsic_dim,
            "pca_var_50": var_50,
        },
        "feature_geometry": {
            "mean_convexity": mean_convexity,
            "mean_boundary_linearity": mean_linearity,
            "n_regions_analyzed": n_regions_analyzed,
        },
        "encoder_directions": {
            "mean_abs_cosine_sim": mean_cos_sim,
            "cosine_sim_std": direction_spread,
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
                # Numeric
                a, b = rng.randint(1, 999), rng.randint(1, 999)
                parts.append(f"{a} plus {b} equals {a + b}.")
            elif rng.random() < 0.5:
                # Syntactic
                s, v, o = rng.choice(subjects), rng.choice(verbs), rng.choice(objects)
                parts.append(f"{s} {v} {o}.")
            else:
                # Positional
                parts.append("the " * rng.randint(4, 12))
        texts.append(" ".join(parts))
    return texts


# ---------------------------------------------------------------------------
# Modal functions
# ---------------------------------------------------------------------------


@app.function(
    timeout=300,
    volumes={"/root/data": vol},
    secrets=[hf_secret],
)
def discover():
    """Verify SAE loads and list checkpoint metadata. No GPU needed."""
    import json
    from pathlib import Path
    from sae_lens import SAE
    from sae_lens.loading.pretrained_saes_directory import get_pretrained_saes_directory

    print("=== Pythia Training Dynamics: Discovery ===\n")

    # Check SAE
    print(f"Loading SAE: {SAE_RELEASE} / {SAE_ID}")
    sae = SAE.from_pretrained(
        release=SAE_RELEASE, sae_id=SAE_ID, device="cpu"
    )
    print(f"  Architecture: {sae.cfg.architecture}")
    print(f"  d_sae (features): {sae.cfg.d_sae}")
    print(f"  d_in: {sae.cfg.d_in}")
    print(f"  dtype: {sae.cfg.dtype}")

    print(f"\nCheckpoint schedule:")
    print(f"  Early steps (geometric): {EARLY_STEPS}")
    print(f"  Late steps: {LATE_STEPS[0]}..{LATE_STEPS[-1]} (every 1000)")
    print(f"  Total: {len(ALL_STEPS)} checkpoints")
    print(f"\nPilot steps ({len(PILOT_STEPS)}): {PILOT_STEPS}")

    # Save manifest
    output_path = Path(OUTPUT_BASE)
    output_path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "model": MODEL_ID,
        "sae_release": SAE_RELEASE,
        "sae_id": SAE_ID,
        "hook_point": HOOK_POINT,
        "n_features": sae.cfg.d_sae,
        "d_in": sae.cfg.d_in,
        "all_steps": ALL_STEPS,
        "pilot_steps": PILOT_STEPS,
    }
    with open(output_path / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    vol.commit()
    print(f"\nManifest saved to {OUTPUT_BASE}/manifest.json")
    return manifest


@app.function(
    gpu="T4",
    timeout=3600,
    volumes={"/root/data": vol},
    secrets=[hf_secret],
)
def run_checkpoint(step: int, n_tokens: int = 1000):
    """Compute geometry metrics for a single Pythia checkpoint."""
    import json
    from pathlib import Path

    metrics = compute_checkpoint_metrics(step=step, n_tokens=n_tokens)

    output_path = Path(OUTPUT_BASE)
    output_path.mkdir(parents=True, exist_ok=True)
    out_file = output_path / f"step_{step:07d}.json"
    with open(out_file, "w") as f:
        json.dump(metrics, f, indent=2)
    vol.commit()
    print(f"Saved: {out_file}")
    return metrics


@app.local_entrypoint()
def pilot(n_tokens: int = 1000):
    """Run the pilot: 11 sampled checkpoints to validate the pipeline."""
    import json
    from pathlib import Path

    print(f"=== Pythia Dynamics PILOT ({len(PILOT_STEPS)} checkpoints) ===")
    print(f"Steps: {PILOT_STEPS}")
    print(f"n_tokens per checkpoint: {n_tokens}")
    print("\nSubmitting to Modal (parallel)...")

    results = list(
        run_checkpoint.map(
            PILOT_STEPS,
            kwargs={"n_tokens": n_tokens},
            order_outputs=False,
        )
    )

    # Aggregate and save locally
    output_dir = Path("research/geometry_analysis/outputs/pythia_dynamics")
    output_dir.mkdir(parents=True, exist_ok=True)

    results_by_step = {r["step"]: r for r in results}

    with open(output_dir / "pilot_results.json", "w") as f:
        json.dump(results_by_step, f, indent=2)

    print(f"\nPilot complete. Results saved to {output_dir / 'pilot_results.json'}")
    _print_pilot_summary(results)
    return results_by_step


@app.local_entrypoint()
def full_run(n_tokens: int = 1000):
    """Run all 154 checkpoints in parallel on Modal."""
    import json
    from pathlib import Path

    print(f"=== Pythia Dynamics FULL RUN ({len(ALL_STEPS)} checkpoints) ===")
    print("NOTE: This will use ~154 GPU-hours on T4. Confirm before running.")
    print("\nSubmitting to Modal (parallel)...")

    results = list(
        run_checkpoint.map(
            ALL_STEPS,
            kwargs={"n_tokens": n_tokens},
            order_outputs=False,
        )
    )

    output_dir = Path("research/geometry_analysis/outputs/pythia_dynamics")
    output_dir.mkdir(parents=True, exist_ok=True)
    results_by_step = {r["step"]: r for r in results}

    with open(output_dir / "full_results.json", "w") as f:
        json.dump(results_by_step, f, indent=2)

    print(f"\nFull run complete. {len(results)} checkpoints processed.")
    return results_by_step


def _print_pilot_summary(results: list):
    """Print a summary table of pilot results."""
    print("\n" + "=" * 80)
    print("PILOT SUMMARY")
    print("=" * 80)
    print(f"{'step':>10}  {'var_exp':>8}  {'l0':>6}  {'n_dead':>7}  "
          f"{'id_2nn':>7}  {'convex':>7}  {'linear':>7}")
    print("-" * 80)
    for r in sorted(results, key=lambda x: x["step"]):
        step = r["step"]
        ve = r["sae_quality"]["var_explained"]
        l0 = r["feature_stats"]["l0_mean"]
        nd = r["feature_stats"]["n_dead_features"]
        idd = r["intrinsic_dimension"]["two_nn"]
        cv = r["feature_geometry"]["mean_convexity"]
        ln = r["feature_geometry"]["mean_boundary_linearity"]
        print(f"{step:>10}  {ve:>8.4f}  {l0:>6.1f}  {nd:>7}  "
              f"{idd:>7.1f}  {cv:>7.3f}  {ln:>7.3f}")
    print("=" * 80)
