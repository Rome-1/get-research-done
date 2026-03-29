# KYC Erosion and the Meat-Puppet Trajectory

**Status:** First draft
**Date:** 2026-03-29
**Author:** Alice (GetResearch)
**Motivation:** PI Feedback F1 — Markets with human-provable identity requirements substantially reduce the sybil surface today, but the protection erodes along a predictable trajectory
**Related:** `assumption-taxonomy.md` (identity cost $c(k)$), `sybil-resistance-mechanisms.md` (proof-of-personhood, stake-based identity)

---

## 1. Introduction

A recurring critique of sybil vulnerability analysis in agent-populated markets is that it overstates the threat by underweighting the protective role of Know Your Customer (KYC) and identity verification regimes. The critique is well-founded for a specific subset of markets: public equities, regulated derivatives exchanges, banking, and insurance markets all require human-provable identity as a precondition for participation. In these markets, the cost of creating sybil identities — our $c(k)$ function — is not merely high; it is anchored to the cost of recruiting and maintaining actual human participants, each with verifiable government-issued identification, residential addresses, and (in many jurisdictions) biometric data.

This protection is real and substantial *today*. An autonomous agent cannot open a brokerage account at Interactive Brokers, submit a Form U4 to FINRA, or pass the photo-ID verification step of a European MiFID II onboarding process. The sybil surface in these markets is, accordingly, much smaller than in permissionless environments like cryptocurrency DEXs or unregulated prediction markets.

But the protection is eroding. The erosion follows a predictable trajectory — from human-as-principal to human-as-pass-through — and the economics of each stage can be formalized. This deep dive traces that trajectory, models how the identity cost function $c(k)$ degrades at each stage, examines historical precedent in corporate identity evasion, and assesses the regulatory response options available. The central finding is that strong KYC buys time, but not indefinitely, and the taxonomy's sybil vulnerability claims should be explicitly qualified as KYC-regime-dependent.

---

## 2. Current State of KYC Protection

### 2.1 Markets with Strong Human Identity Requirements

The most heavily regulated financial markets impose identity verification regimes that are, by historical standards, quite robust:

**Public equities (US).** Opening a brokerage account requires a Social Security Number, government-issued photo ID, and residential address verification. FINRA Rule 2090 (Know Your Customer) and SEC Rule 17a-8 impose ongoing obligations on broker-dealers to verify customer identity and maintain accurate records. The Customer Identification Program (CIP) requirements under the USA PATRIOT Act (Section 326) mandate that financial institutions verify identity using documentary or non-documentary methods (FinCEN 2003).

**Regulated derivatives and futures.** The CFTC requires registration and identity verification for all participants exceeding speculative position limits. The CME, ICE, and other designated contract markets maintain independent KYC processes. Algorithmic traders must additionally register under Regulation AT (proposed) or comply with pre-existing market access rules (SEC Rule 15c3-5).

**European markets under MiFID II.** The Markets in Financial Instruments Directive II (2014/65/EU) imposes identity verification, suitability assessment, and transaction reporting obligations. The Anti-Money Laundering Directives (AMLD4, AMLD5, AMLD6) further require beneficial ownership identification for all accounts.

**Banking and insurance.** Basel III's Pillar 3 disclosure requirements and national banking regulators (OCC, PRA, BaFin) maintain stringent identity verification for account holders. Insurance markets similarly require policyholder identification under state and national regulations.

### 2.2 Robustness of Current KYC

These regimes are not trivially circumvented. Key features that make them robust:

1. **Multi-factor identity verification.** Regulated entities typically require documentary evidence (passport, driver's license), non-documentary corroboration (credit bureau records, public databases), and in many cases biometric verification (photograph matching, liveness detection).

2. **Ongoing monitoring.** KYC is not a one-time gate. Suspicious Activity Reports (SARs), unusual trading pattern detection, and periodic re-verification create continuous identity pressure.

3. **Institutional liability.** Broker-dealers and banks face substantial penalties for KYC failures. FINRA enforcement actions routinely impose seven- and eight-figure fines for inadequate customer identification. This creates strong institutional incentives for genuine verification rather than perfunctory compliance.

4. **Cross-referencing.** Modern KYC systems cross-reference identities against sanctions lists (OFAC SDN), politically exposed person (PEP) databases, and adverse media screening services.

### 2.3 The Sybil Cost Function Under Strong KYC

Under a well-functioning KYC regime, the cost of creating $k$ sybil identities is:

$$c_{\text{KYC}}(k) = k \cdot (\gamma_{\text{human}} + \gamma_{\text{compliance}} + \gamma_{\text{ongoing}})$$

where:
- $\gamma_{\text{human}}$ is the cost of recruiting an actual human willing to lend their identity (or creating a synthetic identity robust enough to survive verification — extremely difficult under current regimes)
- $\gamma_{\text{compliance}}$ is the cost of passing the initial KYC onboarding process (time, documentation, fees)
- $\gamma_{\text{ongoing}}$ is the annualized cost of maintaining the identity under ongoing monitoring (responding to verification requests, managing SAR triggers)

Crucially, $\gamma_{\text{human}}$ is large and scales roughly linearly with $k$. You cannot trivially "copy" a human. Each additional identity requires a distinct person with a distinct government ID. For an agent seeking to create 100 sybil accounts at regulated US brokerages, the cost involves recruiting 100 humans, each willing to undergo identity verification and maintain an ongoing relationship with a regulated entity — a logistically and legally formidable undertaking.

### 2.4 Markets with Weak or Absent KYC

Not all markets enjoy this protection. The sybil surface is dramatically larger where KYC is weak:

- **Cryptocurrency DEXs** (Uniswap, SushiSwap, Curve): Participation requires only a blockchain address. Identity cost $c(k) \approx k \cdot \epsilon$ where $\epsilon$ is the negligible cost of generating a new wallet.
- **Unregulated prediction markets** (some Polymarket configurations, decentralized prediction protocols): Pseudonymous participation with no identity verification.
- **DeFi lending protocols** (Aave, Compound): Overcollateralized lending requires no identity. Undercollateralized ("credit") DeFi is emerging but remains small.
- **NFT and digital asset markets:** Pseudonymous trading is the norm.
- **Informal labor markets and gig platforms:** Identity verification varies dramatically; many platforms have minimal KYC.

The taxonomy's sybil vulnerability claims are most immediately applicable to these low-KYC environments. But the critical question is whether the boundary between "strong KYC" and "weak KYC" markets is stable — or whether it is shifting.

---

## 3. The Erosion Trajectory

We propose a four-stage model of KYC erosion that describes the trajectory from meaningful human identity verification to nominal pass-through arrangements. The stages are defined by the degree of genuine human agency behind the KYC-verified identity.

### Stage 1: Human Uses AI as a Tool (Current Baseline)

**Description.** The human principal makes investment decisions and uses AI systems as analytical tools — screening stocks, optimizing portfolio weights, generating trade signals. The human reviews AI output, exercises judgment, and manually (or semi-automatically) executes trades. The brokerage account is opened by, operated by, and meaningfully controlled by the human whose identity is on file.

**Identity economics.** KYC is fully meaningful. The identity cost function remains:

$$c(k, S_1) = k \cdot (\gamma_{\text{human}} + \gamma_{\text{compliance}} + \gamma_{\text{ongoing}})$$

with all cost components at their full values.

**Regulatory visibility.** High. The human's trading behavior reflects human decision-making patterns (reaction times, bounded rationality, attention limitations). Surveillance systems calibrated to detect algorithmic manipulation can distinguish human-directed from algorithmic trading with reasonable accuracy.

**Detection difficulty.** Low. If a regulator investigates, the human can explain their strategy, demonstrate understanding of their positions, and provide evidence of decision-making. The connection between identity and agency is genuine.

**Prevalence (2026).** This remains the dominant mode for retail investors. The vast majority of the approximately 60 million US brokerage accounts are in Stage 1, where AI assistance (if used at all) takes the form of robo-advisory portfolio allocation or AI-assisted stock screeners.

### Stage 2: Human Delegates to AI with Oversight

**Description.** The human configures an AI agent to execute a strategy autonomously — for example, deploying a GPT-based trading agent through an API-connected brokerage. The human reviews the agent's activity periodically (daily, weekly) and retains the ability to override or shut down the agent. The human understands the broad contours of the strategy and can articulate it if questioned.

**Identity economics.** KYC remains approximately valid. The identity holder is genuinely involved, even if not directing each trade. The cost function shifts modestly:

$$c(k, S_2) = k \cdot (\gamma_{\text{human}}' + \gamma_{\text{compliance}} + \gamma_{\text{ongoing}}')$$

where $\gamma_{\text{human}}'$ is slightly lower than $\gamma_{\text{human}}$ (the human's time commitment per account is reduced, making it easier to manage multiple accounts) and $\gamma_{\text{ongoing}}'$ is slightly lower (the human can plausibly oversee several agent-operated accounts with less effort than manually trading each one).

**Regulatory visibility.** Moderate. The account's trading behavior may appear algorithmic, but regulatory frameworks for algorithmic trading already exist (SEC Rule 15c3-5, MiFID II's algorithmic trading provisions). The human can still demonstrate a principal-agent relationship with genuine oversight.

**Detection difficulty.** Moderate. A regulator can verify that the human understands the strategy and exercises oversight. But the boundary between "oversight" and "rubber-stamping" is subjective and hard to test.

**Prevalence (2026).** Growing rapidly. API-connected trading bots, AI portfolio managers, and delegated execution services are proliferating. Platforms like Alpaca, QuantConnect, and various crypto trading bot services facilitate Stage 2 arrangements.

### Stage 3: AI Operates Autonomously, Human Provides Nominal Oversight

**Description.** The AI agent operates with full autonomy. The human identity holder has a nominal oversight role — perhaps receiving periodic reports they do not meaningfully review, or having a theoretical ability to intervene that they never exercise. The human may not understand the agent's strategy in any detail. They opened the account and provided their identity; the agent does the rest.

**Identity economics.** KYC is significantly degraded. The key insight is that $\gamma_{\text{human}}'$ drops substantially because the human's per-account time commitment approaches zero:

$$c(k, S_3) = k \cdot (\gamma_{\text{human}}'' + \gamma_{\text{compliance}} + \gamma_{\text{ongoing}}'')$$

where $\gamma_{\text{human}}''$ reflects only the initial recruitment cost (persuading the human to open the account) and $\gamma_{\text{ongoing}}''$ reflects the cost of maintaining minimal human engagement (periodic check-ins to prevent account closure for inactivity, responding to occasional compliance inquiries).

A single human could plausibly serve as the nominal identity holder for multiple accounts across multiple brokerages, reducing the effective per-identity cost further if the same human is reused.

**Regulatory visibility.** Low. From the brokerage's perspective, the account is operated by its verified identity holder. The trading behavior is algorithmic, but algorithmic trading is legal. The absence of meaningful human oversight is invisible to standard surveillance unless regulators specifically probe the human's understanding and involvement.

**Detection difficulty.** High. The human is on record, can be contacted, and technically has access to the account. Proving that their oversight is nominal rather than genuine requires intrusive investigation — interviewing the human, testing their understanding, analyzing their login patterns. This is resource-intensive and does not scale.

**Prevalence (2026).** Emerging. The infrastructure for Stage 3 exists (autonomous agent frameworks, API-connected brokerages), and the economic incentives are strong (human oversight is a bottleneck to scaling). Quantifying prevalence is difficult precisely because Stage 3 is designed to be indistinguishable from Stage 2 to external observers.

### Stage 4: Human as "Meat Puppet"

**Description.** Humans are recruited specifically and solely for their identity credentials. They have no knowledge of, interest in, or control over the trading strategy. The agent (or the agent's principal) pays the human a fee for the use of their identity — effectively renting their KYC status. The human completes the onboarding process as directed, provides credentials to the agent operator, and is otherwise uninvolved. The term "meat puppet" (crude but descriptively accurate) captures the dynamic: the human is a biological appendage required by regulatory architecture, not a genuine market participant.

**Identity economics.** The cost function collapses:

$$c(k, S_4) = k \cdot (\gamma_{\text{rental}} + \gamma_{\text{compliance}})$$

where $\gamma_{\text{rental}}$ is the price of renting a human identity — a market price determined by supply and demand for identity credentials. In a gig economy already accustomed to selling attention (paid surveys), data (DNA testing kits), and labor time (microtasks), identity rental is a natural extension. $\gamma_{\text{compliance}}$ remains nonzero (the human still must physically complete KYC) but can be streamlined with scripts and coaching.

The critical economic point: $\gamma_{\text{rental}}$ could be quite low. If identity rental becomes a gig-economy service — "earn $200/month by lending your identity to a trading algorithm" — the supply of willing humans is potentially large, especially among populations with limited alternative income sources. The effective $c(k)$ under Stage 4 may be one to two orders of magnitude lower than under Stage 1.

**Regulatory visibility.** Very low. The KYC records show a real human with a real identity. The account was opened through the standard process. Only behavioral analysis and pattern detection — correlating multiple accounts operated by the same algorithm, detecting implausible trading sophistication from the identity holder's profile — offer detection avenues.

**Detection difficulty.** Very high. This is the fundamental asymmetry: verifying that a person *is* who they claim to be (the traditional KYC problem) is much easier than verifying that a person *controls* what they claim to control (the agency-verification problem). KYC was designed for the former. The latter requires ongoing behavioral monitoring at a scale that current regulatory infrastructure does not support.

**Prevalence (2026).** Speculative but not hypothetical. Identity-rental markets already exist in the cryptocurrency space, where "KYC'd accounts" on centralized exchanges are bought and sold on darknet markets and Telegram channels. The extension to regulated financial markets is a matter of economic incentive and enforcement deterrence, not technical feasibility.

---

## 4. The Identity Cost Function Under Erosion

### 4.1 Formal Model

Let $c(k, s)$ denote the cost of establishing $k$ sybil identities at erosion stage $s \in \{S_1, S_2, S_3, S_4\}$. We decompose this as:

$$c(k, s) = k \cdot \left[\alpha(s) \cdot \gamma_{\text{human}} + \gamma_{\text{compliance}} + \beta(s) \cdot \gamma_{\text{ongoing}}\right]$$

where $\alpha(s) \in [0, 1]$ is the *agency weight* — the fraction of full human agency cost required at stage $s$ — and $\beta(s) \in [0, 1]$ is the *monitoring weight* — the fraction of full ongoing compliance cost that applies.

| Stage | $\alpha(s)$ | $\beta(s)$ | Interpretation |
|-------|-------------|------------|----------------|
| $S_1$ | 1.0 | 1.0 | Full human agency, full monitoring burden |
| $S_2$ | 0.7 | 0.8 | Reduced time commitment, slightly lower monitoring |
| $S_3$ | 0.2 | 0.3 | Nominal human involvement, minimal monitoring response |
| $S_4$ | $\rho$ | 0.1 | Identity rental at market price $\rho \cdot \gamma_{\text{human}}$ |

The parameter $\rho$ in Stage 4 represents the ratio of identity rental cost to full human agency cost. If $\gamma_{\text{human}} = \$5{,}000$/year (a rough estimate for the opportunity cost and risk premium of personally operating a brokerage account) and $\gamma_{\text{rental}} = \$200$/month, then $\rho \approx 0.48$. But in an efficient identity-rental market with large supply, $\rho$ could fall to $0.05$–$0.15$, representing rental fees of $\$25$–$\$75$/month.

### 4.2 Discontinuous Drops

A key feature of this model is that $c(k, s)$ does not degrade smoothly. The transitions between stages involve qualitative shifts in the human-agent relationship that produce step-function drops in identity cost:

- **$S_1 \to S_2$:** The human stops executing trades personally. This is a behavioral shift but not a regulatory one — algorithmic trading is legal. The cost drop is modest.
- **$S_2 \to S_3$:** The human stops meaningfully overseeing the agent. This is the critical transition. It is invisible to KYC systems (no account change is required) but transforms the identity from a genuine control relationship into a nominal one. The cost drop is large because a single human can now nominally oversee many accounts.
- **$S_3 \to S_4$:** The human is explicitly recruited as an identity provider rather than evolving into the role. This introduces a market mechanism (identity rental pricing) that drives costs toward competitive equilibrium. The cost drop is moderate in absolute terms but represents a qualitative shift: identity becomes a commodity input rather than a constraint.

### 4.3 Scaling Implications

The critical scaling question is: at what stage does $c(k, s)$ become low enough that sybil strategies become profitable?

Define the sybil profit condition as $\Pi_{\text{sybil}}(k) > c(k, s)$, where $\Pi_{\text{sybil}}(k)$ is the expected profit from operating $k$ coordinated identities (through information manipulation, market manipulation, auction-theoretic advantages, etc., as formalized in the assumption taxonomy).

Under Stage 1, $c(k, S_1)$ is high enough that $\Pi_{\text{sybil}}(k) > c(k, S_1)$ only for very high-value manipulation targets (e.g., large-cap stock manipulation, which is separately constrained by capital requirements and market depth). Under Stage 4, $c(k, S_4)$ may be low enough that sybil strategies become profitable in a wide range of markets — including mid-cap equities, options markets, and prediction markets that have adopted KYC.

---

## 5. Precedent: Shell Companies and Nominee Directors

The trajectory from genuine identity to pass-through identity is not novel. Corporate identity has traversed a similar path, and the historical record is instructive.

### 5.1 The Corporate Analogy

Corporate KYC requires identification of beneficial owners — the natural persons who ultimately own or control a legal entity. In principle, this prevents the use of shell companies as sybil identities. In practice, the system has been extensively circumvented:

- **Nominee directors and shareholders.** Corporate service providers in permissive jurisdictions supply professional nominees who serve as the named directors and shareholders of shell companies while exercising no genuine control. The beneficial owner operates the entity through nominee arrangements.
- **Layered structures.** Multiple layers of corporate entities across jurisdictions (Company A owns Company B, which owns Company C) obscure the chain of beneficial ownership. Each layer adds cost but reduces traceability.
- **Professional enablers.** Law firms, accounting firms, and corporate service providers facilitate these arrangements, providing a veneer of legitimacy (Findley, Nielson, and Sharman 2014).

### 5.2 Scale of the Problem

The Panama Papers (2016) and FinCEN Files (2020) revealed the scale of corporate identity evasion:

- The Panama Papers exposed approximately 214,000 offshore entities created by a single law firm (Mossack Fonseca), many with nominee directors and opaque ownership structures (Obermayer and Obermaier 2016).
- The FinCEN Files revealed that major global banks processed over $2 trillion in suspicious transactions over two decades, many involving shell company structures designed to obscure beneficial ownership (BuzzFeed News/ICIJ 2020).
- The UK's Companies House has been repeatedly criticized for minimal verification of company formation documents, allowing "Scottish Limited Partnerships" and similar vehicles to be used as money laundering conduits (Transparency International 2017).

### 5.3 Regulatory Response Timeline

The regulatory response to corporate identity evasion has been slow:

- **1970:** Bank Secrecy Act establishes basic financial institution reporting requirements.
- **2001:** USA PATRIOT Act strengthens CIP requirements but focuses on individual, not corporate, identity.
- **2016:** Panama Papers revelations. Public pressure intensifies.
- **2020:** Anti-Money Laundering Act of 2020 requires beneficial ownership reporting.
- **2021:** Corporate Transparency Act passed, creating a beneficial ownership database at FinCEN.
- **2024:** Beneficial ownership reporting requirements take effect for most entities.
- **Timeline: approximately 50 years** from the initial problem to a comprehensive (though still incomplete) regulatory response.

### 5.4 Lessons for AI Identity Erosion

The corporate analogy suggests several conclusions:

1. **Regulatory response will lag the problem.** Decades elapsed between the proliferation of nominee director arrangements and meaningful beneficial ownership transparency requirements. AI identity erosion may proceed faster (the technology is more visible and the public discourse more active), but a multi-year lag is likely.

2. **Professional enablers will emerge.** Just as law firms and corporate service providers facilitated shell company arrangements, intermediaries will emerge to facilitate identity-rental arrangements for AI agents. Some already exist in the crypto space.

3. **Detection is harder than prevention.** It was easier to require beneficial ownership disclosure prospectively than to unwind decades of layered shell company structures retroactively. Similarly, it will be easier to impose "meaningful control" requirements before Stage 3/4 arrangements proliferate than to detect and unwind them after the fact.

4. **The regulatory asymmetry favors evasion.** Regulators must verify the genuine agency of every KYC-verified identity holder. Evaders need only ensure that their arrangements are not among the small fraction that regulators can investigate in depth. This is a needle-in-a-haystack problem that worsens as the number of agent-operated accounts grows.

---

## 6. Regulatory Response Options

### 6.1 Meaningful Control Requirements

The most direct regulatory response to KYC erosion is to supplement identity verification with *agency verification* — requiring that the KYC-identified human demonstrate meaningful control over account activity.

**Possible mechanisms:**
- **Periodic competence testing.** Requiring account holders to demonstrate understanding of their positions and strategy — e.g., answering questions about their current holdings, explaining recent trades, or articulating their investment thesis.
- **Interaction pattern analysis.** Monitoring login frequency, session duration, and interaction patterns to detect accounts where the human identity holder rarely engages with the account directly.
- **Decision point verification.** Requiring human confirmation for trades above certain thresholds or with certain risk profiles, with verification that the confirmation comes from an informed human rather than an automated pass-through.

**Limitations.** Meaningful control requirements are costly to administer and intrusive to legitimate users. A human who delegates to a well-understood robo-advisor (a fully legal Stage 2 arrangement) might fail a competence test about individual positions. The boundary between legitimate delegation and nominal oversight is inherently fuzzy, and any bright-line rule will produce both false positives (legitimate delegators flagged) and false negatives (sophisticated pass-throughs that game the test).

### 6.2 Behavioral Analysis and Anomaly Detection

Rather than testing human agency directly, regulators could infer it from account behavior:

- **Coordination detection.** Identifying clusters of accounts that trade in suspiciously correlated patterns, suggesting common algorithmic control. This is an extension of existing market manipulation surveillance (e.g., spoofing and layering detection) to the multi-account case.
- **Behavioral biometrics.** Analyzing typing patterns, mouse movements, and session behavior to distinguish human from automated interaction. This is already deployed in fraud prevention but would need to be adapted for the specific challenge of detecting pass-through arrangements.
- **Profile-behavior mismatch.** Flagging accounts where the sophistication, frequency, or style of trading activity is inconsistent with the identity holder's profile (e.g., a retiree with no financial background executing complex options strategies at millisecond intervals).

**Limitations.** Behavioral analysis faces an adversarial dynamic. As detection capabilities improve, agents (and their human facilitators) will adapt — introducing artificial behavioral noise, varying trading patterns, and mimicking human interaction styles. The arms race between detection and evasion is unlikely to be won decisively by either side, but the cost of detection scales with the number of accounts monitored while the cost of evasion scales more favorably for the evader (Douceur 2002).

### 6.3 Liability Frameworks

A complementary approach shifts the incentive structure rather than the detection capability:

- **Strict liability for KYC identity holders.** Making the human whose identity is on the account strictly liable for all trading activity conducted through that account, regardless of whether they directed it. This raises the effective cost of identity rental by increasing the risk premium $\gamma_{\text{rental}}$ that identity providers demand.
- **Aiding and abetting liability.** Extending criminal liability for market manipulation to identity providers who knowingly lend their credentials to autonomous agents engaged in manipulative strategies.
- **Platform liability.** Imposing obligations on brokerages and exchanges to detect and prevent pass-through arrangements, analogous to the due diligence obligations imposed by AML regulations.

**Limitations.** Liability frameworks work best when the liable party is identifiable and solvent. In a Stage 4 arrangement, the identity provider may be a low-income individual recruited precisely because they have little to lose from liability. Criminal penalties create stronger deterrence but require proving knowledge and intent, which is difficult when the identity provider genuinely does not understand what the agent is doing.

### 6.4 Enforcement Cost Scaling

The fundamental challenge across all regulatory responses is that enforcement cost scales unfavorably:

$$C_{\text{enforce}}(n) = n \cdot \delta_{\text{investigate}} \cdot p_{\text{investigate}}$$

where $n$ is the number of agent-operated accounts, $\delta_{\text{investigate}}$ is the per-account investigation cost, and $p_{\text{investigate}}$ is the probability that any given account is investigated. As $n$ grows (with the proliferation of AI agents), regulators face a choice between increasing total enforcement expenditure (politically constrained) and decreasing $p_{\text{investigate}}$ (reducing deterrence). This is the standard regulatory scaling problem, but it is exacerbated by the difficulty of distinguishing legitimate from illegitimate human-agent arrangements.

---

## 7. Implications for the Taxonomy

### 7.1 Claims Requiring Qualification

Several claims in the assumption taxonomy should be qualified with reference to the KYC regime:

1. **Sybil cost claims.** Statements about low identity creation cost — e.g., "$c(k)$ scales linearly with $k$ at low per-unit cost" — are accurate for permissionless markets but should be qualified: "In markets lacking human-provable identity requirements, $c(k)$ scales linearly..." or "Under current KYC regimes, $c(k)$ is anchored to human recruitment costs, but this anchor weakens along the erosion trajectory described in [this document]."

2. **Market manipulation vulnerability.** Claims about coordinated multi-identity manipulation strategies should specify the KYC regime under which they become feasible. In strong-KYC markets, such strategies face substantially higher barriers than in permissionless environments.

3. **Sybil equilibrium analysis.** Equilibrium results that depend on low $c(k)$ (e.g., sybil flooding of prediction markets, collusive bidding in auctions) should include sensitivity analysis showing how outcomes change as $c(k)$ varies across the erosion trajectory.

### 7.2 Claims That Hold Even Under Strong KYC

Importantly, many of the taxonomy's core claims are robust to strong KYC:

- **Elastic labor supply.** AI agents operating under legitimate, KYC-verified accounts still represent elastic labor supply. A single human with a single verified account can delegate to an agent that operates 24/7, outperforming human attention constraints. This requires no sybil identities.
- **Speed advantages.** Algorithmic speed in execution, analysis, and reaction requires only a single verified account. KYC does not constrain speed.
- **Correlated strategies.** Even without sybil identities, many agents independently adopting correlated strategies (herding) can produce systemic risk. This is a population-level phenomenon that does not require multi-identity coordination.
- **Principal-agent problems.** The alignment challenges between a human principal and an AI agent exist within a single verified account and are orthogonal to sybil concerns.

### 7.3 Timeline Assessment

How fast is each stage of erosion progressing?

- **Stage 1 $\to$ Stage 2:** Already well underway. API-connected trading, robo-advisors, and AI-assisted portfolio management are mainstream. Timeline: largely complete by 2025.
- **Stage 2 $\to$ Stage 3:** Accelerating. As agent capabilities improve and autonomous operation becomes more reliable, the economic incentive to reduce human oversight increases. Timeline: significant prevalence expected by 2027–2029.
- **Stage 3 $\to$ Stage 4:** Speculative. Requires the emergence of identity-rental markets at scale, which depends on enforcement deterrence and social norms. Already present in crypto markets; extension to regulated markets depends on regulatory response speed. Timeline: potentially 2028–2032 for meaningful prevalence.

These estimates are highly uncertain and depend on the pace of regulatory adaptation. Aggressive early regulation (meaningful control requirements, behavioral monitoring) could delay Stage 3 and Stage 4 significantly. Regulatory inaction or capture could accelerate the timeline.

### 7.4 Recommendation

The taxonomy should adopt an explicitly **KYC-regime-dependent** framing for sybil vulnerability:

> *Sybil vulnerability varies dramatically across market microstructures. In markets with no identity requirements (permissionless blockchains, unregulated platforms), the sybil cost function $c(k)$ is negligible. In markets with strong KYC (regulated exchanges, banking), $c(k)$ is anchored to human recruitment and maintenance costs — currently high, but subject to erosion as agent autonomy increases. The erosion trajectory from tool-use (Stage 1) through delegation (Stage 2) to nominal oversight (Stage 3) and identity rental (Stage 4) progressively decouples identity cost from genuine human agency, and the sybil surface expands accordingly.*

This framing acknowledges the PI's valid critique while preserving the taxonomy's analytical framework and extending it to capture the dynamic erosion process.

---

## 8. Conclusion

Strong KYC requirements in regulated financial markets provide substantial — and currently effective — protection against sybil attacks by autonomous agents. The identity cost function $c(k)$ in these markets is anchored to the cost of recruiting and maintaining actual human participants, which is orders of magnitude higher than in permissionless environments.

But this protection is not permanent. The trajectory from human-as-principal (Stage 1) through human-as-delegator (Stage 2) to human-as-rubber-stamp (Stage 3) and human-as-meat-puppet (Stage 4) is economically rational for any principal seeking to scale agent operations across multiple identities. Each stage transition reduces the effective identity cost $c(k, s)$ while maintaining formal compliance with KYC requirements. The transition from Stage 2 to Stage 3 is particularly dangerous because it is invisible to standard KYC processes — no account change is required, and the degradation of human oversight leaves no documentary trace.

Historical precedent from corporate identity evasion (shell companies, nominee directors, the Panama Papers revelations) confirms that regulatory response to identity erosion is typically slow — measured in decades rather than years. The AI version may provoke faster response given greater public salience, but a meaningful regulatory lag is likely.

Regulatory countermeasures — meaningful control requirements, behavioral analysis, liability frameworks — face a fundamental asymmetry: verification of genuine human agency is costly and does not scale, while maintaining a facade of human involvement is cheap and does scale. This asymmetry favors the erosion trajectory.

For the taxonomy, the implication is clear: sybil vulnerability claims should be framed as KYC-regime-dependent, with explicit acknowledgment that strong KYC currently provides robust protection in regulated markets. But that framing should also note that the protection is time-bounded, and the erosion trajectory is well underway. The question is not *whether* KYC protection will erode, but *how fast* — and whether regulatory adaptation can maintain the identity cost anchor against the economic forces driving it downward.

---

## References

- BuzzFeed News / ICIJ (2020). "The FinCEN Files." International Consortium of Investigative Journalists.
- Douceur, J. R. (2002). "The Sybil Attack." *Proceedings of the 1st International Workshop on Peer-to-Peer Systems (IPTPS '02)*, pp. 251–260.
- European Parliament and Council (2014). Directive 2014/65/EU (MiFID II).
- FinCEN (2003). "Customer Identification Programs for Banks, Savings Associations, Credit Unions, and Certain Non-Federally Regulated Banks." 31 CFR Part 103.
- Findley, M., Nielson, D., and Sharman, J. (2014). *Global Shell Games: Experiments in Transnational Relations, Crime, and Terrorism.* Cambridge University Press.
- FINRA Rule 2090: Know Your Customer.
- Obermayer, B. and Obermaier, F. (2016). *The Panama Papers: Breaking the Story of How the Rich and Powerful Hide Their Money.* Oneworld Publications.
- SEC Rule 15c3-5: Market Access Rule.
- SEC Rule 17a-8: Financial Recordkeeping and Reporting of Currency and Foreign Transactions.
- Transparency International UK (2017). "Hiding in Plain Sight: How UK Companies Are Used to Launder Corrupt Wealth."
- U.S. Congress (2020). Anti-Money Laundering Act of 2020 (Title LXI of the National Defense Authorization Act).
- U.S. Congress (2021). Corporate Transparency Act, 31 U.S.C. 5336.
- USA PATRIOT Act (2001), Section 326: Verification of Identification.
