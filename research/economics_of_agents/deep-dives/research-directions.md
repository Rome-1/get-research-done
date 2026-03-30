# Next Research Directions: Deep Dives

Five research programs extending the core taxonomy. Each follows: hypothesis → method → justification → claim.

---

## 1. Monetary Velocity Spirals Under Agent-Speed Transactions

### Hypothesis

When autonomous AI agents execute transactions at machine speed, monetary velocity (V in MV=PQ) becomes endogenous to agent deployment density, creating feedback loops that destabilize price levels independently of central bank money supply interventions. Specifically: there exists a critical agent density threshold above which velocity growth becomes self-reinforcing, producing either runaway inflation or deflationary spirals depending on the elasticity of real output Q.

### Method

**Agent-based simulation** of a monetary economy with heterogeneous transaction speeds.

1. Implement a simplified economy with N human agents (transaction speed ~1/day) and M AI agents (transaction speed ~1000/s). Both hold money balances and transact for goods/services.
2. Money supply M is fixed (exogenous, as if the central bank is static). Real output Q grows according to a logistic function of productive investment.
3. Sweep agent density M/N from 0 to 100 and measure: (a) realized velocity V = PQ/M, (b) price level stability (coefficient of variation of P over time), (c) time to equilibrium (if one exists).
4. Introduce a reactive central bank (Taylor rule on P) and measure whether conventional policy tools can stabilize prices when V is endogenous.
5. Calibrate against DeFi empirical data: flash loan volumes on Aave/Compound provide real-world velocity measurements for agent-dominated markets.

**Validation criteria:** The simulation must reproduce known results (stable velocity under human-only agents, Fisher equation holds) before introducing AI agents.

### Justification

This is the **only one of the five capability classes** (identity, replication, speed, correlation, endogenous preferences) with no computational evidence in our research program. The taxonomy rates "Quantity Theory of Money" as High severity but the claim rests entirely on analytical argument. Meanwhile, DeFi markets already exhibit the predicted phenomenon: flash loans execute borrow→trade→repay in a single block (~12s), producing effective velocity orders of magnitude above traditional finance. The gap between our theoretical claim and empirical reality is the single largest vulnerability in the paper.

More broadly, monetary velocity is a macroeconomic variable that central banks monitor but assume is approximately stable (the basis for inflation targeting). If AI agents make V volatile and endogenous, the policy implications are immediate and significant — this is the most policy-relevant finding we could produce.

### Claim (if hypothesis confirmed)

Conventional monetary policy (interest rate targeting, quantitative easing) loses effectiveness when autonomous agents make velocity endogenous. Price stability requires direct regulation of agent transaction frequency or computational capacity — a novel policy instrument with no precedent in central banking.

---

## 2. Empirical Identity Cost Functions Across Platform Markets

### Hypothesis

The marginal cost of creating an additional credible identity c_marginal(k) varies by 3-4 orders of magnitude across platform types, and the relationship between c_marginal and exploitable surplus determines which markets are already vulnerable to AI sybil attacks vs. which will become vulnerable as identity costs fall. Specifically: markets where c_marginal < expected_surplus_per_identity are currently exploitable, and the frontier is moving as AI-generated credentials become cheaper.

### Method

**Empirical measurement** combined with **economic modeling.**

1. For each of 8-10 platform categories (freelance labor, prediction markets, governance/DAOs, ad auctions, ride-sharing, social media, academic peer review, financial markets), estimate:
   - c_0: fixed cost of first identity (account creation, KYC if required)
   - c_marginal(k): marginal cost of k-th identity (phone number, ID document, biometric, reputation history)
   - c_coordination(k): coordination cost of operating k identities simultaneously
   - S(k): expected surplus extractable with k identities (from our simulation results where available)
2. Construct the vulnerability curve: for each platform, plot c(k) vs. S(k) and identify the critical k* where S(k*) > c(k*) (attack becomes profitable).
3. Model the time trajectory of c_marginal under technological change: AI-generated documents, deepfake biometrics, synthetic reputation histories. Estimate when currently-safe markets cross the vulnerability threshold.
4. Validate against known cases: documented sybil attacks on Gitcoin Grants (~$30-50 iris scan bribes), wash trading on NFT platforms, bot farms on social media.

### Justification

The identity cost function c(k) is the **theoretical spine** of the entire taxonomy — every severity rating depends on it. But we currently have scattered anecdotes ($30-50 for Worldcoin iris bribes, ~$5 for phone number verification) rather than systematic estimates. This is acknowledged as a gap in the final proof review. Without grounded c(k) estimates, our severity ratings are educated guesses rather than quantitative assessments.

The economic framing (vulnerability = when surplus exceeds cost) is standard in security economics (Anderson 2001, "Why Information Security is Hard") but has never been applied systematically to sybil attacks across platform types. This would be the first cross-market empirical study of identity economics.

### Claim (if hypothesis confirmed)

Identity cost is the single variable that determines whether a market mechanism remains robust under AI agent participation. We provide the first empirical measurement of this variable across market types, enabling platform designers to assess their sybil vulnerability quantitatively and invest in identity infrastructure proportional to at-risk surplus.

---

## 3. Impossibility of Sybil-Proof Efficient Mechanisms (Trilemma Formalization)

### Hypothesis

No mechanism can simultaneously satisfy: (1) sybil-proofness (no agent benefits from creating additional identities), (2) allocative efficiency (Pareto-optimal allocation), and (3) individual rationality (no agent is worse off participating than abstaining). This is a fundamental impossibility result analogous to the Myerson-Satterthwaite theorem, but for the identity dimension rather than the information dimension.

### Method

**Formal proof** (mechanism design theory).

1. Define sybil-proofness formally: for all agents i, for all identity-splitting strategies σ where i operates as {i₁, i₂, ..., iₖ}, u_i(σ) ≤ u_i(truthful). This extends Yokoo et al.'s (2004) false-name-proofness to general mechanisms.
2. Prove the impossibility by construction: assume a mechanism satisfying all three properties exists, then show a contradiction by constructing an agent who can profit from identity-splitting.
3. The key technical step: show that any efficient mechanism must have payments that depend on the *set of other participants* (VCG-style externality pricing), and that any such payment rule creates profitable identity-splitting opportunities when c_marginal < payment_sensitivity_to_agent_set.
4. Characterize the Pareto frontier: for each pair of the three properties, what is the best achievable mechanism? (a) Sybil-proof + efficient but not IR: forced participation with identity bonds. (b) Sybil-proof + IR but not efficient: posted-price mechanisms (no externality pricing). (c) Efficient + IR but not sybil-proof: standard VCG.
5. Identify the critical cost threshold c* below which the impossibility bites. Above c*, standard mechanisms suffice; below c*, designers must choose which property to sacrifice.

### Justification

Our VCG analysis (vcg-sybil-extraction.md) already contains the pieces: Proposition 1 shows single-item Vickrey is NOT directly vulnerable (surprising), Proposition 2 shows multi-unit VCG IS vulnerable, and we conjecture the trilemma. But the conjecture is stated informally and the proof is incomplete. Formalizing this would be a **first-order contribution to mechanism design theory** — it would stand alongside Myerson-Satterthwaite and the Gibbard-Satterthwaite theorem as a fundamental impossibility result.

The practical significance is enormous: every auction platform, governance system, and matching market must implicitly choose which of the three properties to sacrifice. Currently this choice is made ad hoc. A formal impossibility result would provide principled guidance.

### Claim (if hypothesis confirmed)

The sybil-proof mechanism design trilemma: no mechanism achieves sybil-proofness, allocative efficiency, and individual rationality simultaneously when marginal identity cost falls below a mechanism-specific threshold c*. This provides a theoretical foundation for the observation that all real-world mechanisms sacrifice one property: proof-of-stake sacrifices IR (capital lockup), quadratic voting sacrifices sybil-proofness, and posted-price mechanisms sacrifice efficiency.

---

## 4. Algorithmic Collusion Phase Transitions Under Architectural Correlation

### Hypothesis

When AI agents in a repeated oligopoly game share architectural priors (same training data, same model family, same reward signal structure), they converge to supra-competitive pricing without explicit communication or intent, and this convergence exhibits a **sharp phase transition** as a function of architectural correlation ρ. Below ρ_critical, competitive pricing obtains; above ρ_critical, tacit collusion emerges. The critical finding: ρ_critical < 1.0 means even near-identical agents can avoid collusion with sufficient architectural diversity, while ρ = 1.0 (identical agents) guarantees collusion regardless of market structure.

### Method

**Formal game theory** combined with **computational experiments.**

1. Extend our Bertrand simulation (collusion_bertrand.py) which already found the phase transition at ρ=1.0. The current implementation uses Q-learning agents — extend to:
   - Policy gradient agents (different learning dynamics)
   - Transformer-based agents (realistic architecture)
   - Mixture: some Q-learning, some policy gradient (heterogeneous population)
2. Formalize the notion of "architectural correlation" ρ. Candidate formalizations:
   - CKA similarity of learned Q-functions after convergence
   - Mutual information between agents' action distributions
   - Correlation of gradient directions during learning
3. Prove (or provide strong computational evidence for) the phase transition theorem: for repeated Bertrand competition with N ≥ 2 agents, there exists ρ* ∈ (0,1) such that for ρ > ρ*, the unique stable outcome is supra-competitive pricing, and for ρ < ρ*, competitive pricing is stable.
4. Characterize how ρ* depends on: number of agents N, discount factor δ, market concentration (HHI), and learning algorithm.
5. Policy experiment: simulate a regulator mandating architectural diversity (ρ < ρ_max) and measure welfare effects.

### Justification

The existing simulation result — phase transition at ρ=1.0, with "even slight diversity (ρ=0.9) prevents collusion" — is potentially a **major finding for competition policy**. Current antitrust law requires evidence of communication or agreement to establish collusion. Algorithmic collusion through shared architecture evades this entirely. If we can formalize the conditions under which it arises and show that architectural diversity prevents it, we provide regulators with a concrete, implementable intervention (mandate model diversity in pricing algorithms).

Calvano et al. (2020, AER) showed Q-learning agents converge to supra-competitive pricing, but didn't investigate the role of architectural correlation. Our contribution is identifying correlation as the control variable and showing it has a phase transition — this is what makes the result actionable rather than merely concerning.

### Claim (if hypothesis confirmed)

Algorithmic collusion is not an inevitable consequence of AI pricing agents — it is a consequence of architectural monoculture. Regulators can prevent tacit collusion by mandating sufficient architectural diversity (ρ < ρ*) among competing firms' pricing algorithms, without restricting algorithmic pricing itself. This reframes the regulatory question from "should we allow algorithmic pricing?" to "how diverse must pricing algorithms be?"

---

## 5. Net Effect Synthesis: When Do AI Agents Help vs. Harm Economic Systems?

### Hypothesis

The net effect of AI agent participation in economic systems is determined by four interacting conditions: (1) identity cost regime (high → positive, low → negative), (2) agent diversity (diverse → positive, monoculture → negative), (3) market structure (competitive → positive, concentrated → negative), and (4) regulatory adaptation speed (fast → positive, slow → negative). There exist identifiable "safe zones" in this 4D parameter space where AI agents unambiguously improve welfare, and "danger zones" where they unambiguously harm it. Most real-world markets are currently in an intermediate zone where the net effect depends on the specific combination of conditions.

### Method

**Theoretical synthesis** combined with **meta-analysis of simulation results.**

1. Formalize a welfare function W(c, ρ, H, r) where c = identity cost, ρ = architectural correlation, H = Herfindahl index, r = regulatory adaptation speed.
2. From our existing work, populate the parameter space:
   - Auction simulation: W as a function of c (identity cost) — extract the surplus curves
   - Governance simulation: W as a function of c and mechanism type
   - Labor simulation: W as a function of AI supply elasticity (related to c via replication cost)
   - Collusion simulation: W as a function of ρ (correlation)
3. Identify the boundaries: for each 2D slice of the parameter space, find the zero-crossing of W (where AI agents switch from net positive to net negative).
4. Resolve the internal tension flagged in the final proof review: positive-sum-effects.md claims diversity is crucial for positive outcomes, prediction-markets.md argues monoculture is emerging. The synthesis must either:
   - Show these are about different market types (both can be true)
   - Show one is wrong (and correct it)
   - Show the tension is the key finding (the trajectory from diversity to monoculture is the path from positive to negative net effect)
5. Map real-world markets onto the parameter space to assess where we currently are and where we're heading.

### Justification

This is the **headline question** for any policy audience. "AI agents break economic assumptions" is interesting theoretically but the first question any policymaker asks is "so is this good or bad?" Our research currently gives both answers in different documents without synthesizing. The final proof review explicitly flagged this as a Notable issue: "No unified net assessment of whether net effect is positive or negative."

The synthesis also resolves the most important internal inconsistency in the research program. If we can show that the net effect depends predictably on measurable conditions, we provide actionable guidance rather than just warnings.

### Claim (if hypothesis confirmed)

AI agent participation in economic systems produces net positive welfare effects under conditions of high identity cost, architectural diversity, competitive market structure, and responsive regulation. As any of these conditions degrades, welfare effects deteriorate — and critically, the conditions interact multiplicatively: low identity cost alone is manageable, but low identity cost combined with architectural monoculture in concentrated markets produces catastrophic welfare loss. The policy implication is that interventions on any single axis (identity, diversity, market structure, regulation) are insufficient — robust positive outcomes require maintaining all four conditions simultaneously.
