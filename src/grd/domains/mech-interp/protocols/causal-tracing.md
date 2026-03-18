---
load_when:
  - "causal tracing"
  - "causal mediation"
  - "localization"
  - "factual recall"
  - "knowledge localization"
  - "information flow"
  - "ROME"
  - "MEMIT"
tier: 2
context_cost: medium
---

# Causal Tracing Protocol

Causal tracing (causal mediation analysis) identifies WHERE in a model specific knowledge or computation is localized by corrupting inputs and selectively restoring activations at individual sites. It answers: "at which layer and token position does the model retrieve/process this information?" Done incorrectly, it produces misleading localization maps that conflate storage with processing or miss distributed representations.

## Related Protocols

- See `activation-patching.md` for the general patching methodology underlying causal tracing
- See `circuit-discovery.md` for finding the complete circuit after initial localization
- See `probing.md` for complementary correlation-based localization

## Before Tracing

1. **Define the factual association precisely.** Causal tracing works best for discrete factual knowledge:
   - Subject-relation-object triples: ("Eiffel Tower", "located in", "Paris").
   - Specify the exact prompt template: "The Eiffel Tower is located in"
   - Verify the model predicts the correct object ("Paris") with high probability.

2. **Construct the three-run setup.**
   - **Clean run**: original prompt, collect all activations.
   - **Corrupted run**: corrupt the subject tokens (add Gaussian noise to embeddings, or replace with random tokens). Verify the model NO LONGER predicts the correct answer.
   - **Restored run**: start from corrupted run, but restore clean activations at specific (layer, position) sites.

3. **Choose the corruption method.**
   - **Gaussian noise** (original causal tracing): add noise with σ = 3× the embedding standard deviation. Simple but somewhat arbitrary.
   - **Token replacement**: replace subject with random tokens of the same length. More naturalistic but changes token count.
   - **Embedding scramble**: permute the subject token embeddings. Preserves norm statistics.
   - Document your choice — the corruption method affects the localization map.

4. **Verify corruption is effective.** After corrupting:
   - The probability of the correct answer should drop to near-uniform or near-zero.
   - If corruption barely affects the prediction, increase noise or use a different method.
   - If corruption completely destroys all predictions (not just the target), reduce the noise — you want targeted disruption.

## During Tracing

1. **Sweep all (layer, position) pairs.** For each site:
   - Start from the corrupted run.
   - Restore the clean activation at that single site.
   - Measure how much the correct-answer probability is recovered.
   - The "indirect effect" at site (l, p) = P(correct | restore at (l,p)) - P(correct | fully corrupted).

2. **Visualize as a heatmap.** Plot indirect effect with:
   - X-axis: token position.
   - Y-axis: layer number (0 at bottom).
   - Color: effect magnitude.
   - This reveals the causal flow: where does restoring clean information help most?

3. **Distinguish three types of sites.**
   - **Early subject positions, early layers**: information entry — the model reads the subject.
   - **Last subject token, mid layers**: information enrichment — the model retrieves associated knowledge.
   - **Last token, late layers**: information extraction — the model converts knowledge to prediction.
   - A typical causal trace shows a characteristic "L-shape" or "diagonal" pattern.

4. **Test multiple prompts.** Run causal tracing on ≥20 different facts.
   - Average the heatmaps (aligned by subject/last-token position).
   - Individual facts may have atypical traces; the average reveals the general pattern.

## After Tracing

1. **Report the peak localization.** At which (layer, position) is the indirect effect maximized?
   - For factual recall in GPT-2 / GPT-J: typically peaks at the last subject token, layers 15-25 (mid-to-late MLP layers).
   - Report the peak value and the width of the peak (how many layers/positions have >50% of peak effect).

2. **Decompose by component type.** Repeat the trace restoring only:
   - Attention output at each site.
   - MLP output at each site.
   - This reveals whether localization is in attention or MLP.

3. **Validate with ablation.** Does ablating the peak site degrade factual recall?
   - Causal tracing shows where restoration helps; ablation shows where disruption hurts.
   - If these disagree, the localization may not be robust.

4. **Test specificity.** Does restoring the peak site help for UNRELATED facts?
   - If yes: the site handles general processing, not specific knowledge storage.
   - If no: the site is specifically involved in this knowledge.

## Concrete Example: Misleading Localization from Weak Corruption

**Problem:** Localize where GPT-2 Medium stores the fact "The CEO of Apple is Tim Cook."

**Wrong approach:** Add noise with σ = 0.5× embedding std (too weak). The model still predicts "Tim Cook" with 60% probability after corruption. Causal tracing shows large effects everywhere because even small restorations push the already-high probability higher.

**Correct approach following this protocol:**

1. **Corruption:** σ = 3× embedding std on "Apple" token. P("Tim Cook") drops from 85% to 2%.
2. **Sweep:** restore each (layer, position). Peak at (layer 16, last subject token) with 70% recovery.
3. **Decompose:** MLP at layer 16 accounts for 55% of recovery; attention accounts for 15%.
4. **Validate:** ablating MLP at layer 16 for this prompt drops P("Tim Cook") from 85% to 12%.
5. **Specificity:** restoring MLP-16 at "Apple" does NOT help recall "The capital of France is Paris" → localization is specific to Apple-related knowledge.

## Common Pitfalls

- **Corruption too weak.** If the model still predicts correctly after corruption, the causal trace is uninterpretable. Verify P(correct) drops to <10% after corruption.
- **Corruption too strong.** If corruption destroys ALL model capabilities (not just the target fact), restoration effects are inflated because you're measuring general recovery, not fact-specific recovery.
- **Confusing MLP storage with attention routing.** Attention heads at the localized site may be routing information there, not storing it. Decompose by component type to distinguish.
- **Single-fact conclusions.** "The model stores X at layer L" based on one fact is unreliable. Average across many facts.
- **Interpreting causal tracing as "knowledge is stored here."** Causal tracing shows where restoration helps, which may reflect processing/retrieval rather than storage. A fact can be distributed across many sites even if one site dominates the causal trace.
- **Not controlling for token position effects.** Subject tokens at different positions may show different traces purely due to positional encoding effects. Control by varying the prompt prefix length.
