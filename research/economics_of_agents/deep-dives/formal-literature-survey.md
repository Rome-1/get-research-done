# Formal Literature Survey: AI Agents in Economic Theory

**Status:** First draft
**Date:** 2026-03-29
**Author:** Alice (GetResearch)
**Motivation:** Comprehensive literature review of formal academic work on AI agents in economic systems
**Related:** `assumption-taxonomy.md`, `literature-map.md`

---

## Introduction

The entry of artificial intelligence agents into economic systems has precipitated a body of formal academic work that spans mechanism design, industrial organization, labor economics, market microstructure, information economics, and computational social choice. This survey covers the major threads of that literature, with particular attention to results that bear on the claim — developed in our companion `assumption-taxonomy.md` — that AI agents violate implicit substrate assumptions underlying classical economic theory. We focus on papers published or substantially updated between 2020 and 2026, though we reference earlier foundational work where necessary for context.

The survey is organized thematically rather than chronologically. Each section identifies the core formal question, summarizes the key results, and notes open problems. We conclude with a synthesis that maps the literature onto the assumption violations catalogued in the taxonomy.

---

## 1. Mechanism Design and AI Agents

### 1.1 Classical Foundations Under Pressure

The canonical results in mechanism design — the revelation principle (Myerson, 1981), the Gibbard-Satterthwaite impossibility theorem (Gibbard, 1973; Satterthwaite, 1975), and the VCG mechanism (Vickrey, 1961; Clarke, 1971; Groves, 1973) — all assume a fixed, exogenous set of agents with well-defined, stable types. AI agents violate these assumptions along at least three dimensions: identity is cheap and duplicable (the sybil problem), types are endogenous and mutable (preferences can be reprogrammed between interactions), and computational constraints that historically made strategic manipulation infeasible are removed.

Conitzer and Sandholm (2002, 2006) established the research program of automated mechanism design, in which the mechanism itself is computationally generated for a specific problem instance rather than derived analytically. Their early work showed that computational approaches can circumvent seminal impossibility results by exploiting structure in specific instances. More recently, Conitzer (2010) argued that computational complexity had served as an informal barrier to strategic manipulation — agents could not compute optimal deviations — and that AI removes this barrier, requiring mechanism designers to assume worst-case strategic sophistication.

### 1.2 False-Name-Proofness and Sybil Resistance

The formal study of sybil attacks on mechanisms originates with Douceur (2002), who showed in a distributed systems context that sybil resistance requires either a centralized trusted authority or resource testing. The economic implications were developed by Yokoo, Sakurai, and Matsubara (2004), who introduced the concept of *false-name-proofness* for combinatorial auctions. Their central result is stark: there exists no false-name-proof mechanism that always achieves Pareto efficient allocations. This impossibility extends the Gibbard-Satterthwaite framework to settings where agents can submit bids under multiple fictitious identities.

Yokoo's subsequent work established the PORF (price-oriented, rationing-free) protocol class as the necessary and sufficient condition for strategy-proofness in combinatorial settings, and showed that false-name-proofness imposes additional constraints that further reduce the feasible design space. Wagman and Conitzer (2008) extended the analysis to voting, proving that false-name-proof voting rules are severely constrained relative to merely strategyproof ones.

The practical relevance of these results has grown sharply as AI agents proliferate in auction markets. Google's ad auctions use VCG variants at enormous scale, with sybil resistance provided by ancillary identity checks (payment instrument linking, advertiser verification) rather than by the mechanism itself. As the `assumption-taxonomy.md` documents, the cost of creating additional agent identities — the identity cost function c(k) — has collapsed from effectively infinite to approximately epsilon times k, rendering the implicit sybil-freeness assumption of classical mechanism design empirically false in pseudonymous markets.

### 1.3 Optimal Auctions via Deep Learning

Dutting, Feng, Narasimhan, Parkes, and Ravindranath (2019, Journal of the ACM 2024) introduced *RegretNet*, which frames optimal auction design as a constrained learning problem solved by neural networks. The approach models an auction as a multi-layer neural network and uses gradient-based optimization to find mechanisms that approximate revenue optimality while satisfying incentive compatibility constraints. The work recovers known optimal solutions (Myerson's auction for single items) and discovers novel mechanisms for multi-item settings where analytical solutions are unknown.

This line of work — sometimes called "differentiable economics" — represents a paradigm shift: mechanisms are no longer hand-designed but computationally discovered. However, a critical open question is whether learned mechanisms are robust to the very AI agents that might participate in them. If both the mechanism and the bidders are neural networks, the resulting co-optimization problem has no guaranteed convergence properties and may exhibit adversarial dynamics.

### 1.4 The AI Economist

Zheng, Trott, Srinivasa, Parkes, and Socher (2022, Science Advances) developed a two-level deep reinforcement learning framework for economic policy design. In their model, economic agents optimize their behavior under a tax policy while a social planner simultaneously optimizes the tax schedule to maximize social welfare. The AI Economist improved the equality-productivity tradeoff by 16% over the analytically-derived Saez tax framework, and by larger margins over adaptations of the US Federal income tax.

The significance of this work for our purposes is twofold. First, it demonstrates that RL agents can discover economic strategies that no human designed — a concrete instance of the endogenous type problem. Second, the two-level co-adaptive framework is itself a model of the mechanism design challenge: when agents and mechanisms co-evolve, the standard Stackelberg formulation (designer moves first, agents respond) may not converge.

---

## 2. Algorithmic Collusion Models

### 2.1 The Calvano Benchmark

Calvano, Calzolari, Denicolo, and Pastorello (2020, American Economic Review) provided the foundational result: independent Q-learning pricing agents, competing in a simulated oligopoly, converge to supra-competitive prices without any explicit communication or coordination. The agents learn reward-punishment strategies resembling classical collusive equilibria, but arrive at them through independent reinforcement learning rather than negotiation. This result is striking because it shows that algorithmic collusion can be *emergent* — a property of the learning dynamics rather than the agents' design.

Calvano et al. (2023) examined Q-learning without memory, establishing that collusion persists when agents are forward-looking and can condition on past prices, but vanishes when agents are myopic or memoryless. This is an important boundary condition: collusion is not an inevitable artifact of Q-learning but depends on the agents' capacity for intertemporal conditioning.

### 2.2 Challenges and Refinements

Den Boer, Keskin, and Morgenstern (2023) challenged the generality of the Calvano result in their paper "Algorithmic Collusion: Genuine or Spurious?" (International Journal of Industrial Organization), arguing that some reported collusive outcomes in computational experiments may be artifacts of specific parameter choices or convergence criteria rather than robust phenomena. They showed that in certain specifications, what appears to be collusion is instead slow convergence to the competitive equilibrium — a distinction with significant policy implications.

Subsequent work has partially reconciled these positions. Dou, Li, and Wang (2025) demonstrated that Q-learning agents can generate collusive outcomes through price-trigger strategies or learning biases, but that the mechanism varies across market structures. The literature now recognizes that algorithmic collusion is real but context-dependent: market structure, algorithm specification, state space representation, and training duration all matter.

### 2.3 LLM Collusion

Fish, Gonczarowski, and Shorrer (2024, presented at AEA 2025) extended the research program to large language models, finding that LLM-based pricing agents "quickly and autonomously reach supracompetitive prices and profits" in oligopoly settings. This result is more alarming than the Q-learning findings for two reasons. First, LLMs do not require the long and costly training period that Q-learning agents need — they arrive pre-trained on data that includes economic reasoning and pricing strategies. Second, LLMs can perform well across diverse environments, unlike Q-learning agents that are typically trained for a specific game.

Fish et al. also discovered that "variation in seemingly innocuous phrases in LLM instructions ('prompts') may increase collusion" — suggesting that the collusive tendency is sensitive to framing in ways that are difficult to audit or regulate. The result extends to auction settings, where LLM bidders learn to coordinate bid suppression without explicit instruction.

### 2.4 Empirical Evidence

Assad, Clark, Ershov, and Xu (2024, Journal of Political Economy) provided the first rigorous empirical evidence linking algorithmic pricing to reduced competition. Studying Germany's retail gasoline market, where algorithmic pricing software became widely available in 2017, they found that adoption significantly raises profit margins — but only when multiple competitors adopt simultaneously. In duopoly and triopoly markets, margins increase only if all stations adopt, suggesting that algorithmic pricing functions as a coordination device rather than a unilateral advantage.

This finding bridges the theoretical and empirical literatures: the predicted collusive dynamics of computational models appear in real market data, at least in settings where adoption is widespread and competitors can observe each other's algorithmic behavior.

### 2.5 Regulatory Response

The policy literature has struggled to accommodate algorithmic collusion within existing antitrust frameworks. Harrington (2018) identified the core difficulty: collusion law typically requires evidence of agreement or communication, but algorithmic collusion can emerge from independent optimization without any exchange of information. The US Department of Justice's 2024 lawsuit against RealPage (alleging that its algorithmic rental pricing tool facilitated supracompetitive rents) and the Preventing Algorithmic Collusion Act (Senate Bill 232, reintroduced 2025) represent early regulatory attempts, but legal scholars note that existing antitrust statutes, designed to address human coordination, are structurally ill-suited to emergent algorithmic coordination.

Bichler, Fichtl, and Heidekruger (2025) provide a comprehensive survey in "Algorithmic Pricing and Algorithmic Collusion," synthesizing the theoretical, computational, and regulatory dimensions.

---

## 3. AI Labor Economics

### 3.1 The Task Exposure Framework

The dominant analytical framework for AI's labor market effects is the task-based model developed by Acemoglu and Restrepo (2019, Journal of Economic Perspectives), which decomposes occupations into tasks and analyzes which tasks are susceptible to automation versus augmentation. The framework distinguishes between a *displacement effect* (AI substitutes for human labor on existing tasks) and a *reinstatement effect* (new technology creates new tasks that require human labor).

Eloundou, Manning, Mishkin, and Rock (2023, published in Science 2024 as "GPTs are GPTs") operationalized this framework for large language models specifically, developing task-level exposure measures using both human expert assessments and GPT-4 classifications. Their central finding is that approximately 80% of the US workforce could have at least 10% of their work tasks affected by LLMs, while roughly 19% of workers may see at least 50% of their tasks impacted. When incorporating software built on top of LLMs, the share of affected tasks rises to 47-56%.

This paper is methodologically significant for introducing the concept of *exposure* (rather than displacement) as the relevant variable — acknowledging that task-level AI capability does not automatically translate to job-level displacement, because organizational, regulatory, and economic factors mediate adoption.

### 3.2 Macroeconomic Projections

Acemoglu (2024, "The Simple Macroeconomics of AI") used the task-based framework to produce aggregate productivity estimates, arriving at a notably conservative conclusion: total factor productivity gains of less than 0.7% cumulatively over ten years. This stands in sharp contrast to more optimistic projections and reflects Acemoglu's assessment that many AI-exposed tasks are only partially automatable and that the reinstatement of new human-complementary tasks will substantially offset displacement.

Korinek and Stiglitz (2021, revised 2025) provide a more distributional analysis, arguing that even if aggregate productivity effects are modest, the income distribution consequences could be severe. They provide a taxonomy of conditions under which AI leads to Pareto improvement versus worker displacement, and show that under plausible conditions, non-distortionary taxation can compensate losers. Their updated 2025 paper, "Steering Technological Progress," analyzes how to direct AI development toward labor-complementary rather than labor-replacing applications.

### 3.3 Experimental Evidence

The experimental literature has grown rapidly. Brynjolfsson, Li, and Raymond (2023, NBER Working Paper 31161) studied the deployment of a generative AI assistant among 5,179 customer support agents, finding a 14% average productivity increase with a 34% improvement for novice workers and minimal impact on experienced workers. This compression of the productivity distribution — AI helps low-skill workers more — is a recurring finding.

Noy and Zhang (2023, Science) conducted a randomized experiment with 453 professionals performing writing tasks, finding that ChatGPT reduced completion time by 40% and increased output quality by 18%. Again, the benefits accrued disproportionately to lower-ability workers. Noy and Zhang characterized AI as "mostly substituting for worker effort rather than complementing worker skills," and showed that the tool "restructured tasks towards idea-generation and editing and away from rough-drafting."

### 3.4 New Frontiers in Work Creation

Autor, Chin, Salomons, and Seegmiller (2024, Quarterly Journal of Economics, "New Frontiers") provide the historical counterpoint. Analyzing US employment from 1940 to 2018, they show that newly created occupations — roles that did not exist in previous decades — have historically contributed significantly to employment growth, particularly when innovations augment rather than automate work activities. The paper establishes that technology-driven job creation is not merely theoretical but has been the dominant historical pattern. However, the authors note that AI may differ from previous waves because it affects cognitive and creative tasks that were previously immune to automation, potentially limiting the scope for new human-complementary roles.

---

## 4. Market Microstructure and Automated Trading

### 4.1 From HFT to AI Market Making

The intersection of AI and market microstructure has a longer history than other areas surveyed here, with algorithmic and high-frequency trading predating LLMs by decades. The relevant formal question is whether AI market-making agents change the informational properties of prices — specifically, whether they enhance or degrade price discovery, liquidity, and market stability.

Classical market microstructure models (Kyle, 1985; Glosten and Milgrom, 1985) analyze how informed and uninformed traders interact through a market maker, with prices converging to reflect private information. These models assume heterogeneous information processing speeds and costly participation. AI agents compress the speed distribution and reduce participation costs, potentially altering the information aggregation dynamics.

Recent work applies deep reinforcement learning to market making and execution. Kumar et al. (2023) formulate trading as a Markov Decision Process with high-dimensional state features (limit order book snapshots, recent trade flows) and reward functions that capture profit-and-loss adjusted for market impact and inventory risk. Execution algorithms powered by RL learn the microstructure of specific exchanges, including where hidden liquidity lies and how orders typically fill, and optimize order placement in real time.

### 4.2 Correlated Strategies and Flash Crashes

The concern most relevant to our assumption taxonomy is strategy correlation. When market-making agents share architectures, training procedures, or data, their strategies become correlated. The effective diversity of the market — the number of independent decision-makers — drops, even as the nominal number of participants increases. This mirrors the Condorcet Jury Theorem violation identified in the taxonomy: effective sample size N_eff = N/(1 + (N-1)rho), where rho is strategy correlation. When rho approaches 1, the market aggregates one opinion amplified N times.

Empirically, flash crashes — sudden, severe price dislocations that reverse within minutes — have been attributed to correlated algorithmic behavior. The May 2010 Flash Crash, the August 2015 ETF dislocations, and the March 2020 Treasury market dysfunction all involved cascading algorithmic responses. While these events predated LLM-based agents, the concern is that AI agents with shared training data will exhibit even higher strategy correlation.

### 4.3 DeFi and Automated Market Makers

Decentralized finance provides a natural laboratory for studying AI agents in market microstructure, because DeFi protocols are permissionless and pseudonymous — precisely the conditions under which the identity cost function c(k) approaches zero. Automated market makers (AMMs) like Uniswap replace the order book with algorithmic pricing functions, and AI agents that provide liquidity or arbitrage across AMMs face a market design that was explicitly built for automated participants.

The MEV (Maximal Extractable Value) literature documents how sophisticated agents extract surplus from transaction ordering, front-running, and sandwich attacks in blockchain-based markets. This is a concrete instance of the Walrasian auctioneer violation: agents that can observe and front-run the price adjustment process collapse the separation between price-setter and price-taker.

---

## 5. Information Economics and AI

### 5.1 Information Design and Data Markets

Bergemann and Bonatti (2024, American Economic Review) analyze how a monopolist platform uses data to match consumers with sellers, developing a model in which information revelation is a strategic variable. Their framework — where the platform sells targeted advertising campaigns and selectively reveals information to consumers — formalizes the economics of AI-mediated information markets. The key finding for our purposes is that platforms exploit their information advantage to increase bargaining power vis-a-vis sellers, and that privacy-respecting data governance rules can yield welfare gains for consumers. The implication is that AI agents operating on behalf of consumers could potentially counteract platform information asymmetries — but only if the agents are genuinely independent, not themselves products of the platform.

### 5.2 Prediction Markets and Correlated Signals

The formal theory of prediction markets rests on information aggregation results that assume independent, diversely informed traders. The Condorcet Jury Theorem guarantees that majority voting among independently informed jurors converges to the correct answer as the number of jurors grows. The analogous result for prediction markets — that prices converge to true probabilities as the number of informed traders increases — depends on the same independence assumption.

AI agents threaten this assumption because they share training data, architectures, and reasoning patterns. When LLM-based forecasting agents dominate a prediction market, the effective independence of signals collapses. Recent work on information aggregation under ambiguity (published in the Review of Economic Studies, 2024) shows that even without AI agents, theoretical aggregation results are fragile when traders face ambiguity about the information structure. Adding correlated AI agents to this already-fragile framework suggests that the informational efficiency of prediction markets may degrade precisely as AI participation increases.

### 5.3 AI as Forecasting Technology

The empirical literature on AI forecasting is large and growing. BIS Working Paper 1291 (2025) examines how AI can be harnessed for economic monitoring, using LLMs to extract expectations of CPI, unemployment, and market indices from archival news sources. The significance is that AI does not merely trade on information but generates it — constructing forecasts and narratives that other agents (human and artificial) then act upon. This creates a reflexivity problem: if AI-generated forecasts influence the quantities they predict, the standard Bayesian framework for information aggregation may not apply.

---

## 6. Computational Social Choice with AI

### 6.1 Social Choice for AI Alignment

Conitzer, Freedman, Heitzig, Holliday, Jacobs, Lambert, Mosse, Pacuit, Russell, Schoelkopf, Tewolde, and Zwicker (2024, ICML) published a position paper arguing that social choice theory should guide AI alignment in dealing with diverse human feedback. The paper identifies a fundamental problem: when training AI systems on human preferences, the aggregation of potentially conflicting feedback is itself a social choice problem subject to impossibility results (Arrow, 1951; Gibbard-Satterthwaite). The authors argue that the RLHF (reinforcement learning from human feedback) paradigm implicitly makes social choice decisions without acknowledging the formal constraints on preference aggregation.

This connects to our taxonomy in a bidirectional way. Not only do AI agents create social choice problems (as manipulators of voting and allocation mechanisms), but the design of AI systems is itself a social choice problem that inherits the impossibility results our taxonomy catalogs.

### 6.2 LLMs and Strategic Reasoning

A growing benchmark literature evaluates LLMs' capacity for strategic reasoning in game-theoretic settings. GTBench (2024) evaluates LLMs across 10 game-theoretic tasks spanning complete and incomplete information, static and dynamic, probabilistic and deterministic scenarios. TMGBench (2024-2025) covers all 144 game types in the Robinson-Goforth topology of 2x2 games. The LLM Strategic Reasoning study (2025) evaluates 22 state-of-the-art LLMs using behavioral game theory, finding that models like GPT-o3-mini, GPT-o1, and DeepSeek-R1 lead in reasoning depth.

The collective finding is that current LLMs exhibit significant but uneven strategic reasoning capabilities: they perform well in some game classes (particularly those resembling scenarios well-represented in training data) but show "flaws in the accuracy and consistency of strategic reasoning processes" (TMGBench) and "sensitivity to prompt framing and contextual cues" (SmartPlay, FAIRGAME). For our taxonomy, this means that the assumption of bounded rationality — which has historically served as an informal barrier to mechanism manipulation — is partially but not fully eroded by current AI capabilities.

### 6.3 False-Name-Proofness in Digital Voting

The sybil vulnerability of voting mechanisms is a direct concern for digital governance systems. Wagman and Conitzer (2008) showed that false-name-proof voting rules are highly constrained. The quadratic voting mechanism of Lalley and Weyl (2018) — which elicits preference intensity by making the cost of votes quadratic — is particularly sybil-vulnerable: a principal with k identities can express linear rather than quadratic total cost, defeating the mechanism's purpose. As our taxonomy notes, under cheap identity conditions, quadratic voting degenerates to standard one-token-one-vote plutocracy.

Proof-of-personhood systems represent the technological frontier of sybil resistance for digital voting. These systems use biometric verification (iris scans, liveness detection) combined with cryptographic methods (zero-knowledge proofs) to verify unique human identity without revealing personal information. Recent work (2024-2025) on blockchain-based proof-of-personhood proposes binding human identity, wallet address, and physical device into unified frameworks. However, these systems face their own adversarial challenges when AI-generated synthetic identities become sufficiently convincing, creating an arms race between identity verification and identity fabrication technologies.

---

## 7. Open Problems and Research Frontiers

### 7.1 Identity-Aware Mechanism Design

The most urgent theoretical gap is the absence of a general theory of mechanism design under endogenous identity. Classical mechanism design takes the agent set as given; false-name-proofness relaxes this to allow strategic identity manipulation but imposes severe efficiency costs. A satisfying theory would treat identity cost as a continuous parameter and characterize how optimal mechanisms vary as that parameter changes. The identity cost function c(k) proposed in our taxonomy provides a starting point, but the formal development — existence results, revenue and welfare bounds, computational tractability — remains largely open.

### 7.2 Co-Evolutionary Mechanism-Agent Dynamics

When both the mechanism and the participating agents are AI systems, the design problem becomes co-evolutionary. The AI Economist (Zheng et al., 2022) demonstrates this in a simple setting, but the general theory of convergence, stability, and welfare properties of co-adaptive mechanism-agent systems is undeveloped. This is analogous to the well-studied problem of GAN training dynamics but in an economic design context where welfare is the objective.

### 7.3 Algorithmic Collusion Detection and Prevention

The policy-relevant question is whether algorithmic collusion can be detected in real time and prevented by market design rather than ex post enforcement. The current legal framework (Sherman Act, EU competition law) is poorly suited to collusion that emerges without communication. Mechanism design approaches — for instance, introducing randomization or information asymmetries that disrupt the learning dynamics that produce collusion — are theoretically promising but have not been developed at a level of formality comparable to, say, optimal auction theory.

### 7.4 Labor Market Theory for Elastic AI Supply

Classical labor economics assumes an upward-sloping labor supply curve anchored to population. When AI labor supply is elastic to compute cost, the standard wage determination models require reformulation. The task-based framework (Acemoglu and Restrepo, 2019) provides the right level of granularity — task-level rather than occupation-level analysis — but does not yet incorporate the distinctive feature of AI labor: near-zero marginal cost of additional units and instantaneous "skill acquisition" (loading a model). A formal model of labor markets with both human and AI participants, where AI supply is endogenous to compute prices and human supply responds to AI displacement, is needed.

### 7.5 Information Aggregation with Correlated AI Agents

The degradation of prediction market accuracy under correlated AI participation is theoretically understood in the limit (effective sample size collapses) but not well-characterized in the intermediate regime where some fraction of participants are AI agents with varying degrees of strategy correlation. A formal model of information aggregation in mixed human-AI markets — parameterized by the AI participation share, strategy correlation, and signal quality — would provide actionable guidance for prediction market design.

---

## 8. Synthesis

The formal literature surveyed here converges on a set of findings that directly support the assumption violations catalogued in our taxonomy:

**Identity is the critical variable.** The false-name-proofness literature (Yokoo et al., 2004; Wagman and Conitzer, 2008) establishes that mechanism design without sybil-freeness is a fundamentally different — and harder — problem than classical mechanism design. The impossibility result (no false-name-proof mechanism achieves Pareto efficiency) is the formal counterpart of our taxonomy's claim that VCG, Myerson's auction, CEEI, and quadratic voting all break under cheap identity. The practical relevance of this theoretical result has gone from negligible (when identity was expensive) to acute (when AI agents can instantiate identities at near-zero cost).

**Algorithmic collusion is real but context-dependent.** The progression from Calvano et al. (2020) through Fish et al. (2024) establishes that AI agents — whether Q-learning algorithms or LLMs — can learn collusive strategies autonomously. But the phenomenon is not universal: it depends on market structure, algorithm specification, and the agents' capacity for intertemporal conditioning. Assad et al. (2024) provides empirical grounding. The regulatory response is nascent and structurally ill-suited to the problem, because existing antitrust law requires evidence of agreement that algorithmic collusion does not produce.

**AI reshapes labor markets through task displacement, with uncertain net effects.** The Eloundou et al. (2023) task exposure framework and Acemoglu's (2024) macroeconomic analysis provide a rigorous basis for assessing labor market effects. The experimental evidence (Brynjolfsson et al., 2023; Noy and Zhang, 2023) consistently shows that AI augments productivity and compresses the skill distribution, benefiting low-skill workers disproportionately. The open question, addressed by Autor et al. (2024), is whether new human-complementary tasks will be created at a rate sufficient to offset displacement — historically this has been the case, but AI's reach into cognitive tasks makes extrapolation uncertain.

**Market microstructure faces correlated strategy risk.** The central insight is that AI agents with shared architectures and training data reduce the effective diversity of market participants, potentially degrading price discovery even as they increase market speed and nominal liquidity. This connects the EMH and Condorcet violations in our taxonomy to a well-established concern in the HFT and market microstructure literatures.

**Computational social choice is the bridge between AI alignment and economic design.** Conitzer et al. (2024) explicitly connect social choice theory to AI alignment, identifying preference aggregation as the common formal problem. The benchmark literature on LLM strategic reasoning shows that AI agents are partially but not fully rational in game-theoretic contexts, implying that the bounded rationality assumption is weakened but not eliminated — a calibration-sensitive finding that resists binary characterization.

Taken together, the literature establishes that AI agents do not merely perturb existing economic models — they violate structural premises that underlie the major theorems. The theoretical response is still in its early stages. False-name-proofness, algorithmic collusion modeling, and task-based labor economics represent the most developed formal threads, but a unified theory of economic mechanism design for mixed human-AI populations remains an open frontier.

---

## References

Acemoglu, D. (2024). "The Simple Macroeconomics of AI." NBER Working Paper.

Acemoglu, D. and Restrepo, P. (2019). "Automation and New Tasks: How Technology Displaces and Reinstates Labor." *Journal of Economic Perspectives* 33(2): 3-30.

Assad, S., Clark, R., Ershov, D., and Xu, L. (2024). "Algorithmic Pricing and Competition: Empirical Evidence from the German Retail Gasoline Market." *Journal of Political Economy* 132(3): 723-771.

Autor, D., Chin, C., Salomons, A., and Seegmiller, B. (2024). "New Frontiers: The Origins and Content of New Work, 1940-2018." *Quarterly Journal of Economics*.

Bergemann, D. and Bonatti, A. (2024). "Data, Competition, and Digital Platforms." *American Economic Review* 114(8): 2553-2595.

Bichler, M., Fichtl, M., and Heidekruger, S. (2025). "Algorithmic Pricing and Algorithmic Collusion." arXiv:2504.16592.

Brynjolfsson, E., Li, D., and Raymond, L. (2023). "Generative AI at Work." NBER Working Paper 31161.

Calvano, E., Calzolari, G., Denicolo, V., and Pastorello, S. (2020). "Artificial Intelligence, Algorithmic Pricing, and Collusion." *American Economic Review* 110(10): 3267-3297.

Conitzer, V. (2010). "Mechanism Design for the Computational Era." In *Making Decisions in a Complex World*, AAAI Press.

Conitzer, V. and Sandholm, T. (2002). "Complexity of Mechanism Design." *Proceedings of the 18th Conference on Uncertainty in Artificial Intelligence*.

Conitzer, V. and Sandholm, T. (2006). "Failures of the VCG Mechanism." *Proceedings of the 5th International Joint Conference on Autonomous Agents and Multiagent Systems (AAMAS)*.

Conitzer, V., Freedman, R., Heitzig, J., Holliday, W.H., Jacobs, B.M., Lambert, N., Mosse, M., Pacuit, E., Russell, S., Schoelkopf, H., Tewolde, E., and Zwicker, W.S. (2024). "Position: Social Choice Should Guide AI Alignment in Dealing with Diverse Human Feedback." *Proceedings of the 41st International Conference on Machine Learning (ICML)*.

Den Boer, A., Keskin, N.B., and Morgenstern, J. (2023). "Algorithmic Collusion: Genuine or Spurious?" *International Journal of Industrial Organization* 90: 102973.

Douceur, J. (2002). "The Sybil Attack." *Proceedings of the 1st International Workshop on Peer-to-Peer Systems (IPTPS)*.

Dutting, P., Feng, Z., Narasimhan, H., Parkes, D.C., and Ravindranath, S.S. (2024). "Optimal Auctions through Deep Learning: Advances in Differentiable Economics." *Journal of the ACM* 71(1): 5:1-5:53.

Eloundou, T., Manning, S., Mishkin, P., and Rock, D. (2023). "GPTs are GPTs: An Early Look at the Labor Market Impact Potential of Large Language Models." arXiv:2303.10130. Published in *Science* (2024).

Fish, S., Gonczarowski, Y.A., and Shorrer, R.I. (2024). "Algorithmic Collusion by Large Language Models." arXiv:2404.00806. Presented at AEA 2025.

Harrington, J. (2018). "Developing Competition Law for Collusion by Autonomous Artificial Agents." *Journal of Competition Law and Economics* 14(4): 529-563.

Korinek, A. and Stiglitz, J.E. (2021, revised 2025). "Artificial Intelligence and Its Implications for Income Distribution and Unemployment." NBER Working Paper 24174.

Kumar, S. et al. (2023). "Deep Reinforcement Learning for High-Frequency Market Making." *Proceedings of Machine Learning Research* 189.

Noy, S. and Zhang, W. (2023). "Experimental Evidence on the Productivity Effects of Generative Artificial Intelligence." *Science* 381(6654): 187-192.

Wagman, L. and Conitzer, V. (2008). "Optimal False-Name-Proof Voting Rules." *Proceedings of the 23rd AAAI Conference on Artificial Intelligence*.

Yokoo, M., Sakurai, Y., and Matsubara, S. (2004). "The Effect of False-Name Bids in Combinatorial Auctions: New Fraud in Internet Auctions." *Games and Economic Behavior* 46(1): 174-188.

Zheng, S., Trott, A., Srinivasa, S., Parkes, D.C., and Socher, R. (2022). "The AI Economist: Taxation Policy Design via Two-Level Deep Multiagent Reinforcement Learning." *Science Advances* 8(18).
