"""Extract activations from GPT-2 Small via TransformerLens."""

import numpy as np
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from sklearn.decomposition import PCA

from .config import PipelineConfig


@dataclass
class TokenMetadata:
    """Metadata for each token in the activation dataset.

    Each field is a parallel array of length N (one entry per activation vector).
    """
    token_ids: np.ndarray        # (N,) tokenizer token IDs
    token_strings: list[str]     # (N,) decoded token strings
    positions: np.ndarray        # (N,) position in sequence (0-indexed)
    text_indices: np.ndarray     # (N,) which source text generated this token
    condition: str               # condition name


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
    acts, _ = extract_activations_with_tokens(
        model, texts, hook_point, max_seq_len, batch_size, condition="unknown"
    )
    return acts


def extract_activations_with_tokens(
    model,
    texts: list[str],
    hook_point: str,
    max_seq_len: int = 128,
    batch_size: int = 64,
    condition: str = "unknown",
) -> tuple[np.ndarray, TokenMetadata]:
    """Extract activations and token metadata from a specific hook point.

    Returns:
        activations: (total_tokens, hidden_dim) array
        metadata: TokenMetadata with parallel arrays for each token
    """
    import torch

    all_activations = []
    all_token_ids = []
    all_token_strings = []
    all_positions = []
    all_text_indices = []

    tokenizer = model.tokenizer

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        tokens = model.to_tokens(batch, prepend_bos=True)
        if tokens.shape[1] > max_seq_len:
            tokens = tokens[:, :max_seq_len]

        with torch.no_grad():
            _, cache = model.run_with_cache(tokens, names_filter=[hook_point])

        # cache[hook_point] shape: (batch, seq_len, hidden_dim)
        acts = cache[hook_point].cpu().numpy()
        token_ids = tokens.cpu().numpy()  # (batch, seq_len)

        batch_sz, seq_len = token_ids.shape

        # Decode each token to its string representation
        for b in range(batch_sz):
            for s in range(seq_len):
                tid = int(token_ids[b, s])
                all_token_ids.append(tid)
                all_token_strings.append(tokenizer.decode([tid]))
                all_positions.append(s)
                all_text_indices.append(i + b)

        # Flatten batch and seq dimensions
        acts = acts.reshape(-1, acts.shape[-1])
        all_activations.append(acts)

    activations = np.concatenate(all_activations, axis=0)
    metadata = TokenMetadata(
        token_ids=np.array(all_token_ids, dtype=np.int64),
        token_strings=all_token_strings,
        positions=np.array(all_positions, dtype=np.int32),
        text_indices=np.array(all_text_indices, dtype=np.int32),
        condition=condition,
    )

    return activations, metadata


def extract_and_reduce(
    config: PipelineConfig,
    model=None,
) -> dict[str, np.ndarray]:
    """Extract activations for all conditions, PCA reduce, and cache.

    Returns dict mapping condition name to (N, pca_dim) arrays.
    """
    result, _ = extract_and_reduce_with_tokens(config, model)
    return result


def extract_and_reduce_with_tokens(
    config: PipelineConfig,
    model=None,
) -> tuple[dict[str, np.ndarray], dict[str, TokenMetadata]]:
    """Extract activations and token metadata, PCA reduce, and cache.

    Returns:
        activations: dict mapping condition name to (N, pca_dim) arrays
        token_metadata: dict mapping condition name to TokenMetadata
    """
    cache_path = config.cache_dir / "activations.npz"
    metadata_path = config.cache_dir / "token_metadata.pkl"

    if cache_path.exists() and metadata_path.exists():
        print(f"Loading cached activations from {cache_path}")
        data = np.load(cache_path)
        with open(metadata_path, "rb") as f:
            token_metadata = pickle.load(f)
        return {k: data[k] for k in data.files}, token_metadata

    if model is None:
        model = load_model(config.model_name)

    results = {}
    all_raw = []
    token_metadata = {}

    # Extract raw activations with token tracking
    for condition in config.conditions:
        print(f"Extracting activations for condition: {condition}")
        n_texts = max(config.n_tokens_per_condition // (config.max_seq_len // 2), 20)
        texts = generate_condition_texts(condition, n_texts, config.max_seq_len)
        acts, meta = extract_activations_with_tokens(
            model, texts, config.hook_point,
            config.max_seq_len, config.batch_size,
            condition=condition,
        )
        # Subsample to target token count
        if acts.shape[0] > config.n_tokens_per_condition:
            rng = np.random.RandomState(config.random_seed)
            idx = rng.choice(acts.shape[0], config.n_tokens_per_condition, replace=False)
            idx.sort()  # preserve order for interpretability
            acts = acts[idx]
            # Subsample metadata in parallel
            meta = TokenMetadata(
                token_ids=meta.token_ids[idx],
                token_strings=[meta.token_strings[i] for i in idx],
                positions=meta.positions[idx],
                text_indices=meta.text_indices[idx],
                condition=condition,
            )
        all_raw.append(acts)
        token_metadata[condition] = meta
        print(f"  {condition}: {acts.shape[0]} tokens, dim={acts.shape[1]}")

    # Fit PCA on all conditions jointly (shared coordinate system)
    combined = np.concatenate(all_raw, axis=0)
    print(f"Fitting PCA: {combined.shape} -> {config.pca_dim} components")
    pca = PCA(n_components=config.pca_dim, random_state=config.random_seed)
    pca.fit(combined)
    print(f"  Explained variance: {pca.explained_variance_ratio_.sum():.3f}")

    # Transform each condition
    for condition, raw in zip(config.conditions, all_raw):
        results[condition] = pca.transform(raw)

    # Cache
    np.savez(cache_path, **results)
    with open(metadata_path, "wb") as f:
        pickle.dump(token_metadata, f)
    print(f"Cached activations to {cache_path}")
    print(f"Cached token metadata to {metadata_path}")

    return results, token_metadata
