---
load_when:
  - "verification hierarchy"
  - "plan-checker verifier mapping"
  - "cross-agent verification"
tier: 2
context_cost: small
---

# Verification Hierarchy Mapping

Maps verification responsibilities across the three verification agents: plan-checker, verifier, and consistency-checker. Load this when you need to understand scope boundaries or cross-reference checks between agents.

---

## Agent Scope Boundaries

| Agent | Scope | Timing | Subject | Key question |
|---|---|---|---|---|
| **grd-plan-checker** | Plan DESIGN quality | Before execution | Plans (`PLAN.md`) | Will this plan achieve the goal safely and decisively? |
| **grd-verifier** | Within-phase RESULT correctness | After execution | Research outputs and artifacts | Did the phase actually produce a correct result? |
| **grd-consistency-checker** | Between-phase CONSISTENCY | After any phase | Convention locks, dependencies, and value handoffs | Are phases coherent with one another? |

**Non-overlapping responsibilities:**

- Plan-checker does not prove mathematical correctness of results that do not exist yet.
- Verifier does not redesign plan scope once execution has already happened.
- Consistency-checker does not replace within-phase verification.

---

## Plan-Checker Dimensions To Verifier Families

| Plan-checker dimension | Step | Verifier follow-through |
|---|---|---|
| Dim 1: Research Question Coverage | 4 | Plan-only |
| Dim 2: Task Completeness | 5 | Plan-only |
| Dim 3: Mathematical Prerequisites | 6 | Universal checks such as `5.1`, `5.2`, `5.3`, plus domain checklists when the formal machinery is delicate |
| Dim 4: Approximation Validity | 7 | `5.3`, `5.7`, `5.8`, and contract-aware limit / fit-family checks when the claim depends on a specific asymptotic regime |
| Dim 5: Computational Feasibility | 8 | `5.5`, `5.14`, benchmark reproduction, and code-facing numerical evidence |
| Dim 6: Validation Strategy | 9 | Full relevant verifier registry: universal `5.1`-`5.14` plus required contract-aware `5.15`-`5.19` |
| Dim 7: Anomaly / Topological Awareness | inline | Domain checklists, protocol bundles, and decisive anchors when generic checks are insufficient |
| Dim 8: Result Wiring | 10 | Artifact integration and evidence wiring checks inside verification output |
| Dim 9: Dependency Correctness | 11 | Mostly plan-only, with follow-through in consistency-checker dependency checks |
| Dim 10: Scope Sanity | 12 | Plan-only |
| Dim 11: Contract Completeness And Artifact Derivation | 13 | Contract-aware checks `5.15`-`5.19` |
| Dim 12: Literature Awareness | 14 | `5.6` literature cross-check plus `5.16` benchmark reproduction when applicable |
| Dim 13: Path to Publication | 15 | Review / paper-facing verification expectations rather than a single verifier id |
| Dim 14: Failure Mode Identification | 16 | Routing, escalation, and focused re-check behavior after failures |
| Dim 15: Context Compliance | conditional | Planning-only pressure management |
| Dim 16: Environment Validation | 16.5 | Code-execution protocol and evidence-quality limits when tools are unavailable |

---

## Quick Reference To Live Registry

The conceptual quick reference lists 14 universal checks. Those now align directly with the live universal verifier registry:

| Quick-ref # | Universal check | Live registry id |
|---|---|---|
| 1 | Dimensional analysis | `5.1` |
| 2 | Limiting cases | `5.3` |
| 3 | Symmetry verification / sum-rule awareness | `5.9` when identities or sum rules are decisive |
| 4 | Conservation laws | `5.4` |
| 5 | Numerical convergence | `5.5` |
| 6 | Cross-check with literature | `5.6` |
| 7 | Order-of-magnitude estimation | `5.7` |
| 8 | Physical plausibility | `5.8` |
| 9 | Ward identities / sum rules | `5.9` |
| 10 | Unitarity bounds | `5.10` |
| 11 | Causality constraints | `5.11` |
| 12 | Positivity constraints | `5.12` |
| 13 | Kramers-Kronig consistency | `5.13` |
| 14 | Statistical validation | `5.14` |

## Contract-Aware Checks Added On Top

The live registry also has five plan-sensitive checks with no fixed quick-reference counterpart:

| Registry id | Check | Why it exists |
|---|---|---|
| `5.15` | Asymptotic / limit recovery | Stops success claims that miss the decisive limit or boundary behavior |
| `5.16` | Benchmark reproduction | Forces explicit anchor comparison instead of vague agreement claims |
| `5.17` | Direct-vs-proxy consistency | Prevents proxy-only success from substituting for the real observable |
| `5.18` | Fit-family mismatch | Catches wrong extrapolation or fit-family choices |
| `5.19` | Estimator-family mismatch | Catches wrong estimator choices and mismatched uncertainty stories |

---

## Consistency-Checker Audit Points

The consistency-checker operates orthogonally to both plan-checker and verifier:

| Consistency check | What it catches | Related verifier surface |
|---|---|---|
| Convention compliance | Metric signature drift, unit drift, Fourier mismatch | Convention checks plus downstream verifier evidence |
| Provides/requires chains | Broken data flow between phases | Artifact wiring and handoff validation |
| Sign / factor spot-checks across boundaries | Lost factors at phase boundaries | Numerical spot-checks and limit checks |
| Approximation validity propagation | Using a result outside the regime where it was verified | Limiting cases, plausibility, and contract-aware checks |
| Notation consistency | Symbol meaning drift across phases | Artifact integration and manuscript consistency checks |

---

## Profile Comparison Across Agents

| Profile | Plan-checker | Verifier | Consistency-checker |
|---|---|---|---|
| **deep-theory** | All 16 dimensions | Full universal registry plus all required contract-aware checks | Full semantic consistency scrutiny |
| **numerical** | All 16, emphasize feasibility and validation strategy | Full relevant registry with emphasis on convergence, statistics, spot-checks, and benchmark anchors | Focus on numerical value and convention consistency |
| **exploratory** | Contract gate plus core dimensions with abbreviated optional breadth | Lightweight universal floor plus every required contract-aware check | Structural floor remains active |
| **review** | All 16 plus stronger literature awareness | Full registry plus cross-validation pressure from literature and benchmarks | Full cross-phase consistency plus review-facing evidence checks |
| **paper-writing** | All 16 with deliverable and artifact emphasis | Full registry plus manuscript-facing evidence and notation checks | Strong notation and artifact consistency focus |

## See Also

- `../core/verification-quick-reference.md` — conceptual 14-check checklist
- `../core/verification-core.md` — universal verification procedures
- `verifier-profile-checks.md` — domain-specific verifier depth
- `../../orchestration/model-profiles.md` — current profile semantics across agents
