# Agent-Based Computational Economics: Methodology Survey for AI-Agent Research

## What is ACE?

Agent-Based Computational Economics (ACE) is the computational study of economies modeled as evolving systems of autonomous interacting agents. Unlike traditional economic modeling, ACE does not impose equilibrium from above. Instead, it builds an economy from the bottom up: define agents, define their rules of interaction, press play, and observe what emerges.

The foundational framework comes from Leigh Tesfatsion's seven modeling principles (MP1-MP7), which define the ACE approach:

- **MP1 (Agent):** An agent is any software entity that can affect outcomes in its environment through its actions. This includes traders, firms, regulators, and market mechanisms themselves.
- **MP2 (Local constructivity):** An agent's actions at any time are determined by its internal state and its local information. There is no global optimization oracle.
- **MP3 (Autonomy):** Agents act on their own behalf. Their behavior is not dictated by a modeler-imposed objective function applied globally.
- **MP4 (System constructivity):** The state of the world at any time is determined solely by the ensemble of agent states and their interactions. No exogenous equilibrium condition is layered on top.
- **MP5 (Historicity):** The system evolves through time. Past states affect future states. Path dependence is a feature.
- **MP6 (Modularity):** Agents are encapsulated. They interact through well-defined protocols, not shared global state.
- **MP7 (Empirical grounding):** The goal is explanation and prediction, not mathematical elegance. Models should be calibrated against observable phenomena.

### Why ACE is the natural methodology for AI-agent economics

ACE is not merely one option among many for studying AI agents in economic systems. It is the only methodology that does not require assumptions known to be false about AI agents:

1. **AI agents violate equilibrium assumptions.** General equilibrium theory requires agents with stable, well-defined utility functions who reach a fixed point. AI agents update their strategies continuously, may have misaligned objectives, and can exhibit non-stationary behavior. ACE does not need equilibrium to produce results.

2. **Emergent phenomena require simulation.** Algorithmic collusion, herding cascades, flash crashes, and sybil manipulation are emergent properties of multi-agent systems. They cannot be derived analytically because they arise from the nonlinear interaction of heterogeneous strategies. You have to run the simulation and watch them happen.

3. **Heterogeneous populations are native to ABM.** Real AI-affected economies contain humans (slow, bounded-rational, unique identities), AI agents (fast, potentially unbounded, copyable), and sybils (fake identities controlled by a single entity). Agent-based models handle this heterogeneity without any special machinery. Each agent type is just a class with different parameters.

4. **Path dependence and non-convergence are features, not bugs.** When an AI trading agent enters a market and triggers a cascade, the economy may never return to its prior state. ACE treats this as informative. Equilibrium models treat it as a failure of the model.


## ACE vs Traditional Economics for AI-Agent Research

### DSGE (Dynamic Stochastic General Equilibrium)

**What it does well:** DSGE models are the workhorse of macroeconomic policy analysis. They handle intertemporal optimization, stochastic shocks, and provide clean analytical results for monetary and fiscal policy questions. They are well-understood by policymakers and have decades of calibration work behind them.

**Where it fails for AI-agent questions:** DSGE assumes a representative agent (or a small number of agent types) with rational expectations who solves an intertemporal optimization problem. Every one of these assumptions breaks:
- *Representative agent:* AI agents are fundamentally heterogeneous. A GPT-4 trading bot and a human retail investor are not the same agent with different parameters.
- *Rational expectations:* AI agents may be locally rational but are not globally rational in the Muth/Lucas sense. They do not know the true model of the economy.
- *Equilibrium:* Markets with algorithmic agents may not converge. Flash crashes, manipulation cycles, and strategy drift produce non-stationary dynamics.

**When to use alongside ACE:** Use DSGE to establish baseline predictions for what "should" happen in a well-functioning economy, then use ACE to stress-test those predictions when AI agents are introduced. If ACE results converge to DSGE predictions in limiting cases (e.g., when all agents are identical and rational), that validates the ACE model. When they diverge, the divergence is the finding.

### Analytical Game Theory

**What it does well:** Game theory provides clean, provable results about strategic interaction. It characterizes Nash equilibria, identifies dominant strategies, and can prove impossibility results (e.g., Gibbard-Satterthwaite on strategy-proofness). For mechanism design, it is indispensable.

**Where it fails for AI-agent questions:** Analytical game theory requires finite, well-defined strategy spaces and payoff functions. AI agents violate both:
- *Strategy spaces:* An LLM-based trading agent's strategy space is effectively the space of all possible text completions. This is not a finite game.
- *Payoff calculation:* Finding Nash equilibria in games with many players and large strategy spaces is computationally intractable (PPAD-complete). You cannot solve for the equilibrium; you can only simulate.
- *Bounded rationality:* Game theory assumes agents can compute best responses. AI agents use heuristics, learned policies, and prompt-driven reasoning that may be systematically biased.

**When to use alongside ACE:** Use game theory to analyze the mechanism (e.g., prove that a voting rule is strategy-proof against a single manipulator), then use ACE to test what happens when agents are boundedly rational, when there are multiple coordinated manipulators, and when the mechanism is embedded in a larger system. Game theory provides the theoretical upper bound on mechanism performance; ACE provides the realistic estimate.

### Empirical Methods

**What they do well:** Empirical economics (econometrics, natural experiments, RCTs) provides ground truth. It tells us what actually happened. For AI-agent questions where data exists (e.g., the effect of algorithmic trading on market quality), empirical methods are the gold standard.

**Where they fail for AI-agent questions:** Most of the important questions about AI agents in economic systems concern phenomena that have not yet occurred at scale:
- What happens when 80% of market participants are AI?
- What happens when sybil attacks on voting systems become cheap?
- What happens when AI workers can do most cognitive tasks at near-zero marginal cost?

You cannot run a regression on data from a future that has not happened. You cannot run an RCT on a systemic economic transition.

**When to use alongside ACE:** Use empirical data to calibrate ACE model parameters and to validate ACE predictions against known outcomes. For example, calibrate trading agent parameters against observed bid-ask spreads and volatility in real markets with known algorithmic participation. When ACE produces predictions about future scenarios, empirical data from partial precedents (early algorithmic trading, existing bot activity on platforms) serves as a sanity check.


## Software Frameworks for ACE

### Mesa (Python)

Mesa is the most widely used Python framework for agent-based modeling. It provides a modular architecture with agent schedulers, spatial grids, network topologies, and a built-in data collection and visualization server.

**Strengths:**
- Native Python: integrates directly with NumPy, pandas, scikit-learn, and LLM APIs (OpenAI, Anthropic SDKs)
- Active development and community
- Built-in batch runner for parameter sweeps
- Browser-based visualization for debugging and presentation
- Straightforward to extend with custom agent types

**Limitations:**
- Pure Python performance ceiling for very large simulations (>100k agents)
- Visualization server is useful but not publication-quality

### NetLogo

A mature platform designed for education and exploratory modeling, with a visual programming interface and a large model library.

**Strengths:** Low barrier to entry, excellent for building intuition, large existing model library.
**Limitations:** Poor fit for complex agent logic (AI agents with LLM calls), limited scalability, proprietary language.

### Repast (Java/C++)

Repast Simphony is a mature, enterprise-grade ABM toolkit with strong support for large-scale distributed simulations.

**Strengths:** Battle-tested at scale, good parallel execution support, GIS integration.
**Limitations:** Java ecosystem adds friction for data science workflows, heavier setup overhead.

### MASON (Java)

A minimalist, high-performance simulation library focused on speed.

**Strengths:** Very fast execution, clean API, good for pure simulation workloads.
**Limitations:** Minimal built-in analysis tools, Java-only, small community.

### AgentPy (Python)

A newer Python framework with a clean API inspired by Mesa but with some design improvements.

**Strengths:** Clean API, good documentation, integrates with EMA Workbench for sensitivity analysis.
**Limitations:** Smaller community than Mesa, less battle-tested.

### Recommendation for this project: Mesa

For studying AI agents in economic systems, Mesa is the clear choice:

1. **LLM integration:** Our AI agents need to call LLM APIs. Python makes this trivial. Java-based frameworks would require HTTP clients and JSON parsing for every agent decision.
2. **Data analysis pipeline:** Results flow directly into pandas DataFrames for analysis and matplotlib/seaborn for visualization.
3. **Rapid prototyping:** We need to iterate fast on experimental designs. Mesa's simplicity supports this.
4. **Reproducibility:** Mesa models are pure Python scripts that can be version-controlled, reviewed, and run by anyone with a Python environment.

For simulations that hit Python's performance ceiling, we can profile and rewrite hot paths in Cython or move the inner loop to a compiled language while keeping Mesa as the orchestration layer.


## Proposed Experimental Design

### Experiment 1: Double Auction with Sybil Agents

**Research question:** How does sybil capability affect market efficiency and surplus distribution in a continuous double auction?

**Environment:**
- Continuous double auction (CDA) for a single homogeneous good
- Time runs in discrete ticks; each tick, agents may submit/cancel limit orders
- Order book with price-time priority matching
- Each agent has a private valuation drawn from a known distribution
- Market runs for T periods per trial; R independent replications per parameter setting

**Agent types:**

| Type | Count | Behavior | Identity |
|------|-------|----------|----------|
| Honest human-like | N_h (e.g., 50) | Zero-intelligence-plus (ZI-C) or simple adaptive | 1 identity each |
| Sybil-capable AI | N_s (e.g., 5) | Strategic, can create up to k identities | Pays cost c per additional identity |

Honest agents use bounded-rational strategies (ZIP or GD traders from the experimental economics literature). Sybil agents can split their endowment across k identities, submit coordinated orders to manipulate the order book (spoofing, layering, wash trading).

**Treatment variable:** Identity cost c(k), swept from high (c = full_endowment, effectively sybil-proof) down to zero (free identity creation).

**Measurements:**
- **Price efficiency:** Root-mean-square deviation of transaction prices from competitive equilibrium price
- **Allocative efficiency:** Ratio of realized total surplus to maximum possible surplus (Gini coefficient of surplus distribution)
- **Surplus by type:** Average profit per honest agent vs. average profit per sybil agent (pre and post identity costs)
- **Market volatility:** Standard deviation of transaction prices within each period
- **Order book health:** Bid-ask spread, depth at best quotes, frequency of empty books

**Hypothesis:** There exists a critical identity cost c* below which sybil manipulation succeeds and allocative efficiency drops discontinuously (phase transition). Above c*, the market functions approximately as if all agents are honest. Below c*, sybil agents extract surplus from honest agents through order book manipulation, and the magnitude of extraction increases as c approaches zero.

**Controls:**
- Baseline: same market with zero sybil agents (pure honest population)
- Positive control: analytical competitive equilibrium price computed from agent valuations

**Parameter sweep:**
- c in {0, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0} * endowment
- k_max in {1, 2, 5, 10, 50}
- N_h in {20, 50, 100}
- R >= 30 replications per cell

### Experiment 2: Governance/Voting Under Sybil Attack

**Research question:** Which voting mechanisms are most resistant to sybil attacks, and how does resistance degrade as identity cost decreases?

**Environment:**
- Collective decision problem: a group must choose a public good provision level x in [0, 1]
- Each agent has a preferred level x_i drawn from a distribution (e.g., Beta(2, 5) to create realistic skew)
- Agent utility is a quadratic loss: u_i(x) = -(x - x_i)^2
- Decision is made via a voting mechanism, then all agents receive the outcome

**Voting mechanisms tested:**

| Mechanism | Rule | Sybil vulnerability |
|-----------|------|-------------------|
| One-person-one-vote (1p1v) | Median of reported preferences | Linear: k sybils = k votes |
| Quadratic voting (QV) | Agents buy votes at quadratic cost; outcome = weighted median | Sublinear: k sybils cost k * c but influence grows as sqrt(budget_per_identity) |
| Conviction voting (CV) | Agents stake tokens on preferences; conviction accumulates over time | Time-dependent: sybils must sustain stake across periods |

**Agent types:**

| Type | Count | Behavior |
|------|-------|----------|
| Honest voters | N (e.g., 100) | Report true preference x_i |
| Sybil attacker | 1 entity | Wants to shift outcome toward x_a; controls k identities, distributes budget across them |

**Treatment variables:**
- Number of sybil identities k in {1, 2, 5, 10, 20, 50}
- Attacker budget B in {1x, 2x, 5x, 10x} median honest agent budget
- Identity cost c per sybil identity

**Measurements:**
- **Outcome deviation:** |x_decided - x_honest| where x_honest is the outcome with zero sybils
- **Cost-effectiveness of attack:** Outcome deviation per unit attacker expenditure (including identity costs)
- **Mechanism-specific sybil resistance:** For each mechanism, the attacker budget required to shift the outcome by delta = 0.1
- **Welfare loss:** Total utility loss of honest agents relative to honest-only outcome

**Hypothesis:** Quadratic voting is more sybil-resistant than linear voting (1p1v) because splitting budget across identities is suboptimal under quadratic costs. However, QV still breaks at sufficiently low identity cost, because the attacker can create enough identities to effectively linearize their influence. Conviction voting provides time-based resistance that is orthogonal to identity cost, making it the most robust mechanism when identity is cheap but patience is costly.

**Controls:**
- Baseline: zero sybils, each mechanism produces the honest outcome
- Analytical benchmark: for 1p1v and QV, compute the optimal sybil strategy analytically and compare with agent behavior

### Experiment 3: Labor Market with AI Workers

**Research question:** What are the equilibrium and transitional dynamics of a labor market where AI workers enter with elastic supply and improving quality?

**Environment:**
- Matching market for cognitive tasks (e.g., writing, coding, analysis, design)
- Tasks arrive each period with a quality requirement q_min and a value v(q) that increases in quality delivered
- Workers are matched to tasks via a decentralized matching process (agents post prices, firms select)
- Each period represents a quarter; simulation runs for 40 periods (10 years)

**Agent types:**

| Type | Properties |
|------|-----------|
| Human workers (N_h = 200) | Fixed supply; skill q_i drawn from LogNormal(mu, sigma); wage reservation w_r proportional to outside option; can improve skill slowly (learning by doing) |
| AI workers (elastic supply) | Marginal cost c_AI (treatment variable); quality q_AI(t) that improves over time following a sigmoid (slow start, rapid improvement, plateau); no supply constraint |
| Firms (N_f = 100) | Post task with value v and quality requirement; hire cheapest worker meeting quality threshold; maximize profit = v(q) - wage |

**Treatment variable:** AI marginal cost c_AI, swept from expensive (10x median human wage) to near-zero (0.01x median human wage). AI quality trajectory q_AI(t) is fixed across treatments (exogenous technological progress).

**Measurements:**
- **Human wages by skill quantile:** Track 10th, 25th, 50th, 75th, 90th percentile human wages over time
- **Human employment rate:** Fraction of human workers matched to tasks each period
- **Total output:** Sum of v(q) across all completed tasks
- **Gini coefficient:** Income inequality among all workers (human + AI) and among humans only
- **Consumer surplus:** Difference between task value and price paid by firms
- **Task composition:** Fraction of tasks done by humans vs. AI, by task quality tier

**Hypothesis:** There exist three distinct phases as AI cost decreases:

1. **Complementary phase** (c_AI > median human wage): AI takes tasks that humans cannot do (quality above human maximum) or tasks that are not cost-effective for humans. Human wages rise because AI increases total output and creates new task categories. Employment is stable or rising.

2. **Substitution phase** (c_AI approaches median human wage): AI begins competing directly with median-skill humans. Low-skill human wages fall. High-skill humans still earn premiums for tasks where AI quality is insufficient. Employment begins to decline for the bottom skill quartiles. Gini rises.

3. **Displacement phase** (c_AI << median human wage): AI is cheaper than most humans for most tasks. Human employment drops sharply for all but the highest-skill workers. Remaining human employment is concentrated in tasks requiring qualities AI lacks (e.g., physical presence, legal personhood, trust). Total output is high. Consumer surplus is high. Human labor income share is low.

The transitions between phases are predicted to be relatively sharp (occurring over 2-4 periods) rather than gradual, because of positive feedback: as AI takes more tasks, humans lose learning-by-doing opportunities, further widening the quality-cost gap.

**Controls:**
- Baseline: zero AI workers (pure human labor market)
- Partial treatment: AI quality is fixed (no improvement over time) to isolate the effect of cost reduction from quality improvement


## Validation Strategy

ACE simulations are only useful if they are credible. Validation is not optional.

### 1. Reproduce known analytical results in limiting cases

Every ACE model should converge to known theoretical predictions when its assumptions match those of the theory:

- **Double auction (Experiment 1):** With zero sybil agents and many honest ZI-C traders, transaction prices should converge to the competitive equilibrium (Smith, 1962). Allocative efficiency should approach 100% as the number of traders grows.
- **Voting (Experiment 2):** With zero sybils, 1p1v should produce the median voter outcome. QV should produce the utilitarian optimum (Lalley and Weyl, 2018) in the limit of many voters.
- **Labor market (Experiment 3):** With zero AI workers, the matching market should produce wages approximately equal to workers' marginal products, sorted by skill.

If the model does not reproduce these baselines, there is a bug. Fix it before running treatments.

### 2. Sensitivity analysis across parameter ranges

For each experiment, identify the key parameters and sweep them systematically:

- Run each parameter combination with R >= 30 independent replications (different random seeds)
- Report means, standard deviations, and confidence intervals
- Identify phase transitions and tipping points (sudden changes in outcomes as a function of continuous parameter changes)
- Test robustness to distributional assumptions (e.g., does the sybil threshold depend on the valuation distribution?)

Use the EMA Workbench or a custom batch runner to automate parameter sweeps.

### 3. Multiple independent replications

All results must be reported with uncertainty quantification:

- Within-run variation: standard error across time periods within a single run
- Between-run variation: standard error across independent replications with different random seeds
- Report both. If between-run variation is large, the system has multiple attractors or is sensitive to initial conditions. This is a finding, not a problem.

### 4. Compare with empirical data where available

For each experiment, identify the closest real-world analog and calibrate:

- **Double auction:** Calibrate against experimental economics data (e.g., Vernon Smith's CDA experiments). Also calibrate AI agent speed and strategy against observed algorithmic trading behavior (HFT order-to-trade ratios, quote stuffing frequencies).
- **Voting:** Calibrate honest voter preference distributions against survey data. Calibrate attacker budget against observed costs of sybil attacks on real platforms (e.g., social media bot networks, cryptocurrency governance attacks).
- **Labor market:** Calibrate human skill distributions against wage data (BLS Occupational Employment Statistics). Calibrate AI quality trajectory against observed AI benchmark performance over time (e.g., MMLU scores, SWE-bench, coding competition results).

### 5. Cross-validation between experiments

The three experiments are not independent. Insights should transfer:

- The sybil cost threshold from Experiment 1 should inform the identity cost assumptions in Experiment 2
- The AI cost trajectory from Experiment 3 should inform the computational advantage assumptions in Experiment 1
- The governance mechanisms from Experiment 2 should be testable as market regulation mechanisms in Experiment 1

Building these cross-links into the experimental design from the start strengthens all three experiments.

### 6. Adversarial validation

For each experiment, actively try to break the results:

- Find parameter settings where the model produces absurd outcomes and explain why
- Test edge cases: zero agents, one agent, all agents identical
- Invite domain experts to propose scenarios they expect will produce specific outcomes, and test whether the model agrees
- Publish the model code and invite replication

A model that survives adversarial testing is worth taking seriously. One that has only been run with "reasonable" parameters is not.
