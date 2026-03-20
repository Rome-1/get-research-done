"""YAML frontmatter CRUD subcommands."""

from __future__ import annotations

import json

import typer

from grd.cli._helpers import _error, _get_cwd, _output, _run_frontmatter_validation

frontmatter_app = typer.Typer(help="YAML frontmatter operations on markdown files")


@frontmatter_app.command("get")
def frontmatter_get(
    file: str = typer.Argument(..., help="Markdown file path"),
    field: str | None = typer.Option(None, "--field", help="Specific field to get"),
) -> None:
    """Get frontmatter from a markdown file."""
    from grd.core.frontmatter import extract_frontmatter

    file_path = _get_cwd() / file
    try:
        fm_content = file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _error(f"File not found: {file}")
    meta, _ = extract_frontmatter(fm_content)
    if field:
        _output(meta.get(field))
    else:
        _output(meta)


@frontmatter_app.command("set")
def frontmatter_set(
    file: str = typer.Argument(..., help="Markdown file path"),
    field: str = typer.Option(..., "--field", help="Field name"),
    value: str | None = typer.Option(None, "--value", help="Field value (omit to clear)"),
) -> None:
    """Set a frontmatter field."""
    from grd.core.frontmatter import splice_frontmatter

    file_path = _get_cwd() / file
    try:
        fm_content = file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _error(f"File not found: {file}")
    updated = splice_frontmatter(fm_content, {field: value})
    file_path.write_text(updated, encoding="utf-8")
    _output({"updated": field, "value": value})


@frontmatter_app.command("merge")
def frontmatter_merge(
    file: str = typer.Argument(..., help="Markdown file path"),
    data: str = typer.Option(..., "--data", help="JSON data to merge"),
) -> None:
    """Merge JSON data into frontmatter."""
    from grd.core.frontmatter import deep_merge_frontmatter

    try:
        merge_data = json.loads(data)
    except json.JSONDecodeError as e:
        _error(f"Malformed JSON in --data: {e}")
    file_path = _get_cwd() / file
    try:
        fm_content = file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _error(f"File not found: {file}")
    updated = deep_merge_frontmatter(fm_content, merge_data)
    file_path.write_text(updated, encoding="utf-8")
    _output({"merged": True, "file": file})


@frontmatter_app.command("validate")
def frontmatter_validate(
    file: str = typer.Argument(..., help="Markdown file path"),
    schema: str = typer.Option(..., "--schema", help="Schema name to validate against"),
) -> None:
    """Validate frontmatter against a schema."""
    _run_frontmatter_validation(file, schema)
