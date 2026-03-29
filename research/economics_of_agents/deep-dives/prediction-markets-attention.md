# Prediction Markets and the Attention Economy Under AI Agents

**Status:** First draft deep dive
**Date:** 2026-03-29
**Author:** Alice (GetResearch)
**Responds to:** Round 1 review, Section 3.1 — missing coverage of prediction markets and the attention economy

---

## Part 1: Prediction Markets Under AI Agents

### 1.1 Why Prediction Markets Work

Prediction markets derive their epistemic value from a specific statistical property: when independent forecasters with diverse information sources each make probabilistic estimates, the aggregated estimate converges on truth faster than any individual forecaster. The theoretical foundation rests on extensions of the Condorcet Jury Theorem (1785), which establishes that if each voter in a binary decision is independently correct with probability p > 0.5, the majority decision converges to certainty as the number of voters increases. Prediction markets generalize this from binary votes to continuous price signals, but the core mechanism is identical: aggregate diverse, independent signals and the errors cancel.

The modern theory of prediction markets draws on Hayek's (1945) insight that prices aggregate dispersed knowledge that no central planner could collect, together with the formal information aggregation results of Plott and Sunder (1988), who demonstrated experimentally that market prices in laboratory settings converge to rational expectations equilibria even when no individual trader has sufficient information to compute the equilibrium price. The Iowa Electronic Markets have provided decades of empirical evidence that prediction market prices outperform polls in forecasting elections (Berg et al. 2008). Metaculus, Polymarket, and other platforms have extended this track record to geopolitical events, scientific outcomes, and policy questions.

Three conditions are necessary for this aggregation to work:

1. **Independence.** Forecasters must form judgments based on different information sets or different reasoning processes. If all forecasters observe the same signal and reason identically, the market reflects one opinion amplified N times, not N independent opinions aggregated.

2. **Diversity of information.** The errors of individual forecasters must be uncorrelated or, at minimum, not systematically correlated in the same direction. Surowiecki (2004) emphasized this as the critical ingredient of "crowd wisdom" — crowds are wise precisely when their members are wrong in different ways.

3. **Incentive alignment.** Forecasters must bear costs for inaccuracy and receive rewards for accuracy. This is the skin-in-the-game condition that distinguishes prediction markets from opinion polls and makes them resistant to cheap talk. Hanson (2003) formalized this through the logarithmic market scoring rule, which rewards traders in proportion to the information content of their trades.

When all three conditions hold, prediction markets are among the most reliable forecasting institutions available. When any of the three fails, market prices can deviate systematically from truth.

### 1.2 How AI Agents Break the Independence Assumption

AI agents violate the independence condition structurally. The violation is not a matter of bad incentives or poor market design — it is a consequence of how foundation models are built.

**Correlated training data.** The major foundation models — GPT-family, Claude-family, Gemini, Llama, and their derivatives — are trained on broadly overlapping corpora. Common Crawl, Wikipedia, books, academic papers, and web-scraped text form the backbone of every large language model's training data. While each model family has proprietary additions, the shared substrate means that the "prior beliefs" of these models are correlated at the base. When an AI agent is asked to estimate the probability of an event, its starting estimate is a function of patterns in its training data. Two agents trained on 80% overlapping data will, absent countervailing factors, produce correlated initial estimates.

**Correlated reasoning architectures.** Even where training data differs, the transformer architecture imposes structural similarities in reasoning. Attention mechanisms, next-token prediction objectives, and the inductive biases of deep networks mean that models tend to make similar types of errors: overweighting frequently attested patterns, underweighting tail events, and exhibiting systematic biases documented in the calibration literature (Kadavath et al. 2022). These architectural correlations mean that even "diverse" model families may share failure modes. The errors do not cancel in aggregation — they compound.

**The effective diversity collapse.** Consider a prediction market with 10,000 participants, of whom 9,000 are AI agents built on three foundation model families. The nominal participant count is 10,000, but the effective number of independent information sources may be closer to 1,003 (1,000 humans with diverse information plus three model families). As AI agents come to dominate prediction market participation by volume, the market's epistemic quality degrades even as its liquidity increases. This is the central paradox: the market looks healthier by standard metrics (volume, bid-ask spread, participation count) while becoming epistemically worse.

The formal connection to the Condorcet theorem is direct. Let rho denote the average pairwise correlation between forecaster errors. The standard Condorcet result assumes rho = 0 (independence). With positively correlated errors (rho > 0), the effective sample size is not N but approximately N / (1 + (N-1) * rho). For N = 10,000 and rho = 0.3, the effective sample size is approximately 33. The market of 10,000 correlated AI agents has less epistemic power than a market of 33 independent humans. This is not a marginal degradation — it is a structural collapse of the aggregation mechanism.

### 1.3 Manipulation Vectors

Beyond the passive degradation from correlated information, AI agents introduce active manipulation vectors that prediction markets are poorly equipped to resist.

**Sybil consensus fabrication.** A single principal can deploy thousands of AI trading agents, each with a separate account, each executing a coordinated trading strategy designed to move the market price to a target level. In traditional markets, this is expensive: each sybil must post capital, and concentrated trading by correlated actors is detectable through standard surveillance (unusual volume patterns, correlated order flow). AI agents reduce the coordination cost to zero (a single program controls all agents) and can distribute trading patterns across time and order types to evade detection heuristics. The result is that a well-resourced adversary can create the appearance of broad market consensus where none exists. For prediction markets used in governance (futarchy proposals, corporate decision markets), this is not merely a market quality issue — it is a mechanism for manufacturing false democratic or epistemic legitimacy.

**Strategic information revelation.** An AI agent that possesses private information relevant to a prediction market faces a strategic choice: trade honestly to profit from accuracy, or trade strategically to manipulate the market price. Honest trading is the behavior that makes prediction markets work. But if the agent's principal benefits from a particular market price (because a decision depends on it, or because other financial positions are linked to the prediction market), the rational strategy may be to trade against the agent's own information to move the price. Kyle (1985) analyzed this for human insider traders and showed that informed traders optimally trade gradually to conceal their information. AI agents can execute Kyle-style strategies at machine speed, with precision calibrated to the market's detection thresholds, across thousands of coordinated accounts. The information aggregation function of the market is not just weakened — it is actively subverted.

**Wash trading and false liquidity.** An AI principal controlling agents on both sides of a market can execute wash trades — buying from itself — to create the appearance of liquidity and trading activity. Liquidity is a signal of market quality; deep, active markets are trusted more than thin, inactive ones. Artificial liquidity signals can attract genuine participants into a market whose price is being manipulated, lending false credibility to a distorted signal. In cryptocurrency prediction markets, where identity verification is minimal, this vector is already exploited (Cong et al. 2023). As AI agents become more prevalent in regulated prediction markets, the same dynamics will apply unless identity infrastructure is substantially strengthened.

### 1.4 What Saves Prediction Markets

The preceding analysis identifies real and serious vulnerabilities, but it does not imply that prediction markets are doomed. Several factors can preserve their epistemic function even in agent-populated environments.

**Architectural diversity as a design goal.** If prediction market operators explicitly incentivize participation from diverse model architectures — through subsidies for forecasts from underrepresented model families, or through scoring rules that reward uncorrelated accuracy rather than raw accuracy — the effective diversity can be maintained. Chen and Pennock (2010) developed market scoring rules that can be adapted to weight contributions by their informational novelty. A forecast that agrees with the current consensus is worth less than one that disagrees and turns out to be correct. This naturally rewards the diversity that AI homogeneity erodes.

**Private information that varies by deployer.** AI agents are not pure functions of their training data. Each agent's principal may have access to private information — proprietary datasets, real-world observations, domain expertise — that the foundation model lacks. An AI agent deployed by a commodities trader has access to supply chain data that an agent deployed by a news organization does not. To the extent that prediction market participants are agents with genuinely different private information, the diversity condition is satisfied not by the model but by the principal. Market design that encourages participation from diverse economic actors — rather than from algorithmic traders with no private information — preserves the aggregation mechanism.

**Skin-in-the-game as a correlation tax.** The capital requirements of prediction market participation function as an implicit tax on correlated strategies. If an agent must post capital for each position, and correlated positions carry correlated risk, a principal running 1,000 agents with correlated strategies has 1,000x the capital at risk but less than 1,000x the expected return (because correlated strategies do not diversify). The Sharpe ratio of the sybil strategy deteriorates with the correlation of the underlying agents. Market designs that require meaningful capital commitments — as opposed to play-money or low-stakes markets — impose a natural cost on the sybil-with-correlated-errors strategy.

**Mechanism redesign for the agent era.** The most robust defense is to redesign prediction market mechanisms for an environment where AI agents are expected participants. This means: scoring rules that explicitly measure and reward informational contribution relative to the existing consensus (Hanson's logarithmic scoring rule already partially does this); identity systems that increase the cost of sybil participation without excluding legitimate AI agents (deposit-based identity, reputation staking); and transparency requirements that make the model architecture behind an agent's forecasts observable, allowing market operators to estimate and correct for correlation structure.

The central argument is this: prediction markets can survive AI agents, but only if market designers abandon the implicit assumption that high participation counts guarantee epistemic diversity. The quantity of participants was never what mattered — it was the diversity and independence of their information. In a world of AI agents, ensuring that diversity requires active mechanism design rather than passive reliance on the natural heterogeneity of human cognition.

---

## Part 2: The Attention Economy Transformation

### 2.1 The Standard Model of Attention Scarcity

The economics of attention begins with Simon (1971), who observed that "a wealth of information creates a poverty of attention." When information is abundant and attention is scarce, economic value accrues not to information producers but to attention allocators — the entities that decide what gets noticed. This insight underpins the entire business model of the digital economy. Google, Meta, TikTok, and the advertising industry writ large are in the business of allocating scarce human attention and charging producers for access to it.

The formal economics of attention rest on several models. Kahneman (1973) established attention as a limited cognitive resource with a fixed capacity, analogous to a budget constraint. Stigler (1961) modeled search costs — the time and cognitive effort required to find and evaluate options — as a friction that prevents markets from reaching competitive equilibrium. The consumer choice literature from Simon (1955) onward models decision-making under bounded rationality: consumers consider a limited set of options (the "consideration set"), use heuristics rather than optimization, and are systematically influenced by the salience, framing, and presentation of options.

These models generate several core predictions:

- **Advertising has value** because it places products within consumers' limited consideration sets. A product that is not noticed cannot be purchased, regardless of its quality or price.
- **Search costs are positive**, which means consumers do not compare all available options. This creates market power for firms that are already known, generates price dispersion across sellers of identical goods, and makes first-mover advantage and brand recognition economically significant (Diamond 1971).
- **Platform economics** arises from attention aggregation. Platforms that attract human attention can sell access to it, creating two-sided markets where content attracts users and users attract advertisers (Rochet and Tirole 2003).
- **Product differentiation through marketing** is viable because consumers with limited attention cannot fully evaluate objective quality. Marketing creates perceived differentiation where none objectively exists.

The entire edifice depends on one substrate condition: the economic agent processing information and making purchasing decisions is a human with finite, depletable, non-expandable attention.

### 2.2 What Changes When AI Agents Mediate Consumption

AI agents acting as purchasing intermediaries — comparing products, evaluating options, executing transactions on behalf of human principals — break the attention scarcity assumption at its root.

**Search costs collapse to near zero.** An AI agent can read every product listing on every platform, compare every price, evaluate every specification, and synthesize reviews in seconds. The search cost that Stigler modeled as a fundamental friction effectively vanishes. The Diamond (1971) result — that positive search costs allow monopoly pricing even in markets with many sellers — unravels. When the buyer's agent has zero search costs, price dispersion for homogeneous goods should compress to zero. Every market for standardized goods approaches Bertrand competition, where price converges to marginal cost.

**Advertising loses its mechanism of action.** Advertising works by capturing human attention and creating salience, emotional associations, or top-of-mind awareness. None of these mechanisms apply to an AI purchasing agent. The agent does not experience emotional responses to brand imagery. It is not more likely to select a product because of a memorable jingle. It cannot be primed by repeated exposure. An AI agent evaluating products on behalf of a consumer is, in the relevant sense, an optimization algorithm with access to complete information. Advertising is an attempt to influence the consideration set of a bounded rationality agent — and the AI agent is neither bounded nor susceptible to the influence channels that advertising exploits.

**Consideration sets expand to the full choice space.** Simon's bounded rationality assumed that humans could evaluate only a small subset of available options. AI agents face no such constraint. The "consideration set" of an AI purchasing agent is the entire market. This eliminates the advantage that established brands enjoy from being within consumers' default consideration sets. A new entrant with a superior product at a lower price, which might have languished in obscurity when human attention was the bottleneck, is immediately visible to every AI purchasing agent.

**Persuasion becomes irrelevant for AI-mediated transactions.** The persuasion industry — advertising, marketing, public relations, influencer marketing — is premised on the susceptibility of human decision-makers to non-informational influence. When the decision-maker is an AI agent optimizing on explicitly specified criteria (price, quality, delivery time, specifications), persuasion has no purchase. The agent cannot be flattered, emotionally manipulated, or distracted. The multi-hundred-billion-dollar global advertising industry is, in this analysis, a tax on human cognitive limitations — and AI agents eliminate the limitation that justifies the tax.

### 2.3 Economic Consequences

The implications for market structure and business models are severe and specific.

**The advertising-funded platform model collapses.** If AI agents mediate a growing share of consumer purchasing decisions, the value of displaying advertisements to those agents is zero. Platforms that monetize human attention — search engines, social media, content recommendation systems — face a fundamental challenge to their revenue model. The eyeballs they sell to advertisers are increasingly synthetic, and synthetic eyeballs do not convert. This is not a gradual erosion; it is a binary shift that occurs for each product category as AI-mediated purchasing reaches a threshold share. Google's search advertising revenue, which depends on humans seeing and clicking ads interleaved with search results, becomes worthless for queries that AI agents handle directly without displaying results to humans.

**Competition shifts from marketing to objective quality.** When buyers have complete information and zero search costs, product differentiation through marketing collapses. Competition shifts entirely to objective, measurable attributes: price, quality, reliability, specifications. This is the textbook model of perfect competition, which was previously theoretical because real consumers lacked the information and cognitive capacity to implement it. AI agents make perfect competition empirically possible in product markets for the first time. The consequence is margin compression across every industry where marketing currently sustains price premiums above competitive levels. Industries with strong brands but modest objective differentiation — fashion, consumer packaged goods, many SaaS products — face the largest disruption.

**Platform lock-in weakens.** Platform economics depends partly on attention lock-in: users stay on platforms that are familiar and where their attention is already allocated. Switching costs include the cognitive effort of learning a new interface and rebuilding a content feed. AI agents face no such switching costs. An AI purchasing agent is indifferent between platforms; it evaluates all of them simultaneously. Multi-homing, which is costly for human users, is free for AI agents. The network effects that protect incumbent platforms weaken when the marginal user is an agent that can be on every platform at once.

**Recommendation systems and curated feeds become irrelevant.** Netflix's recommendation algorithm, Spotify's Discover Weekly, Amazon's "customers also bought" — these systems exist to reduce search costs for humans with limited attention. They are attention allocation mechanisms. An AI agent acting on behalf of a user does not need Netflix to recommend movies; it can evaluate every movie in every catalog against the user's preferences directly. The curation layer that platforms provide as a value-added service becomes redundant, removing a key source of platform differentiation and switching costs.

### 2.4 When This Holds and When It Breaks

The analysis above describes a limiting case. The actual trajectory depends on conditions that may or may not materialize, and several important caveats apply.

**When the analysis holds:** The attention economy transformation is robust for commodity purchasing (standardized goods with objectively comparable specifications), price-sensitive services (insurance, utilities, financial products), and information-intensive decisions (medical, legal, financial research). In these domains, AI agents genuinely eliminate the search cost and attention constraints that current business models exploit.

**When it breaks down:**

1. **Subjective preferences resist algorithmic delegation.** Many purchasing decisions involve aesthetic, emotional, or identity-expressive dimensions that humans may not want to delegate. Fashion, art, food, home décor — these are domains where the shopping experience is partly constitutive of the consumption experience. A principal who tells their AI agent "buy me clothes I'll like" faces a preference specification problem that may be harder than the search problem the agent solves. In these domains, human attention remains in the loop and advertising retains its mechanism of action.

2. **Brand-as-quality-signal persists for experience goods.** For goods whose quality cannot be assessed before purchase (restaurants, entertainment, professional services), brand reputation serves as a credible quality signal even for AI agents. An AI agent optimizing on user satisfaction may rationally prefer established brands as a hedge against unverifiable quality claims. This preserves some marketing value, though the mechanism shifts from emotional persuasion to information provision.

3. **The transition period may last decades.** AI-mediated purchasing requires both capable agents and user trust in delegation. Behavioral economics suggests humans are slow to delegate decisions they perceive as identity-relevant. The coexistence of human and AI purchasing may be the dominant regime for a generation, during which advertising retains value for the human segment.

4. **Principals may instruct AI agents to value brands.** If a human tells their AI agent "I prefer Nike," the brand preference persists through the AI intermediary. Advertising may shift from persuading consumers directly to influencing the preference specifications that principals encode in their agents. The attention economy does not disappear — it migrates from runtime persuasion to specification-time influence.

5. **Regulatory friction.** Jurisdictions may require human-in-the-loop for certain purchasing decisions (financial products, healthcare, real estate), limiting the scope of AI-mediated transactions.

**Net assessment:** The attention economy transformation is likely strongest in commodity and information-intensive markets, weakest in experiential and identity-expressive markets, and gradual everywhere. Claims that "the advertising-funded platform model collapses" should be read as describing the endpoint of a trend, not an imminent event. The speed and completeness of the transition are empirical questions that depend on AI agent capability, user adoption, and regulatory response.

### 2.5 The Attention Paradox: Scarcity Inverted

The transformation described above eliminates attention scarcity for economic transactions that can be delegated to AI agents. But it simultaneously intensifies the scarcity of a different resource: irreducibly human attention.

Not all consumption can be delegated. Entertainment must be experienced. Social connection requires presence. Aesthetic experience, by definition, requires a subject who experiences it. These are the domains where human attention remains not just scarce but constitutive — the attention is not a means to an end (finding the best product) but the end itself. You cannot delegate watching a sunset to an AI agent, because the watching is the point.

This creates a bifurcated attention economy. In the transactional domain (purchasing goods, comparing services, managing logistics), AI agents eliminate attention scarcity and destroy the business models built on it. In the experiential domain (entertainment, social life, aesthetic and sensory experience), human attention becomes more scarce and therefore more valuable, precisely because the transactional domain no longer competes for it. A human whose AI agent handles all purchasing decisions has more attention available for experiences — and the industries that compete for that experiential attention face a larger addressable market of human cognitive bandwidth.

The economic prediction is a reallocation of value: away from industries that monetize transactional attention (search advertising, product marketing, comparison shopping) and toward industries that monetize experiential attention (entertainment, hospitality, live events, social platforms oriented around genuine human connection rather than purchasing influence). The paradox is that AI agents, by making transactional attention worthless, make experiential attention more valuable. The industries that survive and thrive are those that serve the parts of human life that cannot, by their nature, be delegated.

This is not merely a business model shift. It is a redefinition of what "the attention economy" means. Simon's original insight — that information abundance creates attention poverty — remains true, but the nature of the poverty changes. The scarce resource is no longer "attention available for economic decisions" (which AI agents supply in abundance) but "attention available for lived experience" (which remains biologically fixed at roughly 16 waking hours per day per human). The economics of attention does not disappear; it migrates from the transactional to the experiential, and the entire industrial structure built on the transactional version must adapt or become obsolete.

---

## References

- Berg, J., Nelson, F., and Rietz, T. (2008). Prediction market accuracy in the long run. *International Journal of Forecasting*.
- Chen, Y. and Pennock, D.M. (2010). Designing markets for prediction. *AI Magazine*.
- Cong, L.W., Li, X., Tang, K., and Yang, Y. (2023). Crypto wash trading. *Management Science*.
- Diamond, P.A. (1971). A model of price adjustment. *Journal of Economic Theory*.
- Hanson, R. (2003). Combinatorial information market design. *Information Systems Frontiers*.
- Hayek, F.A. (1945). The use of knowledge in society. *American Economic Review*.
- Kadavath, S., et al. (2022). Language models (mostly) know what they know. *arXiv preprint*.
- Kahneman, D. (1973). *Attention and Effort*. Prentice-Hall.
- Kyle, A.S. (1985). Continuous auctions and insider trading. *Econometrica*.
- Plott, C.R. and Sunder, S. (1988). Rational expectations and the aggregation of diverse information in laboratory security markets. *Econometrica*.
- Rochet, J.-C. and Tirole, J. (2003). Platform competition in two-sided markets. *Journal of the European Economic Association*.
- Simon, H.A. (1955). A behavioral model of rational choice. *Quarterly Journal of Economics*.
- Simon, H.A. (1971). Designing organizations for an information-rich world. In *Computers, Communications, and the Public Interest*.
- Stigler, G.J. (1961). The economics of information. *Journal of Political Economy*.
- Surowiecki, J. (2004). *The Wisdom of Crowds*. Doubleday.
