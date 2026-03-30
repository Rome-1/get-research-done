# Phase 1 Methodology Critique: MI Token Classifiers as a Go/Kill Gate

**Reviewer:** nitro (independent review, dispatched by alice)
**Date:** 2026-03-30
**Verdict:** Phase 1 gate is **too easy to pass** and does not discriminate between "manifolds are functional routing structures" and "any clustering of activations picks up trivial token properties." The PROCEED decision is premature without a naive-clustering baseline.

---

## 1. The Headline Result (token_frequency MI=0.35) Is Likely a Trivial Artifact

**The problem:** The positional condition generates text by repeating one of 8 tokens (`["the", "a", "an", "one", "is", "was", "and", "but"]`, cycled via `i % 8`). Each generated text is a single token repeated ~64 times. After tokenization and activation extraction, the 2000 tokens in this condition come from ~8 distinct token IDs appearing at roughly equal but not identical counts (due to BOS tokens, whitespace tokenization artifacts, and unequal sequence counts per token type).

`classify_token_frequency` (`token_attribution.py:62-73`) computes *within-sample* frequency: it counts how often each token ID appears in the 2000-token sample, then quantile-buckets those counts. In the positional condition, this is essentially a **token identity classifier** — tokens that appear 280 times vs 230 times get different frequency buckets, and tokens with the same ID always get the same bucket.

Meanwhile, SMCE will trivially separate tokens with different IDs because they have different embeddings (only positional encoding varies within a token-ID cluster). The MI=0.35 between manifold assignment and token_frequency is measuring: **"does SMCE separate tokens with different embeddings?"** The answer is obviously yes. This is not evidence of functional routing.

**Test:** Compute MI(token_id, manifold_assignment) directly for the positional condition. If MI(token_id) ≈ MI(token_frequency), the frequency result is just a proxy for token identity.

---

## 2. The Permutation Null Is Necessary but Not Sufficient

The permutation test (`token_attribution.py:135-158`) shuffles manifold labels, destroying all structure. This answers: **"Is there any statistical dependence between manifold assignment and token type?"**

But the actual question for the go/kill gate should be: **"Does SMCE's manifold decomposition capture more token-type structure than a naive clustering method?"**

The permutation null is the *floor*. Any non-degenerate clustering of high-dimensional activations will exceed it, because:
- Tokens with similar embeddings have similar activations (trivial geometry)
- K-means on raw activations will also separate frequent from rare tokens, punctuation from content, BOS from non-BOS
- Even random subspace projections followed by threshold cuts will produce non-zero MI with token properties

**What the null should be:** MI under k-means clustering with the same k, on the same PCA-reduced activations. If MI(SMCE) ≈ MI(k-means), SMCE isn't adding value — any partition of activation space picks up these signals. This comparison is absent from the codebase.

---

## 3. Several Classifiers Measure Properties Trivially Correlated with Activation Geometry

The 5 token-type classifiers are presented as testing "functional routing," but several of them test properties that ANY clustering of transformer activations will pick up:

| Classifier | What it actually tests | Why it's trivial |
|---|---|---|
| `bos_vs_content` | Position 0-1 vs. rest | BOS activations are universally distinctive in transformers. The residual stream at position 0 encodes the start-of-sequence signal. Any partitioning of activations will separate BOS. |
| `punctuation` | Punct vs whitespace vs content | Punctuation tokens have a different embedding distribution. K-means would also separate them. |
| `token_frequency` (positional) | Token identity (see §1) | Confounded by condition design. |
| `position_bucket` | Coarse position | Positional encodings are additive to the residual stream. Early vs. late positions have systematically different activation norms. |

Only `is_number` (for numeric condition) tests something non-trivial: that the model routes number tokens to specific manifolds rather than just clustering them by embedding similarity. But MI=0.04 is a small effect, and even this could arise from embedding-space separation of digit tokens.

**The key classifier that's missing:** Something that requires knowing what the *model is doing* with the token, not just what the token *is*. For example:
- **Attention pattern type:** Does the token attend primarily to local context, to BOS, or to distant tokens?
- **Logit entropy:** Is the model confident or uncertain at this position?
- **Circuit membership:** Is this token part of a known GPT-2 circuit (induction heads, IOI, etc.)?

These would test whether manifolds correspond to computational pathways, not just input properties.

---

## 4. The Go/Kill Gate Criterion Is Too Permissive

The gate passes if **at least one condition × one token type** shows significant MI at p<0.01. With 14 tests (some near-guaranteed to be significant, see §3), this criterion has essentially zero false-negative rate. It cannot falsify the manifold hypothesis in practice.

**Consider what would be needed to KILL:** Every single one of the 14 tests would need p≥0.01. Given that BOS/content separation alone is trivially significant in any transformer activation clustering, this is nearly impossible. The gate is not a meaningful filter.

A more discriminative gate would require:
1. **MI(SMCE) > MI(k-means)** for at least one non-trivial classifier (§2)
2. **Effect size threshold:** Not just p<0.01, but MI > some minimum (e.g., MI > 0.05) after correcting for the number of categories
3. **Normalized MI (NMI):** Raw MI values are incomparable across classifiers with different numbers of categories. NMI ∈ [0,1] would allow meaningful comparison

---

## 5. Missing Baselines: K-Means, Random Subspaces, GMM

The single most important missing experiment: **run the same MI analysis with k-means clustering on the PCA activations, using the same k as SMCE found.**

```python
from sklearn.cluster import KMeans
kmeans_labels = KMeans(n_clusters=k, random_state=42).fit_predict(pca_activations)
# Then compute MI(kmeans_labels, token_type_labels) for each classifier
```

If k-means MI values are comparable to SMCE MI values, the conclusion changes from "manifolds are functional routing structures" to "any activation clustering picks up trivial token properties."

Additional baselines worth running:
- **Random subspace projection:** Project to k random directions, threshold-cluster. If MI is still significant, the test is vacuous.
- **GMM:** Gaussian mixture model with k components. Tests whether the structure is Gaussian-separable (trivial geometry) vs. requiring manifold-aware decomposition.
- **Shuffled-condition control:** Run SMCE on activations where token IDs and positions are shuffled across conditions. If MI persists, the signal is in the activations, not in the condition-specific manifold structure.

---

## 6. The Positional Condition Design Creates Confounds

The positional condition (`_positional_texts`) generates text like `"the the the the..."` using 8 tokens cycled via `i % 8`. This creates several confounds:

1. **Token identity IS frequency:** Within each text, only one token ID appears (plus whitespace/BOS artifacts). Across the 2000-token sample, the 8 token types appear at slightly different rates. Token frequency is not an independent property from token identity.

2. **Sequence homogeneity removes within-sequence variation.** Each sequence has ~64 copies of the same token. Any clustering method will group tokens by sequence (= by token ID), because within-sequence variance is tiny (only positional encoding varies) while between-sequence variance is large (different embeddings).

3. **The condition was designed to isolate positional encoding**, but in practice it isolates *token identity with positional variation*. A better positional condition would use a single token repeated (e.g., only "the"), so all 2000 tokens have the same embedding and only positional encoding varies.

---

## 7. Specific Recommendations

### Must-do before relying on Phase 1 gate:

1. **Add k-means baseline.** Run `compute_token_attribution` with k-means labels replacing SMCE manifold labels. Report MI(SMCE) - MI(k-means) for each classifier. If the difference is not significant, SMCE is not adding value.

2. **Add NMI.** Replace or supplement raw MI with normalized mutual information. This makes values comparable across classifiers and correctable for chance.

3. **Fix positional condition.** Use a single repeated token (e.g., only "the") so token_frequency is not confounded with token identity. Or at minimum, report MI(token_id, manifold) alongside MI(token_frequency, manifold) to quantify the confound.

4. **Add a non-trivial classifier.** Compute attention entropy, logit entropy, or layer-to-layer activation change per token. Test MI between manifold assignment and a property that reflects what the model is *computing*, not what the input *is*.

### Nice-to-have:

5. **Tighten the gate criterion.** Require MI(SMCE) > MI(k-means) + δ for at least one classifier, rather than just MI(SMCE) > permutation null.

6. **Report effect sizes.** Cohen's d or similar for MI_observed vs MI_null, not just p-values. With 2000 tokens and 1000 permutations, p=0.000 tells us nothing about practical significance.

7. **Multiple comparison correction.** 14 tests at p<0.01 each → expected ~0.14 false positives under the null. Not catastrophic, but Bonferroni or BH correction should be applied for rigor.

---

## Summary Verdict

Phase 1 demonstrates that SMCE manifold assignments are statistically associated with coarse token properties. This is **necessary but not sufficient** to claim manifolds are "functional routing structures." The association could arise from:

(a) Functional routing (the claim) — the model deliberately routes tokens to different computational pathways that happen to align with manifolds
(b) Trivial geometry — tokens with similar embeddings have similar activations, any clustering picks this up
(c) Condition design artifacts — the positional condition's 8-token structure creates a confound with token_frequency

**The Phase 1 gate cannot distinguish (a) from (b) or (c)** without a naive-clustering baseline. Adding k-means MI comparison would resolve this. Until then, the PROCEED decision should be treated as provisional, not as evidence for the manifold routing hypothesis.

The Phase 2 causal test (manifold-targeted ablation) is the right next step regardless — it would resolve the ambiguity. But the Phase 1 results should not be cited as "first evidence that discovered manifolds correspond to computational routing" (RESULTS.md line 154) without the baseline comparison.
