# When Agents Transact: How Autonomous AI Breaks Economic Assumptions

## Thesis

The introduction of AI agents capable of autonomous digital transactions violates
foundational assumptions across microeconomics, macroeconomics, and mechanism design.
The most consequential violations stem from three capabilities classical economics
never anticipated: **near-zero identity cost** (sybil capability), **elastic labor
supply** (replicable agents), and **superhuman transaction speed** (machine-speed
markets). These aren't incremental changes — they break the preconditions of
major theorems (Arrow-Debreu, revelation principle, welfare theorems) and create
novel failure modes (algorithmic collusion, governance capture, velocity spirals).

## Status (2026-03-29)

Two rounds of peer review and revision completed. Core taxonomy stable. Five deep
dives written. Three simulations implemented and validated. Round 2 synthesis review
in progress.

## Document Map

### Core Theory
- **[assumption-taxonomy.md](assumption-taxonomy.md)** — 14-entry taxonomy of violated assumptions, severity-rated with explicit rubric. Includes interaction matrix (5×5 capability compound analysis), relation to prior work (Parkes & Wellman 2015), and cross-references to all deep dives. *Second draft — post-review revision.*
- **[literature-map.md](literature-map.md)** — 40+ references across general equilibrium, mechanism design, game theory, sybil attacks, algorithmic collusion, ACE, labor, monetary, network economics, principal-agent theory, prediction markets, and practical sybil resistance.
- **[ace-methodology-survey.md](ace-methodology-survey.md)** — ACE overview (Tesfatsion MP1-MP7), comparison with DSGE/analytical game theory, software frameworks, experimental designs, validation strategy.

### Deep Dives
- **[deep-dives/positive-sum-effects.md](deep-dives/positive-sum-effects.md)** — Balanced analysis: when/how AI agents improve outcomes (efficiency, transaction costs, labor matching). Conditions for net positive vs net negative.
- **[deep-dives/interaction-effects.md](deep-dives/interaction-effects.md)** — 6 pairwise + 1 triple compound analysis of how violations amplify each other (Sybil×Speed, Speed×Correlated, etc.).
- **[deep-dives/principal-agent-ai.md](deep-dives/principal-agent-ai.md)** — Formal P-A framework (Holmstrom, Grossman & Hart) applied to AI deployment. Moral hazard, adverse selection, monitoring, liability.
- **[deep-dives/sybil-resistance-mechanisms.md](deep-dives/sybil-resistance-mechanisms.md)** — Survey of defenses: Worldcoin, Gitcoin Passport, BrightID, Idena, stake-based, reputation. Evaluated against AI agents.
- **[deep-dives/prediction-markets-attention.md](deep-dives/prediction-markets-attention.md)** — How AI agents break information aggregation (Condorcet Jury Theorem) and transform attention economics.

### Simulations (ACE Track)
- **[simulations/sybil_auction.py](simulations/sybil_auction.py)** — Mesa CDA with sybil traders. Cross-side strategy, surplus extraction.
- **[simulations/sybil_governance.py](simulations/sybil_governance.py)** — 1p1v vs QV (Lalley & Weyl 2018) vs conviction voting under sybil attack.
- **[simulations/labor_market.py](simulations/labor_market.py)** — Labor market with elastic AI supply, logistic quality growth, three-phase dynamics.

### Reviews
- **[reviews/round1-theory-review.md](reviews/round1-theory-review.md)** — Identified: one-sidedness, missing interactions, literature gaps (Parkes & Wellman, P-A, DeFi sybil resistance).
- **[reviews/round1-simulation-review.md](reviews/round1-simulation-review.md)** — Identified: inert sybil strategy, non-standard QV, conviction voting time advantage bug, linear AI growth.
- **[reviews/round2-synthesis-review.md](reviews/round2-synthesis-review.md)** — *(in progress)*

## Two Tracks

### Track A: Theory — What Breaks (and What Improves)?

Survey and taxonomy of violated assumptions. For each major result in economics:
does the proof still hold when agents can create identities for free, compute
faster than humans, and replicate themselves? AND: under what conditions do AI
agents actually improve economic outcomes?

Key targets (all addressed in taxonomy):
1. **Arrow-Debreu general equilibrium** — sybils break finite agent assumption (High)
2. **Mechanism design (VCG, Myerson, Maskin)** — sybil-vulnerable without identity layer (Critical)
3. **First/Second welfare theorems** — coordinated sybils are price-makers (Critical/High)
4. **Revelation principle** — mutable types, endogenous preferences (Critical)
5. **Quadratic voting** — degenerates to plutocracy with cheap identity (Critical)
6. **Coase theorem** — identity as property right is undefined (High)
7. **Efficient market hypothesis** — correlated strategies vs improved arbitrage (High)
8. **Nash equilibrium** — endogenous player sets (High)
9. **Labor market clearing** — elastic AI labor supply (Critical)
10. **Quantity theory of money** — machine-speed velocity (High)

### Track B: Experimental — ACE Simulations

Agent-based simulations of specific markets with AI participants.

Completed experiments:
1. **Double auction with sybil agents** — Cross-side sybil strategy extracts surplus via artificial liquidity
2. **Governance/voting with sybils** — Conviction voting ~10x more resistant than 1p1v; QV linearization attack confirmed
3. **Labor market with AI workers** — Three phases visible (complementary→substitution→displacement); high-skill workers retain wages

## Methodological Anchors

- **ACE**: Tesfatsion's agent-based computational economics framework. No imposed equilibrium.
- **Mechanism design**: Formal analysis of incentive compatibility under weakened assumptions.
- **Principal-agent theory**: Holmstrom/Grossman-Hart framework for deployer-AI relationships.
- **Network economics**: Agent interactions on networks, not well-mixed populations.

## Key References

- Parkes, D. & Wellman, M. (2015) — "Economic Reasoning and AI" (Science) — closest antecedent
- Tesfatsion, L. — ACE homepage and methodology papers
- Douceur, J. (2002) — "The Sybil Attack" (original formalization)
- Holmstrom, B. (1979), Grossman & Hart (1983) — principal-agent foundations
- Calvano et al. (2020) — "AI, Algorithmic Pricing, and Collusion" (AER)
- Conitzer & Sandholm (2006) — VCG failures in combinatorial settings
- Lalley & Weyl (2018) — Quadratic voting theory
- Yokoo et al. (2004) — false-name-proof combinatorial auctions
