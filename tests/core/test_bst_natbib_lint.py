"""Tests for grd.core.bst_natbib_lint — static lint of bst/natbib pairings."""

from __future__ import annotations

from pathlib import Path

from grd.core.bst_natbib_lint import (
    NATBIB_AWARE_BSTS,
    NUMERIC_ONLY_BSTS,
    Finding,
    iter_packaged_template_sources,
    lint_default_sources,
    lint_directory,
    lint_template,
)

# ─── Numeric-only bst + natbib (the ge-kus / naturemag bug class) ────────────


class TestNumericBstWithNatbib:
    """Numeric-only bst paired with natbib must FAIL — the silent-render bug."""

    def test_plain_with_usepackage_natbib_flagged(self) -> None:
        tex = r"""
        \documentclass{article}
        \usepackage{natbib}
        \begin{document}
        \bibliographystyle{plain}
        \end{document}
        """
        findings = lint_template(tex, "plain.tex")
        assert len(findings) == 1
        assert findings[0].severity == "error"
        assert "'plain'" in findings[0].message
        assert "(author?)" in findings[0].message

    def test_naturemag_with_natbib_flagged_ge_kus_class(self) -> None:
        # Direct mirror of the naturemag bug that fixed in ge-5iu.
        tex = r"""
        \documentclass[12pt]{article}
        \usepackage[numbers,super,sort&compress]{natbib}
        \bibliographystyle{naturemag}
        """
        findings = lint_template(tex, "nature.tex")
        assert len(findings) == 1
        assert "'naturemag'" in findings[0].message

    def test_unsrt_with_natbib_flagged(self) -> None:
        tex = r"""
        \usepackage{natbib}
        \bibliographystyle{unsrt}
        """
        findings = lint_template(tex, "t.tex")
        assert len(findings) == 1


# ─── natbib-aware bst with no natbib loaded ──────────────────────────────────


class TestNatbibAwareBstWithoutNatbib:
    def test_plainnat_without_natbib_flagged(self) -> None:
        tex = r"""
        \documentclass{article}
        \bibliographystyle{plainnat}
        """
        findings = lint_template(tex, "missing-natbib.tex")
        assert len(findings) == 1
        assert "'plainnat'" in findings[0].message
        assert "natbib is not loaded" in findings[0].message

    def test_unsrtnat_without_natbib_flagged(self) -> None:
        tex = r"""
        \documentclass{article}
        \bibliographystyle{unsrtnat}
        """
        findings = lint_template(tex, "t.tex")
        assert len(findings) == 1


# ─── natbib detection ────────────────────────────────────────────────────────


class TestNatbibDetection:
    """All three real-world ways templates load natbib must be detected."""

    def test_plain_usepackage_natbib(self) -> None:
        tex = r"\usepackage{natbib}" + "\n" + r"\bibliographystyle{plainnat}"
        assert lint_template(tex, "t.tex") == []

    def test_usepackage_natbib_with_options(self) -> None:
        # Mirrors the live nature_template.tex form.
        tex = r"\usepackage[numbers,super,sort&compress]{natbib}" + "\n" + r"\bibliographystyle{unsrtnat}"
        assert lint_template(tex, "t.tex") == []

    def test_revtex_natbib_class_option(self) -> None:
        # Mirrors the live prl_template.tex form (post ge-5iu).
        tex = r"\documentclass[aps,prl,twocolumn,natbib]{revtex4-2}" + "\n" + r"\bibliographystyle{apsrev4-2}"
        assert lint_template(tex, "prl.tex") == []

    def test_mnras_usenatbib_class_option(self) -> None:
        # Mirrors the live mnras_template.tex form.
        tex = r"\documentclass[usenatbib]{mnras}" + "\n" + r"\bibliographystyle{mnras}"
        assert lint_template(tex, "mnras.tex") == []

    def test_jheppub_provides_natbib(self) -> None:
        # JHEP.bst is natbib-aware but the template loads jheppub, not natbib.
        tex = r"""
        \documentclass{article}
        \usepackage{jheppub}
        \bibliographystyle{JHEP}
        """
        assert lint_template(tex, "jhep.tex") == []

    def test_aastex_documentclass_provides_natbib(self) -> None:
        tex = r"""
        \documentclass{aastex631}
        \bibliographystyle{aasjournal}
        """
        assert lint_template(tex, "apj.tex") == []


# ─── Robustness: comments, missing bst, unknown bst ──────────────────────────


class TestRobustness:
    def test_no_bibliographystyle_returns_no_findings(self) -> None:
        tex = r"\documentclass{article}\usepackage{natbib}"
        assert lint_template(tex, "t.tex") == []

    def test_unknown_bst_is_silent(self) -> None:
        # We only know about a finite catalog; unknown bsts pass through.
        tex = r"""
        \usepackage{natbib}
        \bibliographystyle{my-weird-internal-style}
        """
        assert lint_template(tex, "t.tex") == []

    def test_commented_out_natbib_does_not_count(self) -> None:
        # If natbib is only loaded inside a comment, it's not actually loaded.
        tex = r"""
        \documentclass{article}
        % \usepackage{natbib}
        \bibliographystyle{plainnat}
        """
        findings = lint_template(tex, "t.tex")
        assert len(findings) == 1
        assert "'plainnat'" in findings[0].message

    def test_commented_out_bibliographystyle_does_not_fire(self) -> None:
        tex = r"""
        \documentclass{article}
        \usepackage{natbib}
        % \bibliographystyle{plain}
        \bibliographystyle{plainnat}
        """
        assert lint_template(tex, "t.tex") == []

    def test_escaped_percent_does_not_terminate_line(self) -> None:
        tex = r"""
        \usepackage{natbib} % comment with \% escaped
        \bibliographystyle{plainnat}
        """
        assert lint_template(tex, "t.tex") == []


# ─── Source enumeration / wiring ─────────────────────────────────────────────


class TestPackagedSources:
    def test_iter_packaged_templates_includes_all_journals(self) -> None:
        sources = dict(iter_packaged_template_sources())
        labels = set(sources.keys())
        for journal in ("apj", "jfm", "jhep", "mnras", "nature", "prl"):
            assert any(f"templates/{journal}/" in label for label in labels), (
                f"missing template for {journal}: {labels}"
            )

    def test_iter_packaged_includes_export_md_wrapper(self) -> None:
        sources = dict(iter_packaged_template_sources())
        export_blocks = [label for label in sources if "export.md" in label]
        assert export_blocks, "expected at least one LaTeX block in export.md"

    def test_shipped_templates_pass_lint(self) -> None:
        # Regression: the packaged templates must stay in a state that
        # passes the lint. If this fails, we're shipping the bug.
        findings = lint_default_sources()
        assert findings == [], "shipped templates regressed: " + "\n".join(f"{f.source}: {f.message}" for f in findings)


class TestLintDirectory:
    def test_walks_tex_files_recursively(self, tmp_path: Path) -> None:
        sub = tmp_path / "templates" / "broken"
        sub.mkdir(parents=True)
        (sub / "bad.tex").write_text(
            r"\usepackage{natbib}\bibliographystyle{plain}",
            encoding="utf-8",
        )
        (sub / "good.tex").write_text(
            r"\usepackage{natbib}\bibliographystyle{plainnat}",
            encoding="utf-8",
        )
        findings = lint_directory(tmp_path)
        assert len(findings) == 1
        assert findings[0].source.endswith("bad.tex")

    def test_empty_dir_returns_no_findings(self, tmp_path: Path) -> None:
        assert lint_directory(tmp_path) == []


# ─── Bst catalog invariants ──────────────────────────────────────────────────


class TestBstCatalogs:
    def test_no_bst_appears_in_both_sets(self) -> None:
        # Each bst must be unambiguously natbib-aware OR numeric-only —
        # otherwise the lint would emit contradictory findings.
        assert NATBIB_AWARE_BSTS.isdisjoint(NUMERIC_ONLY_BSTS)

    def test_known_silent_failure_bsts_are_numeric(self) -> None:
        # These are the bsts that produced the production bugs we are
        # protecting against. They must stay in the numeric set.
        assert "plain" in NUMERIC_ONLY_BSTS  # ge-kus
        assert "naturemag" in NUMERIC_ONLY_BSTS  # naturemag fix

    def test_known_safe_bsts_are_natbib_aware(self) -> None:
        for bst in ("plainnat", "unsrtnat", "apsrev4-2", "mnras", "JHEP"):
            assert bst in NATBIB_AWARE_BSTS


# ─── Health check integration ────────────────────────────────────────────────


class TestHealthCheckWiring:
    def test_check_bst_natbib_pairing_returns_ok_for_clean_templates(self) -> None:
        # Use the live packaged templates — should be OK in a clean tree.
        from grd.core.health import CheckStatus, check_bst_natbib_pairing

        result = check_bst_natbib_pairing(Path.cwd())
        assert result.label == "BST/Natbib Pairing"
        assert result.status == CheckStatus.OK
        assert result.details["finding_count"] == 0
        # Must have actually scanned multiple sources, not silently no-oped.
        assert result.details["sources_checked"] >= 6

    def test_finding_dataclass_carries_source_and_severity(self) -> None:
        f = Finding(source="x.tex", severity="error", message="m")
        assert f.source == "x.tex"
        assert f.severity == "error"
