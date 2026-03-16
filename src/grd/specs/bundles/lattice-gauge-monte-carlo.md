---
bundle_id: lattice-gauge-monte-carlo
bundle_version: 1
title: Lattice-Gauge Monte Carlo
summary: Gauge-theory Monte Carlo work with topology control, continuum and finite-volume extrapolation, and benchmarked hadronic observables.
selection_tags:
  - "framework:lattice-gauge-theory"
  - "work-mode:monte-carlo-simulation"
  - "validation:topology-continuum-benchmarks"
trigger:
  any_terms:
    - lattice qcd
    - lattice gauge
    - wilson fermion
    - staggered fermion
    - topology freezing
    - gradient flow
    - continuum extrapolation
    - scale setting
    - hadron correlator
    - hybrid monte carlo
  any_tags:
    - acceptance-kind:convergence
    - acceptance-kind:benchmark
    - acceptance-kind:cross_method
    - reference-role:benchmark
  exclusive_with:
    - stat-mech-simulation
  min_term_matches: 2
  min_tag_matches: 1
  min_score: 10
assets:
  project_types:
    - path: templates/project-types/nuclear-particle.md
      required: true
  subfield_guides:
    - path: domains/physics/subfields/qft.md
      required: true
    - path: domains/physics/subfields/nuclear-particle.md
      required: true
  verification_domains:
    - path: domains/physics/verification/domains/verification-domain-qft.md
      required: true
    - path: domains/physics/verification/domains/verification-domain-nuclear-particle.md
      required: true
    - path: domains/physics/verification/domains/verification-domain-statmech.md
  protocols_core:
    - path: domains/physics/protocols/lattice-gauge-theory.md
      required: true
    - path: domains/physics/protocols/monte-carlo.md
      required: true
    - path: domains/physics/protocols/renormalization-group.md
  protocols_optional:
    - path: domains/physics/protocols/group-theory.md
    - path: domains/physics/protocols/perturbation-theory.md
  execution_guides:
    - path: references/execution/executor-subfield-guide.md
anchor_prompts:
  - State the gauge action, fermion discretization, scale-setting observable, and target continuum or chiral limit before production measurements.
  - Ask whether topology, excited-state contamination, or finite-volume systematics are the decisive failure mode for the claim.
reference_prompts:
  - Keep trusted lattice averages, ensemble benchmarks, and scale-setting conventions visible through planning and verification.
  - Preserve renormalization, normalization, and operator-basis conventions when comparing across ensembles or literature.
estimator_policies:
  - Treat autocorrelation, effective-mass plateaus, and correlated continuum or chiral fits as explicit estimator choices, not background implementation detail.
  - Record how topology, finite-volume effects, and excited-state contamination are measured and propagated into uncertainties.
decisive_artifact_guidance:
  - Produce an ensemble table with lattice spacing, volume, m_pi L, configuration counts, and autocorrelation diagnostics.
  - Produce continuum, chiral, or finite-volume fit artifacts with covariance-aware uncertainties and fit-family notes.
  - Preserve topology or gradient-flow diagnostics whenever topology, scale setting, or UV smoothing matters to correctness.
verifier_extensions:
  - name: topology-and-autocorrelation-audit
    rationale: Lattice Monte Carlo can look converged while topology or long autocorrelations silently invalidate the result.
    check_ids:
      - "5.5"
      - "5.14"
      - "5.16"
  - name: continuum-and-fit-family-audit
    rationale: Credible lattice claims require the contracted continuum or asymptotic limit plus a justified extrapolation family.
    check_ids:
      - "5.6"
      - "5.15"
      - "5.18"
---

# Lattice-Gauge Monte Carlo Bundle

Use this bundle for lattice gauge and lattice-QCD projects where topology,
continuum extrapolation, finite-volume control, and benchmarked hadronic
observables matter more than generic Monte Carlo hygiene alone.
