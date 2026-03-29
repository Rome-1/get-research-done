# Crypto/DeFi Sybil Resistance in Practice: A Literature Survey

**Status:** First draft
**Date:** 2026-03-29
**Author:** Alice (GetResearch)
**Motivation:** Literature gap — practical sybil resistance experience from crypto/DeFi not captured in formal literature map
**Related:** `sybil-resistance-mechanisms.md`, `assumption-taxonomy.md` (identity cost function)

---

## Introduction

The companion deep dive (`sybil-resistance-mechanisms.md`) taxonomizes sybil resistance approaches and evaluates each against the identity cost function c(k) from the assumption taxonomy. That document is necessarily theoretical: it analyzes mechanism categories rather than deployed systems. This survey fills the empirical complement. The decentralized finance and governance ecosystem has, over roughly 2018--2025, conducted what amounts to a large-scale natural experiment in sybil resistance under adversarial conditions. Hundreds of millions of dollars in quadratic funding, token airdrops, and governance power have been distributed through mechanisms whose security rests on the assumption that participants represent unique humans. Attackers have repeatedly tested that assumption, and defenders have iterated in response.

This literature review synthesizes the empirical record. The organizing question is: *what do we actually know about the cost, prevalence, and detectability of sybil attacks in practice?* The answer turns out to be richer than the formal literature suggests, because the crypto ecosystem generates unusually detailed public data --- on-chain transaction records, open-source detection algorithms, published post-round analyses --- that permit quantitative assessment of sybil dynamics in ways that traditional identity fraud research cannot.

We proceed in seven sections. Section 1 covers the most extensive empirical record: Gitcoin's quadratic funding rounds and the evolution of its sybil defense. Section 2 surveys proof-of-personhood systems with adoption data. Section 3 examines on-chain detection methods. Section 4 assembles what is known about the actual cost of synthetic identities. Section 5 reviews formal analyses of sybil attacks with quantified cost--return structures. Section 6 draws lessons for mechanism design in agent-populated economies. Section 7 synthesizes.

---

## 1. Gitcoin Grants and Quadratic Funding

### 1.1 Background: Quadratic Funding as a Sybil Testbed

Quadratic funding (QF), proposed by Buterin, Hitzig, and Weyl (2019), allocates matching funds to public goods in proportion to the square of the sum of square roots of individual contributions. The mechanism is provably optimal under the "standard model" --- but that model assumes each contributor is a unique individual. The square-root transformation means that a fixed budget split across many small contributions generates more matching than the same budget from one large contribution. This creates a direct economic incentive for sybil attacks: splitting a single contribution across k wallets amplifies matching by a factor proportional to sqrt(k).

Gitcoin Grants has been the primary real-world deployment of QF, distributing over $60 million across more than 20 rounds since 2019. Because all contributions are on-chain, and because Gitcoin has published detailed post-round fraud analyses (in partnership with BlockScience and the Fraud Detection & Defense workstream), this constitutes the richest empirical dataset on sybil attacks against a deployed mechanism.

### 1.2 The Fraud Tax: Quantified Losses Across Rounds

BlockScience conducted systematic post-round evaluations of Gitcoin Grants Rounds 9 through 12, introducing the concept of the "fraud tax" --- the portion of matching funds diverted to sybil-controlled contributions.

**GR9 (2021).** The fraud tax was $33,014, approximately 6.6% of the $500,000 matching pool. Machine learning algorithms flagged 26,911 contributions (out of ~168,000 total) from 1,995 contributors (out of ~11,500) as presenting sybil or fraud patterns (BlockScience, 2021).

**GR10 (2021).** The fraud tax fell to $14,350, or 2.1% of a $700,000 matching pool --- a reduction of more than 50% from GR9. A lower-aggressiveness model flagged 1,377 sybil accounts. The improvement was attributed primarily to the introduction of trust bonus weighting and more sophisticated ML classifiers (BlockScience, 2021).

**GR11 (2021).** The fraud tax dropped further to $5,787, again more than halving. The combined FDD process (human evaluations, ML predictions, and subject-matter-expert heuristic flags) flagged 853 contributor accounts out of 15,986 total (5.3%) as potential sybils. Using human evaluations as calibrating surveys, BlockScience estimated the true sybil incidence at approximately 6.4%, with a confidence range of 3.6--9.3%. This implies the detection system was catching roughly 83% of sybil accounts, with a lower bound of 57% (BlockScience, 2022).

**GR12 (2022).** BlockScience introduced the Flagging Efficiency Estimate, a metric assessing the percentage efficiency of the overall anti-sybil operations process. The round evaluated data from nearly 29,000 platform users with further refinements to the detection pipeline (BlockScience, 2022).

The trajectory from GR9 to GR11 is striking: the fraud tax declined from 6.6% to approximately 0.6% of the matching pool over three rounds, while the matching pool itself grew. This demonstrates that iterative, data-driven sybil defense can substantially reduce losses even against motivated adversaries --- but note that the true sybil rate likely remained in the 4--9% range; what improved was detection, not deterrence.

### 1.3 Connection-Oriented Cluster Matching (COCM)

Beginning with GG20 (April 2024), Gitcoin deployed Connection-Oriented Cluster Matching (COCM), a fundamental redesign of the matching algorithm. COCM analyzes the social connections between donors and reduces matching for projects whose support comes from tightly coordinated clusters, while boosting matching for projects with support from socially diverse contributor bases (Gitcoin, 2024).

The intuition is mechanism-theoretic: rather than attempting to identify and exclude sybils (a cat-and-mouse classification problem), COCM changes the payoff structure so that sybil clusters receive diminished returns even if they evade detection. Based on comparative analysis of past rounds, Gitcoin reports approximately 50% improvement in funding allocations relative to traditional QF --- measured by reduction in the matching share captured by detected sybil clusters.

COCM was deployed alongside Passport's model-based detection across GG20 (April 2024), GG21 (August 2024), GG22, and GG23. The Human Passport system (formerly Gitcoin Passport) uses machine learning models trained on known sybil and human address behavior across Ethereum L1 and multiple L2 chains.

### 1.4 Implications for Mechanism Design

The Gitcoin experience yields several generalizable lessons. First, quadratic funding is acutely sybil-sensitive by construction: the square-root transformation that makes QF welfare-optimal also makes it maximally vulnerable to identity splitting. Second, purely ex-post detection (flagging and removing sybils after the round) is necessary but insufficient; the estimated 17--43% miss rate means substantial leakage persists. Third, the shift from detection-based to mechanism-based defense (COCM) represents a more robust approach --- altering incentives rather than playing classification games. This is precisely the direction the assumption taxonomy recommends.

The key open question is how COCM performs against AI-operated sybil clusters. Human sybil farmers exhibit behavioral signatures (temporal clustering, gas funding patterns) that ML classifiers exploit. AI agents that vary timing, routing, and interaction patterns may be substantially harder to cluster. COCM's advantage is that it does not depend on behavioral detection --- it directly penalizes coordination regardless of how well individual identities are disguised.

---

## 2. Proof-of-Personhood Systems

### 2.1 Worldcoin / World Network

Worldcoin (rebranded to "World" in 2024) represents the highest-capitalization attempt at proof-of-personhood. The system uses custom iris-scanning hardware (the Orb) to generate a biometric hash, with zero-knowledge proofs enabling verification without revealing raw biometric data.

**Adoption data.** The network has verified over 16 million unique humans as of early 2025, with more than 1,500 Orbs operating across 23 countries (World, 2025). Regional concentrations include Latin America (with approximately one in three residents of Buenos Aires verified), Japan (over 100,000 in 2024), and Singapore (over 100,000 by early 2025). South Korea passed 10,000 verifications in three weeks during April 2025 (Biometric Update, 2025).

World projects deploying 7,500 Orbs across the United States alone by end of 2025, with a stated goal of 50 million verifications by year-end --- though the current trajectory (roughly 12 million over two years since launch) suggests this target is ambitious. A survey of 21,000 World ID holders in Spain found 82% agreement that such technologies are important for distinguishing humans from bots online (World, 2024).

**Limitations.** The biometric approach is the most resistant to AI-driven sybil attacks among existing systems --- AI agents do not have irises. However, the system faces non-technical barriers: regulatory friction (multiple countries have suspended operations over biometric data concerns), hardware distribution bottlenecks, and the centralization risk inherent in a single organization controlling the Orb supply chain and verification pipeline. The system also does not prevent a human from selling or renting their verified identity to a principal operating AI agents, which is the attack vector the assumption taxonomy identifies as most relevant.

### 2.2 Idena and the Puppeteer Problem

Idena implements proof-of-personhood through globally synchronized CAPTCHA ceremonies: participants must solve six AI-resistant FLIP puzzles within two minutes during a scheduled validation session. The synchrony constraint --- all participants solve simultaneously --- prevents a single operator from completing ceremonies for multiple identities sequentially. New participants must complete four consecutive ceremonies to achieve "human" status.

Ohlhaver, Nikulin, and Berman (2024), in "Compressed to 0: The Silent Strings of Proof of Personhood" (Stanford Journal of Blockchain Law & Policy), provide the most detailed empirical analysis of a proof-of-personhood system's failure mode. Studying Idena from its launch in August 2019 through a crisis in May 2022, they document the emergence of "puppeteer pools" --- coordinated groups where operators paid participants to prove their uniqueness in exchange for access to private keys and account control.

The quantitative findings are sobering: **by May 2022, 23 entities constituting less than 0.6% of the network's distinct entities controlled at least approximately 40% of accounts and the distribution of almost half (~48%) of network rewards.** The system successfully verified humans but failed to prevent verified humans from voluntarily subordinating their identities to centralized operators. This is precisely the "identity rental" attack that the assumption taxonomy predicts will intensify with AI agents: the sybil cost c(k) remains high for creating new identities (each requires a distinct human) but the effective cost drops dramatically when identity rental markets emerge.

The Idena case demonstrates a critical distinction: **proof-of-personhood ensures one-person-one-identity, but does not ensure one-person-one-principal.** When the economic incentive to rent out one's verified identity exceeds the cost of participation, pools form. This is an instance of the broader principal-agent separation that the assumption taxonomy identifies as endemic to AI-mediated mechanisms.

### 2.3 BrightID and Social Graph Verification

BrightID verifies humanity by analyzing social connections. Users attend "connection parties" (in-person or video) and form links within a social graph. Graph analysis algorithms identify sybil clusters by detecting sparse connections between the sybil subgraph and the legitimate network. Real humans tend to have organic, diverse connections; sybil identities cluster in unnatural patterns.

The system assigns identity confidence based on node position relative to trusted "seed" nodes, with applications able to set their own seed nodes and evaluation criteria (Frontiers in Blockchain, 2020). This "intersectional identity" paradigm allows customized trust thresholds, but the approach faces a bootstrap problem: at early stages, the network is small enough that sybil clusters can represent a significant fraction of the graph, and graph-based detection algorithms struggle with sophisticated small-scale sybil rings that blend into the social structure.

BrightID's limitations are well-documented in the academic literature. Siddarth, Ivliev, Siri, and de Filippi (2020) note that the system is "limited to a small seed network" with "no established paths for individuals or groups who are completely independent from the existing network to self-authenticate." The Catch-22 is fundamental: the social graph needs to be large to detect sybils reliably, but it cannot grow large without admitting unverified users who may be sybils.

### 2.4 Comparative Assessment

| System | Mechanism | Verified Users | Sybil Model | AI-Agent Resistance |
|--------|-----------|---------------|-------------|-------------------|
| World (Worldcoin) | Iris biometrics | ~16M | Hardware-bound, biometric | High (requires physical human) but vulnerable to identity rental |
| Idena | Synchronous CAPTCHA | ~15K active | Time-bound, cognitive | Medium (AI solving of FLIPs improving) |
| BrightID | Social graph | ~60K | Graph-analytic | Low (AI can simulate social connections) |
| Gitcoin Passport | Multi-signal scoring | ~1M scored | ML classification | Medium (signals can be farmed) |

The common failure mode across all systems is identity rental: a verified human sells or rents access to their identity. No deployed proof-of-personhood system prevents this, and the economics of identity rental become more favorable as AI agents reduce the marginal cost of operating rented identities.

---

## 3. On-Chain Sybil Detection Methods

### 3.1 Graph-Based Clustering

The dominant approach to on-chain sybil detection applies community detection algorithms to transaction graphs. The core insight is that sybil wallets controlled by a single operator tend to exhibit structural patterns in their funding and transaction relationships.

**Louvain community detection.** Multiple airdrop sybil analyses have used the Louvain algorithm to identify wallet clusters. Wormhole applied Louvain to a similarity matrix of cross-chain transactions, identifying sybil clusters based on repetitive actions performed at similar intervals across wallets (Wormhole, 2024). The algorithm detects communities by optimizing modularity --- wallets that transact more densely with each other than with the broader network are grouped together.

**Trusta Labs' two-phase framework.** Trusta's approach separates structural and behavioral analysis. Phase 1 applies community detection (Louvain and K-Core decomposition) to asset transfer graphs, identifying candidate sybil communities. Phase 2 computes user profiles for each address --- transaction frequency, timing patterns, protocol interactions --- and uses K-means clustering to refine communities by screening out addresses whose behavior is dissimilar to the cluster, reducing false positives (Trusta Labs, 2024).

**Subgraph-based feature propagation.** A 2025 study analyzing 193,701 addresses (including 23,240 known sybil addresses) spanning January 2023 to May 2024 proposed subgraph-based machine learning that propagates features through local transaction subgraphs, achieving improved detection over node-level features alone (arXiv:2505.09313).

### 3.2 Behavioral Signatures

Beyond graph structure, temporal and behavioral features provide strong signals:

- **Temporal clustering.** Sybil addresses are typically created shortly before airdrops, with minimal intervals between receiving gas, conducting first transactions, and participating in qualifying activities. Legitimate users create addresses for long-term use.
- **Star topology.** A central controlling address (hub) distributes assets to multiple controlled addresses (spokes), manifesting as abnormally high out-degree for the hub and limited transaction history beyond hub interactions for the spokes.
- **Daisy chains.** Assets pass sequentially through a series of addresses, each performing qualifying actions before forwarding funds. The Hop Protocol sybil analysis identified this pattern extensively, flagging networks where a root address funded first-degree connections that in turn funded second-degree connections used for farming (Hop Protocol, 2022).

### 3.3 Case Studies in Airdrop Sybil Filtering

**LayerZero (2024).** LayerZero conducted the most aggressive public sybil filtering of any major airdrop. Of approximately six million wallets that had used the protocol, roughly one million were identified as involved in sybil farming. The project removed 803,273 wallets (59% of those initially eligible) before distributing tokens. Notably, LayerZero introduced a self-reporting mechanism: approximately 100,000 wallets voluntarily self-reported sybil activity in exchange for receiving 15% of their expected allocation rather than zero. Nearly 10 million tokens that would have gone to sybil attackers were redistributed to legitimate users. The final distribution reached approximately 1.28 million wallets (LayerZero, 2024).

**Optimism (2022).** Optimism removed 17,000 sybil addresses from its OP token airdrop, recovering over 14 million OP tokens (valued at approximately $18.6 million at the time). Detection relied on a combination of community-submitted reports (~2,100 flagged accounts), suspicious L1 activity flags (~9,000 accounts), and suspicious L2 activity flags (~11,000 accounts). Recovered tokens were redistributed proportionally to remaining Airdrop #1 recipients (Optimism Foundation, 2022).

**Hop Protocol (2022).** Hop's detection methodology computed a suspiciousness score for each address based on transactions with other eligible addresses, then calculated a network score from the average of individual scores. Only wallets in groups with an average score exceeding 90% were flagged. The methodology indexed first-transaction metadata across all chains, sorting timestamps and computing deltas between consecutive transactions to identify automated batching patterns. Addresses with more than 30 transactions or more than 10,000 ERC-20 transfers were considered legitimate (Hop Protocol, 2022).

### 3.4 Detection Limits

All on-chain detection methods share a fundamental limitation: they detect coordination, not identity duplication per se. A sophisticated attacker who uses independent funding sources, varied timing, and diverse behavioral patterns for each sybil wallet can evade graph-based and behavioral detection. The arms race is asymmetric: defenders must catch all sybils to prevent mechanism manipulation, while attackers need only evade detection with a fraction of their wallets to profit.

The estimated false negative rates from Gitcoin's analysis (17--43% of sybils undetected) and the sheer scale of LayerZero's exclusions (800K+ wallets) suggest that current detection methods capture a majority but not the entirety of sybil activity. This residual leakage is sufficient to distort mechanism outcomes.

---

## 4. Identity Cost Empirics

### 4.1 Dark Web Identity Markets

The cost of the raw materials for synthetic identities has been extensively documented in cybersecurity research:

- **Social Security Numbers:** $1--6 on dark web markets (DeepStrike, 2025).
- **Full PII sets** (name, SSN, address, date of birth): $100--500 depending on the issuing country and associated credit history (Equifax, 2024).
- **KYC-verified cryptocurrency accounts:** Prices vary significantly by exchange and jurisdiction, ranging from $50 for low-tier exchanges to $500+ for exchanges with stringent verification.
- **Verified social media accounts** (used as identity signals by systems like Gitcoin Passport): $1--15 for aged accounts on bulk markets.

These prices establish a floor for the identity cost function c(k) in crypto contexts. For a Gitcoin Passport-style system that requires multiple identity signals (social media accounts, on-chain history, ENS name), the cost of a minimally qualifying sybil identity is on the order of $20--100. For a system requiring KYC-level verification, costs rise to $100--500 per identity. For biometric systems like Worldcoin, the cost is effectively the willingness-to-accept of a human identity provider --- which varies enormously by jurisdiction and economic context.

### 4.2 Airdrop Farming Economics

The expected return to sybil identity creation can be estimated from airdrop data. The Optimism airdrop allocated tokens worth approximately $1,094 per sybil address at the time of distribution ($18.6M / 17,000 addresses). Against an identity creation cost of $20--100, this implies returns of 10x--50x on sybil investment, explaining the prevalence of farming.

LayerZero's data suggests similar economics. With roughly one million sybil wallets attempting to farm an airdrop worth $120M+ in total, even conservative per-wallet expectations of $100--200 would yield positive returns against wallet creation costs of $5--20 (gas fees plus minimal activity).

The implication for mechanism design is clear: **identity costs in crypto are currently one to two orders of magnitude below the per-identity returns available from sybil-sensitive mechanisms.** This is the fundamental parameter that any sybil resistance system must shift. Either the cost of each identity must rise (proof-of-personhood, stake requirements) or the per-identity return must fall (COCM, conviction voting).

### 4.3 Synthetic Identity Fraud at Scale

Broader financial system data provides context. Synthetic identity fraud --- creating new identities from combinations of real and fabricated data --- costs U.S. financial institutions an estimated $20--40 billion annually, with losses growing approximately 50% from 2022 to 2023 (Equifax, 2024; Mastercard, 2024). The scale of this market demonstrates that identity fabrication is a mature, industrialized activity. The tools and supply chains developed for financial fraud are directly transferable to crypto sybil attacks, lowering the marginal cost of crypto-specific identity creation.

---

## 5. Formal Analysis of Sybil Attacks

### 5.1 Quantifying Sybil Resistance

The theoretical literature on sybil attack costs is anchored by several key results. Douceur (2002) established the foundational impossibility: without a trusted central authority, sybil attacks cannot be prevented in fully open networks. Subsequent work has focused on quantifying the cost of attacks under various mechanism designs.

The critical parameter is the ratio of attack returns to identity costs. Formal analysis demonstrates that a critical value exists: attacks become profitable when the ratio of the attacker's goal value to the per-identity cost exceeds this threshold. Mechanisms can be ranked by the size of this critical ratio --- higher ratios mean more resistance (Springer, 2008).

### 5.2 The Sybil Attack Vulnerability Trilemma

Platt, Platt, and McBurney (2024) formalize three properties that blockchain systems pursue: (1) permissionlessness --- anyone can participate without approval; (2) sybil attack resistance --- creating multiple identities does not yield disproportionate influence; and (3) freeness --- participation does not require resource expenditure. The central result is an impossibility theorem: **no system can simultaneously achieve all three properties.** A system that is free and permissionless must be sybil-vulnerable (International Journal of Parallel, Emergent and Distributed Systems, 2024).

This trilemma has direct implications for mechanism design in AI-agent economies. The assumption taxonomy identifies identity cost collapse as the defining feature of AI agents. The trilemma tells us that resisting this collapse requires either restricting access (abandoning permissionlessness) or imposing costs (abandoning freeness). There is no mechanism-design escape from this constraint.

### 5.3 Attacks on Quadratic Funding

BlockScience's analysis of QF attack vectors (2022) identifies two primary threats: sybil attacks (splitting contributions across fake accounts) and collusion (real users coordinating to amplify matching). The distinction matters because sybil attacks violate the identity assumption while collusion violates the independence assumption --- and the defenses differ.

For sybil attacks on QF, the attacker's return scales as sqrt(k) for k fake identities each contributing 1/k of a fixed budget. The marginal return to an additional sybil identity is positive but decreasing --- implying that even partial sybil resistance (making identities expensive) substantially reduces attack returns, even if it does not eliminate them entirely.

For collusion, BlockScience notes that it "turns a governance system into a cooperative game, which is inevitable and much more complicated" than sybil attacks. In Gitcoin's experience, approximately 35 collusion flags were reported in Round 8 --- a small number suggesting either low prevalence or (more likely) low detectability. Empirical observations from DeFi hackathons have documented "benevolent collusion" where projects promised future airdrops to donor addresses, effectively creating side payments that compromise QF's welfare optimality (BlockScience, 2022).

### 5.4 Sybil Attacks on Proof-of-Stake

The interaction between sybil resistance and consensus mechanisms has been analyzed formally. Sybil attacks on identity-augmented proof-of-stake systems --- where validator weight depends partly on identity and partly on stake --- introduce attack vectors not present in pure stake-weighted systems. The key insight is that identity augmentation, while intended to reduce plutocratic concentration, creates a new attack surface: acquiring identities to dilute the identity-weighted component of consensus (Computer Networks, 2021).

---

## 6. Lessons for Mechanism Design

### 6.1 Detection Is Necessary but Insufficient

The Gitcoin experience demonstrates that iterative ML-based sybil detection can reduce fraud taxes by an order of magnitude (from 6.6% to ~0.6% of the matching pool). However, the estimated true positive rate of ~83% means that roughly one in six sybil accounts evades detection. This residual leakage is large enough to matter: in a $1M matching pool, a 5% sybil rate with 83% detection still allows approximately $8,500 in fraudulent matching.

The lesson is that detection-based approaches face a ceiling. Each incremental improvement in detection triggers adaptive responses from attackers, and the asymmetry between attacker and defender (the attacker knows the detection criteria; the defender does not know the attacker's next strategy) ensures persistent leakage. This is the standard argument for mechanism-based rather than detection-based security.

### 6.2 Mechanism-Based Defenses Are More Robust

COCM represents a shift from "find and remove sybils" to "make sybils unprofitable." By reducing matching for coordinated clusters regardless of whether individual wallets are classified as sybils, COCM changes the attacker's optimization problem. The attacker must not only create indistinguishable identities but also ensure those identities are socially distant from each other in the connection graph --- a much harder constraint.

Conviction voting (Commons Stack, 1Hive) applies similar logic through the time dimension: influence accumulates through sustained stake-weighted support, making it expensive to maintain multiple influential identities simultaneously. Stake-based approaches (Ethereum's 32-ETH validator minimum) impose direct capital costs.

The common principle is: **mechanisms should be designed so that the per-identity cost of meaningful participation exceeds the per-identity return from sybil duplication.** When c(k) > R/k for all k > 1 (where R is the total return from sybil activity), sybil attacks are unprofitable regardless of detection capability.

### 6.3 Identity Rental Is the Binding Constraint

The Idena puppeteer phenomenon generalizes: any system that successfully binds identity to unique humans will face a secondary market in identity rental. When a verified human can earn $X by renting their identity to an operator, and the operator can earn $Y > X by using that rented identity in a mechanism, the rental market clears. Proof-of-personhood pushes the sybil cost from near-zero (creating fake identities) to the cost of renting real identities from real humans --- but this cost can be surprisingly low in developing economies.

This is the central challenge for mechanism design in agent-populated economies. The assumption taxonomy identifies identity cost collapse as the fundamental problem; the empirical record from crypto demonstrates that even when identity creation costs are high (biometric verification), identity *rental* costs can be low enough to enable profitable sybil attacks.

### 6.4 The Trilemma Constrains Design Space

The Platt, Platt, and McBurney (2024) trilemma implies that any sybil-resistant mechanism must sacrifice either permissionlessness or freeness. In practice, most successful approaches sacrifice freeness: staking requirements, gas costs, Passport score thresholds, and biometric enrollment all impose costs on participation. The design question is how to impose costs that differentially burden sybil identities (which must pay k times) relative to legitimate participants (who pay once).

This framing connects directly to the identity cost function c(k). A well-designed mechanism ensures that c(k) is superlinear in k --- each additional identity costs more than the last --- while the per-identity return R(k)/k is sublinear in k. The intersection of these curves defines the equilibrium sybil count, and good mechanism design pushes that equilibrium toward k = 1.

---

## 7. Synthesis

The empirical record from crypto and DeFi yields five principal findings for the economics of agents:

**First, sybil attacks are endemic and profitable.** Every major token distribution and funding mechanism has been targeted. Quantified data from Optimism ($18.6M in sybil-allocated tokens), LayerZero (~1M sybil wallets from 6M total users), and Gitcoin (4--9% sybil rate across rounds) establish that sybil activity is not a marginal phenomenon but a structural feature of any mechanism where identity duplication is profitable.

**Second, detection technology has improved substantially but faces inherent limits.** Gitcoin's fraud tax declined from 6.6% to ~0.6% of matching pools across rounds, and LayerZero successfully filtered 59% of initially eligible wallets. But estimated detection rates of 57--83% (Gitcoin) imply significant residual leakage. Graph-based and behavioral detection methods are effective against unsophisticated sybil farmers but face declining returns against adaptive adversaries --- and AI agents will be far more adaptive than human farmers.

**Third, mechanism-based defenses outperform detection-based defenses.** COCM's approximately 50% improvement in funding allocation quality, and the theoretical properties of conviction voting and stake-based mechanisms, demonstrate that changing incentive structures is more robust than improving classification accuracy. The design principle is to make the return to sybil duplication sublinear while keeping the cost superlinear.

**Fourth, identity rental is the frontier challenge.** Idena's puppeteer pools (0.6% of entities controlling 40% of accounts by May 2022) demonstrate that proof-of-personhood solves identity creation but not identity rental. Worldcoin's 16 million verifications establish the feasibility of biometric proof-of-personhood at scale, but the system cannot prevent verified humans from renting their credentials to operators running AI agents. The binding constraint is not "can we verify humans?" but "can we ensure verified humans operate independently?"

**Fifth, the sybil attack vulnerability trilemma constrains the design space.** No permissionless, free system can be sybil-resistant (Platt, Platt, and McBurney, 2024). Practical sybil resistance requires imposing costs, and the art of mechanism design is ensuring those costs fall disproportionately on sybil identities. The identity cost function c(k) must be superlinear, and the empirical evidence suggests that achieving superlinearity requires combining multiple approaches: biometric or social verification (high fixed cost per identity), stake requirements (capital cost scaling with k), reputation accumulation (time cost scaling with k), and mechanism-level defenses like COCM (reduced returns with k).

For the economics of agents specifically, the crypto record is simultaneously encouraging and alarming. Encouraging because it demonstrates that practical sybil resistance is achievable --- the tools exist and have been tested under adversarial conditions. Alarming because the current equilibrium was reached against human sybil farmers operating manually or with simple scripts. AI agents that can operate thousands of identities with human-like behavioral diversity represent a qualitative escalation that existing defenses have not yet confronted. The gap between current sybil resistance and AI-agent-grade sybil resistance is, we submit, one of the most important open problems in mechanism design.

---

## References

- BlockScience. (2021). "Evaluating the Anti-Fraud Results for Gitcoin Round 10." BlockScience Blog.
- BlockScience. (2022a). "Gitcoin Grants Round 11 Anti-Fraud Evaluation & Results." BlockScience Blog.
- BlockScience. (2022b). "Gitcoin Grants Round 12 Evaluation & Results." BlockScience Blog.
- BlockScience. (2022c). "How to Attack and Defend Quadratic Funding." Gitcoin Blog / BlockScience.
- Buterin, V., Hitzig, Z., and Weyl, E. G. (2019). "A Flexible Design for Funding Public Goods." *Management Science*, 65(11), 5171--5187.
- DeepStrike. (2025). "Dark Web Data Pricing 2025: Real Costs of Stolen Data." DeepStrike Research.
- Douceur, J. R. (2002). "The Sybil Attack." In *Proceedings of the 1st International Workshop on Peer-to-Peer Systems (IPTPS)*.
- Equifax. (2024). "Synthetic Identity Fraud: The Unseen Threat and Its Cost to Businesses." Equifax Business Insights.
- Gitcoin. (2024). "Leveling the Field: How Connection-Oriented Cluster Matching Strengthens Quadratic Funding." Gitcoin Blog.
- Hop Protocol. (2022). "Sybil Attacker Reports." GitHub: hop-protocol/hop-airdrop.
- Human Tech. (2024). "Human Passport x Gitcoin Grants: Defending GG23 with Model-Based Sybil Detection." Human Tech Blog.
- LayerZero. (2024). "LayerZero Airdrop Sybil Detection Results." Various sources including CryptoBriefing, The Defiant.
- Mastercard. (2024). "Understanding Synthetic Identity Theft and Fraud Risks." Mastercard Insights.
- Ohlhaver, P., Nikulin, M., and Berman, P. (2024). "Compressed to 0: The Silent Strings of Proof of Personhood." *Stanford Journal of Blockchain Law & Policy*.
- Optimism Foundation. (2022). "Airdrop 1 Sybil Filtering." Optimism Docs / The Defiant.
- Platt, M., Platt, M., and McBurney, P. (2024). "Sybil Attack Vulnerability Trilemma." *International Journal of Parallel, Emergent and Distributed Systems*, 39(5).
- Siddarth, D., Ivliev, S., Siri, S., and de Filippi, P. (2020). "Who Watches the Watchmen? A Review of Subjective Approaches for Sybil-Resistance in Proof of Personhood Protocols." *Frontiers in Blockchain*, 3, 590171.
- Trusta Labs. (2024). "AI and Machine Learning Framework for Robust Sybil Resistance in Airdrops." GitHub / Medium.
- World. (2025). "Proof of Human Is Essential, and It's Going Mainstream in 2025." World Blog.
- Wormhole. (2024). "From Eligibility to Sybil Detection: A Deep-Dive into Wormhole's Multichain Airdrop." Wormhole Blog.
- Zhang, R., et al. (2025). "Detecting Sybil Addresses in Blockchain Airdrops: A Subgraph-based Feature Propagation and Fusion Approach." arXiv:2505.09313.
