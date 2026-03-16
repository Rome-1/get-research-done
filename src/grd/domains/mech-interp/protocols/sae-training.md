---
load_when:
  - "sparse autoencoder"
  - "SAE"
  - "dictionary learning"
  - "feature dictionary"
  - "SAE training"
  - "sparse features"
  - "superposition"
  - "learned features"
tier: 1
context_cost: medium
---

# SAE Training Protocol

Sparse autoencoders (SAEs) decompose neural network activations into interpretable feature directions. Training them incorrectly produces features that are uninterpretable (noise directions), incomplete (missing important features), or unfaithful (don't reconstruct the original activations well). This protocol covers setup through evaluation.

## Related Protocols

- See `feature-analysis.md` for interpreting trained SAE features
- See `circuit-discovery.md` for using SAE features as circuit nodes
- See `activation-patching.md` for validating feature causal roles

## Before Training

1. **Choose the hook point.** Decide which activation to decompose:
   - **Residual stream** (most common): captures the full representation at a given layer.
   - **MLP output**: isolates MLP computation from attention.
   - **Attention output**: isolates attention patterns.
   - **Post-layer-norm activations**: if the model uses pre-norm architecture, this is the input to attention/MLP.
   - Document the exact hook point name in your framework (e.g., `blocks.6.hook_resid_post` in TransformerLens).

2. **Decide the expansion factor.** The SAE dictionary size relative to the activation dimension:
   - Typical range: 4x to 64x the activation dimension.
   - Larger = more features, finer-grained, but slower training and more dead features.
   - Start with 8x-16x for initial exploration; scale up for comprehensive dictionaries.

3. **Select the SAE architecture.**
   - **ReLU SAE** (vanilla): encoder with ReLU activation, L1 sparsity penalty.
   - **Top-k SAE**: encoder selects the k largest activations, no L1 needed.
   - **Gated SAE**: separate gating and magnitude pathways, reduces shrinkage bias.
   - **JumpReLU SAE**: learnable threshold per feature, reduces dead features.
   - Document the architecture choice and rationale.

4. **Prepare the activation dataset.**
   - Collect activations from a diverse, representative text corpus (e.g., OpenWebText, The Pile).
   - Minimum: 100M-1B tokens for a production SAE; 10M for initial experiments.
   - Store activations to disk to avoid recomputing — activation collection is often the bottleneck.
   - **Normalize activations** if required by your architecture (subtract mean, or apply layer norm).

5. **Set hyperparameters.**
   - Learning rate: 1e-4 to 3e-4 (Adam/AdamW).
   - L1 coefficient (for ReLU SAE): start at 1e-3, tune based on L0 vs reconstruction loss tradeoff.
   - Batch size: 4096-8192 activation vectors.
   - Training steps: enough for multiple passes over the dataset (100K-500K steps typically).

## During Training

1. **Monitor key metrics every 1K steps:**
   - **Reconstruction loss** (MSE): how well the SAE reconstructs activations. Should decrease steadily.
   - **L0** (average number of active features per input): measures sparsity. Target depends on expansion factor — typically 10-100 for 16x expansion.
   - **Dead feature fraction**: features that never activate. Should be <10%; >30% indicates problems.
   - **Explained variance**: fraction of activation variance captured by the SAE. Should be >95% for a good SAE.
   - **Loss recovered**: run the model with SAE-reconstructed activations replacing the originals. Compare final loss to original model loss and zero-ablation loss.

2. **Address dead features proactively.**
   - If dead features exceed 20% early in training, try:
     - Reducing L1 coefficient.
     - Using feature resampling (re-initialize dead features from poorly-reconstructed examples).
     - Switching to Gated or JumpReLU architecture.
   - Never ignore dead features — they waste dictionary capacity.

3. **Check for feature splitting.** As training progresses:
   - Do some features have nearly identical decoder directions (cosine similarity > 0.9)?
   - These may be the same underlying feature split across multiple dictionary elements.
   - Some splitting is expected at high expansion factors; excessive splitting indicates underfitting of L1.

4. **Save checkpoints.** Training can be unstable — save every 10K-50K steps.

## After Training

1. **Compute final evaluation metrics:**
   - Reconstruction MSE on held-out activations.
   - L0 sparsity.
   - Explained variance (R²).
   - Dead feature fraction.
   - Loss recovered (substitute SAE into the model, measure cross-entropy loss).

2. **Validate feature quality (sample check).**
   - For 20-50 random active features:
     - Find the top-10 activating dataset examples.
     - Check: do these examples share an interpretable pattern?
   - Features that activate on unrelated examples are likely noise.

3. **Generate the Pareto frontier.** Train multiple SAEs with different L1 values.
   - Plot L0 (sparsity) vs reconstruction loss.
   - The optimal SAE is on the Pareto frontier — best reconstruction for a given sparsity level.

4. **Test downstream faithfulness.**
   - Use the SAE features in a circuit discovery task.
   - Verify that steering with individual features produces the expected behavioral change.

## Concrete Example: Dead Features from Excessive L1

**Problem:** Train a 16x SAE on GPT-2 Small layer 6 residual stream.

**Wrong approach:** Set L1 coefficient to 0.01 (high) to "encourage sparsity." After 200K steps: L0 = 5, reconstruction MSE is high, 45% of features are dead. The surviving features are overly broad (each covers multiple unrelated concepts) because the SAE was forced to be too sparse.

**Correct approach following this protocol:**

1. Start with L1 = 1e-3. After 50K steps: L0 = 80, dead features = 5%, MSE decreasing steadily.
2. Train three SAEs: L1 ∈ {5e-4, 1e-3, 2e-3}.
3. Plot Pareto frontier: L1 = 1e-3 gives L0 ≈ 50, explained variance = 97%, dead features = 8%.
4. Sample check 30 features: 25/30 have clear interpretable patterns (e.g., "Python code", "names after 'said'", "mathematical notation").
5. Loss recovered: 93% (original loss 3.2 → SAE-substituted loss 3.4 → zero-ablation loss 8.1).

## Common Pitfalls

- **Training on too little data.** SAE features memorize the training set. Use ≥100M tokens for production SAEs.
- **Ignoring dead features.** They silently reduce your effective dictionary size. Always report and address them.
- **Tuning L1 on reconstruction loss alone.** Low reconstruction loss with high L0 means the SAE is not sparse — it's just a good autoencoder, not a dictionary of interpretable features.
- **Not computing loss recovered.** MSE on activations doesn't tell you whether the SAE preserves model behavior. Always test with SAE substituted into the model.
- **Comparing SAEs at different expansion factors without controlling for L0.** A 64x SAE with L0=100 is not "more interpretable" than a 16x SAE with L0=50 — it's using more features per input.
- **Using pre-norm activations when you meant post-norm** (or vice versa). In pre-norm transformers, the residual stream before layer norm has different statistics than after. Document your hook point precisely.
