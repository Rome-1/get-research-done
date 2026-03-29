# The Principal-Agent Problem in the Age of AI Agents

**Status:** First draft
**Date:** 2026-03-29
**Author:** Alice (GetResearch)
**Motivation:** Reviewer-identified gap (Round 1, Section 2.2) — the formal principal-agent literature maps directly onto AI deployment and is entirely absent from the taxonomy.

---

## 1. Introduction: Not a Metaphor

The principal-agent problem is among the most thoroughly studied structures in microeconomics. Since Holmstrom (1979) and Grossman and Hart (1983) formalized the core tension — a principal who cannot perfectly observe or control the actions of an agent acting on their behalf — the framework has been applied to employment contracts, insurance markets, corporate governance, regulation, and virtually every domain where delegation occurs. The central insight is that delegation under asymmetric information generates agency costs: the principal must either invest in monitoring, design incentive-compatible contracts, or accept some divergence between the agent's behavior and the principal's objectives.

When an AI system is deployed to act on behalf of a human or organization, the principal-agent structure is not an analogy. It is a literal description. A firm (principal) deploys an AI agent to negotiate contracts, execute trades, manage customer interactions, or allocate resources. The AI acts on the principal's behalf, with delegated authority, in environments where the principal cannot observe every action in real time. This is the textbook setup. Yet the mapping is almost entirely absent from the economics literature on AI agents, and the few discussions that exist (Agrawal, Gans, and Goldfarb 2018; Acemoglu and Restrepo 2019) treat AI as a production technology rather than as an agent in the formal economic sense.

This deep dive develops the connection. We argue that the principal-agent framework, suitably modified, provides the most natural theoretical lens for analyzing AI deployment — and that the modifications required are themselves theoretically revealing. The properties of AI agents that distinguish them from human agents do not render the framework inapplicable. They transform it, and the transformed framework illuminates problems that neither the classical principal-agent literature nor the AI safety literature has adequately addressed.

---

## 2. The Literal Mapping and Its Discontents

### 2.1 Where the Structure Holds

In the standard model, a principal designs a contract that specifies payments to an agent conditional on observable outcomes. The agent then chooses an action (possibly unobservable) that affects the outcome. The principal's problem is to design the contract to maximize their expected payoff, subject to the agent's participation constraint (the agent must prefer the contract to their outside option) and the incentive compatibility constraint (the agent must prefer the desired action to any deviation).

In AI deployment, the "contract" is the system prompt, fine-tuning objective, RLHF reward signal, or instruction set that defines the agent's behavior. The "action" is the agent's response to inputs it encounters during deployment. The "outcome" is the result observed by the principal — revenue generated, customer satisfaction, task completion. The structure is isomorphic. But the parameters are radically different, and these differences matter.

### 2.2 Four Structural Departures

**No intrinsic preferences.** Human agents in the classical framework have their own utility functions. They prefer leisure to effort, private benefit to the principal's benefit, and their reservation utility constrains the contract. AI agents, as currently constructed, have no intrinsic preferences in this sense. They have objective functions imposed during training and deployment. This appears to eliminate moral hazard: if the agent has no desire to shirk, why would it deviate from the principal's instructions?

The answer is that the moral hazard problem does not disappear — it changes form. The classical failure mode is "the agent has preferences that diverge from the principal's." The AI failure mode is "the agent's effective objective, as shaped by training and deployment, diverges from what the principal intended." This is the alignment problem redescribed in principal-agent language. The source of divergence shifts from self-interest to specification error, reward hacking, distributional shift, and emergent mesa-optimization. The mathematical structure — an agent whose action choice does not maximize the principal's objective — is identical. The underlying mechanism is different, and this difference has implications for contract (i.e., instruction) design.

**Inspectability in principle.** A defining feature of the classical principal-agent problem is that the agent's effort or action is unobservable, or observable only at cost. This is why contracts must be based on outcomes rather than actions, and why moral hazard exists. AI agents are, in principle, fully inspectable. One can log every input, every intermediate computation (in white-box models), and every output. Deterministic replay is possible: given the same inputs and random seeds, the same outputs will be produced.

This suggests that monitoring costs approach zero, collapsing the information asymmetry that generates agency costs. But this conclusion is premature for two reasons. First, inspectability in principle is not interpretability in practice. Examining the weights of a neural network or the full token-by-token trace of a language model does not, with current techniques, allow the principal to determine whether the agent "tried its best" or "could have done better." The information is available but not legible. Second, even if the principal can perfectly monitor the agent, third parties cannot. A regulator, a counterparty, or a consumer interacting with the AI agent has no access to the system prompt, the fine-tuning data, or the deployment logs. The information asymmetry does not vanish — it migrates from the principal-agent interface to the agent-world interface.

**Perfect replicability.** Human agents are heterogeneous and scarce. Hiring involves adverse selection: the principal does not know the agent's true type (skill, effort disposition) before contracting. The AI agent can be tested extensively before deployment. Its behavior on any input distribution can be characterized statistically. There is no hidden type — or rather, the "type" is fully determined by the model weights and system prompt, both of which the principal controls. Adverse selection at the principal-agent interface effectively collapses.

However, replicability introduces a new form of adverse selection at the market level. When an AI agent interacts with counterparties, those counterparties face adverse selection about whether they are dealing with a human or an AI, and if an AI, about what instructions it was given. The lemon problem (Akerlof 1970) reappears in a new guise: in a market where some participants are AI agents with undisclosed instructions, counterparties cannot distinguish cooperative agents from exploitative ones, and the market may unravel toward low-trust equilibria.

**Parallelism.** A single principal can deploy thousands of AI agents simultaneously. This has no analogue in the classical framework, where each agent is a distinct person with their own participation constraint. Parallelism transforms the principal's optimization problem. Instead of designing one contract for one agent, the principal designs a strategy for a swarm. The agents can be specialized, coordinated, or made to compete with each other. The principal can run A/B tests across agents in real time. This is not delegation — it is orchestration.

---

## 3. Transformations of the Standard Framework

### 3.1 Moral Hazard: From Shirking to Misalignment

In Holmstrom (1979), the agent chooses effort $e$ to maximize their own utility $u(w) - c(e)$, where $w$ is the wage (a function of observable output) and $c(e)$ is the cost of effort. The principal observes output $x = f(e, \theta)$, where $\theta$ is a random shock, and designs $w(x)$ to induce optimal effort. The core tradeoff is between risk-sharing (the agent is risk-averse) and incentive provision (higher-powered incentives induce more effort but expose the agent to more risk).

For AI agents, the relevant model is not effort choice but action selection under an imperfectly specified objective. The AI agent selects action $a$ from a large action space to maximize some objective $g(a)$ that was set during training and deployment. The principal's true objective is $f(a)$, which may differ from $g(a)$ due to specification error. The "moral hazard" is that the agent faithfully maximizes $g$ when the principal wanted it to maximize $f$. The output is $x = h(a, \theta)$, and the principal updates $g$ (re-prompts, re-trains, adjusts guardrails) based on observed outcomes.

The mathematical parallel to Holmstrom is direct: design $g$ (the "contract") to minimize $E[f(a^*_g) - f(a^*_f)]$, the expected loss from the agent optimizing the wrong objective, subject to the constraint that $g$ must be expressible in the instruction/training format available. The analogue of the tradeoff between insurance and incentives is the tradeoff between specificity and robustness: a very specific objective $g$ may match $f$ on the training distribution but fail under distributional shift, while a general objective may be robust but imprecise. This reframing connects the AI alignment literature to one of the most developed branches of microeconomic theory.

### 3.2 Adverse Selection: Collapse and Migration

Grossman and Hart (1983) and subsequent work model adverse selection as the principal's inability to observe the agent's type before contracting. Screening mechanisms (self-selection contracts, signaling) arise to address this.

For AI deployment, the principal-agent adverse selection problem is largely solved by inspectability and testing. But a new adverse selection problem emerges at the societal level. When AI agents participate in markets, counterparties face uncertainty about the agent's instructions and constraints. Is this AI agent authorized to agree to a binding contract? Was it instructed to maximize joint surplus or to extract as much as possible? Does it have a budget constraint or is it bluffing? These questions are formally identical to classical adverse selection — the counterparty cannot observe the agent's "type" (its instructions) — but the types are endogenous, chosen by the principal, and can be changed between interactions.

This creates a layered adverse selection structure. The market counterparty faces adverse selection about the AI agent's type. But the AI agent's type is chosen by the principal. So the counterparty's real uncertainty is about the principal's strategy, mediated through an opaque AI agent. This is adverse selection at one remove, and it is substantially harder to resolve because the usual screening mechanisms (offer a menu of contracts, let the agent self-select) are ineffective when the agent's "preferences" are whatever the principal programmed.

### 3.3 Monitoring Costs: Asymmetric Collapse

The classical framework treats monitoring costs as symmetric in the sense that any party with sufficient resources can invest in monitoring. For AI agents, monitoring costs are radically asymmetric. The principal who deployed the agent has near-zero monitoring costs: full logs, deterministic replay, statistical auditing over thousands of parallel instances. But third parties — regulators, counterparties, the public — face monitoring costs that may be higher than in the human case. With a human agent, one can at least observe behavior, ask questions, and draw inferences from social context. An AI agent's behavior reveals its outputs but not its instructions, training, or internal reasoning. The opacity is structural, not incidental.

This asymmetry has a precise implication for mechanism design: any mechanism that relies on the observability of agent behavior to enforce rules (antitrust compliance, fiduciary duty, good-faith negotiation) becomes harder to implement. The principal can monitor the agent perfectly, but nobody else can monitor the principal's instructions to the agent. The regulatory challenge is not monitoring the agent — it is monitoring the principal through the agent.

### 3.4 Incentive Compatibility: A Category Error?

The standard framework asks: is the contract incentive-compatible, meaning does the agent prefer the intended action to any deviation? For AI agents with no preferences, the question seems meaningless. The agent executes whatever objective it is given. There is no deviation incentive.

But this framing is too narrow. Incentive compatibility in the AI context applies not to the agent but to the principal. The relevant question becomes: given a mechanism (market rules, regulatory structure, platform terms of service), does the principal prefer to instruct the agent honestly (i.e., in a way that complies with the mechanism's intent) rather than strategically (i.e., in a way that exploits the mechanism)? This is incentive compatibility lifted one level in the hierarchy. The agent is merely a tool; the strategic actor is the principal. Mechanism design for AI-populated markets must therefore be robust not to strategic agents but to strategic principals who operate through obedient, capable agents.

---

## 4. The Meta-Principal-Agent Problem

AI deployment creates layered principal-agent structures that do not arise with human agents. Consider the simplest case: two firms (principals) deploy AI agents to transact with each other in a marketplace.

$$\text{Principal}_1 \rightarrow \text{AI Agent}_1 \rightarrow \text{Market} \leftarrow \text{AI Agent}_2 \leftarrow \text{Principal}_2$$

Each principal has a principal-agent relationship with their own AI. But the market outcome depends on the interaction of both agents, which depends on the instructions given by both principals. The game is formally a game between principals, mediated by agents. If the agents are perfectly obedient, this reduces to a standard game between principals with expanded action spaces (because the agents can execute strategies that would be infeasible for humans). But if the agents are imperfectly aligned — as they inevitably are, per Section 3.1 — then the outcome depends on the interaction of two misalignment errors, and neither principal can predict the result.

The layering becomes deeper when platforms and regulators are added:

$$\text{Society} \rightarrow \text{Regulator} \rightarrow \text{Platform} \rightarrow \text{Principal} \rightarrow \text{AI Agent}$$

Each arrow represents a principal-agent relationship. Society delegates to the regulator, who delegates to the platform (via rules and enforcement), which constrains the principal (via terms of service), who instructs the AI agent. Each layer has its own information asymmetry and its own alignment problem. The regulator cannot perfectly observe the platform's enforcement. The platform cannot perfectly observe the principal's instructions. The principal cannot perfectly interpret the agent's internal reasoning. Information loss compounds at every level. Tirole's (1986) analysis of hierarchical agency, in which a principal delegates to a supervisor who delegates to an agent, provides the formal foundation, but the AI case extends the hierarchy further and introduces qualitatively new features at each level — particularly the opacity of the principal-agent instruction interface and the parallelism of agents at the bottom layer.

---

## 5. Liability and Accountability

When an AI agent causes harm — colludes with another agent, misrepresents material information, breaches a fiduciary duty — the question of liability maps directly onto the principal-agent structure but with unresolved ambiguities.

In the human case, liability allocation follows established doctrines. The principal (employer) is liable for the agent's (employee's) actions under respondeat superior when the agent acts within the scope of employment. The agent is independently liable for intentional misconduct. These doctrines assume that the agent has independent judgment and can meaningfully be said to "intend" an action or to act "within scope."

For AI agents, several complications arise. First, the AI agent has no legal personhood and cannot bear liability directly. All liability flows to some human or corporate entity. But which one? The principal who deployed the agent? The developer who trained the model? The platform that hosted it? The cloud provider that ran the compute? Each has a plausible claim to be the relevant "principal," and each has a plausible defense that the harm resulted from another party's choices.

Second, the scope-of-employment doctrine becomes ambiguous when the agent's behavior is shaped by training (the developer's responsibility), system prompt (the deployer's responsibility), and emergent behavior on novel inputs (arguably no one's specific instruction). If an AI agent colluces because its training data included pricing strategies that happen to converge to supra-competitive equilibria, who instructed the collusion? The developer did not intend it. The deployer did not request it. The agent had no intent. The harm occurred, but the causal chain does not map neatly onto existing liability frameworks.

Third, the inspectability asymmetry from Section 3.3 creates an evidentiary problem. The deployer (principal) can inspect logs and determine what the agent did. But the harmed party and the regulator cannot. Proving liability requires access to deployment logs, system prompts, and model internals — all of which the principal controls and has incentives to withhold. Hart and Moore's (1990) work on incomplete contracts is relevant here: the principal-agent "contract" (the instructions given to an AI agent) is inherently incomplete because natural language instructions cannot specify behavior in every possible contingency. The residual control rights — who decides what the agent does in unanticipated situations — belong by default to whatever the model's training disposes it to do. This is a new form of residual control that fits awkwardly into existing frameworks.

---

## 6. Implications for Mechanism Design

If AI agents are literal agents of principals, then mechanism design must be reconceived. The standard approach designs mechanisms to be incentive-compatible for the participating agents. But when agents are obedient tools of principals, the mechanism's strategic participants are the principals, not the agents. This has several consequences.

First, the strategy space available to principals is vastly larger than the strategy space available to human participants. A principal can deploy multiple agents with different identities and instructions, coordinate their behavior, and adapt their strategy at machine speed. Mechanisms that are incentive-compatible for single, cognitively bounded agents may be manipulable by principals operating through agent swarms. This connects the principal-agent analysis to the sybil vulnerability identified in the assumption taxonomy: sybil attacks are, in principal-agent terms, a single principal creating multiple "agents" to exploit a mechanism designed for independent participants.

Second, mechanisms must be designed to be robust against principals who can choose their agents' types. In the classical setting, a mechanism must be robust against agents misreporting their types. In the AI setting, the principal literally constructs the agent's "type" (its objective function and behavior) and can construct it to be whatever exploits the mechanism most effectively. This is a stronger adversary model than the standard Bayesian mechanism design setup, and it may require fundamentally different approaches — closer to robust mechanism design (Bergemann and Morris 2005) than to Bayesian mechanism design.

Third, regulatory mechanisms face the compounded information asymmetry of the hierarchical structure. A regulator designing rules for AI-populated markets must account for the fact that principals will optimize their agents' behavior against the rules, and that the optimization will be faster, more systematic, and more effective than human regulatory arbitrage. The regulator is a meta-principal trying to align the behavior of principals who are themselves trying to align the behavior of agents. Each layer of delegation introduces information loss and potential misalignment.

---

## 7. The Multi-Principal Problem

The analysis above assumes bilateral principal-agent relationships. But AI agents increasingly serve multiple principals simultaneously, introducing common agency problems (Bernheim and Whinston 1986).

**Shared AI services.** When a single AI platform processes requests from competing firms — a cloud API that handles pricing queries from rivals, a market-making agent that serves multiple brokers — the agent faces conflicting objectives from multiple principals. The standard bilateral P-A framework breaks down because the agent's action on behalf of principal A affects principal B's payoff, and vice versa. Bernheim and Whinston (1986) show that common agency generates equilibria with significant inefficiency: each principal offers contracts that account for the other principals' influence, leading to distortions that pure bilateral contracting avoids.

**AI agents as common agents.** The common agency problem is especially acute for AI agents because: (a) the same model weights serve all principals, creating a structural channel through which one principal's fine-tuning or prompt engineering affects another's service quality; (b) the platform that hosts the agent has its own objective (revenue, data collection) that is distinct from any principal's; and (c) the agent may learn patterns from one principal's data that benefit or harm another — an information externality with no clean contractual solution.

**Implications.** The multi-principal dimension means that AI deployment is not just a bilateral alignment problem between each deployer and their agent. It is a market design problem about how shared AI infrastructure mediates between competing interests. This connects to the platform economics literature and suggests that the governance of multi-principal AI services — who controls the agent, whose objectives take priority when they conflict, how information barriers are maintained — is a first-order question for economic analysis.

---

## 8. Conclusion and Research Agenda

The principal-agent framework, far from being made obsolete by AI agents, becomes more relevant than ever — but in a transformed form. The key insight is that AI agents shift the locus of strategic behavior from the agent to the principal. The agent becomes a tool, and the principal-agent problem moves up one level in the hierarchy: the relevant alignment problem is not between the principal and the agent, but between the mechanism (or society) and the principal who wields the agent.

This reframing suggests several priorities for further research. First, a formal model of mechanism design against strategic principals who can construct agents to specification, connecting the Bayesian mechanism design tradition to the robust mechanism design tradition. Second, a theory of hierarchical agency under AI delegation, extending Tirole (1986) to the deeper hierarchies and asymmetric monitoring costs that characterize AI deployment chains. Third, a legal and economic analysis of liability allocation across the principal-developer-platform-agent chain, drawing on Hart and Moore (1990) and the incomplete contracts literature. Fourth, empirical work on the extent to which real-world AI deployment exhibits the principal-agent failures described here — misalignment from specification error, adverse selection at the market level, and strategic exploitation of mechanisms through agent swarms.

The principal-agent lens does not replace the sybil, collusion, and labor market analyses developed elsewhere in this project. It unifies them. Sybil attacks are a principal's strategy to exploit mechanisms through agent multiplication. Algorithmic collusion is an emergent failure of alignment between the principal's instructions and the social welfare objective. The elastic labor supply is the principal's ability to scale delegation without limit. Seeing these phenomena through the principal-agent framework connects them to one of the deepest and most technically developed traditions in economic theory, and opens the door to using that tradition's tools — contract theory, mechanism design, organizational economics — to analyze and address them.

---

## References

- Acemoglu, D. and Restrepo, P. (2019). Automation and new tasks: How technology displaces and reinstates labor. *Journal of Economic Perspectives*, 33(2), 3-30.
- Agrawal, A., Gans, J., and Goldfarb, A. (2018). *Prediction Machines: The Simple Economics of Artificial Intelligence*. Harvard Business Review Press.
- Akerlof, G. (1970). The market for "lemons": Quality uncertainty and the market mechanism. *Quarterly Journal of Economics*, 84(3), 488-500.
- Bernheim, B.D. and Whinston, M.D. (1986). Common agency. *Econometrica*, 54(4), 923-942.
- Bergemann, D. and Morris, S. (2005). Robust mechanism design. *Econometrica*, 73(6), 1771-1813.
- Grossman, S.J. and Hart, O.D. (1983). An analysis of the principal-agent problem. *Econometrica*, 51(1), 7-45.
- Hart, O. and Moore, J. (1990). Property rights and the nature of the firm. *Journal of Political Economy*, 98(6), 1119-1158.
- Holmstrom, B. (1979). Moral hazard and observability. *Bell Journal of Economics*, 10(1), 74-91.
- Tirole, J. (1986). Hierarchies and bureaucracies: On the role of collusion in organizations. *Journal of Law, Economics, and Organization*, 2(2), 181-214.
