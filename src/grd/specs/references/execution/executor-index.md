---
load_when:
  - "which reference to load"
  - "executor needs guidance"
  - "execution scenario"
tier: 1
context_cost: small
---

# Executor Reference Index

Maps execution scenarios to the correct reference file. Load this at execution start, then load the specific reference(s) needed for the current task.

## By Execution Scenario

| Scenario | Load These References |
|---|---|
| **Any derivation** | `references/shared/shared-protocols.md` (conventions), `references/execution/executor-verification-flows.md` (verification) |
| **QFT calculation** | `domains/physics/verification/domains/verification-domain-qft.md`, plus `domains/physics/protocols/perturbation-theory.md`, `domains/physics/protocols/renormalization-group.md`, `domains/physics/protocols/supersymmetry.md`, `domains/physics/protocols/asymptotic-symmetries.md`, `domains/physics/protocols/generalized-symmetries.md`, or `domains/physics/protocols/conformal-bootstrap.md` when fixed-point CFT data or crossing constraints are central |
| **Condensed matter** | `domains/physics/verification/domains/verification-domain-condmat.md`, `references/execution/executor-subfield-guide.md` §Condensed Matter |
| **Statistical mechanics / simulation** | `domains/physics/verification/domains/verification-domain-statmech.md`, `domains/physics/protocols/monte-carlo.md` or `domains/physics/protocols/molecular-dynamics.md`; add `domains/physics/protocols/conformal-bootstrap.md` when the target is critical exponents, universality class data, or the critical-point CFT |
| **General relativity / cosmology** | `domains/physics/verification/domains/verification-domain-gr-cosmology.md`, plus `domains/physics/protocols/general-relativity.md`, `domains/physics/protocols/de-sitter-space.md`, `domains/physics/protocols/asymptotic-symmetries.md`, or `domains/physics/protocols/cosmological-perturbation-theory.md` depending on regime |
| **Quantum gravity / holography** | `domains/physics/subfields/quantum-gravity.md`, plus `domains/physics/verification/domains/verification-domain-gr-cosmology.md`, `domains/physics/verification/domains/verification-domain-qft.md`, and `domains/physics/protocols/holography-ads-cft.md`, `domains/physics/protocols/de-sitter-space.md`, or `domains/physics/protocols/asymptotic-symmetries.md` depending on asymptotics |
| **String theory / compactification** | `domains/physics/subfields/string-theory.md`, plus `domains/physics/verification/domains/verification-domain-qft.md`, `domains/physics/verification/domains/verification-domain-mathematical-physics.md`, and `domains/physics/protocols/supersymmetry.md`, `domains/physics/protocols/holography-ads-cft.md`, `domains/physics/protocols/de-sitter-space.md`, or `domains/physics/protocols/path-integrals.md` depending on regime |
| **AMO physics** | `domains/physics/verification/domains/verification-domain-amo.md`, `references/execution/executor-subfield-guide.md` §AMO |
| **Nuclear / particle** | `domains/physics/verification/domains/verification-domain-nuclear-particle.md`, `domains/physics/protocols/phenomenology.md`, and `references/execution/executor-subfield-guide.md` §Nuclear & Particle Physics |
| **Astrophysics** | `domains/physics/verification/domains/verification-domain-astrophysics.md`, `references/execution/executor-subfield-guide.md` §Astrophysics |
| **Mathematical physics** | `domains/physics/verification/domains/verification-domain-mathematical-physics.md`, `references/execution/executor-subfield-guide.md` §Mathematical Physics, plus `domains/physics/protocols/conformal-bootstrap.md` or `domains/physics/protocols/holography-ads-cft.md` for CFT-heavy problems |
| **Algebraic QFT / operator algebras** | `domains/physics/subfields/algebraic-qft.md`, `domains/physics/verification/domains/verification-domain-algebraic-qft.md`, `domains/physics/protocols/algebraic-qft.md`, and `references/execution/executor-subfield-guide.md` §Algebraic Quantum Field Theory |
| **String field theory** | `domains/physics/subfields/string-field-theory.md`, `domains/physics/verification/domains/verification-domain-string-field-theory.md`, `domains/physics/protocols/string-field-theory.md`, and `references/execution/executor-subfield-guide.md` §String Field Theory; add `domains/physics/subfields/string-theory.md` when worldsheet, D-brane, or compactification input is part of the setup |
| **Conformal bootstrap / CFT** | `domains/physics/verification/domains/verification-domain-mathematical-physics.md`, `domains/physics/protocols/conformal-bootstrap.md`, and `domains/physics/subfields/qft.md` or `domains/physics/subfields/mathematical-physics.md` depending on whether the project is field-theoretic or structural |
| **Numerical computation** | `domains/physics/protocols/numerical-computation.md`, `domains/physics/protocols/symbolic-to-numerical.md`, `domains/physics/verification/core/verification-numerical.md` |
| **Paper writing** | `domains/physics/publication/figure-generation-templates.md`, `domains/physics/publication/bibtex-standards.md` |
| **Debugging / error recovery** | `references/execution/execute-plan-recovery.md`, `references/execution/executor-deviation-rules.md` |

## By Execution Phase

| Phase | Load These References |
|---|---|
| **Pre-execution setup** | `references/shared/shared-protocols.md` §Convention Lock, `references/execution/executor-subfield-guide.md` (subfield section) |
| **During execution** | `references/execution/executor-verification-flows.md`, `references/execution/executor-task-checkpoints.md` |
| **Deviation from plan** | `references/execution/executor-deviation-rules.md` |
| **Checkpoint / save** | `references/execution/execute-plan-checkpoints.md`, `references/orchestration/checkpoints.md` |
| **Task completion** | `references/execution/executor-completion.md`, `references/execution/execute-plan-validation.md` |
| **Error recovery** | `references/execution/execute-plan-recovery.md` |

## By Error Class Concern

| Concern | Load These References |
|---|---|
| **Convention mismatch suspected** | `domains/physics/conventions/conventions-quick-reference.md`, `references/shared/shared-protocols.md` §Convention Tracking |
| **LLM error patterns** | `domains/physics/verification/audits/verification-gap-summary.md` (compact), `domains/physics/verification/errors/llm-errors-core.md` or relevant part file |
| **Numerical issues** | `domains/physics/verification/core/verification-numerical.md`, `domains/physics/protocols/numerical-computation.md` |
| **Reproducibility** | `domains/physics/protocols/reproducibility.md` |

## Verification Domain Files

| Domain | File |
|---|---|
| QFT / particle / GR | `domains/physics/verification/domains/verification-domain-qft.md` |
| Condensed matter | `domains/physics/verification/domains/verification-domain-condmat.md` |
| Quantum info | `domains/physics/verification/domains/verification-domain-quantum-info.md` |
| AMO | `domains/physics/verification/domains/verification-domain-amo.md` |
| Soft matter | `domains/physics/verification/domains/verification-domain-soft-matter.md` |
| Fluid / plasma | `domains/physics/verification/domains/verification-domain-fluid-plasma.md` |
| Statistical mechanics / cosmology / fluids | `domains/physics/verification/domains/verification-domain-statmech.md` |
| General relativity / cosmology | `domains/physics/verification/domains/verification-domain-gr-cosmology.md` |
| Quantum gravity / holography | `domains/physics/verification/domains/verification-domain-gr-cosmology.md` + `domains/physics/verification/domains/verification-domain-qft.md` |
| String theory / compactification | `domains/physics/verification/domains/verification-domain-qft.md` + `domains/physics/verification/domains/verification-domain-mathematical-physics.md` + `domains/physics/verification/domains/verification-domain-gr-cosmology.md` |
| AMO physics | `domains/physics/verification/domains/verification-domain-amo.md` |
| Nuclear / particle physics | `domains/physics/verification/domains/verification-domain-nuclear-particle.md` |
| Astrophysics | `domains/physics/verification/domains/verification-domain-astrophysics.md` |
| Mathematical physics | `domains/physics/verification/domains/verification-domain-mathematical-physics.md` |
| Algebraic QFT / operator algebras | `domains/physics/verification/domains/verification-domain-algebraic-qft.md` |
| String field theory | `domains/physics/verification/domains/verification-domain-string-field-theory.md` |

## Protocol Files

See `references/shared/shared-protocols.md` §Detailed Protocol References for the full protocol index.
