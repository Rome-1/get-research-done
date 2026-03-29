# Sybil Resistance Audit Protocol

## Purpose
Systematically evaluate whether an economic mechanism, market, or institution
is robust to sybil attacks — agents creating multiple identities to gain
unfair advantage.

## Steps

1. **Catalog identity assumptions** — List every point where the mechanism
   assumes one-agent-one-identity. Lock `identity_model`.
2. **Enumerate sybil strategies** — For each identity assumption, describe
   how a sybil attacker could exploit it:
   - **Bid splitting**: Dividing a single bid across k identities to manipulate price.
   - **Wash trading**: Trading with yourself to create false volume/liquidity signals.
   - **Governance capture**: Creating identities to gain disproportionate voting power.
   - **Reputation farming**: Building reputation across identities, then spending it.
   - **Airdrop/subsidy extraction**: Claiming per-identity rewards multiple times.
   - **Quota evasion**: Circumventing per-agent limits by creating new identities.
3. **Quantify attack cost** — For each strategy, compute:
   - Identity creation cost (registration, proof-of-personhood, stake required)
   - Expected gain from k sybils vs k identity cost
   - Break-even k where attack becomes profitable
4. **Assess impact** — For each viable attack:
   - Effect on allocative efficiency
   - Effect on honest participant welfare
   - Effect on mechanism revenue/budget balance
   - Cascading effects (does the attack destabilize the market?)
5. **Design countermeasures** — For each vulnerability:
   - Identity cost increases (staking, proof-of-humanity)
   - Mechanism redesign (sybil-proof mechanisms, quadratic penalties)
   - Detection and punishment (behavioral fingerprinting, slashing)
   - Rate limiting and cooldowns
6. **Re-audit with countermeasures** — Verify that countermeasures don't
   introduce new vulnerabilities or disproportionately burden honest agents.

## Common Pitfalls
- Testing only single-sybil attacks when the real threat is thousands of identities.
- Assuming identity verification solves the problem (AI agents can pass many verification schemes).
- Focusing on one attack vector while ignoring combined/chained strategies.
- Making sybil resistance so expensive that honest participation is discouraged.
- Assuming the cost of creating identities is fixed (it decreases with scale and automation).

## Convention Lock Fields
- `identity_model`, `transaction_cost_model`, `agent_rationality`
