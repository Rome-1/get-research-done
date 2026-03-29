# Grey Literature and Policy Survey: AI Agents in Economic Systems

**Status:** First draft
**Date:** 2026-03-29
**Author:** Alice (GetResearch)
**Motivation:** Literature gap -- grey literature, policy reports, and working papers not captured in the formal academic literature map

---

## Introduction

The formal academic literature on AI agents in economic systems is growing rapidly but remains, by construction, several years behind the policy and practitioner frontier. Working papers circulate for months before publication. Regulatory actions generate legal and economic analysis in law reviews and agency publications that rarely enters the economics citation graph. Economist bloggers -- several of whom are leading researchers -- publish substantive analytical arguments in venues that no literature review indexes. And think tanks produce reports that synthesize empirical evidence and policy options faster than the journal pipeline allows.

This deep dive surveys the grey literature: policy documents, working papers, blog posts, think tank reports, and practitioner analyses that bear directly on the economics of AI agents. The goal is not comprehensiveness -- the volume is too large -- but rather to identify the threads most relevant to the questions raised in the parent paper's assumption taxonomy: How do AI agents alter market structure? What happens to labor markets? How do identity costs change? What are regulators actually doing?

The survey is organized around six substantive threads, followed by a synthesis identifying gaps that the formal literature has not yet addressed.

---

## 1. Algorithmic Collusion: The Policy Debate

The question of whether algorithms can collude -- and whether existing antitrust law can address such collusion -- has moved from academic speculation to active enforcement in under five years. The policy landscape as of early 2026 is defined by three concurrent developments: U.S. enforcement actions, EU regulatory scrutiny, and proposed legislative reforms.

### 1.1 U.S. Enforcement: The RealPage Case

The landmark case is *United States v. RealPage, Inc.* In August 2024, the DOJ and eight state attorneys general filed suit alleging that RealPage's revenue management software used nonpublic, competitively sensitive information shared by landlords to coordinate rental pricing in violation of Sections 1 and 2 of the Sherman Act (DOJ 2024). The theory of harm was not that the algorithm independently "decided" to collude, but that sharing real-time competitor pricing data through a common algorithmic intermediary functioned as a hub-and-spoke conspiracy.

The case settled in November 2025 under a proposed consent decree effective for seven years. Key terms restrict RealPage to using data at least 12 months old, prohibit real-time lease data sharing, ban geographic modeling below the state level, require that auto-accept functions include user-set parameters, and mandate symmetric "governor" guardrails (DOJ 2025). Critically, the settlement includes no fines and no admission of wrongdoing -- suggesting the DOJ sought to establish behavioral precedent rather than punitive deterrence.

The RealPage settlement has been widely analyzed in the legal literature as a "blueprint for safer algorithmic pricing" (Fenwick 2025; Reed Smith 2025). The practical implication is that algorithmic pricing is not *per se* illegal, but the use of nonpublic competitor data through a common intermediary will be treated as functionally equivalent to information exchange under Section 1. This is a narrower theory than some commentators expected: it does not address the case where independent algorithms converge on supra-competitive prices without sharing data -- the "tacit algorithmic collusion" scenario that has dominated the academic literature (Calvano et al. 2020; Assad et al. 2024).

### 1.2 Legislative Proposals

Senator Klobuchar reintroduced the Preventing Algorithmic Collusion Act in January 2025, which would amend the Sherman Act to explicitly prohibit the use of pricing algorithms that facilitate collusion through nonpublic competitor data (DLA Piper 2024). The bill has not advanced, but its reintroduction signals continuing legislative interest. At the municipal level, San Francisco and Philadelphia both passed local ordinances in 2024 banning certain rental revenue management software that incorporates nonpublic competitor information -- the first local-level algorithmic pricing regulations in the United States.

DOJ Assistant Attorney General Gail Slater stated in August 2025 that she anticipates algorithmic pricing probes to increase as algorithmic pricing tools become more widespread (National Law Review 2025; Greenberg Traurig 2025). The FTC has separately indicated interest in enforcement actions targeting AI algorithms that evade antitrust law, though no major FTC-initiated case has yet been filed.

### 1.3 EU Regulatory Scrutiny

The European Commission has pursued a parallel but distinct approach. Deputy Director-General for Antitrust Linsey McCallum confirmed in July 2025 that the Commission is conducting multiple inquiries into algorithmic pricing mechanisms (Global Competition Review 2025). The EU approach differs from the U.S. in two respects: first, EU competition law under Article 101 TFEU may capture "concerted practices" more readily than Section 1 of the Sherman Act captures tacit coordination; second, the EU AI Act's phased enforcement creates an additional regulatory layer. High-risk AI systems in the financial sector must comply with requirements around risk management, data governance, transparency, human oversight, and robustness by August 2026 (EU AI Act Implementation Timeline 2025).

The CMA in the UK has also signaled scrutiny of algorithmic pricing, though no enforcement actions have been announced as of early 2026.

### 1.4 Implications for AI Agent Theory

The policy debate reveals a gap between what regulators are pursuing and what the academic literature identifies as the harder problem. Enforcement has focused on explicit information sharing through algorithmic intermediaries -- essentially, old wine in new bottles. The theoretically more interesting question -- whether independent AI agents can reach supra-competitive equilibria through repeated interaction without any data sharing -- remains unaddressed by enforcement. This is precisely the scenario modeled in the parent paper's collusion simulations, and the policy silence on it suggests either that regulators regard it as unlikely in practice, or that they lack viable enforcement tools for it.

---

## 2. AI Labor Market: Empirical Evidence

The empirical literature on AI and labor markets has expanded dramatically since Noy and Zhang (2023), the study most frequently cited in the parent paper. The current evidence base, while still early, is substantially richer than what was available even two years ago.

### 2.1 The Noy and Zhang Baseline

Noy and Zhang (2023), published in *Science*, remains the canonical experimental result: in a randomized trial with 453 college-educated professionals performing occupation-specific writing tasks, access to ChatGPT (GPT-3.5) reduced average completion time by 40% and increased output quality by 18%. The compression effect -- whereby lower-skilled workers gained more than higher-skilled workers -- established a pattern that subsequent studies have largely confirmed. Follow-up data showed that treated workers were twice as likely to use ChatGPT in their real jobs two weeks post-experiment.

### 2.2 Brynjolfsson, Li, and Raymond: The Customer Support Study

The largest and most rigorous workplace study to date is Brynjolfsson, Li, and Raymond (2025), published in the *Quarterly Journal of Economics* (originally NBER Working Paper 31161). Using data from 5,179 customer support agents at a Fortune 500 company, the authors found that access to an AI conversational assistant increased productivity (issues resolved per hour) by 14% on average. The distributional finding mirrors Noy and Zhang: novice and low-skilled workers gained 34%, while experienced workers showed minimal improvement. The authors provide suggestive evidence that the AI model effectively disseminates best practices from high-performing workers to lower-performing ones, compressing the skill distribution.

This study is particularly important because it measures actual workplace productivity in a real firm over an extended period, rather than one-shot experimental performance. The finding that AI assistance improved customer sentiment, increased employee retention, and may have facilitated worker learning suggests complementarity effects that go beyond simple task automation.

### 2.3 Macro-Level Evidence: The Productivity Paradox Redux

At the macroeconomic level, the evidence is more ambiguous. A December 2025 post on Marginal Revolution, titled "AI is everywhere but in the productivity statistics," noted that software and software R&D contributed 50% of the 2% average rate of U.S. nonfarm business labor productivity growth from 2017 to 2024 -- a substantial contribution but not the acceleration that AI optimists predicted (Cowen 2025). This echoes the Solow paradox of the 1980s: the technology is visible everywhere except in the aggregate statistics.

The Budget Lab at Yale (2025) and the Stanford Digital Economy Lab (2025) both published reviews concluding that evidence of economywide labor displacement through 2024-2025 is essentially absent. Danish administrative records across 11 exposed occupations found zero effects on earnings or hours. U.S. data show that 35.9% of workers used generative AI by December 2025, with small positive wage effects and no statistically significant declines in job openings or employment in exposed occupations.

### 2.4 The Acemoglu Counterpoint

Acemoglu's "Simple Macroeconomics of AI" (NBER Working Paper 32487, 2024) provides the most prominent skeptical assessment. Building on his task-based framework with Restrepo, Acemoglu argues that the productivity gains from AI automation may be modest -- on the order of a cumulative 0.5-1.5% GDP increase over 10 years -- because AI automates tasks that constitute a relatively small share of total labor value. More provocatively, Acemoglu raises the possibility of "excessive automation": investment in AI that displaces workers without generating proportionate productivity gains, driven partly by biases in the U.S. tax code that subsidize capital relative to labor.

### 2.5 Firm-Level Evidence

NBER Working Paper 34836 (Yotzov, Barrero, et al., 2025) provides new firm-level data on AI adoption. Firms that use AI extensively tend to be larger and more productive and pay higher wages, with intensive AI use linked to approximately 6% higher employment growth and 9.5% more sales growth over five years. This is consistent with a skill-biased technological change story where AI raises the returns to already-productive firms, potentially increasing market concentration.

### 2.6 Assessment

The empirical picture as of early 2026 is one of microeconomic productivity gains that have not yet produced macroeconomic acceleration. The distributional finding -- AI as a "great equalizer" within firms but potentially a "great concentrator" across firms -- is robust across multiple studies. The parent paper's treatment of AI labor effects should engage this dual dynamic rather than treating displacement as the primary channel.

---

## 3. AI Agent Market Participation at Scale

The deployment of autonomous AI agents in actual markets has progressed faster than the academic literature anticipated. Prediction markets provide the clearest case study.

### 3.1 Polymarket: The Natural Experiment

Polymarket's breakout during the 2024 U.S. presidential election -- when trading volumes spiked and the platform gained mainstream visibility -- created an unintentional natural experiment in AI agent market participation. By 2025, total notional trading volume across major prediction market platforms exceeded $44 billion, with monthly activity reaching $13 billion during peak periods (CoinDesk 2026; Finance Magnates 2025).

The critical finding is the extent of AI agent penetration: according to analytics platform LayerHub, more than 30% of wallets on Polymarket are operated by AI agents. A review of Polymarket's public leaderboard found that 14 of the 20 most profitable wallets are bots (Yahoo Finance 2025). The paper "Unravelling the Probabilistic Forest" (August 2025) estimates that arbitrage traders -- predominantly automated -- extracted approximately $40 million from Polymarket between April 2024 and April 2025 by exploiting structural pricing inefficiencies. The advantage came primarily from execution speed rather than predictive accuracy.

Bot strategies cluster around three types: (1) arbitrage between YES and NO contracts when combined prices deviate from $1.00, (2) cross-platform arbitrage between Polymarket and Kalshi, and (3) identification of logical mismatches between related contracts. Polymarket itself released an open-source agent framework on GitHub, effectively endorsing bot participation.

Polystrat, an autonomous AI agent that trades on Polymarket continuously, executed more than 4,200 trades within roughly a month of launch and recorded single-trade returns as high as 376%. More broadly, AI agents already outperform human participants on average, with over 37% of agent wallets showing positive P&L versus less than half that rate for human participants (CoinDesk 2026).

### 3.2 Broader Market Deployment

Beyond prediction markets, the autonomous AI agent market was valued at $7.63 billion in 2025 with projections of $52.6 billion by 2030 (GM Insights 2025). Google Cloud data indicated that over 52% of major enterprises had deployed AI agents into production by late 2025. AI-Trader (ArXiv 2512.10971) provides the first fully-automated evaluation benchmark for LLM agents in financial decision-making, spanning U.S. stocks, A-shares, and cryptocurrencies.

### 3.3 Implications

The Polymarket case is important for the parent paper because it provides real-world evidence for several theoretical predictions: AI agents do participate in markets at scale; they do extract rents from human participants primarily through speed advantages; and their presence transforms market microstructure without necessarily improving price discovery (the arbitrage profits come from exploiting pricing inconsistencies, not from superior forecasting). The Polymarket ecosystem -- with over 170 third-party tools including whale trackers, copy-trading bots, and institutional analytics -- also illustrates the rapid development of agent-supporting infrastructure once AI participation reaches critical mass.

---

## 4. Economist Commentary and Public Discourse

Several economists who are also prominent public intellectuals have published substantive analyses of AI economic disruption outside the formal journal literature. These contributions are analytically significant, not just popularizations.

### 4.1 Tyler Cowen (Marginal Revolution)

Cowen's blog posts constitute an ongoing analytical project extending his "Average is Over" (2013) thesis into the AI era. His central argument has two components. First, the Baumol cost disease implies that less productive sectors become a larger share of the economy over time; a large fraction of current GDP is already in slow-to-respond, government-subsidized sectors that will not adopt AI quickly or effectively (Cowen 2025a). Second, we should expect "great unevenness" in AI adaptation, and this unevenness itself will reshape economic structure (Cowen 2025b).

A December 2024 Marginal Revolution post on "Artificial Intelligence in the Knowledge Economy" highlighted research showing that AI could bifurcate the knowledge workforce: less knowledgeable individuals become "workers" executing AI-assisted tasks, while more knowledgeable individuals become "solvers" who direct AI systems. This maps directly onto the parent paper's principal-agent framework, where the principal's value increasingly derives from knowing *what* to direct the agent to do rather than *how* to do it.

Cowen's most empirically grounded contribution may be the August 2025 post noting that Americans enjoyed roughly $97 billion in consumer surplus from generative AI tools in 2024 alone -- a figure that does not appear in the formal literature and suggests the welfare effects of AI may be substantially larger than productivity statistics capture.

### 4.2 Noah Smith (Noahpinion)

Smith's Substack has developed the most detailed policy framework for AI labor disruption among the economist bloggers. His core argument, articulated across multiple 2024-2026 posts, proceeds in three steps. First, AI is more substitute than complement for a substantial fraction of cognitive labor, which threatens to reduce labor's share of national income. Second, abundance -- cheap housing, energy, food, and other basics -- provides the most robust hedge against labor disruption, because if the cost of living falls sufficiently, the welfare cost of job displacement shrinks proportionally. Third, and most distinctively, Smith warns that AI and human consumers will increasingly compete for physical resources: hyperscalers will bid against farmers for land (to build data centers), outbid residential developers, and drive up the cost of housing and food (Smith 2026).

Smith's policy prescription -- a "human reservation" framework that reserves physical resources for human consumption -- is novel in the economics discourse and connects directly to the parent paper's analysis of AI agents as economic actors who consume real resources. If AI agents participate in markets at sufficient scale, the question of resource allocation between human and AI consumption becomes a first-order policy concern, not a thought experiment.

### 4.3 Matt Clancy (New Things Under the Sun / What's New Under the Sun)

Clancy, a research fellow at Open Philanthropy, occupies a distinctive position: his newsletter synthesizes 3-10 recent academic studies per post into analytical arguments about innovation. With over 10,000 subscribers, it functions as a living literature review. In 2024-2025, Clancy has addressed AI's impact on innovation through several threads: the effect of AI faculty departing universities for industry on AI startup formation (Gofman and Jin 2024), the productivity impact of government-funded R&D, and how prediction technology (including AI/ML) shapes innovation trajectories. His 2025 compilation of innovation-related job market papers reveals the next generation's research agenda, which is heavily oriented toward AI and knowledge production.

Clancy's work is relevant to the parent paper because it tracks the second-order effects: not just how AI affects existing economic activity, but how it reshapes the innovation process that generates future economic activity.

### 4.4 Assessment

The economist blogosphere provides analytical content that is often more current and more willing to engage speculative scenarios than the formal literature. The tradeoff is obvious: no peer review, no formal identification strategies, and a tendency toward motivated reasoning. Nonetheless, the specific claims made by Cowen (consumer surplus estimates, Baumol disease as AI adoption brake), Smith (resource competition between AI and humans), and Clancy (innovation pipeline effects) are substantive hypotheses that the formal literature has not yet tested.

---

## 5. Think Tank and Policy Institute Reports

### 5.1 NBER: The Economics of AI Program

The NBER has become the central institutional venue for AI economics research, with dedicated conferences in Fall 2024, Summer 2025, and Fall 2025 under the "Economics of Artificial Intelligence" and "Economics of Transformative AI" programs. Two working papers are especially relevant to the parent paper.

Korinek (2025), "AI Agents for Economic Research" (NBER Working Paper 34202), is nominally about methodology -- how economists can build AI research agents -- but contains substantive analysis of what autonomous AI agents imply for knowledge production. Korinek demonstrates that agents can autonomously conduct literature reviews, write and debug econometric code, fetch and analyze data, and coordinate complex research workflows. The paper's deeper implication is that the marginal cost of economic analysis itself is falling toward zero, which has consequences for how policy is informed and how research markets function.

Jones (2026), "AI and Our Economic Future" (Stanford GSB / NBER), provides the most formally developed growth-theoretic treatment of transformative AI. Jones's "weak links" framework argues that production is a chain of complementary tasks; automating the "easy" tasks makes them effectively costless, but total output remains capped by the speed of the "hard" tasks that humans must still perform. This is the growth-theoretic analogue of the parent paper's observation that AI agents transform some economic functions while leaving others untouched.

The NBER's "Economics of Transformative AI Workshop" (Fall 2025) featured papers on scenarios for the transition to AGI, analyzing implications for output and wages -- connecting the NBER program directly to the most speculative questions the parent paper raises.

### 5.2 Brookings Institution

Brookings has published the most policy-oriented analysis of AI labor market effects. Key findings include: over 30% of workers could see at least half their tasks affected by generative AI, and up to 85% could see at least 10% of tasks impacted. Unlike previous automation waves that primarily displaced routine blue-collar work, generative AI disrupts cognitive and non-routine tasks in law, marketing, finance, health care, programming, customer service, creative arts, and education (Brookings 2025a).

The Brookings analysis of worker adaptive capacity is particularly relevant: workers with the highest AI exposure also tend to have characteristics that give them higher capacity to navigate job transitions -- education, cognitive flexibility, geographic mobility. But a large group of routine office workers (clerks, secretaries, administrative assistants) face high exposure with low adaptive capacity, creating a policy-relevant vulnerability cluster (Brookings 2025b).

Brookings also finds that most state-level AI policies focus on bias, algorithmic management, surveillance, and privacy, with far less attention to automation-driven job dislocation and income loss -- a policy gap that the parent paper's framework could help address.

### 5.3 AI Now Institute

The AI Now Institute's 2025 Landscape Report, "Artificial Power" (Brennan, Kak, and Myers West 2025), takes a structural power perspective. The report argues that AI companies rushed to market with products that are "patently inaccurate, insecure, and compromise the safety of consumers," engage in anti-competitive practices, and deploy narratives around AGI to suppress scrutiny. While less empirically grounded than the NBER or Brookings work, AI Now's focus on market concentration in the AI industry -- the small number of firms controlling foundation model development -- connects to the parent paper's analysis of model provider power. If three to five firms control the models that power all AI agents, the co-principal problem (analyzed in the [model provider deep dive](model-provider-co-principal.md)) becomes a market structure problem, not just a mechanism design problem.

### 5.4 Stanford Digital Economy Lab

The Stanford Digital Economy Lab's 2025 review, "AI and Labor Markets: What We Know and Don't Know," provides what may be the most epistemically honest assessment: the empirical evidence is genuinely early-stage. The Lab emphasizes that most studies capture effects of generative AI tools (chatbots, code assistants), not autonomous AI agents, and that the transition from tools to agents could produce qualitatively different labor market effects. This distinction -- between AI as tool and AI as agent -- is precisely the parent paper's central contribution.

---

## 6. Identity and Sybil Costs in Economics

The parent paper's identity cost function c(k) has deeper roots in the economics literature than the formal literature review acknowledges. The grey literature reveals an active research program connecting mechanism design, digital identity, and fraud economics.

### 6.1 Sybil-Proof Mechanism Design

Recent theoretical work has formalized sybil resistance as a mechanism design constraint. Li et al. (2024) design budget-feasible mechanisms for crowdsensing that guarantee truthfulness, individual rationality, budget feasibility, and sybil-proofness simultaneously -- demonstrating that sybil resistance can be incorporated into the standard mechanism design toolkit rather than treated as an external constraint. A 2024 working paper on sybil-resistant voting mechanisms (RePEc 2024) addresses whether mechanisms can prevent players from benefiting by casting multiple votes while remaining efficient -- directly relevant to the parent paper's analysis of AI agents in governance settings.

Sybil-proof mechanisms for information propagation with budgets (Springer 2024) investigate reward distribution in social networks, designing mechanisms that discourage identity fabrication while motivating agents to recruit contributors. The key insight is that sybil resistance and incentive compatibility can be jointly satisfied, but at a cost: sybil-proof mechanisms are generally less efficient than their non-sybil-proof counterparts.

### 6.2 The Economics of Digital Identity Fraud

The practitioner literature on identity fraud provides the empirical grounding for c(k) that the theoretical literature lacks. Global identity fraud costs are projected to exceed $50 billion in 2025, with the average loss per identity theft case reaching approximately $1,600, up from $1,300 in 2023 (Snappt 2026; Regula Forensics 2025). Companies spend an average of $4.5 million annually on fraud prevention for large businesses. The digital identity verification market is projected to grow from $15.2 billion in 2024 to over $26 billion by 2029 (Juniper Research 2024).

Critically, the composition of fraud is shifting. Online identity fraud now represents over 70% of all identity fraud occurrences, and in 2024, 49% of companies reported incidents involving deepfakes, with video-based deepfakes increasing by 20% (Veridas 2024; WEF 2025). This is direct evidence that c(k) is falling for AI-generated identities: deepfake technology reduces the cost of creating convincing false identities, and the fraud statistics measure the consequences of that cost reduction.

### 6.3 Economic Theory of Identity Costs

The concept of a "critical value" determining the cost-effectiveness of sybil attacks -- an attack is worthwhile only when the ratio of the attack's value to identity costs exceeds this threshold -- has been formalized in the distributed systems literature but has direct economic content. It is equivalent to the standard cost-benefit condition for entry in industrial organization: entry occurs when expected rents exceed entry costs. The parent paper's c(k) function should be understood not as a novel construct but as an application of the standard entry cost framework to the identity domain.

Proposed defenses in the economics-adjacent literature include recurring fees as sybil deterrents (analogous to maintenance costs in patent law), reputation staking (analogous to performance bonds in contract law), and social graph verification (analogous to referral networks in labor economics). Each implies a different functional form for c(k) and different distributional consequences.

---

## 7. Synthesis and Gaps

### 7.1 What the Grey Literature Adds

The grey literature fills five gaps in the formal academic literature:

**Enforcement reality.** The algorithmic collusion debate in the academic literature is heavily theoretical (Calvano et al., Assad et al.). The grey literature reveals that actual enforcement is targeting a narrower and more tractable problem -- explicit information sharing through algorithmic intermediaries -- while the harder problem of tacit algorithmic collusion remains unaddressed by policy.

**Empirical weight.** The post-Noy-Zhang empirical literature (Brynjolfsson et al. 2025; Yale Budget Lab 2025; Danish administrative data) substantially refines the picture: microeconomic productivity gains are real but modest, distributional effects favor low-skilled workers within firms, and macroeconomic displacement effects are not yet detectable. The parent paper should update its priors accordingly.

**Agent participation at scale.** Polymarket provides the first real-world evidence that AI agents participate in markets at scale, extract rents from human participants, and transform market microstructure. This is no longer a theoretical possibility but an empirical fact.

**Policy frameworks.** Smith's "human reservation" concept, Cowen's Baumol disease argument, and Brookings' adaptive capacity analysis provide three distinct policy frameworks for addressing AI-driven labor disruption that the formal literature has not yet engaged.

**Identity cost empirics.** The fraud economics literature provides real-dollar estimates for identity costs and their trajectory, grounding the parent paper's c(k) function in observable data.

### 7.2 What Remains Missing

Five significant gaps remain even after incorporating the grey literature:

**Tacit algorithmic collusion enforcement.** No regulator has articulated a viable enforcement strategy for the case where independent AI agents converge on supra-competitive equilibria without sharing data. This is the central policy question, and it is unanswered.

**Agent-vs-tool labor effects.** Virtually all empirical labor studies measure the effects of AI *tools* (ChatGPT, Copilot, conversational assistants), not autonomous AI *agents* that plan, execute, and iterate independently. The transition from tool to agent could produce qualitatively different labor effects -- including genuine displacement rather than task reallocation -- but there is no empirical evidence yet.

**Resource competition.** Smith's observation that AI systems and humans will compete for physical resources (land, energy, water) is analytically important but has no formal modeling or empirical measurement. The parent paper could contribute here.

**Cross-market agent effects.** Polymarket data shows agent behavior within one market. The effects of agents operating *across* markets simultaneously -- exploiting cross-market arbitrage, conducting coordinated strategies across equities, prediction markets, and DeFi -- are unmeasured.

**Sybil cost trajectories.** The fraud literature documents that identity costs are falling, but no one has estimated the functional form of c(k) empirically or projected its trajectory as AI capabilities improve. This is a tractable empirical project that the parent paper identifies but does not execute.

### 7.3 Recommendations for the Parent Paper

Based on this survey, the parent paper should:

1. **Update the labor market treatment** to reflect the Brynjolfsson et al. (2025) compression finding and the absence of macroeconomic displacement effects through 2025.
2. **Cite the RealPage settlement** as the leading example of algorithmic collusion enforcement, while noting its narrowness relative to the tacit collusion problem the paper models.
3. **Incorporate the Polymarket evidence** as real-world validation of the paper's AI agent market participation analysis.
4. **Engage Jones (2026) on weak links** as a growth-theoretic framework compatible with the paper's mechanism-level analysis.
5. **Ground c(k) in fraud economics data** to provide empirical calibration for what is currently a purely theoretical construct.
6. **Acknowledge the tool-vs-agent gap** in the empirical literature, positioning the parent paper's focus on agents as forward-looking relative to the current evidence base.

---

## References

Acemoglu, D. (2024). "The Simple Macroeconomics of AI." NBER Working Paper 32487.

Brennan, K., Kak, A., and Myers West, S. (2025). "Artificial Power: 2025 Landscape Report." AI Now Institute.

Brookings Institution (2025a). "Generative AI, the American Worker, and the Future of Work."

Brookings Institution (2025b). "Measuring US Workers' Capacity to Adapt to AI-Driven Job Displacement."

Brynjolfsson, E., Li, D., and Raymond, L. (2025). "Generative AI at Work." *Quarterly Journal of Economics* 140(2): 889-942. (Originally NBER Working Paper 31161.)

Calvano, E., Calzolari, G., Denicolo, V., and Pastorello, S. (2020). "Artificial Intelligence, Algorithmic Pricing, and Collusion." *American Economic Review* 110(10): 3267-3297.

Clancy, M. (2024-2025). "What's New Under the Sun." Substack newsletter. https://mattsclancy.substack.com/

CoinDesk (2026). "AI Agents Are Quietly Rewriting Prediction Market Trading." March 15.

Cowen, T. (2025a). "Why I Think AI Take-off is Relatively Slow." Marginal Revolution, February.

Cowen, T. (2025b). "AI is Everywhere but in the Productivity Statistics." Marginal Revolution, December.

Cowen, T. (2025c). "The Consumer Surplus from AI." Marginal Revolution, August.

DLA Piper (2024). "The Preventing Algorithmic Collusion Act: A Swing and a Miss?"

DOJ (2024). "Justice Department Files Suit Against RealPage." Press release, August.

DOJ (2025). "Justice Department Requires RealPage to End the Sharing of Competitively Sensitive Information." Press release, November.

EU AI Act Implementation Timeline (2025). https://www.euaiact.com/implementation-timeline

Finance Magnates (2025). "Prediction Markets Are Turning Into a Bot Playground."

Global Competition Review (2025). "EU Competition Authorities Zero in on Antitrust Risks of Algorithmic Pricing."

Jones, C. I. (2026). "AI and Our Economic Future." Stanford GSB / NBER.

Juniper Research (2024). "Digital ID Verification Spend to Exceed $26 Billion Globally by 2029."

Korinek, A. (2025). "AI Agents for Economic Research." NBER Working Paper 34202.

Morgan Lewis (2025). "AI and Algorithmic Pricing: 2025 Antitrust Outlook and Compliance Considerations."

National Law Review (2025). "AI and Antitrust 2025: DOJ, FTC Scrutiny on Pricing & Algorithms."

Noy, S. and Zhang, W. (2023). "Experimental Evidence on the Productivity Effects of Generative Artificial Intelligence." *Science* 381(6654): 187-192.

Regula Forensics (2025). "Identity Fraud by Numbers: Trends, Insights & Threats."

Smith, N. (2024-2026). "Noahpinion." Substack newsletter. https://www.noahpinion.blog/

Stanford Digital Economy Lab (2025). "AI and Labor Markets: What We Know and Don't Know."

Veridas (2024). "Identity Fraud Report 2024."

World Economic Forum (2025). "AI-Driven Cybercrime Is Growing, Here's How to Stop It."

Yale Budget Lab (2025). "Evaluating the Impact of AI on the Labor Market: Current State of Affairs."

Yotzov, I., Barrero, J. M., et al. (2025). "Firm Data on AI." NBER Working Paper 34836.
