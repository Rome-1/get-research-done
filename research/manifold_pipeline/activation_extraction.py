"""Extract activations from GPT-2 Small via TransformerLens."""

import numpy as np
from dataclasses import dataclass
from pathlib import Path
from sklearn.decomposition import PCA

from .config import PipelineConfig


@dataclass
class ExtractionResult:
    """Activations with token metadata for attribution analysis."""
    activations: np.ndarray   # (N, pca_dim) PCA-reduced
    token_ids: np.ndarray     # (N,) vocab token ID per activation
    positions: np.ndarray     # (N,) sequence position per activation


# --- Condition text generators ---

def _positional_texts(n: int, seq_len: int) -> list[str]:
    """Single repeated token — isolates positional encoding.

    Uses only "the" to ensure all tokens have identical embeddings.
    Any manifold structure must come from positional encoding, not
    token identity. (Previous version cycled 8 tokens, confounding
    token_frequency with token_id.)
    """
    texts = []
    for _ in range(n):
        texts.append(("the " * (seq_len // 2)).strip())
    return texts


def _numeric_texts(n: int, seq_len: int) -> list[str]:
    """Number-heavy sequences — number representation features."""
    import random
    rng = random.Random(42)
    templates = [
        "The number {n} is {adj} than {m}.",
        "There are {n} items in the collection of {m} objects.",
        "{n} plus {m} equals {s}.",
        "The population of the city is {n} thousand people, up from {m}.",
        "In {n}, the company earned {m} million dollars.",
        "The temperature was {n} degrees, dropping to {m} by evening.",
    ]
    texts = []
    for _ in range(n):
        parts = []
        while len(" ".join(parts)) < seq_len * 3:
            t = rng.choice(templates)
            a, b = rng.randint(1, 9999), rng.randint(1, 9999)
            parts.append(t.format(
                n=a, m=b, s=a + b,
                adj=rng.choice(["greater", "less", "more", "fewer"])
            ))
        texts.append(" ".join(parts))
    return texts


def _syntactic_texts(n: int, seq_len: int) -> list[str]:
    """Varied syntactic structures — syntax features."""
    import random
    rng = random.Random(43)
    subjects = ["The cat", "A researcher", "My friend", "The system", "An artist",
                "The professor", "A student", "The engineer", "Our team", "The model"]
    verbs = ["discovered", "analyzed", "created", "observed", "transformed",
             "evaluated", "designed", "implemented", "studied", "proposed"]
    objects = ["a new approach", "the hidden pattern", "an elegant solution",
               "the underlying structure", "a novel framework", "the core mechanism",
               "an unexpected result", "the fundamental theory", "a complex system",
               "the missing component"]
    clauses = [
        "which had been overlooked for decades",
        "that nobody expected to find",
        "despite the initial skepticism",
        "after years of careful investigation",
        "while working on an unrelated problem",
        "that challenged existing assumptions",
    ]
    texts = []
    for _ in range(n):
        parts = []
        while len(" ".join(parts)) < seq_len * 3:
            s, v, o = rng.choice(subjects), rng.choice(verbs), rng.choice(objects)
            if rng.random() > 0.5:
                c = rng.choice(clauses)
                parts.append(f"{s} {v} {o}, {c}.")
            elif rng.random() > 0.5:
                parts.append(f"Did {s.lower()} really {v.replace('ed', '')} {o}?")
            else:
                parts.append(f"{s} {v} {o}.")
        texts.append(" ".join(parts))
    return texts


def _arithmetic_texts(n: int, seq_len: int) -> list[str]:
    """Arithmetic sequences with verifiable answers.

    Each sentence has a simple addition/subtraction with the correct answer.
    Used by Diagnostic C to test whether manifolds group by prediction
    accuracy (model gets it right vs wrong).
    """
    import random
    rng = random.Random(44)
    texts = []
    for _ in range(n):
        parts = []
        while len(" ".join(parts)) < seq_len * 3:
            a = rng.randint(1, 50)
            b = rng.randint(1, 50)
            if rng.random() > 0.5:
                parts.append(f"{a} plus {b} equals {a + b}.")
            else:
                big, small = max(a, b), min(a, b)
                parts.append(f"{big} minus {small} equals {big - small}.")
        texts.append(" ".join(parts))
    return texts


def _cloze_texts(n: int, seq_len: int) -> list[str]:
    """High-predictability cloze sentences.

    Common collocations and idioms where the final word is highly predictable.
    Used to test whether manifolds correspond to prediction confidence.
    """
    import random
    rng = random.Random(45)
    templates = [
        "The sun rises in the east and sets in the west.",
        "She opened the door and walked into the room.",
        "He picked up the phone and made a call.",
        "The cat sat on the mat and fell asleep.",
        "They went to the store to buy some food.",
        "The bird flew over the tree and landed on the ground.",
        "She turned on the light and read a book.",
        "The rain fell from the sky and hit the ground.",
        "He drank a glass of water and felt better.",
        "The dog barked at the mailman and wagged its tail.",
        "She wrote a letter and put it in the mailbox.",
        "The students took the test and passed with flying colors.",
        "He drove the car to the gas station and filled up the tank.",
        "The flowers bloomed in the spring and wilted in the fall.",
        "She cooked dinner and set the table for the family.",
    ]
    texts = []
    for _ in range(n):
        parts = []
        while len(" ".join(parts)) < seq_len * 3:
            parts.append(rng.choice(templates))
        texts.append(" ".join(parts))
    return texts


CONDITION_GENERATORS = {
    "positional": _positional_texts,
    "numeric": _numeric_texts,
    "syntactic": _syntactic_texts,
    "arithmetic": _arithmetic_texts,
    "cloze": _cloze_texts,
}


def generate_condition_texts(
    condition: str, n: int, seq_len: int = 128
) -> list[str]:
    """Generate text samples for a given condition."""
    gen = CONDITION_GENERATORS.get(condition)
    if gen is None:
        raise ValueError(f"Unknown condition: {condition}. "
                         f"Available: {list(CONDITION_GENERATORS.keys())}")
    return gen(n, seq_len)


def load_model(model_name: str = "gpt2"):
    """Load model via TransformerLens.

    Supports GPT-2 ('gpt2') and Gemma 2 ('google/gemma-2-2b').
    """
    import torch
    from transformer_lens import HookedTransformer

    dtype = torch.float32
    if "gemma" in model_name.lower():
        dtype = torch.bfloat16  # Gemma 2 expects bf16

    model = HookedTransformer.from_pretrained(
        model_name,
        dtype=dtype,
    )
    model.eval()
    return model


def extract_activations(
    model,
    texts: list[str],
    hook_point: str,
    max_seq_len: int = 128,
    batch_size: int = 64,
) -> np.ndarray:
    """Extract activations from a specific hook point.

    Returns array of shape (total_tokens, hidden_dim) — one activation
    vector per token position across all texts.
    """
    import torch

    all_activations = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        tokens = model.to_tokens(batch, prepend_bos=True)
        if tokens.shape[1] > max_seq_len:
            tokens = tokens[:, :max_seq_len]

        with torch.no_grad():
            _, cache = model.run_with_cache(tokens, names_filter=[hook_point])

        # cache[hook_point] shape: (batch, seq_len, hidden_dim)
        acts = cache[hook_point].cpu().float().numpy()
        # Flatten batch and seq dimensions
        acts = acts.reshape(-1, acts.shape[-1])
        all_activations.append(acts)

    return np.concatenate(all_activations, axis=0)


def extract_activations_with_tokens(
    model,
    texts: list[str],
    hook_point: str,
    max_seq_len: int = 128,
    batch_size: int = 64,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Extract activations with token metadata.

    Returns:
        activations: (total_tokens, hidden_dim)
        token_ids: (total_tokens,) vocab ID per token
        positions: (total_tokens,) sequence position per token
    """
    import torch

    all_activations = []
    all_token_ids = []
    all_positions = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        tokens = model.to_tokens(batch, prepend_bos=True)
        if tokens.shape[1] > max_seq_len:
            tokens = tokens[:, :max_seq_len]

        batch_size_actual, seq_len = tokens.shape

        with torch.no_grad():
            _, cache = model.run_with_cache(tokens, names_filter=[hook_point])

        acts = cache[hook_point].cpu().float().numpy()
        acts = acts.reshape(-1, acts.shape[-1])
        all_activations.append(acts)

        # Token IDs: flatten (batch, seq_len) -> (batch * seq_len,)
        all_token_ids.append(tokens.cpu().numpy().reshape(-1))

        # Positions: [0, 1, ..., seq_len-1] repeated per batch item
        pos = np.tile(np.arange(seq_len), batch_size_actual)
        all_positions.append(pos)

    return (
        np.concatenate(all_activations, axis=0),
        np.concatenate(all_token_ids, axis=0),
        np.concatenate(all_positions, axis=0),
    )


def _apply_dim_reduction(
    all_raw: list[np.ndarray],
    config: "PipelineConfig",
) -> list[np.ndarray]:
    """Apply dimensionality reduction to raw activation arrays.

    Supports: "pca", "umap", "diffusion", "none".
    Fits on combined data across all conditions (shared coordinate space).

    Returns list of reduced arrays in same order as all_raw.
    """
    method = getattr(config, "dim_reduction", "pca")
    # Legacy: if dim_reduction not set, infer from pca_dim
    if method == "pca" and getattr(config, "pca_dim", None) is None:
        method = "none"

    combined = np.concatenate(all_raw, axis=0)
    sizes = [r.shape[0] for r in all_raw]

    if method == "pca":
        target_dim = config.pca_dim
        print(f"Fitting PCA: {combined.shape} -> {target_dim} components")
        pca = PCA(n_components=target_dim, random_state=config.random_seed)
        pca.fit(combined)
        print(f"  Explained variance: {pca.explained_variance_ratio_.sum():.3f}")
        reduced_all = pca.transform(combined)

    elif method == "umap":
        try:
            import umap
        except ImportError:
            raise ImportError("UMAP not installed. Add 'umap-learn' to pip dependencies.")
        n_components = getattr(config, "umap_n_components", 50)
        n_neighbors = getattr(config, "umap_n_neighbors", 30)
        print(f"Fitting UMAP: {combined.shape} -> {n_components} components "
              f"(n_neighbors={n_neighbors})")
        reducer = umap.UMAP(
            n_components=n_components,
            n_neighbors=n_neighbors,
            random_state=config.random_seed,
            verbose=False,
        )
        reduced_all = reducer.fit_transform(combined)
        print(f"  UMAP complete: {reduced_all.shape}")

    elif method == "diffusion":
        print(f"Fitting diffusion maps: {combined.shape} -> {config.diffusion_n_components} components")
        reduced_all = _diffusion_map_reduce(combined, config)
        print(f"  Diffusion maps complete: {reduced_all.shape}")

    elif method == "none":
        print(f"No dim reduction — using raw {combined.shape[1]}-dim activations")
        reduced_all = combined

    else:
        raise ValueError(f"Unknown dim_reduction method: {method!r}. "
                         f"Choose from: pca, umap, diffusion, none")

    # Split back into per-condition arrays
    result = []
    offset = 0
    for size in sizes:
        result.append(reduced_all[offset:offset + size])
        offset += size
    return result


def _diffusion_map_reduce(X: np.ndarray, config: "PipelineConfig") -> np.ndarray:
    """Compute diffusion map coordinates for dimensionality reduction.

    Uses a Gaussian kernel with automatic bandwidth (median heuristic).
    Returns top-k diffusion coordinates (excluding trivial constant component).
    """
    from scipy.spatial.distance import cdist

    N = X.shape[0]
    n_components = config.diffusion_n_components

    # Subsample if too large (diffusion maps are O(N²))
    max_pts = 2000
    if N > max_pts:
        print(f"  Subsampling {N} -> {max_pts} for diffusion map kernel")
        rng = np.random.RandomState(config.random_seed)
        idx = rng.choice(N, max_pts, replace=False)
        X_sub = X[idx]
    else:
        X_sub = X
        idx = None

    # Pairwise distances
    dists = cdist(X_sub, X_sub, metric="euclidean")

    # Bandwidth: median heuristic
    epsilon = np.median(dists) ** 2
    print(f"  Diffusion map bandwidth epsilon={epsilon:.2f}")

    # Gaussian kernel
    K = np.exp(-dists ** 2 / epsilon)

    # Normalize (Markov normalization)
    D = K.sum(axis=1)
    M = K / (D[:, None] * D[None, :])

    # Symmetric normalization for eigendecomposition
    D_sqrt_inv = 1.0 / np.sqrt(M.sum(axis=1))
    M_sym = M * D_sqrt_inv[:, None] * D_sqrt_inv[None, :]

    # Top eigenvectors
    from scipy.linalg import eigh
    eigenvalues, eigenvectors = eigh(M_sym, subset_by_index=[N - n_components - 1, N - 2])
    # Sort descending
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]

    # Diffusion coordinates = eigenvectors scaled by eigenvalues
    coords_sub = eigenvectors * eigenvalues[None, :]

    if idx is not None:
        # Nystrom extension: embed remaining points
        dists_full = cdist(X, X_sub, metric="euclidean")
        K_full = np.exp(-dists_full ** 2 / epsilon)
        D_full = K_full.sum(axis=1)
        K_norm = K_full / D_full[:, None]
        coords = K_norm @ coords_sub / eigenvalues[None, :]
    else:
        coords = coords_sub

    return coords.astype(np.float32)


def extract_and_reduce(
    config: PipelineConfig,
    model=None,
) -> dict[str, np.ndarray]:
    """Extract activations for all conditions, PCA reduce, and cache.

    Returns dict mapping condition name to (N, pca_dim) arrays.
    """
    cache_path = config.cache_dir / "activations.npz"
    if cache_path.exists():
        print(f"Loading cached activations from {cache_path}")
        data = np.load(cache_path)
        return {k: data[k] for k in data.files}

    if model is None:
        model = load_model(config.model_name)

    results = {}
    all_raw = []

    # Extract raw activations
    for condition in config.conditions:
        print(f"Extracting activations for condition: {condition}")
        n_texts = max(config.n_tokens_per_condition // (config.max_seq_len // 2), 20)
        texts = generate_condition_texts(condition, n_texts, config.max_seq_len)
        acts = extract_activations(
            model, texts, config.hook_point,
            config.max_seq_len, config.batch_size,
        )
        # Subsample to target token count
        if acts.shape[0] > config.n_tokens_per_condition:
            rng = np.random.RandomState(config.random_seed)
            idx = rng.choice(acts.shape[0], config.n_tokens_per_condition, replace=False)
            acts = acts[idx]
        all_raw.append(acts)
        print(f"  {condition}: {acts.shape[0]} tokens, dim={acts.shape[1]}")

    # Dimensionality reduction
    reduced_per_condition = _apply_dim_reduction(all_raw, config)
    for condition, reduced in zip(config.conditions, reduced_per_condition):
        results[condition] = reduced

    # Cache
    np.savez(cache_path, **results)
    print(f"Cached activations to {cache_path}")

    return results


def extract_and_reduce_with_tokens(
    config: PipelineConfig,
    model=None,
) -> dict[str, ExtractionResult]:
    """Extract activations with token metadata, PCA reduce, and cache.

    Returns dict mapping condition name to ExtractionResult with
    (activations, token_ids, positions) all aligned.
    """
    cache_path = config.cache_dir / "activations_with_tokens.npz"
    if cache_path.exists():
        print(f"Loading cached activations+tokens from {cache_path}")
        data = np.load(cache_path)
        results = {}
        for cond in config.conditions:
            results[cond] = ExtractionResult(
                activations=data[f"{cond}_acts"],
                token_ids=data[f"{cond}_token_ids"],
                positions=data[f"{cond}_positions"],
            )
        return results

    if model is None:
        model = load_model(config.model_name)

    all_raw = []
    all_tids = []
    all_pos = []

    for condition in config.conditions:
        print(f"Extracting activations+tokens for condition: {condition}")
        n_texts = max(config.n_tokens_per_condition // (config.max_seq_len // 2), 20)
        texts = generate_condition_texts(condition, n_texts, config.max_seq_len)
        acts, tids, pos = extract_activations_with_tokens(
            model, texts, config.hook_point,
            config.max_seq_len, config.batch_size,
        )
        # Subsample to target token count (preserving alignment)
        if acts.shape[0] > config.n_tokens_per_condition:
            rng = np.random.RandomState(config.random_seed)
            idx = rng.choice(acts.shape[0], config.n_tokens_per_condition, replace=False)
            acts = acts[idx]
            tids = tids[idx]
            pos = pos[idx]
        all_raw.append(acts)
        all_tids.append(tids)
        all_pos.append(pos)
        print(f"  {condition}: {acts.shape[0]} tokens, dim={acts.shape[1]}")

    # Dimensionality reduction (PCA / UMAP / diffusion maps / none)
    reduced_per_condition = _apply_dim_reduction(all_raw, config)

    results = {}
    cache_arrays = {}
    for condition, reduced, tids, pos in zip(
        config.conditions, reduced_per_condition, all_tids, all_pos
    ):
        results[condition] = ExtractionResult(
            activations=reduced, token_ids=tids, positions=pos,
        )
        cache_arrays[f"{condition}_acts"] = reduced
        cache_arrays[f"{condition}_token_ids"] = tids
        cache_arrays[f"{condition}_positions"] = pos

    np.savez(cache_path, **cache_arrays)
    print(f"Cached activations+tokens to {cache_path}")

    return results
