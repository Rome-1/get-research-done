---
load_when:
  - "feature"
  - "feature analysis"
  - "feature interpretation"
  - "feature visualization"
  - "polysemanticity"
  - "monosemanticity"
  - "neuron interpretation"
  - "max activating examples"
  - "feature steering"
tier: 1
context_cost: medium
---

# Feature Analysis Protocol

Feature analysis interprets what individual features (neurons, SAE features, or other directions in activation space) represent. Done incorrectly, it produces overconfident interpretations based on cherry-picked examples, mistakes correlation for the feature's actual causal role, or labels polysemantic features as if they were monosemantic.

## Related Protocols

- See `sae-training.md` for training the SAE that produces features to analyze
- See `activation-patching.md` for testing feature causal roles
- See `circuit-discovery.md` for understanding how features compose into circuits

## Before Analyzing

1. **Define what "interpretation" means for your purpose.**
   - **Qualitative labeling**: assign a human-readable description (e.g., "Python function definitions").
   - **Quantitative prediction**: can you predict when the feature will activate on unseen text?
   - **Causal understanding**: does steering the feature produce the expected behavioral change?
   - Document your goal — the analysis depth depends on it.

2. **Select features to analyze.** You cannot interpret all features manually. Prioritize:
   - **Task-relevant features**: features identified by circuit discovery as important for a behavior.
   - **Highest-activation features**: features that activate most strongly on your domain of interest.
   - **High-frequency features**: features that activate on many inputs (widely used by the model).
   - **Random sample**: for estimating overall dictionary quality.

3. **Prepare a diverse evaluation dataset.**
   - Use a different corpus than SAE training data to avoid memorization artifacts.
   - Include varied domains: code, prose, dialogue, technical writing, multiple languages.
   - Minimum 1M tokens for reliable activation statistics.

## During Analysis

1. **Find max-activating examples.** For each feature:
   - Collect the top-20 dataset examples by activation magnitude.
   - Also collect 20 random examples where the feature activates (at any strength).
   - Also collect 5 examples where the feature is near-zero (negative examples).
   - The max-activating examples show the feature's core pattern; random activating examples show its range; negative examples confirm what it does NOT respond to.

2. **Look for the common pattern.** Across max-activating examples:
   - What do the activating tokens share? (Syntax, semantics, position, context?)
   - What specific token position does the feature activate on? (The keyword itself? The token after it? The last token?)
   - Is there an obvious description, or is the pattern complex/disjunctive?

3. **Test your hypothesis.** Once you have a candidate interpretation:
   - Generate 10 new examples that should activate the feature (based on your interpretation).
   - Generate 10 new examples that are superficially similar but should NOT activate.
   - Run these through the model and check feature activations.
   - If the feature activates on unexpected examples or fails on expected ones, refine the interpretation.

4. **Check for polysemanticity.** Does the feature activate on multiple unrelated patterns?
   - Cluster the activating examples by context type.
   - If there are 2+ distinct clusters with no obvious connection, the feature is polysemantic.
   - Report it as such — don't force a single label on a polysemantic feature.

5. **Measure feature properties.**
   - **Activation density**: what fraction of tokens activate this feature? (L0 contribution.)
   - **Activation distribution**: histogram of activation magnitudes. Bimodal = potential polysemanticity.
   - **Decoder direction**: the feature's decoder weight vector. Cosine similarity to token embeddings reveals what the feature "writes" to the residual stream.

## Feature Steering (Causal Validation)

1. **Amplify the feature.** Add k× the decoder direction to the residual stream at the feature's layer. Generate text and observe:
   - Does the behavior match your interpretation? (E.g., if the feature is "French language," does amplification cause French output?)
   - At what scale (k) does the effect appear? Too high and you get degenerate output.

2. **Suppress the feature.** Clamp the feature activation to zero and observe:
   - Does the expected behavior disappear?
   - Are there backup features that compensate?

3. **Compare steering vs natural activation.** The behavioral effect of artificial steering should be consistent with the behavioral context of natural max activations.

## After Analysis

1. **Write a feature card** for each analyzed feature:
   - **ID**: feature index and SAE details.
   - **Label**: short description (e.g., "Python import statements").
   - **Confidence**: high/medium/low based on interpretation evidence.
   - **Activation density**: fraction of tokens.
   - **Max activating examples**: 5 representative examples with context.
   - **Steering result**: brief description of amplification/suppression effects.
   - **Polysemanticity**: none / mild (related patterns) / strong (unrelated patterns).

2. **Compute automated interpretability scores** (if using auto-interp):
   - Generate explanations using an LLM.
   - Score: can the LLM predict feature activations from the explanation alone?
   - Correlation between predicted and actual activations is the "explanation score."
   - Scores >0.7 indicate good interpretability; <0.3 indicates the feature is hard to interpret.

3. **Aggregate statistics.** Over all analyzed features:
   - What fraction are monosemantic? Mildly polysemantic? Strongly polysemantic?
   - What fraction have clear interpretations?
   - How do these statistics vary by activation density?

## Concrete Example: Cherry-Picked Interpretation

**Problem:** Interpret SAE feature #4217 in GPT-2 Small layer 8.

**Wrong approach:** Look at the top-5 max-activating examples. All contain the word "president." Label the feature "president mentions." Stop.

Later, someone finds the feature also fires on "CEO," "chairman," "dean," and "captain" — it's actually a "leadership titles" feature, and the top-5 happened to all be "president" by coincidence.

**Correct approach following this protocol:**

1. **Max activating (top-20):** 12 contain "president", 4 contain "CEO", 2 contain "chairman", 1 "director", 1 "captain."
2. **Random activating (20):** "governor", "commander", "editor-in-chief", "principal", plus 5 that don't obviously fit (requiring investigation).
3. **Hypothesis:** "leadership/authority titles."
4. **Test:** generate 10 examples with authority titles not seen above ("admiral", "pope", "chancellor") → 8/10 activate. Generate 10 with non-authority words ("teacher", "doctor", "artist") → 1/10 activates (borderline "teacher" case).
5. **Steering:** amplifying the feature causes the model to insert authority titles into generated text.
6. **Label:** "Authority/leadership titles" (confidence: high).
7. **Polysemanticity:** mild — mostly leadership titles but occasionally fires on formal address contexts.

## Common Pitfalls

- **Looking only at top-k examples.** Top examples show the most extreme activations but not the feature's full range. Always include random activating examples.
- **Forcing monosemantic labels on polysemantic features.** If the feature activates on two unrelated patterns, say so. A misleading monosemantic label is worse than acknowledging polysemanticity.
- **No causal validation.** Interpretation from max-activating examples alone is correlation. Always test with steering (amplification and suppression) to confirm the feature's causal role.
- **Interpreting inactive features.** If a feature activates on <0.01% of tokens, its max-activating examples may be noise. Check that the pattern is robust across multiple max-activating examples.
- **Confusing the feature's decoder direction with its encoder direction.** The encoder detects the feature; the decoder writes it. They may correspond to different concepts (especially for polysemantic features).
- **Not documenting confidence.** Some features have obvious interpretations; others are ambiguous. Report confidence levels so downstream consumers know which labels to trust.
