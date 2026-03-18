---
load_when:
  - "probing"
  - "probe"
  - "probing classifier"
  - "linear probe"
  - "diagnostic classifier"
  - "representation analysis"
  - "information content"
tier: 2
context_cost: medium
---

# Probing Protocol

Probing trains simple classifiers (usually linear) on neural network activations to test whether specific information is represented at a given layer. Done incorrectly, probes detect information that the model doesn't actually USE (correlation without causation), overfit to noise, or measure probe capacity rather than representation quality.

## Related Protocols

- See `causal-tracing.md` for causal (not just correlational) evidence of information localization
- See `activation-patching.md` for causal validation of probing results
- See `feature-analysis.md` for understanding what features encode the probed information

## Before Probing

1. **Define the target property precisely.**
   - Binary classification: "does this token's activation encode whether the subject is singular or plural?"
   - Multi-class: "which part of speech does this activation encode?"
   - Regression: "what is the numeric value encoded at this position?"
   - Document the exact label set and how labels are derived from the data.

2. **Construct a balanced, diverse dataset.**
   - Minimum 1000 labeled examples (500 train / 500 test) for binary classification.
   - Balance classes: if one class is 90% of the data, accuracy is meaningless.
   - Diversify contexts: don't probe singular/plural using only "the cat/cats" — use many different nouns in varied sentences.
   - **Critical:** the test set must be disjoint from training in the task-relevant dimension. If probing for word identity, no test word should appear in training. If probing for syntax, use different sentence templates.

3. **Choose the probe architecture.**
   - **Linear probe** (recommended default): logistic regression on activations. Interpretable, limited capacity.
   - **MLP probe**: one hidden layer. More expressive but risks learning the classification itself rather than reading it from the representation.
   - **Control:** train the same probe on random labels. If accuracy is significantly above chance on random labels, the probe has too much capacity.
   - Document the probe architecture and training details (optimizer, epochs, regularization).

4. **Select layers and positions to probe.**
   - Probe ALL layers to see where information emerges and disappears.
   - For each layer, decide which token position to probe:
     - The subject token position (for properties of the subject).
     - The last token position (for information available at prediction time).
     - Document this choice — it affects interpretation.

## During Probing

1. **Train one probe per layer.** Use the same hyperparameters for all layers to ensure fair comparison.

2. **Use cross-validation if data is limited.** 5-fold CV gives more reliable accuracy estimates than a single train/test split.

3. **Train the control probes.** For each probe:
   - **Selectivity control**: train on randomly permuted labels. Accuracy should be near chance. If not, the probe is overfitting or the dataset has spurious correlations.
   - **Complexity control** (optional): compare linear vs MLP probe accuracy. If MLP is much better, the information may be nonlinearly encoded or the linear probe is underfitting.

4. **Record accuracy AND confidence.** Report:
   - Accuracy with 95% confidence intervals (or standard error across folds).
   - Baseline accuracy (majority class or chance level).
   - Selectivity: (probe accuracy - control accuracy).

## After Probing

1. **Plot accuracy by layer.** The characteristic curve shows:
   - Low accuracy in early layers (information not yet extracted).
   - Rising accuracy in mid layers (information being computed).
   - Sustained or dropping accuracy in late layers (information used or discarded).
   - The layer where accuracy first reaches significance is the "emergence" layer.
   - The layer with peak accuracy is where the representation is richest.

2. **Compare to causal evidence.** Probing shows correlation ("the information is present") but not causation ("the model uses this information"). Validate with:
   - Causal tracing: does corrupting these layers affect the model's use of this information?
   - Activation patching: does patching this information change model behavior?
   - If probing says "layer 8 encodes X" but causal tracing says "layer 8 doesn't matter for X," the information may be present but unused.

3. **Report selectivity scores.** For each layer:
   - Selectivity = (true-label accuracy) - (random-label accuracy).
   - Only layers with selectivity > 0.1 have meaningfully encoded representations.

4. **Test generalization.** Does the probe trained on one distribution work on a different distribution?
   - Train on formal text, test on informal text (or vice versa).
   - Poor transfer suggests the probe learned distribution-specific features, not the target property.

## Concrete Example: Probe Overfitting Masquerading as Representation

**Problem:** Does GPT-2 Small encode syntactic tree depth at the residual stream?

**Wrong approach:** Train an MLP probe (256 hidden units) on 200 examples per tree depth (0-5). Report 75% accuracy at layer 8. Conclude: "GPT-2 encodes tree depth."

This is unreliable: a 256-unit MLP can memorize 200 examples, and the control accuracy on random labels was never checked.

**Correct approach following this protocol:**

1. **Dataset:** 5000 examples per depth level, 5 levels, from diverse sentence structures.
2. **Train/test split:** 80/20, ensuring no sentence template appears in both.
3. **Linear probe** with L2 regularization (C=1.0).
4. **Control:** linear probe on random labels → 21% accuracy (near chance for 5 classes).
5. **Results by layer:**
   - Layers 0-3: 25% (near chance).
   - Layers 4-8: rising to 52%.
   - Layers 9-12: declining to 35%.
6. **Selectivity at layer 8:** 52% - 21% = 31% (meaningful).
7. **Causal validation:** mean-ablating layer 8 at the target position disrupts syntactically-sensitive predictions (e.g., subject-verb agreement across relative clauses).
8. **Conclusion:** GPT-2 encodes partial tree depth information, peaking at layer 8, and this information is causally relevant.

## Common Pitfalls

- **No control probes.** Without random-label controls, you cannot distinguish representation quality from probe capacity. ALWAYS run controls.
- **MLP probes without justification.** If a linear probe achieves the same accuracy as an MLP, the information is linearly encoded and the MLP is unnecessary. If the MLP is much better, acknowledge that the information may be hard to extract and the probe itself may be doing nontrivial computation.
- **Probing = "the model knows X."** Probing shows information is present in the representation, not that the model uses it. Always pair with causal evidence.
- **Small datasets.** With <500 examples, linear probes underfit and MLP probes overfit. Use sufficient data.
- **Imbalanced classes.** Report balanced accuracy (average per-class accuracy) rather than raw accuracy when classes are imbalanced.
- **Testing on the same distribution as training.** If all examples share the same sentence template, the probe may learn template-specific features rather than the target property.
