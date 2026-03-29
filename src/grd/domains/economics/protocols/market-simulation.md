# Market Simulation Protocol

## Purpose
Rigorous agent-based simulation of economic markets with heterogeneous participants,
including AI agents with varying rationality models and identity capabilities.

## Steps

1. **Define market structure** — Specify price mechanism, goods, participation rules.
   Lock conventions: `market_structure`, `price_mechanism`, `time_model`.
2. **Specify agent populations** — Define types (human-like, AI, sybil-capable),
   strategy spaces, and population proportions. Lock `agent_rationality`,
   `identity_model`, `agent_population`.
3. **Calibrate parameters** — Use empirical data or theory to set initial endowments,
   valuations, costs. Document calibration sources.
4. **Run baseline** — Simulate without AI agents to establish benchmark.
5. **Introduce treatment** — Add AI agents with specified capabilities. Vary one
   dimension at a time (speed, identity cost, rationality).
6. **Measure outcomes** — Track: prices, allocative efficiency, agent surplus by type,
   market stability (volatility, liquidity), welfare measures.
7. **Sensitivity analysis** — Vary key parameters across meaningful ranges. Report
   which qualitative conclusions are robust.
8. **Statistical validation** — Run sufficient replications for confidence intervals.
   Test for convergence. Report distributional outcomes, not just means.

## Common Pitfalls
- Running too few replications and reporting a single "representative" run.
- Not testing whether results depend on initialization.
- Comparing AI-agent equilibrium to no-AI equilibrium without transient analysis.
- Ignoring that simulation results are conditional on the strategy space modeled.
- Confusing emergent coordination with designed collusion.

## Convention Lock Fields
- `market_structure`, `price_mechanism`, `agent_rationality`, `identity_model`,
  `time_model`, `agent_population`, `simulation_framework`
