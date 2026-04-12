# Pitch: Pandoc as GRD's Structured LaTeX Conversion Layer

**Bead:** ge-6we (pitch) + ge-be3, ge-5e6, ge-4gr, ge-z7q, ge-xf5, ge-ow7 (implementation)
**Author:** alice (crew)
**Opened:** 2026-04-11
**Status:** Living document — pitch awaiting approval; will track progress and evolution during implementation.

**Portability goal:** If this approach works in GRD, the same tooling (pandoc utils, Lua filters, agent spec changes) should be portable to the original [Get Physics Done (GPD)](https://github.com/Rome-1/get-physics-done) repo via PR. Design decisions should favor GRD/GPD-agnostic abstractions where cheap — anything physics-specific goes in a separate layer.

---

## Executive Summary

GRD currently has two disconnected approaches to LaTeX:

1. **Write-paper pipeline** — agents write raw LaTeX, which passes through an auto-fix engine (`latex.py`) that patches common LLM errors (unescaped underscores, bad braces, wrong environments), then gets assembled into journal templates via Jinja2.

2. **Export pipeline** — hardcoded LaTeX string templates in `export.md` that produce bare scaffolds. No journal targeting, no pandoc, no AST-level processing.

Meanwhile, OSB's Second Brain Tooling has a working pandoc pipeline: markdown files pass through a Lua filter and template to produce clean `.tex` on every git commit. It's simple, fast (~200ms/file), and correct.

**Proposal:** Adopt pandoc as GRD's deterministic markdown-to-LaTeX conversion layer. Agents draft in markdown (which LLMs do well) instead of raw LaTeX (which LLMs do poorly). Pandoc handles the syntax conversion via its AST. GRD's existing journal template system handles the structural assembly.

This is not replacing GRD's paper system. It's giving it a proper engine where today it relies on string patching.

---

## The Problem

### LLMs write bad LaTeX

GRD's `latex.py` exists because agents writing LaTeX directly produce predictable errors:

| Error | Frequency | Current Fix |
|-------|-----------|-------------|
| Unescaped `_` and `^` outside math mode | Common | `_fix_unescaped_underscores_and_carets()` regex |
| Missing `\begin{document}` | Occasional | `_fix_missing_document_begin()` |
| Unbalanced braces | Common | `_fix_unbalanced_braces()` brace counter |
| Bibliography style conflicts | Frequent | `fix_bibliography_conflict()` regex strip |
| Unicode characters in LaTeX | Pervasive | `sanitize_latex()` 50+ character mappings |
| Markdown fences in LaTeX output | Common | `clean_latex_fences()` |

This is a post-hoc error correction approach: let the agent make mistakes, then try to fix them with regex. It works, but it's fragile — each new error pattern requires a new fix rule, and the fixes can interact badly (e.g., escaping underscores inside math mode where they're already valid).

### LLMs write good markdown

The same agents that struggle with LaTeX syntax produce clean, well-structured markdown naturally. Markdown is closer to how LLMs "think" — it's what they were predominantly trained on.

### The export pipeline is a raw string template

`grd:export --format latex` writes a hardcoded LaTeX document structure character by character in a workflow spec. There's no AST, no template system, no sanitization. It produces a compilable but low-quality scaffold.

---

## The Proposal

### Architecture

```
Current:  Agent → raw LaTeX → auto-fix (regex) → template assembly → .tex
                  ^^^^^^^^     ^^^^^^^^^^^^^^^^
                  error-prone  fragile patches

Proposed: Agent → markdown → pandoc + Lua filters → LaTeX fragments → template assembly → .tex
                  ^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^
                  natural     deterministic AST transform
```

### What changes

1. **Paper-writer agents draft in markdown** with embedded LaTeX math (`$...$`, `$$...$$`, `\begin{equation}...\end{equation}`). Pandoc passes math through unchanged — it knows not to touch it.

2. **Pandoc converts markdown → LaTeX fragments** via its AST. This handles text formatting, lists, tables, code blocks, and prose structure correctly every time. No regex patching needed.

3. **GRD-specific Lua filters** handle domain conventions: phase cross-references, figure path resolution, callout conversion, metadata stripping.

4. **The existing template_registry.py assembles fragments** into journal-specific templates exactly as it does today. The Jinja2 journal templates (PRL, APJ, MNRAS, Nature, JHEP, JFM) are unchanged.

5. **Citations use pandoc's native `@key` syntax** in markdown, resolved by citeproc during conversion. GRD's bibliography audit validates keys before pandoc sees them.

### What doesn't change

- Journal template system (Jinja2 with LaTeX-safe delimiters)
- Paper compilation pipeline (pdflatex/latexmk, multi-pass, cross-platform detection)
- Bibliography audit system (pybtex, BIBLIOGRAPHY-AUDIT.json)
- Artifact manifest system (SHA256 tracking, provenance)
- PaperConfig data model
- The `grd paper-build` CLI command

### Graceful degradation

Pandoc is an **optional** dependency. When not installed:
- Agents fall back to writing LaTeX directly (current behavior)
- `latex.py` auto-fix engine remains as the safety net
- `grd health` reports pandoc status with installation guidance

When installed, pandoc becomes the primary conversion path and `latex.py` auto-fix becomes a safety net rather than the main defense.

---

## Implementation Plan

Six beads, ordered by dependency. Each is independently valuable — the plan can stop after any phase and still have improved the system.

### Phase 1: Foundation

**ge-be3 — Core `grd.utils.pandoc` module** (P2)

Build the programmatic interface to pandoc:

```python
# grd/utils/pandoc.py

def detect_pandoc() -> PandocStatus:
    """Check pandoc availability, version, and installed filters."""

def run_pandoc(input: str, *, 
               from_format: str = "markdown",
               to_format: str = "latex",
               lua_filters: list[Path] = [],
               bibliography: Path | None = None,
               template: Path | None = None) -> str:
    """Run pandoc programmatically, return output string."""

def markdown_to_latex_fragment(markdown: str, *,
                                lua_filters: list[Path] = []) -> str:
    """Convert a markdown string to a LaTeX fragment (no preamble/document wrapper).
    This is the primary API for paper-writer agents."""
```

- Minimum pandoc version: >=2.17 (reliable Lua filter support)
- Subprocess wrapper with timeout, error capture, temp file management
- Status check integrated into `grd health`

**ge-5e6 — GRD Lua filter set** (P2)

Four composable Lua filters in `src/grd/mcp/paper/filters/`:

| Filter | Purpose |
|--------|---------|
| `grd-obsidian-compat.lua` | Extended version of OSB's filter. Handles wikilinks, callouts, Obsidian-specific YAML fields. Superset of the existing `obsidian-compat.lua`. |
| `grd-crossref.lua` | Resolves GRD phase references (`[[phase:3]]`) to LaTeX `\ref{}` targets. Maps phase numbers to section labels. |
| `grd-math.lua` | Normalizes math environments. Ensures `$$...$$` becomes `\begin{equation}...\end{equation}` with labels. Fixes common LLM math-mode errors at the AST level (before they become LaTeX syntax errors). |
| `grd-figure.lua` | Resolves figure paths against GRD's figure tracker. Validates figure existence. Converts markdown image syntax to proper LaTeX figure environments with captions. |

Each filter is independently testable: input markdown → expected LaTeX output.

### Phase 2: Pipeline Integration

**ge-4gr — Upgrade `grd:export` LaTeX pipeline** (P2)
Depends on: ge-be3, ge-5e6

Replace the hardcoded LaTeX in `export.md` step `generate_latex`:

```
Current:  SUMMARY.md content → string-interpolated LaTeX
Proposed: SUMMARY.md content → assembled markdown document → pandoc + filters → LaTeX
```

The assembled markdown document preserves GRD's export structure (phases as sections, equations, key results) but lets pandoc handle the syntax. The output uses the existing journal template system when a target journal is specified, or a clean `article`-class document otherwise.

**ge-z7q — Paper-writer agents draft in markdown** (P2)
Depends on: ge-be3, ge-5e6

Modify the `grd-paper-writer` agent spec:

- Agent receives section outline + research context (unchanged)
- Agent outputs markdown with LaTeX math blocks instead of raw LaTeX
- `render_paper()` in `template_registry.py` calls `markdown_to_latex_fragment()` on each section's content before template substitution
- The `Section.content` field accepts both markdown and LaTeX — detected by heuristic (presence of `\begin{` or `\section{` indicates LaTeX; otherwise treated as markdown)
- Backward compatible: existing PaperConfig JSON files with LaTeX content continue to work

### Phase 3: Citation and Cross-Reference

**ge-xf5 — Citeproc + bibliography bridge** (P2)
Depends on: ge-z7q

- Agents use `@citation-key` syntax in markdown drafts
- GRD's bibliography audit (`bibliography.py`) validates all keys exist in the `.bib` file before pandoc runs
- Pandoc's `--citeproc` resolves citations during conversion
- Eliminates the `fix_bibliography_conflict()` workaround — citations are handled correctly from the start
- Journal-specific citation styles via CSL files (pandoc's native format) or natbib/biblatex passthrough

**ge-ow7 — pandoc-crossref for figures and equations** (P1)
Depends on: ge-xf5

- Integrate [pandoc-crossref](https://github.com/lierdakil/pandoc-crossref) for automatic numbering
- Agents write `{#eq:euler}` after equations and `@eq:euler` for references
- Same for figures (`{#fig:convergence}`, `@fig:convergence`) and tables
- Filter ordering: pandoc-crossref → grd-filters → citeproc (pandoc-crossref must run first because both it and citeproc use `@` syntax)
- Optional dependency — degrade to manual `\label{}`/`\ref{}` when not installed

---

## Cost/Benefit Analysis

### Costs

| Cost | Severity | Mitigation |
|------|----------|------------|
| New dependency (pandoc) | Low | Optional; graceful degradation. Already installed on this VPS. Available via `apt`, `brew`, `choco` on all platforms. |
| New dependency (pandoc-crossref) | Low | Optional Phase 3 add-on. Not required for core benefits. |
| Lua filter maintenance | Low | Filters are small (<100 LOC each), independently testable, and the Lua filter API is stable across pandoc versions. |
| Agent spec changes | Medium | Backward-compatible — existing LaTeX content still works. Markdown drafting is additive. |
| Learning curve for contributors | Low | Pandoc Lua filters are well-documented. The filter set is small and focused. |

### Benefits

| Benefit | Impact |
|---------|--------|
| **Eliminate most LaTeX auto-fix code path** | High — the regex-based error correction in `latex.py` becomes a safety net, not the primary defense. Fewer false fixes, fewer edge cases. |
| **Higher quality LaTeX output** | High — pandoc's AST-based conversion produces correct LaTeX by construction. No unescaped underscores, no brace mismatches. |
| **Better agent output quality** | High — agents draft in markdown (their strength) instead of LaTeX (their weakness). |
| **Proper citation handling** | Medium — citeproc replaces the `fix_bibliography_conflict()` workaround with correct citation processing. |
| **Automatic cross-references** | Medium — pandoc-crossref eliminates manual `\label{}`/`\ref{}` management by agents. |
| **Export pipeline upgrade** | Medium — `grd:export --format latex` goes from bare scaffold to publication-quality output. |
| **Shared infrastructure with OSB** | Low — GRD's Lua filters extend OSB's, reducing maintenance across both systems. |

### Risk: pandoc availability

Pandoc is packaged for every major OS and has been stable for 15+ years. It's a single static binary with no runtime dependencies. The risk of it becoming unavailable is negligible. The graceful degradation path (fall back to direct LaTeX) eliminates the risk entirely.

---

## What This Is NOT

- **Not replacing GRD's paper system.** The journal templates, compilation pipeline, bibliography audit, artifact manifest, and PaperConfig model are all unchanged. Pandoc is inserted as a conversion step, not a replacement.

- **Not adopting Quarto.** Quarto requires `.qmd` files, which breaks Obsidian compatibility and introduces a parallel format. Pandoc works with standard markdown.

- **Not adopting Typst.** Journals don't accept Typst output. The target is LaTeX.

- **Not making pandoc mandatory.** It's optional with graceful degradation. GRD works without it — just less well.

---

## Recommended Execution Order

1. **ge-be3** (core module) + **ge-5e6** (Lua filters) — can be done in parallel
2. **ge-4gr** (export upgrade) — quick win, improves `grd:export` immediately
3. **ge-z7q** (paper-writer markdown) — the big payoff, eliminates most LaTeX errors
4. **ge-xf5** (citeproc bridge) — cleans up citation handling
5. **ge-ow7** (pandoc-crossref) — polish, automatic numbering

Each phase is independently valuable. The plan can stop after phase 1 and still have a useful `markdown_to_latex_fragment()` utility. It can stop after phase 2 and have an improved export pipeline. The full plan delivers a fundamentally better paper-writing experience.

---

## Decision Requested

Approve this plan for implementation, with any scope adjustments or priority changes.

Beads: ge-be3, ge-5e6, ge-4gr, ge-z7q, ge-xf5, ge-ow7 (all discovered-from ge-6we)

---

## Progress Log

Append-only log of work on this plan. Newest entries on top. Each entry: what was tried, what worked, what didn't, what it means for the plan.

### Template for entries

```
### YYYY-MM-DD — <bead id>: <short title>

**What changed:** One sentence on the concrete action.
**Outcome:** Worked / partially worked / failed / superseded.
**Findings:** What we learned — especially anything surprising.
**Plan impact:** How this changes scope, priority, or ordering of remaining beads.
**Artifacts:** Commit SHAs, files touched, test results.
```

### 2026-04-12 — ge-ow7: pandoc-crossref auto-enablement

**What changed:** External pandoc filters are now first-class in the pandoc wrapper. `grd.utils.pandoc` gained an `external_filters` parameter on `run_pandoc`/`markdown_to_latex_fragment`, plus a new `resolve_external_filters(requested, status)` helper. Default behaviour (`external_filters=None` → "auto"): every entry of `_KNOWN_EXTERNAL_FILTERS` (`pandoc-crossref`, `pandoc-citeproc`) that is actually in `status.installed_filters` gets prepended to the filter chain ahead of Lua filters and `--citeproc`. `markdown_support.maybe_convert_to_latex` forwards the arg so `render_paper` picks up pandoc-crossref automatically when installed. Health check now emits a hint-level warning when pandoc is present but pandoc-crossref isn't, pointing to the install command. Agent spec documents the `{#fig:foo}` / `@fig:foo` syntax and its fallback behaviour; the export workflow spec notes auto-enablement and the opt-out (`external_filters=[]`).

**Outcome:** Worked — 8 new tests in `tests/test_pandoc_utils.py` covering auto/explicit/empty-list resolution and command-line ordering (crossref before Lua filters, before `--citeproc`). Full paper+pandoc suite (146 tests) green. Same 13 pre-existing `tests/core/test_health.py` failures as on main — unrelated.

**Findings:**
- Command-line order matters to pandoc-crossref. The filter has to see the AST before our GRD Lua filters touch it, so `--filter pandoc-crossref` is inserted ahead of `--lua-filter`. It also must run before `--citeproc`, or `@fig:foo` would be ambiguous with a citation key (this is the ordering the bead called out).
- Making `external_filters=None` mean "auto-enable installed" (rather than "disable all") is the right default for a drop-in improvement: hosts with pandoc-crossref get numbered figures without any caller change; hosts without it keep working exactly as before.
- Not installing pandoc-crossref locally meant integration tests had to be mocked. The only real-pandoc path I exercise is the existing GRD Lua filter chain, which remains the default on this host.

**Plan impact:**
- All six Phase 1-3 beads are now done. The pitch's "primary objective" (LaTeX pipeline hardened via pandoc + filters) is complete end-to-end: markdown → pandoc → GRD Lua filters → (optional) pandoc-crossref → journal template → sanitised LaTeX.
- GPD portability checklist can be fully ticked.

**Artifacts:**
- `src/grd/utils/pandoc.py` (`external_filters` arg, `resolve_external_filters`, `_build_command` now takes ordered filter lists)
- `src/grd/mcp/paper/markdown_support.py` (forwards `external_filters` through `maybe_convert_to_latex`)
- `src/grd/core/health.py` (`check_pandoc` warns when pandoc-crossref is missing)
- `src/grd/agents/grd-paper-writer.md` (documents `{#fig:foo}` / `@fig:foo` + fallback)
- `src/grd/specs/workflows/export.md` (notes auto-enablement + opt-out)
- `tests/test_pandoc_utils.py` (+8 tests)
- Commit SHA: *pending*

### 2026-04-12 — ge-xf5: citation bridge (markdown @key → .bib audit)

**What changed:** New `grd.mcp.paper.citations` module: `extract_markdown_citations()` pulls pandoc-style `@key` refs from markdown while ignoring fenced/inline code and email addresses; `audit_markdown_citations()` + `MarkdownCitationAudit` model summarise which keys are defined vs unresolved; `load_bib_keys()` parses a `.bib` via pybtex and returns its key set. `render_paper(..., bib_keys=...)` now runs the audit over markdown sections and logs a single warning listing any unresolved keys — advisory only, never fails the render. `build_paper()` in `compiler.py` passes `set(bib_data.entries)` through to `render_paper` when a bibliography is loaded, so the audit happens automatically for every real build. `grd-paper-writer.md` authoring guide now documents `@key` and `[@key1; @key2]` syntax and forbids inline `\begin{thebibliography}` in markdown sections.

**Outcome:** Worked — 21 new tests (`tests/test_paper_citations.py`) pass; full paper+pandoc suite (139 tests) green; ruff clean.

**Findings:**
- Pandoc's citation-key grammar is permissive: keys may contain `_`, `:`, `-`, `+`, `/`, `#`, `$`, `%`, `&`, `?`, `.`, and internal digits. The naive `@[A-Za-z][\w.-]*` regex greedily captures trailing sentence punctuation (`@smith2020.` matches as key `smith2020.`). Fix: require the key to end on `[A-Za-z0-9]`, allow `.` only mid-key, and strip fenced/inline code regions before matching so `@name` inside backticks or ``` blocks isn't flagged.
- Raw-LaTeX sections use `\cite{...}`, not `@key`, so the audit correctly skips anything that passes `looks_like_latex()`. Otherwise a legacy LaTeX section with `\cite{foo}` would (absurdly) be blamed for undefined markdown citations.
- The "replace fragile inline thebibliography workaround" framing in the original pitch resolves naturally: agents write `@key` in markdown → pandoc emits `\cite{key}` → template's `\bibliography{...}` resolves at compile time. `fix_bibliography_conflict()` stays in place as a defensive patcher for legacy raw-LaTeX payloads, but new markdown-authored papers never trigger it.

**Plan impact:**
- ge-ow7 (pandoc-crossref) is the last Phase 3 bead. The `@key` audit is orthogonal to pandoc-crossref — that bead handles `{#eq:label}` / `{#fig:label}` resolution to numbered `\ref{...}` via the external pandoc-crossref filter. `PandocStatus.installed_filters` already exposes whether pandoc-crossref is present, so wiring it into the pipeline is straightforward.
- No downstream reordering.

**Artifacts:**
- `src/grd/mcp/paper/citations.py` (new)
- `src/grd/mcp/paper/template_registry.py` (`render_paper(config, *, bib_keys=None)` signature + audit helper)
- `src/grd/mcp/paper/compiler.py` (passes bib keys through to `render_paper`)
- `src/grd/agents/grd-paper-writer.md` (documents `@key` citation syntax)
- `tests/test_paper_citations.py` (21 tests)
- Commit SHA: `3bb0872`

### 2026-04-12 — ge-4gr + ge-z7q: Phase 2 pipeline wired

**What changed:** Two pieces of plumbing:
1. `grd:export` LaTeX step (`src/grd/specs/workflows/export.md`) rewritten to assemble an intermediate `exports/results.md`, run it through `markdown_to_latex_fragment(..., lua_filters=all_filter_paths())`, then wrap in the journal template (or standalone article w/ `\usepackage{float}` for `[H]`). Legacy raw-LaTeX scaffold preserved as a fallback when `detect_pandoc()` reports unavailable/too-old.
2. Paper-writer pipeline now accepts markdown in `Section.content`. New module `grd.mcp.paper.markdown_support` with `looks_like_latex()` (structural-sigil detection — section/begin/documentclass/title/author/bibliography, plus fenced ```latex/```tex blocks) and `maybe_convert_to_latex()` (graceful degradation: pandoc missing / too old / conversion error → content returned as-is). `template_registry.render_paper()` runs this conversion on every section + appendix_section before the existing `clean_latex_fences` step. Agent spec (`src/grd/agents/grd-paper-writer.md`) gained an `<authoring_format>` section documenting the two modes (markdown vs raw LaTeX) and the crossref / figure / equation syntax.

**Outcome:** Worked — 22 new tests (`tests/test_paper_markdown_support.py`) pass; no regressions in `test_paper_models.py` / `test_paper_e2e.py` / `test_latex_utils.py` / `test_paper_quality.py` (76 total). Ruff clean.

**Findings:**
- Running pandoc blindly on fenced ```latex blocks mangled contents like `E = mc^2` (caret escaped, math semantics lost). Fix: treat fenced latex/tex blocks as an explicit author-declared "already LaTeX" signal in `_LATEX_SIGIL_PATTERN`. This is safer than cleaning fences first, because the unwrapped body (e.g. raw equation text) isn't valid markdown either.
- Pre-existing contract: `PaperConfig` authors historically wrote raw LaTeX, including partial fragments (no `\documentclass`). The sigil check had to key on structural commands that *can't* appear in markdown prose — `\section{`, `\begin{figure}`, etc. — and explicitly exclude inline math (`$x$`) since math is valid markdown.
- `render_paper` pays for `detect_pandoc()` once per call (not once per section). `all_filter_paths()` likewise resolved once.

**Plan impact:**
- Phase 3 (ge-xf5 citeproc + ge-ow7 pandoc-crossref) can now layer in cleanly. The hook for bibliography/citeproc is already present in `maybe_convert_to_latex(bibliography=..., citeproc=...)`; Phase 3 wires `PaperConfig.bib_file` through.
- No change to downstream ordering.

**Artifacts:**
- `src/grd/specs/workflows/export.md` (primary/fallback paths in `generate_latex`)
- `src/grd/mcp/paper/markdown_support.py` (new)
- `src/grd/mcp/paper/template_registry.py` (conversion step added)
- `src/grd/agents/grd-paper-writer.md` (`<authoring_format>` section)
- `tests/test_paper_markdown_support.py` (22 tests)
- Commit SHA: `2a0bc4b`

### 2026-04-12 — ge-be3 + ge-5e6: Phase 1 foundation landed

**What changed:** Built `grd.utils.pandoc` (programmatic pandoc wrapper with availability/version detection, subprocess execution, `markdown_to_latex_fragment` helper) and the four GRD Lua filters (`grd-obsidian-compat`, `grd-crossref`, `grd-math`, `grd-figure`). Wired pandoc availability into `grd health` as a WARN-level check so missing pandoc degrades gracefully. Added 40 tests across unit (parsing, error paths, mocked subprocess) and integration (real pandoc against each filter + composition).
**Outcome:** Worked — all 40 new tests pass; no pre-existing tests regressed. Ruff clean. Pandoc 3.1.3 verified locally.
**Findings:**
- Pandoc 3.x uses a dedicated `Figure` AST block (not `Para [Image]`). `grd-figure.lua` has to handle both so it works across pandoc versions. Kept the `Para` path as a pandoc<3 fallback.
- Lua `--[[ ]]` block comments terminate at the *first* `]]`, so any doc text mentioning `[[target]]` (wikilinks!) broke parsing silently. Switched every header to line comments.
- Filter order matters in the bundled chain: `grd-crossref` must run before `grd-obsidian-compat` so namespaced `[[ns:id]]` links become `\ref{}` before the wikilink handler collapses them to plain text. Documented in the `all_filter_paths()` docstring.
- Pandoc's `--citeproc` flag and our bracket-wikilink syntax don't actually overlap (we target `[[...]]`, citeproc uses `@key`), but the pitch's filter-ordering note still applies for pandoc-crossref (Phase 3).
- External filter probe (`pandoc-crossref`, `pandoc-citeproc`) added to `PandocStatus.installed_filters` so Phase 3 can introspect cheaply.
**Plan impact:**
- Phase 2 (ge-4gr, ge-z7q) can start immediately; the programmatic API is the shape callers will want (`markdown_to_latex_fragment(md, lua_filters=all_filter_paths())`).
- No change to Phase 3 scope. The `PandocStatus.installed_filters` tuple gives ge-ow7 a cheap capability check.
**Artifacts:**
- `src/grd/utils/pandoc.py` (core module, 299 LOC)
- `src/grd/mcp/paper/filters/{grd-crossref,grd-figure,grd-math,grd-obsidian-compat}.lua` + `__init__.py` (filter loader)
- `src/grd/core/health.py` (`check_pandoc`, registered in `_ALL_CHECKS`)
- `tests/test_pandoc_utils.py` (20 tests) + `tests/test_pandoc_filters.py` (20 tests)
- Commit SHA: `f813997`

### 2026-04-11 — ge-6we: Pitch drafted

**What changed:** Researched both LaTeX pipelines (OSB pandoc + GRD paper system); wrote this pitch; created six implementation beads.
**Outcome:** Worked — pitch committed, six beads created, ge-6we closed.
**Findings:** GRD has two disconnected LaTeX paths (write-paper via agents + raw string export in workflow spec). OSB's pandoc pipeline is small (~150 LOC across 3 files) and proven. `latex.py`'s auto-fix engine exists specifically because LLMs write bad LaTeX — which is the exact problem pandoc-as-converter solves.
**Plan impact:** None yet. Awaiting approval.
**Artifacts:** Commit `678eef4`, file `research/pandoc-latex-pitch.md`.

---

## GPD Portability Notes

Design choices that keep the work portable to Get Physics Done:

- **Name filters/modules `grd-*` but structure them to be domain-agnostic.** The core of `grd-math.lua`, `grd-crossref.lua`, `grd-figure.lua` handles markdown→LaTeX mechanics, not physics. When porting, rename to `gpd-*` and the logic transfers unchanged.
- **Journal templates are already shared concepts.** PRL, APJ, MNRAS, Nature, JHEP, JFM exist in both codebases (or will). Templates port 1:1.
- **Keep GRD-specific conventions (phase cross-refs, SUMMARY.md schema) isolated.** The `grd-crossref.lua` filter handles phase references — GPD has the same concept with identical structure. Port is a find/replace of `.grd/` paths and bead ID prefixes.
- **Avoid coupling to crew/bead tooling in the filter logic itself.** Filters should take markdown in, emit LaTeX out. Bead tracking belongs in the workflow specs, which differ more between repos.

Checklist to maintain as the plan executes:
- [x] `grd.utils.pandoc` module has no GRD-specific hardcoded paths (verified: no imports from `grd.core`, `grd.mcp.paper`; all config via function args)
- [x] Lua filters take config via frontmatter/metadata, not via hardcoded directory assumptions (`figure_base_path`, `crossref_namespaces`, `obsidian_strip_fields`, `math_autowrap` all read from pandoc `Meta`)
- [x] Agent spec changes (markdown drafting) are expressed as a prompt pattern, portable to GPD's agents (`<authoring_format>` section in `grd-paper-writer.md` describes markdown mode + raw-LaTeX fallback in prompt-only terms; no GRD-specific paths)
- [x] A final "GPD port checklist" section added below (implementation complete)

### GPD Port Checklist

The GRD pandoc pipeline is ready to port to Get Physics Done. Specific steps:

1. **Copy `grd.utils.pandoc` → `gpd.utils.pandoc`.** Zero GRD-specific code; the module only talks to the `pandoc` binary. The `_KNOWN_EXTERNAL_FILTERS` tuple is generic tooling.
2. **Copy `grd.mcp.paper.filters/` → `gpd.mcp.paper.filters/`.** Filter names can stay `grd-*` or be renamed to `gpd-*`. All configuration goes through pandoc `Meta` (`figure_base_path`, `crossref_namespaces`, `obsidian_strip_fields`, `math_autowrap`, `figure_placement`, `obsidian_wikilink_style`, `crossref_prefix`) — no hardcoded paths.
3. **Copy `grd.mcp.paper.markdown_support` and `grd.mcp.paper.citations`.** The sigil detection (`_LATEX_SIGIL_PATTERN`) and the pandoc-style `@key` grammar are domain-agnostic. `looks_like_latex()` flags structural LaTeX regardless of the physics/research vocabulary.
4. **Update `render_paper` call sites.** GPD's paper registry should accept an optional `bib_keys` arg and wire it the same way GRD's `compiler.build_paper` does.
5. **Agent spec port.** `grd-paper-writer.md`'s `<authoring_format>` section is pure prompt material — copy it into GPD's equivalent agent, rename references from `.grd/` / `grd-crossref` to GPD equivalents as needed. The `[[phase:N]]` namespace should be generalised to GPD's phase/milestone terminology (consider adding `[[milestone:N]]` in both codebases).
6. **Health check.** `check_pandoc()` already lives in the GRD health registry; GPD's `gpd doctor` can register the same function under `"pandoc"`.
7. **Export workflow.** The `generate_latex` step in `specs/workflows/export.md` uses only the pandoc utilities plus `grd.mcp.paper.template_registry.render_paper`. Swap the import paths and the step ports cleanly.
