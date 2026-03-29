# Formalization Audit Protocol

## Purpose
Verify that the formal claims in a philosophical argument about mathematics are
technically correct — that the formal systems are accurately described, that
logical inferences are valid in the claimed logic, and that meta-mathematical
results are applied within their scope.

## Steps

1. **Inventory formal claims** — List every claim in the argument that invokes
   a formal system, theorem, or logical principle. Lock `foundational_framework`,
   `logic_system`, and `formalization_level`.
2. **Verify system descriptions** — For each formal system mentioned, check:
   (a) Are the axioms stated correctly?
   (b) Is the claimed relationship to other systems accurate (e.g., "ZFC
       extends ZF with Choice" — correct; "type theory is stronger than
       set theory" — requires qualification)?
   (c) Are technical terms used in their standard sense?
3. **Check theorem citations** — For each cited theorem:
   (a) State the exact theorem with its hypotheses.
   (b) Verify that the hypotheses are satisfied in the context of the argument.
   (c) Check that the conclusion drawn matches what the theorem actually says.
   (d) Common failure: citing Goedel's incompleteness theorems without
       verifying that the system is recursively axiomatizable and sufficiently
       strong.
4. **Validate logical inferences** — Check that each inference step is valid
   in the logic the argument claims to use. Particular attention to:
   (a) Uses of excluded middle in supposedly constructive arguments.
   (b) Uses of the axiom of choice when choice-free reasoning is claimed.
   (c) Impredicative definitions in predicative frameworks.
   (d) Confusion between object language and metalanguage.
5. **Assess formalization claims** — If the argument claims that some informal
   mathematical reasoning can or cannot be formalized:
   (a) Has the formalization been exhibited or merely claimed?
   (b) Is the target system specified precisely?
   (c) Are known obstacles to formalization acknowledged?
6. **Check scope of meta-mathematical results** — Meta-mathematical results
   (completeness, incompleteness, independence, categoricity) apply to specific
   classes of systems. Verify that the argument doesn't overgeneralize:
   (a) Independence of CH from ZFC does not mean CH is "indeterminate."
   (b) Completeness of FOL does not mean all mathematical truth is capturable.
   (c) Categoricity of second-order PA does not resolve all foundational issues.
7. **Report findings** — Classify errors as: (a) fatal (argument invalidated),
   (b) repairable (argument weakened but salvageable), (c) inessential
   (technical inaccuracy that doesn't affect the philosophical point).

## Common Pitfalls
- Assuming all philosophical arguments need formal verification (some are
  purely conceptual and formalization is beside the point).
- Holding informal philosophical arguments to standards of formal proof.
- Missing that some formal claims are conventional abbreviations understood
  by specialists, not literal assertions.
- Conflating proof-theoretic and model-theoretic notions of consequence.

## Convention Lock Fields
- `foundational_framework`, `logic_system`, `formalization_level`,
  `proof_conception`, `mathematical_domain`
