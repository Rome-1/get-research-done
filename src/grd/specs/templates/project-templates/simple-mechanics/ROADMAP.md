# Roadmap

## Phases

- [ ] **Phase 1: Derive Hamiltonian and State Energy Conservation** - Define the SHO Hamiltonian, derive dH/dt = 0 from Hamilton's equations, verify through heuristic checks and formal proof

## Phase Details

### Phase 1: Derive Hamiltonian and State Energy Conservation

**Goal:** Prove that the 1D SHO Hamiltonian is conserved along trajectories of Hamilton's equations.

**Success Criteria:**

1. [Hamiltonian H(q,p) = p^2/(2m) + m*omega^2*q^2/2 written with all parameters identified]
2. [Hamilton's equations derived: dq/dt = p/m, dp/dt = -m*omega^2*q]
3. [dH/dt = 0 derived by chain rule + Hamilton's equations]
4. [Heuristic checks passing: dimensional analysis, limiting cases, symmetry]
5. [Formal Lean proof of energy conservation typechecks]

**Claims:**

- **derived-energy-conservation**: For all m > 0, omega > 0, and all solutions (q(t), p(t)) of Hamilton's equations, dH/dt = 0.

Plans:

- [ ] 01-01: [Define Hamiltonian, derive Hamilton's equations, compute dH/dt]
- [ ] 01-02: [Run heuristic verification checks (Tier 1-4)]
- [ ] 01-03: [Formalize and prove energy conservation in Lean (Tier 5)]
