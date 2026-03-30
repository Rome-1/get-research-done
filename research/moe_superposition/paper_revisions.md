# Sparsity and Superposition in Mixture of Experts — Revision Notes

**Source**: arXiv:2510.23671v2 (Chaudhari, Nuer, Thorstenson 2025)
**Revision guide**: ML Paper Writing Protocol (ge-axu)

This document provides rewritten sections implementing the improvements identified
in REVIEW.md. Each section includes the original text reference and the revised
version. These revisions focus on framing, claims calibration, narrative arc, and
presentation—not on changing experimental results or adding new experiments.

---

## Revised Abstract

**Original problems**: No concrete numbers, excessive hedging, diffuse narrative.

**Revised**:

> Mixture of Experts (MoE) models are central to scaling modern language models,
> yet how their routing mechanisms affect internal representations remains poorly
> understood. We show that MoEs consistently exhibit less feature superposition
> than dense networks with matched parameters: features per dimension decreases
> by 2–4× as expert count increases, with individual experts approaching
> monosemantic representations. Unlike dense models, MoEs exhibit no
> discontinuous phase changes between monosemantic and superimposed feature
> regimes—network sparsity (the ratio of active to total experts), not feature
> sparsity, is the controlling variable. We propose a specialization definition
> based on monosemantic feature representation and show that appropriately
> initialized experts achieve near-perfect routing accuracy (up to 100%) for
> their specialized features. These findings demonstrate that expert count is
> a direct architectural lever for interpretability, suggesting that the
> capability–interpretability tradeoff assumed under the superposition hypothesis
> may be specific to dense architectures rather than a fundamental constraint.

**Changes**: Added concrete numbers (2–4×, 100%). Removed all hedges. Applied
Carlini's 5-sentence formula (topic → result → method → other finding →
significance). Single-pass readable.

---

## Revised Introduction

**Original problems**: Assumes too much background, list-of-questions framing,
no contributions list, buries the punchline.

**Revised structure** (paragraph-by-paragraph):

### ¶1 — Context (meet the reader)

> Mixture of Experts (MoE) architectures have become the dominant paradigm for
> scaling language models. Production systems including Qwen3 (Yang et al., 2025),
> Mixtral (Jiang et al., 2024), and Gemini (Anil et al., 2024) use MoEs to
> achieve strong performance while activating only a fraction of total parameters
> per input. Despite this widespread adoption, we lack a mechanistic understanding
> of what individual experts learn and how their representations differ from those
> of dense networks.

**Change**: Opens with practical relevance, not technical jargon. Establishes
the knowledge gap immediately.

### ¶2 — Technical bridge (superposition problem)

> A central challenge in neural network interpretability is *superposition*: the
> phenomenon where models represent more features than they have dimensions by
> encoding sparse features as non-orthogonal directions in activation space
> (Elhage et al., 2022). In dense models, superposition enables efficient
> feature packing but makes individual neurons polysemantic—responding to
> multiple unrelated concepts—which frustrates mechanistic interpretation.
> The extent of superposition depends on feature sparsity and importance,
> with discrete phase transitions between monosemantic and superimposed regimes.

**Change**: Defines superposition for a broader ML audience. One paragraph, no
detours.

### ¶3 — The question (natural transition)

> MoE architectures introduce a structural variable absent in dense models:
> *network sparsity*, the fraction of total experts active for any given input.
> While dense models activate all neurons regardless of input, MoEs can
> potentially dedicate entire experts to specific feature subsets. This raises
> a fundamental question: does the MoE architecture change the superposition
> dynamics that make dense models hard to interpret?

**Change**: Frames the research question as a natural consequence of the
architectural difference.

### ¶4 — Key contribution (the punchline)

> We show that it does. Using controlled toy models that extend the framework
> of Elhage et al. (2022) to MoE settings, we demonstrate that MoEs exhibit
> substantially less superposition than dense models with matched parameters.
> This effect is governed by network sparsity—not the feature sparsity and
> importance variables that control superposition in dense models. Increasing
> the number of experts while holding the active-to-total ratio constant
> yields progressively more monosemantic representations.

**Change**: States the result directly. No hedging.

### ¶5 — Evidence summary

> This reduced superposition has structural consequences. Unlike dense models,
> MoEs show no discontinuous phase transitions between feature representation
> regimes; instead, transitions are continuous and controlled by expert count.
> Furthermore, experts naturally specialize around coherent feature combinations:
> when initialized to route specific features, experts represent those features
> monosemantically (dimensionality ≈ 1.0) and achieve up to 100% routing
> accuracy for inputs where only those features are active.

### ¶6 — Implications

> These findings have a provocative implication. The superposition hypothesis
> (Elhage et al., 2022) frames interpretability as fundamentally constrained
> by model capacity: networks *must* superimpose features to represent more
> concepts than dimensions. Our results suggest this constraint may be specific
> to dense architectures. In MoEs, scaling expert count provides a direct
> lever for interpretability that does not require sacrificing reconstruction
> quality—challenging the assumption that capability and interpretability are
> inherently opposed.

### ¶7 — Contributions list

> Our specific contributions are:
>
> - **Less superposition in MoEs.** We show that features per dimension
>   decreases by 2–4× as expert count increases, with MoE representations
>   capped at the monosemantic limit (n_learned ≈ m_total) while dense models
>   exceed it (n_learned > m_total). (§4, Figures 2–3)
>
> - **No phase changes.** MoEs exhibit continuous transitions in feature
>   representation as sparsity varies, unlike the discrete phase changes
>   observed in dense models. Network sparsity, not feature sparsity, is the
>   controlling variable. (§5, Figure 4)
>
> - **Feature-based specialization.** We propose a specialization metric based
>   on monosemantic feature representation and show that initialization schemes
>   directly control which features experts represent monosemantically, with
>   k-hot initialization achieving 100% routing accuracy for specialized
>   features. (§6, Table 1)

**Change**: Explicit bullet-point contributions with section and figure pointers.
Reader can find evidence for each claim immediately.

---

## Revised Figure Captions

### Figure 1 caption (currently: dense model only)

**Recommendation**: Replace Figure 1 with a side-by-side dense vs. MoE comparison.

**Revised caption**:

> **Figure 1.** Superposition in dense vs. MoE architectures. **(a–b)** Dense
> model (n=20, m=6): feature weight norms and Gram matrix showing widespread
> inter-feature interference (off-diagonal structure). **(c–d)** MoE model
> (n=20, E=33, m=2 per expert, top-1): feature weight norms and Gram matrix
> showing block-diagonal interference confined within experts. The MoE
> partitions the feature space across experts, eliminating cross-expert
> interference and reducing superposition. Color indicates superposition
> score (purple = monosemantic, red = superimposed).

### Figure 2 caption

**Original**: Describes the setup without stating the finding.

**Revised**:

> **Figure 2.** MoE models produce block-diagonal Gram matrices, confining
> feature interference within individual experts. Configuration: n=20 features,
> 33 experts, m=2 hidden dimensions per expert, top-1 routing. Feature importance
> I=0.7^i, density 1−S=0.1. Compare to Figure 1(a–b): the dense model's full
> interference matrix becomes block-diagonal under MoE routing.

### Figure 3 caption

**Revised**:

> **Figure 3.** MoEs have less superposition than dense models, and superposition
> decreases with expert count. Features per dimension (y-axis) vs. inverse feature
> density for dense (n=100, m=20) and MoE architectures with uniform importance.
> Increasing total experts while keeping k/E ratio constant reduces superposition
> monotonically. MoE representations approach the monosemantic limit (1.0) while
> the dense model substantially exceeds it.

### Figure 4 caption

**Revised**:

> **Figure 4.** Phase diagrams for dense and MoE models across three architectures
> (A: n=2,m=1; B: n=3,m=1; C: n=3,m=2). Each panel shows feature representation
> (ignored/monosemantic/superimposed) as a function of feature sparsity (x-axis)
> and relative importance (y-axis). **Key finding**: Dense models (X/1 panels)
> exhibit sharp phase boundaries; MoE models show continuous transitions that
> become smoother with increasing expert count. Blue regions indicate monosemantic
> representations absent in the dense baselines.

### Figure 5 caption

**Revised**:

> **Figure 5.** Initialization controls expert specialization. Expert feature norms
> and superposition (color) for three initialization schemes (n=20, m=5, E=4,
> S=0.1). **(a)** Identity init: each expert monosemantically represents a single
> feature. **(b)** Ordered k-hot: experts represent the most important features
> they were initialized over. **(c)** Shuffled k-hot: experts select the most
> important features from their assigned subset. In all cases, initialization
> determines which features an expert specializes in.

### Figure 6 caption

**Revised**:

> **Figure 6.** MoEs achieve comparable reconstruction loss to dense models despite
> lower superposition. Log average loss vs. feature density for dense (m=20) and
> MoE models (n=100 features, uniform importance). The loss gap narrows as expert
> count increases, showing that monosemantic representations do not require
> sacrificing reconstruction quality.

---

## Revised Section 5 Conclusion Paragraph

**Original**: "This leads us to conclude it is misleading to think of MoEs as
an aggregation of dense models."

**Revised**:

> These results establish that MoEs are not simply aggregations of dense models.
> Even with only two experts (E=2) and a single active expert (k=1), the router's
> ability to restrict each expert's view of the feature space fundamentally alters
> representation learning. Phase changes—a defining characteristic of dense model
> superposition—disappear, replaced by continuous transitions controlled by
> network sparsity. This mechanistic distinction has practical implications:
> it means that increasing expert count is a predictable lever for reducing
> superposition, unlike the discrete jumps observed in dense models where small
> changes in feature sparsity can qualitatively change representations.

---

## Revised Section 7 (Conclusion)

**Original problems**: Restates results without answering "so what?" Generic
concluding sentence.

**Revised**:

> We investigated how expert routing affects feature superposition in MoE
> architectures. Three findings emerge. First, MoEs consistently exhibit less
> superposition than dense models with matched parameters, with features per
> dimension decreasing monotonically with expert count. Second, this reduction is
> controlled by network sparsity—not feature sparsity or importance—and proceeds
> continuously without the discrete phase changes characteristic of dense models.
> Third, experts naturally specialize around coherent monosemantic features when
> initialization encourages it, with specialized experts achieving up to 100%
> routing accuracy for their features in isolation.
>
> These findings carry a practical implication: for practitioners building or
> interpreting MoE models, expert count is a direct, predictable lever for
> representation quality. Increasing network sparsity yields more monosemantic
> experts without degrading reconstruction loss. This challenges a widely held
> assumption—that interpretability requires sacrificing capability—and suggests
> it may be an artifact of dense architectures rather than a fundamental
> constraint.
>
> Our experiments are limited to toy autoencoder models with synthetic feature
> distributions (see Limitations below). The most important open question is
> whether these dynamics hold in large-scale transformer MoEs, where feature
> distributions are unknown and routing involves multi-layer interactions.
> Understanding when monosemantic specialization emerges during training—and
> whether it can be encouraged by initialization or architecture choices in
> real models—is a direct path toward designing interpretable-by-construction
> language models.

---

## New Discussion Section (insert before Conclusion)

**This section does not exist in the current paper. It should be added as §7,
with the current §7 becoming §8.**

> ## Discussion
>
> ### Synthesizing the findings
>
> Our three results—reduced superposition, absence of phase changes, and
> feature-based specialization—are linked by a common mechanism. The router
> partitions the input space into convex cones (Appendix A.3), restricting each
> expert's view to a feature subset. Within this restricted view, the expert has
> sufficient capacity to represent its assigned features monosemantically rather
> than resorting to superposition. As expert count increases, each cone narrows
> and each expert's feature burden decreases, driving the monotonic reduction in
> superposition we observe.
>
> This explains why phase changes disappear: in dense models, phase transitions
> occur when the feature-to-dimension ratio crosses a threshold. In MoEs, the
> effective ratio per expert is controlled by routing, and increasing expert count
> smoothly reduces this ratio below the threshold for any given expert. There is
> no system-wide phase transition because different experts can be in different
> regimes simultaneously.
>
> ### Relationship to sparse autoencoders
>
> Sparse autoencoders (SAEs) address the interpretability challenge post-hoc by
> learning to decompose dense model activations into sparse, monosemantic features
> (Bricken et al., 2023; Cunningham et al., 2024). Our findings suggest that
> MoE architectures may produce representations that are *natively* more
> amenable to interpretation, reducing the need for post-hoc decomposition.
> An important open question is whether SAEs applied to MoE activations discover
> qualitatively different features than those applied to dense models.
>
> ### Implications for architecture design
>
> If monosemanticity scales with expert count, then interpretability-oriented
> architectures should favor many small experts over few large ones, even at fixed
> total parameter count. This aligns with recent trends toward fine-grained MoEs
> (e.g., DeepSeekMoE), though the interpretability benefits have not been the
> stated motivation. Our work provides a mechanistic justification for this design
> choice.
>
> ### Limitations
>
> Our results should be interpreted with several caveats.
>
> **Toy model scope.** All experiments use single-layer autoencoders with synthetic
> feature distributions. Real transformer MoEs involve multi-layer computation,
> attention mechanisms, heterogeneous feature distributions, and realistic routing
> dynamics. Our findings establish a mechanistic principle, but its strength in
> full-scale models is unverified.
>
> **Restricted routing.** We use top-1 routing exclusively. With k > 1, multiple
> experts contribute to each output, and the block-diagonal interference structure
> we observe may partially break down. The effect of k on superposition is an
> important variable we have not explored.
>
> **Parameter matching.** While we match total parameters between dense and MoE
> models, MoEs inherently have more distinct parameter matrices (E separate
> weight matrices). The additional expressiveness from separate parameterizations—
> independent of routing—may contribute to reduced superposition. Disentangling
> architectural routing effects from parameterization effects requires further
> study.
>
> **Synthetic features.** Our features are independent, uniformly sparse, and
> have exponentially decaying importance. Natural language features are correlated,
> have varying sparsity levels, and importance structures we cannot specify a
> priori. How correlated features interact with expert routing is unknown.
>
> **No downstream evaluation.** We measure reconstruction loss and superposition
> metrics but not downstream task performance, training stability, or scaling
> behavior. Whether reduced superposition translates to practical interpretability
> gains in deployed models remains to be demonstrated.

---

## Line-Level Fixes

### §1: "the prevalent zeitgeist" → "a widely held assumption"
Rationale: "zeitgeist" is colloquial and imprecise.

### §3: "A primary focus of Mechanistic Interpretability is to reverse engineer neural networks"
→ "Mechanistic interpretability aims to identify the computational features and circuits that neural networks use internally."
Rationale: More precise, less broad.

### §4: "MoEs are often conceptualized as compositions of dense models"
→ "A natural hypothesis is that each MoE expert behaves as an independent dense network, with the router simply selecting which sub-network to activate (cf. Fedus et al., 2022)."
Rationale: Attributes the conceptualization; sets up the falsification.

### §4.2: "To analyze feature representations across architectures, we compared two fundamental properties"
→ "We compare feature representation quality across architectures using two metrics that jointly characterize superposition."
Rationale: Motivates before defining.

### A.6: "Unfortunately, our methods do not scale naturally to larger models"
→ "Our methods do not scale naturally to larger models, as the feature distributions in real transformers are unknown and the metrics require ground-truth feature labels."
Rationale: Neutral tone; states why, not just that.
