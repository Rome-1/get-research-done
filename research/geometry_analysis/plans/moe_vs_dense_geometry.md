# Research Plan: Geometry of MoE vs Dense Model Activations

**GRD ID:** ge-6xh  
**Status:** Planning  
**Date:** 2026-04-01  
**Authors:** Chaudhari, Nuer, Thorstenson  
**Dependencies:** Polyhedral Cone Hypothesis (confirmed GPT-2 Small L6), MoE Superposition paper (arXiv:2510.23671v2)

---

## 0. Motivation

We have two independent results that should connect but currently do not:

1. **Polyhedral Cone Hypothesis** (this group): SAE features partition transformer
   residual streams into hyperplane arrangements. Confirmed empirically on GPT-2
   Small layer 6 (convexity 0.943, linearity 0.999, 345 occupied polytopes).

2. **MoE Superposition paper** (arXiv:2510.23671v2): MoEs exhibit 2-4x less
   superposition than dense models in toy settings. Experts approach monosemantic
   representations. Network sparsity (not feature sparsity) controls the transition.

The gap: the MoE paper used toy autoencoders with synthetic features. The polyhedral
hypothesis was tested on a dense model (GPT-2 Small). **Nobody has studied the
polyhedral geometry of real MoE model activations.** This plan bridges that gap.

The central question: **Does the explicit partitioning from expert routing interact
with the implicit partitioning from SAE feature hyperplanes, and if so, how?**

---

## 1. Literature Survey

### 1.1 MoE Internal Representations and Expert Specialization

**Mixtral 8x7B** (Jiang et al., 2024, arXiv:2401.04088): 8 experts per layer,
top-2 routing, 47B total / 13B active parameters. The original paper provides
limited interpretability analysis. Subsequent work found:

- **Syntactic, not semantic, specialization.** Experts in Mixtral are assigned based
  on syntactic properties (token position, POS category) rather than topic or domain.
  Specialization is strongest in later layers, weakest in early layers (CS231n 2024
  student project, "Do Experts Specialize? A Mechanistic Exploration of Mixture of
  Experts Models").

- **"A Closer Look into Mixture-of-Experts in LLMs"** (NAACL 2025 Findings):
  Systematic analysis showing layer-dependent specialization patterns. Deeper layers
  show lower inter-expert similarity, suggesting progressive differentiation.

**OLMoE** (Muennighoff et al., 2024, arXiv:2409.02060): Fully open MoE, 7B total /
1B active, 64 experts per layer, top-8 routing. Key for our purposes:

- Routing analysis scripts available (GitHub: allenai/OLMoE).
- Per-layer routing skew is 4.0-4.9x higher than global CV -- experts strongly
  specialize within layers.
- Code/programming produces lowest routed-expert entropy -- domain-specific routing
  patterns exist.
- The matched dense counterpart is OLMo-1B, enabling controlled comparisons.

**DeepSeekMoE** (Dai et al., 2024, arXiv:2401.06066, ACL 2024): Key architectural
innovations relevant to geometry:

- Fine-grained expert segmentation: mN total experts, mK activated. Allows finer
  decomposition of knowledge into expert-specific subspaces.
- Shared expert isolation: K_s always-on experts capturing common knowledge.
  Geometrically, shared experts define a "background" subspace present in all
  routing configurations.
- This two-tier structure (shared + routed) maps naturally onto our polyhedral
  framework: shared experts define the common cone, routed experts refine within it.

**"Beyond Benchmarks: Understanding MoE Models through Internal Mechanisms"**
(arXiv:2509.23933, Sep 2025): Studied 13 MoE models (20B-200B) plus OLMoE training
checkpoints. Found: (1) neuron utilization decreases during training (stronger
generalization), (2) task completion requires collaborative multi-expert contributions
with shared experts driving concentration, (3) activation patterns at neuron level
proxy data diversity. The MoE-MUI metric provides fine-grained interpretability.

### 1.2 SAEs Applied to MoE Models

**This is the critical gap.** Direct SAE-on-MoE work is sparse but emerging:

- **No published work trains standard SAEs on Mixtral/OLMoE residual streams** and
  analyzes the resulting feature geometry. This is our primary opportunity.

- **Switch Sparse Autoencoders** (Conerly et al., 2024, arXiv:2410.08201): SAEs that
  internally use MoE-style routing between expert sub-dictionaries. This is the
  inverse direction -- using MoE structure *within* the SAE rather than applying SAEs
  *to* MoE models. Key result: substantial Pareto improvement in reconstruction vs.
  sparsity. Relevant because it shows MoE-style routing is beneficial even for the
  dictionary learning problem itself.

- **Route Sparse Autoencoder** (arXiv:2503.08200, Mar 2025): Routes activations to
  specialized SAE sub-dictionaries. Related to Switch SAEs but with different routing
  mechanism.

- **Scale SAE**: Claims 99% reduction in feature redundancy and 24% lower
  reconstruction error compared to prior MoE-SAE methods. Demonstrates that
  MoE-structured SAEs can dramatically reduce feature overlap.

### 1.3 Architecturally Interpretable MoEs

Two recent papers directly attempt to make MoEs interpretable by construction:

- **MoE-X: Mixture of Experts Made Intrinsically Interpretable** (arXiv:2503.07639,
  Mar 2025, ICML 2025): Rewrites MoE layer as equivalent sparse large MLP. Enforces
  sparse activation within each expert. Routes to experts with highest activation
  sparsity. Achieves perplexity better than GPT-2 with interpretability surpassing
  SAE-based approaches. **Critical implication for us:** if MoE-X achieves
  interpretability without SAEs, the polyhedral structure may be architecturally
  simpler -- fewer overlapping polytopes by construction.

- **Monet: Mixture of Monosemantic Experts for Transformers** (Park et al.,
  arXiv:2412.04139, ICLR 2025): Integrates sparse dictionary learning directly into
  MoE pretraining. Scales to 262,144 experts per layer. Achieves monosemantic experts
  with mutual exclusivity of knowledge. **Key geometric prediction:** with 262K
  monosemantic experts, the hyperplane arrangement should be extremely clean --
  each expert's subspace should correspond to a small number of polytope faces with
  minimal overlap.

### 1.4 Geometric Analysis of Expert Routing

- **Grassmannian MoE** (arXiv:2602.17798, Feb 2026): Routes on the Grassmannian
  manifold of subspaces. Each expert is associated with a subspace; routing = subspace
  classification. Uses Matrix Bingham distributions for concentration-controlled
  routing. **Direct geometric connection:** expert routing is literally subspace
  selection on a manifold, which is a coarse-grained version of polytope face
  selection in our framework.

- **ReMoE: ReLU Routing** (arXiv:2412.14711, ICLR 2025): Replaces TopK+Softmax
  routing with ReLU gates. Each expert's activation is controlled by ReLU(w_e . x + b_e),
  which is exactly a half-space indicator. **This is the most direct connection to our
  polyhedral hypothesis:** ReLU routing literally defines a hyperplane arrangement
  over expert assignments. ReMoE shows stronger domain specialization than TopK
  routing.

- **MoE with Gradient Conflict-Driven Subspace Topology Pruning** (arXiv:2512.20291,
  Dec 2025): Prunes experts based on gradient subspace conflicts, revealing modular
  structure. Relevant because it shows experts occupy distinct gradient subspaces.

### 1.5 Expert Collapse, Load Balancing, and Geometric Implications

- Expert collapse = multiple experts converging to same representation = polytope
  faces merging. Geometrically, collapsed experts define redundant hyperplanes.
- Auxiliary load-balancing losses (standard in Mixtral, Switch Transformer) prevent
  collapse by distributing tokens across experts. Geometrically, this enforces that
  the routing hyperplane arrangement has roughly equal-volume polytopes.
- DeepSeek-V3 (2024) achieves load balance without auxiliary loss, suggesting the
  geometry self-organizes.
- Similarity-preserving load balancing stabilizes expert selection for related inputs
  while avoiding collapse -- geometrically, this preserves local polytope structure.

### 1.6 What Has NOT Been Done

1. Nobody has trained SAEs on MoE residual streams and measured arrangement complexity.
2. Nobody has compared the polyhedral geometry of dense vs. MoE models at matched scale.
3. Nobody has asked whether expert routing boundaries align with SAE feature boundaries.
4. Nobody has measured whether individual experts have simpler hyperplane arrangements.
5. The connection between ReLU routing hyperplanes and SAE feature hyperplanes is
   uncharacterized.

---

## 2. Research Questions

### Q1: Arrangement Complexity

**Do MoE models have cleaner polyhedral structure than dense models?**

- Operationalization: Train SAEs on matched dense/MoE pairs. Measure convexity,
  linearity, number of occupied polytopes, intrinsic dimension distribution.
- Expected from theory: MoE should have fewer occupied polytopes (cleaner arrangement)
  because expert routing pre-partitions the space. Each expert handles a subset of the
  full arrangement.
- Null hypothesis: Arrangement complexity is the same because the SAE captures
  information the model represents, not how it routes.

### Q2: Routing-Feature Alignment

**Does expert routing align with SAE feature boundaries?**

- Operationalization: For each expert's routing region, identify which SAE features
  are active. Measure mutual information between expert assignment and SAE feature
  activation patterns.
- Expected: High MI if routing and features decompose the same structure. Low MI if
  routing is a coarser/orthogonal partitioning.
- This is the key bridging question between our two papers.

### Q3: Superposition Visibility

**Is the 2-4x less superposition from toy models visible in real model geometry?**

- Operationalization: Measure features-per-dimension in SAE reconstructions of MoE
  vs dense activations. Compute feature direction angles, co-activation density.
- Expected from arXiv:2510.23671v2: MoE features should be more orthogonal, have
  lower co-activation, and approach monosemantic representations.
- Key test: does the 2-4x ratio from toy models hold at real scale?

### Q4: Within-Expert Arrangement Simplicity

**Do individual experts have simpler hyperplane arrangements than equivalent dense layers?**

- Operationalization: Train per-expert SAEs (or segment a global SAE by routing
  assignments). Measure arrangement metrics per expert. Compare to the full-model
  arrangement and to a dense model's arrangement.
- Expected: Each expert's arrangement should have fewer hyperplanes and fewer occupied
  polytopes than the full model or a dense equivalent, because the expert handles a
  subset of the input distribution.

### Q5: Expert Boundary Geometry

**What is the geometric signature of routing decisions?**

- Operationalization: Sample activations near expert routing boundaries (where router
  scores for top-2 experts are close). Measure local intrinsic dimension, SAE feature
  stability (do features flip at routing boundaries?), and polytope transitions.
- Expected: Routing boundaries should coincide with SAE feature transitions (some
  features change activity status at the routing boundary). The routing boundary is
  a hyperplane in the polyhedral arrangement.

### Q6: ReLU Routing Connection (Bonus)

**For ReMoE-style models, does the routing hyperplane arrangement literally coincide
with a subset of the SAE feature arrangement?**

- This is the sharpest possible test: ReLU routing defines hyperplanes. SAE features
  define hyperplanes. Are they the same hyperplanes?
- Operationalization: Compare routing weight vectors to SAE encoder weight vectors
  using cosine similarity. Perfect alignment = 1.0.

---

## 3. Theoretical Predictions

### 3.1 Expert Routing as Coarse-Grained Hyperplane Arrangement

**Claim:** The expert routing function in a top-k MoE defines a hyperplane arrangement
on the residual stream that is a coarsening of the SAE feature arrangement.

**Argument:** In standard top-k routing, the router computes scores s_e = w_e . x + b_e
for each expert e. The routing decision selects the top-k experts by score. The
boundary between expert e1 being selected over expert e2 is the hyperplane
w_{e1} . x + b_{e1} = w_{e2} . x + b_{e2}, i.e., (w_{e1} - w_{e2}) . x = b_{e2} - b_{e1}.

For E experts with top-k routing, this defines C(E,2) potential boundary hyperplanes
(one for each pair). The actual routing creates a Voronoi-like partition of activation
space into regions, one per expert combination.

In ReLU routing (ReMoE), the correspondence is even more direct: each expert's gate
g_e(x) = ReLU(w_e . x + b_e) defines a half-space, exactly like an SAE feature.

**Prediction P1:** The routing partition is a union of SAE polytope faces. That is,
every routing region boundary aligns with (or is well-approximated by) a boundary
in the SAE feature arrangement.

### 3.2 Within-Expert Arrangement Simplicity

**Claim:** Restricting to activations routed to a single expert e, the SAE feature
arrangement is simpler than the full arrangement.

**Argument:** Expert e processes a subset of the input distribution. If the routing
effectively partitions by feature usage (as suggested by our MoE paper's
monosemanticity findings), then expert e's inputs activate a smaller subset of SAE
features. Fewer active features = fewer relevant hyperplanes = simpler arrangement.

**Prediction P2:** For an MoE with E experts and top-1 routing, the per-expert
arrangement should have roughly 1/E as many occupied polytopes as the full
arrangement, and the hyperplane count should be reduced by a similar factor.

### 3.3 Superposition Reduction as Arrangement Sparsification

**Claim:** The 2-4x superposition reduction from our toy model paper manifests
geometrically as a sparser hyperplane arrangement -- fewer features per dimension
means fewer hyperplanes per dimension, which means larger polytopes with more
interior volume.

**Prediction P3:** Polytope occupancy (fraction of tokens sharing a sparsity pattern)
should be higher in MoE models than dense models. In dense GPT-2 L6, we measured
345 unique patterns / 1500 tokens = 0.23 compression. An MoE equivalent should have
compression < 0.12 (2x improvement) to < 0.06 (4x improvement).

### 3.4 Expert Routing Boundaries as Feature Transitions

**Claim:** At expert routing boundaries (where the router is near-indifferent between
two experts), multiple SAE features should simultaneously change activation status.

**Argument:** If routing partitions by feature groups, the routing boundary is where
the dominant feature group changes. Multiple features should transition together at
this boundary, producing a "bundle" of hyperplane crossings.

**Prediction P4:** Local intrinsic dimension should be lower at routing boundaries
than at random points (more hyperplane constraints active = lower effective dimension).
Additionally, the number of SAE feature transitions (features that change from
active to inactive or vice versa) within epsilon of a routing boundary should be
higher than at random locations.

### 3.5 Interaction Between Explicit and Implicit Partitioning

**Claim:** In well-trained MoEs, the two partitioning mechanisms (routing and SAE
features) should be hierarchically organized: routing provides the coarse partition
into expert regions, SAE features provide the fine partition within each region.

**Prediction P5:** The mutual information I(expert_assignment; SAE_sparsity_pattern)
should be high but not maximal. It should be higher than I(random_partition;
SAE_sparsity_pattern) by a factor of at least 2x. The conditional entropy
H(SAE_pattern | expert) should be substantially lower than H(SAE_pattern), indicating
that expert assignment reduces uncertainty about which polytope a token occupies.

---

## 4. Experimental Design

### 4.1 Model Selection

We need matched dense/MoE pairs to isolate the effect of expert routing:

| MoE Model | Dense Match | Total Params | Active Params | Experts | Routing | Open Weights | SAE Available |
|-----------|-------------|:---:|:---:|:---:|---------|:---:|:---:|
| **OLMoE-1B-7B** | OLMo-1B | 7B | 1B | 64/layer, top-8 | TopK+Softmax | Yes | No |
| **Mixtral 8x7B** | Mistral 7B | 47B | 13B | 8/layer, top-2 | TopK+Softmax | Yes | No |
| Snowflake Arctic | -- | 480B | 17B | 128, top-2 | TopK | Yes | No |
| DeepSeek-V2-Lite | -- | 16B | 2.4B | 64, top-6 | TopK | Yes | No |

**Primary pair: OLMoE-1B-7B vs OLMo-1B.**

Rationale:
- Exact architectural match (same tokenizer, training data distribution, hyperparams
  except MoE layers)
- OLMo-1B is small enough to run on a single A100
- OLMoE-1B-7B active params = 1B, same as OLMo-1B
- 64 experts provides rich routing structure
- Fully open with routing analysis tools
- Allen AI has published detailed routing analysis

**Secondary pair: Mixtral 8x7B vs Mistral 7B.**

Rationale:
- Most-studied MoE in the interpretability literature
- Only 8 experts (coarser partition, different regime than OLMoE's 64)
- Larger model tests whether findings scale
- Requires more compute (47B params) but can be run in 4-bit on 2x A100

**Bonus (if ReMoE weights available): ReMoE vs equivalent TopK MoE.**

Rationale: ReLU routing provides the sharpest test of routing-SAE alignment (Q6).

### 4.2 What to Measure

#### Metric Suite A: Arrangement Complexity (for Q1, Q3, Q4)

| Metric | Definition | What It Tests |
|--------|-----------|---------------|
| **Convexity** | Linear SVM accuracy on feature active/inactive | P1: half-space structure |
| **Boundary linearity** | SVM accuracy at feature boundaries | P1: hyperplane boundaries |
| **Occupied polytopes** | Count of unique SAE sparsity patterns | P2, P3: arrangement simplicity |
| **Polytope compression** | Occupied / total tokens | P3: tokens per polytope |
| **Features per dim** | L0 / residual stream dim | P3: superposition level |
| **Feature angles** | Mean pairwise angle of SAE encoder weights | P3: orthogonality |
| **Intrinsic dim distribution** | Two-NN and local PCA across the space | P4: boundary structure |

#### Metric Suite B: Routing-Feature Alignment (for Q2, Q5, Q6)

| Metric | Definition | What It Tests |
|--------|-----------|---------------|
| **MI(expert, SAE pattern)** | Mutual information between routing and sparsity pattern | P5: hierarchical structure |
| **Conditional entropy** | H(SAE_pattern \| expert) vs H(SAE_pattern) | P5: uncertainty reduction |
| **Feature stability at boundaries** | Fraction of features that flip within epsilon of routing boundary | P4: bundled transitions |
| **Boundary intrinsic dim** | Local PCA dim at routing boundaries vs interior | P4: lower dim at boundaries |
| **Router-encoder cosine sim** | cos(w_router_e, w_SAE_k) for all (e,k) pairs | P1, Q6: hyperplane alignment |

#### Metric Suite C: Per-Expert Analysis (for Q4)

| Metric | Definition | What It Tests |
|--------|-----------|---------------|
| **Per-expert polytope count** | Unique patterns restricted to expert e's tokens | P2: simpler per-expert |
| **Per-expert feature count** | Number of SAE features active for expert e's tokens | P2: fewer features |
| **Per-expert convexity** | Convexity measured within expert e's token set | P1 per expert |
| **Expert feature overlap** | Jaccard(features_e1, features_e2) across expert pairs | Specialization measure |

### 4.3 SAE Training Strategy

**Problem:** No published SAEs exist for OLMoE or Mixtral residual streams.

**Options (ranked by feasibility):**

1. **Train our own SAEs on OLMoE-1B-7B and OLMo-1B.** Use SAELens or the
   EleutherAI SAE training pipeline. Target: residual stream at layers {0, L/4,
   L/2, 3L/4, L-1}. Dictionary size: 8x-32x residual dim. ReLU activation
   (to maintain the hyperplane arrangement structure).

   Compute: ~4-8 A100-hours per SAE per layer. For 5 layers x 2 models = 10 SAEs
   = 40-80 A100-hours. **Feasible on Modal/Lambda.**

2. **Use existing GPT-2/Gemma SAEs as a methodological validation**, then train
   MoE SAEs. We already have GPT-2 Small results; this provides a dense baseline.

3. **Skip SAEs and use the model's own neurons as features.** Faster but loses
   the polyhedral framework comparison. Only as a fallback.

**Recommendation:** Option 1 is necessary for the core contribution. Start with
Option 2 for methodology validation.

**SAE architecture decision:** Must use ReLU (not TopK or JumpReLU) to maintain
the hyperplane interpretation. TopK SAEs produce hyperpyramids (Hindupur et al.
2025), complicating the comparison. We can add TopK SAEs as a robustness check.

### 4.4 Experimental Pipeline

**Phase 0: Methodology Validation (2-3 days, ~10 A100-hours)**

- Reproduce polyhedral measurements on GPT-2 Small L6 (already done)
- Train SAE on Mistral 7B residual stream at one layer
- Verify arrangement metrics work on a 7B-scale dense model
- Deliverable: confirmed pipeline scalability

**Phase 1: SAE Training (1-2 weeks, ~80 A100-hours)**

- Train ReLU SAEs on OLMoE-1B-7B residual stream, 5 layers, 16x overcomplete
- Train ReLU SAEs on OLMo-1B residual stream, matching layers
- Validate: reconstruction loss, L0, dead features comparable to published SAEs
- Deliverable: 10 trained SAEs with matched specifications

**Phase 2: Arrangement Comparison (3-5 days, ~20 A100-hours)**

- Run Metric Suite A on both models across all layers
- Collect 10K+ tokens per condition (need more than the 1.5K used for GPT-2)
- Statistical tests: paired comparisons across layers, bootstrap CIs
- Deliverable: Table comparing arrangement complexity dense vs MoE

**Phase 3: Routing-Feature Analysis (1 week, ~30 A100-hours)**

- Extract routing assignments for the 10K+ tokens
- Compute Metric Suite B (MI, conditional entropy, boundary analysis)
- Run Metric Suite C (per-expert analysis)
- For routing boundaries: identify tokens where top-2 expert scores are within
  10% of each other. Measure feature stability in this boundary region.
- Deliverable: routing-feature alignment quantification

**Phase 4: Cross-Scale Validation (1-2 weeks, ~60 A100-hours)**

- Repeat Phase 2-3 on Mixtral 8x7B vs Mistral 7B (only if Phase 2-3 show signal)
- 8 experts vs 64 experts: does arrangement simplicity scale with expert count?
- Deliverable: scaling analysis

**Total estimated compute: 200 A100-hours (~$600-800 on Modal at $3-4/hr)**

### 4.5 Normalization and Comparison Strategy

Comparing models of different sizes requires care:

- **Features per dimension** (L0 / d_model): already normalized by model width.
- **Polytope compression** (unique patterns / N tokens): normalized by sample size.
- **Convexity and linearity**: already in [0, 1].
- **Feature angles**: normalize by the expected angle for random vectors in d
  dimensions (arccos(0) = 90 degrees in high dim).
- **MI and entropy**: normalize MI by min(H(expert), H(SAE_pattern)) to get
  normalized MI in [0, 1].
- **Per-expert metrics**: normalize by expert count (report per-expert averages).

For the OLMoE vs OLMo comparison, the models have the same active parameter count
(1B), same tokenizer, and similar training data -- this is as clean a comparison as
exists in the open-source ecosystem.

---

## 5. Connection to Published MoE Paper

### 5.1 What the Paper Showed (Toy Models)

- MoEs exhibit 2-4x less superposition (features per dimension)
- No discontinuous phase changes
- Network sparsity controls the transition
- Experts approach monosemantic representations
- All in synthetic settings with known features

### 5.2 What This Plan Tests (Real Models)

| Toy Model Finding | Real Model Test | Success Criterion |
|---|---|---|
| 2-4x less superposition | Features per dim in OLMoE vs OLMo | OLMoE shows measurably lower features/dim |
| No phase changes | (Not directly testable without varying sparsity) | N/A for this plan |
| Network sparsity controls | Compare OLMoE (64 experts) vs Mixtral (8 experts) | More experts = less superposition |
| Expert monosemanticity | Per-expert SAE analysis | Per-expert arrangements are simpler |
| Block-diagonal interference | Expert feature overlap (Jaccard) | Low cross-expert feature sharing |

### 5.3 How This Extends the Theory

The polyhedral framework provides the missing measurement toolkit for the MoE paper's
theoretical predictions. Instead of measuring "features per dimension" via toy model
ground truth (which doesn't exist in real models), we can measure:

- **Arrangement complexity** as a proxy for superposition level
- **Per-expert arrangement simplicity** as evidence for monosemanticity
- **Routing-feature alignment** as evidence for the "block-diagonal" claim
- **Polytope compression** as a geometric signature of reduced superposition

This turns the MoE paper's theoretical predictions into empirically testable
geometric measurements on real models.

### 5.4 Potential Paper

**Working title:** "The Polyhedral Geometry of Expert Routing: How MoE Architecture
Simplifies Hyperplane Arrangements in Transformer Residual Streams"

**Narrative:** Our prior work predicted MoEs should have simpler feature structure.
Our polyhedral framework provides the measurement. We confirm: MoE models have
[fewer polytopes / higher compression / simpler per-expert arrangements] than
matched dense models, and expert routing boundaries align with SAE feature
boundaries, providing geometric evidence that MoE architecture reduces superposition
in real-scale language models.

---

## 6. Risks and Mitigations

### 6.1 Compute Feasibility

**Risk:** MoE models are large. OLMoE-1B-7B has 7B total params; Mixtral has 47B.

**Mitigation:** We only need forward passes (no training the MoE). OLMoE's active
params = 1B, comparable to GPT-2 XL. With 4-bit quantization, OLMoE fits on a
single A100. Mixtral in 4-bit needs 2x A100 or an A100-80GB. Modal and Lambda
provide this at ~$3-4/hr.

### 6.2 SAE Training on MoEs

**Risk:** Nobody has published SAEs on MoE residual streams. The residual stream
in MoE models may have different statistical properties (e.g., multimodal
distribution from different expert outputs being added back).

**Mitigation:** (a) Start with OLMo-1B (dense) to validate the pipeline. (b) The
residual stream in MoEs is architecturally identical to dense models between MoE
layers -- it's the same vector space. The MoE layer writes to the residual stream
just like a dense MLP layer. (c) If SAE training struggles, try training SAEs on
expert outputs separately (per-expert SAEs) rather than on the combined residual
stream.

### 6.3 SAE Quality

**Risk:** Our SAEs might be lower quality than the published GPT-2 SAEs
(JumpReLU SAEs from Anthropic, TopK from OpenAI). Low-quality SAEs could produce
meaningless arrangement comparisons.

**Mitigation:** (a) Use established SAE training recipes (SAELens default configs).
(b) Report standard SAE quality metrics (L0, reconstruction loss, dead features)
alongside arrangement metrics. (c) Compare our GPT-2 SAE to published GPT-2 SAEs
as a calibration.

### 6.4 Routing Too Coarse

**Risk:** Expert routing may be too coarse a partitioning to interact meaningfully
with the fine-grained SAE feature arrangement. With only 8 experts (Mixtral),
the routing creates 8 regions vs potentially thousands of SAE polytopes.

**Mitigation:** (a) OLMoE has 64 experts (finer partitioning). (b) Even if routing
is coarse, the hierarchical structure (coarse routing + fine SAE features) is itself
a finding. (c) We can analyze top-k routing scores (not just assignments) to get a
continuous routing signal.

### 6.5 Null Result

**Risk:** MoE and dense models have identical polyhedral geometry, and expert
routing is orthogonal to SAE features.

**Assessment:** This would itself be a publishable finding -- it would mean our
toy model predictions don't hold at scale, and expert routing solves a different
problem than superposition reduction. It would also constrain future theories.

**Mitigation:** Design experiments to be informative regardless of direction.
Report effect sizes and confidence intervals, not just significance.

### 6.6 ReLU SAE Requirement

**Risk:** We require ReLU SAEs for the hyperplane interpretation, but state-of-the-art
SAEs use TopK or JumpReLU activations.

**Mitigation:** (a) ReLU SAEs are well-characterized and SAELens supports them.
(b) We can train TopK SAEs as a secondary analysis. (c) Hindupur et al. (2025)
show TopK SAEs produce hyperpyramids, which are still polyhedral -- just with a
different combinatorial structure. The arrangement comparison still works, it's
just more complex.

### 6.7 Expert-Level SAE Training Data

**Risk:** Individual experts may not see enough diverse tokens to train high-quality
per-expert SAEs (Q4 requires this).

**Mitigation:** (a) With top-k routing (k >= 2 in Mixtral, k = 8 in OLMoE), each
expert sees a large fraction of tokens. (b) Alternative: train a single global SAE,
then segment its features by which expert's tokens activate them. This avoids the
per-expert training data problem entirely.

---

## 7. Timeline and Milestones

| Week | Phase | Milestone | Go/No-Go |
|------|-------|-----------|----------|
| 1 | 0 | Pipeline validated on Mistral 7B dense | Can we measure arrangements at 7B scale? |
| 2-3 | 1 | SAEs trained on OLMoE + OLMo | Reconstruction loss within 2x of published SAEs |
| 4 | 2 | Arrangement comparison complete | Is there a measurable MoE vs dense difference? |
| 5 | 3 | Routing-feature analysis complete | Does routing align with SAE features? |
| 6-7 | 4 | Mixtral validation (conditional) | Does the finding replicate at larger scale? |
| 8 | -- | Paper draft | -- |

**Go/No-Go decision after Week 4:** If arrangement metrics show no significant
difference between OLMoE and OLMo, pivot to analyzing the null result or shift
focus to per-expert analysis (which may still show signal even if global metrics
don't differ).

---

## 8. References

### Our Work
1. Chaudhari, Nuer, Thorstenson (2025). "Sparsity and Superposition in Mixture of
   Experts." arXiv:2510.23671v2.
2. Polyhedral Cone Hypothesis (this repo). GPT-2 Small L6 results.

### MoE Architecture and Interpretability
3. Jiang et al. (2024). "Mixtral of Experts." arXiv:2401.04088.
4. Muennighoff et al. (2024). "OLMoE: Open Mixture-of-Experts Language Models."
   arXiv:2409.02060.
5. Dai et al. (2024). "DeepSeekMoE: Towards Ultimate Expert Specialization."
   arXiv:2401.06066. ACL 2024.
6. "Do Experts Specialize? A Mechanistic Exploration of Mixture of Experts Models."
   CS231n 2024 student project.
7. "A Closer Look into Mixture-of-Experts in LLMs." NAACL 2025 Findings.
8. "Beyond Benchmarks: Understanding MoE Models through Internal Mechanisms."
   arXiv:2509.23933, Sep 2025.

### Interpretable MoE Architectures
9. "MoE-X: Mixture of Experts Made Intrinsically Interpretable." arXiv:2503.07639,
   ICML 2025.
10. Park et al. (2024). "Monet: Mixture of Monosemantic Experts for Transformers."
    arXiv:2412.04139, ICLR 2025.

### SAE and MoE-Structured SAEs
11. Conerly et al. (2024). "Efficient Dictionary Learning with Switch Sparse
    Autoencoders." arXiv:2410.08201.
12. "Route Sparse Autoencoder to Interpret LLMs." arXiv:2503.08200, Mar 2025.
13. "A Survey on Sparse Autoencoders." arXiv:2503.05613, EMNLP 2025 Findings.

### Geometric Routing
14. "Grassmannian MoE: Concentration-Controlled Routing on Subspace Manifolds."
    arXiv:2602.17798, Feb 2026.
15. "ReMoE: Fully Differentiable MoE with ReLU Routing." arXiv:2412.14711, ICLR 2025.
16. "MoE with Gradient Conflict-Driven Subspace Topology Pruning." arXiv:2512.20291.

### Polyhedral and Geometric Foundations
17. Black et al. (2022). "Interpreting Neural Networks through the Polytope Lens."
    arXiv:2211.12312.
18. Hindupur et al. (2025). "Projecting Assumptions: Duality Between SAEs and Concept
    Geometry." NeurIPS 2025. arXiv:2503.01822.
19. Balestriero & Baraniuk (2018). "A Spline Theory of Deep Networks." ICML 2018.
20. Brandenburg, Loho & Montufar (2024). "Real tropical geometry of neural networks."
    arXiv:2403.11871.
21. Lee et al. (2024). "Defining Neural Network Architecture through Polytope
    Structures of Datasets." ICML 2024. arXiv:2402.02407.

### Superposition Theory
22. Elhage et al. (2022). "Toy Models of Superposition." Anthropic. arXiv:2209.10652.
23. Li, Michaud, Baek et al. (2024). "The Geometry of Concepts." arXiv:2410.19750.
24. Prieto et al. (2026). "From Data Statistics to Feature Geometry." arXiv:2603.09972.
