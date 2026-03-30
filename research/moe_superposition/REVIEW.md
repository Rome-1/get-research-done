# Peer Review: Sparsity and Superposition in Mixture of Experts

**Paper**: Chaudhari, Nuer, Thorstenson (2025). arXiv:2510.23671v2
**Review framework**: ML Paper Writing Protocol (Carlini 2026 + Nanda 2026)

---

## Overall Assessment: B+

Strong mechanistic contribution to an under-explored area. The core finding—MoEs
exhibit less superposition than dense models due to network sparsity—is clean and
well-supported by the toy model evidence. However, the paper undersells its results,
buries the most compelling findings, and has structural issues that weaken the
narrative arc. With targeted revisions, this is a solid workshop-to-main-conference
paper.

---

## 1. Narrative and Claims (Writing Guide §1, §6)

### Current state
The paper advances three claims:
1. MoEs exhibit less superposition than dense models
2. MoEs do not exhibit sharp phase changes
3. Expert specialization should be redefined around monosemantic features

### Problems

**Claims are not rank-ordered by strength.** Claim 1 (less superposition) is
the strongest and best-supported. Claim 3 (specialization redefinition) is the
most novel and impactful. Yet the paper leads with the least novel claim and
buries the most interesting one.

**Claim calibration mismatch.** The abstract says MoEs "cannot be explained
through this same framework" (referring to Elhage et al.'s superposition framework).
This is an overclaim—the paper shows the framework *applies differently*, not that
it fails entirely. The MoE still shows superposition; it just shows less of it.

**Missing the killer punchline.** The paper's most provocative finding—that
interpretability and capability may not be fundamentally in tension—is relegated
to a single sentence in the conclusion. This should be the paper's central thesis
with the three claims marshaled as evidence.

### Recommendations

- **Restructure around a single thesis**: "Network sparsity in MoEs enables
  interpretability without the capability penalty assumed by the superposition
  hypothesis." Claims 1-3 become evidence for this thesis.
- **Recalibrate claim 1** from "MoEs cannot be explained" → "MoEs require a
  modified understanding of superposition centered on network sparsity."
- **Promote claim 3** (specialization redefinition): this is the most actionable
  and novel contribution—front-load it.

---

## 2. Abstract (Writing Guide §2)

### Current state
The abstract follows a reasonable structure but violates several protocol rules.

### Problems

- **No concrete numbers.** The abstract contains zero quantitative results.
  "Greater monosemanticity" and "more continuous transitions" are vague.
- **Hedges in the abstract.** "Could enable" and "potentially challenging" are
  weasel words in the one place the paper should be maximally direct.
- **Too long and diffuse.** Three distinct claims compete for attention. The
  reader retains none.

### Recommended abstract (applying Carlini's 5-sentence formula)

> Mixture of Experts (MoE) models have become central to scaling language models,
> yet their internal representations remain poorly understood. **[Topic]**
> We show that MoEs consistently exhibit less superposition than dense networks
> with matched parameters: features per dimension drops by 2-4× as expert count
> increases, with individual experts approaching monosemantic representations.
> **[Result]**
> Unlike dense models, MoEs show no discontinuous phase changes in feature
> representation as sparsity varies—network sparsity (active/total experts),
> not feature sparsity, is the controlling variable. **[Method/Finding]**
> We propose a specialization metric based on monosemantic feature representation
> and show that experts initialized over specific features achieve 100%
> routing accuracy for those features in isolation. **[Other finding]**
> These results suggest that scaling expert count is a direct lever for
> interpretability, challenging the assumption that capability and
> interpretability are fundamentally opposed. **[Significance]**

---

## 3. Introduction (Writing Guide §3)

### Current state
The introduction covers background, motivation, and a contribution summary,
but the structure is weak.

### Problems

**Doesn't meet the reader where they are.** The opening assumes familiarity
with Qwen3, Mixtral, and superposition literature. An ML practitioner who uses
MoEs for efficiency—the natural audience—won't know "superposition" in the mech
interp sense.

**Three questions but no story.** The intro poses three research questions as a
list. This is a grab-bag framing, not a narrative. The reader doesn't know why
these questions matter *together* until the conclusion.

**Contributions list is missing.** The writing guide prescribes an explicit
bullet-point contributions list with evidence pointers. The paper relies on
prose summary instead, making it easy to miss specific claims.

### Recommendations

1. **Open with the tension**: "MoEs are everywhere. They're efficient. But we
   don't understand what individual experts actually learn." → sells the setting
2. **Bridge to superposition**: Briefly explain that dense models pack features
   via superposition → this is what makes interp hard → does the MoE architecture
   change this?
3. **Lead with the punchline**: "We show that MoEs exhibit fundamentally less
   superposition, controlled by network sparsity rather than feature sparsity."
4. **Add explicit contributions list** with evidence pointers.

---

## 4. Figures (Writing Guide §4)

### Current state
Six figures plus two appendix figures.

### Problems

**No hero figure (Figure 1).** Figure 1 shows the dense model baseline. The
paper's *contribution* is about MoEs. Figure 1 should be a side-by-side that
immediately shows the MoE difference—ideally the Gram matrix comparison showing
block-diagonal vs. full interference.

**Captions describe what is plotted, not the takeaway.** Every caption says "X
for parameters Y" but not "This shows that Z." A skimming reader—which is most
readers—learns nothing from the figures alone.

**Figure 4 is the centerpiece but is too dense.** The phase diagram comparison
(Figure 4) is the paper's most important visualization. But it shows 12+ panels
with no annotation guiding the eye. The key observation (phase changes vanish in
MoEs) should be highlighted with annotations or a simplified summary panel.

**Colorblind safety.** Green-purple color scheme in Figure 1 is not
colorblind-safe. The blue-red scheme in later figures is better but should be
verified.

### Recommendations

- **New Figure 1**: Side-by-side dense vs. MoE Gram matrices showing block-diagonal
  structure. Caption: "MoEs partition the feature space across experts, creating
  block-diagonal interference patterns that reduce superposition."
- **Rewrite all captions** to state the takeaway, not just the setup.
- **Add annotations to Figure 4**: arrows or highlights pointing to where phase
  changes vanish. Consider a simplified 2-panel summary version.
- **Audit color schemes** for colorblind safety.

---

## 5. Experimental Evidence (Writing Guide §5)

### Current state
All experiments use synthetic toy models with controlled feature distributions.

### Problems

**No baselines beyond vanilla dense models.** The paper compares MoEs to dense
models, but doesn't compare to other sparsity-inducing architectures (e.g.,
sparse autoencoders, top-k activations in dense models). This leaves open whether
the MoE architecture specifically drives the effect, or whether any form of
sparsity would.

**Statistical reporting is inconsistent.** Section 6 trains "one hundred models"
but doesn't report confidence intervals. The Table 1 usage statistics aggregate
across 1000 experts without variance.

**Missing ablations.** Key design choices go unablated:
- What happens with k>1? (Only briefly mentioned as limitation)
- How does the effect scale with n/m ratio?
- Is the auxiliary loss necessary or harmful for interpretability?

**Red-teaming gap.** The paper doesn't address the most obvious alternative
explanation: MoEs have more total parameters (E×m vs. m). The comparison at
"matched total parameters" is mentioned but the claim that MoEs are more
monosemantic *per active parameter* deserves stronger evidence.

### Recommendations

- **Add a sparse-dense baseline**: dense model with top-k activation (not routing).
  This isolates architectural routing from activation sparsity.
- **Report error bars** on all aggregated metrics. 100 models is enough for
  confidence intervals.
- **Ablation table**: vary k, n/m ratio, and aux loss systematically.
- **Address the parameter argument head-on** in the main text, not just in passing.

---

## 6. Related Work Positioning (Writing Guide §7)

### Current state
Section 2 covers the linear representation hypothesis, superposition work, and
prior MoE interpretability efforts.

### Problems

**Too brief on direct competitors.** The mention of "sparsity-aware routing with
wide, ReLU-based experts" in the intro is not expanded in related work. Who
proposed this? How does your work extend or contradict it?

**No comparison to SAE literature.** Sparse autoencoders are the dominant
interpretability method. The paper should explicitly position against the SAE
approach: "SAEs post-hoc extract features from dense models; we show MoEs
produce interpretable features architecturally."

**Novelty framing is too modest.** The paper says "we address this gap." It
should say what the gap *is* more explicitly and why prior work couldn't fill it.

### Recommendations

- **Expand related work** to 1-1.5 pages. Explicitly compare to SAE-based
  interpretability.
- **State your delta clearly**: "Prior work X showed Y; we extend this to MoEs
  and find Z, which contradicts the expectation from X."
- **Move related work after main results** (penultimate section) since it's not
  needed to motivate the paper.

---

## 7. Discussion and Limitations (Writing Guide §8)

### Current state
Limitations are in Appendix A.6. The conclusion is 7 sentences.

### Problems

**Limitations hidden in appendix.** This signals either lack of awareness or
avoidance. Sophisticated reviewers will notice. Moving limitations to the main
text signals confidence.

**Conclusion restates results without answering "so what?"** The concluding
sentence ("can inform the design of more interpretable, high-performing language
models") is generic. What *specifically* should a practitioner do differently
based on this paper?

**No discussion section.** The paper goes directly from experiments to conclusion
with no synthesis. The relationship between the three findings—less superposition
→ no phase change → feature-based specialization—is never explicitly drawn.

### Recommendations

- **Add a Discussion section** (1 page) synthesizing findings into a coherent story:
  network sparsity → less superposition → experts specialize monosemantically →
  this is a design lever.
- **Move limitations into main text.** Add a subsection after Discussion.
- **Rewrite conclusion** to answer: "If you are building or interpreting an MoE,
  here is what you should do differently based on our findings."

---

## 8. Narrative Arc (Writing Guide §§1,3,8)

### Current diagnosis
The paper reads as three loosely connected experiments rather than a single
coherent investigation. The narrative arc is:

> Dense models have superposition → Do MoEs? → Yes but less → Also no phase
> change → Also specialization is about features

### Recommended arc

> **Setup**: MoEs are everywhere, but we don't know if the superposition problem
> that plagues dense model interpretability also afflicts MoEs.
>
> **Twist**: Network sparsity—not feature sparsity—is the controlling variable.
> This means the interpretability problem in MoEs is architecturally different
> from dense models.
>
> **Payoff**: Experts naturally specialize around coherent features, and this
> specialization increases with expert count. Scaling experts is a direct lever
> for interpretability.
>
> **Implication**: The supposed interpretability-capability tradeoff may be an
> artifact of dense architectures, not a fundamental law.

---

## 9. Specific Line-Level Issues

| Location | Issue | Fix |
|----------|-------|-----|
| Abstract | "cannot be explained through this same framework" | → "requires a modified framework centered on network sparsity" |
| Abstract | "could enable" / "potentially" | → Remove hedges; state findings directly |
| §1 ¶1 | Drops Qwen3, Mixtral, Gemini without context | → "Production language models (Qwen3, Mixtral, Gemini) increasingly use MoE architectures for..." |
| §3 | "A primary focus of Mechanistic Interpretability is to reverse engineer neural networks" | → Too broad; cut to one sentence of mech interp context |
| §4 | "MoEs are often conceptualized as compositions of dense models" | → Cite who conceptualizes them this way |
| §4.2 | "features per dimension" metric introduced without motivation | → Explain why this is the right metric before defining it |
| §5 | "affirming the work of Elhage2022Toy" | → Name the finding being affirmed |
| §5 | "middleground in MoEs" | → Quantify: what % of the phase space? |
| §6 | "conditional on their specialized features being active, their usage increases far greater than other experts" | → Give the number: "usage increases from ~10% to 67-100%" |
| §7 | "challenging the prevalent zeitgeist" | → Too colloquial for a technical paper; → "challenging a widely held assumption" |
| A.6 | "Unfortunately, our methods do not scale naturally" | → Never say "unfortunately" in a paper; state it neutrally |

---

## 10. Priority-Ordered Improvement Checklist

### High Impact (do first)
1. [ ] Restructure narrative around single thesis (interpretability-capability tension)
2. [ ] Rewrite abstract with concrete numbers and no hedges
3. [ ] New Figure 1: side-by-side dense vs. MoE comparison
4. [ ] Rewrite all figure captions to state takeaways
5. [ ] Add explicit contributions list to introduction

### Medium Impact
6. [ ] Add Discussion section synthesizing the three findings
7. [ ] Move limitations to main text
8. [ ] Rewrite conclusion with actionable takeaways
9. [ ] Expand related work (SAE comparison, explicit deltas)
10. [ ] Report error bars on Table 1 and aggregated metrics

### Lower Impact (polish)
11. [ ] Fix colorblind-unsafe figures
12. [ ] Simplify Figure 4 with annotation/summary panel
13. [ ] Fix line-level issues from §9 table above
14. [ ] Add sparse-dense baseline experiment
15. [ ] Ablation table for k, n/m ratio, aux loss
