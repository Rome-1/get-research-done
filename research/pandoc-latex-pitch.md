# Pitch: Pandoc as GRD's Structured LaTeX Conversion Layer

**Bead:** ge-6we
**Author:** alice (crew)
**Date:** 2026-04-11
**Status:** Pitch for Rome's approval

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
