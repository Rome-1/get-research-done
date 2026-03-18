---
load_when:
  - "error traceability"
  - "which check catches which error"
  - "verification strategy"
  - "mech-interp verification"
tier: 2
context_cost: medium
---

# LLM Mech-Interp Error Traceability Matrix

Maps each error class to the verification checks that can detect it. Use this to design verification strategies for mech-interp analyses.

| Error Class | Patching Direction Check | Metric Consistency | Control Experiments | Ablation Baseline Check | Tokenization Audit | Multi-Example Verification | Causal Validation | Numerical Precision | Code-Description Match |
|---|---|---|---|---|---|---|---|---|---|
| 1. Confusing denoising/noising | ✓ verify base vs patch run | | | | | | | | ✓ check code matches text |
| 2. Wrong residual stream composition | | | | | | | ✓ path patching | | |
| 3. Hallucinating feature interpretations | | | ✓ blind labeling | | | ✓ 20+ examples | ✓ steering test | | |
| 4. Probing as causal evidence | | | ✓ random label control | | | | ✓ ablation must agree | | |
| 5. Wrong ablation baseline | | | | ✓ verify operation matches name | | | | | ✓ code vs description |
| 6. Layer-off-by-one | | | | | | | | | ✓ map hook points |
| 7. Ignoring QKV decomposition | | | | | | | ✓ QKV path patching | | |
| 8. Distribution shift from ablation | | | ✓ compare zero vs mean ablation | ✓ check activation norms | | | | | |
| 9. Superposition vs polysemanticity | | | | | | | | | ✓ terminology check |
| 10. Wrong logit attribution | | ✓ attributions must sum to total | | | | | | ✓ verify summation | |
| 11. Wrong corruption strength | | | ✓ verify P(correct) drops <10% | | | | | | |
| 12. Attention ≠ information flow | | | | | | | ✓ patch attention vs values | | |
| 13. SAE fidelity claims | | ✓ MSE vs loss recovered | | | | | | | |
| 14. Positional effects in patching | | | | | ✓ matched-length prompts | | | | |
| 15. Activation vs importance | | ✓ attribution = act × decoder · W_U | | | | | | | |
| 16. Wrong feature counts | | ✓ specify which count | | | | | | | |
| 17. Not accounting for layer norm | | | | | | | | ✓ include in computation | |
| 18. Assuming feature orthogonality | | ✓ check attributions sum correctly | | | | | | ✓ cosine similarity check | |
| 19. Generalizing from one model | | | ✓ replicate in another model | | | | | | |
| 20. MLP neurons vs features | | | | | | ✓ check polysemanticity | | | |
| 21. Wrong causal scrubbing | | | ✓ structural constraints | | | | | | ✓ distribution matching |
| 22. Misinterpreting negative heads | | | | | | | ✓ check suppression of incorrect | | |
| 23. Token vs sequence analysis | | | | | | ✓ per-position breakdown | | | |
| 24. Wrong component type | | | ✓ test both attn and MLP | | | | | | |
| 25. SAE tradeoff claims | | ✓ report both L0 and loss recovered | | | | | | | |
| 26. Dataset selection bias | | | ✓ test on diverse distribution | | | ✓ varied templates | | | |
| 27. Metric p-hacking | | ✓ pre-register metric | | | | | | | |
| 28. Direct vs indirect effects | | ✓ compare direct and total | | | | | ✓ path patching | | |
| 29. Tokenization inconsistency | | | | | ✓ verify per-example | | | | |
| 30. Dead feature interpretation | | | | | | ✓ check density >0.01% | | | |
| 31. Training data contamination | | | ✓ novel vs memorized inputs | | | | | | |
| 32. Averaging heterogeneous mechanisms | | | | | | ✓ cluster before averaging | | | |
| 33. Temperature/sampling interaction | | | ✓ test at deployment temp | | | | | | |
| 34. Editing ≠ understanding | | | ✓ generalization + specificity | | | | | | |
| 35. BOS token effects | | | | | | | | | ✓ handle BOS separately |
| 36. Pre-trained vs fine-tuned | | | ✓ verify on base model | | | | | | |
| 37. Wrong virtual weights | | | | | | | | ✓ compare to actual output | ✓ check matrix shapes |
| 38. Confirmation bias | | | ✓ blind labeling | | | ✓ report counterexamples | | | |
| 39. Floating point precision | | | | | | | | ✓ stability across runs | |
| 40. Multi-token word attention | | | | | ✓ map tokens to words | | | | |
| 41. Feature overlap | | | | | | ✓ deduplicate by cosine sim | | | |
| 42. Output normalization | | ✓ include final layer norm | | | | | | ✓ verify summation | |
| 43. Single-step tracing | | | ✓ multi-site restoration | | | | | | |
| 44. Not reporting compute | | | | | | | | | |
| 45. Feature cosine similarity | | | ✓ verify on activating examples | | | | | | |
| 46. Loss landscape vs features | | | ✓ compare decompositions | | | | | | |
| 47. Wrong composition analysis | | | | | | | | ✓ compare to path patching | ✓ check matrix order |
| 48. Ignoring skip connections | | | ✓ ablate circuit + check residual | | | | | | |
| 49. Frozen activations | | | | | | | | | ✓ re-run forward pass |
| 50. Frequency ≠ importance | | ✓ measure behavioral effect | | | | | ✓ steering test | | |
