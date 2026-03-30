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
    """Repeated token sequences — positional encoding should dominate."""
    texts = []
    tokens = ["the", "a", "an", "one", "is", "was", "and", "but"]
    for i in range(n):
        tok = tokens[i % len(tokens)]
        texts.append((tok + " ") * (seq_len // 2))
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


CONDITION_GENERATORS = {
    "positional": _positional_texts,
    "numeric": _numeric_texts,
    "syntactic": _syntactic_texts,
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
    """Load GPT-2 Small via TransformerLens."""
    from transformer_lens import HookedTransformer
    model = HookedTransformer.from_pretrained(model_name)
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
        acts = cache[hook_point].cpu().numpy()
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

        acts = cache[hook_point].cpu().numpy()
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

    # Fit PCA on all conditions jointly (shared coordinate system)
    combined = np.concatenate(all_raw, axis=0)
    print(f"Fitting PCA: {combined.shape} -> {config.pca_dim} components")
    pca = PCA(n_components=config.pca_dim, random_state=config.random_seed)
    pca.fit(combined)
    print(f"  Explained variance: {pca.explained_variance_ratio_.sum():.3f}")

    # Transform each condition
    offset = 0
    for condition, raw in zip(config.conditions, all_raw):
        results[condition] = pca.transform(raw)
        offset += raw.shape[0]

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

    # Fit PCA on all conditions jointly
    combined = np.concatenate(all_raw, axis=0)
    print(f"Fitting PCA: {combined.shape} -> {config.pca_dim} components")
    pca = PCA(n_components=config.pca_dim, random_state=config.random_seed)
    pca.fit(combined)
    print(f"  Explained variance: {pca.explained_variance_ratio_.sum():.3f}")

    # Transform and build results
    results = {}
    cache_arrays = {}
    for condition, raw, tids, pos in zip(config.conditions, all_raw, all_tids, all_pos):
        reduced = pca.transform(raw)
        results[condition] = ExtractionResult(
            activations=reduced,
            token_ids=tids,
            positions=pos,
        )
        cache_arrays[f"{condition}_acts"] = reduced
        cache_arrays[f"{condition}_token_ids"] = tids
        cache_arrays[f"{condition}_positions"] = pos

    np.savez(cache_path, **cache_arrays)
    print(f"Cached activations+tokens to {cache_path}")

    return results
