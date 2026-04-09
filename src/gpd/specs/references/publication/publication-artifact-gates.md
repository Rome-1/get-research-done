---
load_when:
  - "publication artifact gates"
  - "manuscript-root review gate"
  - "submission gate"
type: publication-artifact-gates
tier: 2
context_cost: low
---

# Publication Artifact Gates

Compatibility entry point for manuscript-root and latest-round publication gating.

Canonical sources:

- `@{GPD_INSTALL_DIR}/templates/paper/publication-manuscript-root-preflight.md`
- `@{GPD_INSTALL_DIR}/references/publication/publication-review-round-artifacts.md`
- `@{GPD_INSTALL_DIR}/references/publication/publication-response-artifacts.md`

The manuscript-root contract owns root resolution, manuscript-local artifact rooting, and `gpd paper-build` authority. The round and response contracts own latest-round gating, paired response completion, and fail-closed child-return semantics.
