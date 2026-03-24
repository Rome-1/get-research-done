---
load_when:
  - "artifact surfacing"
  - "review artifacts"
  - "artifact summary"
  - "wave completion"
  - "phase deliverables"
tier: 2
context_cost: low
---

# Artifact Surfacing and Review UX

How artifacts are classified, surfaced at wave boundaries, and presented for review. This document covers artifact visibility during execution, not manifest generation (for build-time manifests, see `src/gpd/mcp/paper/artifact_manifest.py`).

**Related files:**
- `references/orchestration/checkpoints.md` -- checkpoint interaction points
- `workflows/execute-phase.md` -- wave-based execution with artifact_summary step
- `workflows/verify-phase.md` -- phase verification against contract targets

---

## 1. Artifact Classes

Every artifact produced during a research project falls into one of the following classes. The class determines its review priority and surfacing behavior.

| Class | Description | Typical extensions | Example paths |
|---|---|---|---|
| **planning-doc** | Phase plans, roadmaps, requirements | `.md` | `.gpd/phases/01-*/01-01-PLAN.md` |
| **literature-review** | Survey notes, citation databases, reading summaries | `.md`, `.bib` | `notes/literature-survey.md` |
| **experiment-config** | Simulation parameters, grid definitions, model setups | `.json`, `.yaml`, `.py` | `simulations/config.json` |
| **result-table** | Numerical outputs, data frames, benchmark comparisons | `.csv`, `.json`, `.md` | `data/eigenvalues.csv` |
| **generated-figure** | Plots, diagrams, phase diagrams, convergence curves | `.pdf`, `.png`, `.eps`, `.svg` | `figures/dispersion.pdf` |
| **draft-section** | Manuscript sections, appendix drafts | `.tex`, `.md` | `paper/sections/results.tex` |
| **final-latex** | Complete compiled manuscript source | `.tex`, `.bib`, `.bst` | `paper/main.tex` |
| **final-pdf** | Compiled PDF output | `.pdf` | `paper/output/main.pdf` |
| **peer-review-output** | Review panel reports, referee responses | `.md`, `.json` | `.gpd/paper/REVIEW-REPORT.md` |

---

## 2. Review Priority Levels

Each artifact is assigned a review priority that determines how prominently it appears in wave completion summaries and whether it blocks downstream work.

### Required Review

Artifacts that must be inspected before downstream waves proceed. These represent load-bearing results where errors propagate.

- Key derivations that downstream calculations depend on
- Numerical results that serve as inputs to later phases
- Convention-setting documents (notation, unit systems)
- Contract deliverables tagged as acceptance tests

### Optional Review

Artifacts worth inspecting but that do not block progress. Errors here are contained and correctable later.

- Supporting plots and figures
- Intermediate calculation notebooks
- Literature survey notes
- Auxiliary data files

### Final Deliverable

Artifacts that represent completed research outputs. These are surfaced at phase completion, not at wave boundaries.

- Final manuscript LaTeX source and compiled PDF
- Peer review panel reports
- Experiment configuration archives
- Publication-ready figures with captions

---

## 3. Surfacing at Phase and Wave Completion

### Wave Completion Summary

After each wave completes (see `execute_waves` in `workflows/execute-phase.md`), the orchestrator emits an `artifact_summary` block listing key artifacts produced. The summary follows this format:

```
## Artifacts: Wave {N}

| Path | Class | Review |
|------|-------|--------|
| derivations/dispersion.py | result-table | required |
| figures/dispersion_plot.pdf | generated-figure | optional |
| notes/01-02-SUMMARY.md | planning-doc | optional |

Required review: 1 artifact(s) -- inspect before Wave {N+1}
```

**Rules for the artifact summary:**

1. List only artifacts created or modified in the completed wave (from SUMMARY.md `key-files.created` and `key-files.modified`)
2. Assign the artifact class from the table in section 1 based on file extension and path
3. Mark review priority using the rules in section 2
4. Show paths relative to the project root
5. Keep the summary compact -- one row per artifact, no inline content

### Phase Completion Summary

At phase completion (after all waves and verification), emit a full artifact inventory:

```
## Phase {X} Artifact Inventory

### Required Review (inspect before next phase)
- derivations/hamiltonian.py -- result-table
- data/eigenvalues.csv -- result-table

### Final Deliverables
- paper/sections/methods.tex -- draft-section
- figures/phase_diagram.pdf -- generated-figure

### Optional Review
- notes/01-01-SUMMARY.md -- planning-doc
- notes/literature-notes.md -- literature-review
```

---

## 4. Recommended Review Order

When multiple artifacts require review, present them in this order to maximize review efficiency:

1. **Convention-setting artifacts** -- notation definitions, unit system locks, coordinate conventions. These affect interpretation of everything else.
2. **Load-bearing derivations** -- analytical results that downstream calculations consume. Errors here have the highest propagation cost.
3. **Numerical results and benchmarks** -- computed values, convergence data, comparison tables. Check these against known limits and dimensional expectations.
4. **Generated figures** -- visual outputs that summarize results. Review after the underlying data is confirmed.
5. **Draft manuscript sections** -- prose and LaTeX. Review last since they depend on all prior artifacts being correct.
6. **Peer review outputs** -- panel reports and referee responses. These are terminal artifacts with no downstream dependents.

This order follows the dependency chain: upstream artifacts first, downstream artifacts after their inputs are validated.

---

## 5. Integration with Progress and Checkpoint Commands

### Progress Command

The `/gpd:progress` command includes artifact counts in its phase status output:

```
Phase 2: Numerical Simulation -- 3/4 plans complete
  Artifacts: 12 total (3 required-review, 2 final-deliverable, 7 optional)
  Pending review: derivations/self_energy.py, data/convergence.csv, figures/spectral.pdf
```

When artifacts marked as required-review remain uninspected, the progress display flags them so the researcher can prioritize review before proceeding.

### Checkpoint Integration

Checkpoints of type `checkpoint:human-verify` should reference the specific artifacts being verified:

```xml
<task type="checkpoint:human-verify" gate="blocking">
  <what-derived>Self-energy in GW approximation</what-derived>
  <artifacts>
    derivations/self_energy.py (required review)
    figures/spectral_function.pdf (optional review)
  </artifacts>
  <how-to-verify>
    1. Im[Sigma] = 0 at Fermi surface
    2. Spectral weight Z between 0 and 1
  </how-to-verify>
</task>
```

This ties the verification request to concrete file paths, making it actionable.

### Artifact Manifest Linkage

For paper-writing phases, the artifact summary at wave completion feeds into the ARTIFACT-MANIFEST.json generated by the paper build pipeline. The manifest records SHA-256 hashes, provenance chains, and category labels for each artifact. The wave-level summaries provide the upstream traceability that the manifest formalizes.
