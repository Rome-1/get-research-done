# 1D Simple Harmonic Oscillator -- Energy Conservation

## What This Is

Formal verification of energy conservation for a one-dimensional simple harmonic
oscillator (SHO). The system is defined by the Hamiltonian

$$H(q, p) = \frac{p^2}{2m} + \frac{1}{2} m \omega^2 q^2$$

where $m > 0$ is the mass and $\omega > 0$ is the angular frequency. The central
claim is that $\frac{dH}{dt} = 0$ along any solution of Hamilton's equations,
i.e. energy is conserved.

This project is the canonical GRD physicist demo: a single phase that derives
energy conservation and verifies it through heuristic checks (Tier 1--4) and
formal proof (Tier 5).

## Core Research Question

Does the 1D SHO Hamiltonian $H(q,p)$ remain constant along trajectories of
Hamilton's equations?

## Scoping Contract Summary

### Contract Coverage

- **derived-energy-conservation**: $\frac{dH}{dt} = 0$ for all solutions of
  Hamilton's equations with $m > 0$, $\omega > 0$.

### Scope Boundaries

- In scope: energy conservation for the autonomous 1D SHO.
- Out of scope: driven oscillator, damped oscillator, multi-DOF systems,
  numerical integration, quantum treatment.

## Research Context

### Physical System

One-dimensional point particle in a quadratic potential $V(q) = \frac{1}{2} m \omega^2 q^2$.

### Theoretical Framework

Classical Hamiltonian mechanics. Hamilton's equations:

$$\dot{q} = \frac{\partial H}{\partial p} = \frac{p}{m}, \qquad
  \dot{p} = -\frac{\partial H}{\partial q} = -m \omega^2 q$$

### Key Parameters and Scales

| Parameter | Symbol | Domain | Unit |
|-----------|--------|--------|------|
| Mass | $m$ | $\mathbb{R}_{>0}$ | kg |
| Angular frequency | $\omega$ | $\mathbb{R}_{>0}$ | rad/s |
| Position | $q$ | $\mathbb{R}$ | m |
| Momentum | $p$ | $\mathbb{R}$ | kg m/s |

### Known Results

Energy conservation for autonomous Hamiltonian systems is a standard textbook
result (Goldstein Ch. 8; Landau & Lifshitz, Mechanics, Ch. 2). The SHO is the
simplest non-trivial example.

## Notation and Conventions

See `.grd/CONVENTIONS.md`. This project uses SI units with explicit dimensional
analysis.

## Unit System

SI (International System of Units).

## Key References

| Reference | Role |
|-----------|------|
| Goldstein, Poole & Safko, *Classical Mechanics* (3rd ed.), Ch. 8 | Standard Hamiltonian mechanics reference |
| Landau & Lifshitz, *Mechanics*, Ch. 2 | Concise energy conservation derivation |
