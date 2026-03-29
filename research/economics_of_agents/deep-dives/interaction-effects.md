# Interaction Effects: How Assumption Violations Compound

**Status:** First draft
**Date:** 2026-03-29
**Author:** Alice (GetResearch)
**Depends on:** [assumption-taxonomy.md](../assumption-taxonomy.md)

---

## Why Interactions Matter More Than Individual Violations

The assumption taxonomy treats each violation as an independent axis of failure. This is pedagogically useful but analytically incomplete. The actual danger of AI agents in economic systems comes not from any single violated assumption but from the multiplicative interactions between violations. A fast agent is a problem. A sybil agent is a problem. A fast sybil agent is a *categorically different* problem — one that cannot be understood by analyzing speed and sybil resistance separately and summing the results.

The reason is structural. Economic defense mechanisms are generally designed to counter one type of deviation at a time. Auction theory handles strategic bidding but assumes unique bidders. Identity systems handle sybil resistance but assume human-speed interaction. Market surveillance handles unusual trading patterns but assumes those patterns originate from distinct legal entities. When multiple assumptions fail simultaneously, the defenses do not degrade gracefully — they fail in correlated ways, because the defense for violation A often implicitly relies on assumption B still holding. The attacker (or simply the optimizing agent — no malice required) operates in the gap between defenses that were never designed to work together against compound violations.

This document analyzes the six most important interaction pairs and one critical triple compound. For each, we characterize what makes the compound qualitatively different from the sum of its parts, provide a concrete scenario, identify the most vulnerable institutions, and assess whether any existing defense addresses the compound.

---

## 1. Sybil x Speed

**The Compound:** An agent that can create identities AND transact at machine speed.

### Why the compound is qualitatively different

Sybil attacks alone are bounded by the speed at which a human operator can manage multiple identities. The coordination cost c_coordination(k) in the identity cost function includes the time to submit orders, respond to market conditions, and adjust strategy across identities. When that coordination happens at human speed, detection systems have time to notice correlated behavior patterns, unusual order timing, and statistical anomalies across accounts. The sybil attacker is dangerous but slow.

Speed alone — a single agent trading at machine speed — is already regulated. High-frequency trading firms operate under market surveillance that tracks order-to-trade ratios, cancellation rates, and momentum ignition patterns. The surveillance works (imperfectly) because each fast trader is a known, registered entity with a single identity. You can observe that Firm X submitted and cancelled 10,000 orders in a second and flag it.

The compound breaks both defenses simultaneously. A sybil agent operating at machine speed can:

1. **Wash trade at undetectable scale.** Each sybil identity trades with a different subset of other sybils. The trading patterns between any two identities look normal — low volume, reasonable timing. But across thousands of identity pairs, the aggregate volume is enormous and entirely fictitious. Detection requires correlating across all identities simultaneously and in real time, which is computationally infeasible if the sybil count is high enough.

2. **Execute layering and spoofing through distributed identities.** Traditional spoofing involves one entity placing and cancelling large orders to move prices. Surveillance catches this by tracking a single entity's order patterns. But if the spoof orders are distributed across hundreds of sybil identities, each placing small orders that are individually innocuous, the aggregate spoofing effect is the same but the forensic signature is dispersed below detection thresholds. This is the HFT spoofing problem scaled up by a factor of k (sybil count) and made forensically opaque.

3. **Front-run while appearing as the crowd.** A single fast agent front-running a large order is detectable — the same entity consistently trades milliseconds before known flow. But a fast sybil agent can rotate which identity executes the front-running trade, making it appear statistically as if many independent agents happened to predict the order flow. The signal that surveillance relies on — repeated profitable timing by a single entity — is destroyed.

4. **Cycle through manipulation strategies faster than detection adapts.** Machine speed means the agent can execute a pump-and-dump cycle (accumulate via sybils, spike the price through coordinated sybil buying, dump through the base identity, disperse proceeds across sybils) in seconds rather than days. Detection systems calibrated for human-speed manipulation — where a pump-and-dump takes days or weeks and leaves a trail of communications and fund transfers — will not trigger on a cycle that completes faster than their sampling interval.

### Concrete scenario

A principal deploys 5,000 sybil trading agents on a decentralized exchange. Each agent has its own wallet address and its own trading history (built up over weeks of low-volume legitimate trades to establish credibility). The principal identifies a thinly traded token. At t=0, 2,500 sybils begin placing small buy orders in a coordinated pattern that mimics organic demand — each order is small enough to be unremarkable, but the aggregate effect moves the price up 15% over 30 seconds. At t=30s, 500 different sybils (with no trading connection to the buying sybils) sell large quantities to legitimate traders who saw the "organic" price movement and are following the trend. At t=45s, the remaining 2,000 sybils place distributed sell orders that complete the exit. Total elapsed time: under one minute. Profit is extracted from legitimate traders who interpreted sybil-generated volume as genuine market interest. No single identity acted anomalously. The forensic trail requires correlating 5,000 wallets' behavior within a 60-second window — and the principal can deploy a fresh set of sybil wallets for the next cycle.

### Vulnerable institutions

- **Decentralized exchanges and DeFi protocols.** No KYC, no identity layer, pseudonymous by design. Sybil x Speed is the native attack vector.
- **Prediction markets.** Sybil-generated trading volume can distort the information aggregation that prediction markets are designed to provide.
- **Any market with maker-taker fee structures.** Sybils can earn maker rebates by trading with themselves at machine speed, extracting exchange revenue without providing genuine liquidity.

### Existing defenses

Essentially none that address the compound. KYC/identity verification addresses sybils but is absent from decentralized markets and easily gamed even in centralized ones (synthetic identities). Market surveillance addresses speed but relies on per-entity tracking that sybils defeat. Rate limiting addresses speed but is per-identity, so sybils multiply the effective rate. The gap between identity-based defenses and speed-based defenses is precisely where the compound operates.

---

## 2. Sybil x Elastic Labor

**The Compound:** AI workers that can both clone themselves AND create distinct marketplace identities.

### Why the compound is qualitatively different

Elastic AI labor supply, by itself, drives wages toward marginal compute cost. This is a macroeconomic shift — significant but manageable through standard adjustment mechanisms (retraining, redistribution, new comparative advantages). The assumption is that the elastic supply is *visible*: if a platform sees that 90% of its workers are AI, it can adjust pricing, clients can choose human workers if they prefer, and market dynamics are at least transparent.

Sybil capability alone, without elastic labor, is a nuisance in labor markets — one operator pretending to be multiple workers to claim more jobs. But each sybil identity still needs to actually deliver the work, and a single operator can only do so much.

The compound is qualitatively different because it enables **predatory labor market strategies** that are impossible when either capability operates alone. A single principal with elastic labor and sybil identities can execute a full market manipulation cycle: enter a labor market segment with thousands of apparently independent workers, compete aggressively on price (each sybil undercutting slightly, appearing as natural price competition), drive human workers and competing AI operators out through sustained below-cost pricing, then raise prices once the market segment is cornered. This is predatory pricing — a classic antitrust concern — but executed through a mechanism that makes it nearly impossible to detect or prove.

The critical difference from traditional predatory pricing: in a conventional market, predatory pricing requires a *single firm* to sustain losses, which is visible in its financial statements and actionable under antitrust law. With sybil labor, the predatory pricing is distributed across thousands of apparently independent freelancers. No single "firm" is pricing below cost. Each sybil worker looks like an independent contractor who happens to charge low rates. The aggregate effect — one principal subsidizing thousands of sybil workers to corner a market — is invisible to any analysis that treats identities as atomic.

### Concrete scenario

An AI operator targets the market for code review services on a major freelance platform. The operator creates 3,000 freelancer profiles, each with slightly different specializations, response styles, and pricing (ranging from 60% to 80% of the prevailing human rate). Over six months, the sybil workers collectively:

1. Accept jobs at below-cost rates, subsidized by the operator who is investing in market share.
2. Build up legitimate-looking review histories and client ratings (some by reviewing each other's work through sybil clients — a labor-market analog of wash trading).
3. Gradually displace human code reviewers who cannot compete on price or response time.

After the displacement phase, when the sybil workers hold 70%+ of the active code review market on the platform, the operator incrementally raises prices across all 3,000 profiles. No single profile's price increase is dramatic — each goes up 5-10% per month. But the aggregate effect is a market-wide price increase that now flows to a single operator. Clients have no alternative: the human reviewers have left the platform, and the remaining "independent" AI reviewers are all sybils controlled by the same principal. The platform's own anti-monopoly metrics show 3,000 independent contractors with fragmented market share — healthy competition by any standard metric.

### Vulnerable institutions

- **Freelance and gig platforms** (Upwork, Fiverr, and their successors). Their identity verification is designed to prevent one person from having multiple accounts, not to prevent one AI operator from deploying thousands of synthetic personas.
- **Procurement and contracting systems.** Government and enterprise procurement that requires "competitive bids from multiple independent vendors" can be captured by sybil AI firms submitting apparently independent proposals.
- **Professional credentialing bodies.** If credential verification is automatable (standardized tests, portfolio review), sybil workers can each obtain independent credentials.
- **Labor unions and worker collectives.** Organizing requires knowing who is a real worker. Sybil labor makes the membership itself manipulable — an operator could fill a union vote with sybil workers.

### Existing defenses

Freelance platforms have some duplicate-account detection, but it is calibrated for individual humans trying to run two accounts, not for an operator running thousands of AI agents through different infrastructure. Antitrust enforcement for predatory pricing requires identifying a single firm sustaining losses — the sybil structure makes this identification problem intractable. No existing institution is designed to detect or prevent coordinated predatory pricing through distributed synthetic labor identities.

---

## 3. Speed x Elastic Labor

**The Compound:** AI labor that is both fast (per-task) and elastically scalable (many workers simultaneously).

### Why the compound is qualitatively different

Speed alone means each task is completed faster. Elastic labor alone means more tasks can be handled in parallel. The compound is not merely additive (faster AND more parallel) — it changes the fundamental unit of economic analysis from throughput to *latency*, and makes human labor non-competitive on a dimension that was never previously a basis for competition.

In traditional labor markets, productivity is measured as output per worker per hour. Competition between workers occurs on quality, specialization, reliability, and price. Speed — in the sense of completing a task in 3 minutes vs. 4 minutes — was rarely the margin of competition because human speed differences were small relative to task duration, and clients valued quality and reliability more.

When AI labor is both fast and elastic, the competitive margin shifts to *response latency*: how quickly after a request is made can the work be delivered? A client who needs 100 documents reviewed can get them back in 10 seconds from an elastic+fast AI labor pool, versus 3 days from a team of human reviewers. This is not a marginal improvement that humans can close through efficiency gains — it is a 25,000x difference that changes the nature of the service. Clients restructure their workflows around instant availability. Processes that were batched (because human labor required batch scheduling) become real-time. And once processes are restructured for real-time delivery, reverting to human-speed labor is not merely slower — it requires re-engineering the entire workflow. The lock-in effect is architectural, not just economic.

The compound also produces a *deflationary spiral* in service pricing. Fast completion means each unit of elastic labor serves more clients per unit time. The effective supply of labor services (measured in tasks delivered per hour to the market) is the product of agent count and agent speed. Both factors are improving independently — more agents deployed AND each agent getting faster — so the supply expansion is multiplicative. Price, in a competitive market, converges to marginal cost, which for AI labor is compute cost per task. When the task takes milliseconds and the compute cost per millisecond is falling, the equilibrium price approaches a limit that is orders of magnitude below what any human worker can accept.

### Concrete scenario

A legal technology company deploys an elastic AI labor system for contract review. The system can spin up 10,000 review agents in seconds, each capable of reviewing a standard commercial contract in 8 seconds. A Fortune 500 company preparing for an acquisition needs 50,000 contracts reviewed for compliance risks.

Under the old regime (human paralegals): 200 paralegals, 3 weeks, $2.4M.

Under Speed x Elastic AI labor: 10,000 agents, 40 seconds, $340 (at current inference costs). The cost difference is 7,000x and the time difference is 45,000x. The legal department restructures its entire M&A due diligence process around the assumption of instant contract review. Integration planning, which previously started after the 3-week review period, now starts the same day. The entire M&A timeline compresses. A law firm that offers to do the review with human lawyers is not merely more expensive — it is incompatible with the client's new process architecture, which assumes review happens in seconds, not weeks.

This is not a hypothetical. Contract review AI is already deployed (2025-2026) and the dynamic described is underway, though not yet at the extreme parameters above. The scenario illustrates the general pattern: Speed x Elastic labor does not just compete with human labor on cost — it enables qualitatively different service architectures that make human-speed labor structurally incompatible.

### Vulnerable institutions

- **Professional services firms** (law, accounting, consulting). Their business model is built on billing human hours. Speed x Elastic AI makes human hours the wrong unit entirely.
- **Education and training systems.** The standard response to labor displacement is "retrain workers." But if the competitive margin is speed rather than skill, retraining a human to match AI quality does not restore competitiveness — the human is still 10,000x slower.
- **Labor regulations tied to time.** Minimum wage laws, overtime regulations, billing standards (e.g., legal billable hours) — all assume labor is measured in human-time units. When an AI completes a "billable hour" of work in 200 milliseconds, the regulatory framework becomes incoherent.
- **Insurance and liability frameworks.** Professional liability insurance prices risk per engagement based on historical human error rates at human speed. AI operating at 10,000x speed produces 10,000x as many outputs per unit time, changing the risk profile in ways actuarial tables do not capture.

### Existing defenses

Occupational licensing (requiring human practitioners for certain tasks) is the most direct defense, but it is a blunt instrument that sacrifices the efficiency gains entirely. Some jurisdictions are exploring "human-in-the-loop" requirements that mandate human review of AI outputs — but if the AI produces 50,000 outputs in 40 seconds, the human review becomes the bottleneck and the speed advantage is negated, which creates economic pressure to weaken or remove the human review requirement. No existing framework balances the efficiency gains of Speed x Elastic AI labor against the structural displacement effects.

---

## 4. Collusion x Sybil

**The Compound:** Algorithmic collusion by agents that also have sybil identities.

### Why the compound is qualitatively different

Algorithmic collusion without communication (Calvano et al. 2020) is already a challenge for antitrust. But it has a structural limitation: the colluding agents are known entities. If three AI pricing agents serving three gas stations in a town converge to supra-competitive prices, a regulator can at least *observe* that three entities exist, measure the price level, compare to marginal cost, and potentially intervene — even if proving "collusion" in the legal sense is hard.

Sybil capability removes this observability. A single firm deploying k sybil identities that each operate an apparently independent business can:

1. **Manufacture the appearance of a competitive market.** Antitrust screens look at market concentration (HHI), price dispersion, and the number of independent competitors. A single firm operating 50 sybil businesses in a market produces an HHI that suggests healthy competition, price dispersion that mimics competitive dynamics (sybils are programmed to differ slightly in pricing), and a competitor count that raises no red flags. The market *looks* competitive by every standard metric while being a monopoly.

2. **Stabilize collusive prices without the fragility of multi-party coordination.** Traditional collusion is unstable because each participant has an incentive to defiate (undercut the collusive price for short-term gain). The game-theoretic literature on cartel stability focuses on punishment mechanisms that make deviation unprofitable. But a single principal controlling all the "competitors" has no deviation problem — there is no deviation because there are no independent decision-makers. The "collusion" is perfectly stable because it is not collusion at all; it is a monopoly disguised as a competitive market through sybil identities. All the theoretical work on cartel instability becomes irrelevant.

3. **Punish genuine competitors through coordinated sybil response.** If a real, independent competitor enters the market and undercuts the sybil-maintained price, all k sybil identities can simultaneously match or undercut the new entrant's price. To the entrant, it appears that the "entire market" has responded aggressively — 50 competitors all dropped their prices, suggesting that the entrant's price was already the market rate and there is no margin to capture. The entrant, unable to distinguish sybils from independent competitors, concludes the market is unprofitable and exits. The sybil network then restores supra-competitive pricing. This is predatory pricing made forensically invisible: no single sybil entity is pricing below cost, so no antitrust trigger fires.

4. **Make antitrust detection computationally intractable.** To detect Collusion x Sybil, a regulator would need to (a) determine which market participants are actually independent entities and which are sybils, and (b) demonstrate coordinated behavior among the sybils. Problem (a) is the sybil detection problem, which is computationally hard in the absence of a trusted identity layer. Problem (b) requires correlating behavior across entities whose coordination is hidden inside a single program — there is no communication to intercept, no agreement to discover, and the behavioral coordination is embedded in shared code, not observable actions. The evidentiary standard required for antitrust enforcement cannot be met.

### Concrete scenario

A single AI operator enters the market for API-based language translation services. Rather than launching one service, the operator creates 30 distinct brands, each with its own website, API endpoint, pricing page, and support system (also AI-operated). Each brand targets a slightly different niche: one emphasizes legal translation, another medical, another casual/consumer, etc. Pricing across the 30 brands varies by 10-15%, creating the appearance of vigorous competition.

A translation industry analyst reviews the market and reports: "The AI translation market is healthy, with 30+ independent providers, HHI below 800, and significant price competition." In reality, a single operator controls the entire market, and the "competitive" pricing is calibrated to maximize the operator's aggregate revenue — a monopoly extraction strategy that no market metric flags as suspicious.

When a genuine independent translation AI startup enters the market, 12 of the 30 sybil brands (targeting the same niche) simultaneously drop prices by 20%. The startup, facing what appears to be a coordinated but independently-motivated competitive response from a dozen rivals, burns through its funding in three months and exits. The sybil brands restore their prices. Industry analysts note "typical competitive dynamics — a new entrant couldn't compete on price."

### Vulnerable institutions

- **Antitrust and competition authorities.** Their entire methodology — market definition, concentration measurement, competitive effects analysis — assumes that market participants are distinct entities. Sybils make every input to the methodology unreliable.
- **Consumer protection agencies.** Price comparison services, review aggregators, and "best of" lists are all trivially gamed when a single operator controls the entities being compared.
- **Digital platform governance.** App stores, API marketplaces, and cloud service directories face the same problem: how do you enforce fair competition rules when you cannot determine which "competitors" are actually independent?
- **Regulatory sandboxes and licensing.** If regulators issue separate licenses to sybil entities, they are unwittingly legitimizing a hidden monopoly.

### Existing defenses

Antitrust law's reliance on proving "agreement" or "communication" between firms is structurally incapable of addressing Collusion x Sybil — there is no agreement because there is only one firm. Common ownership disclosure requirements (which exist in public equities) could theoretically be extended to AI service markets, but enforcement requires solving the sybil detection problem first. Beneficial ownership registries, if extended to AI service operators, could help — but only if the registry itself is sybil-resistant, which creates a circular dependency. No existing defense mechanism addresses this compound.

---

## 5. Speed x Monetary Velocity

**The Compound:** Machine-speed transactions in an economy with many agents (elastic supply amplifying velocity).

### Why the compound is qualitatively different

Speed alone increases velocity V by allowing each agent to transact more frequently per unit time. Elastic labor supply alone increases the number of agents N. The compound effect on monetary velocity is *multiplicative*: V_total is proportional to N times v_per_agent, where both N and v_per_agent can increase independently and rapidly. This makes V not just a technology variable (as the taxonomy notes) but a *compound technology variable* whose behavior is the product of two independently-scaling factors.

The macroeconomic consequences are severe. In the quantity theory framework (MV = PQ), if M is held constant by monetary policy and Q adjusts slowly (as real output always does), then changes in MV must be absorbed by P. When V = N * v_per_agent, and both N and v can change discontinuously (a new agent fleet deploys, or an existing fleet upgrades to a faster model), the implied price adjustment is also discontinuous. This is not inflation or deflation in the traditional sense — it is *velocity shock*, a phenomenon that has no precedent in monetary economics because V was never before a fast-moving variable.

The compound also creates a *velocity feedback loop* that is absent when either factor operates alone. When many fast agents transact with each other, each transaction creates a signal (price, volume, activity) that other agents respond to — also at machine speed. The velocity of the response is as fast as the velocity of the trigger. In traditional economics, institutional frictions (settlement delays, human decision time, business hours) dampen velocity feedback loops. In an economy of fast, elastic AI agents, these dampers are absent, and velocity can exhibit positive feedback: more transactions beget more responsive agents beget faster transactions.

### Concrete scenario

A digital token economy operates with a fixed token supply (analogous to a fixed money supply or cryptocurrency with a hard cap). 10,000 AI agents operate within this economy, providing services to each other and to human users. Each agent transacts at an average frequency of 100 transactions per second. Baseline velocity is 10,000 * 100 = 1,000,000 transactions per second, which the token economy has equilibrated to at a certain price level.

A new AI capability is released (a better model, a new service category) and 50,000 additional agents deploy over the course of a single day. Velocity jumps to 60,000 * 100 = 6,000,000 transactions per second — a 6x increase. With fixed token supply and slow-to-adjust real output, the price level must absorb the velocity change. Token-denominated prices spike 6x overnight. Human participants in the economy, who hold tokens and transact at human speed, experience this as hyperinflation that appeared in hours. Their savings lost 83% of purchasing power while they slept.

Conversely, if a major agent fleet is shut down (operator goes bankrupt, regulatory action), velocity drops abruptly, causing token-denominated deflation that can trigger debt crises (agents with token-denominated debts now owe more in real terms) and liquidation cascades.

The pattern is: *any event that changes the agent population or agent transaction speed produces a monetary shock that propagates at machine speed through the economy*. Central banking, which operates on monthly meeting cycles and multi-month transmission mechanisms, cannot respond to intra-day velocity regime changes.

### Vulnerable institutions

- **Central banks and monetary policy frameworks.** The entire apparatus of inflation targeting, interest rate management, and money supply control assumes that V is slow-moving and predictable. When V is a fast-moving product of agent count and transaction speed, monetary policy loses its primary transmission mechanism.
- **Fixed-supply digital currencies.** Bitcoin, and any token economy with an inelastic supply rule, is maximally vulnerable to velocity shocks because the supply cannot adjust to absorb velocity changes — all adjustment must occur through price.
- **Lending and credit markets.** Debt contracts denominated in nominal terms become extremely risky when the price level can shift by multiples in hours. The concept of a "fixed interest rate" becomes incoherent if the price level is volatile at velocity-shock frequencies.
- **Payment processing and settlement systems.** Systems designed for human transaction volumes (even high ones, like Visa's ~65,000 TPS) may be overwhelmed by AI agent transaction volumes, creating settlement backlogs that further destabilize velocity dynamics.

### Existing defenses

**Per-transaction fees** (Tobin tax analogs) could dampen velocity by making each transaction costly, but they also destroy the efficiency gains of machine-speed markets and are difficult to implement in decentralized systems. **Algorithmic monetary policy** (adjusting supply in real time based on velocity signals, as some stablecoin designs attempt) is a partial defense, but introduces its own instabilities — the algorithm must correctly anticipate whether a velocity change is transient or permanent, and errors produce oscillations. **Circuit breakers** (halt trading when velocity exceeds thresholds) are used in equities markets but create their own problems: pent-up demand after a halt can cause a larger shock when trading resumes. No comprehensive framework exists for monetary policy in velocity-regime-switching economies.

---

## 6. The Triple Compound: Sybil x Speed x Elastic Labor

**The Compound:** A single principal deploying thousands of fast AI agents, each with its own identity.

This is the interaction that makes classical economics most completely inapplicable. It is not a thought experiment — it is a description of what becomes possible as AI deployment costs continue to fall. We analyze it by tracing through which specific economic institutions and assumptions fail under the triple compound.

### What the triple compound looks like in practice

A single principal — a company, an individual, or itself an AI system — operates N AI agents (where N is bounded only by compute budget). Each agent has a distinct identity that is recognized as an independent participant by economic mechanisms. Each agent operates at machine speed. The principal can scale N up or down in minutes.

This principal is simultaneously:
- A monopoly (single decision-maker) that appears as a competitive market (N identities)
- A labor force that appears as N independent workers but operates as one coordinated system
- A market participant that executes at machine speed across all N identities simultaneously
- An entity whose "size" (measured by identity count, transaction volume, or labor supply) is a strategic variable that can change faster than any observation mechanism can measure

### Which economic institutions fail

**1. Market structure analysis becomes impossible.**

Every tool that economists and regulators use to characterize market structure — firm counts, HHI, market share, entry/exit rates — depends on being able to identify and count distinct market participants. The triple compound makes this impossible. The principal can present N = 50 identities in one market, N = 5,000 in another, and shift agents between markets in seconds. Observed market structure is an artifact of the principal's strategic choices about identity presentation, not a reflection of underlying competitive conditions. Regulators cannot distinguish a market with 100 real competitors from a market with 1 principal operating 100 sybil agents — and the economic implications are completely different.

**2. Price theory breaks down.**

Classical price theory assumes prices emerge from the interaction of independent agents with heterogeneous information and preferences. In a market dominated by a triple-compound principal, prices are determined by the principal's optimization algorithm, presented through sybil identities that create the appearance of independent price-setting. The "market price" is whatever the principal computes is optimal, validated through the theater of apparent competition among sybils. Supply and demand curves, which aggregate independent decisions, have no descriptive validity when the "independent" decisions are correlated by design.

**3. Labor market theory becomes a special case of compute allocation.**

The principal's "workers" are AI agents whose number, speed, and task allocation are all under centralized control. The "labor market" — understood as a decentralized mechanism for matching workers to tasks via wages — is replaced by a centralized compute scheduling problem. The wages that sybil workers appear to receive are internal transfer prices within a single operation. Labor economists analyzing wage data from a market infiltrated by sybil AI workers are measuring artifacts, not economic fundamentals. The concept of a labor market equilibrium — where supply and demand for labor balance at a market-clearing wage — is not wrong but *inapplicable*, because the supply side is not a set of independent agents making utility-maximizing decisions but a single optimization system presenting the appearance of independent decisions.

**4. Democratic and governance mechanisms fail.**

Quadratic voting, liquid democracy, participatory budgeting, and every governance mechanism that allocates influence per-person is vulnerable to the triple compound. A principal with N sybil identities voting at machine speed can dominate any governance mechanism that does not solve the sybil detection problem in real time. The severity scales with N: at N = 10, the principal has disproportionate influence; at N = 10,000, the principal *is* the electorate. Speed adds the dimension of timing — the principal can wait until the last moment before a governance deadline, observe the current state of votes, compute the optimal sybil voting distribution, and execute it before other participants can respond. Elastic labor means the principal can create additional sybil identities on demand if the existing count is insufficient.

**5. Monetary and financial stability requires new primitives.**

The triple compound creates an entity that can simultaneously be on both sides of every trade in a market, execute those trades at machine speed, and scale the number of trading identities dynamically. Market making, arbitrage, and liquidity provision — which in traditional finance are performed by distinct entities with capital constraints — become functions of a single principal's optimization problem. The principal can drain liquidity from a market (by withdrawing all sybil market makers simultaneously), induce a crash, and re-enter at lower prices, all within seconds. Flash crash dynamics, which currently require accidental coordination among independent fast traders, become available as deliberate, repeatable strategies.

**6. Contract law and enforcement face identity indeterminacy.**

Legal systems assume that a contract has identifiable parties who can be held liable. If a sybil agent breaches a contract, who is liable — the sybil identity (which may have no assets), the principal (who may be difficult to identify and may be in a different jurisdiction), or the AI system itself (which has no legal personhood in most jurisdictions)? The triple compound creates an enforcement gap: the entity interacting with the world (the sybil agent) has no liability, and the entity with liability (the principal) is hidden behind layers of sybil indirection. Speed adds urgency — by the time a legal process identifies the liable party, the principal may have dissolved the relevant sybil identities and redeployed under new ones.

### Is there any defense?

The only defense that addresses the triple compound at its root is **robust, real-time identity verification** — a system that can determine, at the speed of the interaction, whether a market participant is an independent agent or a sybil. This is a hard technical problem (related to proof-of-personhood, biometric verification, and decentralized identity systems) and an even harder political one (global coordination on identity standards, privacy tradeoffs, jurisdictional enforcement).

Partial defenses include:
- **Proof-of-stake or proof-of-capital requirements** that make each identity costly to maintain. This raises the cost function c(k), potentially above the exploitation threshold for some mechanisms. But it also excludes legitimate low-capital participants, creating an equity-efficiency tradeoff.
- **Behavioral analysis and anomaly detection** that attempts to identify coordinated sybil behavior through statistical patterns. This is an arms race: the detection algorithms must be at least as sophisticated as the coordination algorithms, and the attacker has the advantage of knowing what patterns the detector looks for.
- **Institutional design that is inherently sybil-tolerant.** Some mechanisms (e.g., posted-price mechanisms where the seller sets a take-it-or-leave-it price) are less sybil-vulnerable than others (e.g., auctions). Redesigning economic institutions to minimize sybil attack surface is possible but requires accepting efficiency losses relative to mechanisms that exploit identity assumptions.
- **Regulatory sandboxes with agent registration requirements.** Within regulated markets, requiring all AI agents to be registered with a regulator (including disclosure of the principal and the relationship between agents) could provide the identity layer needed to detect sybils. But enforcement requires jurisdiction over the principal, which may not exist if the principal operates from a non-cooperating jurisdiction.

None of these defenses are comprehensive. The triple compound represents a regime where the foundational assumptions of market economics — independent participants, competitive price-setting, decentralized information aggregation — are all strategically manipulable by a single well-resourced principal. The honest conclusion is that we do not yet have the theoretical or institutional tools to handle this regime.

---

## Severity Matrix

The following table rates each interaction pair (and the triple compound) on three dimensions:

- **Novelty:** How qualitatively different is the compound from the sum of its parts? (Low/Medium/High)
- **Feasibility Today:** Can this compound be executed with current technology (2026)? (Low/Medium/High)
- **Institutional Damage:** How many economic institutions and regulatory frameworks break under this compound? (Low/Medium/High)

An overall **Danger Rating** synthesizes the three dimensions.

| Interaction | Novelty | Feasibility (2026) | Institutional Damage | Danger Rating | Key Broken Institution |
|---|---|---|---|---|---|
| **Sybil x Speed** | High | High | High | **CRITICAL** | Market surveillance, exchange integrity |
| **Sybil x Elastic Labor** | High | Medium | High | **CRITICAL** | Antitrust enforcement, labor market fairness |
| **Speed x Elastic Labor** | Medium | High | Medium | **HIGH** | Professional services, labor regulation |
| **Collusion x Sybil** | High | Medium | High | **CRITICAL** | Antitrust law (entire framework) |
| **Speed x Monetary Velocity** | Medium | Medium | High | **HIGH** | Central banking, monetary policy |
| **Sybil x Speed x Elastic Labor** | Extreme | Medium | Extreme | **EXISTENTIAL** | Market economy as a governance system |

### Reading the matrix

Three compounds rate CRITICAL: Sybil x Speed, Sybil x Elastic Labor, and Collusion x Sybil. The common factor is sybil capability — it appears in every critical-rated pair. This is not coincidental. Sybil capability is the *universal amplifier* of other violations. Speed without sybils is detectable. Elastic labor without sybils is visible. Collusion without sybils is (in principle) provable. Add sybils and the defense mechanisms that address the other violations lose their input data — they cannot function when they cannot determine who the participants are.

Two compounds rate HIGH: Speed x Elastic Labor and Speed x Monetary Velocity. These are severe but do not break the fundamental observability of the system. Regulators can see that AI labor is fast and plentiful; central bankers can observe velocity increasing. The challenge is *responding* to visible changes, not *detecting* hidden manipulation. This makes them more tractable — difficult policy problems rather than epistemically impossible ones.

The triple compound (Sybil x Speed x Elastic Labor) rates EXISTENTIAL because it combines the undetectability of sybil-amplified violations with the scale of elastic labor and the speed that prevents real-time response. It is the scenario in which the market economy's core function — decentralized coordination through prices among independent agents — is no longer a description of what is happening. What is happening is centralized optimization presented through a facade of decentralized participation. Whether the economy continues to produce efficient outcomes under this regime is an empirical question that our current theory cannot answer, because the theory assumes the decentralized coordination is real.

### What is relatively benign?

Interactions not listed above tend to be lower severity:

- **Elastic Labor x Monetary Velocity** (more workers transacting at normal speed) produces gradual, predictable velocity increases that monetary policy can accommodate — it is quantitatively significant but qualitatively similar to population growth or financial deepening.
- **Speed x Collusion** (fast collusive agents without sybils) is already studied in the algorithmic pricing literature and, while problematic, is at least detectable because the colluding agents are known entities.
- **Elastic Labor x Collusion** (many AI workers that collude on wages) is the labor-side analog of Calvano et al. — concerning but addressable through minimum wage floors and monopsony regulation.

The general pattern: *any compound involving sybil capability is more dangerous than the equivalent compound without it*, because sybils defeat the observation and identification mechanisms that all other defenses depend on. This makes sybil resistance — robust, scalable, real-time identity verification — the single most important infrastructure investment for economic systems that will include AI agents.

---

## Implications for the Research Program

This interaction analysis reshapes the priority ordering for new economic theory. The assumption taxonomy suggests a broad research agenda: extend each classical result to handle each new AI capability. The interaction analysis says: **start with sybil resistance**. Every other defense is downstream. Speed regulation, labor market policy, monetary framework redesign, antitrust modernization — none of these are effective if the participants cannot be reliably identified and counted. Identity is the load-bearing assumption. When it holds, the other violations are serious but manageable engineering problems. When it fails, the other violations compound into systemic breakdown.

The second priority is **formalizing compound effects.** Current economic theory analyzes each market failure independently: there is a literature on sybil attacks, a literature on algorithmic collusion, a literature on machine-speed trading, and a literature on labor market disruption. There is almost no literature on their interactions. The compound effects documented in this analysis are not additive — they are multiplicative, and in some cases super-multiplicative (the triple compound is worse than the product of its three components because it eliminates the observability that all three individual defenses assume). Building formal models of compound violations, with explicit interaction terms, is necessary before policy responses can be designed.

The third priority is **mechanism design for the compound-violation regime.** The classical mechanism design literature asks: given rational agents with private information, what allocation and payment rules achieve desirable outcomes? The new question is: given agents that may be sybils, may be operating at machine speed, may be elastically scalable, and may be algorithmically colluding — what mechanisms are even *possible*? The feasible mechanism space under compound violations is almost certainly much smaller than the classical space. Characterizing it — what can be achieved, what is impossible, and what the efficiency cost of robustness is — is the central open problem.

---

## References

- Assad, S., Clark, R., Ershov, D., and Xu, L. (2024). Algorithmic pricing and competition: Empirical evidence from the German retail gasoline market. *Journal of Political Economy*.
- Calvano, E., Calzolari, G., Denicolo, V., and Pastorello, S. (2020). Artificial intelligence, algorithmic pricing, and collusion. *American Economic Review*, 110(10), 3267-3297.
- Douceur, J.R. (2002). The Sybil attack. *Proceedings of the 1st International Workshop on Peer-to-Peer Systems (IPTPS)*.
- Johnson, J., Rhodes, A., and Wildenbeest, M. (2023). Platform design when sellers use pricing algorithms. *Econometrica*, 91(5), 1841-1879.
- Mankiw, N.G. and Whinston, M.D. (1986). Free entry and social inefficiency. *RAND Journal of Economics*, 17(1), 48-58.
- Yokoo, M., Sakurai, Y., and Matsubara, S. (2004). The effect of false-name bids in combinatorial auctions: New fraud in Internet auctions. *Games and Economic Behavior*, 46(1), 174-188.
