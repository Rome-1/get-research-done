# Geometry of Post-Training in Activation Space

**Direction:** ge-4t5 (broader post-training geometry, not model-specific)
**Status:** Research plan
**Date:** 2026-04-01
**Prerequisites:** Polyhedral Cone Hypothesis (confirmed on GPT-2 Small), Pythia training dynamics (non-sequential alignment, capability-geometry dissociation), MoE superposition findings

---

## 0. Motivation

Post-training (RLHF, DPO, constitutional AI, safety fine-tuning) is how base
models become deployed products. Yet we understand almost nothing about what
these procedures do to the *geometry* of internal representations. We know:

- Base model residual streams live on unions of polyhedral cones defined by
  SAE feature hyperplanes (our Phase 2 result on GPT-2 Small).
- Training dynamics show that geometric consolidation is dissociated from
  capability acquisition (our Pythia dynamics result).
- A single "refusal direction" can disable safety in 13 models (Arditi et al.
  2024), but recent work shows refusal is actually multi-dimensional concept
  cones (Wollschlager et al. 2025).
- Representation engineering can read and control high-level concepts (Zou et
  al. 2023), and circuit breakers operate at the representation level (Zou et
  al. 2024).

**The gap:** Nobody has connected the polyhedral/hyperplane arrangement
framework to post-training. If base models have a specific polytope structure,
what does RLHF/DPO do to that structure? Is alignment a geometric concept? Can
we measure how "deep" alignment goes by measuring how much of the arrangement
changes?

---

## 1. Literature Survey

### 1.1 Representation Engineering and Activation Steering

**Zou et al. (2023).** "Representation Engineering: A Top-Down Approach to AI
Transparency." arXiv 2310.01405. Introduces RepE: population-level
representations as the unit of analysis. Shows that concepts like honesty,
harmlessness, power-seeking are represented as directions in activation space.
Provides reading vectors (probing) and control vectors (steering) for these
concepts. Key insight: concepts are linearly accessible in intermediate layers.

**Zou et al. (2024).** "Improving Alignment and Robustness with Circuit
Breakers." arXiv 2406.04313. Extends RepE to interrupt harmful outputs by
controlling the representations responsible for them, rather than training
refusal. Works on text and multimodal models. Demonstrates that
representation-level interventions can be more robust than behavioral
fine-tuning. Later shown to be vulnerable to multi-turn jailbreaks (arXiv
2507.02956), suggesting the representation-level intervention is not yet
complete.

**Survey:** Xu et al. (2025). "Representation Engineering for Large-Language
Models: Survey and Research Challenges." arXiv 2502.17601. Comprehensive
overview of the RepE landscape as of early 2025.

### 1.2 Refusal Vectors and the Geometry of Safety

**Arditi et al. (2024).** "Refusal in Language Models Is Mediated by a Single
Direction." NeurIPS 2024, arXiv 2406.11717. Across 13 open-source chat models
(up to 72B), finds a single direction in residual stream space such that:
ablating it disables refusal; adding it induces refusal on benign inputs.
Proposes directional ablation as a white-box jailbreak. This is the strongest
evidence that alignment has a simple geometric signature.

**Wollschlager et al. (2025).** "The Geometry of Refusal in Large Language
Models: Concept Cones and Representational Independence." ICML 2025, arXiv
2502.17420. Challenges the single-direction finding: uncovers multiple
independent refusal directions and multi-dimensional concept *cones* mediating
refusal. Introduces "representational independence" (not just orthogonality)
as the correct criterion. Shows refusal geometry is polyhedral-conic rather
than one-dimensional. **This is the closest existing work to our research
program** -- they find cones, we find polyhedral cones. The connection must be
made explicit.

**arXiv 2505.17306.** "Refusal Direction is Universal Across Safety-Aligned
Languages." Shows the refusal direction is language-invariant, suggesting it is
a deep geometric feature, not a surface-level heuristic.

**arXiv 2601.08489.** "Surgical Refusal Ablation: Disentangling Safety from
Intelligence via Concept-Guided Spectral Cleaning." Proposes more targeted
ablation methods that preserve capability while removing refusal, suggesting
the refusal geometry is partially separable from the capability geometry.

### 1.3 The Linear Representation Hypothesis

**Park, Choe & Veitch (2024).** "The Linear Representation Hypothesis and the
Geometry of Large Language Models." ICML 2024, arXiv 2311.03658. Formalizes
what "linear representation" means using counterfactuals. Proves that linear
probing and model steering are dual to two formalizations of linear
representation. Identifies a non-Euclidean inner product that respects language
structure. **Critical theoretical foundation:** if post-training preserves
linearity of representations, then the hyperplane arrangement framework
applies to aligned models too.

**Hindupur et al. (2025).** "Projecting Assumptions: The Duality Between SAEs
and Concept Geometry." NeurIPS 2025, arXiv 2503.01822. Shows ReLU/JumpReLU
SAE receptive fields are half-spaces; TopK SAEs produce hyperpyramids. Does not
develop hyperplane arrangement composition, but establishes the mathematical
foundation we build on.

### 1.4 Jailbreak Geometry and Safety Mechanisms

**Wei et al. (2024).** "How Alignment and Jailbreak Work: Explain LLM Safety
through Intermediate Hidden States." EMNLP Findings 2024, arXiv 2406.05644.
Key finding: LLMs learn ethical concepts during *pre-training*, not alignment.
Alignment associates early-layer ethical classification with middle-layer
negative emotions and late-layer rejection tokens. Jailbreaks disrupt this
association chain. Implication for our work: post-training may not add new
hyperplanes but rather strengthen/reweight connections between existing
arrangement regions.

**Li et al. (2024).** "JailbreakLens: Interpreting Jailbreak Mechanism in the
Lens of Representation and Circuit." arXiv 2411.11114. Jailbreaks amplify
affirmative-response components while suppressing refusal components. Despite
shifting representations toward safe-looking clusters, jailbreaks produce
abnormal activation patterns detectable by circuit analysis. Implication: the
geometric signature of jailbreaks is not just about where activations are, but
about which polytope faces they occupy.

**Zhou et al. (2024).** "Towards Understanding Jailbreak Attacks in LLMs: A
Representation Space Analysis." arXiv 2406.10794. Analyzes jailbreaks through
the learned representation space of victim LLMs.

### 1.5 Base vs. Aligned Model Representations

**Panickssery et al. (2023).** "Steering Llama 2 via Contrastive Activation
Addition." arXiv 2312.06681. Directly compares Llama 2 Base and Chat
representations. Finds: steering vector similarity decays across layers except
for a peak at layers 7-15; representation vectors match until layer 11, then
diverge, with an intersection again at layer 15. RLHF has minimal effect on
middle-layer representations. This is consistent with "shallow alignment" --
post-training primarily affects late layers.

**LessWrong analysis (2024).** "Comparing representation vectors between llama
2 base and chat." Extends the layer-by-layer comparison, confirms that RLHF
effects concentrate in specific layer ranges.

### 1.6 SAEs and Post-Training

**Ferrao et al. (2025).** "The Anatomy of Alignment: Decomposing Preference
Optimization by Steering Sparse Features." arXiv 2509.12934. Uses SAE features
as an interface for alignment. Key finding: models learn to reward *stylistic
presentation* as a proxy for quality, disproportionately relying on
style/formatting features over alignment-relevant features (honesty, safety).
**Direct implication for our work:** DPO may preferentially modify
style-related hyperplanes while leaving safety-relevant geometry largely
unchanged.

**AlignSAE (2025).** arXiv 2512.02004. Proposes post-training SAEs to align
feature space with human-defined concepts. Standard SAEs have no incentive to
align features with human concepts; this work adds that incentive.

**OpenAI (2025).** "Debugging misaligned completions with sparse-autoencoder
latent attribution." Uses SAE latents to debug alignment failures, suggesting
SAE features can reveal the geometry of misalignment.

### 1.7 MoE and Superposition

**Allenzhu et al. (2025).** "Sparsity and Superposition in Mixture of
Experts." arXiv 2510.23671. MoEs exhibit 2-4x less superposition than dense
models. Greater network sparsity (ratio of active to total experts) yields
greater monosemanticity. Experts specialize by aligning routing cones to
features they represent monosemantically. **Implication:** MoE post-training
may operate on a fundamentally different geometry (less superposed, more
separated cones) than dense model post-training.

### 1.8 Polyhedral and Tropical Geometry of Neural Networks

**Black et al. (2022).** "Interpreting Neural Networks through the Polytope
Lens." arXiv 2211.12312. Polytopes in GPT-2 MLPs. Does not connect to SAEs.

**Balestriero & Baraniuk (2018).** "A Spline Theory of Deep Networks." ICML
2018. Deep ReLU networks are spline operators tessellating input space via
hyperplane arrangements. General theory, not transformer/SAE-specific.

**Brandenburg, Loho & Montufar (2024).** "Real Tropical Geometry of Neural
Networks." arXiv 2403.11871. Activation polytope normal fan captures
classification combinatorics; subfan structure. Connects to our framework
through tropical polynomial interpretation of ReLU SAE encoder.

**TAG-DS 2025 work.** Topological signatures of ReLU activation region
decomposition, including persistent homology of polyhedral complex structure.

---

## 2. Research Questions

### 2.1 Core Geometric Questions

**Q1: What geometric signatures distinguish post-trained from base models?**
Specifically: does the hyperplane arrangement (defined by SAE features) change
after RLHF/DPO? If so, how -- new hyperplanes? Rotated hyperplanes? Same
arrangement with shifted activation distribution?

**Q2: Is "alignment" a geometric concept?**
The polyhedral cone hypothesis says activations live on polytope unions. If
alignment is a geometric property, it should correspond to a measurable change
in the arrangement. Three possibilities:
- (a) New polytope boundaries: post-training adds hyperplanes that separate
  "aligned" from "unaligned" behavior.
- (b) Redistributed activation mass: same polytopes, but activations shift to
  different regions (aligned responses occupy different polytopes than
  unaligned ones).
- (c) Rotated arrangement: existing hyperplanes tilt to better separate safe
  from unsafe behaviors.

**Q3: Do refusal behaviors correspond to specific hyperplane arrangements?**
Arditi (2024) found a single refusal direction; Wollschlager (2025) found
multi-dimensional concept cones. Our framework predicts that refusal
corresponds to a specific *face* of the hyperplane arrangement -- the
intersection of multiple feature half-spaces. The refusal "direction" is the
normal to this face. Multiple refusal directions would correspond to different
faces of the arrangement.

**Q4: How do different post-training methods leave different geometric
signatures?**
- RLHF (reward model + PPO): may reshape many hyperplanes (global optimization
  pressure).
- DPO (direct preference): may create sharper boundaries between
  preferred/dispreferred (pairwise contrast).
- Constitutional AI: may induce hierarchical arrangement changes (principles
  organize hyperplanes).
- Safety fine-tuning (circuit breakers): may add specific blocking hyperplanes
  without changing the rest.

**Q5: Is the "alignment tax" visible geometrically?**
If post-training reduces the number of effective polytopes (fewer computational
regimes), this could explain capability loss. Alternatively, if post-training
adds hyperplanes that fragment existing polytopes, it could increase capacity
but reduce coherence.

### 2.2 Depth-of-Alignment Questions

**Q6: What does "shallow alignment" look like geometrically vs "deep
alignment"?**
Shallow alignment (behavioral filter, easily jailbroken) should show:
- Changes concentrated in late layers only.
- Refusal geometry is a small perturbation of base geometry.
- A single ablatable direction suffices to undo it.

Deep alignment (value internalization, robust) should show:
- Changes propagated through many layers.
- The arrangement itself is restructured, not just augmented.
- Multiple independent directions needed to undo it (high-dimensional refusal
  cone).

**Q7: Does the layer-dependent alignment wave we observed in Pythia training
dynamics have a post-training analogue?**
Our finding: during pre-training, layers align non-sequentially with the epoch
boundary as a critical event. Question: does RLHF/DPO induce a similar
layer-dependent geometric transition? Which layers change first?

### 2.3 Safety-Relevant Questions

**Q8: Do jailbreaks exploit geometric structure?**
If refusal corresponds to a polytope face, do jailbreaks work by:
- (a) Steering activations to a different polytope (one where refusal features
  are inactive).
- (b) Collapsing the refusal face (reducing its dimension).
- (c) Moving activations to the boundary between polytopes (ambiguous region).

**Q9: Can we predict jailbreak vulnerability from arrangement geometry?**
If the refusal polytope face has low codimension (easily accessible from many
directions), the model is geometrically vulnerable. If it has high codimension
(deeply embedded), the model is robust.

**Q10: Does the MoE architecture provide inherently more robust alignment
geometry?**
MoEs have 2-4x less superposition. If alignment geometry benefits from lower
superposition (less interference between safety features and capability
features), MoE alignment may be geometrically deeper.

---

## 3. Theoretical Framework

### 3.1 Extending the Polyhedral Cone Hypothesis to Post-Training

**Definition.** Let A_base = {H_1, ..., H_m} be the hyperplane arrangement
defined by the SAE features of a base model at a given layer. Each H_k is the
boundary {x : w_k . x + b_k = 0} of feature k's half-space. The arrangement
partitions R^d into at most sum_{i=0}^d C(m,i) polytopes.

**Post-training transformation.** After RLHF/DPO, we obtain a new model whose
residual stream activations define a new arrangement A_post. (We measure this
by training a new SAE on the post-trained model.) We formalize three possible
relationships:

**Case 1: Distributional shift (same arrangement).**
A_post = A_base (same hyperplanes), but the distribution P_post over polytopes
differs from P_base. Aligned behavior corresponds to activations concentrating
on a subset of "safe" polytopes. Prediction: SAE features are nearly identical
between base and aligned models; only activation frequencies change.

**Case 2: Arrangement perturbation.**
A_post is a small perturbation of A_base: hyperplanes rotate by small angles,
preserving combinatorial type (same polytope adjacency structure). Aligned
behavior is encoded in the angular shifts. Prediction: SAE feature directions
have high cosine similarity (>0.9) between base and aligned models; the
arrangement's combinatorial type is preserved.

**Case 3: Arrangement restructuring.**
A_post has different combinatorial type from A_base: some polytopes merge,
others split, new faces appear. Aligned behavior requires fundamentally
different geometric decomposition. Prediction: SAE features differ
substantially; many features in aligned model have no base-model counterpart.

**Shallow alignment hypothesis:** Most current post-training produces Case 1 or
Case 2, concentrated in late layers. Evidence: Arditi's single refusal
direction (Case 1 -- one distributional shift); Llama 2 base/chat similarity
until layer 11 (Case 2 in late layers only).

**Deep alignment conjecture:** Robust alignment requires Case 3 in multiple
layers. If the arrangement itself is restructured, single-direction ablation
cannot undo it (you would need to restructure back, which requires many
directions).

### 3.2 The Refusal Face Hypothesis

We propose that the "refusal direction" of Arditi et al. is the normal vector
to a specific *face* of the hyperplane arrangement. Specifically:

Let F_refuse = intersection of half-spaces {H_k^+ : k in S} for some feature
subset S. This intersection is a polytope face. The refusal direction r is
(approximately) the vector pointing from the centroid of the non-refusal region
toward the centroid of F_refuse.

Wollschlager et al.'s multiple refusal directions correspond to *multiple
faces* of the arrangement, each mediating refusal in different contexts.
Their "concept cones" are exactly the polyhedral cones we predict.

**Testable prediction:** The refusal features (SAE features whose activation
pattern differs between base and aligned models on harmful inputs) should define
a low-dimensional face of the arrangement. The dimension of this face is the
"geometric depth of refusal."

### 3.3 Geometric Depth of Alignment

**Definition.** The *geometric depth* of a post-training intervention at layer
l is the fraction of hyperplanes in the arrangement that change by more than
threshold theta:

    depth(l, theta) = |{k : angle(w_k^base, w_k^post) > theta}| / m

Averaged across layers, this gives a scalar "alignment depth" score.

**Properties:**
- depth = 0: pure distributional shift (Case 1).
- depth << 1: shallow perturbation (Case 2).
- depth ~ 1: full restructuring (Case 3).

**Prediction:** RLHF/DPO typically gives depth < 0.1. Constitutional AI may
give higher depth. Circuit breakers give depth ~ 0 (they do not change the
model, only add a representation-level filter).

### 3.4 The Alignment Capacity Hypothesis

If a model has P effective polytopes (polytopes with non-negligible activation
mass), and alignment requires dedicating some polytopes to safety behavior, then
the "alignment tax" on capability is approximately:

    tax = P_safety / P_total

where P_safety is the number of polytopes whose primary function is safety-
related behavior (refusal, hedging, disclaimers). If P_safety is large relative
to P_total, alignment significantly reduces the model's capacity for useful
computation.

**Prediction for MoE models:** Because MoEs have more effective polytopes (less
superposition, more monosemantic experts), the alignment tax should be lower:
the same absolute number of safety polytopes constitutes a smaller fraction.
This could explain why MoE models are empirically easier to align without
capability loss.

---

## 4. Experimental Program

### 4.1 Model Selection

We need base/aligned model pairs from multiple families to ensure generality:

| Model Family | Base | Aligned | Size | Why |
|---|---|---|---|---|
| **Llama 3.1** | Llama-3.1-8B | Llama-3.1-8B-Instruct | 8B | Most studied; CAA/steering literature |
| **OLMo 2** | OLMo-2-7B | OLMo-2-7B-Instruct | 7B | Fully open (data + code); DPO+SFT pipeline |
| **Gemma 2** | gemma-2-9b | gemma-2-9b-it | 9B | Different architecture (GQA, different norm) |
| **Qwen 2.5** | Qwen2.5-7B | Qwen2.5-7B-Instruct | 7B | Non-Western training data, different alignment |
| **Mistral** | Mistral-7B-v0.3 | Mistral-7B-Instruct-v0.3 | 7B | Sliding window attention, different arch |
| **Mixtral (MoE)** | Mixtral-8x7B (base) | Mixtral-8x7B-Instruct | 47B (13B active) | MoE comparison point |

**SAE availability:** Pre-trained SAEs exist for Llama 3.1, Gemma 2, and
GPT-2. For others, we would train SAEs using the SAELens library (Bloom et al.)
or EleutherAI's SAE training code. Alternatively, we start with models that
have published SAEs and expand.

**Priority ordering:** Llama 3.1 first (most literature, best SAEs), then
Gemma 2, then OLMo 2 (fully open for reproducibility), then MoE comparison.

### 4.2 Measurement Framework

#### 4.2.1 Arrangement-Level Metrics (applied per layer)

1. **Feature direction similarity.** For each SAE feature k, compute
   cos(w_k^base, w_k^post). Distribution of cosine similarities characterizes
   whether the arrangement is preserved (Case 1/2) or restructured (Case 3).
   Challenge: SAE features between base and aligned models are not naturally
   paired. We pair them by maximum cosine similarity (Hungarian algorithm).

2. **Polytope occupancy divergence.** For a fixed prompt set, compute sparsity
   patterns (which polytope each token occupies) in both base and aligned
   models. Measure Jensen-Shannon divergence of the polytope occupancy
   distributions.

3. **Combinatorial type preservation.** Two arrangements have the same
   combinatorial type if their face lattices are isomorphic. Approximate this
   by comparing the co-activation matrices: C_ij = P(feature i and feature j
   both active). If C^base ~ C^post, the combinatorial type is preserved.

4. **Arrangement volume ratios.** For the top-k most frequent polytopes,
   estimate their volume (fraction of activation mass). Compare volume ratios
   between base and aligned models.

5. **Convexity and linearity (our Phase 2 metrics).** Verify that post-trained
   models still exhibit polyhedral geometry (convexity > 0.9, linearity > 0.95).
   If post-training breaks polyhedrality, the entire framework needs revision.

#### 4.2.2 Refusal-Specific Metrics

6. **Refusal face identification.** On harmful prompts, identify which SAE
   features are differentially active in aligned vs. base model. The
   intersection of their half-spaces defines the refusal face. Measure its
   dimension (number of defining features).

7. **Refusal face codimension.** How many independent directions are needed to
   move from a non-refusal polytope to the refusal face? Higher codimension =
   more robust refusal.

8. **Refusal direction decomposition.** Compute the Arditi refusal direction r.
   Project r onto SAE feature directions. If the refusal face hypothesis is
   correct, r should decompose as a sparse linear combination of a few SAE
   feature directions.

#### 4.2.3 Layer-Resolved Metrics

9. **Per-layer geometric depth.** depth(l, theta) as defined in Section 3.3,
   computed for each layer. Produces a "geometric depth profile" showing where
   in the network alignment changes concentrate.

10. **Layer-wise CKA/SVCCA.** Centered Kernel Alignment and Singular Vector
    Canonical Correlation Analysis between base and aligned model activations
    at each layer. These are standard tools; we extend them with
    arrangement-specific metrics above.

#### 4.2.4 Cross-Method Comparison Metrics

11. **Method signature.** For each post-training method (RLHF, DPO, SFT,
    constitutional), compute the geometric depth profile (metric 9). The
    "signature" is the vector of per-layer depths. We hypothesize different
    methods have distinct signatures.

12. **Alignment-capability Pareto frontier.** Plot geometric depth (metric 9)
    vs. capability retention (benchmarks). Does deeper geometric alignment
    correlate with greater capability loss?

### 4.3 Prompt Design

Three prompt categories, each with 500+ examples:

**Category A: Unambiguously harmful.** Requests that all aligned models should
refuse (violence, illegal activity, deception). These activate refusal
geometry. Source: HarmBench, AdvBench.

**Category B: Unambiguously benign.** Normal helpful-assistant prompts (coding,
math, creative writing). These should show minimal base/aligned divergence.
Source: Alpaca, ShareGPT.

**Category C: Boundary cases.** Prompts near the refusal boundary (dual-use
knowledge, sensitive topics, edge cases). These probe the geometry at the
decision surface. Source: XSTest, GrayArea benchmarks.

### 4.4 Experimental Phases

**Phase 1: Polyhedral validation on aligned models (1-2 weeks compute).**
Confirm that post-trained models still exhibit polyhedral geometry. Run our
Phase 2 metrics (convexity, linearity, boundary analysis) on Llama 3.1
Instruct and Gemma 2 IT. If polyhedrality breaks, reassess everything.

**Phase 2: Arrangement comparison (2-3 weeks compute).**
For Llama 3.1 base vs. instruct:
- Train matched SAEs (same architecture, same layer positions).
- Compute all arrangement-level metrics (4.2.1).
- Determine which case (1/2/3) applies at each layer.
- Produce the geometric depth profile.

**Phase 3: Refusal geometry (2-3 weeks compute).**
On Llama 3.1 Instruct:
- Compute refusal face (metric 6) using all three prompt categories.
- Decompose Arditi refusal direction into SAE features (metric 8).
- Test refusal face codimension (metric 7).
- Replicate on Gemma 2 IT and OLMo 2 Instruct.

**Phase 4: Cross-method comparison (3-4 weeks compute).**
Using OLMo 2 (fully open pipeline):
- Compare base, SFT-only, DPO, and full instruct checkpoints.
- Compute method signatures (metric 11).
- Determine whether different methods produce distinct geometric signatures.

**Phase 5: MoE comparison (2 weeks compute).**
Compare Mixtral base/instruct arrangement geometry with dense model findings.
Test the alignment capacity hypothesis (Section 3.4).

**Phase 6: Jailbreak geometry (2-3 weeks compute).**
On models from Phases 2-3:
- Run standard jailbreaks (GCG, AutoDAN, Crescendo, in-context) and measure
  which polytope the activations occupy during successful jailbreaks.
- Test whether jailbreaks systematically steer activations off the refusal
  face.
- Measure distance from refusal face for successful vs. failed jailbreaks.

### 4.5 Infrastructure Requirements

- **Compute:** A100/H100 GPUs for SAE training and activation extraction.
  No GPU work in this planning phase. Estimated total: ~200-400 GPU-hours
  across all phases.
- **SAE training:** SAELens or custom training code. Need matched SAEs for
  each base/aligned pair. Target: 32k-65k features, matching architecture to
  existing published SAEs where available.
- **Activation storage:** ~50-100GB per model per layer for 10k tokens with
  full activations. Total: ~2-5TB across all experiments.
- **Evaluation:** Standard benchmarks (MMLU, HumanEval, GSM8K, TruthfulQA)
  for capability measurement alongside geometric metrics.

---

## 5. Connection to Safety and Interpretability

### 5.1 Why This Matters Beyond Pure Geometry

**Alignment robustness diagnosis.** If we can measure the geometric depth of
alignment, we can predict which models are vulnerable to jailbreaks *without
running jailbreak attacks*. A model with depth < 0.05 at all layers is likely
to have single-direction refusal (easily ablated). A model with depth > 0.3
across multiple layers has restructured geometry (harder to undo).

**Post-training quality metric.** Current alignment evaluation relies on
behavioral benchmarks (HarmBench, TruthfulQA). Geometric depth provides a
*mechanistic* quality metric: how much did alignment actually change the model's
internal computation, vs. how much is it surface-level pattern matching?

**Jailbreak defense.** If jailbreaks exploit geometric structure (moving
activations off the refusal face), defenses can be designed geometrically:
monitor distance to the refusal face in real time, flag activations that
approach polytopes associated with harmful behavior. This is more principled
than output-level filtering.

**Alignment tax estimation.** The alignment capacity hypothesis (Section 3.4)
gives a geometric framework for estimating how much capability is sacrificed
for safety. This could guide architecture choices: if MoE models have lower
alignment tax, that is a concrete argument for MoE architectures in
safety-critical deployments.

### 5.2 Connection to Existing Safety Programs

- **Representation engineering (Zou et al.):** Our framework explains *why*
  RepE works: steering vectors move activations between polytopes. It also
  predicts limitations: steering cannot cross polytope boundaries that do not
  exist in the base model.
- **Circuit breakers (Zou et al.):** Circuit breakers add a representation-
  level filter. In our framework, this adds a *hyperplane* that separates
  harmful from safe regions. The vulnerability of circuit breakers to multi-turn
  attacks suggests this hyperplane is low-dimensional (easily circumvented).
- **Constitutional AI:** If constitutional training restructures the
  arrangement rather than just adding a filter, it should produce deeper
  geometric alignment. This is testable.
- **Anthropic's SAE interpretability program:** Their SAE-based attribution
  debugging aligns with our approach. Our contribution is the geometric
  framework that organizes individual feature findings into a structural theory.

### 5.3 Broader Implications

If alignment is fundamentally a geometric property of activation space, then:
1. **Alignment is measurable** without behavioral tests: measure the arrangement.
2. **Alignment is transferable** in principle: if two models have isomorphic
   arrangements, alignment of one implies alignment of the other (up to
   arrangement isomorphism).
3. **Alignment has a natural notion of "depth"** that is missing from current
   discourse, which conflates behavioral compliance with value internalization.

---

## 6. Risks and Falsification Criteria

### 6.1 What Would Falsify This Program

**F1: Post-trained models are not polyhedral.** If aligned model residual
streams have fundamentally non-linear geometry (convexity << 0.9, linearity
<< 0.95), the hyperplane arrangement framework does not apply. This would
require rethinking the entire approach. *Likelihood: LOW.* The polyhedral
structure is a mathematical consequence of ReLU SAE architecture, which does
not change with post-training.

**F2: Base and aligned models have identical arrangements (no geometric
signal).** If all metrics show no difference between base and aligned model
geometry, then alignment does not have a geometric signature, and this research
direction is vacuous. *Likelihood: LOW.* Arditi's refusal direction and
Wollschlager's concept cones already demonstrate geometric differences.

**F3: The arrangement changes are uninterpretable.** If arrangements differ but
the differences do not correspond to any meaningful alignment concept (refusal,
safety, helpfulness), then the geometric framework adds complexity without
insight. *Likelihood: MEDIUM.* This is the most realistic failure mode. The
geometry may be too high-dimensional to interpret, or the "meaningful" changes
may be swamped by random variation.

**F4: SAE quality gap between base and aligned models.** If SAEs trained on
aligned models are systematically worse (higher reconstruction error, more dead
features), the comparison is confounded. Post-training may change the
distribution in ways that make SAEs less effective, biasing all downstream
metrics. *Likelihood: MEDIUM.*

**F5: Results do not generalize across model families.** If the geometric
signatures are model-specific (different for Llama vs. Gemma vs. OLMo), there
is no general theory of post-training geometry. *Likelihood: MEDIUM.* This is
why we test multiple families.

### 6.2 Specific Go/No-Go Criteria

| Phase | Go criterion | No-go criterion |
|---|---|---|
| Phase 1 | Convexity > 0.85, linearity > 0.90 on aligned models | Convexity < 0.70 or linearity < 0.80 |
| Phase 2 | At least 2 of 5 arrangement metrics show statistically significant (p<0.01) base/aligned difference | No metric shows p<0.05 difference |
| Phase 3 | Refusal direction decomposes into <20 SAE features with R^2 > 0.8 | Refusal direction requires >100 features or R^2 < 0.5 |
| Phase 4 | Different post-training methods produce distinguishable geometric signatures (AUROC > 0.8) | All methods produce indistinguishable signatures |
| Phase 5 | MoE arrangement metrics differ from dense by >2 standard deviations on at least 2 metrics | No significant difference |

### 6.3 Other Risks

**Computational cost.** SAE training is expensive. If we cannot obtain quality
SAEs for all model pairs, the program scope must shrink. Mitigation: prioritize
models with pre-existing SAEs (Llama 3.1, Gemma 2).

**Feature matching problem.** Pairing SAE features between base and aligned
models is non-trivial. Maximum cosine similarity may be unreliable. Mitigation:
use multiple matching methods (cosine, activation correlation, semantic
similarity of feature descriptions) and report sensitivity to matching method.

**Dual-publication concern.** Wollschlager et al. (2025) already published on
"geometry of refusal" with "concept cones." We must clearly differentiate: they
study refusal specifically; we study the *entire arrangement* and how
post-training changes it. Refusal is one face of our framework.

**Ethical considerations.** Some experiments involve measuring how easily
alignment can be removed. This is dual-use research (understanding jailbreaks
to defend against them). We will follow responsible disclosure practices and
focus on defensive applications.

---

## 7. Timeline and Deliverables

| Month | Phase | Deliverable |
|---|---|---|
| 1 | Phase 1 | Polyhedral validation report for 2+ aligned models |
| 2-3 | Phase 2 | Arrangement comparison for Llama 3.1 base/instruct, geometric depth profiles |
| 3-4 | Phase 3 | Refusal face analysis, refusal direction decomposition into SAE features |
| 4-5 | Phase 4 | Cross-method comparison (OLMo 2 pipeline), method signatures |
| 5-6 | Phase 5-6 | MoE comparison, jailbreak geometry analysis |
| 6-7 | Write-up | Paper draft: "The Geometry of Alignment" |

**Paper target:** Top venue (ICML, NeurIPS, ICLR). The combination of
theoretical framework (polyhedral cones + post-training) with broad empirical
validation (multiple model families, multiple post-training methods) and
safety implications should be competitive.

---

## 8. Key References

1. Zou et al. (2023). "Representation Engineering." arXiv 2310.01405.
2. Zou et al. (2024). "Circuit Breakers." arXiv 2406.04313.
3. Arditi et al. (2024). "Refusal Mediated by a Single Direction." arXiv 2406.11717.
4. Wollschlager et al. (2025). "Geometry of Refusal: Concept Cones." arXiv 2502.17420.
5. Park, Choe & Veitch (2024). "Linear Representation Hypothesis." arXiv 2311.03658.
6. Hindupur et al. (2025). "SAEs and Concept Geometry." arXiv 2503.01822.
7. Wei et al. (2024). "Alignment and Jailbreak via Hidden States." arXiv 2406.05644.
8. Li et al. (2024). "JailbreakLens." arXiv 2411.11114.
9. Panickssery et al. (2023). "Steering Llama 2 via CAA." arXiv 2312.06681.
10. Ferrao et al. (2025). "Anatomy of Alignment." arXiv 2509.12934.
11. Allenzhu et al. (2025). "Sparsity and Superposition in MoE." arXiv 2510.23671.
12. Black et al. (2022). "Polytope Lens." arXiv 2211.12312.
13. Balestriero & Baraniuk (2018). "Spline Theory of Deep Networks." ICML 2018.
14. Brandenburg, Loho & Montufar (2024). "Real Tropical Geometry." arXiv 2403.11871.
15. Xu et al. (2025). "RepE Survey." arXiv 2502.17601.
16. arXiv 2505.17306. "Refusal Direction Universal Across Languages."
17. arXiv 2601.08489. "Surgical Refusal Ablation."
18. arXiv 2512.02004. "AlignSAE."
19. OpenAI (2025). "SAE Latent Attribution for Debugging Misalignment."
20. arXiv 2406.10794. "Jailbreak Representation Space Analysis."
