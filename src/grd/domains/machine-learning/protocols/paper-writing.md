# ML Paper Writing Protocol

## Purpose
Operational guide for drafting, structuring, and reviewing ML research papers.
Distilled from Carlini (2026) and Nanda (2026) into actionable principles that
GRD agents can apply when producing or reviewing paper drafts.

---

## 1. Narrative First

Before writing anything, compress your research into **1-3 concrete, specific claims**.
Everything in the paper exists to support these claims. If you cannot state them in
plain sentences, the paper is not ready.

- Each claim should be falsifiable and evidence-backed.
- Claims should fit a cohesive theme — a grab-bag of unrelated results is not a paper.
- Calibrate claim strength to evidence: existence-proof, systematic, hedged, or narrow.

**Test**: Describe the paper to someone in 60 seconds. What they remember is your narrative.

---

## 2. Abstract

The abstract must let a cold-start reader understand the paper's contribution and
decide whether to read further.

### Formula (Carlini pattern)
1. **Topic** — What area are you working in?
2. **Problem** — What specific problem are you solving?
3. **Method or Result** — What did you do / find?
4. **The other one** — Whichever of method/result sentence 3 didn't cover.
5. **Significance** — Why does this matter?

### Requirements
- Include at least one concrete number or quantitative result.
- State claims directly — do not hedge in the abstract.
- Use simple language; minimize jargon. A reader from an adjacent subfield should follow.
- End by conveying importance: practical utility, correcting misconceptions, or advancing basic science.
- Be specific: "we consider problem X" is weaker than stating the actual result.

---

## 3. Introduction

The introduction is a **story** that moves the reader from what they already believe
to the point where your contribution lands naturally.

### Structure
1. **Context** (1 para) — What topic, what motivating question, why it matters. Cite liberally.
2. **Technical background** (1 para) — Established techniques your paper rests on.
3. **Key contribution** (1 para) — Your main claim with nuance and detail.
4. **Evidence summary** (0.5-1 para) — Why the reader should believe the claim.
5. **Impact** (1 para) — So what? Implications, who should change behavior, broader context.
6. **Contributions list** — Bullet points of each claim with brief evidence pointers.

### Principles
- Meet the reader where they are. If the problem is not well-known, you must sell the
  *setting* before selling the result (but keep it under 2 pages).
- For heretical results, lay evidence so the reader arrives at the conclusion themselves —
  stating it baldly will trigger dismissal.
- The introduction is a self-contained paper summary. Repetition with the abstract is fine;
  complex ideas need varied restatement.
- Define key terms here or in background. Readers have less context than you think.

---

## 4. Figures

Figures are often the only thing a skimming reader examines. Each figure must be
interpretable without reading the body text.

### Checklist
- [ ] Caption states the takeaway, not just what is plotted.
- [ ] Axes labeled with units; tick labels readable at print size.
- [ ] Legend is clear; no reliance on red/green distinction (colorblind-unsafe).
- [ ] One figure = one message. If it needs two messages, split it.
- [ ] Key line/bar emphasized (bold, dark, or annotated) when comparing many.
- [ ] Figure 1 is a "hero figure" — conveys the core idea to a skimming reader.

### Color guidance
- Positive data starting at zero: white-to-dark sequential scale (e.g. `Blues`).
- Positive-negative with meaningful zero: diverging scale (e.g. `RdBu`), white at zero.

---

## 5. Experimental Evidence

Evidence exists to convince a skeptical, engaged reader that your claims are true.

### Quality over quantity
- One compelling, hard-to-deny experiment outweighs many mediocre ones.
- Diverse lines of evidence (qualitatively different methods) are more robust than
  many similar experiments.
- Highlight the strongest experiments in the main text; move weaker ones to appendix.

### Rigor checklist
- [ ] Multiple seeds / trials with mean and std reported.
- [ ] Confounders controlled; setup described precisely enough to reproduce.
- [ ] Baselines are **strong** — put real effort into tuning them, not just your method.
- [ ] Ablation studies isolate each component's contribution.
- [ ] Pre-registered predictions separated from post-hoc analysis.
- [ ] Cherry-picking acknowledged; randomly-selected examples shown alongside.
- [ ] Statistical thresholds: be skeptical of p in (0.01, 0.05); prefer p < 0.001
  for exploratory work.

### Red-teaming your own results
- Assume you made a mistake. What is it?
- Assume there is an alternative explanation. What is it?
- For each key experiment, attempt re-implementation via a different pathway.
- If a result seems too clean, investigate — it may be a bug or artifact.

---

## 6. Claims Calibration

### Strength ladder
| Level | Wording | Evidence bar |
|-------|---------|-------------|
| Existence proof | "We found at least one case where X" | Single trustworthy example |
| Hedged | "Suggestive/tentative evidence that X" | Limited but real signal |
| Systematic | "X generally holds across contexts" | Broad sweep, many settings |
| Strong | "X should be used in practice for Y" | Comparative eval + baselines |

### Anti-patterns
- Overclaiming: stating a systematic result from a single model/dataset.
- Underclaiming: burying the lead because you are afraid of reviewers.
- Ignoring limitations: researchers who matter will notice; address them first.
- Vague claims: "our method performs well" — compared to what? On what metric?

---

## 7. Related Work and Novelty

- Be explicit about what is and is not novel. The same paper can seem arrogant or
  modest depending on how claims are framed.
- Cite the most relevant prior work and explain how yours differs — not just a list.
- If building directly on someone's work, credit them clearly and state your delta.
- Related work can go after main content (penultimate section) unless it is essential
  for motivating the paper.

---

## 8. Discussion, Limitations, and Conclusion

### Discussion / Limitations
- Acknowledge limitations honestly. Competent readers see through spin; candor builds trust.
- Include: scope restrictions, assumptions that may not hold, failure modes observed.
- Suggest future work directions with enough specificity to be actionable.

### Conclusion
- The conclusion is **not** the abstract in past tense.
- Its purpose: answer "so what?" for someone who just read the technical details.
- Be heavy-handed about the moral / takeaway — leave nothing unsaid.
- If you cannot write a conclusion beyond restating results, the paper may lack significance.

**Pre-mortem test** (Carlini): Before starting research, write the best-case conclusion.
If it says nothing beyond "number went up 2%", reconsider whether the paper is worth writing.

---

## 9. Writing Process

### Iterative expansion
1. **Compress** — Write the 1-3 claims + key evidence as bullet points.
2. **Bullet-point intro** — Expand claims into a structured introduction outline.
3. **Full outline** — Every section as bullets; every bullet justifies its existence.
4. **Figures** — Draft key figures; verify they support the narrative.
5. **First draft** — Flesh bullets into prose.
6. **Edit** — Multiple passes; get external feedback at each stage.

### Time allocation
Spend roughly equal time on: abstract, introduction, figures, and everything else.
Most readers only see the first three.

### Prose principles
- Read your writing aloud (or use TTS). Fix anything that sounds wrong.
- Avoid dual-meaning sentences, especially where the wrong reading is plausible.
- Cut words. Short sentences after long ones give the reader air.
- Use jargon only when the alternative is imprecision.
- Passive voice is fine where appropriate, but active voice is usually clearer.
- Proofread, but don't polish endlessly — time is finite.

---

## 10. Strategic Considerations

### Focus
A paper should advance **one idea**. Multiple ideas in one paper means the reader
remembers none. If you have many findings, pick the best one; save others for
follow-up work or appendices.

### The maximal version
Your paper should be at a local optimum — no obvious improvement the reader wishes
you had done. But leave room for others to extend: that invites engagement.

### Kill early, pivot ruthlessly
- De-risk first: tackle the sub-problem most likely to fail.
- If an idea is working but clearly low-impact, kill it or downgrade to workshop paper.
- If a higher-impact idea appears, pivot immediately. Sunk costs are irrelevant.

### Persistence
Many best-paper winners were rejected at least once. A rejection means the argument
was not yet clear enough — revise and resubmit. Thick skin is a prerequisite.

### Timing
- Being early can mean reviewers reject what they don't yet believe — write the
  introduction to sell the future.
- Being late means the contribution is smaller. Move quickly on emerging topics.

---

## Common Pitfalls
- Writing the paper as an afterthought instead of treating it as core research work.
- The illusion of transparency: you have months of context; the reader has none.
- Unnecessary complexity and jargon to sound impressive (simplicity signals confidence).
- Obsessing over publishability at the expense of scientific integrity.
- Ignoring tacit knowledge — hard-won insights about what worked/failed belong in
  appendices or blog posts, not discarded.
- Not getting external feedback — paper swaps are high-ROI.

---

## Convention Lock Fields
- `evaluation_metric`, `data_split_strategy`, `random_seed_policy`, `claim_strength`

## Sources
- Carlini, N. (2026). "How to win a best paper award." nicholas.carlini.com.
- Nanda, N. (2026). "Highly opinionated advice on how to write ML papers." Alignment Forum.
