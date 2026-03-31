"""Pipeline configuration."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PipelineConfig:
    # Model
    model_name: str = "gpt2"
    layer: int = 6
    hook_point: str = "blocks.6.hook_resid_post"
    activation_dim: int = 768  # GPT-2 Small hidden dim

    # Sampling
    n_tokens_per_condition: int = 2000
    pca_dim: int | None = 100  # None = skip PCA, use raw activations
    dim_reduction: str = "pca"  # "pca", "umap", "diffusion", or "none"
    umap_n_components: int = 50  # UMAP output dim (if dim_reduction="umap")
    umap_n_neighbors: int = 30   # UMAP neighborhood size
    batch_size: int = 64
    max_seq_len: int = 128

    # SMCE
    smce_alpha: float = 0.05
    smce_max_iter: int = 2000
    max_k_manifolds: int = 15

    # Topology
    homology_dimensions: list[int] = field(default_factory=lambda: [0, 1, 2])
    max_ph_points: int = 500  # subsample for persistent homology (O(N^3))

    # Scoring
    n_permutations: int = 1000
    top_k_variation: int = 3

    # Diffusion maps
    diffusion_alpha: float = 1.0  # density normalization exponent
    diffusion_n_components: int = 5
    diffusion_epsilon: str = "auto"  # or float for manual bandwidth

    # Conditions
    conditions: list[str] = field(default_factory=lambda: [
        "positional",
        "numeric",
        "syntactic",
    ])

    # Paths
    output_dir: Path = Path("research/manifold_pipeline/outputs")
    cache_dir: Path = Path("research/manifold_pipeline/outputs/cache")

    # Reproducibility
    random_seed: int = 42

    def __post_init__(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def gpt2(cls, **overrides) -> "PipelineConfig":
        """GPT-2 Small (117M) — baseline model."""
        defaults = dict(
            model_name="gpt2",
            layer=6,
            hook_point="blocks.6.hook_resid_post",
            activation_dim=768,
        )
        defaults.update(overrides)
        return cls(**defaults)

    @classmethod
    def gemma2_2b(cls, layer: int = 13, **overrides) -> "PipelineConfig":
        """Gemma 2 2B (2.6B) — primary model with Gemma Scope SAEs.

        Default layer 13 (mid-network of 26 layers). Gemma Scope provides
        SAEs at all layers for direct comparison.
        """
        defaults = dict(
            model_name="google/gemma-2-2b",
            layer=layer,
            hook_point=f"blocks.{layer}.hook_resid_post",
            activation_dim=2304,  # Gemma 2 2B hidden dim
            batch_size=16,  # smaller batches for larger model
            max_seq_len=128,
        )
        defaults.update(overrides)
        return cls(**defaults)
