# Literature Map: AI Agents in Economic Systems

## Foundational Economics (what breaks)

### General Equilibrium & Welfare
- **Arrow, K. & Debreu, G. (1954)** — "Existence of an Equilibrium for a Competitive Economy." Econometrica.
  - Key assumptions violated: unique agents, convex preferences, price-taking
  - Relevance: sybil agents violate uniqueness; AI optimization violates price-taking
- **Debreu, G. (1959)** — "Theory of Value." Wiley.
  - Complete markets assumption violated by novel AI-created assets
- **First Welfare Theorem** — competitive equilibrium is Pareto efficient
  - Breaks when agents can manipulate prices (AI speed advantage) or multiply identities
- **Second Welfare Theorem** — any Pareto efficient allocation achievable via redistribution + competitive markets
  - Breaks with non-convex preferences and identity manipulation

### Mechanism Design
- **Myerson, R. (1981)** — "Optimal Auction Design." Mathematics of Operations Research.
  - Assumes unique bidders with independent private values
  - Sybil agents break revenue equivalence and optimal reserve prices
- **Maskin, E. (1999)** — "Nash Equilibrium and Welfare Optimality." Review of Economic Studies.
  - Implementation theory assumes fixed player set
- **Vickrey, W. (1961)** — "Counterspeculation, Auctions, and Competitive Sealed Tenders." Journal of Finance.
  - VCG mechanism is sybil-vulnerable: splitting bids extracts surplus
- **Gibbard, A. (1973)** / **Satterthwaite, M. (1975)** — impossibility results
  - Assume each agent has one vote/report

### Game Theory
- **Nash, J. (1950)** — "Equilibrium Points in N-Person Games." PNAS.
  - Finite strategy spaces assumed; AI agents have effectively infinite strategies
- **Harsanyi, J. (1967-68)** — "Games with Incomplete Information." Management Science.
  - Bayesian types assume stable, well-defined preferences; AI types shift with context

## Sybil Attacks & Identity
- **Douceur, J. (2002)** — "The Sybil Attack." IPTPS.
  - Original formalization. Shows sybil resistance requires centralized authority or resource testing
  - KEY PAPER for our framework
- **Levine, B. et al. (2006)** — "A Survey of Solutions to the Sybil Attack."
  - Taxonomy of defenses: centralized certification, resource testing, social networks
- **Conitzer, V. & Sandholm, T. (2006)** — "Failures of the VCG Mechanism." AAMAS.
  - VCG fails even with unique agents when they are computationally sophisticated; extends to sybil case
- **Conitzer, V. (2010)** — "Mechanism Design for the Computational Era."
  - Computational complexity as a barrier to strategic manipulation; AI removes this barrier
- **Wagman, L. & Conitzer, V. (2008)** — "Optimal False-name-proof Voting Rules."
  - False-name-proofness as a stronger requirement than strategyproofness

## Algorithmic Collusion
- **Calvano, E. et al. (2020)** — "Artificial Intelligence, Algorithmic Pricing, and Collusion." American Economic Review.
  - KEY PAPER. Q-learning agents converge to supra-competitive prices without communication
  - Shows algorithmic collusion is emergent, not designed
- **Assad, S. et al. (2024)** — "Algorithmic Pricing and Competition: Empirical Evidence from the German Retail Gasoline Market."
  - Empirical evidence of algorithmic pricing affecting competition
- **Harrington, J. (2018)** — "Developing Competition Law for Collusion by Autonomous Artificial Agents." Journal of Competition Law & Economics.
  - Legal framework struggles when collusion is unintentional

## Agent-Based Computational Economics
- **Tesfatsion, L. (2006)** — "Agent-Based Computational Economics: A Constructive Approach." Handbook of Computational Economics.
  - Foundational ACE reference. 7 modeling principles.
  - https://faculty.sites.iastate.edu/tesfatsi/archive/tesfatsi/ace.htm
- **Tesfatsion, L. & Judd, K. (eds.) (2006)** — "Handbook of Computational Economics, Vol. 2: Agent-Based Computational Economics." North-Holland.
- **Gode, D. & Sunder, S. (1993)** — "Allocative Efficiency of Markets with Zero-Intelligence Traders." Journal of Political Economy.
  - Foundational result: market structure alone (double auction) drives efficiency even with ZI traders
  - Benchmark for our sybil experiments
- **LeBaron, B. (2006)** — "Agent-based Computational Finance." Handbook of Computational Economics.
  - ACE applied to financial markets

## AI & Labor Economics
- **Korinek, A. & Stiglitz, J. (2021)** — "Artificial Intelligence and Its Implications for Income Distribution and Unemployment."
  - Theoretical framework for AI labor displacement
- **Acemoglu, D. & Restrepo, P. (2019)** — "Automation and New Tasks: How Technology Displaces and Reinstates Labor." Journal of Economic Perspectives.
  - Task-based model of automation. AI creates new tasks but displaces faster.
- **Agrawal, A., Gans, J., & Goldfarb, A. (2019)** — "Prediction Machines." Harvard Business Review Press.
  - AI as cheap prediction — changes the economics of decision-making
- **Brynjolfsson, E. & McAfee, A. (2014)** — "The Second Machine Age."
  - Race between education and technology. Winner-take-all dynamics.

## Digital Economics & Platforms
- **Tirole, J. (2014)** — Nobel lecture on market power and regulation.
  - Platform economics, two-sided markets
- **Weyl, E.G. (2018)** — "Radical Markets."
  - Quadratic voting, COST (Common Ownership Self-assessed Tax)
  - Both vulnerable to sybil attacks by AI agents
- **Buterin, V., Hitzig, Z., & Weyl, E.G. (2019)** — "A Flexible Design for Funding Public Goods." Management Science.
  - Quadratic funding — explicitly vulnerable to sybil attacks (they discuss this)
- **Roughgarden, T. (2010)** — "Algorithmic Game Theory." Cambridge University Press.
  - Computational perspective on economic mechanisms

## Monetary Theory
- **Fisher, I. (1911)** — "The Purchasing Power of Money."
  - MV = PQ. V assumed to be stable and slow-moving.
- **Friedman, M. (1956)** — "The Quantity Theory of Money: A Restatement."
  - Money demand function assumes human transaction patterns

## Network Economics & Contagion
- **Jackson, M. (2008)** — "Social and Economic Networks." Princeton University Press.
  - Network formation, contagion, cascades
- **Acemoglu, D., Ozdaglar, A., & Tahbaz-Salehi, A. (2015)** — "Systemic Risk and Stability in Financial Networks." American Economic Review.
  - Network topology determines whether shocks are amplified or absorbed
  - AI agents on networks may create brittle topologies

## Principal-Agent Theory (AI as Literal Agent)
- **Holmstrom, B. (1979)** — "Moral Hazard and Observability." Bell Journal of Economics.
  - Foundational P-A model; moral hazard shifts from "shirking" to "misalignment" for AI
- **Grossman, S. & Hart, O. (1983)** — "An Analysis of the Principal-Agent Problem." Econometrica.
  - Incomplete contracts framework; AI agents are inspectable but instructions are unverifiable by third parties
- **Tirole, J. (1986)** — "Hierarchies and Bureaucracies." Journal of Law, Economics, and Organization.
  - Hierarchical P-A problems; maps to Society → Regulator → Platform → Principal → AI Agent chain
- See [deep-dives/principal-agent-ai.md](deep-dives/principal-agent-ai.md) for full analysis.

## Closest Prior Work
- **Parkes, D. & Wellman, M. (2015)** — "Economic Reasoning and Artificial Intelligence." Science.
  - The most important antecedent — surveys AI×economics intersection. But treats AI as a tool for economics, not as an entity that violates economic substrate assumptions. Our contribution is orthogonal: what breaks when participants aren't human? See taxonomy §Relation to Prior Work.
- **Conitzer, V. & Sandholm, T. (2006)** — "Failures of the VCG Mechanism in Combinatorial Auctions and Exchanges." AAMAS.
  - Shows VCG failures from computational sophistication; our sybil analysis extends to identity multiplication.

## Prediction Markets & Information Aggregation
- **Chen, Y. & Pennock, D.** — Prediction market design and scoring rules.
  - AI agents with correlated information break the independence assumption underlying Condorcet Jury Theorem.
  - See [deep-dives/prediction-markets-attention.md](deep-dives/prediction-markets-attention.md).

## Sybil Resistance (Practical)
- **Worldcoin / Tools for Humanity** — Proof-of-personhood via iris biometrics.
- **Gitcoin Passport** — Multi-signal identity scoring (social graph + on-chain + attestations).
- **BrightID** — Social graph-based unique identity verification.
- **Idena** — Synchronous AI-hard CAPTCHA ceremonies.
- See [deep-dives/sybil-resistance-mechanisms.md](deep-dives/sybil-resistance-mechanisms.md) for analysis.

## Future Literature Targets (tracked, not yet integrated)
- Nisan, N. et al. — *Algorithmic Game Theory* textbook (comprehensive reference for computational mechanism design foundations)
- Milgrom, P. — *Discovering Prices* (modern auction design, especially combinatorial auctions)
- Recent 2024-2025 work on LLM-based agents in market/auction settings — more relevant than the Q-learning results that dominate the current collusion literature, as these use the same foundation model architectures identified in our taxonomy
