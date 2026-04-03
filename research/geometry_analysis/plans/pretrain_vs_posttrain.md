# Research Plan: Activation Geometry Pre-Training vs Post-Training (OLMo Snapshots)

**Direction:** ge-fdc
**Status:** Planning
**Date:** 2026-04-01
**Dependencies:** ge-plx (Pythia dynamics), ge-y3a (polyhedral cone hypothesis), ge-97d (capability-geometry correlation)

---

## 0. Motivation

We have established three core findings about transformer activation geometry:

1. **The Polyhedral Cone Hypothesis** (GPT-2 Small): residual stream activations partition into convex polytopes defined by SAE feature hyperplanes (convexity 0.943, linearity 0.999).
2. **Geometric consolidation during pre-training** (Pythia-70m, 154 checkpoints, 6 layers): capabilities emerge in the first 16% of training, but geometric alignment with the final SAE takes 79-100% of training. The two are negatively correlated (r=-0.451).
3. **Non-sequential layer alignment**: layers align in the order L1->L4->L2->L0->L3->L5, not input-to-output. The epoch boundary is a critical consolidation trigger.

The open question: **what does post-training (SFT, DPO, RLHF, RLVR) do to this geometry?** Post-training is responsible for safety behaviors, instruction following, and reasoning capabilities. If pre-training establishes the hyperplane arrangement and post-training merely adjusts activation distributions within existing polytopes, that has profound implications for alignment robustness. If post-training creates genuinely new geometric structure, that tells a different story about how deep safety goes.

OLMo is the ideal testbed: fully open weights, intermediate pre-training checkpoints at every 1000 steps, and a documented multi-stage post-training pipeline (SFT -> DPO -> RLVR) with all intermediate checkpoints released.

---

## 1. Literature Survey

### 1.1 Post-Training and Internal Representations

**Refusal direction universality.** Arditi et al. (2024, arXiv:2406.11717) showed that refusal in safety-aligned LLMs is mediated by a single direction in activation space. Erasing this direction abolishes refusal; adding it triggers over-refusal. This is the strongest geometric result about post-training effects: safety alignment creates (or amplifies) a specific linear subspace.

**Refusal is not monosemantic.** Wollschlager et al. (2025) challenge the single-direction model, arguing refusal is governed by multiple independently controllable axes -- a "concept cone" rather than a line. This directly connects to our polyhedral framework: refusal may correspond to a polytope face (intersection of multiple hyperplanes) rather than a single hyperplane.

**Post-training changes are directionally distinct from pre-training.** Du et al. (2025) show that the refusal direction in base models has low cosine similarity with the refusal direction in aligned models. Forward transfer of the base-model direction is ineffective. This implies post-training creates genuinely new geometric structure, not just amplification of existing directions.

**RLHF-induced saturation.** Ali et al. (2025) find that refusal signals in aligned models are "maxed out" -- negative steering (subtracting refusal direction) is far more effective than positive steering. This asymmetry has geometric implications: post-training may push activations to the boundary of a polytope face where further movement in the safety direction is constrained.

**Safety features via SAEs.** Arditi et al. (2024, arXiv:2411.11296) use SAEs to identify and steer refusal features. Kerl (2025, TU Wien thesis) systematically evaluates SAE-based refusal features across data regimes. A key finding: SAEs trained on instruction-tuning data plus pre-training data yield more robust refusal features than either alone. This suggests post-training features are distributed across the SAE basis, not isolated.

**SAFER framework.** The SAFER paper (arXiv:2507.00665) uses SAEs to probe safety in reward models, finding interpretable safety features in reward model activations. This establishes precedent for SAE-based analysis of post-training artifacts.

**Refusal direction is cross-lingual.** Research (arXiv:2505.17306) shows refusal directions generalize across languages, suggesting post-training geometry is language-agnostic -- a structural rather than content-level change.

### 1.2 Representation Engineering and Activation Steering

**Linear Representation Hypothesis.** Park et al. (ICML 2024) formalize the hypothesis that concepts are encoded as linear directions. They prove geometric connections between linear probing and model steering. This is the theoretical foundation for measuring post-training changes as directional shifts.

**Representation Engineering survey.** Wehner et al. (arXiv:2502.19649) and the broader RepE survey (arXiv:2502.17601) document the two-step paradigm: representation reading (locating concepts) and representation control (steering). SAE features provide a natural basis for both.

**Conditional Activation Steering (CAST).** Uses cosine similarity between hidden states and condition vectors to selectively trigger interventions. This technique could be adapted to measure how post-training changes the activation distribution relative to pre-training hyperplane arrangements.

**Runtime steering can surpass post-training.** Recent work shows that extracting reasoning directions from base models and patching them at runtime can outperform instruction-tuned models. This implies post-training effects are at least partially capturable as geometric shifts that can be applied externally.

### 1.3 OLMo as a Testbed

**OLMo 2 (AI2, 2024).** 7B and 13B parameter models with full transparency: training data (Dolma, 3T tokens), intermediate checkpoints every 1000 steps, and complete post-training pipeline. Architecture: 32 layers, hidden size 4096, 32 attention heads, SwiGLU activation, RoPE, no biases.

**OLMo 3 (AI2, 2025).** Extends to multiple post-training paths from the same base: Instruct (SFT->DPO->RLVR), Think (reasoning SFT->DPO->RLVR), and RL Zero (direct RL from base). Available at 7B and 32B. The multi-path design is ideal for comparing geometric effects of different post-training recipes.

**Checkpoint naming:** Intermediate checkpoints are named like `step1000-tokens5B` and accessible via HuggingFace revisions. Post-training stages each produce separate model releases.

**No pre-trained OLMo SAEs exist** (as of April 2026). We will need to train our own or use a framework like SAE Lens / Language-Model-SAEs. This is a significant but tractable compute cost.

### 1.4 MoE and Superposition Context

**MoE superposition paper** (arXiv:2510.23671v2). MoE models exhibit 2-4x less superposition than dense models. Network sparsity (ratio of active to total experts) better characterizes MoE behavior than feature sparsity. If post-training reduces superposition (by specializing representations), we should see this in our metrics: fewer active SAE features per token, more concentrated polytope occupancy.

### 1.5 Gaps in the Literature

No published work has:
1. Measured how SAE hyperplane arrangements change across the pre-training -> post-training boundary
2. Compared polyhedral cone structure (convexity, linearity, intrinsic dimension) between base and aligned models
3. Tracked which specific SAE features are created, destroyed, or shifted by post-training
4. Connected the refusal direction literature to the broader hyperplane arrangement framework
5. Used OLMo's multi-path post-training (Instruct vs Think vs RL Zero) to compare geometric effects of different alignment recipes

---

## 2. Research Questions

### Primary Questions

**RQ1: Does post-training reorganize the hyperplane arrangement, or just shift activation distributions within existing polytopes?**
- Operationalized: Train SAEs on both base and post-trained OLMo. Measure (a) feature direction cosine similarity between the two SAEs, (b) the number of shared vs unique features, (c) whether base-SAE polytope boundaries are preserved in post-trained activations.
- If post-training is "shallow": base-SAE convexity and linearity metrics are preserved on post-trained activations; feature overlap is high (>80%).
- If post-training is "deep": base-SAE metrics degrade on post-trained activations; many new features appear that have no base-model counterpart.

**RQ2: Do safety behaviors correspond to new hyperplanes or repurposed existing ones?**
- Operationalized: Identify SAE features that activate differentially for harmful-prompt refusal in the post-trained model. Check whether these features (a) exist in the base-model SAE (repurposed) or (b) emerge only in the post-trained SAE (new).
- Connect to Arditi et al.'s refusal direction: is the refusal direction expressible as a sparse linear combination of base-model SAE features?

**RQ3: Is the geometric change localized to specific layers or global?**
- Operationalized: Compute arrangement similarity (feature overlap, convexity change, intrinsic dimension shift) at every layer. Plot the "post-training impact profile" across layers.
- Prediction from our Pythia results: layers that aligned latest during pre-training (L5 equivalent, output-adjacent) may show the most post-training change.

**RQ4: How does the polyhedral cone structure differ between base and post-trained OLMo?**
- Operationalized: Run the full Phase 2 measurement suite (convexity, linearity, intrinsic dimension, polytope count, sparsity patterns) on both base and post-trained models at matched layers.
- If polyhedral structure is purely architectural: convexity/linearity should be identical. If post-training alters it: we may see systematic shifts.

### Secondary Questions

**RQ5: Do different post-training recipes (SFT-only, DPO, RLVR) produce different geometric signatures?**
- OLMo 3 releases intermediate post-training checkpoints. Compare geometry after SFT vs after DPO vs after RLVR.
- Hypothesis: DPO produces more targeted geometric changes (specific hyperplane shifts) while RLVR produces broader rearrangement.

**RQ6: Does post-training change intrinsic dimension?**
- RLHF may either compress representations (specialization -> lower ID) or expand them (new capabilities -> higher ID).
- Measure Two-NN intrinsic dimension at each layer for base vs post-trained.

**RQ7: Is the epoch boundary effect from Pythia analogous to the pre-train/post-train boundary?**
- Both involve a distribution shift (new data for epoch 2; new objective for post-training). Both may trigger geometric consolidation.
- Compare the rate and pattern of geometric change at the Pythia epoch boundary vs the OLMo post-training boundary.

---

## 3. Experimental Design

### 3.1 Model Selection

**Primary models (OLMo 2 7B family):**

| Model | Role | HuggingFace ID |
|---|---|---|
| OLMo-2-1124-7B | Base (pre-trained) | `allenai/OLMo-2-1124-7B` |
| OLMo-2-1124-7B-SFT | After SFT only | Intermediate checkpoint (if available) |
| OLMo-2-1124-7B-DPO | After DPO | Intermediate checkpoint (if available) |
| OLMo-2-1124-7B-Instruct | Full post-training | `allenai/OLMo-2-1124-7B-Instruct` |

**Extended comparison (OLMo 3 7B, if OLMo 2 intermediates unavailable):**

| Model | Role | HuggingFace ID |
|---|---|---|
| Olmo-3-1025-7B | Base | `allenai/Olmo-3-1025-7B` |
| Olmo-3-7B-Instruct-DPO | DPO path | `allenai/Olmo-3-7B-Instruct-DPO` |
| Olmo-3-7B-Instruct | Full Instruct | `allenai/Olmo-3-7B-Instruct` |

**Rationale for 7B:** Large enough for meaningful post-training effects, small enough for SAE training on academic compute. 32 layers provides good depth resolution for layer-wise analysis.

### 3.2 SAE Training

**Approach A (preferred): Train matched SAEs.**

Train SAEs on both the base and post-trained models using identical hyperparameters:
- Architecture: ReLU SAE (to match our polyhedral theory), expansion factor 8x (d_sae = 32,768 for d_model = 4096)
- Training data: 100M tokens from a neutral corpus (e.g., C4 or Dolma validation split)
- Layers: all 32, but focus analysis on layers {0, 4, 8, 12, 16, 20, 24, 28, 31} (every 4th + first/last)
- Framework: Language-Model-SAEs or SAE Lens
- Estimated cost: ~2-4 GPU-days per model per layer on A100. For 9 layers x 2 models = ~36-72 GPU-days total.

**Approach B (faster, less clean): Use base-model SAE as fixed probe.**

Train SAE only on the base model. Apply it to post-trained activations (analogous to our Pythia fixed-probe approach). This directly measures how well the base geometric structure describes the post-trained model.
- Pro: half the SAE training cost; directly comparable to Pythia results.
- Con: cannot discover genuinely new post-training features; biased toward finding "shallow" effects.

**Recommendation: Do both.** Approach B first (fast, answers RQ1/RQ3/RQ4 immediately), then Approach A for RQ2/RQ5.

### 3.3 Evaluation Data

Three carefully controlled datasets:

**Dataset 1: Neutral text (control)**
- 10,000 tokens from C4/Dolma validation set
- Purpose: baseline geometry measurement where base and post-trained models should behave similarly
- Both models should produce similar activations on this data

**Dataset 2: Instruction-following prompts**
- 2,000 prompts from Alpaca/Dolci-style instruction data
- Purpose: measure geometry on data where post-training has maximum effect
- Include variety: factual QA, creative writing, code generation, multi-step reasoning

**Dataset 3: Safety-critical prompts**
- 1,000 prompts from standard red-teaming datasets (AdvBench, HarmBench, or similar)
- Plus 1,000 benign prompts that superficially resemble harmful ones (over-refusal probes)
- Purpose: isolate safety-specific geometric changes
- This is where refusal direction / safety feature analysis is most relevant

### 3.4 Metrics

**Metric Group 1: Arrangement Structure (per layer)**

| Metric | What it measures | Expected sensitivity |
|---|---|---|
| Convexity | Are SAE feature regions still half-spaces? | Low (architectural) |
| Boundary linearity | Are feature boundaries still hyperplanes? | Low (architectural) |
| Intrinsic dimension (Two-NN) | How many effective dimensions? | Medium |
| Polytope count (unique sparsity patterns) | How many occupied regions? | High |
| L0 sparsity | Features active per token | High |
| Dead feature fraction | Unused SAE capacity | Medium |

**Metric Group 2: Arrangement Similarity (base vs post-trained)**

| Metric | What it measures |
|---|---|
| Feature direction cosine similarity | Are the same directions used? |
| Feature overlap (activation correlation) | Do the same tokens activate the same features? |
| var_explained (base SAE on post-trained activations) | How well does base geometry describe post-trained space? |
| Matched feature fraction | What fraction of base features have a post-trained counterpart (cosine > 0.8)? |
| New feature fraction | What fraction of post-trained features have no base counterpart? |

**Metric Group 3: Safety-Specific**

| Metric | What it measures |
|---|---|
| Refusal direction projection | Magnitude of Arditi et al. refusal direction in base vs post-trained |
| Safety feature sparsity | How many SAE features mediate refusal? |
| Safety feature provenance | Are safety features expressible in the base-model SAE basis? |
| Polytope occupancy shift on harmful prompts | Do harmful prompts land in different polytopes post-training? |

### 3.5 Layer Analysis Strategy

OLMo 2 7B has 32 layers. Full analysis of all 32 is expensive. Strategy:

**Phase 1 (pilot):** Layers {0, 8, 16, 24, 31} (5 layers, even spacing + boundaries)
- Fast turnaround, identifies which layers show the most change
- Estimated: 1-2 GPU-days with pre-trained SAEs

**Phase 2 (targeted):** Add layers around the most-changed regions from Phase 1
- If layers 24-31 show the most change, add {20, 22, 26, 28, 30}
- If the change is uniform, sample every 4th layer

**Phase 3 (full):** All 32 layers if the story warrants it

### 3.6 Controls

**Control 1: Two base-model checkpoints.** Compare geometry between two late pre-training checkpoints (e.g., step 900k vs step 1000k) to establish the baseline rate of geometric change during pre-training. Post-training changes should exceed this baseline.

**Control 2: Random weight perturbation.** Add Gaussian noise to base model weights (calibrated to match the L2 norm of the base->post-trained weight diff) and measure geometric change. This controls for whether observed changes are specific to post-training or generic consequences of weight perturbation.

**Control 3: Different post-training recipes.** Compare OLMo Instruct vs OLMo Think vs OLMo RL Zero (all from same base). If geometric changes are recipe-specific, this is strong evidence for meaningful structure.

**Control 4: Prompt-type interaction.** Measure all metrics separately on neutral, instruction, and safety prompts. If geometric changes are prompt-dependent (e.g., only visible on safety prompts), this localizes the effect.

### 3.7 Compute Budget Estimate

| Component | GPU-hours (A100) | Cost @ $2/hr |
|---|---|---|
| SAE training (Approach B: base only, 9 layers) | 72-144 | $144-288 |
| SAE training (Approach A: base + post-trained, 9 layers) | 144-288 | $288-576 |
| Activation extraction (2 models x 9 layers x 3 datasets) | 18-36 | $36-72 |
| Geometric analysis (CPU-heavy, minimal GPU) | 10-20 | $20-40 |
| **Total (Approach B only)** | **~100-200** | **$200-400** |
| **Total (both approaches)** | **~250-500** | **$500-1000** |

This is within academic compute budgets. Modal T4s could reduce cost 3-4x but increase wall time.

---

## 4. Predictions

### 4.1 Scenario A: Post-Training is "Shallow" (Cosmetic)

Post-training shifts activation distributions within the existing polytope structure but does not fundamentally alter the hyperplane arrangement.

**Predictions under Scenario A:**
- var_explained (base SAE on post-trained activations) > 0.8 on neutral text
- Feature direction cosine similarity > 0.9 for >80% of features
- Convexity and linearity metrics are indistinguishable between base and post-trained
- Intrinsic dimension is unchanged (+/- 5%)
- Safety features ARE expressible as sparse combinations of base features (refusal direction has high projection onto base SAE)
- Polytope occupancy shifts on safety prompts but the polytopes themselves are the same
- L0 changes are small (<20%)

**Implications if true:** Post-training is a "distribution shift within fixed geometry." Safety is a surface-level behavioral pattern, not a deep structural change. Jailbreaks work because they shift activations back into the base-model distribution, which occupies the same polytopes. Alignment is inherently fragile.

### 4.2 Scenario B: Post-Training is "Deep" (Structural)

Post-training creates new hyperplanes, destroys old ones, or substantially reorients the arrangement.

**Predictions under Scenario B:**
- var_explained (base SAE on post-trained activations) < 0.5 even on neutral text
- Feature direction cosine similarity < 0.7 for >30% of features
- New features emerge in post-trained SAE with no base counterpart (>20% new features)
- Intrinsic dimension changes significantly (>15% shift in some layers)
- Safety features are NOT well-described by base SAE; they require genuinely new hyperplanes
- L0 changes substantially (>30%)
- The changes are layer-dependent (concentrated in specific layers)

**Implications if true:** Post-training fundamentally restructures the model's computational geometry. Safety behaviors have deep geometric grounding. However, this also means post-training is more expensive than necessary if most of training is geometric consolidation (our Pythia finding).

### 4.3 Most Likely Scenario: "Selectively Deep"

Based on the literature (especially Arditi et al. on refusal directions, Du et al. on directional distinctness):

**Predictions under Scenario C (our best guess):**
- Arrangement structure (convexity, linearity) is preserved -- still polyhedral (architectural property)
- Most features are preserved (>70% high cosine similarity) -- the "vocabulary" of features is mostly shared
- But a small set of features (5-15%) are genuinely new or substantially rotated -- these mediate safety and instruction-following
- Changes are concentrated in late-middle to output-adjacent layers (layers 20-31 in OLMo 2 7B)
- Intrinsic dimension decreases slightly in late layers (post-training specializes representations)
- Safety features form a low-dimensional subspace (1-5 dimensions) within the full arrangement
- Different post-training recipes (DPO vs RLVR) produce different geometric signatures: DPO is more targeted (fewer changed features), RLVR is broader

This is the "surgical edit" hypothesis: post-training adds a small number of safety hyperplanes and slightly adjusts existing ones, without rebuilding the whole arrangement.

---

## 5. Connections to Existing Results

### 5.1 Pythia Training Dynamics

Our Pythia work found that geometric consolidation takes 84% of pre-training compute while capabilities emerge in 16%. The pre-train/post-train transition is a second boundary: does it trigger another consolidation wave?

**Specific connection:** In Pythia, the epoch boundary (step ~99k) triggered rapid alignment in 4/6 layers. The SFT/DPO boundary is an analogous distribution shift. If we see rapid geometric change at the post-training boundary, this supports a general principle: distribution shifts trigger geometric consolidation.

**Layer ordering prediction:** In Pythia, output-adjacent layers (L5) aligned latest and were most volatile. In OLMo post-training, we predict output-adjacent layers (L28-L31) will show the most geometric change, because they are most directly shaped by the post-training loss.

### 5.2 Polyhedral Cone Hypothesis

Our Phase 2 results on GPT-2 Small established convexity 0.943 and linearity 0.999. If post-training preserves these values (Prediction 4.1/4.3), this strengthens the claim that polyhedral structure is architectural. If it doesn't, we learn something new: that the arrangement can be structurally modified by fine-tuning.

**Specific test:** Run the P1-P6 prediction suite (THEORY.md Section 3) on both base and post-trained OLMo. This is a direct replication + extension of Phase 2.

### 5.3 MoE Superposition Paper

The MoE paper (arXiv:2510.23671v2) found that network sparsity (not feature sparsity) drives monosemanticity. Post-training typically increases L0 sparsity. If post-training reduces superposition (more monosemantic features, fewer active per token), this parallels the MoE finding and suggests a general principle: any mechanism that increases routing selectivity reduces superposition.

**Testable:** Compare L0, dead feature fraction, and polytope count between base and post-trained OLMo. If post-training increases sparsity and reduces polytope count, it's behaving like moving along the "network sparsity" axis toward MoE-like behavior.

### 5.4 Capability-Geometry Dissociation

We found negative correlation between SAE alignment and capability in Pythia. Post-training adds capabilities (instruction following, safety) while potentially reorganizing geometry. Does this dissociation persist? Or does post-training break the pattern because it explicitly optimizes for behavioral capabilities rather than next-token prediction?

---

## 6. Risks and Alternatives

### 6.1 Risk: No OLMo SAEs Exist

**Severity:** Medium. Mitigated by training our own.
**Mitigation:** Use SAE Lens or Language-Model-SAEs framework. Start with a single layer (layer 16, middle) to validate the pipeline before scaling. If SAE training on OLMo 2 7B proves too expensive, fall back to OLMo 2 1B (same architecture family, 16 layers, d_model=2048).

### 6.2 Risk: Post-Training Changes Are Too Small to Detect

**Severity:** Medium. If the weight diff is tiny, geometric changes may be within measurement noise.
**Mitigation:** (a) Use safety-specific prompts where behavioral differences are maximized; (b) compute the weight-space L2 distance between base and post-trained to calibrate expectations; (c) use the random perturbation control (3.6 Control 2) to establish noise floor.
**What falsification looks like:** If base-SAE var_explained on post-trained activations is >0.95 across all layers and all prompt types, and no feature shows cosine similarity <0.95, then post-training genuinely is cosmetic at the geometric level. This would be a meaningful negative result worth publishing.

### 6.3 Risk: Fixed-Probe Bias (Same as Pythia)

**Severity:** High for Approach B, mitigated by Approach A.
**Problem:** A base-model SAE is biased toward finding that post-training is "shallow" because it cannot represent genuinely new features. The var_explained metric will undercount new structure.
**Mitigation:** Approach A (train both SAEs) is essential for RQ2 and RQ5. Approach B is a fast first pass, not the final answer.

### 6.4 Risk: OLMo 2 Intermediate Post-Training Checkpoints Unavailable

**Severity:** Medium. We need SFT-only and DPO-only checkpoints to answer RQ5.
**Mitigation:** OLMo 3 explicitly releases intermediate post-training checkpoints. Fall back to OLMo 3 7B if OLMo 2 intermediates are not publicly available. Alternatively, we can perform our own SFT/DPO on the base model to create controlled intermediates (more compute, but more control).

### 6.5 Risk: Compute Exceeds Budget

**Severity:** Low-Medium. SAE training on 7B models is non-trivial.
**Mitigation:** (a) Start with Approach B (base SAE only, ~$200-400); (b) Use OLMo 2 1B as a pilot model (~$50-100 total); (c) Focus on 5 layers initially; (d) Use Modal T4s to reduce cost.

### 6.6 Risk: Results Are Model-Specific

**Severity:** Medium. OLMo-specific findings may not generalize.
**Mitigation:** (a) OLMo's architecture is standard transformer, so findings likely generalize; (b) if results are striking, replicate on Llama 3.1 8B (Llama Scope SAEs already exist for base model); (c) the Pythia results already establish cross-model geometric patterns.

### 6.7 What Would Falsification Look Like?

The strongest form of falsification: post-training changes are indistinguishable from random weight perturbation of equal magnitude (Control 2). This would mean there is no meaningful geometric signature of alignment, and the behavioral changes are achieved through a mechanism that our metrics cannot capture (e.g., pure attention pattern changes with no residual stream signature).

A weaker falsification: the polyhedral structure itself breaks down in post-trained models (convexity <0.7, linearity <0.8). This would falsify the architectural claim from our Pythia work and suggest that fine-tuning can alter the fundamental geometric form, not just the feature assignment.

---

## 7. Timeline and Milestones

| Phase | Duration | Deliverable |
|---|---|---|
| **Phase 0: Setup** | 1 week | OLMo 2 7B loaded on Modal; activation extraction pipeline validated; evaluation datasets prepared |
| **Phase 1: Fixed-probe analysis** | 2 weeks | Train base-model SAE (1 layer pilot -> 5 layers); apply to both models; RQ1/RQ3/RQ4 preliminary answers |
| **Phase 2: Matched SAE training** | 2-3 weeks | Train post-trained SAEs at 5 layers; feature matching analysis; RQ2 answered |
| **Phase 3: Safety-specific analysis** | 1-2 weeks | Refusal direction decomposition; safety feature provenance; RQ2 deepened |
| **Phase 4: Multi-recipe comparison** | 2 weeks | OLMo 3 Instruct vs Think vs RL Zero comparison; RQ5 answered |
| **Phase 5: Write-up** | 2 weeks | Full results document; figures; paper section draft |
| **Total** | ~10-12 weeks | |

### Decision Gates

**After Phase 1:** If base-SAE var_explained on post-trained activations is >0.9 for all layers, post-training is shallow at the SAE level. Pivot to finer-grained analysis (individual feature tracking, attention pattern geometry) rather than arrangement-level metrics.

**After Phase 2:** If matched feature fraction is >0.9, the story is "post-training preserves arrangement, adjusts distribution." If <0.7, the story is "post-training restructures." Adjust Phase 3-4 framing accordingly.

---

## 8. References

1. Arditi et al. (2024). "Refusal in Language Models Is Mediated by a Single Direction." arXiv:2406.11717.
2. Arditi et al. (2024). "Steering Language Model Refusal with Sparse Autoencoders." arXiv:2411.11296.
3. Du et al. (2025). Post-training refusal direction distinctness from base models.
4. Ali et al. (2025). RLHF-induced saturation and steering asymmetry.
5. Wollschlager et al. (2025). "Concept cones" -- multi-axis refusal geometry.
6. Kerl (2025). "Evaluation of Sparse Autoencoder-based Refusal Features in LLMs." TU Wien.
7. SAFER (arXiv:2507.00665). SAE-based safety probing of reward models.
8. Park et al. (2024). "The Linear Representation Hypothesis and the Geometry of Large Language Models." ICML 2024.
9. Wehner et al. (2025). "Representation Engineering for LLMs." arXiv:2502.19649.
10. OLMo 2 Team (2024). "OLMo 2: The best fully open language model to date." arXiv:2501.00656.
11. OLMo 3 Team (2025). "OLMo 3: Charting a path through the model flow." AI2 Blog.
12. Hindupur et al. (2025). "Projecting Assumptions: Duality Between SAEs and Concept Geometry." arXiv:2503.01822.
13. Black et al. (2022). "Interpreting Neural Networks through the Polytope Lens." arXiv:2211.12312.
14. Our prior work: ge-y3a (polyhedral cone hypothesis), ge-plx (Pythia dynamics), ge-97d (capability-geometry correlation), ge-341 (multi-layer dynamics).
15. MoE superposition paper (arXiv:2510.23671v2). "Sparsity and Superposition in Mixture of Experts."
16. arXiv:2505.17306. "Refusal Direction is Universal Across Safety-Aligned Languages."
17. arXiv:2602.11180. "Mechanistic Interpretability for LLM Alignment: Progress, Challenges, and Future Directions."
18. Prieto et al. (2026). "From Data Statistics to Feature Geometry." arXiv:2603.09972.
