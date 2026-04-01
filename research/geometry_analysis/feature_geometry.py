"""SAE feature activation region geometry analysis.

Characterizes the geometric structure of SAE feature activation regions:
- Are they convex (half-spaces, as predicted by ReLU theory)?
- What is their codimension?
- How do they intersect?
- Is the overall structure a hyperplane arrangement?

Key theoretical prediction: ReLU SAE features define half-spaces
    S_k = {x : w_k · x - b_k > 0}
The activation space is partitioned into convex polytopes by the
arrangement of hyperplanes H_k = {x : w_k · x = b_k}. Each polytope
corresponds to a unique binary sparsity pattern (which features are on).
"""

import numpy as np
from dataclasses import dataclass, field
from scipy.spatial import ConvexHull
from scipy.spatial.distance import cdist


@dataclass
class FeatureRegionGeometry:
    """Geometric properties of a single SAE feature's activation region."""
    feature_id: int
    n_active: int
    n_total: int
    activation_rate: float
    # Convexity: ratio of points inside convex hull of active set
    convexity_score: float  # 1.0 = perfectly convex
    # Codimension: ambient dim - intrinsic dim of the boundary
    codimension: float
    # Angular concentration: how tightly clustered is the active region?
    angular_spread: float  # std of angles from centroid direction
    # Linearity of the boundary
    boundary_linearity: float  # 1.0 = perfectly linear boundary (hyperplane)
    metadata: dict = field(default_factory=dict)


@dataclass
class IntersectionGeometry:
    """Geometry of the intersection of two feature activation regions."""
    feature_a: int
    feature_b: int
    n_both_active: int
    n_either_active: int
    jaccard: float  # intersection over union
    # Does the intersection follow independence?
    independence_ratio: float  # observed / expected under independence
    # Angle between feature directions
    direction_angle: float  # radians
    # Is the intersection convex?
    intersection_convexity: float


def analyze_feature_regions(
    X: np.ndarray,
    feature_acts: np.ndarray,
    sae_W: np.ndarray | None = None,
    top_k: int = 30,
    min_active: int = 20,
) -> list[FeatureRegionGeometry]:
    """Analyze geometric properties of SAE feature activation regions.

    For each of the top-k most frequently active features:
    1. Test convexity of the active region
    2. Estimate codimension of the boundary
    3. Measure angular concentration
    4. Test boundary linearity (is it a hyperplane?)

    Args:
        X: (N, D) activation vectors (raw or PCA-reduced)
        feature_acts: (N, n_features) SAE feature activations
        sae_W: (n_features, D) SAE encoder weight matrix (optional)
        top_k: number of features to analyze
        min_active: minimum active tokens to analyze a feature
    """
    N, D = X.shape
    n_features = feature_acts.shape[1]

    # Select top-k features by activation frequency
    active_counts = (feature_acts > 0).sum(axis=0)
    eligible = np.where(active_counts >= min_active)[0]
    sorted_eligible = eligible[np.argsort(active_counts[eligible])[::-1]]
    selected = sorted_eligible[:top_k]

    results = []
    for feat_id in selected:
        mask = feature_acts[:, feat_id] > 0
        X_active = X[mask]
        X_inactive = X[~mask]
        n_active = mask.sum()

        # 1. Convexity test via linear separability
        # If the active region is a half-space (convex), a linear classifier
        # should achieve near-perfect accuracy
        convexity = _test_convexity(X, mask)

        # 2. Codimension estimation
        # The boundary S_k ∩ ∂S_k should have codimension 1 if it's a hyperplane
        codim = _estimate_codimension(X, feature_acts[:, feat_id])

        # 3. Angular spread
        centroid = X_active.mean(axis=0)
        centered = X_active - centroid
        norms = np.linalg.norm(centered, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-10)
        directions = centered / norms
        # Mean direction
        mean_dir = directions.mean(axis=0)
        mean_dir_norm = np.linalg.norm(mean_dir)
        if mean_dir_norm > 0:
            mean_dir /= mean_dir_norm
            # Angular spread: std of cosine similarities to mean direction
            cosines = directions @ mean_dir
            angular_spread = float(np.std(cosines))
        else:
            angular_spread = 1.0

        # 4. Boundary linearity
        boundary_lin = _boundary_linearity(X, feature_acts[:, feat_id], sae_W, feat_id)

        results.append(FeatureRegionGeometry(
            feature_id=int(feat_id),
            n_active=int(n_active),
            n_total=N,
            activation_rate=float(n_active / N),
            convexity_score=convexity,
            codimension=codim,
            angular_spread=angular_spread,
            boundary_linearity=boundary_lin,
        ))

    return results


def _test_convexity(X: np.ndarray, mask: np.ndarray) -> float:
    """Test if a region is convex via linear separability.

    A convex region can be perfectly separated from its complement by a
    hyperplane. We train a linear SVM and report accuracy as a proxy for
    convexity. Score near 1.0 = region is a half-space (convex).
    """
    from sklearn.svm import LinearSVC
    from sklearn.model_selection import cross_val_score

    n_active = mask.sum()
    n_inactive = (~mask).sum()

    if n_active < 10 or n_inactive < 10:
        return float("nan")

    # Subsample for speed if needed
    max_n = 500
    if len(X) > max_n:
        rng = np.random.RandomState(42)
        # Stratified subsample
        active_idx = np.where(mask)[0]
        inactive_idx = np.where(~mask)[0]
        n_a = min(max_n // 2, len(active_idx))
        n_i = min(max_n // 2, len(inactive_idx))
        idx = np.concatenate([
            rng.choice(active_idx, n_a, replace=False),
            rng.choice(inactive_idx, n_i, replace=False),
        ])
        X_sub = X[idx]
        y_sub = mask[idx].astype(int)
    else:
        X_sub = X
        y_sub = mask.astype(int)

    clf = LinearSVC(max_iter=1000, dual="auto")
    try:
        scores = cross_val_score(clf, X_sub, y_sub, cv=3, scoring="accuracy")
        return float(scores.mean())
    except Exception:
        return float("nan")


def _estimate_codimension(X: np.ndarray, feature_vals: np.ndarray) -> float:
    """Estimate the codimension of the feature activation boundary.

    The boundary is where feature activation transitions from 0 to >0.
    We find points near this boundary and estimate the local dimension
    of the boundary set, then compute codimension = ambient_dim - boundary_dim.

    For a hyperplane boundary, codimension should be ~1.
    """
    D = X.shape[1]

    # Find boundary points: active but with small activation
    active = feature_vals > 0
    if active.sum() < 20 or (~active).sum() < 20:
        return float("nan")

    # Boundary: points in the 10th percentile of positive activations
    positive_vals = feature_vals[active]
    threshold = np.percentile(positive_vals, 15)
    near_boundary = active & (feature_vals < threshold)

    n_boundary = near_boundary.sum()
    if n_boundary < 15:
        return float("nan")

    X_boundary = X[near_boundary]

    # Local PCA on boundary points
    centered = X_boundary - X_boundary.mean(axis=0)
    _, s, _ = np.linalg.svd(centered, full_matrices=False)
    eigenvalues = s ** 2 / (n_boundary - 1)

    # Participation ratio for boundary dimension
    total = eigenvalues.sum()
    if total == 0:
        return float("nan")
    boundary_dim = total ** 2 / (eigenvalues ** 2).sum()

    return float(D - boundary_dim)


def _boundary_linearity(
    X: np.ndarray,
    feature_vals: np.ndarray,
    sae_W: np.ndarray | None,
    feat_id: int,
) -> float:
    """Test whether the feature boundary is a hyperplane.

    If the SAE encoder weight is available, the theoretical boundary is
    w_k · x = b_k (a hyperplane). We test how well this matches the
    empirical boundary.

    Without SAE weights: train a linear classifier on active/inactive
    and measure how well the decision boundary fits.
    """
    active = feature_vals > 0
    if active.sum() < 10 or (~active).sum() < 10:
        return float("nan")

    from sklearn.svm import LinearSVC
    from sklearn.metrics import accuracy_score

    # Subsample
    max_n = 500
    if len(X) > max_n:
        rng = np.random.RandomState(42)
        active_idx = np.where(active)[0]
        inactive_idx = np.where(~active)[0]
        n_a = min(max_n // 2, len(active_idx))
        n_i = min(max_n // 2, len(inactive_idx))
        idx = np.concatenate([
            rng.choice(active_idx, n_a, replace=False),
            rng.choice(inactive_idx, n_i, replace=False),
        ])
        X_sub = X[idx]
        y_sub = active[idx].astype(int)
    else:
        X_sub = X
        y_sub = active.astype(int)

    clf = LinearSVC(max_iter=2000, dual="auto")
    try:
        clf.fit(X_sub, y_sub)
        acc = accuracy_score(y_sub, clf.predict(X_sub))
        return float(acc)
    except Exception:
        return float("nan")


def analyze_intersections(
    X: np.ndarray,
    feature_acts: np.ndarray,
    sae_W: np.ndarray | None = None,
    top_k: int = 20,
    min_active: int = 20,
) -> list[IntersectionGeometry]:
    """Analyze how SAE feature activation regions intersect.

    For pairs of top-k features, characterize:
    1. Intersection size vs independence expectation
    2. Angle between feature directions
    3. Convexity of the intersection

    Key prediction: if features are arranged as a hyperplane arrangement,
    intersections should be approximately independent (each hyperplane
    cuts independently), and intersection regions should be convex.
    """
    N = X.shape[0]
    n_features = feature_acts.shape[1]

    # Select top-k features
    active_counts = (feature_acts > 0).sum(axis=0)
    eligible = np.where(active_counts >= min_active)[0]
    sorted_eligible = eligible[np.argsort(active_counts[eligible])[::-1]]
    selected = sorted_eligible[:top_k]

    results = []
    for i, feat_a in enumerate(selected):
        mask_a = feature_acts[:, feat_a] > 0
        p_a = mask_a.sum() / N

        for feat_b in selected[i + 1:]:
            mask_b = feature_acts[:, feat_b] > 0
            p_b = mask_b.sum() / N

            both = mask_a & mask_b
            either = mask_a | mask_b
            n_both = both.sum()
            n_either = either.sum()

            jaccard = n_both / n_either if n_either > 0 else 0

            # Independence test
            expected = p_a * p_b * N
            independence_ratio = n_both / expected if expected > 0 else float("inf")

            # Angle between feature directions
            if sae_W is not None:
                w_a = sae_W[feat_a]
                w_b = sae_W[feat_b]
                cos_angle = np.dot(w_a, w_b) / (
                    np.linalg.norm(w_a) * np.linalg.norm(w_b) + 1e-10
                )
                angle = float(np.arccos(np.clip(cos_angle, -1, 1)))
            else:
                # Estimate from data: direction of max activation difference
                angle = _estimate_direction_angle(X, feature_acts, feat_a, feat_b)

            # Intersection convexity
            if n_both >= 20:
                int_convexity = _test_convexity(X, both)
            else:
                int_convexity = float("nan")

            results.append(IntersectionGeometry(
                feature_a=int(feat_a),
                feature_b=int(feat_b),
                n_both_active=int(n_both),
                n_either_active=int(n_either),
                jaccard=float(jaccard),
                independence_ratio=float(independence_ratio),
                direction_angle=angle,
                intersection_convexity=int_convexity,
            ))

    return results


def _estimate_direction_angle(
    X: np.ndarray,
    feature_acts: np.ndarray,
    feat_a: int,
    feat_b: int,
) -> float:
    """Estimate angle between feature directions from data.

    Uses the normal vectors of the best-fit separating hyperplanes
    for each feature's active/inactive partition.
    """
    from sklearn.svm import LinearSVC

    def _get_normal(feat_id):
        mask = feature_acts[:, feat_id] > 0
        if mask.sum() < 10 or (~mask).sum() < 10:
            return None
        y = mask.astype(int)
        # Subsample
        max_n = 300
        if len(X) > max_n:
            rng = np.random.RandomState(42)
            idx = rng.choice(len(X), max_n, replace=False)
            X_s, y_s = X[idx], y[idx]
        else:
            X_s, y_s = X, y
        clf = LinearSVC(max_iter=1000, dual="auto")
        try:
            clf.fit(X_s, y_s)
            return clf.coef_[0]
        except Exception:
            return None

    w_a = _get_normal(feat_a)
    w_b = _get_normal(feat_b)
    if w_a is None or w_b is None:
        return float("nan")

    cos_angle = np.dot(w_a, w_b) / (np.linalg.norm(w_a) * np.linalg.norm(w_b) + 1e-10)
    return float(np.arccos(np.clip(cos_angle, -1, 1)))


def sparsity_pattern_analysis(
    feature_acts: np.ndarray,
    top_k: int = 50,
    min_active: int = 10,
) -> dict:
    """Analyze the binary sparsity pattern structure.

    In a hyperplane arrangement of n hyperplanes in R^d, the number of
    regions is at most C(n,0) + C(n,1) + ... + C(n,d). If the number
    of observed sparsity patterns is much less than 2^k (for k active
    features), it suggests the arrangement has special structure
    (features are not in general position).

    Returns statistics about the sparsity pattern distribution.
    """
    N, n_features = feature_acts.shape

    # Select top-k features
    active_counts = (feature_acts > 0).sum(axis=0)
    eligible = np.where(active_counts >= min_active)[0]
    sorted_eligible = eligible[np.argsort(active_counts[eligible])[::-1]]
    selected = sorted_eligible[:top_k]

    # Binary activation patterns for selected features
    binary = (feature_acts[:, selected] > 0).astype(np.uint8)

    # Count unique patterns
    # Convert each row to a hashable tuple
    patterns = set(map(tuple, binary))
    n_patterns = len(patterns)

    # Pattern frequency distribution
    pattern_strs = [binary[i].tobytes() for i in range(N)]
    from collections import Counter
    pattern_counts = Counter(pattern_strs)
    freq_dist = sorted(pattern_counts.values(), reverse=True)

    # Theoretical maximum for k hyperplanes in d dimensions
    d = feature_acts.shape[1]  # not ambient dim, but doesn't matter for the bound
    k = len(selected)

    # Features per token statistics
    features_per_token = (feature_acts[:, selected] > 0).sum(axis=1)

    # Co-activation matrix
    coact = binary.T @ binary / N  # (k, k) co-activation probability

    return {
        "n_features_analyzed": k,
        "n_tokens": N,
        "n_unique_patterns": n_patterns,
        "max_possible_patterns": 2 ** k,
        "pattern_compression": n_patterns / (2 ** k) if k < 30 else float("nan"),
        "top_10_pattern_frequencies": freq_dist[:10],
        "features_per_token_mean": float(features_per_token.mean()),
        "features_per_token_std": float(features_per_token.std()),
        "features_per_token_median": float(np.median(features_per_token)),
        "coactivation_density": float((coact > 0.01).sum() / (k * k)),
        "coactivation_matrix": coact.tolist(),
    }
