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

## Two Tracks

### Track A: Theory — What Breaks?

Survey and taxonomy of violated assumptions. For each major result in economics,
ask: does the proof still hold when agents can create identities for free, compute
faster than humans, and replicate themselves?

Key targets:
1. **Arrow-Debreu general equilibrium** — assumes unique agents, convex preferences
2. **Mechanism design (Myerson, Maskin)** — assumes sybil-free environments
3. **First/Second welfare theorems** — assume price-taking (but AI agents can manipulate)
4. **Coase theorem** — assumes well-defined property rights over identities
5. **Efficient market hypothesis** — assumes information processing limits
6. **Nash equilibrium existence** — assumes finite strategy spaces
7. **Labor market clearing** — assumes inelastic labor supply

Deliverable: `assumption-taxonomy.md` — table mapping {assumption} × {AI capability that breaks it} × {consequence}

### Track B: Experimental — ACE Simulations

Agent-based computational economics simulations of specific markets with AI
participants. Build on Tesfatsion's ACE methodology — let behavior emerge rather
than imposing equilibrium.

Priority experiments:
1. **Double auction with sybil agents** — How many sybil identities before price manipulation succeeds? What's the welfare cost?
2. **Governance/voting with sybils** — Quadratic voting vs linear voting under sybil attack. At what identity cost does QV become sybil-resistant?
3. **Labor market with AI workers** — Elastic supply + human workers with fixed supply. Wage dynamics as AI marginal cost approaches zero.

Deliverable: Mesa-based simulations with reproducible results.

## Methodological Anchors

- **ACE**: Tesfatsion's agent-based computational economics framework. No imposed equilibrium. Let structure emerge.
- **Mechanism design**: Formal analysis of incentive compatibility under weakened assumptions.
- **Network economics**: Agent interactions on networks, not well-mixed populations.

## Key References (to survey)

- Tesfatsion, L. — ACE homepage and methodology papers
- Douceur, J. (2002) — "The Sybil Attack" (original formalization)
- Myerson, R. — Mechanism design under Bayesian assumptions
- Calvano et al. (2020) — "Artificial Intelligence, Algorithmic Pricing, and Collusion"
- Conitzer, V. — Computational aspects of mechanism design
- Roughgarden, T. — Algorithmic game theory
- Agrawal, Gans, Goldfarb — "Prediction Machines" (economics of AI)
- Korinek & Stiglitz — "Artificial Intelligence and Its Implications for Income Distribution and Unemployment"
