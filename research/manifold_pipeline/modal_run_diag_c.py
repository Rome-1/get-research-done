"""Diagnostic C: Computational classifiers — logit entropy, attention entropy, prediction accuracy.

Hypothesis: Token-type classifiers (is_number, position_bucket, etc.) are too
coarse to distinguish SMCE from k-means. Both methods find 'obvious' clusters.
Computational classifiers (what the model is DOING) should better distinguish
manifold structure from k-means.

Tests three new classifiers:
1. Logit entropy (model uncertainty) — manifolds group confident vs uncertain tokens
2. Attention entropy (focus vs distributed) — manifolds correspond to processing mode
3. Prediction accuracy (correct vs wrong) — manifolds route correctly-predicted tokens

Usage:
    modal run research/manifold_pipeline/modal_run_diag_c.py
"""

import modal

app = modal.App("manifold-diag-c")

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
def run_diag_c(n_tokens: int = 500):
    """Run Diagnostic C: computational classifiers on three text conditions.

    Runs on: arithmetic, cloze, and syntactic (syntactic as control).
    Uses both standard AND computational classifiers.
    """
    import sys
    sys.path.insert(0, "/root")

    import json
    import time
    import numpy as np
    from pathlib import Path

    from research.manifold_pipeline.config import PipelineConfig
    from research.manifold_pipeline.activation_extraction import (
        load_model, extract_activations_with_tokens,
        generate_condition_texts, ExtractionResult,
    )
    from research.manifold_pipeline.stage1_decompose import decompose
    from research.manifold_pipeline.token_attribution import (
        compute_token_attribution,
        run_phase1_gate,
        kmeans_baseline_labels,
    )
    from sklearn.decomposition import PCA

    output_dir = Path("/root/data/manifold-pipeline/diag-c")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use arithmetic + cloze + syntactic conditions
    conditions = ["arithmetic", "cloze", "syntactic"]

    config = PipelineConfig.gpt2(
        n_tokens_per_condition=n_tokens,
        conditions=conditions,
        output_dir=output_dir,
        cache_dir=output_dir / "cache",
    )

    model = load_model(config.model_name)
    tokenizer = model.tokenizer

    t0 = time.time()

    # --- Extract activations ---
    print("=" * 70)
    print("DIAGNOSTIC C — EXTRACTION")
    print("=" * 70)

    extraction_results = {}
    all_raw = []
    all_token_tensors = {}

    for condition in conditions:
        print(f"\nExtracting: {condition}")
        n_texts = max(n_tokens // (config.max_seq_len // 2), 20)
        texts = generate_condition_texts(condition, n_texts, config.max_seq_len)

        # Get raw activations + token metadata
        acts, tids, pos = extract_activations_with_tokens(
            model, texts, config.hook_point,
            config.max_seq_len, config.batch_size,
        )

        # Also get token tensors for computational classifiers
        import torch
        tokens = model.to_tokens(texts, prepend_bos=True)
        if tokens.shape[1] > config.max_seq_len:
            tokens = tokens[:, :config.max_seq_len]
        all_token_tensors[condition] = tokens

        # Subsample
        if acts.shape[0] > n_tokens:
            rng = np.random.RandomState(config.random_seed)
            idx = rng.choice(acts.shape[0], n_tokens, replace=False)
            acts = acts[idx]
            tids = tids[idx]
            pos = pos[idx]

        all_raw.append(acts)
        extraction_results[condition] = ExtractionResult(
            activations=None,  # will set after PCA
            token_ids=tids,
            positions=pos,
        )
        print(f"  {condition}: {acts.shape[0]} tokens, dim={acts.shape[1]}")

    # PCA reduce
    combined = np.concatenate(all_raw, axis=0)
    print(f"\nFitting PCA: {combined.shape} -> {config.pca_dim} components")
    pca = PCA(n_components=config.pca_dim, random_state=config.random_seed)
    pca.fit(combined)
    print(f"  Explained variance: {pca.explained_variance_ratio_.sum():.3f}")

    for condition, raw in zip(conditions, all_raw):
        extraction_results[condition].activations = pca.transform(raw)

    # --- Decompose (SMCE) ---
    print("\n" + "=" * 70)
    print("DIAGNOSTIC C — SMCE DECOMPOSITION")
    print("=" * 70)

    decompositions = {}
    for condition in conditions:
        X = extraction_results[condition].activations
        print(f"\nDecomposing {condition} ({X.shape[0]} points, dim={X.shape[1]})")
        decomp = decompose(
            X, alpha=config.smce_alpha,
            max_k=config.max_k_manifolds,
            max_iter=config.smce_max_iter,
        )
        decompositions[condition] = decomp

    # --- Attribution with computational classifiers ---
    print("\n" + "=" * 70)
    print("DIAGNOSTIC C — COMPUTATIONAL ATTRIBUTION")
    print("=" * 70)

    condition_attr_results = {}
    for condition in conditions:
        er = extraction_results[condition]
        decomp = decompositions[condition]
        tokens = all_token_tensors[condition]
        print(f"\nCondition: {condition} (k={decomp.k} manifolds)")

        attr_results = compute_token_attribution(
            manifold_labels=decomp.labels,
            token_ids=er.token_ids,
            positions=er.positions,
            tokenizer=tokenizer,
            activations=er.activations,
            n_permutations=config.n_permutations,
            seed=config.random_seed,
            model=model,
            tokens_tensor=tokens,
            layer=config.layer,
            include_computational=True,
        )
        condition_attr_results[condition] = attr_results

    phase1_result = run_phase1_gate(condition_attr_results)

    t1 = time.time()
    print(f"\nTotal time: {t1 - t0:.1f}s")

    # --- Build results ---
    print("\n" + "=" * 70)
    print("DIAGNOSTIC C — RESULTS")
    print("=" * 70)

    results = {
        "n_tokens": n_tokens,
        "conditions": conditions,
        "manifold_counts": {c: int(d.k) for c, d in decompositions.items()},
        "gate": {
            "proceed": phase1_result.proceed,
            "kill_reason": phase1_result.kill_reason,
        },
        "attribution": {},
        "computational_summary": {},
    }

    # Separate standard vs computational classifiers
    standard_types = {"is_number", "position_bucket", "token_frequency",
                      "bos_vs_content", "punctuation"}
    computational_types = {"logit_entropy", "attention_entropy", "prediction_correct"}

    for cond, attrs in condition_attr_results.items():
        results["attribution"][cond] = []
        for r in attrs:
            entry = {
                "token_type": r.token_type,
                "mi_smce": round(float(r.mi_observed), 6),
                "mi_kmeans": round(float(r.mi_kmeans), 6),
                "nmi_smce": round(float(r.nmi_observed), 4),
                "nmi_kmeans": round(float(r.nmi_kmeans), 4),
                "p_value": round(float(r.p_value), 4),
                "significant": bool(r.significant),
                "classifier_type": "computational" if r.token_type in computational_types else "standard",
            }
            results["attribution"][cond].append(entry)

            is_comp = "COMP" if r.token_type in computational_types else "STD"
            delta = ((r.mi_observed - r.mi_kmeans) / r.mi_kmeans * 100
                     if r.mi_kmeans > 0 else float("inf"))
            sig = "SMCE WINS" if r.significant else "parity"
            print(f"  [{is_comp}] {cond}/{r.token_type}: "
                  f"SMCE={r.mi_observed:.6f} km={r.mi_kmeans:.6f} "
                  f"({delta:+.1f}%) [{sig}]")

    # Summary: do computational classifiers show more SMCE advantage?
    std_wins = sum(
        1 for cond in conditions
        for r in condition_attr_results[cond]
        if r.significant and r.token_type in standard_types
    )
    comp_wins = sum(
        1 for cond in conditions
        for r in condition_attr_results[cond]
        if r.significant and r.token_type in computational_types
    )
    std_total = sum(
        1 for cond in conditions
        for r in condition_attr_results[cond]
        if r.token_type in standard_types
    )
    comp_total = sum(
        1 for cond in conditions
        for r in condition_attr_results[cond]
        if r.token_type in computational_types
    )

    results["computational_summary"] = {
        "standard_significant": f"{std_wins}/{std_total}",
        "computational_significant": f"{comp_wins}/{comp_total}",
    }

    print(f"\nStandard classifiers: {std_wins}/{std_total} significant")
    print(f"Computational classifiers: {comp_wins}/{comp_total} significant")

    if comp_wins > 0 and std_wins == 0:
        results["verdict"] = "COMPUTATIONAL_CLASSIFIERS_REVEAL_STRUCTURE"
        print(">>> Computational classifiers show SMCE advantage where standard don't!")
    elif comp_wins > std_wins:
        results["verdict"] = "COMPUTATIONAL_BETTER"
        print(">>> Computational classifiers show stronger SMCE advantage.")
    elif comp_wins == 0 and std_wins == 0:
        results["verdict"] = "NO_SMCE_ADVANTAGE"
        print(">>> Neither classifier type shows SMCE advantage.")
    else:
        results["verdict"] = "STANDARD_SUFFICIENT"
        print(">>> Standard classifiers already capture the signal.")

    # Save
    results_path = output_dir / "diag_c_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    vol.commit()
    return results


@app.local_entrypoint()
def main(n_tokens: int = 500):
    import json
    print(f"Running Diagnostic C (N={n_tokens}, conditions=[arithmetic, cloze, syntactic])...")
    result = run_diag_c.remote(n_tokens=n_tokens)
    print("\n" + "=" * 70)
    print("DIAGNOSTIC C RESULTS")
    print("=" * 70)
    print(json.dumps(result, indent=2))
