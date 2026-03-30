"""Synthetic ground-truth tests for the manifold pipeline.

These MUST pass before running on real GPT-2 data.
Tests use known manifold structures where the expected output is unambiguous.
"""

import numpy as np
import pytest
from pathlib import Path


@pytest.fixture
def output_dir(tmp_path):
    return tmp_path / "test_outputs"


# --- Stage 1: SMCE tests ---

class TestSMCEDecomposition:
    """Test SMCE on synthetic manifolds with known structure."""

    def _embed_in_high_dim(self, X_2d, D=100, seed=42):
        """Embed 2D data in R^D via random projection + noise."""
        rng = np.random.RandomState(seed)
        proj = rng.randn(2, D) * 0.3
        noise = rng.randn(X_2d.shape[0], D) * 0.01
        return X_2d @ proj + noise

    def test_two_moons_finds_k2(self):
        """Two moons dataset should yield k=2 manifolds."""
        from sklearn.datasets import make_moons
        from research.manifold_pipeline.stage1_decompose import decompose

        X, _ = make_moons(n_samples=300, noise=0.05, random_state=42)
        X_hd = self._embed_in_high_dim(X)

        result = decompose(X_hd, alpha=0.05, max_k=10)
        assert result.k == 2, f"Expected k=2 for two moons, got k={result.k}"

    def test_three_blobs_finds_k3(self):
        """Three well-separated blobs should yield k=3."""
        from sklearn.datasets import make_blobs
        from research.manifold_pipeline.stage1_decompose import decompose

        X, _ = make_blobs(n_samples=300, centers=3, n_features=2,
                          cluster_std=0.5, random_state=42)
        X_hd = self._embed_in_high_dim(X)

        result = decompose(X_hd, alpha=0.05, max_k=10)
        assert 2 <= result.k <= 4, f"Expected k≈3 for three blobs, got k={result.k}"

    def test_affinity_matrix_properties(self):
        """Affinity matrix W should be symmetric and non-negative."""
        from sklearn.datasets import make_moons
        from research.manifold_pipeline.stage1_decompose import smce

        X, _ = make_moons(n_samples=100, noise=0.05, random_state=42)
        X_hd = self._embed_in_high_dim(X)

        W = smce(X_hd, alpha=0.05)

        assert W.shape == (100, 100)
        assert np.allclose(W, W.T), "Affinity matrix should be symmetric"
        assert np.all(W >= 0), "Affinity matrix should be non-negative"
        assert np.all(np.diag(W) == 0), "Diagonal should be zero"


# --- Stage 2: Topology tests ---

class TestTopology:
    """Test persistent homology on known topological structures."""

    def test_circle_has_beta1(self):
        """A circle should have β₁ ≥ 1 (one 1-cycle)."""
        from research.manifold_pipeline.topology import compute_persistence

        theta = np.linspace(0, 2 * np.pi, 200, endpoint=False)
        circle = np.column_stack([np.cos(theta), np.sin(theta)])
        # Add small noise
        circle += np.random.RandomState(42).randn(*circle.shape) * 0.02

        result = compute_persistence(circle, max_dim=2, max_points=200)
        assert result.betti[1] >= 1, \
            f"Circle should have β₁≥1, got β={result.betti}"

    def test_two_clusters_beta0(self):
        """Two separated clusters should have β₀ = 2."""
        from research.manifold_pipeline.topology import compute_persistence

        c1 = np.random.RandomState(42).randn(100, 2)
        c2 = np.random.RandomState(43).randn(100, 2) + [10, 10]
        points = np.concatenate([c1, c2])

        result = compute_persistence(points, max_dim=1, max_points=200)
        assert result.betti[0] >= 2, \
            f"Two clusters should have β₀≥2, got β₀={result.betti[0]}"


# --- Stage 2: Matching tests ---

class TestMatching:
    """Test manifold matching on known correspondences."""

    def test_self_matching_identity(self):
        """Matching a condition with itself should give identity permutation."""
        from research.manifold_pipeline.stage2_match import (
            compute_manifold_descriptor, match_manifolds,
        )

        rng = np.random.RandomState(42)
        # Create two "manifolds" with distinct properties
        m1_points = rng.randn(100, 10) * [3, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        m2_points = rng.randn(100, 10) * [1, 1, 1, 1, 1, 1, 1, 1, 1, 1] + 5

        desc_a = [
            compute_manifold_descriptor(m1_points, "test", 0),
            compute_manifold_descriptor(m2_points, "test", 1),
        ]
        # Same descriptors as "another condition"
        desc_b = [
            compute_manifold_descriptor(m1_points, "test2", 0),
            compute_manifold_descriptor(m2_points, "test2", 1),
        ]

        matches = match_manifolds(desc_a, desc_b)
        # Should match M0↔M0, M1↔M1
        match_map = {m.manifold_a: m.manifold_b for m in matches}
        assert match_map[0] == 0, f"Expected M0↔M0, got M0↔M{match_map[0]}"
        assert match_map[1] == 1, f"Expected M1↔M1, got M1↔M{match_map[1]}"


# --- Stage 3: Scoring tests ---

class TestScoring:
    """Test variation scoring on known cases."""

    def test_identical_manifolds_low_variation(self):
        """Two identical point clouds should have near-zero geometric variation."""
        from research.manifold_pipeline.stage2_match import compute_manifold_descriptor
        from research.manifold_pipeline.stage3_score import geometric_variation

        rng = np.random.RandomState(42)
        points = rng.randn(100, 10)

        desc_a = compute_manifold_descriptor(points, "a", 0)
        desc_b = compute_manifold_descriptor(points, "b", 0)

        v = geometric_variation(desc_a, desc_b)
        assert v < 0.01, f"Identical manifolds should have V_geom≈0, got {v:.4f}"

    def test_different_manifolds_high_variation(self):
        """Very different point clouds should have high geometric variation."""
        from research.manifold_pipeline.stage2_match import compute_manifold_descriptor
        from research.manifold_pipeline.stage3_score import geometric_variation

        rng = np.random.RandomState(42)
        # One elongated, one spherical
        points_a = rng.randn(100, 10) * [10, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        points_b = rng.randn(100, 10) * [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]

        desc_a = compute_manifold_descriptor(points_a, "a", 0)
        desc_b = compute_manifold_descriptor(points_b, "b", 0)

        v = geometric_variation(desc_a, desc_b)
        assert v > 0.1, f"Different manifolds should have V_geom>0.1, got {v:.4f}"


# --- Stage 4: Diffusion map tests ---

class TestDiffusionMap:
    """Test diffusion map on known structures."""

    def test_circle_embedding(self):
        """Diffusion map of a circle should give periodic coordinates."""
        from research.manifold_pipeline.stage4_characterize import diffusion_map

        theta = np.linspace(0, 2 * np.pi, 200, endpoint=False)
        circle = np.column_stack([np.cos(theta), np.sin(theta)])

        result = diffusion_map(circle, n_components=3, alpha=1.0)

        assert result.coordinates.shape == (200, 3)
        # First eigenvalue should be close to 1 (Markov matrix)
        assert result.eigenvalues[0] > 0.9, \
            f"First eigenvalue should be ~1, got {result.eigenvalues[0]:.4f}"
        # Coordinates should be non-degenerate
        coord_range = result.coordinates[:, 0].max() - result.coordinates[:, 0].min()
        assert coord_range > 0.01, "Diffusion coordinates should be non-degenerate"

    def test_density_independence(self):
        """Alpha=1 should give similar embeddings for uniform vs non-uniform sampling."""
        from research.manifold_pipeline.stage4_characterize import diffusion_map

        # Uniform sampling of line segment
        x_uniform = np.linspace(0, 1, 200)[:, np.newaxis]
        x_uniform = np.hstack([x_uniform, np.zeros((200, 1))])

        # Non-uniform sampling (more points near 0)
        rng = np.random.RandomState(42)
        x_nonuniform = rng.beta(0.5, 2, size=200)[:, np.newaxis]
        x_nonuniform = np.hstack([x_nonuniform, np.zeros((200, 1))])

        dm_uniform = diffusion_map(x_uniform, n_components=2, alpha=1.0)
        dm_nonuniform = diffusion_map(x_nonuniform, n_components=2, alpha=1.0)

        # Both should have similar eigenvalue structure
        # (density independence means geometry, not density, determines spectrum)
        ratio = dm_uniform.eigenvalues[1] / (dm_nonuniform.eigenvalues[1] + 1e-10)
        # They won't be identical (different point sets) but should be same order
        assert 0.1 < ratio < 10, \
            f"Eigenvalue ratio should be O(1) with alpha=1, got {ratio:.4f}"


# --- Integration test ---

class TestIntegration:
    """End-to-end pipeline test on synthetic data."""

    def test_full_pipeline_synthetic(self, output_dir):
        """Full pipeline on synthetic data should complete without error."""
        from research.manifold_pipeline.config import PipelineConfig
        from research.manifold_pipeline.run_pipeline import run_synthetic

        output_dir.mkdir(parents=True, exist_ok=True)

        config = PipelineConfig(
            n_tokens_per_condition=200,  # small for speed
            pca_dim=20,
            smce_alpha=0.1,
            max_k_manifolds=8,
            n_permutations=50,  # small for speed
            max_ph_points=100,
            output_dir=output_dir,
            cache_dir=output_dir / "cache",
        )

        results = run_synthetic(config)

        assert "manifold_counts" in results
        assert len(results["manifold_counts"]) == 3  # three conditions
        assert results["total_time_seconds"] > 0

        # Check that outputs were generated
        assert (output_dir / "results.json").exists()
        assert (output_dir / "summary_report.png").exists()


# --- Stage 5: Token Attribution tests ---

class TestTokenAttribution:
    """Test token-manifold attribution on synthetic data with known labels."""

    def _make_synthetic_metadata(self, n_tokens, condition="test"):
        """Create synthetic TokenMetadata for testing."""
        from research.manifold_pipeline.activation_extraction import TokenMetadata

        # Simulate two groups of tokens: function words and content words
        function_words = ["the", " the", "a", " a", "is", " is", "and", " and"]
        content_words = ["cat", " cat", "dog", " dog", "tree", " tree", "run", " run"]
        all_words = function_words + content_words

        rng = np.random.RandomState(42)
        token_ids = rng.randint(0, 50000, size=n_tokens)
        token_strings = [rng.choice(all_words) for _ in range(n_tokens)]
        positions = rng.randint(0, 128, size=n_tokens).astype(np.int32)
        text_indices = np.arange(n_tokens, dtype=np.int32) // 128

        return TokenMetadata(
            token_ids=token_ids.astype(np.int64),
            token_strings=token_strings,
            positions=positions,
            text_indices=text_indices,
            condition=condition,
        )

    def test_profile_manifold_tokens(self):
        """Token profiling should produce correct statistics."""
        from research.manifold_pipeline.token_attribution import profile_manifold_tokens

        meta = self._make_synthetic_metadata(200)
        mask = np.zeros(200, dtype=bool)
        mask[:100] = True  # first 100 tokens in manifold

        profile = profile_manifold_tokens("test", 0, meta, mask)

        assert profile.n_tokens == 100
        assert profile.condition == "test"
        assert profile.manifold_id == 0
        assert len(profile.top_tokens) > 0
        assert profile.token_entropy > 0  # multiple token types
        assert 0 < profile.uniqueness_ratio <= 1.0
        assert sum(c for _, c, _ in profile.top_tokens) <= 100

    def test_attribution_result_structure(self):
        """Full attribution should produce profiles for each manifold."""
        from research.manifold_pipeline.token_attribution import (
            attribute_tokens_to_manifolds,
        )
        from research.manifold_pipeline.stage1_decompose import DecompositionResult

        n = 200
        meta = self._make_synthetic_metadata(n, "cond_a")

        # Simulate decomposition with 3 manifolds
        labels = np.array([0] * 80 + [1] * 70 + [2] * 50)
        decomp = DecompositionResult(
            labels=labels,
            k=3,
            affinity=np.eye(n),
            eigenvalues=np.arange(20, dtype=float),
            local_dims=np.ones(n),
        )
        X = np.random.RandomState(42).randn(n, 10)

        result = attribute_tokens_to_manifolds(
            {"cond_a": (decomp, X)},
            {"cond_a": meta},
        )

        assert "cond_a" in result.condition_profiles
        profiles = result.condition_profiles["cond_a"]
        assert len(profiles) == 3
        assert profiles[0].n_tokens == 80
        assert profiles[1].n_tokens == 70
        assert profiles[2].n_tokens == 50

    def test_empty_manifold_skipped(self):
        """Manifolds with zero tokens should be skipped."""
        from research.manifold_pipeline.token_attribution import (
            attribute_tokens_to_manifolds,
        )
        from research.manifold_pipeline.stage1_decompose import DecompositionResult

        n = 100
        meta = self._make_synthetic_metadata(n)

        # k=3 but no tokens assigned to manifold 2
        labels = np.array([0] * 60 + [1] * 40)
        decomp = DecompositionResult(
            labels=labels, k=3,
            affinity=np.eye(n),
            eigenvalues=np.arange(20, dtype=float),
            local_dims=np.ones(n),
        )
        X = np.random.RandomState(42).randn(n, 10)

        result = attribute_tokens_to_manifolds(
            {"test": (decomp, X)}, {"test": meta},
        )
        profiles = result.condition_profiles["test"]
        assert len(profiles) == 2  # only M0 and M1

    def test_entropy_uniform_vs_concentrated(self):
        """Uniform token distribution should have higher entropy than concentrated."""
        from research.manifold_pipeline.token_attribution import _compute_entropy
        from collections import Counter

        # Concentrated: all same token
        concentrated = Counter({"the": 100})
        # Uniform: 10 tokens each appearing 10 times
        uniform = Counter({f"tok_{i}": 10 for i in range(10)})

        assert _compute_entropy(concentrated) == 0.0
        assert _compute_entropy(uniform) > _compute_entropy(concentrated)

    def test_metadata_subsampling_preserves_alignment(self):
        """Subsampling activations and metadata should keep them aligned."""
        from research.manifold_pipeline.activation_extraction import TokenMetadata

        n = 500
        rng = np.random.RandomState(42)
        token_ids = np.arange(n, dtype=np.int64)
        token_strings = [f"tok_{i}" for i in range(n)]
        positions = np.arange(n, dtype=np.int32) % 128
        text_indices = np.arange(n, dtype=np.int32) // 128

        meta = TokenMetadata(
            token_ids=token_ids,
            token_strings=token_strings,
            positions=positions,
            text_indices=text_indices,
            condition="test",
        )

        # Subsample like extract_and_reduce_with_tokens does
        target = 200
        idx = rng.choice(n, target, replace=False)
        idx.sort()

        sub_meta = TokenMetadata(
            token_ids=meta.token_ids[idx],
            token_strings=[meta.token_strings[i] for i in idx],
            positions=meta.positions[idx],
            text_indices=meta.text_indices[idx],
            condition="test",
        )

        assert len(sub_meta.token_strings) == target
        assert sub_meta.token_ids.shape == (target,)
        # Check alignment: token string should match original index
        for j, orig_idx in enumerate(idx):
            assert sub_meta.token_strings[j] == f"tok_{orig_idx}"
            assert sub_meta.token_ids[j] == orig_idx

    def test_format_report_runs(self):
        """Attribution report formatting should not error."""
        from research.manifold_pipeline.token_attribution import (
            attribute_tokens_to_manifolds,
            format_attribution_report,
        )
        from research.manifold_pipeline.stage1_decompose import DecompositionResult

        n = 100
        meta = self._make_synthetic_metadata(n)
        labels = np.array([0] * 50 + [1] * 50)
        decomp = DecompositionResult(
            labels=labels, k=2,
            affinity=np.eye(n),
            eigenvalues=np.arange(20, dtype=float),
            local_dims=np.ones(n),
        )
        X = np.random.RandomState(42).randn(n, 10)

        result = attribute_tokens_to_manifolds(
            {"test": (decomp, X)}, {"test": meta},
        )
        report = format_attribution_report(result)
        assert "TOKEN-MANIFOLD ATTRIBUTION REPORT" in report
        assert "test" in report
        assert "M0" in report


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
