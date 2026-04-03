from __future__ import annotations

import json
from pathlib import Path

from gpd.core.manuscript_artifacts import (
    ManuscriptArtifacts,
    locate_publication_artifact,
    resolve_current_manuscript_artifacts,
    resolve_current_manuscript_entrypoint,
    resolve_current_manuscript_root,
)


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_resolve_current_manuscript_artifacts_prefers_manifest_declared_entrypoint(tmp_path: Path) -> None:
    _write(tmp_path / "paper" / "curvature_flow_bounds.tex", "\\documentclass{article}\\begin{document}Hi\\end{document}\n")
    _write(
        tmp_path / "paper" / "ARTIFACT-MANIFEST.json",
        json.dumps(
            {
                "version": 1,
                "paper_title": "Curvature Flow Bounds",
                "journal": "prl",
                "created_at": "2026-04-02T00:00:00+00:00",
                "artifacts": [
                    {
                        "artifact_id": "tex-paper",
                        "category": "tex",
                        "path": "curvature_flow_bounds.tex",
                        "sha256": "0" * 64,
                        "produced_by": "test",
                        "sources": [],
                        "metadata": {},
                    }
                ],
            }
        )
        + "\n",
    )
    _write(tmp_path / "paper" / "BIBLIOGRAPHY-AUDIT.json", "{}\n")
    _write(tmp_path / "paper" / "reproducibility-manifest.json", "{}\n")

    artifacts = resolve_current_manuscript_artifacts(tmp_path)

    assert isinstance(artifacts, ManuscriptArtifacts)
    assert artifacts.manuscript_entrypoint == tmp_path / "paper" / "curvature_flow_bounds.tex"
    assert artifacts.manuscript_root == tmp_path / "paper"
    assert artifacts.artifact_manifest == tmp_path / "paper" / "ARTIFACT-MANIFEST.json"
    assert artifacts.bibliography_audit == tmp_path / "paper" / "BIBLIOGRAPHY-AUDIT.json"
    assert artifacts.reproducibility_manifest == tmp_path / "paper" / "reproducibility-manifest.json"
    assert resolve_current_manuscript_entrypoint(tmp_path) == tmp_path / "paper" / "curvature_flow_bounds.tex"
    assert resolve_current_manuscript_root(tmp_path) == tmp_path / "paper"


def test_resolve_current_manuscript_artifacts_supports_config_derived_markdown_and_canonical_reproducibility(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "manuscript" / "PAPER-CONFIG.json",
        json.dumps(
            {
                "title": "Asymptotic Matching Note",
                "authors": [{"name": "A. Researcher"}],
                "abstract": "Abstract.",
                "sections": [{"heading": "Intro", "content": "Hello."}],
            }
        )
        + "\n",
    )
    _write(tmp_path / "manuscript" / "asymptotic_matching_note.md", "# Manuscript\n")
    _write(tmp_path / "manuscript" / "ARTIFACT-MANIFEST.json", "{}\n")
    _write(tmp_path / "manuscript" / "BIBLIOGRAPHY-AUDIT.json", "{}\n")
    _write(tmp_path / "manuscript" / "reproducibility-manifest.json", "{}\n")

    artifacts = resolve_current_manuscript_artifacts(tmp_path)

    assert artifacts.manuscript_entrypoint == tmp_path / "manuscript" / "asymptotic_matching_note.md"
    assert artifacts.manuscript_root == tmp_path / "manuscript"
    assert artifacts.reproducibility_manifest == tmp_path / "manuscript" / "reproducibility-manifest.json"


def test_resolve_current_manuscript_artifacts_ignores_uppercase_reproducibility_manifest_alias(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write(
        tmp_path / "manuscript" / "PAPER-CONFIG.json",
        json.dumps(
            {
                "title": "Asymptotic Matching Note",
                "authors": [{"name": "A. Researcher"}],
                "abstract": "Abstract.",
                "sections": [{"heading": "Intro", "content": "Hello."}],
            }
        )
        + "\n",
    )
    _write(tmp_path / "manuscript" / "asymptotic_matching_note.md", "# Manuscript\n")
    _write(tmp_path / "manuscript" / "REPRODUCIBILITY-MANIFEST.json", "{}\n")

    requested_filenames: list[tuple[str, ...]] = []

    def fake_locate_publication_artifact(manuscript_root: Path, *filenames: str) -> Path | None:
        requested_filenames.append(filenames)
        if filenames == ("ARTIFACT-MANIFEST.json",):
            return manuscript_root / "ARTIFACT-MANIFEST.json"
        if filenames == ("BIBLIOGRAPHY-AUDIT.json",):
            return manuscript_root / "BIBLIOGRAPHY-AUDIT.json"
        if filenames == ("reproducibility-manifest.json",):
            return manuscript_root / "reproducibility-manifest.json"
        return None

    monkeypatch.setattr("gpd.core.manuscript_artifacts.locate_publication_artifact", fake_locate_publication_artifact)

    artifacts = resolve_current_manuscript_artifacts(tmp_path)

    assert artifacts.manuscript_entrypoint == tmp_path / "manuscript" / "asymptotic_matching_note.md"
    assert requested_filenames == [
        ("ARTIFACT-MANIFEST.json",),
        ("BIBLIOGRAPHY-AUDIT.json",),
        ("reproducibility-manifest.json",),
    ]
    assert artifacts.reproducibility_manifest == tmp_path / "manuscript" / "reproducibility-manifest.json"


def test_locate_publication_artifact_accepts_named_entrypoint_path(tmp_path: Path) -> None:
    manuscript = tmp_path / "draft" / "scalar_gap_bounds.tex"
    _write(manuscript, "\\documentclass{article}\\begin{document}Hi\\end{document}\n")
    _write(tmp_path / "draft" / "ARTIFACT-MANIFEST.json", "{}\n")

    assert locate_publication_artifact(manuscript, "ARTIFACT-MANIFEST.json") == tmp_path / "draft" / "ARTIFACT-MANIFEST.json"


def test_resolve_current_manuscript_artifacts_does_not_fall_back_to_legacy_main_entrypoint(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "draft" / "main.tex", "\\documentclass{article}\\begin{document}Hi\\end{document}\n")

    assert resolve_current_manuscript_entrypoint(tmp_path) is None


def test_resolve_current_manuscript_artifacts_requires_manifest_or_config_for_topic_stem_entrypoint(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "draft" / "curvature_flow_bounds.tex", "\\documentclass{article}\\begin{document}Hi\\end{document}\n")
    _write(
        tmp_path / "draft" / "ARTIFACT-MANIFEST.json",
        json.dumps(
            {
                "version": 1,
                "paper_title": "Curvature Flow Bounds",
                "journal": "jhep",
                "created_at": "2026-04-02T00:00:00+00:00",
                "artifacts": [
                    {
                        "artifact_id": "tex-draft",
                        "category": "tex",
                        "path": "curvature_flow_bounds.tex",
                        "sha256": "0" * 64,
                        "produced_by": "test",
                        "sources": [],
                        "metadata": {},
                    }
                ],
            }
        ),
    )

    assert resolve_current_manuscript_entrypoint(tmp_path) == tmp_path / "draft" / "curvature_flow_bounds.tex"


def test_resolve_current_manuscript_entrypoint_fails_closed_when_manifest_and_config_disagree(tmp_path: Path) -> None:
    _write(tmp_path / "paper" / "curvature_flow_bounds.tex", "\\documentclass{article}\\begin{document}Hi\\end{document}\n")
    _write(tmp_path / "paper" / "alternate_title.tex", "\\documentclass{article}\\begin{document}Hi\\end{document}\n")
    _write(
        tmp_path / "paper" / "ARTIFACT-MANIFEST.json",
        json.dumps(
            {
                "version": 1,
                "paper_title": "Curvature Flow Bounds",
                "journal": "jhep",
                "created_at": "2026-04-02T00:00:00+00:00",
                "artifacts": [
                    {
                        "artifact_id": "tex-paper",
                        "category": "tex",
                        "path": "curvature_flow_bounds.tex",
                        "sha256": "0" * 64,
                        "produced_by": "test",
                        "sources": [],
                        "metadata": {},
                    }
                ],
            }
        )
        + "\n",
    )
    _write(
        tmp_path / "paper" / "PAPER-CONFIG.json",
        json.dumps(
            {
                "title": "Alternate Title",
                "authors": [{"name": "A. Researcher"}],
                "abstract": "Abstract.",
                "sections": [{"heading": "Intro", "content": "Hello."}],
            }
        )
        + "\n",
    )

    assert resolve_current_manuscript_entrypoint(tmp_path) is None
    assert resolve_current_manuscript_root(tmp_path) is None


def test_resolve_current_manuscript_artifacts_returns_none_when_missing(tmp_path: Path) -> None:
    artifacts = resolve_current_manuscript_artifacts(tmp_path)

    assert artifacts == ManuscriptArtifacts(
        project_root=tmp_path,
        manuscript_root=None,
        manuscript_entrypoint=None,
        artifact_manifest=None,
        bibliography_audit=None,
        reproducibility_manifest=None,
    )
    assert resolve_current_manuscript_entrypoint(tmp_path) is None
    assert resolve_current_manuscript_root(tmp_path) is None
