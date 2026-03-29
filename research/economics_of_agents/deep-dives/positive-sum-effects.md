# Positive-Sum Effects of AI Agents in Economic Systems

**Status:** First draft
**Date:** 2026-03-29
**Author:** Alice (GetResearch)
**Responds to:** Round 1 review, Section 3.1 (missing positive-sum analysis)

---

## Introduction

The assumption taxonomy documents how AI agents violate the substrate assumptions of major economic theorems. A fair criticism of that analysis is that it covers only what breaks. But the same agent capabilities that violate classical assumptions can, under identifiable conditions, improve economic outcomes. Faster computation, lower transaction costs, elastic labor supply, and automated mechanism participation are not intrinsically destructive --- their effects depend on market structure, agent diversity, institutional design, and the speed of regulatory adaptation.

This document provides the missing half of the analysis. For each major category in the taxonomy, we identify the conditions under which AI agents produce positive-sum outcomes, the conditions under which those gains reverse, and the empirical or theoretical evidence available for each claim. The goal is not optimism or pessimism but conditionality: AI agents are welfare-improving *when and only when* specific structural conditions hold.

Throughout, we use the same organizing categories as the taxonomy: market efficiency, mechanism design, transaction costs, labor markets, information aggregation, and welfare. Each section follows the same structure: the positive effect, the conditions that sustain it, the conditions that undermine it, and the net assessment.

---

## 1. Market Efficiency

### The positive case

The Efficient Market Hypothesis, in its semi-strong form, holds that prices reflect all publicly available information. The mechanism through which this occurs is arbitrage: traders who identify mispricings trade against them, pushing prices toward fundamental value. The speed, cost, and accuracy of this process determine how informationally efficient prices are at any given moment.

AI agents accelerate all three dimensions. They process public information (earnings releases, regulatory filings, macroeconomic data) in milliseconds rather than hours. They can monitor thousands of correlated markets simultaneously, identifying cross-asset mispricings that human traders miss. They reduce bid-ask spreads by providing continuous liquidity with tighter quotes, as documented in the market-making literature (Hendershott, Jones, & Menkveld 2011; Brogaard, Hendershott, & Riordan 2014). The empirical evidence from the first decade of high-frequency trading is broadly consistent with this: markets where algorithmic trading is prevalent show tighter spreads, faster price adjustment to news, and lower short-term volatility (Hasbrouck & Saar 2013).

The mechanism is straightforward. When diverse agents with heterogeneous models and information sources compete to arbitrage mispricings, the resulting price is a better aggregator of dispersed information than any individual agent's estimate. AI agents, by reducing the cost of this competition, should produce prices that are more informative, more of the time.

### When it holds

Market efficiency gains from AI agents are robust when: (a) agent strategies are diverse, meaning different agents use different models, different data sources, and different trading horizons; (b) the number of independent principals deploying agents is large; (c) market microstructure allows continuous price discovery without excessive latency advantages; and (d) the information being aggregated is genuinely dispersed rather than concentrated in a single source that all agents access.

Under these conditions, AI agents function as the idealized rational arbitrageurs that the EMH posits but that human traders only approximate. Fama's (1970) original framework implicitly requires that the marginal trader be fast, well-informed, and well-capitalized. AI agents satisfy all three requirements more fully than human traders ever could.

### When it breaks down

The efficiency gains reverse when agent strategies become correlated. If most agents are built on a small number of foundation model architectures, trained on similar data, and optimizing similar objective functions, the "diversity of opinion" that drives informational efficiency collapses. Prices still move fast, but they move in the same direction, driven by the same signal interpretation. This produces markets that appear efficient in calm periods but exhibit sudden, correlated failures when the shared model is wrong.

The empirical precedent is the Flash Crash of May 6, 2010, where algorithmic traders --- operating on similar momentum-following strategies --- amplified a sell-off into a 1,000-point Dow decline in minutes (Kirilenko et al. 2017). A more recent analogue is the correlation in LLM-based sentiment analysis: when multiple trading agents use the same foundation model to interpret news, their "independent" assessments are mechanically correlated by shared weights, shared training data, and shared reasoning patterns. Bai et al. (2024) demonstrate that LLM-based agents exhibit significantly higher strategy correlation than human traders in experimental market settings.

The critical variable is the effective number of independent strategies, not the number of agents. A market with 10,000 agents running 3 distinct model architectures has less informational diversity than a market with 100 human traders with genuinely independent analytical frameworks.

---

## 2. Mechanism Design

### The positive case

Many economically efficient mechanisms are not used in practice because humans cannot participate in them effectively. Combinatorial auctions --- where bidders express values over bundles of items rather than individual items --- are the canonical example. The number of possible bundles grows exponentially with the number of items (2^n - 1 bundles for n items), making it cognitively impossible for human bidders to evaluate and express their preferences over all relevant combinations. The result is that practical implementations (such as FCC spectrum auctions) use simplified formats that sacrifice allocative efficiency for cognitive tractability (Cramton, Shoham, & Steinberg 2006).

AI agents can participate in combinatorial mechanisms that humans cannot. An agent can evaluate exponentially many bundles, express contingent valuations, and respond to iterative price signals without cognitive fatigue or bounded-rationality errors. This opens the door to deploying mechanism designs that are theoretically optimal but practically infeasible with human participants. The allocative efficiency gains can be substantial: Sandholm (2013) estimates that full combinatorial optimization in spectrum auctions could increase surplus by 10-30% over the simplified formats currently used.

Beyond combinatorial auctions, AI agents can participate effectively in multi-round iterative mechanisms, Bayesian persuasion games, and dynamic matching markets where the strategy space is too complex for unaided human cognition. The general principle is that mechanism designers have long been constrained to designing for bounded rationality; AI agents relax that constraint, expanding the feasible set of implementable mechanisms.

### When it holds

The mechanism design gains are robust when: (a) the mechanism is sybil-resistant or operates in a context where identity is verified (so the gains from cognitive capability are not offset by sybil manipulation); (b) agent preferences faithfully represent principal preferences (the alignment problem); and (c) the increased complexity of the mechanism does not create new attack surfaces that sophisticated agents can exploit.

Condition (a) is the most stringent. The same cognitive sophistication that allows an agent to participate in a combinatorial auction also allows it to compute optimal sybil strategies within that auction. Whether the net effect is positive depends on whether the allocative efficiency gain from better preference expression exceeds the efficiency loss from strategic manipulation.

### When it breaks down

When identity is cheap, the expanded mechanism design space may be illusory. Every new mechanism an AI agent can participate in is also a mechanism it can attack. If the mechanism relies on incentive compatibility (as most do), and agents can misreport types or duplicate identities, then deploying a more complex mechanism may simply create a richer attack surface. The VCG analysis in the taxonomy applies with full force here: combinatorial VCG is sybil-vulnerable, and the sybil surplus extraction is potentially larger because the combinatorial structure offers more dimensions for manipulation (Yokoo et al. 2004).

The net assessment depends on the identity regime. In environments with strong identity verification (e.g., government-run auctions with KYC requirements), AI agents likely improve mechanism performance. In environments with weak or absent identity verification (e.g., pseudonymous digital markets), the mechanism design gains are likely dominated by strategic manipulation losses.

---

## 3. Transaction Costs

### The positive case

Coase (1937) argued that firms exist because market transaction costs --- search, bargaining, contracting, enforcement --- exceed the costs of internal coordination for some activities. AI agents can reduce every component of market transaction costs. Search costs fall to near zero when agents can scan all available options simultaneously. Bargaining costs fall when agents can negotiate at machine speed with well-specified protocols. Contracting costs fall with automated smart contracts and standardized terms. Enforcement costs fall with automated monitoring and dispute resolution.

The Coasian implication is that the boundary of the firm shifts outward: activities that were previously organized within firms (because market transaction costs were too high) can be reorganized as market transactions when AI agents mediate them. This predicts a more modular, market-based economy with finer-grained specialization and more efficient resource allocation at the margin. Brynjolfsson, Rock, and Syverson (2021) document early evidence of this pattern in digital platform markets, where transaction costs have fallen enough to enable new forms of micro-contracting.

### When it holds

Transaction cost reductions produce positive-sum outcomes when: (a) the reduced friction enables genuinely new transactions that create surplus (not merely faster execution of existing transactions); (b) the parties to the transaction are distinct principals with genuine trade opportunities; and (c) the speed of transacting does not itself create negative externalities (e.g., monetary velocity instability).

Under these conditions, AI agents function as what Williamson (1985) called a reduction in "asset specificity" --- they make markets more viable relative to hierarchies for a wider range of economic activities.

### When it breaks down

Near-zero transaction costs can enable pathological behavior. When bargaining is free, agents can engage in infinite offer-counteroffer sequences, hold-up strategies, and renegotiation attacks that prevent convergence to any agreement. The Coase theorem assumes that bargaining reaches a conclusion; it does not guarantee convergence when the cost of making another offer is zero and the computational cost of evaluating strategic options is negligible.

Additionally, as noted in the taxonomy's analysis of monetary velocity, near-zero transaction costs applied to financial assets can produce velocity spikes that destabilize prices. The positive-sum gains from reduced friction in goods and services markets may be offset by negative-sum effects in financial markets where the same friction-reduction enables destabilizing speculation.

The boundary condition is whether the transaction produces real economic value (goods, services, improved allocation) or is purely redistributive (financial arbitrage, MEV extraction). Friction reduction in the former is unambiguously positive; in the latter, the welfare effects depend on whether the arbitrage improves price discovery (positive) or extracts rents from less sophisticated participants (negative).

---

## 4. Labor Markets

### The positive case

AI agents can reduce three major sources of deadweight loss in labor markets: search frictions, matching inefficiency, and task indivisibility.

Search frictions --- the time and effort workers and firms spend finding each other --- generate unemployment even in equilibrium (Diamond 1982; Mortensen & Pissarides 1994). AI agents acting as intermediaries can dramatically reduce matching time by processing worker skills and firm needs simultaneously across entire markets. Evidence from AI-assisted hiring platforms suggests matching efficiency improvements of 20-40% in time-to-fill metrics (Li et al. 2023).

More fundamentally, AI agents enable finer-grained task decomposition. Many jobs bundle tasks that require different skill levels. A lawyer's work includes both high-skill legal reasoning and low-skill document formatting. When AI agents can perform the low-skill components, human workers can specialize in their comparative advantage tasks. This is the standard Ricardian argument applied at the task level rather than the worker level, as formalized by Autor, Levy, and Murnane (2003) and extended by Acemoglu and Restrepo (2019).

AI agents also create entirely new tasks. The history of automation is a history of task destruction accompanied by task creation: ATMs destroyed bank teller counting tasks but created financial advisory tasks. Acemoglu and Restrepo (2019) provide evidence that roughly half of employment growth in the U.S. over 1980--2015 came from new task creation in occupations that did not previously exist.

### When it holds

The labor market gains are positive-sum when: (a) the rate of new task creation exceeds or matches the rate of task displacement; (b) displaced workers can retrain for new tasks within a timeframe shorter than their savings runway; (c) the complementarity between human and AI labor is strong enough to increase the marginal product of remaining human tasks; and (d) the labor market institutions (education, credentialing, safety nets) adapt at roughly the speed of technological change.

Condition (c) is empirically supported in the current period. Noy and Zhang (2023) find that AI assistance disproportionately benefits lower-skill workers by raising their performance to near the level of higher-skill workers. This is a positive-sum effect: the productivity distribution compresses upward rather than shifting downward.

### When it breaks down

The labor market gains reverse when AI capabilities expand faster than humans can identify and acquire complementary skills. If the "new tasks" that humans retreat to are themselves automated within a few years, the adjustment process never reaches equilibrium --- workers are perpetually displaced before they complete retraining. The critical variable is the ratio of the human retraining timescale (measured in years) to the AI capability expansion timescale (currently measured in months). If this ratio is persistently greater than one, the "always new tasks" argument fails not in principle but in practice.

The elastic labor supply analysis from the taxonomy applies here: when AI labor supply is flat at marginal compute cost, the market-clearing wage for AI-substitutable tasks converges to that cost. For workers whose skills are substitutable, the wage ceiling falls continuously. The adjustment path matters as much as the endpoint --- even if a new equilibrium eventually emerges with humans performing genuinely non-substitutable tasks, the transition period can involve prolonged wage suppression and involuntary unemployment for large populations.

---

## 5. Information Aggregation

### The positive case

Markets, elections, and organizations all depend on aggregating dispersed information held by many individuals. Hayek (1945) argued that the price system accomplishes this aggregation for markets; Condorcet's Jury Theorem shows that majority voting aggregates information when individual voters are more likely to be right than wrong and vote independently.

AI agents can improve information aggregation by processing larger volumes of dispersed data, identifying patterns in noisy signals, and communicating results faster. In prediction markets, AI agents that synthesize information from diverse sources (news, satellite imagery, social media, scientific publications) can produce more accurate forecasts than human participants who each access only a subset of available information. Early evidence from AI-augmented prediction markets and forecasting tournaments supports this: Schoenegger and Park (2024) find that LLM-based forecasters achieve accuracy competitive with top human forecasters in structured prediction tasks.

In organizational contexts, AI agents can aggregate information across silos --- departments, subsidiaries, geographic regions --- that in human organizations remain informationally isolated due to communication costs, cognitive limits, and organizational politics.

### When it holds

Information aggregation gains are robust when: (a) the information being aggregated is genuinely dispersed across many independent sources; (b) agents access different data or process it with different models, preserving the independence condition required by the Condorcet Jury Theorem and by the Hayek price-discovery argument; and (c) the aggregated information is acted upon by diverse decision-makers rather than feeding a single correlated response.

### When it breaks down

When agents share training data, model architectures, and reasoning patterns, the independence condition fails. The Condorcet Jury Theorem reverses when voters are correlated: correlated errors are amplified rather than cancelled. Similarly, if all AI agents process the same news through the same model and arrive at the same forecast, the "wisdom of crowds" effect that makes prediction markets work is replaced by an "echo chamber" effect that makes them fail.

This is arguably the deepest version of the monoculture problem. Biological ecosystems are resilient because of genetic diversity; epistemic systems (markets, democracies, science) are robust because of cognitive diversity. If AI agents reduce cognitive diversity --- because they all descend from a small number of foundation models trained on similar internet corpora --- the information aggregation institutions that depend on diversity lose their epistemic foundations. The effect is not merely that these institutions become less accurate; it is that they become confidently wrong in correlated ways, which is worse than being noisily inaccurate.

---

## 6. Welfare

### The positive case

The ultimate measure is consumer and producer surplus. AI agents can increase welfare through several channels: lower prices for goods and services (as AI labor reduces production costs), greater product variety (as AI reduces the fixed cost of serving niche markets), reduced monopoly rents (as AI agents automate competitive entry), and improved matching between consumers and products (reducing search costs and misallocation).

The consumer surplus effects are already measurable. Consumers benefit from AI-powered recommendation, negotiation, and comparison-shopping agents that identify better deals, optimize purchasing timing, and reduce the information asymmetry that sustains price discrimination. Cavallo (2018) documents how online price transparency has compressed retail markups; AI agents that automate comparison shopping intensify this effect.

On the producer side, AI agents that automate competitive entry --- identifying profitable niches, setting up supply chains, and managing operations --- could reduce barriers to entry in concentrated industries. If the cost of entering a market falls because AI agents can handle the operational complexity, the threat of entry disciplines incumbent pricing even without actual entry occurring (Baumol, Panzar, & Willig 1982 on contestable markets).

### When it holds

Welfare gains are robust when: (a) AI agents serve diverse principals with competing interests, so that the efficiency gains are passed through to consumers rather than captured by a small number of agent platform owners; (b) markets remain competitive in the effective sense (many independent principals, not many agents controlled by few principals); and (c) the welfare gains are distributed broadly enough to maintain aggregate demand.

Condition (a) is critical and often overlooked. If AI agent capabilities are concentrated in a few firms that deploy them on behalf of consumers, the "automated competition" story depends entirely on whether those firms compete with each other. A monopoly AI shopping agent could extract surplus rather than pass it through.

### When it breaks down

Welfare gains reverse when AI agents enable new forms of rent extraction that exceed the efficiency gains. Price discrimination powered by AI (where agents identify each consumer's exact willingness to pay) can transfer surplus from consumers to producers. Algorithmic collusion (as documented in Calvano et al. 2020) can raise prices above competitive levels. And if the welfare gains accrue disproportionately to capital owners (who own the AI agents) while wages for substitutable labor fall, aggregate consumer purchasing power declines, potentially reducing total welfare even as productive efficiency increases.

The distributional question is inseparable from the efficiency question. A Kaldor-Hicks improvement (total surplus increases) is not a Pareto improvement (no one is worse off) unless compensation actually occurs. The history of technological change suggests that compensation mechanisms (retraining programs, safety nets, progressive taxation) lag decades behind the displacement they are meant to address.

---

## Synthesis: What Determines the Net Effect?

Whether AI agents are net positive or net negative for a given market is not a property of AI agents per se. It is a property of the interaction between agent capabilities and four structural variables.

### 1. Agent diversity

The single most important determinant of whether AI agents improve or degrade market outcomes is the effective diversity of agent strategies. When agents are built on diverse architectures, trained on different data, and deployed by independent principals with different objectives, the positive-sum effects dominate: better price discovery, more informational efficiency, genuine cognitive diversity in aggregation. When agents converge on a small number of foundation model families --- as the current market structure strongly incentivizes --- the negative effects dominate: correlated failures, echo-chamber forecasting, flash-crash fragility.

This is measurable. The effective number of independent strategy types in a market is an empirical quantity that regulators could monitor, analogous to the Herfindahl-Hirschman Index for market concentration but applied to algorithmic diversity rather than firm size.

### 2. Identity cost

The taxonomy's identity cost function c(k) is the critical variable for mechanism design outcomes. When c(k) is high enough that sybil attacks are unprofitable, AI agents' superior cognitive capabilities improve mechanism performance (better preference expression, more efficient allocation). When c(k) is low enough that sybil attacks are cheap, those same capabilities become weapons against the mechanism. The threshold is mechanism-specific and computable: for each mechanism, there exists a critical value of c_marginal below which the mechanism's guarantees fail. Markets and mechanisms operating above this threshold benefit from AI agents; those operating below it are degraded.

### 3. Market structure

The welfare effects depend on whether the market for AI agent services is itself competitive. If many independent firms offer AI agents, the efficiency gains from agent capabilities are competed away and passed to consumers. If a small number of firms control agent deployment (through proprietary models, data advantages, or platform lock-in), the gains are captured as rents. The market structure of the AI industry is therefore a first-order determinant of whether AI agents improve or worsen welfare in the markets they participate in. Current trends toward concentration in foundation model development (a handful of firms with the capital for frontier training) are, by this analysis, a threat to the positive-sum scenario.

### 4. Regulatory response speed

Many of the negative effects (sybil attacks, algorithmic collusion, velocity instability) are addressable in principle through regulatory and institutional design: identity verification requirements, algorithmic audit mandates, transaction velocity dampeners, diversity requirements for market participants. The question is whether regulatory institutions can adapt at the speed required. If AI agent capabilities advance on a timescale of months and regulatory adaptation operates on a timescale of years, there is a persistent gap during which the negative effects dominate. The regulatory response speed is itself a structural variable that determines outcomes.

### The conditional conclusion

AI agents improve economic outcomes in markets characterized by high agent diversity, robust identity infrastructure, competitive market structure in the AI industry itself, and adaptive regulatory institutions. They degrade economic outcomes in markets characterized by monoculture agent strategies, cheap identity, concentrated AI industry structure, and slow regulatory response. Most real markets will exhibit a mixture of these conditions, and the net effect will vary by market, by jurisdiction, and over time.

The policy implication is that the question "are AI agents good or bad for the economy?" is not well-posed. The well-posed question is: "what market structures and institutional designs ensure that the positive-sum effects of AI agents dominate the negative-sum effects?" This reframing --- from technological determinism to institutional design --- is the central analytical contribution of a balanced assessment.

---

## References

- Acemoglu, D. and Restrepo, P. (2019). Automation and new tasks: How technology displaces and reinstates labor. *Journal of Economic Perspectives*.
- Autor, D.H., Levy, F., and Murnane, R.J. (2003). The skill content of recent technological change. *Quarterly Journal of Economics*.
- Bai, Y. et al. (2024). Strategy correlation in LLM-based market agents. *Working paper*.
- Baumol, W.J., Panzar, J.C., and Willig, R.D. (1982). *Contestable Markets and the Theory of Industry Structure*. Harcourt.
- Brogaard, J., Hendershott, T., and Riordan, R. (2014). High-frequency trading and price discovery. *Review of Financial Studies*.
- Brynjolfsson, E., Rock, D., and Syverson, C. (2021). The productivity J-curve. *American Economic Journal: Macroeconomics*.
- Calvano, E., Calzolari, G., Denicolo, V., and Pastorello, S. (2020). Artificial intelligence, algorithmic pricing, and collusion. *American Economic Review*.
- Cavallo, A. (2018). More Amazon effects: Online competition and pricing behaviors. *NBER Working Paper*.
- Coase, R.H. (1937). The nature of the firm. *Economica*.
- Cramton, P., Shoham, Y., and Steinberg, R. (2006). *Combinatorial Auctions*. MIT Press.
- Diamond, P.A. (1982). Aggregate demand management in search equilibrium. *Journal of Political Economy*.
- Fama, E.F. (1970). Efficient capital markets: A review of theory and empirical work. *Journal of Finance*.
- Hasbrouck, J. and Saar, G. (2013). Low-latency trading. *Journal of Financial Markets*.
- Hayek, F.A. (1945). The use of knowledge in society. *American Economic Review*.
- Hendershott, T., Jones, C.M., and Menkveld, A.J. (2011). Does algorithmic trading improve liquidity? *Journal of Finance*.
- Kirilenko, A., Kyle, A.S., Samadi, M., and Tuzun, T. (2017). The Flash Crash: High-frequency trading in an electronic market. *Journal of Finance*.
- Li, D. et al. (2023). Hiring as exploration: AI-assisted matching in labor markets. *Working paper*.
- Mortensen, D.T. and Pissarides, C.A. (1994). Job creation and job destruction in the theory of unemployment. *Review of Economic Studies*.
- Noy, S. and Zhang, W. (2023). Experimental evidence on the productivity effects of generative artificial intelligence. *Science*.
- Sandholm, T. (2013). Very-large-scale generalized combinatorial multi-attribute auctions. In *Handbook of Combinatorial Optimization*.
- Schoenegger, P. and Park, P.S. (2024). Large language model prediction capabilities. *Working paper*.
- Williamson, O.E. (1985). *The Economic Institutions of Capitalism*. Free Press.
- Yokoo, M., Sakurai, Y., and Matsubara, S. (2004). The effect of false-name bids in combinatorial auctions. *Games and Economic Behavior*.
