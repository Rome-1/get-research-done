# Paper Outline: The Geometry of SAE Feature Spaces During Training

**Working title:** "Hyperplane Arrangements in Transformer Residual Streams: Architecture, Alignment, and the Dissociation of Geometry from Capability"

**Framing strategy** (per Bob's ge-2gs novelty assessment): Lead with training dynamics (Claim 2, more novel) and position the hyperplane arrangement characterization (Claim 1, partially novel) as the measurement framework.

---

## Abstract (draft)

We study the geometric structure of sparse autoencoder (SAE) feature spaces in transformer residual streams, discovering that SAE features partition activation space into a hyperplane arrangement — a union of convex polytopes with linear boundaries. Using Pythia-70m-deduped across 154 training checkpoints and 6 layers, we track how this arrangement evolves during training. We find: (1) the polyhedral structure (convexity 0.89-0.95, linearity 0.95-0.99) is present from the earliest training steps and is stable across all layers, indicating it is an architectural property of ReLU SAEs rather than a learned feature; (2) the model's representations align with their final-model SAE probe in a layer-dependent wave — early layers align first, with the last layer not aligning until 93% of training; (3) this geometric alignment transition is *negatively* correlated with downstream capability (r=-0.45), occurring after capabilities have already plateaued. We conclude that most of training is spent reorganizing *how* information is represented (geometric consolidation) rather than *what* information is represented (capability acquisition).

---

## 1. Introduction

- Mechanistic interpretability relies on SAE features being meaningful decompositions of neural network representations
- Prior work established: SAE features as half-spaces (Hindupur et al. 2025), polytopes in neural networks (Black et al. 2022), spline theory (Balestriero & Baraniuk 2018)
- Gap: no one has studied how the geometric arrangement of SAE features evolves during training, or whether geometric structure corresponds to capability
- **Our contribution:** Bridge the polytope lens (Black 2022) with SAE interpretability (Hindupur 2025), add novel empirical measurements, and use training dynamics to separate architecture from learning

### Key claims:
1. SAE features compose into a hyperplane arrangement on the residual stream (partially novel — extends Hindupur 2025)
2. The polyhedral structure is architectural, not learned (novel measurement)
3. Geometric alignment and capability acquisition are dissociated (novel finding)
4. Alignment propagates as a layer-dependent wave during late training (novel finding)

---

## 2. Background

### 2.1 SAE Features as Half-Spaces
- Hindupur et al. 2025: ReLU SAE features define half-spaces, TopK define hyperpyramids
- Our extension: the *composition* of features creates a hyperplane arrangement

### 2.2 Polytope Lens
- Black et al. 2022: polytopes in GPT-2 MLPs
- Balestriero & Baraniuk 2018: spline theory for ReLU networks
- Connection: SAE encoder = single-layer ReLU network → tropical polynomial → hyperplane arrangement

### 2.3 Training Dynamics of SAE Features
- Inglis 2024: feature matching across Pythia checkpoints
- Xu et al. 2024: semantic feature evolution
- Gap: neither studies the *geometric* evolution of the arrangement

---

## 3. Methods

### 3.1 Hyperplane Arrangement Metrics
- **Convexity:** Linear SVM accuracy on feature active/inactive regions
- **Boundary linearity:** SVM accuracy at feature transition boundaries
- **Intrinsic dimension:** Two-NN estimator, local PCA dimension maps
- **Sparsity pattern analysis:** Polytope occupancy (unique sparsity patterns)

### 3.2 Training Dynamics Pipeline
- Fixed SAE probe: final-model SAE applied to all training checkpoints
- Caveat: this measures alignment with the *final* representation, not intrinsic quality
- Metrics per checkpoint: var_explained, L0, dead features, convexity, linearity, intrinsic dim
- Scale: 154 checkpoints × 6 layers × 1000 tokens each

### 3.3 Capability-Geometry Correlation
- Published Pythia zero-shot evaluations (EleutherAI) at 20 checkpoints
- Benchmarks: LAMBADA, PIQA, ARC-Easy, SciQ, WinoGrande, etc.
- Pearson correlation between geometric metrics and capability scores

---

## 4. Results

### 4.1 Static Geometry: The Hyperplane Arrangement (Phase 2 data, GPT-2 Small)
- Convexity: 0.943 (30 features, all >0.90)
- Boundary linearity: 0.999 (87% of features = perfect 1.000)
- Feature activation regions are 1D rays (dim_active ≈ 1.0)
- 345 unique polytopes out of ~10^9 possible (extreme structure)
- Intrinsic dim varies 13.6x (polytope face structure)

### 4.2 The Polyhedral Structure is Architectural
- Convexity stable across all 154 checkpoints: 0.86-0.95
- Linearity stable: 0.95-0.99
- Present from step 16 (first step with enough active features to measure)
- Consistent across all 6 layers (0-5)
- Does not depend on SAE-model alignment (present even when var_exp = -10,000)

### 4.3 Training Dynamics: Three Phases

**Phase 1: Capability Acquisition (steps 1k-23k, 1-16% of training)**
- 90%+ of final capability acquired
- var_explained deeply negative (SAE sees model as "incompatible")
- L0 very high (5k-15k features active per token)

**Phase 2: Plateau & Divergence (steps 23k-99k, 16-69% of training)**
- Capabilities plateau or slightly decline
- L0 slowly decreasing, dead features increasing
- Epoch boundary at step ~99k (deduped Pile = 207B tokens)

**Phase 3: Geometric Consolidation (steps 99k-143k, 69-100% of training)**
- var_explained crosses zero at step 113k
- Capabilities continue slight decline
- Model spends 84% of compute reorganizing HOW it represents, not WHAT

### 4.4 Capability-Geometry Dissociation
- var_explained vs aggregate capability: r=-0.451 (p=0.079)
- As SAE alignment improves, benchmark performance *decreases*
- Table: timeline of capability peaks vs geometric transitions

### 4.5 Layer-Dependent Alignment Wave
- Layer 0: aligns at step 113k (79%), non-monotonic path
- Layer 3: aligns at step 113k (79%), monotonic convergence
- Layer 5: aligns at step 133k (93%), late divergence then rapid catch-up
- Interpretation: alignment wave propagates input → output

### 4.6 Step-32 Anomaly: Transient Representation Collapse
- At steps 32-64, layer 3 experiences extreme sparsification (L0: 96, 96% dead features)
- Layer-dependent: strongest in middle layers, weak in early layers
- Occurs during LR warmup (2% of warmup schedule)
- Reverses by step 128

---

## 5. Discussion

### 5.1 Architecture vs Learning in Geometric Structure
- The hyperplane arrangement is a mathematical consequence of ReLU SAE architecture
- Training does not create the arrangement; it selects which hyperplanes are used
- This resolves a potential confound in SAE interpretability: the "geometric meaningfulness" of features is partially architectural

### 5.2 The Consolidation Hypothesis
- Most training compute goes to representation reorganization, not capability acquisition
- This connects to: (a) grokking literature (delayed generalization), (b) neural tangent kernel regime transitions, (c) representation learning theory
- The epoch boundary may trigger consolidation by removing new information

### 5.3 Implications for SAE Interpretability
- SAE features define a valid geometric decomposition at ALL training stages
- But the specific feature *assignment* only stabilizes in late training
- Studying SAE features at early checkpoints may reveal *different but equally valid* decompositions

### 5.4 Limitations
- Fixed SAE probe bias (trained on final model)
- Single model size (Pythia-70m)
- Marginal p-value on capability correlation (p=0.079, n=16)
- PCA reduction to 50-100 dims may miss high-dimensional structure

---

## 6. Related Work
- Black et al. 2022 (Polytope Lens) — most direct predecessor
- Hindupur et al. 2025 (SAE feature geometry)
- Balestriero & Baraniuk 2018 (Spline theory)
- Inglis 2024, Xu et al. 2024 (SAE training dynamics)
- Valeriani et al. 2023, Li et al. 2024 (Transformer geometry)
- Biderman et al. 2023 (Pythia)

---

## 7. Conclusion

SAE features partition transformer residual streams into hyperplane arrangements whose geometric form is architectural but whose specific feature assignment evolves through training in three distinct phases. The finding that geometric consolidation is dissociated from — and even negatively correlated with — capability acquisition suggests that much of LLM training compute is spent on representation optimization, not information acquisition.

---

## Figures Needed

1. **Fig 1:** Schematic: hyperplane arrangement in 2D/3D showing convex polytopes, feature boundaries, sparsity patterns
2. **Fig 2:** Convexity and linearity heatmap across 154 checkpoints (showing stability)
3. **Fig 3:** var_explained trajectory for all 6 layers (cross-layer comparison)
4. **Fig 4:** Capability benchmarks overlaid on var_explained (the dissociation plot)
5. **Fig 5:** Three-phase diagram: capability (blue) vs geometry (red) vs L0 (green)
6. **Fig 6:** Intrinsic dimension evolution by layer
7. **Fig S1:** Step-32 anomaly detail across layers
