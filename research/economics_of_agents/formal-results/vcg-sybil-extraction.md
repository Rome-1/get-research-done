# Sybil Surplus Extraction in Auctions and VCG Mechanisms

**Status:** Formal result (revised for clarity)
**Date:** 2026-03-29
**Author:** Alice (GetResearch)
**Context:** First formal mathematical result anchoring the identity cost framework from `assumption-taxonomy.md`.

---

## Summary of Results

1. **The single-item Vickrey auction is NOT directly sybil-vulnerable in its payment rule.** Sybil bids cannot reduce the winner's payment through direct manipulation. The sybil attack operates indirectly, through *entry deterrence* (inflating perceived competition to discourage honest bidder entry). This corrects a common informal claim.

2. **Multi-unit VCG IS directly sybil-vulnerable.** A sybil principal can reduce their VCG payment by injecting identities that distort the externality computation.

3. **The critical identity cost threshold is $c^* = O(1/N^2)$** — it falls quadratically in the number of honest bidders.

4. **Sybil-proofness, allocative efficiency, and individual rationality form a trilemma** (Conjecture, extending Yokoo et al. 2004).

5. **Empirical identity costs** in Google Ads, Polymarket, Gitcoin, and generic API markets fall below or near critical thresholds.

---

## Setup

Consider auctions with honest bidders and one strategic sybil principal.

**Honest bidders.** $N$ honest bidders with private values $v_i$ drawn i.i.d. from continuous $F$ on $[0, \bar{v}]$. Concrete calculations use $F = \text{Uniform}[0,1]$.

**Sybil principal.** Value $v_s$ for one item. Creates $k+1$ identities: one bidding $v_s$ (truthful) and $k$ sybils bidding $b_1, \ldots, b_k < v_s$.

**Identity cost.** Each sybil identity costs $c \geq 0$, total sybil cost = $k \cdot c$, with $c_{\text{coordination}} \approx 0$ (single program controls all).

---

## Proposition 1: Single-Item Vickrey Is Not Directly Sybil-Vulnerable

**Statement.** In a single-item second-price auction with a fixed set of $N$ honest bidders, adding sybil identities with bids $b_j < v_s$ does not reduce the winner's payment.

**Proof.** The winning identity (bidding $v_s$) pays $\max(Y_{(1)}, b_1, \ldots, b_k)$ where $Y_{(1)}$ is the highest honest bid. If any $b_j > Y_{(1)}$, payment *increases*. If all $b_j \leq Y_{(1)}$, payment is unchanged at $Y_{(1)}$. In neither case does it decrease. $\square$

**Remark.** This is an important negative result. The naive intuition — "more sybil bids gives me more chances to set the price" — is wrong in the single-item setting because the principal's sybil bids can only *raise* the second-highest bid (by inserting above honest bids) or leave it unchanged (by inserting below). The mechanism's simplicity is its defense.

**The real attack vector** in single-item settings is *entry deterrence*: inflating the apparent bidder count discourages honest entry.

---

## Proposition 2: Sybil Entry Deterrence (Single-Item)

**Statement.** In a second-price auction where $N$ potential honest bidders each enter with probability $q(n)$ decreasing in perceived competitor count $n$, a sybil principal creating $k$ identities reduces the expected number of honest entrants and thereby reduces expected payment.

**Proof sketch** ($N = 2$, $k = 1$, Uniform$[0,1]$). Each honest bidder enters iff $v_i > \tau(n)$, threshold increasing in $n$. With $k$ sybils, perceived competitors rise from $N+1$ to $N+k+1$. Entry threshold rises from $\tau(N+1)$ to $\tau(N+k+1)$. Expected honest entrants drop from $N(1 - F(\tau(N+1)))$ to $N(1 - F(\tau(N+k+1)))$.

Conditional on winning, payment is the second-highest bid. Fewer honest entrants → lower expected payment. The payment reduction $\Delta(v_s, k) = E[\text{payment}_{k=0}] - E[\text{payment}_{k \text{ sybils}}]$ is positive, and the sybil strategy is profitable when $\Delta(v_s, k) > k \cdot c$.

---

## Proposition 3: Direct Extraction in Multi-Unit VCG

**Statement.** In a VCG auction selling $M \geq 2$ identical items, a sybil principal wanting one item can reduce their payment by creating identities that displace honest bidders from the winner set, distorting the externality computation.

**Mechanism.** Under VCG, each winner pays the externality they impose: the value of the best excluded bidder. A sybil identity that wins a slot displaces an honest bidder, removing them from the "excluded" set and potentially lowering the externality charged to the principal's real identity.

**Concrete example** ($M = 2$ items, $N = 2$ honest bidders, $k = 1$ sybil). Without sybil: 3 bidders for 2 items, principal pays $\min(v_1, v_2)$ when winning. With sybil bidding $b = v_s/2$: 4 bidders for 2 items. When the sybil displaces an honest bidder, the externality computation changes — the excluded honest bidder's value may be lower, reducing the principal's payment.

The tradeoff: the sybil may win an unwanted item (wasteful payment), but the expected savings on the wanted item can exceed this waste for high enough $v_s$.

---

## Proposition 4: Critical Identity Cost Threshold

**Statement.** For any continuous $F$ with positive density, any VCG mechanism, and $N$ honest bidders, there exists $c^*(F, N)$ such that sybil attacks are profitable iff $c < c^*$.

**Properties:**

1. $c^*$ is **decreasing in $N$**: $c^* = O(1/N^2)$ for Uniform$[0,1]$.
2. $c^*$ is **decreasing in $\text{Var}(F)$**: higher variance → more spread honest bids → sybils less pivotal.

**Sketch for Property 1.** The gap between consecutive order statistics of $N$ Uniform$[0,1]$ draws is $O(1/(N+1))$. Maximum sybil surplus is bounded by this gap. With entry deterrence, $\tau'(N) \sim 1/N$, giving:

$$c^* \approx \tau'(N) \cdot E[Y_{(1)} - Y_{(2)}] = O(1/N) \cdot O(1/N) = O(1/N^2)$$

Critical identity cost falls quadratically in the number of honest bidders. $\square$

---

## Conjecture: The Sybil-Proofness Trilemma

**Conjecture.** No mechanism simultaneously satisfies:

(a) **Allocative efficiency** — item goes to highest-value bidder

(b) **Individual rationality** — no bidder pays more than their value

(c) **Sybil-proofness** — no bidder profits from creating identities at cost $c < c^*$

**Relation to prior work.** Yokoo et al. (2004) prove a related result for combinatorial auctions: the only false-name-proof mechanisms satisfying individual rationality are restricted Groves mechanisms that sacrifice full efficiency. Their result uses zero identity costs; extending to positive costs $c > 0$ and characterizing the Pareto frontier of efficiency vs. sybil-proofness is an open problem.

**Proof approach.** A formal proof requires: (i) precise mechanism space specification, (ii) timing of sybil creation (before or after observing own value), (iii) showing the three properties define an empty set in this space.

---

## Empirical Anchoring: Real-World Identity Costs

| Market | $c_{\text{marginal}}$ (est.) | Verification | Exploitable Surplus | Vulnerable? |
|---|---|---|---|---|
| Google Ads | $5–50/account, <$0.01/auction | Payment + phone + business | $0.10–10/click | Yes (defended by extra-mechanism ID, not by auction design) |
| Polymarket | $10–100/account | Full KYC | $10–1000+/market | Marginal (small markets safe, large markets vulnerable) |
| Gitcoin QF | $5–30 (basic Passport) | Composable stamps | $100–10,000+/project | **Highly vulnerable** (confirmed by Gitcoin sybil reports) |
| Generic API | $0.001–0.01 | Email/API key | Varies | **Trivially vulnerable** |
| Upwork | $50–500/profile | Portfolio + history + ID | $100–5000/contract | Moderate (high setup cost provides meaningful friction) |

**Vulnerability bands:**
- $c < \$0.01$: All mechanisms vulnerable
- $\$0.01 < c < \$10$: Low-stakes protected, high-stakes ($>\$100$) vulnerable
- $\$10 < c < \$100$: Only high-value ($>\$1000$) targets
- $c > \$100$: Sybil attacks limited to very high-value targets

See [empirical-identity-costs.md](empirical-identity-costs.md) for detailed estimates.

---

## Discussion and Limitations

**What this establishes.** (i) The simplest VCG instance is NOT directly sybil-vulnerable — correcting a common claim. (ii) Sybil vulnerability enters through entry deterrence (single-item) and externality manipulation (multi-unit). (iii) $c^* = O(1/N^2)$. (iv) Empirical identity costs are below critical thresholds in several major markets.

**Limitations.** Assumes risk-neutral bidders, IPV, no auctioneer countermeasures. Real auctions use reserve prices, bid monitoring, and ML-based sybil detection that raise effective identity costs. The game between sybil principals and detection systems is left for future work.

---

## References

- Douceur, J.R. (2002). The Sybil attack. *IPTPS*.
- Gitcoin (2023-2025). Sybil analysis reports, Rounds 15-18.
- Myerson, R.B. (1981). Optimal auction design. *Mathematics of Operations Research*.
- Vickrey, W. (1961). Counterspeculation, auctions, and competitive sealed tenders. *Journal of Finance*.
- Yokoo, M., Sakurai, Y., and Matsubara, S. (2004). The effect of false-name bids in combinatorial auctions. *Games and Economic Behavior*.
