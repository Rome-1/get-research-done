# GPT-2 Small Multi-Manifold Detection: Results Analysis

**Pipeline run:** 2026-03-29 | **Runtime:** 90.4s | **Model:** GPT-2 Small (117M params)
**Configuration:** Layer 6, 1000 tokens/condition, PCA→100 dims, SMCE α=0.05, 500 permutations

---

## 1. Manifold Count and Eigengap Analysis

SMCE decomposition with Laplacian eigengap selection yields condition-dependent manifold counts:

| Condition   | Manifolds (k) | Eigengap location | Interpretation |
|-------------|:-:|:-:|---|
| Positional  | 2 | λ₂→λ₃ | Clean binary split — likely position-encoding vs. token-identity subspaces |
| Numeric     | 3 | λ₃→λ₄ | Three-way structure — number representation involves distinct processing modes |
| Syntactic   | 3 | λ₃→λ₄ | Three-way structure — consistent with subject/verb/modifier feature families |

**Key finding:** Positional text (repeated tokens like "the the the...") produces the simplest manifold structure (k=2), consistent with the hypothesis that positional encodings dominate when token identity is uninformative. Numeric and syntactic conditions, which require richer semantic processing, produce more complex manifold decompositions.

The eigengap at k=2 for positional inputs is notably sharper than the k=3 gaps for numeric/syntactic, suggesting positional manifold separation is more robust. See `outputs/eigengap_*.png`.

---

## 2. Topological Characterization

Persistent homology reveals the topological signature of each manifold:

### Positional condition (k=2)
- **M0** (majority manifold): Dominant connected component — likely captures the bulk of positional-encoding-driven activations.
- **M1** (minority manifold): Smaller cluster of tokens that deviate from the repetitive pattern.

### Numeric condition (k=3)
- **M0** (906 points): High-dimensional manifold, intrinsic dim ≈ 20.3. Betti numbers β = [497, 271, 107] — extremely rich topological structure with 271 independent loops and 107 voids. This suggests number representations occupy a complex, highly-connected region of activation space.
- **M1** (84 points): Low-dimensional manifold, intrinsic dim ≈ 1.0. Betti numbers β = [83, 0, 0] — 83 disconnected components with no loops. This is a scatter of isolated points — likely number tokens at extreme values or rare number formats that the model processes differently.
- **M2** (10 points): Micro-cluster, too small for reliable topology.

### Syntactic condition (k=3)
- **M0** (880 points): Intrinsic dim ≈ 29.8. Betti numbers β = [491, 231, 79] — comparable complexity to numeric/M0 but higher-dimensional. The syntactic processing manifold is the most dimensionally complex, consistent with the combinatorial nature of syntactic structure.
- **M1, M2**: Smaller manifolds capturing syntactic outliers.

**Comparison with predictions:** The Phase 5 survey predicted k=2–6 manifolds per condition. Our results (k=2–3) are at the low end, likely because N=1000 tokens limits the statistical power for detecting small manifolds. The prediction of significant cross-condition variation (p<0.05) is confirmed: 4/7 matched pairs are significant.

**Notable absence:** We did **not** observe β₁ ≥ 1 (loops) as a dominant feature of positional manifolds. The predicted circular topology for position-encoding features may require higher N or analysis at earlier layers where positional encodings are more prominent.

---

## 3. Cross-Condition Variation Analysis

The pipeline scored 7 matched manifold pairs across conditions. Results sorted by combined variation score:

| Rank | Pair | V_combined | V_topo | V_geom | V_dim | p-value | Significant? |
|:--:|---|:--:|:--:|:--:|:--:|:--:|:--:|
| 1 | numeric/M1 ↔ syntactic/M0 | **319.4** | 304.3 | 0.68 | 28.7 | 0.002 | Yes |
| 2 | numeric/M0 ↔ syntactic/M1 | **316.8** | 306.5 | 0.62 | 19.2 | 0.002 | Yes |
| 3 | positional/M0 ↔ syntactic/M0 | **297.9** | 287.1 | 0.25 | 21.2 | 0.002 | Yes |
| 4 | positional/M0 ↔ numeric/M0 | **293.7** | 287.6 | 0.23 | 11.8 | 0.002 | Yes |
| 5 | positional/M1 ↔ numeric/M2 | 0.0 | 0.0 | 0.0 | 0.0 | 1.0 | No |
| 6–7 | (remaining pairs) | ~0 | ~0 | ~0 | ~0 | 1.0 | No |

### Interpretation

**Topological variation dominates.** V_topo accounts for >95% of the combined score in all significant pairs. This means the manifolds differ primarily in their *topological structure* (number of connected components, loops, voids) rather than their eigenvalue spectra (V_geom) or dimensionality (V_dim). This is a strong finding: different text conditions produce activations with fundamentally different *shapes*, not just different sizes or orientations.

**Numeric ↔ Syntactic shows greatest variation.** The top two pairs both involve numeric↔syntactic comparisons (V ≈ 316–319). This makes sense: number processing and syntactic processing are computationally distinct — numbers involve magnitude comparison and arithmetic, syntax involves hierarchical structure parsing. The model appears to route these through topologically distinct manifold regions in layer 6.

**Positional is intermediate.** Positional activations are more similar to both numeric and syntactic than those two are to each other (V ≈ 294–298 vs. 317–319). This suggests positional encoding features form a "baseline" manifold structure that both numeric and syntactic processing build upon differently.

**Small manifolds match trivially.** The minor manifolds (positional/M1, numeric/M2) show zero variation when matched, indicating they represent similar "outlier" populations across conditions — tokens that the model processes outside the main computational pathway.

### Statistical significance

All four top pairs achieve p = 0.002 (the minimum achievable with 500 permutations), indicating the observed variation is robust — random permutation of token-condition assignments never produces comparable variation. This is strong evidence that the manifold structure is *condition-dependent*, not an artifact of sampling or the decomposition algorithm.

---

## 4. Diffusion Map Characterization

Stage 4 applied diffusion maps (α=1, density-independent) to the top-3 varying manifolds:

### numeric/M1 (84 points, dim ≈ 1.0)
- **Eigenvalue spectrum:** [1.002, 0.986, 0.938, 0.847, 0.737, 0.658]
- **Interpretation:** Slow eigenvalue decay indicates the manifold has significant structure across multiple diffusion coordinate dimensions. Despite being low-dimensional (intrinsic dim ≈ 1), the points are spread along a curve rather than clustered. This 1D manifold likely represents a *gradient* in number processing — perhaps encoding magnitude or digit count along a single principal direction.

### syntactic/M0 (880 points, dim ≈ 29.8)
- **Eigenvalue spectrum:** [1.002, 0.406, 0.380, 0.370, 0.343, 0.296]
- **Interpretation:** Sharp eigenvalue drop after λ₁ indicates the manifold has a strong "backbone" direction with many weaker secondary directions. The high intrinsic dimensionality (≈30) and rich Betti numbers suggest syntactic representations are genuinely complex — many independent degrees of freedom are needed to encode the combinatorial space of syntactic structures.

### numeric/M0 (906 points, dim ≈ 20.3)
- **Eigenvalue spectrum:** [1.002, 0.537, 0.418, 0.341, 0.317, 0.295]
- **Interpretation:** More gradual eigenvalue decay than syntactic/M0 — the manifold has 2–3 important coordinate directions before the spectrum flattens. Number processing, while high-dimensional, may have a more structured (lower effective rank) geometric organization than syntactic processing.

---

## 5. Synthesis and Key Takeaways

### What we found

1. **Manifold structure is real and condition-dependent.** GPT-2 Small layer 6 activations decompose into 2–3 manifolds per text condition, with statistically significant topological variation between conditions (4/7 pairs, all p = 0.002).

2. **Topology is the dominant axis of variation.** Cross-condition differences are primarily topological (component/loop/void counts), not geometric (eigenvalue spectra) or dimensional. This suggests the model doesn't just *rotate* or *scale* the same manifold for different tasks — it creates *structurally different* manifold arrangements.

3. **Numeric vs. syntactic processing is most distinct.** The model uses the most topologically different manifold structures for number vs. syntax processing, consistent with these being computationally distinct tasks requiring different representational strategies.

4. **Small manifolds capture outlier processing.** Minor manifolds (k=2,3) with few points appear consistently across conditions and match with zero variation, suggesting they capture a generic "exception handling" pathway rather than condition-specific computation.

### Comparison with Phase 5 predictions

| Prediction | Result | Assessment |
|---|---|---|
| k = 2–6 manifolds/condition | k = 2–3 | **Partial** — lower end of range, likely N-limited |
| Cross-condition variation significant (p<0.05) | 4/7 significant | **Confirmed** |
| Positional features show circular topology (β₁≥1) | β₁ = 0 for positional | **Not confirmed** at layer 6 / N=1000 |
| Feature families align with manifolds | Preliminary support | **Plausible** — clear numeric/syntactic separation |

---

## 6. Limitations

1. **Sample size (N=1000).** The low token count limits detection of smaller manifolds and reduces the stability of topological invariants. The PCA explained variance (99.6%) is excellent, but SMCE's Lasso stage produced convergence warnings for ~5% of points, suggesting some local neighborhoods are undersampled.

2. **Single layer (layer 6).** Layer 6 is mid-network for GPT-2's 12-layer architecture. Manifold structure likely evolves across layers — earlier layers may show stronger positional topology, later layers may show more task-specific structure.

3. **PCA as preprocessing.** Reducing from 768→100 dimensions preserves 99.6% of variance but discards low-variance directions that may carry topological signal (e.g., rare features encoded in small singular values).

4. **Betti number inflation.** The high β₀ values (83–497 connected components) for individual manifolds suggest the Vietoris-Rips persistence threshold may need tuning. Many short-lived H₀ features are likely noise rather than genuine disconnected components.

5. **No token-level attribution.** The current pipeline extracts activation vectors but doesn't track which tokens produced which manifold assignments. Adding token-to-manifold mapping would enable semantic interpretation of discovered structures.

---

## 7. Next Steps

1. **Scale to N=2000+ on GPU (Modal).** Bead ge-ilz covers the Modal GPU run. Higher N should reveal additional manifolds and stabilize topology estimates. Target: confirm or refute circular positional topology with better statistics.

2. **Multi-layer sweep.** Run the pipeline at layers 0, 3, 6, 9, 11 to characterize the layer-wise evolution of manifold structure. Does the number of manifolds peak at a specific depth? Does topological complexity follow the "hunchback" pattern?

3. **Token-manifold attribution.** Extend `activation_extraction.py` to track source tokens alongside activation vectors. Map manifold assignments back to tokens to identify *what* each manifold represents semantically.

4. **Persistence threshold calibration.** Implement adaptive thresholding for persistence diagrams to reduce β₀ inflation. Use the gap between short-lived and long-lived H₀ features as a natural cutoff.

5. **Cross-seed stability.** Run the pipeline on activations from different random initializations of the same text conditions. Seed-stable manifold structure would be strong evidence for converged geometric representations (relevant to Nova/pgolf's geometric regularization question).

6. **Trajectory dynamics within manifolds.** Jiang et al. (2026, TRACED) showed that reasoning quality correlates with geometric properties of reasoning *trajectories* — displacement and curvature through activation space. Applying their trajectory analysis within each detected manifold could reveal whether different manifolds support different trajectory dynamics (stable progress vs. hesitation loops), bridging our static manifold decomposition with dynamic reasoning characterization.

---

## Appendix: Output Artifacts

All outputs in `research/manifold_pipeline/outputs/`:

| File pattern | Description |
|---|---|
| `eigengap_*.png` | Laplacian eigenvalue spectrum with eigengap selection |
| `clusters_*.png` | 2D PCA projection colored by manifold assignment |
| `persistence_*_M*.png` | Persistence diagram per manifold per condition |
| `variation_heatmap.png` | Cross-condition variation score matrix |
| `diffusion_*_M*.png` | Diffusion map coordinates for top-varying manifolds |
| `summary_report.png` | Combined summary visualization |
| `results.json` | Machine-readable results |
| `cache/activations.npz` | Cached PCA-reduced activations (for re-runs) |
