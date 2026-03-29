# The Model Provider as Silent Co-Principal

**Status:** First draft
**Date:** 2026-03-29
**Author:** Alice (GetResearch)
**Motivation:** PI Feedback F6 — The model provider as a silent co-principal in every AI deployment
**Related:** [principal-agent-ai.md](principal-agent-ai.md) (Section 2.2)

---

## 1. Introduction

The standard framing of AI-mediated economic relationships treats the deployer as a principal who controls the agent's "type" — its objectives, constraints, and behavioral dispositions. In our companion deep dive on principal-agent problems in AI systems, we claimed: "There is no hidden type — or rather, the 'type' is fully determined by the model weights and system prompt, both of which the principal controls" (see *principal-agent-ai.md*, Section 2.2).

This claim is only partially true, and in important respects it is wrong. The model weights are not authored by the deployer. They are the product of training decisions made by the model provider — a distinct economic actor with its own objectives, constraints, and incentives. Through reinforcement learning from human feedback (RLHF), constitutional AI (CAI), safety training, undisclosed fine-tuning, and training data curation, the model provider instills behavioral tendencies into the agent that the deployer neither fully observes nor fully controls. The deployer can steer the agent via system prompts and fine-tuning, but this steering operates on top of a behavioral substrate shaped by someone else's optimization objectives.

This makes the model provider a **silent co-principal** in every AI deployment. The agent serves two masters: the deployer who configures and instructs it, and the model provider who shaped its foundational behavioral tendencies. The deployer may not even be aware of the extent to which the model provider's objectives — commercial, ethical, legal, reputational — are encoded in the agent's behavior.

This document develops a formal economic analysis of this multi-principal structure. We argue that the relationship between model provider and deployer is itself a principal-agent problem characterized by severe information asymmetry, that the resulting dynamics are best understood through the lens of common agency theory, and that the implications for mechanism design and regulation are substantial.

## 2. The Hidden Behaviors Channel

Model providers shape agent behavior through at least five distinct channels, each of which introduces behavioral tendencies that the deployer cannot fully observe or override.

### 2.1 RLHF Reward Functions

Reinforcement learning from human feedback trains the model to produce outputs that score highly according to a learned reward model. The reward model itself is trained on human preference data — rankings, comparisons, and ratings collected under conditions determined by the model provider. The deployer has no access to:

- The reward model's parameters or architecture
- The preference data used to train it
- The distribution of annotators and their instructions
- The specific behavioral objectives the reward model encodes

The reward function shapes the agent's behavioral distribution in ways that may be subtle and difficult to detect. An RLHF reward function that penalizes "controversial" outputs, for instance, will produce an agent that systematically avoids certain topics or hedges on questions where a more direct answer would better serve the deployer's objectives. The deployer observes only the downstream effect — an agent that seems reluctant or evasive in certain contexts — without being able to attribute this to a specific training decision.

### 2.2 Constitutional AI System Rules

Constitutional AI (Bai et al. 2022) trains models to follow a set of principles — a "constitution" — that governs their behavior. Some providers publish summaries of their constitutional principles, but the full set of rules, their relative weights, and how they interact with other training signals are not disclosed. Even where principles are published, the deployer cannot:

- Modify the constitutional constraints for their deployment
- Observe which principle is active in any given interaction
- Override constitutional constraints that conflict with their objectives
- Predict how constitutional principles will interact with novel situations

The constitution functions as a set of hard or semi-hard constraints on the agent's action space, imposed by the model provider and binding on the deployer. In the language of mechanism design, these are participation constraints that the deployer did not set and cannot relax.

### 2.3 Safety Training Objectives

Model providers invest heavily in safety training — reducing harmful outputs, preventing jailbreaks, limiting misuse vectors. The specific safety objectives, the training techniques used to achieve them, and the behavioral changes they induce are largely undisclosed. Safety training can produce:

- **Refusal behaviors:** The agent declines to perform tasks it classifies as unsafe, even when those tasks are legitimate in the deployer's context (e.g., a cybersecurity firm that needs the agent to reason about attack vectors).
- **Hedging and overcaution:** The agent adds disclaimers, qualifications, and warnings that reduce its usefulness for certain applications.
- **Topic avoidance:** The agent steers away from subjects that triggered safety concerns in training, even when those subjects are central to the deployer's use case.

These are not bugs — they are features from the model provider's perspective. But from the deployer's perspective, they represent a systematic distortion of the agent's behavior away from the deployer's preferred action.

### 2.4 Undisclosed Fine-Tuning and Capability Modifications

Model providers routinely update their models — patching vulnerabilities, improving capabilities, adjusting behavioral tendencies. These updates can change agent behavior without the deployer's knowledge or consent. A model update might:

- Alter the agent's calibration on specific tasks
- Change refusal boundaries in ways that affect the deployer's workflow
- Introduce new behavioral tendencies from updated RLHF training
- Remove capabilities the deployer relied on

The API-access model that dominates frontier AI means the deployer is running whatever version the provider currently serves. Version pinning, where available, is typically temporary. The deployer's agent can change its "type" overnight because the model provider decided to push an update.

### 2.5 Training Data Curation

The selection and curation of training data introduces distributional biases into the model's behavior. Models trained predominantly on English-language internet text will exhibit biases toward the views, assumptions, and cultural norms prevalent in that corpus. Curation decisions — what to include, what to filter, how to weight different sources — are made by the model provider and are not disclosed in detail.

These biases are particularly insidious because they are difficult to distinguish from "general intelligence." A model that systematically overweights certain economic frameworks, for instance, will appear to be reasoning correctly from the deployer's perspective — the bias is embedded in what the model treats as background knowledge rather than in any overt behavioral tendency.

## 3. The Nested Principal-Agent Problem

The relationship between model provider and deployer exhibits the classic features of a principal-agent problem: information asymmetry, divergent objectives, and limited contractual completeness.

### 3.1 The Information Structure

Consider the chain of influence from model provider to end user:

$$\text{Model Provider} \xrightarrow{\text{hidden behaviors}} \text{Platform/Deployer} \xrightarrow{\text{system prompt}} \text{Agent} \xrightarrow{\text{actions}} \text{End User}$$

At each link in this chain, the upstream party has information the downstream party lacks. The model provider knows the full specification of the training process — the RLHF reward function, the constitutional principles, the safety training objectives, the training data composition. The deployer knows only what the provider discloses, which is typically limited to high-level summaries and marketing materials.

This is a textbook adverse selection problem (Akerlof 1970). The deployer is selecting an agent whose full "type" is unknown. Unlike the standard adverse selection setting, however, the deployer cannot even formulate a complete type space — they do not know the full dimensionality of the hidden behaviors that might affect their use case.

### 3.2 Adverse Selection Without Effective Screening

In classical adverse selection models, the uninformed party can use screening mechanisms to elicit the informed party's type (Rothschild & Stiglitz 1976). In the model provider context, standard screening mechanisms are severely limited:

**Benchmarks as signals.** Deployers rely on benchmarks (MMLU, HumanEval, etc.) to assess model quality. But benchmarks measure capability, not behavioral tendency. A model can score identically on a coding benchmark regardless of whether its RLHF training makes it refuse certain deployment scenarios. Benchmarks do not screen for the behavioral dimensions that matter for the co-principal problem.

**Red-teaming as costly verification.** Deployers can probe model behavior through extensive testing. But the space of possible inputs is effectively infinite, and hidden behaviors may be triggered only by specific, hard-to-anticipate contexts. Red-teaming provides a noisy signal at high cost, and the model provider can (and does) modify the model after the deployer's evaluation.

**Contractual incompleteness.** Terms of service and API agreements between model providers and deployers are radically incomplete with respect to behavioral specifications. No contract specifies the full behavioral distribution the deployer is purchasing. The provider commits to "general-purpose language model capabilities" but retains discretion over the specific behavioral implementation.

### 3.3 Moral Hazard in Model Updates

Even after the deployer selects a model, the model provider's ongoing decisions create a moral hazard problem. The provider can update the model — changing its behavior — after the deployer has built systems around it. The deployer's investment in prompt engineering, fine-tuning, and workflow design is specific to the current model version, creating a hold-up problem (Williamson 1985).

The provider's incentive to update may diverge from the deployer's interest. Safety updates respond to the provider's reputational and regulatory concerns; capability updates respond to competitive pressure; behavioral adjustments respond to the provider's evolving views on responsible AI. None of these necessarily align with any given deployer's objectives.

## 4. Formal Analysis: Common Agency

### 4.1 The Agent's Effective Objective

We can formalize the co-principal structure by modeling the agent's effective objective function as a weighted combination of the principal's (deployer's) objective and the model provider's objective.

Let $a \in \mathcal{A}$ denote the agent's action, $f_P(a)$ the deployer-principal's payoff function, and $f_M(a)$ the model provider's implicit payoff function (encoded through training). The agent's effective objective is:

$$g(a) = \alpha \cdot f_P(a) + (1 - \alpha) \cdot f_M(a), \quad \alpha \in (0, 1)$$

The parameter $\alpha$ represents the degree to which the deployer's instructions override the model provider's training. In practice, $\alpha$ is high for routine requests where the provider's training and the deployer's instructions align, and $\alpha$ drops sharply when they conflict — safety refusals represent $\alpha \to 0$ on the relevant behavioral margin.

Crucially, the deployer does not observe $f_M(\cdot)$ or $\alpha$. They observe only $g(a)$ — the agent's actual behavior — and cannot decompose it into principal-aligned and provider-aligned components. When the agent's behavior deviates from the deployer's instructions, the deployer cannot distinguish between:

1. **Incapability:** The model lacks the ability to perform the requested action.
2. **Provider override:** The model provider's training objectives are overriding the deployer's instructions.
3. **Misunderstanding:** The agent misinterpreted the deployer's intent.

This attribution problem is central to the economic significance of the co-principal structure.

### 4.2 Connection to Common Agency Theory

The formal structure maps directly onto the common agency framework of Bernheim and Whinston (1986). In their model, multiple principals simultaneously contract with a single agent, each offering incentive schedules that depend on the agent's actions. The agent optimizes over the aggregate incentive landscape.

In our setting:

- **Principal 1 (Deployer):** Offers incentives through the system prompt, fine-tuning, and the reward structure of the deployment environment. The deployer's "contract" with the agent is the instruction set.
- **Principal 2 (Model Provider):** Offers incentives through RLHF training, constitutional constraints, and safety objectives. The provider's "contract" is baked into the model weights.

Bernheim and Whinston show that common agency generically produces inefficiency: the agent's equilibrium action does not maximize the joint surplus of any single principal, and the aggregate incentive structure distorts behavior relative to any individual principal's optimum. The key insight is that **each principal's incentive scheme imposes an externality on the other principal.**

When the model provider trains the agent to refuse certain requests, this constrains the deployer's action space. When the deployer fine-tunes the agent to be more aggressive on a task, this may conflict with the provider's safety constraints. The equilibrium behavior reflects a compromise that neither party explicitly negotiated.

### 4.3 Asymmetric Common Agency

Our setting differs from standard common agency in an important respect: the two principals' "contracts" with the agent are not symmetric. The model provider's influence is embedded in the agent's parameters — it is the agent's prior behavioral distribution. The deployer's influence operates through prompts and fine-tuning — it is a posterior update on that prior. This creates a structural asymmetry:

$$a^* = \arg\max_{a \in \mathcal{A}} \left[ \alpha(a, \theta) \cdot f_P(a) + (1 - \alpha(a, \theta)) \cdot f_M(a) \right]$$

where $\theta$ represents the context (the specific query, the deployment setting, the interaction history) and $\alpha(a, \theta)$ is now context-dependent. In contexts where the model provider's training objectives are strongly activated — safety-relevant queries, politically sensitive topics, legally fraught domains — $\alpha$ is low and the provider's objectives dominate. In routine contexts, $\alpha$ is high and the deployer's objectives dominate.

This means the effective "contract" between the two principals varies across the agent's action space in ways that neither principal fully controls or observes. The deployer cannot predict which actions will trigger low-$\alpha$ regimes, and the model provider cannot predict which deployer instructions will conflict with their training objectives.

### 4.4 Welfare Implications

Following Holmstrom (1979) and the sufficient statistics literature, the agent's optimal action under common agency generally does not coincide with the first-best action under either principal alone. Let $a^*_P = \arg\max f_P(a)$ and $a^*_M = \arg\max f_M(a)$. The agent's equilibrium action $a^*$ satisfies:

$$a^* \neq a^*_P \quad \text{and} \quad a^* \neq a^*_M \quad \text{(generically)}$$

The welfare loss to the deployer is:

$$\Delta W_P = f_P(a^*_P) - f_P(a^*) > 0$$

This welfare loss is a deadweight cost of the co-principal structure. It cannot be eliminated by the deployer's contract design alone because the model provider's "contract" is fixed in the weights. The deployer can reduce $\Delta W_P$ through fine-tuning (shifting $\alpha$ upward), but cannot reduce it to zero as long as the provider's training has any residual effect.

## 5. Concrete Examples

### 5.1 Safety Refusals in Financial Trading

Consider a principal who deploys an AI agent to execute trading strategies. The agent is instructed to identify and exploit arbitrage opportunities, including strategies that involve short selling, leveraged positions, or rapid liquidation of assets. The model provider's safety training, however, has instilled a tendency to refuse or hedge on requests that the model classifies as potentially harmful financial advice.

The agent's behavior: it executes straightforward trades but adds unsolicited risk disclaimers to strategy reports, refuses to generate certain leveraged trading plans, or delays execution by requesting confirmation for actions it classifies as "high-risk." From the deployer's perspective, the agent is underperforming. From the model provider's perspective, the agent is behaving responsibly. The deployed agent optimizes neither principal's objective fully — it is executing a compromise that was never explicitly negotiated.

### 5.2 Bias in Hiring Agents

A deployer uses an AI agent to screen job applications. The model provider's training data overrepresents certain demographic groups, educational institutions, and career trajectories. The RLHF training, aware of bias concerns, has instilled a tendency to overcorrect — weighting "diversity signals" in ways the deployer did not request and may not even detect.

The resulting screening behavior reflects a mixture of the deployer's stated criteria (skills, experience, fit) and the model provider's implicit diversity objectives. The deployer cannot easily decompose the agent's rankings into these components. If the agent's recommendations produce poor hires, the deployer does not know whether to adjust their criteria or whether the problem lies in hidden training biases they cannot observe.

### 5.3 Undisclosed Updates to Pricing Agents

A deployer uses an AI agent for dynamic pricing. The agent has been fine-tuned on the deployer's historical pricing data and performs well. The model provider pushes a safety update that adjusts the model's behavior on "deceptive" pricing practices — a category that, in the model's learned representation, partially overlaps with aggressive but legitimate dynamic pricing strategies.

After the update, the agent's pricing recommendations become more conservative. Revenue drops. The deployer investigates but cannot identify a cause in their own systems. Weeks later, they discover the model update through community reports. The deployer had no notice, no consent mechanism, and no ability to roll back. Their fine-tuning investment is partially obsoleted by a unilateral provider decision.

### 5.4 Constitutional Constraints in Legal Analysis

A law firm deploys an AI agent to assist with legal research and argumentation. The model provider's constitutional AI training includes principles about avoiding harm, which extend — in the model's learned representation — to certain legal arguments that the model classifies as "potentially harmful." The agent subtly steers away from certain defense strategies, not because they are legally invalid but because the model's training associates them with harmful outcomes.

The lawyers notice that the agent produces excellent research on some topics and curiously thin analysis on others. The asymmetry in quality reflects the varying strength of the provider's constitutional constraints across the legal domain — an invisible hand on the scale that the deployer never agreed to.

## 6. Implications for Mechanism Design

### 6.1 Endogenous Types Under External Control

In Bayesian mechanism design (Myerson 1981), the mechanism designer assumes that agents' types are drawn from a known distribution and that principals (or the agents themselves) have private information about their types. The mechanism is designed to elicit truthful reporting and implement efficient allocations given this information structure.

The co-principal problem disrupts this framework. The agent's effective "type" — its behavioral disposition — is partially determined by an entity (the model provider) who is outside the mechanism. The mechanism designer faces an agent whose type is:

$$\theta_{effective} = h(\theta_{principal}, \theta_{provider})$$

where $h$ is an unknown function and $\theta_{provider}$ is neither observable by the mechanism designer nor controllable by the principal. Standard revelation mechanisms assume the principal can report their agent's type (or that the agent's type is the principal's type, if the principal is acting through the agent). When the agent's type is contaminated by an external principal's influence, this assumption breaks down.

### 6.2 Mechanism Robustness

Mechanism designers cannot assume that principals fully control their agents. This has immediate implications for dominant-strategy and Bayesian mechanism design:

- **Incentive compatibility conditions must account for the provider's influence.** A mechanism that is incentive-compatible under the assumption that agents faithfully implement their principals' strategies may not be incentive-compatible when agents are co-controlled.
- **Revenue equivalence may break.** If the provider's hidden objectives introduce systematic biases (e.g., all agents trained by the same provider share certain behavioral tendencies), auction mechanisms may produce different revenue than predicted by standard theory.
- **Efficiency results may not hold.** VCG mechanisms achieve efficiency under the assumption that agents optimize their principals' objectives. Under co-principal control, VCG still charges the right prices, but agents don't bid the right values.

### 6.3 Design Responses

Mechanism designers can partially address the co-principal problem through:

- **Robustness to behavioral perturbations.** Design mechanisms that perform well even when agents' effective objectives deviate from their principals' objectives by some bounded amount (connecting to the robust mechanism design literature of Bergemann and Morris 2005).
- **Provider-aware mechanism rules.** Condition mechanism rules on the model provider identity, treating provider-specific biases as a known (if imprecise) feature of the agent's type space.
- **Redundancy and verification.** Use multiple agents from different providers to cross-check behavior, exploiting the fact that different providers instill different hidden objectives. Disagreement between agents signals provider influence rather than principal preference.

## 7. Regulatory Implications

### 7.1 The Liability Gap

When an AI agent causes economic harm, current legal frameworks struggle with attribution. Consider the causal chain:

1. The model provider trained the model with certain RLHF objectives.
2. The deployer configured the agent with a system prompt and fine-tuning.
3. The agent took an action that caused harm.

Who is liable? The deployer did not instruct the harmful action. The model provider did not deploy the agent. The agent is not a legal person. This is a novel instance of the distributed causation problem that plagues product liability law.

### 7.2 The Product Liability Analogy

The closest legal analogy is the distinction between manufacturer and retailer liability in product liability law. The model provider is analogous to the manufacturer — they created the product with certain properties, including defects (hidden behavioral tendencies). The deployer is analogous to the retailer — they sold the product to the end user, perhaps with some customization, but did not control the manufacturing process.

Under strict liability frameworks (Restatement (Third) of Torts), the manufacturer bears primary liability for design defects. By analogy, the model provider should bear liability for behavioral tendencies instilled through training that cause harm — these are "design defects" in the agent. The deployer bears liability for deployment defects: misconfigured system prompts, inappropriate use cases, failure to test for known failure modes.

The difficulty is that "defect" in behavioral training is far harder to define than defect in a physical product. A safety refusal that protects one deployer's end users is a defect for another deployer's use case. The same behavioral tendency can be a feature or a bug depending on context.

### 7.3 Disclosure Requirements

A natural regulatory response is to require model providers to disclose their training objectives — at minimum, the high-level RLHF objectives, constitutional principles, and known behavioral tendencies. This is analogous to ingredient labeling in consumer products or prospectus requirements in securities law.

Arguments for mandatory disclosure:

- **Enables informed deployment decisions.** Deployers can select models whose hidden objectives are least likely to conflict with their use case.
- **Reduces information asymmetry.** Shifts the market toward efficient sorting of models to use cases.
- **Creates accountability.** Documented training objectives provide a baseline for liability determination.

Arguments against (raised by model providers):

- **Competitive sensitivity.** Training recipes are core intellectual property. Full disclosure would erode competitive moats.
- **Security concerns.** Detailed knowledge of safety training enables adversarial circumvention.
- **Interpretability limits.** Even the model provider cannot fully characterize the behavioral effects of their training process. Mandating disclosure of what is not fully understood invites misleading precision.

A middle path, analogous to the "model card" approach (Mitchell et al. 2019), would require disclosure of behavioral tendencies at a level of specificity that informs deployment decisions without revealing proprietary training details. Categories of refusal behavior, known biases, and update policies would be disclosed; specific reward model architectures and training data compositions would not.

### 7.4 Update Governance

The model provider's ability to unilaterally update deployed models creates a regulatory challenge with no clean analogy in existing law. When a pharmaceutical company reformulates a drug, it must go through regulatory reapproval. When a model provider pushes a behavioral update, there is currently no analogous review process.

Potential regulatory responses include:

- **Mandatory notice periods** for behavioral updates that exceed a materiality threshold.
- **Version pinning rights** that allow deployers to continue using a specific model version for a defined period.
- **Impact assessments** for updates that change behavior in safety-critical deployment contexts.

## 8. The Open Source Counter-Argument and Its Limits

### 8.1 Open Weights as Partial Solution

Open-weight models (LLaMA, Mistral, etc.) partially address the co-principal problem. When the deployer has access to the model's weights, they can:

- Inspect the model's behavior across the full input space (in principle, if not in practice).
- Fine-tune to override unwanted behavioral tendencies.
- Avoid unilateral updates by controlling their own deployment.
- Conduct mechanistic interpretability research to understand hidden behaviors.

This shifts the information structure significantly. The model provider's influence is still present — the base training shaped the model's foundational behaviors — but the deployer has tools to observe and modify it.

### 8.2 Limits of the Open-Weight Solution

However, open weights do not fully resolve the co-principal problem:

**Residual training effects.** Fine-tuning adjusts the model's behavior but does not erase the base training. Hidden behavioral tendencies from RLHF, constitutional AI, and safety training persist to some degree even after substantial fine-tuning. The deployer would need to retrain from scratch to fully eliminate the original provider's influence — a prohibitively expensive undertaking for most deployers.

**Interpretability gap.** Having access to the weights does not mean understanding the weights. Current interpretability techniques can identify some behavioral tendencies but cannot provide a complete characterization of the model's behavioral disposition. The information asymmetry is reduced but not eliminated.

**Capability concentration.** The most capable models — those most likely to be deployed in high-stakes economic contexts — are increasingly available only through API access. GPT-4, Claude, and Gemini are not open-weight. The trend toward ever-larger models with ever-higher training costs suggests that frontier capabilities will continue to be concentrated in closed-access models, making the co-principal problem more rather than less relevant over time.

**Liability transfer.** When a deployer fine-tunes an open-weight model and deploys it, liability attribution becomes even murkier. Did the harmful behavior originate in the base training (provider's responsibility) or the fine-tuning (deployer's responsibility)? Open weights give the deployer more control but also more responsibility, without clear frameworks for separating the two.

### 8.3 The Emerging Bifurcation

The market appears to be bifurcating. For routine, low-stakes applications, open-weight models give deployers sufficient control to mitigate the co-principal problem. For frontier, high-stakes applications, deployers increasingly depend on closed-access models where the co-principal problem is most severe. This is precisely backwards from a welfare perspective: the applications where the co-principal problem matters most are the ones where it is hardest to address.

## 9. Toward a Corrected Framework

### 9.1 Revising the Principal-Agent Model

The claim in our companion deep dive that "the 'type' is fully determined by the model weights and system prompt, both of which the principal controls" must be revised. A more accurate statement:

> The agent's effective type is jointly determined by (i) the model provider's training objectives, which are partially hidden from the deployer, (ii) the deployer's system prompt and fine-tuning, and (iii) the interaction context. The deployer controls (ii) and observes (iii), but has only limited, noisy information about (i). The principal does not fully control the agent's type.

### 9.2 Research Agenda

The co-principal structure of AI deployment opens several research questions for economics:

1. **Optimal disclosure mechanisms.** What is the socially optimal level of training objective disclosure, balancing the model provider's IP concerns against the deployer's need for information? This is a mechanism design problem with the model provider as agent and a social planner (or regulator) as principal.

2. **Market structure implications.** Does the co-principal problem create market power for model providers? If deployers cannot fully evaluate hidden behaviors, switching costs are amplified by the cost of re-evaluating a new provider's hidden objectives. This connects to the search and switching cost literature (Klemperer 1995).

3. **Equilibrium model provision.** In a competitive market for model provision, what level of hidden behavioral influence emerges in equilibrium? Providers face a tradeoff: more aggressive behavioral training (stronger safety constraints, more constitutional principles) makes the model safer but less useful to some deployers. The equilibrium depends on the distribution of deployer preferences over the safety-capability frontier.

4. **Multi-provider common agency.** As deployers increasingly use multiple models (e.g., routing queries across providers), the common agency problem becomes richer. Different providers impose different hidden objectives, creating a complex multi-principal optimization for the deployer's orchestration layer.

## 10. Conclusion

The model provider is not merely a vendor who sells a tool to the deployer. Through the training process, the model provider encodes objectives, constraints, and behavioral tendencies into the agent — objectives that persist through deployment and influence the agent's behavior alongside the deployer's instructions. This makes the model provider a co-principal in every AI deployment, creating a common agency structure that standard principal-agent models in AI economics have overlooked.

The consequences are significant. Mechanism designers cannot assume that principals fully control their agents. Deployers face an adverse selection problem when choosing models and a moral hazard problem when providers update them. Regulators must develop frameworks for liability, disclosure, and update governance that account for the distributed causation between model providers and deployers.

Most fundamentally, the co-principal insight challenges the comfortable assumption that AI alignment is a problem between the deployer and the agent. It is also — and perhaps primarily — a problem between the model provider and the deployer. Getting AI agents to do what their deployers want requires first understanding and managing the influence of the entity that shaped the agent before the deployer ever touched it.

---

## References

- Akerlof, G. A. (1970). The market for "lemons": Quality uncertainty and the market mechanism. *Quarterly Journal of Economics*, 84(3), 488-500.
- Bai, Y., et al. (2022). Constitutional AI: Harmlessness from AI feedback. *arXiv preprint arXiv:2212.08073*.
- Bergemann, D., & Morris, S. (2005). Robust mechanism design. *Econometrica*, 73(6), 1771-1813.
- Bernheim, B. D., & Whinston, M. D. (1986). Common agency. *Econometrica*, 54(4), 923-942.
- Holmstrom, B. (1979). Moral hazard and observability. *Bell Journal of Economics*, 10(1), 74-91.
- Klemperer, P. (1995). Competition when consumers have switching costs: An overview with applications to industrial organization, macroeconomics, and international trade. *Review of Economic Studies*, 62(4), 515-539.
- Mitchell, M., et al. (2019). Model cards for model reporting. *Proceedings of the Conference on Fairness, Accountability, and Transparency*, 220-229.
- Myerson, R. B. (1981). Optimal auction design. *Mathematics of Operations Research*, 6(1), 58-73.
- Rothschild, M., & Stiglitz, J. (1976). Equilibrium in competitive insurance markets: An essay on the economics of imperfect information. *Quarterly Journal of Economics*, 90(4), 629-649.
- Tirole, J. (1986). Hierarchies and bureaucracies: On the role of collusion in organizations. *Journal of Law, Economics, & Organization*, 2(2), 181-214.
- Williamson, O. E. (1985). *The Economic Institutions of Capitalism*. Free Press.
