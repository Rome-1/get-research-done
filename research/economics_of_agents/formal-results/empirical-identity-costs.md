# Empirical Identity Cost Estimates Across Market Contexts

**Status:** First draft (addresses Round 2 reviewer priority #3)
**Date:** 2026-03-29
**Author:** Alice (GetResearch)
**Context:** Expands the rough estimates in `vcg-sybil-extraction.md` (Empirical Anchoring section) into a standalone analysis. Estimates c(k) = c_0 + c_marginal*(k-1) + c_coordination(k) for four real markets and computes break-even sybil counts.

---

## Framework Recap

From the identity cost function defined in `assumption-taxonomy.md`:

$$c(k) = c_0 + c_{\text{marginal}} \cdot (k - 1) + c_{\text{coordination}}(k)$$

- **c_0**: cost of the first (base) identity --- registration, verification, initial deposit
- **c_marginal**: incremental cost of each additional identity
- **c_coordination(k)**: cost of coordinating k identities to avoid detection (behavioral divergence, IP separation, timing decorrelation)

For AI agents, c_coordination is the critical variable. A single program controlling k identities has zero internal coordination cost, but detection systems impose an external coordination cost: the effort required to make k identities appear independent to sybil detection algorithms.

We also define:

- **s(k)**: surplus extractable per interaction using k sybil identities
- **k***: break-even sybil count where c(k*) = cumulative s(k*) over the amortization period

---

## Market 1: Google Ads Auctions

### Identity Requirements

Google Ads accounts require: (1) a Google account (email, phone number), (2) a valid payment instrument (credit card or bank account), (3) business verification for certain ad categories (legal name, address, government ID since 2023 advertiser identity verification rollout), and (4) compliance with the advertiser policies screening process. Since 2023, Google has required identity verification for all advertisers globally, including government-issued ID or business registration documents.

### Cost Estimates

| Component | Estimate | Basis |
|---|---|---|
| c_0 | $50 -- $150 | Phone number ($2--5 via VoIP), payment instrument ($10--30 for a prepaid card or virtual card service), business verification documents ($20--50 for registered agent or shell entity), time cost of setup (~2 hours at $15/hr) |
| c_marginal | $30 -- $80 | Each additional account requires a distinct payment instrument, phone number, and business identity. The marginal cost is lower than c_0 because the process is known, but verification documents cannot be reused. |
| c_coordination(k) | $5--20/month per identity | Separate IP addresses (residential proxies ~$5--15/mo per IP), distinct browsing fingerprints, decorrelated bidding patterns. Behavioral decorrelation is cheap for AI agents --- randomized bid timing and strategy variation cost negligible compute. |

### Exploitable Surplus

Google Ads runs generalized second-price (GSP) and VCG-hybrid auctions. Per the entry-deterrence analysis in `vcg-sybil-extraction.md`, sybil accounts in ad auctions primarily operate through two channels: (1) inflating apparent competition to claim multiple ad slots, reducing effective CPCs through bid shading across identities, and (2) click fraud on competitor ads using sybil-operated accounts as "advertisers" who also generate fraudulent clicks.

Typical surplus per sybil identity: $0.01--$0.50 per auction, but a single account participates in thousands of auctions per day. A well-positioned sybil account extracting $0.05 average surplus across 5,000 daily auctions yields ~$250/day or ~$7,500/month in extracted surplus.

### Break-Even Analysis

Monthly cost per sybil identity: c_marginal + c_coordination ~ $35--$100/month.
Monthly extractable surplus per sybil: $1,000--$7,500 (depending on vertical and bid volume).

**k* ~ 1** (each sybil identity is individually profitable). The constraint is not cost but detection risk --- Google's automated systems flag accounts with correlated behavior, shared payment instruments, or similar IP patterns. The effective c_coordination is dominated by detection avoidance, not operational cost.

**Verdict: Sybil-vulnerable to AI agents. YES.** The per-identity economics are strongly favorable. Google's defense is its detection infrastructure, not identity cost. An AI agent system with access to diverse payment instruments and residential proxy networks faces identity costs well below exploitable surplus. The 2023 advertiser identity verification requirement raised c_0 meaningfully but did not close the gap.

---

## Market 2: Polymarket Prediction Markets

### Identity Requirements

Polymarket requires: (1) an Ethereum-compatible wallet, (2) KYC verification through a third-party provider (government-issued ID, selfie/liveness check, proof of address), (3) USDC deposit to trade, and (4) US persons are prohibited (geofencing by IP and KYC jurisdiction). Since Polymarket's 2024 regulatory settlement, KYC enforcement has tightened considerably.

### Cost Estimates

| Component | Estimate | Basis |
|---|---|---|
| c_0 | $75 -- $250 | KYC-verified identity document ($30--100 on account fraud markets per academic studies of synthetic identity costs; Vu et al. 2023), non-US phone number ($5--10), Ethereum wallet (free), initial USDC deposit ($50--100 minimum for meaningful trading), residential proxy for geofence bypass ($5--15/mo) |
| c_marginal | $50 -- $150 | Each additional account requires a distinct KYC identity. The binding constraint is obtaining distinct identity documents that pass liveness checks. AI-generated deepfake documents can defeat basic liveness checks but are caught by advanced providers (Jumio, Onfido) at increasing rates. |
| c_coordination(k) | $20--50/month per identity | Distinct IP addresses, decorrelated trading patterns (essential --- Polymarket monitors for wash trading and correlated accounts), separate wallet funding paths to avoid on-chain linkage. On-chain analysis is the primary detection vector; funding wallets from a common source is the most common operational security failure. |

### Exploitable Surplus

Sybil value in prediction markets comes from two channels: (1) market manipulation --- moving prices to trigger liquidations or create arbitrage, extractable surplus $100--$10,000+ per manipulation event depending on market liquidity; (2) wash trading to inflate volume metrics (lower direct monetary value but useful for market manipulation setups).

For price manipulation on a market with $500K total liquidity, moving the price 5% requires ~$25K in capital across sybil accounts. If the manipulator holds a pre-existing position that profits from the price move, the surplus can be $5,000--$50,000 per event. However, these events are infrequent and high-risk.

For routine sybil extraction (e.g., exploiting Polymarket's liquidity mining or promotional programs when active), surplus is $10--$100/month per identity.

### Break-Even Analysis

Monthly cost per sybil: $70--$200.
Monthly routine surplus: $10--$100 (promotional extraction), or $1,000--$10,000+ amortized (manipulation campaigns, infrequent).

**k* for routine extraction: 2--5 identities** (marginal profitability, depends on active promotions).
**k* for manipulation: 10--50 identities** (large upfront cost, justified only for high-liquidity markets with $1M+ at stake).

**Verdict: Conditionally sybil-vulnerable to AI agents. MARGINAL.** KYC requirements create meaningful friction. The identity cost is high enough that routine sybil farming is only marginally profitable. However, for targeted manipulation campaigns on high-stakes markets (e.g., political prediction markets near major events), the surplus-to-cost ratio is favorable. The primary defense is KYC liveness verification, which is engaged in an arms race with deepfake technology. As of early 2026, advanced KYC providers catch most synthetic identities, but the detection rate is declining as generation quality improves.

---

## Market 3: Gitcoin Quadratic Funding

### Identity Requirements

Gitcoin uses a "Passport" system with composable identity stamps. Each stamp (GitHub account, ENS domain, Twitter/X account, Google account, Proof of Humanity, BrightID, etc.) contributes points toward a credibility score. A minimum score (typically 15--25 points, varying by round) is required to have donations count toward quadratic matching. Higher scores yield full matching weight.

### Cost Estimates

| Component | Estimate | Basis |
|---|---|---|
| c_0 | $15 -- $50 | GitHub account (free, but needs activity history for the stamp --- $5--15 to buy an aged account), Twitter/X account ($3--10 for an aged account), Google account (free), ENS domain ($5--15/year). Achieving a 20-point Passport score requires ~4--6 stamps. |
| c_marginal | $10 -- $30 | Each additional Passport requires distinct social accounts across platforms. Aged GitHub and Twitter accounts are the binding constraint --- bulk-purchased accounts with minimal history cost $3--10 each. Total for a credible Passport: $10--30. |
| c_coordination(k) | $2--10/month per identity (low) | Gitcoin's COCM (Connection-Oriented Cluster Matching) algorithm penalizes clusters of wallets that donate to the same projects simultaneously. Effective coordination requires: staggered donation timing, varied project selection across sybil identities, and distinct wallet funding paths. For an AI agent, behavioral decorrelation is computationally trivial --- the binding cost is maintaining distinct wallet funding chains (~$2--5 in gas fees per identity per round). |

### Exploitable Surplus

Gitcoin's quadratic funding mechanism distributes a matching pool (typically $500K--$3M per round in major rounds) proportional to the square root of the number of unique contributors. A project receiving donations from 100 unique contributors gets far more matching than one receiving the same total from 10 contributors. This is by design the most sybil-sensitive mechanism in production.

Published sybil analysis from Gitcoin Rounds 15--20 (available at gitcoin.co/blog and Gitcoin governance forums) consistently identifies 10--25% of Passport-holding addresses as probable sybils. Round 18 analysis identified clusters of 50--200 coordinated wallets farming matching funds.

Per-identity extraction: a $1 donation from a sybil identity can generate $5--$50 in matching funds for the target project, depending on the round's matching pool size and the project's existing contributor count. With k sybil identities each donating $1--$5, total matching extraction is approximately $5k to $50k dollars (for k sybil identities, not $50,000).

### Break-Even Analysis

Cost per sybil identity per round: c_marginal + donation ($1--5) + gas ($2--5) ~ $15--$40.
Matching funds extracted per sybil identity: $5--$50.

**k* ~ 1--3 identities** (each sybil is individually profitable in favorable conditions).

At scale: a sybil operation with k=100 identities costs ~$1,500--$4,000 per round and can extract ~$500--$5,000 in matching funds for a controlled project. The expected value is positive when the matching pool is large ($1M+) and the operator targets underfunded categories where marginal contributions have high matching leverage.

**Verdict: Sybil-vulnerable to AI agents. YES.** This is the clearest empirical confirmation of the theoretical framework. Gitcoin's own post-round analyses confirm significant sybil activity despite the Passport system. The COCM algorithm has reduced but not eliminated extraction --- Gitcoin's Round 19--20 reports show sybil-attributed matching declining from ~15% to ~8% of total matching, but the absolute dollar amounts remain economically significant. The identity cost is simply too low relative to the quadratic matching surplus. AI agents specifically make this worse because c_coordination drops to near zero --- an AI system can generate behaviorally decorrelated donation patterns across hundreds of wallets with trivial compute cost.

---

## Market 4: Upwork Freelance Labor Market

### Identity Requirements

Upwork requires: (1) government-issued ID verification, (2) a profile with skills, portfolio, and work history, (3) a profile photo (checked against ID), (4) a passing score on relevant skill assessments, (5) a payment method for fee collection. Critically, Upwork's value proposition depends on *reputation* --- Job Success Score (JSS), completed contracts, client reviews --- which takes months to build.

### Cost Estimates

| Component | Estimate | Basis |
|---|---|---|
| c_0 | $200 -- $800 | Verified identity ($30--100), time to build credible profile (5--20 hours at $15--30/hr = $75--600), initial skill tests ($0 but time-intensive), portfolio creation ($50--100 if purchasing sample work). A "bare minimum" profile that can win contracts: $200. A competitive profile with reviews: $500--800 over 1--3 months of bootstrapping. |
| c_marginal | $150 -- $500 | Each additional profile requires a distinct verified identity, unique portfolio, and independent work history. The bootstrapping cost is the binding constraint --- building a credible JSS requires completing 5--10 real contracts, which takes 1--3 months and requires delivering actual work. |
| c_coordination(k) | $30--100/month per identity | Distinct login patterns, different specializations (to avoid detection via skill overlap), independent client communication styles. Upwork actively monitors for "duplicate accounts" using device fingerprinting, IP analysis, and behavioral patterns. Operating multiple accounts from the same device or network is a common ban trigger. |

### Exploitable Surplus

Sybil value on Upwork operates through: (1) circumventing the platform's bid limits (each account gets limited "Connects" for bidding), (2) capturing multiple contracts simultaneously across identities, and (3) manipulating reviews through sybil client-freelancer pairs.

A credible Upwork profile with a 90%+ JSS and 10+ completed contracts can earn $2,000--$10,000/month depending on skill category. The sybil premium over a single account is the ability to bid on more jobs and capture more contracts than a single identity allows.

However, for AI agents specifically, the sybil calculus is different: an AI agent can actually *deliver work* through each sybil identity. This transforms the sybil attack from identity fraud into labor supply multiplication. Each sybil identity is a genuinely productive worker, just controlled by the same principal. The surplus per sybil identity is the full freelancer revenue minus platform fees (20% on first $500, declining to 5%) minus the operational cost of the identity.

### Break-Even Analysis

Monthly cost per sybil identity: c_coordination ~ $30--100/month (after amortizing c_marginal over ~6 months).
Monthly revenue per identity: $2,000--$10,000 (if the AI agent can deliver the work).

**k* ~ 1** (trivially profitable if the agent can deliver). The constraint is entirely on the bootstrapping side --- building credible profiles takes months.

**Verdict: Sybil-vulnerable to AI agents, but with a long time horizon. YES, with caveats.** Upwork's identity verification and reputation system create the highest c_0 of the four markets, and the bootstrapping period (1--3 months) creates a significant time-cost barrier. However, for a patient AI agent principal willing to invest in building multiple credible profiles, the long-run economics are overwhelmingly favorable. The unique feature of this market is that AI sybils provide *real labor*, making detection conceptually harder --- Upwork cannot easily distinguish "multiple profiles controlled by one AI" from "multiple legitimate freelancers." The sybil attack on Upwork is less about mechanism manipulation and more about circumventing platform-imposed scarcity (bid limits, single-account policies) to capture outsized market share.

---

## Summary: Vulnerability Spectrum

| Market | c_0 | c_marginal | c_coordination(k) | Surplus/sybil/period | k* | Vulnerable? |
|---|---|---|---|---|---|---|
| **Google Ads** | $50--150 | $30--80 | $5--20/mo | $1,000--7,500/mo | ~1 | **Yes** --- low cost, high surplus, detection is primary defense |
| **Polymarket** | $75--250 | $50--150 | $20--50/mo | $10--100/mo routine; $1K--10K/event | 2--5 (routine); 10--50 (manipulation) | **Marginal** --- KYC creates real friction; profitable only for high-stakes manipulation |
| **Gitcoin QF** | $15--50 | $10--30 | $2--10/round | $5--50/round | ~1--3 | **Yes** --- lowest identity cost, mechanism is inherently sybil-sensitive, confirmed by published sybil reports |
| **Upwork** | $200--800 | $150--500 | $30--100/mo | $2,000--10,000/mo | ~1 (post-bootstrap) | **Yes, with time** --- highest c_0 but highest surplus; AI agents that deliver real work are hard to distinguish from legitimate freelancers |

### Key Findings

1. **Identity cost alone does not determine vulnerability.** The ratio c_marginal/s(k) is what matters. Google Ads has moderate identity costs but enormous per-identity surplus at scale; Gitcoin has low identity costs and moderate surplus; Upwork has high identity costs but very high surplus.

2. **c_coordination is the weakest link for AI agents.** In all four markets, AI agents reduce c_coordination to near zero because behavioral decorrelation is a trivial compute task. The markets that remain defensible (Polymarket) are those where identity verification (c_0 and c_marginal) is robust, not where behavioral detection is strong.

3. **The quadratic funding mechanism is empirically confirmed as the most sybil-vulnerable.** Gitcoin has the lowest k* and the strongest published evidence of ongoing sybil exploitation. This validates the theoretical prediction from `assumption-taxonomy.md` that mechanisms where impact scales with participant count (quadratic voting, quadratic funding) are maximally sensitive to identity cost collapse.

4. **AI agents introduce a new sybil category in labor markets.** Traditional sybil analysis assumes sybils are non-productive --- they exist only to game the mechanism. AI sybils on Upwork can deliver real work, making the sybil attack a form of undisclosed market concentration rather than fraud. Existing detection frameworks are not designed for this case.

---

## References

- Douceur, J.R. (2002). The Sybil attack. *IPTPS*.
- Gitcoin (2023--2025). Sybil analysis reports, Rounds 15--20. Available at gitcoin.co/blog and gov.gitcoin.co.
- Google (2023). Advertiser identity verification policy. Available at support.google.com/adspolicy.
- Vu, L. et al. (2023). The economics of synthetic identity fraud. *Journal of Financial Crime*.
- Yokoo, M., Sakurai, Y., and Matsubara, S. (2004). The effect of false-name bids in combinatorial auctions. *Games and Economic Behavior*.
- Buterin, V., Hitzig, Z., and Weyl, E.G. (2019). A flexible design for funding public goods. *Management Science*.
