"""Paper build subcommand."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from grd.cli._helpers import (
    _default_paper_output_dir,
    _format_display_path,
    _get_cwd,
    _load_json_document,
    _output,
    _reject_legacy_paper_config_location,
    _resolve_bibliography_path,
    _resolve_existing_input_path,
    _resolve_paper_config_paths,
    app,
)
from grd.core.errors import GRDError


@app.command("paper-build")
def paper_build(
    config_path: str | None = typer.Argument(
        None,
        help="Path to a PaperConfig JSON file. Defaults to paper/, manuscript/, or draft/ candidates.",
    ),
    output_dir: str | None = typer.Option(
        None,
        "--output-dir",
        help="Directory for emitted manuscript artifacts. Defaults to the config directory.",
    ),
    bibliography: str | None = typer.Option(
        None,
        "--bibliography",
        help="Optional .bib file to ingest before building the manuscript.",
    ),
    citation_sources: str | None = typer.Option(
        None,
        "--citation-sources",
        help="Optional JSON file containing a CitationSource array for bibliography generation/audit.",
    ),
    enrich_bibliography: bool = typer.Option(
        True,
        "--enrich-bibliography/--no-enrich-bibliography",
        help="Allow bibliography enrichment when citation sources are provided.",
    ),
) -> None:
    """Build a paper from the canonical mcp.paper JSON config surface."""

    from grd.core.storage_paths import DurableOutputKind, ProjectStorageLayout
    from grd.mcp.paper.bibliography import CitationSource
    from grd.mcp.paper.compiler import build_paper

    config_file = _resolve_existing_input_path(
        config_path,
        candidates=(
            "paper/PAPER-CONFIG.json",
            "paper/paper-config.json",
            "manuscript/PAPER-CONFIG.json",
            "manuscript/paper-config.json",
            "draft/PAPER-CONFIG.json",
            "draft/paper-config.json",
        ),
        label="paper config",
    )
    _reject_legacy_paper_config_location(config_file)
    raw_config = _load_json_document(str(config_file))
    if not isinstance(raw_config, dict):
        raise GRDError(f"Paper config must be a JSON object: {_format_display_path(config_file)}")

    paper_config = _resolve_paper_config_paths(raw_config, base_dir=config_file.parent)
    output_path = Path(output_dir) if output_dir else _default_paper_output_dir(config_file)
    if not output_path.is_absolute():
        output_path = _get_cwd() / output_path
    output_path = output_path.resolve(strict=False)
    storage_layout = ProjectStorageLayout(_get_cwd())
    storage_layout.validate_final_output(output_path)
    storage_check = storage_layout.check_user_output(
        output_path,
        preferred_kinds=(
            DurableOutputKind.PAPER,
            DurableOutputKind.MANUSCRIPT,
            DurableOutputKind.DRAFT,
        ),
    )

    bib_source = _resolve_bibliography_path(
        explicit_path=bibliography,
        config_path=config_file,
        output_dir=output_path,
        bib_stem=paper_config.bib_file.removesuffix(".bib"),
    )
    bib_data = None
    if bib_source is not None:
        from pybtex.database import parse_file

        try:
            bib_data = parse_file(str(bib_source))
        except Exception as exc:  # noqa: BLE001
            raise GRDError(f"Failed to parse bibliography {_format_display_path(bib_source)}: {exc}") from exc

    citation_payload = None
    citation_source_path: Path | None = None
    if citation_sources is not None:
        citation_source_path = _resolve_existing_input_path(citation_sources, candidates=(), label="citation sources")
        raw_sources = _load_json_document(str(citation_source_path))
        if not isinstance(raw_sources, list):
            raise GRDError(f"Citation sources must be a JSON array: {_format_display_path(citation_source_path)}")
        citation_payload = [CitationSource.model_validate(item) for item in raw_sources]

    result = asyncio.run(
        build_paper(
            paper_config,
            output_path,
            bib_data=bib_data,
            citation_sources=citation_payload,
            enrich_bibliography=enrich_bibliography,
        )
    )

    payload = {
        "config_path": _format_display_path(config_file),
        "output_dir": _format_display_path(output_path),
        "tex_path": _format_display_path(output_path / "main.tex"),
        "bibliography_source": _format_display_path(bib_source),
        "citation_sources_path": _format_display_path(citation_source_path),
        "manifest_path": _format_display_path(result.manifest_path),
        "bibliography_audit_path": _format_display_path(result.bibliography_audit_path),
        "pdf_path": _format_display_path(result.pdf_path),
        "success": result.success,
        "error_count": len(result.errors),
        "errors": result.errors,
        "warnings": list(storage_check.warnings),
    }
    _output(payload)
    if not result.success:
        raise typer.Exit(code=1)
