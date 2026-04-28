# Erdős Problem #789 — Formalization Plan

**Bead:** ge-kqxj
**Source:** <https://www.erdosproblems.com/789> (accessed 2026-04-28)
**Status:** Plan only. No proof assistant was invoked in producing this document.
**Author:** polecat shiny

---

## 0. Problem statement

Let $h : \mathbb{N} \to \mathbb{N}$ be the maximal function such that for every
$A \subseteq \mathbb{Z}$ with $|A| = n$ there exists $B \subseteq A$ with
$|B| \geq h(n)$ satisfying

$$a_1 + \cdots + a_r = b_1 + \cdots + b_s,\;\; a_i, b_i \in B
\;\Longrightarrow\; r = s.$$

Estimate $h(n)$. Status on erdosproblems.com: **OPEN, cannot be resolved by a
finite computation.** Tag: additive combinatorics.

Known partial results:

| Bound | Direction | Attribution |
|---|---|---|
| $h(n) \ll n^{5/6}$ | upper | Erdős [Er62c] |
| $h(n) \ll n^{1/2}$ | upper (current best) | Straus [St66] |
| $h(n) \gg n^{1/3}$ | lower | Erdős, random-$\alpha$ construction [Er62c] |
| $h(n) \gg (n \log n)^{1/3}$ | lower (current best) | Erdős–Choi [Er62c, Ch74b] |

Cross-references on erdosproblems.com:

- **#186** (Straus / Erdős–Sárközy / Conlon–Fox–Pham / Pham–Zakharov):
  non-averaging sets in $\{1,\dots,N\}$. $F(N) = N^{1/4+o(1)}$. Solved (asymptotically).
- **#874** (Erdős, Straus, Erdős–Nicolas–Sárközy, Deshouillers–Freiman):
  admissible sets where $S_r = \{\sum_{a_1<\cdots<a_r,\,a_i\in A} a_i\}$ are
  pairwise disjoint. $k(N) \sim 2 N^{1/2}$. **Proved** (Deshouillers–Freiman 1999).

Both #186 and #874 share probabilistic-construction and double-counting
techniques with #789 and would likely share lemma infrastructure if formalized.

## 1. Existing formal status

A formal *statement* (no proofs) already exists upstream:

- Repo: `google-deepmind/formal-conjectures`
- Path: `FormalConjectures/ErdosProblems/789.lean`
- Language: **Lean 4** (mathlib4)

The file declares `IsSubsetSumSeparatingCard n m`, the noncomputable
`subsetSumThreshold n := sSup { m | IsSubsetSumSeparatingCard n m }`, and four
theorems, all currently `sorry`:

1. `erdos_789` — `subsetSumThreshold =Θ atTop answer(sorry)` (the open principal version)
2. `erdos_789.variants.sq` — $\Theta(\sqrt{n})$ candidate (open)
3. `erdos_789.variants.isBigO_sq` — Straus's upper bound (marked `solved`, sorry)
4. `erdos_789.variants.sq_isBigO` — matching lower bound (open)
5. `erdos_789.variants.cube_root_linearithmic` — $\Theta((n \log n)^{1/3})$ candidate (open)
6. `erdos_789.variants.cube_root_linearithmic_isBigO` — Erdős–Choi lower bound (marked `solved`, sorry)
7. `erdos_789.variants.isBigO_cube_root_linearithmic` — matching upper bound (open)

**The work is the proofs, not the statement.** Two of the seven theorems
correspond to genuinely solved math (Straus upper bound, Erdős–Choi lower
bound); the rest remain open in the literature and cannot be formalized
until new mathematics appears.

## 2. Candidate proof assistants

### 2.1 Lean 4 / mathlib4 — **recommended**

Rationale:
- The statement is already formalized in Lean 4 by DeepMind's
  `formal-conjectures` project. Using a different assistant means redoing
  that work and forking the convention.
- mathlib4 has the strongest additive-combinatorics library among current
  proof assistants: `Finset.sum`, `Mathlib.Combinatorics.Additive.*`
  (sumsets, Plünnecke–Ruzsa partial), `Mathlib.NumberTheory.SumsetEstimates`,
  and `Mathlib.Probability.*` for measure-theoretic random constructions.
- Active mathematician community (Tao, Mehta, et al. routinely formalize
  combinatorics there); peer review available.
- Asymptotic notation (`Asymptotics.IsBigO`, `IsLittleO`, `IsTheta`,
  `Filter.atTop`) is mature and is the exact vocabulary the existing file uses.
- Tactic ecosystem (`gcongr`, `polyrith`, `positivity`, `bound`) covers most
  inequality plumbing the bounds will need.

### 2.2 Coq / mathcomp — discouraged

Rationale:
- mathcomp has rich finite-set algebra and combinatorics, but no equivalent
  of mathlib's measure theory + asymptotic-notation stack out of the box.
- No upstream statement exists. Net cost: roughly 2× Lean for equivalent work.
- Useful only if a collaborator brings deep mathcomp expertise.

### 2.3 Isabelle/HOL — discouraged

Rationale:
- AFP has measure theory and analysis, but additive-combinatorics scaffolding
  is thin. Isar prose-style proofs would be readable to mathematicians, which
  is a real plus, but the lemma gap is too wide to close cheaply.
- No upstream statement.

### 2.4 Decision

Proceed in **Lean 4 / mathlib4**, contributing back to
`google-deepmind/formal-conjectures` (replacing `sorry`s in the two `solved`
variants) and lifting general lemmas into mathlib4 PRs as they crystallize.

## 3. Prerequisite library content

Inventory of what is needed and where it currently sits.

### 3.1 Already in mathlib4 (used as-is)

- `Finset.sum`, `Finset.subset`, `#A` cardinality lemmas.
- `Asymptotics.IsBigO`, `IsLittleO`, `IsTheta`, `Filter.atTop`,
  `Asymptotics.isBigO_of_le`, log/√ comparisons.
- `Real.log`, `Real.rpow`, monotonicity and asymptotic lemmas.
- Probability infrastructure: `MeasureTheory.MeasureSpace`,
  `ProbabilityTheory.IndepFun`, `volume` on `[0,1]`,
  Borel–Cantelli (`MeasureTheory.measure_limsup_eq_zero`).
- `Int.fract` (fractional part), uniform measure on $[0,1)$.

### 3.2 Likely already in mathlib4, needs verification

- Bound on number of representations of an integer as a sum of $r$ elements
  of a set (`Finset.Nat.antidiagonal`-style for $\mathbb{Z}$).
- "First-moment" / "alteration" probabilistic-method formalisms — partially
  present via `MeasureTheory.integral`/`expectation`; a clean `expectation_lt`
  pruning lemma may need to be written.

### 3.3 Likely absent — must be developed

- A clean *combinatorial nucleus*: "for $B \subseteq \mathbb{Z}$, the number
  of pairs $(T, S)$ with $T, S \subseteq B$ and $\sum T = \sum S$ but
  $|T| \neq |S|$ is bounded above by …". This is the engine of Straus's
  upper bound and does not exist in mathlib in this form.
- *Dissociation by length*: a definition equivalent to
  `IsSubsetSumSeparatingCard` reformulated as
  "$B$ has no nontrivial $\mathbb{Z}$-relation $\sum c_i b_i = 0$ with
  $c_i \in \{-1, 0, +1\}$ and $\sum c_i \neq 0$". Useful as an interface
  layer between the existing file and analytical lemmas.
- *Random-translate construction lemmas*: "for almost every $\alpha \in [0,1]$,
  $|\{a \in [n] : \{\alpha a\} \in I\}| \approx |I| \cdot n$" — a quantitative
  equidistribution lemma. Mathlib has Weyl equidistribution; a quantitative
  version for finite sets at the precision needed for $(n \log n)^{1/3}$ may
  need a dedicated PR.

## 4. Proof structure sketches (for the two solved variants)

### 4.1 Straus's $h(n) \ll \sqrt{n}$

Goal: `erdos_789.variants.isBigO_sq`.

Mathematical idea (standard double-counting). For any $B$ of size $m$ with the
separating property, count ordered pairs $(T, S)$ of subsets with
$|T| \neq |S|$ and $\sum T = \sum S$: by hypothesis there are *zero* such
pairs even though there are $\sim \binom{m}{r}\binom{m}{s}$ candidates for each
$(r, s)$ pair. Comparing against the spread of subset sums forces $m \ll \sqrt{n}$.

Lemma chain:

1. `subset_sum_range_le`: $|\{\sum T : T \subseteq B\}| \leq m \cdot \max B - m \cdot \min B + 1$.
   Trivial bound on the image of the sum map.
2. `subset_sum_count_by_card`: $\sum_{r=0}^{m} \binom{m}{r}^2$ bounds the
   number of equal-cardinality coincidences; pure binomial identity.
3. `separating_implies_distinct_pairs`: combine (1) and (2). If $B$ separates,
   then the off-diagonal pairs contribute zero, leaving the diagonal — and
   the diagonal cannot exceed the range from (1).
4. `straus_upper`: the inequality $2^m \leq C \cdot m \cdot N$ where $A \subseteq [-N, N]$,
   yielding $m \leq O(\log N)$ in the abstract case; the $\sqrt n$ form arises
   from the *normalization* $A \subseteq [n]$ (after translation) and a careful
   application to the largest $B$ guaranteed by the definition of $h(n)$.
5. `isBigO_sq`: package as `Asymptotics.IsBigO` against `√n` at `Filter.atTop`.

Estimated size: 400–800 lines of Lean once the `Finset` plumbing is in place.
The hardest step is (4): the literature proof uses an explicit bijective
argument between subset sums and a fattened lattice region; Lean does not
make this easier.

### 4.2 Erdős–Choi $(n \log n)^{1/3} \ll h(n)$

Goal: `erdos_789.variants.cube_root_linearithmic_isBigO`.

Mathematical idea (probabilistic / random-$\alpha$ thresholding). Erdős's
original construction: pick $\alpha$ uniformly in $[0,1]$, and define
$B = \{a \in A : \{\alpha a\} \in n^{-1/3} + \frac{1}{2}(-n^{-2/3}, n^{-2/3})\}$.
The expected size of $B$ is $\sim n \cdot n^{-2/3} = n^{1/3}$; a careful
analysis of the variance and a $\log n$ improvement (Choi) bumps this to
$(n \log n)^{1/3}$.

Lemma chain:

1. `random_threshold_expected_size`: under uniform $\alpha$,
   $\mathbb{E}|B| = |A| \cdot \mathrm{length}(I)$ for the threshold interval $I$.
   First moment, no concentration needed.
2. `random_threshold_separates`: if $B$ falls in a narrow band of fractional
   parts, then any equal sum with mismatched length forces a constraint
   $\{|r - s| \cdot c\} \in (-n^{-2/3} \cdot k, n^{-2/3} \cdot k)$ which fails
   for the chosen interval radius. This is the core of the construction.
3. `expected_bad_pairs_small`: bound $\mathbb{E}|\{(T, S) : |T| \neq |S|,
   \sum T = \sum S\}| \leq o(\mathbb{E}|B|)$, so first-moment pruning
   yields a $B'$ of comparable size that *exactly* separates.
4. `choi_log_improvement`: replace the single-window construction with a
   union over $\Theta(\log n)$ shifts and apply pigeonhole. This is where the
   $\log^{1/3}$ factor enters.
5. `cube_root_linearithmic_isBigO`: package as `Asymptotics.IsBigO`.

Estimated size: 800–1500 lines. The variance / Borel–Cantelli flavored
arguments are exactly the kind of thing mathlib supports but requires care
with measurability and integrability of the indicator functions involved.

### 4.3 Open variants — explicitly out of scope

`erdos_789`, `erdos_789.variants.sq`, `.sq_isBigO`,
`.cube_root_linearithmic`, `.isBigO_cube_root_linearithmic` correspond to
mathematically open statements. Formal verification cannot close them. The
plan does not attempt them; they remain `sorry` in the upstream file until
new mathematics is published.

## 5. Estimated complexity

| Component | Calendar effort | Lean LoC | Risk |
|---|---|---|---|
| Library survey + design | 1 week | 0 | Low |
| Combinatorial nucleus lemmas (§3.3) | 2–4 weeks | 600–1200 | Medium |
| Straus upper bound (§4.1) | 3–6 weeks | 400–800 | Medium |
| Erdős–Choi lower bound (§4.2) | 6–12 weeks | 800–1500 | High |
| Mathlib upstream PRs | 4–8 weeks (parallel) | varies | Medium |

Calibrated against published Lean formalizations of comparable additive
combinatorics results (Polynomial Freiman–Ruzsa: ~60 person-weeks for a
deeper theorem with Tao steering; Roth's theorem in $\mathbb{F}_3^n$:
~10–15 person-weeks). #789's two solved variants are individually simpler
than PFR but rely on probabilistic infrastructure that PFR partially built.

A focused Lean-fluent mathematician with additive-combinatorics background
should expect **3–6 calendar months** to land both `solved` variants
upstream; a generalist Lean contributor without combinatorics background
should expect **9–12 months**.

## 6. Failure modes / why this is hard

1. **The principal problem is open.** Formalization yields *certified
   partial results*, not a resolution. Any communication of this work must
   be careful not to overclaim.
2. **Probabilistic-method formalization is historically painful.** Measurability
   bookkeeping, integrability side-conditions, and Borel–Cantelli setup
   inflate proof length 3–5× over the paper proof. Erdős–Choi is the at-risk
   component on this axis.
3. **The original papers are terse.** Erdős [Er62c] is in Hungarian
   (Mat. Lapok) and runs ~10 pages; Straus's argument is sketched in J. Math. Sci.
   1966 in similarly compressed form. Reconstructing a fully rigorous proof
   from the literature is the prerequisite to formalization and is itself
   non-trivial.
4. **mathlib gaps are slippery.** It is normal in this kind of project to
   discover, mid-proof, that an "obvious" lemma about (e.g.) the number of
   subsets of fixed cardinality summing to a given value is not in mathlib
   and must be PR'd separately. Plan for 20–30% of effort to be lemma-PR work.
5. **Asymptotic-notation pitfalls.** The existing file uses
   `=Θ[atTop]` / `=O[atTop]`; converting between $\ll$ in informal prose and
   `IsBigO` in Lean introduces sign / constant traps (e.g., `n^{1/3}` vs
   `n^{(1:ℝ)/3}` and integer-coercion noise). Expect a non-trivial fraction
   of bug surface here.
6. **Norm conventions.** Erdős's lower-bound construction works with
   $\alpha \in [0,1]$ and the fractional-part metric; mathlib has `Int.fract`
   but the quantitative equidistribution lemmas at the precision needed
   ($\Theta(n^{-2/3})$) may not exist as stated and may require a dedicated
   intermediate lemma developed in mathlib.
7. **The technique may not generalize to the open part.** Straus's $\sqrt n$
   upper bound has resisted improvement for ~60 years; a formal proof is
   archaeological, not exploratory. Effort yields verification, not insight.
8. **Maintainer queue.** Upstreaming into mathlib4 has review latency
   (weeks to months); plan for it explicitly rather than blocking on it.

## 7. Recommended sequencing

1. **Week 0–1.** Read Straus 1966 and Erdős 1962c carefully; produce a
   self-contained TeX writeup of both proofs at full rigor. Validate against
   Choi 1974b for the $\log$ improvement.
2. **Week 1–2.** Audit mathlib4 for the §3.3 gaps. File mathlib issues for any
   missing infrastructure (do not start PRs yet — design first).
3. **Week 2–6.** Develop combinatorial nucleus + Straus upper bound. Land as
   a PR against `google-deepmind/formal-conjectures` replacing the
   `isBigO_sq` `sorry`. Lift any general-purpose lemmas into mathlib PRs.
4. **Week 6–18.** Develop probabilistic infrastructure + Erdős–Choi lower
   bound. Land as a PR replacing `cube_root_linearithmic_isBigO`.
5. **Week 18+.** Maintenance: respond to reviewer comments, keep proofs
   compiling against mathlib bumps.

## 8. Out of scope (hard rule from bead)

- No proof-assistant invocations were performed in producing this plan.
  The plan is paper-only, derived from the public problem page and the
  upstream Lean *statement* file (read as text).
- No mathlib lemma names above are claimed to exist verbatim; they are
  identifiers from familiarity with the library and require verification
  during step 2 of §7.
- No code changes proposed beyond this report.

## 9. Open questions for Rome / mayor

1. Is the goal to land both solved variants upstream in
   `google-deepmind/formal-conjectures`, or to produce a standalone
   formalization repo? The plan assumes the former (cheaper, higher leverage).
2. Is there appetite for the parallel related-problem #874
   (Deshouillers–Freiman, fully proved) as a warm-up? The techniques
   overlap heavily and the mathlib infrastructure built for #789 would
   directly accelerate #874.
3. Hours / calendar budget? The estimates above assume one focused
   mathematician-engineer; multi-person plans need different sequencing.

## References

- [Er62c] P. Erdős, *Some remarks on number theory III*, Mat. Lapok **13** (1962), 28–38.
- [St66] E. G. Straus, *On a problem in combinatorial number theory*, J. Math. Sci. **1** (1966), 77–80.
- [Ch74b] S. L. G. Choi, *On an extremal problem in number theory*, J. Number Theory **6** (1974), 105–111.
- T. F. Bloom, *Erdős Problem #789*, <https://www.erdosproblems.com/789>, accessed 2026-04-28.
- Google DeepMind, `formal-conjectures` repo,
  `FormalConjectures/ErdosProblems/789.lean`, accessed 2026-04-28.
- Cross-references: <https://www.erdosproblems.com/186>, <https://www.erdosproblems.com/874>.
