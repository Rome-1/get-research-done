---
load_when:
  - "activation patching"
  - "ablation"
  - "causal intervention"
  - "patching"
  - "zero ablation"
  - "mean ablation"
  - "resample ablation"
  - "denoising"
  - "noising"
tier: 1
context_cost: medium
---

# Activation Patching Protocol

Activation patching (also called causal intervention or ablation) replaces activations at specific model components with alternative values to measure their causal contribution to model behavior. Done incorrectly, it produces misleading importance scores due to distribution shift, correlated components, or inappropriate baselines.

## Related Protocols

- See `circuit-discovery.md` for using patching results to identify circuits
- See `causal-tracing.md` for the localization step that precedes systematic patching
- See `feature-analysis.md` for interpreting what patched components compute

## Before Patching

1. **Define the metric precisely.** What output behavior are you measuring?
   - **Logit difference**: logit(correct) - logit(incorrect). Best for binary discrimination tasks.
   - **Probability**: P(correct token). Sensitive to calibration.
   - **KL divergence**: between patched and unpatched output distributions. Measures total distributional change.
   - **Loss difference**: cross-entropy on the target token. Standard for generic tasks.
   - Document your metric — results are not comparable across different metrics.

2. **Construct clean and corrupted inputs.**
   - **Clean input**: a prompt where the model exhibits the target behavior.
   - **Corrupted input**: identical to clean except the task-relevant information is changed.
   - The corrupted input should change ONLY the relevant variable. Example for IOI: swap the indirect object name ("Mary" → "Alice"), keeping everything else identical.
   - **Bad corrupted inputs**: random text, empty string, or prompts that differ in multiple ways from clean.

3. **Choose the patching direction.**
   - **Denoising (activation patching)**: run model on corrupted input, patch in clean activations at target site. Measures: "is this component sufficient to restore correct behavior?"
   - **Noising (resample ablation)**: run model on clean input, patch in corrupted activations at target site. Measures: "is this component necessary for correct behavior?"
   - These are NOT equivalent. Use both for robust conclusions.

4. **Choose the baseline for ablation.**
   - **Zero ablation**: replace with zeros. Simple but causes distribution shift (activations are never zero in practice).
   - **Mean ablation**: replace with mean activation across a reference dataset. Better calibrated but loses position/context information.
   - **Resample ablation**: replace with activations from a different input. Best for causal claims but requires paired inputs.
   - Document which baseline you use — results depend on it.

## During Patching

1. **Patch one component at a time first.** Get individual importance scores for all components (heads, MLPs, SAE features).

2. **Use batched evaluation.** Run patching across your full dataset, not a single example. Report mean and standard error of the metric change.

3. **Track the sign of the effect.**
   - Positive effect (denoising restores correct behavior): component carries task-relevant information.
   - Negative effect (denoising makes things worse): component may be a suppressor or backup circuit that's disrupted.
   - Near-zero effect: component is not involved in this task.

4. **Test for interaction effects.** After identifying individually important components:
   - Patch pairs of components together.
   - Compare joint effect to sum of individual effects.
   - Superadditive = components in the same pathway (redundant).
   - Subadditive = components in parallel pathways (complementary).

5. **Path patching for edge-level analysis.** To determine whether component A sends information to component B:
   - Run the model with A's output from the clean run and B's input from the corrupted run.
   - If patching A's output to B's input restores behavior, A→B is a critical edge.

## After Patching

1. **Report results as a ranked list** of components by effect size, with confidence intervals.

2. **Visualize the results:**
   - Heatmap of effect sizes by layer and component.
   - Separate plots for denoising vs noising if both were used.

3. **Validate top components.** For the top-5 most important components:
   - Inspect their activations on representative examples.
   - Check: does the component's behavior make mechanistic sense for the task?

4. **Quantify total explained effect.** What fraction of the metric is explained by all identified components together? If <80%, important components are likely missing.

## Concrete Example: Distribution Shift from Zero Ablation

**Problem:** Determine which attention heads in GPT-2 Small are important for predicting the next token after "The Eiffel Tower is in".

**Wrong approach:** Zero-ablate each head and measure loss increase. Find that heads in layers 0-2 have the largest loss increase. Conclude: "early heads are most important for factual recall."

This is wrong because zero ablation causes massive distribution shift in early layers — zeroing an early head corrupts the residual stream for ALL downstream computation, not just fact recall. The large loss increase reflects disruption of general processing, not task-specific importance.

**Correct approach following this protocol:**

1. **Define metric:** logit difference for "Paris" vs next-most-likely token.
2. **Corrupted input:** "The Colosseum is in" (same structure, different fact).
3. **Denoising:** run on corrupted, patch each head with clean activations.
   - Heads 9.1 and 10.7 restore most of the logit difference → carry factual information.
4. **Noising:** run on clean, patch each head with corrupted activations.
   - Heads 9.1 and 10.7 also reduce logit difference when corrupted → necessary for fact recall.
5. **Control:** zero ablation shows layers 0-2 as important → this is distribution shift artifact.
6. **Conclusion:** factual recall circuit involves heads in layers 9-10, not layers 0-2.

## Common Pitfalls

- **Zero ablation for importance ranking.** Zero ablation measures "how much does this component disrupt the model" rather than "how much does this component contribute to the task." Use paired clean/corrupted inputs instead.
- **Using a single example.** Patching results on one prompt may not generalize. Always average across a dataset (≥50 examples).
- **Confusing sufficiency and necessity.** Denoising tests sufficiency; noising tests necessity. A component can be sufficient but not necessary (backup exists) or necessary but not sufficient (part of a multi-component pathway).
- **Ignoring the residual stream.** Patching a head's output affects all downstream computation via the residual stream. The observed effect includes both the head's direct contribution and indirect effects through downstream components.
- **Not reporting the baseline.** "We ablated head 9.1 and performance dropped" is meaningless without specifying the ablation method (zero, mean, resample) and the comparison baseline.
