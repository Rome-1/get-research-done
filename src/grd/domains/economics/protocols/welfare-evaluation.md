# Welfare Evaluation Protocol

## Purpose
Evaluate the welfare consequences of AI agent participation in economic systems,
distinguishing between efficiency effects and distributional effects.

## Steps

1. **Choose welfare criterion** — Lock `welfare_criterion`. Justify the choice.
   Note that different criteria can give opposite conclusions (total surplus up
   but Gini worse = efficient but inequitable).
2. **Define agent populations** — Identify who benefits and who loses. At minimum
   distinguish: human consumers, human producers, AI agents, AI operators,
   platform operators.
3. **Measure baseline welfare** — Compute welfare metrics in the pre-AI counterfactual.
4. **Measure treatment welfare** — Compute welfare metrics with AI participation.
5. **Decompose effects** — Separate: (a) efficiency gains (larger pie),
   (b) redistribution (same pie, different slices), (c) rent extraction
   (value captured by AI operators), (d) deadweight loss from strategic behavior.
6. **Dynamic analysis** — Short-run effects may differ from long-run. Report both.
   Check whether initial welfare gains are sustained or competed away.
7. **Robustness** — Vary the welfare criterion. Report sensitivity to
   discount rate, population weights, and time horizon.

## Common Pitfalls
- Reporting total surplus increase while ignoring that all gains accrue to AI operators.
- Using Pareto efficiency when the relevant question is distributional.
- Ignoring transition costs (unemployment, skill depreciation) in long-run analysis.
- Treating consumer surplus as welfare-equivalent when consumers are heterogeneous.
- Measuring welfare at equilibrium when the system never reaches equilibrium.

## Convention Lock Fields
- `welfare_criterion`, `agent_population`, `time_model`
