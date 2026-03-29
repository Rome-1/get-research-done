# Simulation Results: Economics of AI Agents

**Date:** 2026-03-29
**Simulations:** sybil_auction.py, sybil_governance.py, labor_market.py
**Runtime:** Mesa 3.5.1, NumPy, Python 3.12

---

## 1. Sybil Auction Results

**Setup:** 20 honest traders, 2 sybil traders (5 identities each), 200 steps/run, 10 replications, identity costs swept from 0.0 to 5.0.

### Key Findings

| Identity Cost | Efficiency | Price Deviation | Honest $/agent | Sybil $/agent | Trades/step |
|:---:|:---:|:---:|:---:|:---:|:---:|
| Baseline | 0.993 (0.007) | 5.06 | 2313.33 | N/A | 4.77 |
| 0.0 | 1.205 (0.591) | 6.69 | 2358.30 | 6211.43 | 8.22 |
| 1.0 | 1.173 (0.589) | 6.69 | 2358.30 | 5411.43 | 8.22 |
| 2.5 | 1.125 (0.585) | 6.69 | 2358.30 | 4211.43 | 8.22 |
| 5.0 | 1.044 (0.579) | 6.69 | 2358.30 | 2211.43 | 8.22 |

**Price deviation rises from 5.06 (baseline) to 6.69 across all sybil conditions** -- a 32% increase. This is invariant to identity cost, meaning sybils distort prices regardless of how expensive identity is. Only their profitability changes.

**Efficiency exceeds 1.0 in all sybil conditions.** This counterintuitive result occurs because the sybil traders generate additional trade volume (8.22 trades/step vs. 4.77 baseline) that produces surplus beyond the theoretical maximum computed from honest traders alone. The sybils are not just redistributing surplus -- they are creating new transactions that would not otherwise occur. However, the high standard deviation (0.58-0.59) indicates this surplus is volatile and unevenly distributed. The "efficiency > 1.0" reflects the simulation's efficiency metric being calibrated against the honest-only maximum; once sybils participate, total realized surplus can exceed that baseline.

**Sybil surplus extraction is massive.** At zero identity cost, each sybil agent earns 6211.43 vs. 2358.30 for honest agents -- a 2.6x rent extraction ratio. Even at the highest identity cost tested (5.0), sybils still earn 2211.43 per agent, roughly on par with honest traders. **No tested identity cost made sybil participation unprofitable.**

**Honest traders are not harmed in aggregate** (2358.30 vs. 2313.33 baseline), but the additional surplus comes from inflated trade volume, not improved allocation.

---

## 2. Governance/Voting Results

**Setup:** 50 honest voters with preferences drawn over [0, 100], 1 sybil attacker (ideal point = 90.0), sybil counts from 0 to 100, identity costs swept 0.0-10.0, 50 replications per condition.

**Implementation caveat (QV).** The Quadratic Voting results below use an equilibrium-play proxy: each voter buys sqrt(budget × intensity) votes, and the outcome is the vote-weighted mean of ideal points. This captures the sqrt(k) sybil amplification from budget splitting but does not model the strategic vote-buying choice that defines QV. Results should be interpreted as measuring QV's *structural* sybil vulnerability, not its full strategic properties. A proper QV implementation where agents choose vote quantities and face quadratic costs may show different resistance characteristics.

### Sybil Resistance Comparison (identity cost = 0.0)

| Sybil Count | 1p1v Deviation | Quadratic Deviation | Conviction Deviation |
|:---:|:---:|:---:|:---:|
| 0 | 0.00 | 0.97 | 0.00 |
| 1 | 0.57 | 1.91 | 0.00 |
| 2 | 0.89 | 2.83 | 1.00 |
| 5 | 3.19 | 5.24 | 32.10 |
| 10 | 4.84 | 8.75 | 41.80 |
| 20 | 10.67 | 13.91 | 38.70 |
| 50 | 38.41 | 22.40 | 41.00 |
| 100 | 40.02 | 28.39 | 40.40 |

**1p1v** is trivially sybil-vulnerable: every additional identity shifts the outcome linearly. With 50 sybils vs. 50 honest voters, the attacker achieves a 38.41-point deviation (near-total capture). It is 100% profitable at all sybil counts when identity is free.

**Quadratic Voting** shows sub-linear scaling of attack power -- 100 sybils produce only 28.39 deviation vs. 40.02 for 1p1v. QV's quadratic cost structure partially resists sybils by spreading budget across identities. However, it is still 100% profitable at all sybil counts when identity is free, and it shows a non-zero baseline deviation (0.97) even without sybils due to the intensity-weighted mechanism.

**Conviction Voting** exhibits a threshold effect: it is fully resistant at 1 sybil (0.00 deviation, 0% profitability), partially resistant at 2 sybils (1.00 deviation, 2% profitability), then collapses catastrophically at 5 sybils (32.10 deviation, 80% profitability). Once the threshold is breached, conviction voting is as vulnerable as 1p1v. The time-locking mechanism provides strong resistance to small-scale attacks but shatters under coordinated mass identity creation.

### Critical Identity Costs (attack becomes unprofitable)

| Mechanism | 5 Sybils | 10 Sybils | 20 Sybils | 50 Sybils |
|:---:|:---:|:---:|:---:|:---:|
| 1p1v | 0.5 | 0.5 | 0.5 | 1.0 |
| Quadratic | 2.0 | 1.0 | 1.0 | 0.5 |
| Conviction | 10.0 | 5.0 | 2.0 | 1.0 |

**1p1v** requires only trivial identity cost (0.5) to deter attacks, because each identity contributes little marginal influence.

**Quadratic Voting** requires moderate identity cost (1.0-2.0) and shows an interesting pattern: the critical cost *decreases* with more sybils, because the budget must be spread thinner across more identities.

**Conviction Voting** requires very high identity cost at low sybil counts (10.0 for 5 sybils) but drops to 1.0 at 50 sybils. This reflects the threshold behavior -- small attacks are already blocked by the mechanism itself, so the identity cost merely needs to discourage the larger attacks that breach the threshold.

---

## 3. Labor Market Results

**Setup:** 100 human workers (skill levels uniformly distributed over [0,1]), 150 tasks/period, 100 periods, AI initial costs swept from 20.0 down to 0.1. AI quality improves over time.

### Aggregate Outcomes by AI Cost

| AI Initial Cost | Employment % | Mean Wage | Gini | Total Output | Phase |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 20.0 | 99.4% | 4.59 | 0.151 | 1332.6 | substitution |
| 10.0 | 85.4% | 4.54 | 0.284 | 1341.1 | substitution |
| 5.0 | 48.6% | 5.43 | 0.564 | 1348.5 | displacement |
| 2.0 | 48.3% | 5.45 | 0.565 | 1348.5 | displacement |
| 1.0 | 48.3% | 5.45 | 0.565 | 1348.5 | displacement |
| 0.5 | 48.3% | 5.45 | 0.565 | 1348.5 | displacement |
| 0.1 | 48.3% | 5.45 | 0.565 | 1348.5 | displacement |

### Three-Phase Dynamics

**Phase 1 -- Complementary (early periods):** AI handles low-skill tasks, humans specialize in higher-skill work. Both coexist. Observed in early periods across all scenarios.

**Phase 2 -- Substitution (AI cost 10.0-20.0):** AI quality improves to match mid-skill humans. Employment drops from 99.4% to 85.4% as AI begins replacing the lowest-skill workers. The transition is gradual -- the simulation shows oscillation between complementary and substitution phases around period 59-73 for high-cost AI, reflecting a contested boundary.

**Phase 3 -- Displacement (AI cost <= 5.0):** A sharp cliff. Employment collapses from 85.4% to 48.3-48.6% as AI cost crosses the 5.0 threshold. Below this point, further cost reductions produce no additional displacement -- the market has already reached its displacement equilibrium where only workers with skills above the AI quality ceiling remain employed.

**The displacement threshold is AI cost = 5.0.** Below this, outcomes are essentially identical (48.3% employment, 5.45 wage, 0.565 Gini). This suggests a binary phase transition rather than a continuous degradation.

### Wages by Skill Quintile (Final State)

| AI Cost | Q1 (lowest) | Q2 | Q3 | Q4 | Q5 (highest) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 20.0 | 3.22 | 4.13 | 4.51 | 5.09 | 6.32 |
| 10.0 | 2.96 | 1.94 | 2.60 | 5.09 | 6.32 |
| 5.0 | 0.00 | 0.00 | 1.91 | 5.09 | 6.32 |
| 2.0 | 0.00 | 0.00 | 1.91 | 5.09 | 6.32 |
| 0.1 | 0.00 | 0.00 | 1.91 | 5.09 | 6.32 |

**The bottom two quintiles are fully displaced** once AI cost falls below 5.0 (wages drop to zero). Q3 retains partial employment at a compressed wage (1.91 vs. 4.51 at high AI cost). **Q4 and Q5 are completely insulated** -- their wages (5.09 and 6.32) are unchanged across all AI cost levels. The Gini coefficient nearly quadruples from 0.151 to 0.565, reflecting an extreme polarization between employed high-skill and displaced low-skill workers.

**Mean wage paradoxically rises** from 4.59 to 5.45 during displacement because the mean is computed only over employed workers -- a survivorship bias. The displaced workers earning zero are excluded from the employed-mean calculation.

---

## 4. Theory Alignment

### Sybil Auction -- Taxonomy Claims #2, #5, #6

**Supports Claim #2 (First Welfare Theorem):** Sybil agents acting as coordinated price-makers distort prices 32% above baseline, confirming that identity multiplication breaks the price-taking assumption. However, the simulation *challenges* the pure welfare-destruction narrative -- honest traders are not harmed in aggregate, and total surplus increases. The First Welfare Theorem's efficiency guarantee fails in the specific sense that the Pareto-optimal allocation under sybil manipulation differs from the competitive equilibrium, but the realized outcome is not obviously worse for honest participants.

**Supports Claim #5 (VCG / mechanism vulnerability):** Sybil surplus extraction (2.6x at zero identity cost) confirms that splitting across identities extracts rent that the mechanism design was intended to prevent. No tested identity cost level eliminated sybil profitability, consistent with the taxonomy's prediction that as identity costs approach zero, "virtually every VCG instance becomes sybil-vulnerable."

**Challenges Claim #6 (Myerson) in degree:** The taxonomy predicts "revenue can collapse" -- but in this double auction setting, honest traders' surplus slightly *increases*. The mechanism is distorted but not destroyed. The severity may be market-structure dependent.

### Governance -- Taxonomy Claims #4, #13

**Strongly supports Claim #13 (Quadratic Voting):** QV is vulnerable at all sybil counts when identity is free, confirming the taxonomy's prediction that QV "degenerates to standard one-token-one-vote plutocracy" as identity cost approaches zero. The sub-linear scaling provides partial resistance but does not prevent exploitation.

**Supports Claim #4 (Revelation Principle) indirectly:** The conviction voting threshold effect demonstrates that mechanisms can be robust against small-scale type manipulation but fail catastrophically when the number of fake identities exceeds a critical threshold. This suggests that the revelation principle's failure is not continuous -- it has a phase-transition character.

**Novel finding on conviction voting:** The taxonomy does not specifically discuss conviction voting, but the simulation reveals it has the strongest small-scale sybil resistance (fully immune to 1 sybil) but the most catastrophic failure mode (32-point deviation at just 5 sybils). This suggests a fourth mechanism design principle: threshold resistance mechanisms may be preferable when identity cost is high enough to keep attacks below the threshold, but are dangerous when identity becomes cheap.

### Labor Market -- Taxonomy Claim #11

**Strongly supports Claim #11 (Labor Market Clearing):** The simulation directly confirms the taxonomy's prediction that "market clearing wage for AI-substitutable tasks converges to marginal compute cost." The sharp displacement threshold at AI cost = 5.0 demonstrates the "qualitatively different" dynamics described in the elastic labor deep dive. The flat supply curve behavior is evident: below the threshold, further cost reductions produce zero marginal displacement.

**Supports the "speed of adjustment" concern:** The phase transition data shows substitution-to-displacement transitions occurring over just a few periods (e.g., periods 85-91 for cost = 2.0). The transition is abrupt, not gradual -- consistent with the taxonomy's warning that "if it happens over years... the adjustment problem is qualitatively different from any historical precedent."

**Supports the inequality prediction:** The Gini coefficient nearly quadrupling (0.151 to 0.565) with Q4-Q5 wages perfectly insulated while Q1-Q2 go to zero confirms the extreme polarization predicted by the taxonomy. This is not standard technological unemployment -- it is a binary employed/displaced partition determined entirely by skill level relative to AI capability.

**Challenges the taxonomy in one respect:** The taxonomy frames this as a "wage collapse singularity," but the simulation shows a *floor* rather than a singularity. Once displacement equilibrium is reached (at AI cost = 5.0), further cost reductions produce no additional damage. The collapse is severe but bounded -- roughly half the workforce is displaced, not all of it, because tasks requiring skills above the AI quality ceiling remain human-dominated.

---

## 5. Collusion Bertrand Results

**Setup:** Repeated Bertrand pricing game with Q-learning agents. N firms (2, 3, 5), homogeneous good, marginal cost = 1.0, monopoly price = 2.0, 15 price levels, 5000 learning periods, measurement over final 1000. Architectural correlation parameter rho ∈ [0, 1] controls Q-table initialization similarity.

### Price Index by Correlation and Firm Count

Price Index = (mean_price - marginal_cost) / (monopoly_price - marginal_cost). 0 = competitive, 1 = monopoly.

| rho | N=2 | N=3 | N=5 |
|:---:|:---:|:---:|:---:|
| 0.0 | 0.491 | 0.425 | 0.409 |
| 0.2 | 0.487 | 0.456 | 0.398 |
| 0.5 | 0.489 | 0.470 | 0.421 |
| 0.8 | 0.487 | 0.481 | 0.372 |
| 0.9 | 0.484 | 0.473 | 0.344 |
| **1.0** | **0.727** | **0.699** | **0.717** |

### Key Findings

**Phase transition at rho=1.0.** The most striking result is the sharp discontinuity at full architectural identity. For rho < 1.0, price indices cluster around 0.40-0.49 regardless of correlation level — agents with even slight independence settle near midpoint pricing. At rho = 1.0 (identical Q-tables and exploration), prices jump to ~0.72 — a 48% increase toward monopoly pricing. This is not gradual: the transition from rho=0.9 to rho=1.0 accounts for more price increase than the entire 0.0-to-0.9 range.

**Collusion emerges without communication.** At rho=1.0, agents sustain supra-competitive pricing (PI > 0.7) for the entire measurement window despite having no shared state, no communication channel, and no explicit coordination mechanism. This directly confirms the Calvano et al. (2020) result under controlled conditions. The agents collude because their identical learning dynamics find the same basin of attraction in the strategy space.

**N does not prevent collusion at rho=1.0.** Standard Bertrand theory predicts that more firms drive prices toward marginal cost. This holds for rho < 1.0 (PI decreases from ~0.49 to ~0.40 as N increases from 2 to 5). But at rho=1.0, the price index is ~0.72 regardless of N — identical architecture overrides competitive pressure from additional firms.

**Punishment behavior exists but is weak.** After forced deviations, competitors lower prices 10-70% of the time, but the magnitude is small (-0.01 to -0.07). This is weaker punishment than Calvano et al. report, possibly due to our simpler Q-learning setup (tabular, no eligibility traces).

**The policy implication is stark.** Architectural monoculture — not the number of competitors — is the primary determinant of collusive outcomes. Antitrust policy focused on market concentration (number of firms) is insufficient when the firms use identical AI pricing agents. The relevant metric is architectural diversity, not market share.

### Theory Alignment — Taxonomy Claims on Algorithmic Collusion

**Strongly supports the taxonomy's collusion-without-communication claim.** The simulation demonstrates that shared architecture produces supra-competitive pricing without any communication or coordination. The mechanism is exactly as described: correlated learning dynamics find the same equilibrium.

**Partially supports the interaction-effects Collusion x Sybil analysis.** While this simulation does not include sybils, the rho=1.0 result shows that a single principal deploying identical agents would achieve the highest collusive pricing. Combined with the sybil auction results showing rent extraction, the interaction compound is empirically grounded.

**Adds nuance to the Calvano et al. caveat.** The taxonomy (post-revision) notes that Calvano results may not generalize. Our results confirm the core finding (collusion emerges from shared architecture) but show that even slight architectural diversity (rho=0.9) is enough to prevent it. This suggests the concern about "a small number of foundation model families" is more nuanced than a binary: collusion requires near-identity, not just similarity.
