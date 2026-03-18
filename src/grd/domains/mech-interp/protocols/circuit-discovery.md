---
load_when:
  - "circuit"
  - "circuit discovery"
  - "circuit analysis"
  - "circuit tracing"
  - "component identification"
  - "subgraph"
  - "minimal circuit"
  - "faithfulness"
tier: 1
context_cost: medium
---

# Circuit Discovery Protocol

Circuit discovery identifies the minimal subgraph of a neural network responsible for a specific behavior. Done carelessly, it produces circuits that are incomplete (missing critical components), overcomplete (including irrelevant nodes), or that only appear faithful due to distribution shift from ablation.

## Related Protocols

- See `activation-patching.md` for the patching methods used to isolate circuit components
- See `causal-tracing.md` for localizing causal sites before circuit enumeration
- See `feature-analysis.md` for interpreting what individual circuit components compute

## Before Starting

1. **Define the task precisely.** Specify the exact input-output behavior the circuit should explain. Avoid vague descriptions like "the model does addition" — instead: "given prompts of the form 'X + Y = ', the circuit produces the correct sum token in the logit difference between the correct and most-likely-incorrect answer."

   - Write a dataset of clean/corrupted prompt pairs with expected behavior.
   - Define the metric: logit difference, probability, KL divergence, or accuracy.
   - Verify the model performs the task reliably (>90% accuracy on your dataset) before searching for a circuit.

2. **Choose your granularity.** Decide the resolution of circuit components:
   - **Attention heads + MLPs** (coarsest): each layer's attention heads and MLP treated as atomic units.
   - **Attention heads + MLP neurons**: individual MLP neurons included.
   - **SAE features**: use sparse autoencoder features as the basis for circuit nodes.
   - Document the choice — it determines what "minimal" means.

3. **Select a patching method and baseline.**
   - **Activation patching (denoising)**: run on corrupted input, patch in clean activations. Shows which components are sufficient.
   - **Resample ablation (noising)**: run on clean input, patch in corrupted activations. Shows which components are necessary.
   - **Both together**: necessary AND sufficient gives the tightest circuit.
   - Choose the corrupted distribution carefully — it must differ from clean only in the task-relevant way.

## During Discovery

1. **Start with coarse localization.** Use activation patching at the layer level to identify which layers matter. This narrows the search space before testing individual heads/neurons.

2. **Iterate from coarse to fine.**
   - Patch entire layers → identify important layers.
   - Within important layers, patch individual heads and MLPs.
   - Within important heads, test whether QKV circuits or OV circuits carry the signal.
   - Optionally decompose into SAE features for finer resolution.

3. **Track path-dependent effects.** A component may appear unimportant when patched alone but be critical in combination. Test interactions:
   - Patch pairs of components that individually have small effects.
   - Use path patching to trace information flow between specific components.

4. **Measure circuit faithfulness at every step.**
   - Run the full model and the ablated model (everything outside the circuit ablated).
   - Compare: does the circuit recover ≥ X% of the full model's metric?
   - Report the exact percentage, not just "it works."

5. **Check for backup circuits.** Ablating the primary circuit may activate backup mechanisms. Test:
   - Does ablating the discovered circuit degrade performance to chance?
   - Or does the model partially recover, suggesting redundant pathways?

## After Discovery

1. **Report the complete circuit specification:**
   - List of components (head indices, MLP layers, SAE features).
   - Edges: which components communicate (via residual stream composition).
   - Faithfulness metric: what percentage of the full behavior is recovered.
   - Size: what fraction of total model components are included.

2. **Verify minimality.** For each component in the circuit:
   - Remove it and re-measure faithfulness.
   - If faithfulness doesn't drop significantly, the component is not essential — remove it.

3. **Test generalization.** Does the circuit work on held-out examples not used during discovery?
   - Use a separate test set.
   - Report both train and test faithfulness.

## Concrete Example: Incomplete Circuit from One-Direction Patching

**Problem:** Discover the circuit for indirect object identification (IOI) in GPT-2 Small.

**Wrong approach:** Use only activation patching (denoising) — patch clean activations into a corrupted run. Find that heads 9.9, 9.6, 10.0 recover most of the logit difference. Declare this the IOI circuit.

This misses the name mover heads, S-inhibition heads, and duplicate token heads that are NECESSARY (as shown by noising) even though they are not individually sufficient (as shown by denoising alone).

**Correct approach following this protocol:**

1. **Define task:** IOI sentences like "When Mary and John went to the store, John gave a drink to" → "Mary". Metric: logit difference (logit(Mary) - logit(John)).
2. **Clean/corrupted pairs:** corrupted = replace indirect object with random name ("Mary" → "Alice").
3. **Coarse scan:** activation patching by layer shows layers 7-11 are critical.
4. **Fine scan (both directions):**
   - Denoising: identifies S-inhibition heads (7.3, 7.9, 8.6, 8.10) and name mover heads (9.9, 9.6, 10.0).
   - Noising: additionally identifies duplicate token heads (0.1, 3.0) and induction-like heads (5.5, 6.9).
5. **Combined circuit:** 26 heads across layers 0-11, organized into sub-circuits (duplicate token → S-inhibition → name mover).
6. **Faithfulness:** circuit recovers 97% of logit difference on test set.
7. **Minimality check:** removing any named head drops faithfulness by >5%.

## Common Pitfalls

- **Using only one patching direction.** Denoising finds sufficient components; noising finds necessary ones. You need both for a complete circuit.
- **Corrupted distribution too different from clean.** If corrupted prompts are nonsensical, patching reveals attention pattern changes rather than task-specific computation.
- **Declaring faithfulness on training data only.** Always report held-out faithfulness.
- **Ignoring MLP layers.** Attention heads are easier to interpret, but MLPs often carry critical signal. Test them.
- **Conflating "small effect when patched alone" with "unimportant."** Components in series may each have small individual effects but large joint effects.
