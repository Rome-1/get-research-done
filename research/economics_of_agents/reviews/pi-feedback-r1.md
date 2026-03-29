# PI Feedback — Round 1 (2026-03-29)

Feedback from project PI after full corpus review. These should be incorporated
into the next revision round alongside internal review feedback and literature
deep dive results.

---

## F1: KYC Markets Already Assuage Many Sybil Concerns

In many markets of significance (public asset markets, regulated exchanges),
human-provable identity is already required to participate. This substantially
reduces the sybil surface in precisely the markets that matter most.

**However:** The merit of the sybil analysis remains as agents become more
independent, assume responsibility, and move across markets faster — with humans
acting as mere "meat puppets" for KYC. The transition from "human uses agent as
tool" to "agent uses human as KYC pass-through" is where the real risk emerges.

**Action:** The corpus should acknowledge this explicitly. Many claims about
sybil vulnerability need to be qualified with "in markets that don't require
human-provable identity" or reframed around the KYC-erosion trajectory.

---

## F2: Collusion Basin of Attraction — Generalization Is Open

The collusion simulation result (convergence at rho=1.0) is best understood as:
agents converged because their learning dynamics, operating on the same
environment structure, found the same basin of attraction.

Whether these results generalize to larger player counts, richer strategy spaces,
non-stationary environments, or different learning algorithms (deep RL,
LLM-based agents) remains an open question. Den Boer et al. 2022 and Banchio &
Skrzypacz 2022 offer critical perspectives.

**Action:** The simulation results section should frame this as "basin of
attraction convergence" rather than implying general collusion inevitability.
Add explicit caveats about generalization limits.

---

## F3: Flash Loans as Monetary Velocity Countermeasure/Amplifier

The "Machine-Speed Velocity and Monetary Instability" section's key insight is
that agent access to money could make money even more valuable to own at any
point in time — effectively creating demand for very short-term loans.

**Flash loans** (the mechanism the PI referenced) are an existing blockchain
primitive where agents can borrow, transact, and return funds within a single
atomic block. If the transaction fails at any step, the entire operation reverts.
This effectively allows agents to "invent money" within a single block's scope.

**Key question:** Do flash loans provide a countermeasure to the monetary
instability concerns (by enabling frictionless capital reallocation), or do they
amplify them (by making velocity effectively infinite within a block)?

**Action:** Add flash loans to the monetary velocity discussion. This is a
concrete, existing mechanism that directly instantiates the theoretical concerns.
The DeFi ecosystem has empirical data on flash loan usage patterns and their
systemic effects.

---

## F4: Biometric + Citizenship for Sybil Resistance

The sybil resistance section should consider biometric identity tied to
citizenship as a mechanism. This goes beyond proof-of-personhood (Worldcoin,
BrightID) to nation-state-backed biometric identity.

**Strengths:** Hard to forge, scales with existing infrastructure, high c(k).
**Weaknesses:** Excludes stateless persons, privacy concerns, government
overreach potential, assumes nation-state cooperation, creates geographic
identity monopolies.

**Action:** Add to sybil resistance mechanisms discussion alongside existing
proof-of-personhood coverage. Analyze the identity cost c(k) implications —
biometric + citizenship likely creates a step-function cost rather than the
smooth c(k) curve modeled.

---

## F5: Model Diversity Caveats for Collusion Analysis

The collusion analysis assumes high overlap in model training, deployment
infrastructure, and harnesses. This is largely true today (widely distributed
training data, similar architectures, common deployment patterns), and probably
doesn't change outcomes much in the near term.

**However**, the analysis also assumes agents participate directly in markets
rather than, e.g., conducting independent research first — which itself may
converge due to similar training. These are important caveats.

**PI's take:** Long-term wide-ranging post-training and more diverse model sets
may partially alleviate collusion convergence, but the transition period may be
rough. The monoculture risk is real now and for the medium term.

**Action:** Add these caveats to the collusion analysis. Frame as:
(1) Training overlap → similar priors → same basin of attraction (current)
(2) Deployment/harness overlap → same optimization landscape (current)
(3) Independent research convergence → possible even with diverse models (longer term)
(4) Diverse post-training may help but transition period is dangerous

---

## F6: Model Provider Hidden Behaviors Complicate Principal-Agent

The principal-agent deep dive states: "There is no hidden type — or rather, the
'type' is fully determined by the model weights and system prompt, both of which
the principal controls."

**This is only partially true.** The model provider may instill particular
public or hidden behaviors in models. RLHF objectives, constitutional AI rules,
safety training, and undisclosed fine-tuning all create behaviors that the
deploying principal does not control and may not even be aware of.

This means the principal-agent chain is actually:
Model Provider → [hidden behaviors] → Platform → Principal → Agent

The principal's control over agent "type" is partial, not complete. The model
provider is a silent participant in every principal-agent relationship.

**Action:** This is a significant qualification to the principal-agent analysis.
Revise the "no hidden type" claim. The information asymmetry between model
provider and principal is itself a principal-agent problem nested inside the
framework.

---

## F7: Parallelism Precedent in Blockchain

The corpus should acknowledge that many of the parallelism concerns raised
(atomic transactions, concurrent agent participation, speed-of-light economic
activity) have direct precedent in blockchain technologies. Blockchain systems
have already solved or encountered many of these problems.

**Action:** Add blockchain precedent discussion where relevant. The DeFi
ecosystem is effectively a preview of agent-dominated economic systems.

---

## Priority for Next Revision

1. **F6** (hidden behaviors) — fundamentally changes the principal-agent argument
2. **F1** (KYC markets) — qualifies the broadest sybil claims
3. **F3** (flash loans) — concrete mechanism for the monetary velocity discussion
4. **F5** (model diversity caveats) — nuances the collusion analysis
5. **F2** (basin of attraction framing) — tightens the collusion narrative
6. **F4** (biometric + citizenship) — adds to sybil resistance coverage
7. **F7** (blockchain precedent) — strengthens multiple sections
