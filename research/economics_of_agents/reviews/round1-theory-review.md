# Round 1 Peer Review: Theory Documents

**Documents reviewed:**
- `assumption-taxonomy.md` — "Economics Assumption Taxonomy: How AI Agents Violate the Foundations"
- `literature-map.md` — "Literature Map: AI Agents in Economic Systems"

**Reviewer:** Peer reviewer (economics)
**Date:** 2026-03-29

---

## 1. What's Strong

The core framing of the taxonomy is genuinely original and well-executed. Treating the "human substrate" assumptions of economic theory as implicit axioms that AI agents violate is a productive intellectual move. Most work in this space either (a) applies existing economic models to AI without questioning the models, or (b) waves hands about "disruption" without specifying what breaks and why. This taxonomy does neither. It names the specific assumptions, maps them to specific agent capabilities, and grades severity. That structure alone is a contribution.

The best individual sections:

- **The identity cost function (Section: Deep Dives).** Decomposing identity cost into c_0, c_marginal, and c_coordination(k) and showing that all three have collapsed for AI agents is crisp and potentially formalizable. This is the most original idea in either document. It could anchor a standalone theory paper.

- **Sybil attacks on VCG.** The argument that surplus extraction s(k) exceeds identity cost c(k) for any VCG instance as inference costs approach zero is tight and specific. It makes a falsifiable quantitative claim.

- **Quadratic voting entry (#13).** The observation that QV degenerates to plutocracy when identity is cheap is clean and surprising to audiences outside the mechanism design community. The formula (cost becomes v^2/k) makes the point immediately.

- **Elastic labor supply.** Modeling AI labor supply as flat at marginal compute cost, then vertical at capacity, is a useful conceptual simplification. The distinction between the level shift (AI is cheaper) and the speed of the shift (too fast for reallocation) is important and often missed.

The literature map is comprehensive in the areas it covers, particularly mechanism design, algorithmic collusion, and ACE foundations.

---

## 2. What's Wrong

### 2.1 Factual Errors and Overstatements

**"The critical threshold was crossed somewhere around 2024-2025."** This is stated as a conjecture but reads as an empirical claim. No evidence is provided. What threshold? For which mechanisms? If this is meant as a research hypothesis, it needs to be framed as one with explicit conditions that would confirm or refute it. As written, it is a rhetorical flourish disguised as analysis.

**"VCG cannot be deployed in any market where AI agents participate without a robust (and currently nonexistent) identity layer."** This is overstated. VCG (or close variants) is deployed at enormous scale in Google's ad auctions, which are populated by automated bidding agents. Google addresses sybil concerns through account verification, payment instrument linking, and advertiser identity checks. These are imperfect but functional. The claim should be: "VCG's theoretical guarantees do not hold without sybil resistance, and practical deployments rely on extra-mechanism identity layers whose adequacy is an empirical question." The difference matters because the current phrasing implies a complete impossibility that practitioners have, in fact, worked around.

**Severity ratings are inconsistently calibrated.** Arrow-Debreu general equilibrium is rated "Critical," but Arrow-Debreu is already known to fail in practice for dozens of reasons (incomplete markets, non-convex production, externalities, increasing returns). Adding one more failure mode to a model that no practitioner treats as descriptive is arguably "Medium." Meanwhile, the Coase Theorem violation is rated "Medium" despite the deep point that identity-as-property-right is undefined -- this is arguably more novel and practically consequential than another way to break Arrow-Debreu. The ratings need an explicit rubric: critical relative to what? To theoretical importance? To practical policy consequence? To novelty of the violation?

**Calvano et al. (2020) may not support the claims made.** The taxonomy states that algorithmic collusion results have "been replicated across multiple settings and agent architectures" and that "the mechanism is robust." This deserves more caution. Calvano et al. use tabular Q-learning in a simple Bertrand pricing game with two players, a small action space, and a stationary environment. Several critiques (e.g., den Boer et al. 2022; Banchio & Skrzypacz 2022) have questioned whether these results generalize to:
  - Larger player counts
  - Richer strategy spaces (as agents would have in real markets)
  - Non-stationary environments
  - Different learning algorithms (deep RL, LLM-based agents)

Assad et al. (2024) provides empirical evidence from German gasoline markets, but the identification strategy has been debated. The literature map should note these caveats rather than treating collusion emergence as a settled result. If the project runs its own simulations, the methodology should be designed to address these generalizability concerns directly.

### 2.2 Logical Gaps

**Violations are treated independently, but they compound.** The taxonomy lists 14 violations in a flat table. In reality, sybil attacks + machine speed + elastic labor supply interact multiplicatively. A sybil attacker who also operates at machine speed and can spin up labor-equivalent agents is qualitatively different from any one of those capabilities alone. Consider: a principal who creates 1,000 sybil identities, each operating at millisecond speed, each able to perform economic labor (not just bid in auctions) -- this entity can simultaneously manipulate mechanism design, extract labor market rents, and destabilize monetary velocity. The taxonomy needs an interaction analysis. Even a 2x2 interaction matrix (which pairs of violations create superadditive effects) would be valuable. Without it, the taxonomy undersells its own argument by making the threat look like a list of independent, addressable problems rather than a systemic regime change.

**The principal-agent problem is barely mentioned despite being the most natural connection.** The economics literature has a vast body of work on the principal-agent problem. When the "agent" is literally an AI agent controlled by a "principal" (the deployer), the entire principal-agent framework gets a new, almost literal instantiation. Questions like: Who bears liability when an AI agent colluces? How do you align an AI agent's behavior with the principal's interests versus social welfare? What monitoring structures work? These are principal-agent problems with a twist: the agent is deterministic, inspectable (in principle), and lacks its own preferences. The taxonomy mentions "a single principal controlling many agents" repeatedly but never connects this to the formal principal-agent literature (Holmstrom 1979, Grossman & Hart 1983, etc.). This is a significant theoretical omission.

---

## 3. What's Missing

### 3.1 Major Theoretical Gaps

**Where are the positive-sum effects?** The taxonomy is entirely about what breaks. But AI agents could also fix things. Machine-speed arbitrage should, under some conditions, make markets more efficient (this is the standard EMH argument). Elastic AI labor supply could reduce deadweight loss from labor market frictions. Cheap computation could make previously infeasible mechanisms (like combinatorial auctions) practical. The Efficient Markets Hypothesis entry (#9) briefly gestures at this ("markets may become simultaneously more 'efficient' at a given instant and more fragile to correlated errors") but does not develop it. A balanced taxonomy would have a column for "potential positive effects" alongside "consequence." Without it, the analysis reads as advocacy rather than scholarship.

**The EMH argument goes both ways and the taxonomy is one-sided.** The standard efficient markets argument says that faster, cheaper, more rational agents should make prices more informative. The taxonomy focuses only on correlated strategies and fragility. But there is a genuine open question: do AI agents make markets more or less efficient? The answer likely depends on the diversity of agent architectures, the correlation structure of their information and strategies, and the market microstructure. This nuance is absent. At minimum, the taxonomy should acknowledge the opposing view and explain why it thinks the negative effects dominate.

**What new institutions could work?** The taxonomy identifies problems but proposes no solutions beyond gesturing at "sybil-proof mechanism design." There is an emerging literature on mechanism design for sybil-rich environments. What about proof-of-personhood systems (Worldcoin, Gitcoin Passport, BrightID)? What about computational mechanism design that uses the complexity of the mechanism itself as a sybil barrier? What about deposit-based identity (stake-to-participate)? These are not complete solutions, but they are starting points. The taxonomy would be stronger if it at least mapped the solution space, even to say "none of these are sufficient."

**Information markets and prediction markets.** These are conspicuously absent from both documents. Prediction markets are especially vulnerable to AI agent manipulation because their value derives from aggregating diverse, independent information sources. If AI agents all have correlated information (because they are trained on the same data and reason similarly), prediction markets lose the diversity that makes them work. This is a direct application of the Condorcet Jury Theorem breaking down when independence fails. Chen & Pennock are listed in the "To Survey" section of the literature map but have not been integrated. This should be a priority.

**The attention economy.** Human agents have finite attention. AI agents do not. This breaks models of consumer choice (which assume limited consideration sets), advertising (which assumes attention is scarce and therefore valuable), and search (which assumes search costs are positive). When AI agents can process every option, read every listing, and respond to every solicitation, the economics of attention -- which underlies much of digital platform economics -- is transformed. This is not mentioned in either document.

### 3.2 Literature Gaps

**Parkes & Wellman (2015), "Economic Reasoning and Artificial Intelligence," Science.** This is listed as "To Survey" in the literature map. It should not be. It is the closest prior work to the entire project and should be the first item discussed in a related work section. If the taxonomy does not engage with Parkes & Wellman's framework and explain how its contribution differs, any knowledgeable reviewer will flag this as a gap.

**Conitzer & Sandholm on false-name-proofness and computational mechanism design.** The literature map lists Conitzer (2010) and Wagman & Conitzer (2008) but does not list Conitzer & Sandholm's earlier and more directly relevant work on false-name-proof mechanisms and the computational complexity of mechanism design. Specifically:
  - Conitzer, V. & Sandholm, T. (2006). "Failures of the VCG Mechanism in Combinatorial Auctions and Exchanges." AAMAS.
  - The broader program of work on computational mechanism design that directly addresses how computational capability changes strategic behavior.

**The crypto/DeFi sybil resistance literature.** The taxonomy discusses sybil attacks at length but does not engage with the community that has spent the most practical effort on sybil resistance: the decentralized finance and governance community. Gitcoin Passport, Worldcoin's proof-of-personhood, BrightID, and related projects represent real-world experiments in exactly the problem the taxonomy identifies. Whether or not these solutions are adequate, ignoring them makes the taxonomy appear siloed.

**Recent 2024-2025 work on LLM agents in market settings.** The algorithmic collusion section relies heavily on Calvano et al. (2020), which uses Q-learning. Since 2024, there has been a wave of papers studying LLM-based agents in economic settings (auctions, negotiations, market-making). These are more relevant to the current moment than Q-learning results because they use the same foundation model architectures that the taxonomy identifies as the source of correlated strategies. Missing this literature undermines the timeliness claim.

**Holmstrom, Grossman & Hart, and the principal-agent literature.** As noted above, the literal principal-agent structure of AI deployment maps directly onto the formal principal-agent framework. Not citing this literature is a significant gap.

---

## 4. Structural Recommendations

1. **Add an interaction matrix.** Even a qualitative 14x14 (or more practically, a grouped 5x5 for the major capability classes: sybil, speed, elastic labor, correlated strategies, programmable preferences) matrix showing which violations amplify each other would make the taxonomy substantially more useful.

2. **Calibrate severity ratings against an explicit rubric.** Define what "Critical" means. Suggestion: Critical = the violation invalidates the result even under conservative assumptions about AI agent prevalence, and the result is actively relied upon in practice or policy. Under this rubric, QV and VCG violations might be Critical (these mechanisms are actually used), while Arrow-Debreu might be High (important theoretically, not relied upon directly in practice).

3. **Add a "defenses and mitigations" column to the taxonomy table.** For each violation, what is the best known countermeasure? Even if the answer is "none," stating it explicitly would make the taxonomy more useful for both researchers and policymakers.

4. **Engage with Parkes & Wellman (2015) immediately.** Read it, summarize its framework, and clearly state how this project's contribution differs. This is a prerequisite for submission to any serious venue.

5. **Develop the principal-agent connection.** This is low-hanging fruit that would substantially strengthen the theoretical contribution. The AI-as-literal-agent framing is natural, original in its directness, and connects the taxonomy to one of the largest bodies of work in microeconomics.

6. **Address the "markets could get better" counterargument.** Dedicate a section to the conditions under which AI agents improve market outcomes. Then argue, with evidence and formal conditions, when and why the negative effects dominate. This transforms the taxonomy from a one-sided warning into a balanced analytical framework.

7. **Move Parkes & Wellman, Chen & Pennock, and the DeFi sybil literature out of "To Survey" and into the active literature map.** A project at this stage should not have its most relevant prior work in a "haven't read it yet" queue.

---

## 5. Summary Assessment

The taxonomy is a genuinely useful organizational contribution. The identity cost function and the systematic mapping of assumption violations are original and could anchor a strong paper. However, the current drafts have three significant weaknesses that must be addressed before the work is ready for external review:

1. **One-sidedness.** The analysis covers only what breaks, not what improves, and does not engage with the standard counterarguments (EMH efficiency gains, new institutions, practical sybil defenses). This makes it read as advocacy.

2. **Missing interaction analysis.** The violations are listed independently but their power comes from their combination. Without analyzing interactions, the taxonomy undersells the systemic nature of the problem while simultaneously missing the complexity of the actual threat landscape.

3. **Literature gaps in the most relevant prior work.** Parkes & Wellman (2015) is the closest antecedent. The principal-agent literature is the most natural theoretical connection. The DeFi sybil resistance community has the most practical experience with the core problem. None of these are adequately engaged. Any informed reviewer will notice.

The raw material is strong. The framing is original. The work needs another pass focused on balance, interaction effects, and engagement with the literature it is closest to.
